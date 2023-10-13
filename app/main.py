from fastapi import Depends, FastAPI, Body, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from config import settings
from services.book import BookService

from sql_app import crud, models, schemas
from sql_app.database import get_db, engine, SessionLocal
from sql_app.schemas import GutenburgBookUrl

models.Base.metadata.create_all(bind=engine)

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

templates = Jinja2Templates(directory="templates")

print(f'settings={settings}')

@app.get("/", response_class=HTMLResponse)
async def root(request: Request, db: Session = Depends(get_db)):
    books = crud.get_books(db)
    print(f'books={books}')
    return templates.TemplateResponse("base.html", {
        "request": request,
        "books": books
    })


@app.post('/books/import/')
async def import_book(data: GutenburgBookUrl, db: Session = Depends(get_db)):
    book, status = await BookService.import_from_gutenburg_url(db, data.book_url)
    if book:
        return JSONResponse(content={"success": True})
    else:
        return JSONResponse(content={"error": status})