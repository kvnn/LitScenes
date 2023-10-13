from sqlalchemy.orm import Session

from . import models, schemas


def get_book_by_gutenburg_id(db: Session, gutenburg_id: id):
    # import pdb; pdb.set_trace()
    return db.query(models.Book).filter(models.Book.gutenburg_id == gutenburg_id).first()

def get_books(db: Session):
    return db.query(models.Book).all()

def create_book(db: Session, book: schemas.BookCreate):
    db_book = models.Book(**book.dict())
    db.add(db_book)
    db.commit()
    db.refresh(db_book)
    return db_book

def create_chunk(db: Session, chunk: schemas.ChunkCreate):
    db_chunk = models.Chunk(**chunk.dict())
    db.add(db_chunk)
    db.commit()
    db.refresh(db_chunk)
    return db_chunk