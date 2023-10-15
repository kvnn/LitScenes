import asyncio
import json
import logging
import os

from celery.result import AsyncResult
from fastapi import Depends, FastAPI, Body, Request, WebSocket
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
    scene_prompt = models.ScenePrompt(
        title=seeds.chunk_to_scene_prompt_01['title'],
        content=seeds.chunk_to_scene_prompt_01['content'],
        max_length=seeds.chunk_to_scene_prompt_01['max_length']
    )
    db.add(scene_prompt)
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

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    error_stack = {}
    await websocket.accept()
    while True:
        data = await websocket.receive_text()
        logger.info(f"websocket receive_text() Message text was: {data}")
        async def loop():
            try:
                generate_scene_task_id = redis_client.get('generate_scene_task_id')
                generate_scene_task_id = generate_scene_task_id.decode('utf-8') if generate_scene_task_id else None
                print(f'generate_scene_task_id={generate_scene_task_id}')
                if generate_scene_task_id:
                    print(f'generate_scene_task_id exists and is {generate_scene_task_id}')
                    task_details = AsyncResult(generate_scene_task_id)

                    if task_details and task_details.result and 'content' in task_details.result:
                        await websocket.send_text(json.dumps({
                            "type": "scene_generate",
                            "task_id": generate_scene_task_id,
                            "task_results": task_details.result
                        }))
                    else:
                        logger.info(f'result not in task_details. task_details={task_details}')

                    if task_details and task_details.ready():
                        logger.info(f'task complete task_details={task_details}')
                        await websocket.send_text(json.dumps({
                            "type": "scene_generate",
                            "task_id": generate_scene_task_id,
                            "task_results": task_details.result,
                            "completed": True
                        }))
                        redis_client.delete('generate_scene_task_id')

            except Exception as e:
                # import pdb; pdb.set_trace()
                logger.info(f'[error] generate_scene_task_id={generate_scene_task_id}')
                if generate_scene_task_id:
                    error_stack[generate_scene_task_id] = error_stack.get(generate_scene_task_id, 0) + 1
                    if error_stack[generate_scene_task_id] > 5:
                        redis_client.delete('generate_scene_task_id')
                        error_stack[generate_scene_task_id] = 0
                        logger.info(f'Too many errors for {generate_scene_task_id}, deleted')
                    logger.info(f'[error] AsyncResult(generate_scene_task_id)={AsyncResult(generate_scene_task_id)}')
                logger.error(f'[error] generate_scene_task websocket send error: {e}')

            await asyncio.sleep(1)
            await loop()
        await loop()
