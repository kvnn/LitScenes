import asyncio
import json
import logging
import os
from typing import List

from celery.result import AsyncResult
from fastapi import Depends, FastAPI, Body, Request, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from fastapi.middleware.cors import CORSMiddleware
import redis

from config import settings
from services.book import BookService
from services.scene import SceneService

from sql_app import crud, models, schemas, seed_values as seeds
from sql_app.database import get_db, engine, SessionLocal
from sql_app.schemas import ImportGutenburgBookRequest, CreateSceneRequest, CreatePromptTemplateRequest


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

models.Base.metadata.create_all(bind=engine)

app = FastAPI()

templates = Jinja2Templates(directory="templates")

redis_url = settings.redis_url
redis_client = redis.from_url(redis_url)

print(f'settings={settings}')


''' Seed our db '''
db = SessionLocal()
if not db.query(models.ScenePromptTemplate).first():
    for key, scene_prompt in seeds.scene_prompts.items():
        db_item = models.ScenePromptTemplate(
            title=scene_prompt['title'],
            content=scene_prompt['content'],
        )
    db.add(db_item)
    db.commit()

if not db.query(models.SceneAesthetic).first():
    for aesthetic in seeds.scene_prompt_aesthetics:
        db.add(models.SceneAesthetic(title=aesthetic))
    db.commit()
''' end Seed '''

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],  # Adjust this to your needs
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/", response_class=HTMLResponse)
async def root(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse("base.html", {
        "request": request,
        "books": crud.get_books(db)
    })


@app.get('/books/{id}', response_class=HTMLResponse)
def book(request: Request, id: int, db: Session = Depends(get_db)):
    books = crud.get_books(db)
    return templates.TemplateResponse(
        'book.html', {
            "request": request,
            'books': books,
            'book': crud.get_book_by_id(db, id),
            'scene_aesthetics': crud.get_scene_aesthetics(db)
        })

@app.get('/scenes/recent')
async def recent_scenes(db: Session = Depends(get_db)):
    scenes = crud.get_recent_scenes(db)
    return JSONResponse(content=scenes)

@app.post('/books/import')
async def import_book(data: ImportGutenburgBookRequest, db: Session = Depends(get_db)):
    book, status = await BookService.import_from_gutenburg_url(db, data.book_url)
    if book:
        return JSONResponse(content={"success": True})
    else:
        return JSONResponse(content={"error": status})


@app.post('/scenes/generate')
def generate_scene(data: CreateSceneRequest, db: Session = Depends(get_db)):
    task_id, error = SceneService.generate_scene(db, data)
    if task_id:
        return JSONResponse(content={"task_id": task_id})
    return JSONResponse(content={"error": error})


@app.get('/prompt_templates')
async def get_prompt_templates(db: Session = Depends(get_db)):
    return crud.get_prompt_templates(db)

@app.post('/prompt_templates')
def create_prompt_template(data: CreatePromptTemplateRequest, db: Session = Depends(get_db)):
    try:
        assert len(data.title) > 3
        assert len(data.content) > 6
        SceneService.get_prompt_template_output(data.content, 'title', 'aesthetic')
    except Exception as err:
        print(f'Error formatting prompt: {err}')
        raise HTTPException(status_code=404, detail="Error formatting prompt. Title must be 4 characters or more and content must be 6 or more. Invalid template tags will also cause error.")

    prompt_template = crud.create_prompt_template(db=db, title=data.title, content=data.content)

    return prompt_template


@app.get('/scenes/from_chunk/{chunk_id}')
async def scenes_from_chunk(chunk_id: int, db: Session = Depends(get_db)):
    return crud.get_scenes_by_chunk_id(db, chunk_id)


@app.get('/images/from_chunk/{chunk_id}')
async def images_from_chunk(chunk_id: int, db: Session = Depends(get_db)):
    return crud.get_images_by_chunk_id(db, chunk_id)


@app.websocket("/ws/{task_id}")
async def websocket_endpoint(websocket: WebSocket, task_id: str):
    await websocket.accept()
    try:
        if not await is_valid_task_id(task_id):
            await websocket.send_text(json.dumps({"error": f"Invalid task ID {task_id}"}))
            return

        await subscribe_to_task_updates(websocket, task_id)
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")


async def is_valid_task_id(task_id):
    try:
        return redis_client.exists(task_id)
    except Exception as e:
        logger.error(f"Error while validating task ID: {e}")
        return False


async def subscribe_to_task_updates(websocket, task_id):
    try:
        # Start a separate task to send updates while the task is running
        await asyncio.create_task(send_task_updates(websocket, task_id))
    except Exception as e:
        logger.error(f"Error while subscribing to task updates: {e}")


async def send_task_updates(websocket, task_id):
    try:
        while True:
            # TODO: if determine if the celery backend is down / task is not running
            # and handle appropriately
            task_details = AsyncResult(task_id)
            
            print(f'task_details for {task_id} is {task_details.result} with state {task_details.state}')

            if task_details.ready():
                logger.info(f'send_task_updates] clearing task result={task_details.result}')
                await send_task_result(websocket, task_id, task_details.result, completed=True)
                await clear_task_id(task_id)
                break
            else:
                await send_task_result(websocket, task_id, task_details.result)

            await asyncio.sleep(1)
    except Exception as e:
        logger.error(f"Error while sending task updates: {e}")


async def send_task_result(websocket, task_id, result, completed=False):
    try:
        # Attempt to serialize the result to JSON
        try:
            payload = {
                "task_id": task_id,
                "task_results": result,
                "completed": completed
            }
            await websocket.send_text(json.dumps(payload))
        except Exception as e:
            logger.warn(f'[send_task_result] send for {result} due to error {e}')
        
    except Exception as e:
        logger.error(f"Error sending task result over WebSocket: {e}")


async def clear_task_id(task_id):
    try:
        redis_client.delete(task_id)
    except Exception as e:
        logger.error(f"Error clearing task ID: {e}")