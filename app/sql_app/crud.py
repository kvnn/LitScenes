from sqlalchemy.orm import Session

from . import models, schemas


''' Books'''
def get_books(db: Session):
    return db.query(models.Book).all()

def get_book_by_id(db: Session, id: int):
    return db.query(models.Book).filter(models.Book.id == id).first()

def get_book_by_gutenburg_id(db: Session, gutenburg_id: int):
    return db.query(models.Book).filter(models.Book.gutenburg_id == gutenburg_id).first()

def create_book(db: Session, book: schemas.BookCreate):
    db_book = models.Book(**book.dict())
    db.add(db_book)
    db.commit()
    db.refresh(db_book)
    return db_book

''' Chunks '''
def create_chunk(db: Session, chunk: schemas.ChunkCreate):
    db_chunk = models.Chunk(**chunk.dict())
    db.add(db_chunk)
    db.commit()
    db.refresh(db_chunk)
    return db_chunk

''' Scenes '''
def get_scene_prompts(db: Session):
    return db.query(models.ScenePrompt).all()

def get_scene_prompt_by_id(db: Session, id: int):
    return db.query(models.ScenePrompt).filter(models.ScenePrompt.id == id).first()

def get_scene_aesthetics(db: Session):
    return db.query(models.SceneAesthetic).all()

def create_scene(db: Session, title: str, content: str, aesthetic_id=int, chunk_id=int, scene_prompt_id=int):
    db_scene = models.Scene(
        title=title,
        content=content,
        aesthetic_id=aesthetic_id,
        chunk_id=chunk_id,
        scene_prompt_id=scene_prompt_id
    )
    db.add(db_scene)
    db.commit()
    db.refresh(db_scene)
    return db_scene