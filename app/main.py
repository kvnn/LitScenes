import asyncio
import json
import logging
import os
from typing import List

from celery.result import AsyncResult
from fastapi import Depends, FastAPI, Body, Request, WebSocket, WebSocketDisconnect
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
from sql_app.schemas import ImportGutenburgBookRequest, CreateSceneRequest


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

models.Base.metadata.create_all(bind=engine)

app = FastAPI()

templates = Jinja2Templates(directory="templates")

redis_url = os.environ.get("REDIS_URL")
redis_client = redis.from_url(redis_url)

print(f'settings={settings}')


''' Seed our db '''
db = SessionLocal()
if not db.query(models.ScenePrompt).first():
    for key, scene_prompt in seeds.scene_prompts.items:
        db_item = models.ScenePrompt(
            title=scene_prompt['title'],
            content=scene_prompt['content'],
            max_length=scene_prompt['max_length']
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
    books = crud.get_books(db)
    logger.info(f'AHHH HERE ARE MY books={books}')
    return templates.TemplateResponse("base.html", {
        "request": request,
        "books": books
    })

@app.get('/books/{id}', response_class=HTMLResponse)
def book(request: Request, id: int, db: Session = Depends(get_db)):
    books = crud.get_books(db)
    return templates.TemplateResponse(
        'book.html', {
            "request": request,
            'books': books,
            'book': crud.get_book_by_id(db, id),
            'scene_prompts': crud.get_scene_prompts(db),
            'scene_aesthetics': crud.get_scene_aesthetics(db)
        })

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

@app.get('/scenes_from_chunk/{chunk_id}')
async def scenes_from_chunk(chunk_id: int, db: Session = Depends(get_db)):
    return crud.get_scenes_by_chunk_id(db, chunk_id)

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
            task_details = AsyncResult(task_id)

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
                "type": "scene_generate",
                "task_id": task_id,
                "task_results": result,
                "completed": completed
            }
            await websocket.send_text(json.dumps(payload))
        except Exception as e:
            logger.warn(f'[send_task_result] send for {result} due to error {e}')
            result_json = str(result)
        
    except Exception as e:
        logger.error(f"Error sending task result over WebSocket: {e}")

async def clear_task_id(task_id):
    try:
        redis_client.delete(task_id)
    except Exception as e:
        logger.error(f"Error clearing task ID: {e}")