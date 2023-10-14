import logging

from fastapi import Depends, FastAPI, Body, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from fastapi.middleware.cors import CORSMiddleware


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

