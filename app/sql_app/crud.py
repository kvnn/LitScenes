import json
import logging

from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session
from sqlalchemy.sql import text

from utils import get_scene_image_url
from . import models, schemas


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


''' Books'''
def get_books(db: Session):
    return db.query(models.Book).order_by(models.Book.title.asc()).all()

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
def get_recent_scenes(db: Session):
    query = text('''SELECT DISTINCT ON (s.id)
                s.id as scene_id,
                si.filename AS scene_image_filename,
                s.chunk_id,
                c.book_id,
                s.title as scene_title,
                SUBSTRING(s.content FROM 1 FOR 200) as scene_content
            FROM
                scenes s
            JOIN
                scene_images si ON s.id = si.scene_id
            JOIN
                chunks c ON s.chunk_id = c.id
            JOIN
                books b ON c.book_id = b.id
            ORDER BY
                s.id, s.dateadded DESC
            LIMIT 20;''')

    scenes = db.execute(query).mappings().all()
    scenes = jsonable_encoder(scenes)

    for scene in scenes:
        scene['scene_image_url'] = get_scene_image_url(scene['scene_image_filename'])

    return scenes

def get_scenes_by_chunk_id(db: Session, chunk_id: int):
    return db.query(models.Scene).filter(models.Scene.chunk_id == chunk_id).order_by(models.Scene.dateadded.desc()).all()

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

''' Scene Prompts and Images '''
def get_prompt_templates(db: Session):
    return db.query(models.ScenePromptTemplate).order_by(models.ScenePromptTemplate.title).all()    

def create_prompt_template(db: Session, title: str, content: str):
    prompt_template = models.ScenePromptTemplate(
        title=title,
        content=content
    )
    db.add(prompt_template)
    db.commit()
    db.refresh(prompt_template)
    return prompt_template

def get_images_by_chunk_id(db: Session, chunk_id:int):
    images = db.query(models.SceneImage).filter(models.SceneImage.chunk_id == chunk_id).order_by(models.SceneImage.dateadded.desc()).all()
    for image in images:
        image.url = get_scene_image_url(image.filename)
    return images

def create_scene_image_prompt(db: Session, scene_id: int, content: str):
    new = models.SceneImagePrompt(
        scene_id=scene_id,
        content=content
    )
    db.add(new)
    db.commit()
    return new

def create_scene_image(db: Session, scene_id: int, chunk_id: int, scene_image_prompt_id: int, filename: str):
    new = models.SceneImage(
        scene_image_prompt_id=scene_image_prompt_id,
        chunk_id=chunk_id,
        scene_id=scene_id,
        filename=filename
    )
    db.add(new)
    db.commit()
    return new
