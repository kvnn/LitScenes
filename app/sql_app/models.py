from datetime import datetime
from uuid import uuid4

from sqlalchemy import create_engine, Column, DateTime, Integer, String, Text, ForeignKey
from sqlalchemy.orm import DeclarativeBase, relationship, sessionmaker
from sqlalchemy.ext.declarative import declarative_base

from .database import Base
from config import settings


''' Define our models '''
class TimestampMixin:
    dateadded = Column(DateTime, default=datetime.utcnow, nullable=False)
    dateupdated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


# Define the Book model
class Book(Base, TimestampMixin):
    __tablename__ = 'books'
    
    id = Column(Integer, primary_key=True)
    gutenburg_id = Column(Integer, nullable=True, unique=True)
    gutenburg_url = Column(String(255), nullable=True, unique=True)

    title = Column(String(255), nullable=False)
    author = Column(String(255), nullable=False)
    status = Column(String(255), nullable=False, default='pending')

    chunks = relationship('Chunk', backref='book', lazy=True)
    
    @property
    def dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'author': self.author,
            'gutenburg_id': self.gutenburg_id,
            'dateadded': self.dateadded,
            'dateupdated': self.dateupdated,
        }
    
    # @classmethod
    # def get_by_id(cls, id):
    #     return db.session.execute(db.select(Book).where(Book.id == id)).scalar()

    # @classmethod
    # def get_list(cls):
    #     return db.query(Book).all()



# Define the Chunk model
class Chunk(Base, TimestampMixin):
    __tablename__ = 'chunks'
    
    id = Column(Integer, primary_key=True)
    book_id = Column(Integer, ForeignKey('books.id'), nullable=False)
    sequence_number = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)



class SceneAesthetic(Base, TimestampMixin):
    __tablename__ = 'scene_aesthetics'
    id = Column(Integer, primary_key=True)
    title = Column(String(255), nullable=False)


class ScenePrompt(Base, TimestampMixin):
    __tablename__ = 'scene_prompts'
    id = Column(Integer, primary_key=True)
    title = Column(String(255), nullable=False)
    max_length = Column(Integer, nullable=True, default=1800)
    content = Column(Text, nullable=False)
    

# Define the Scene model
class Scene(Base, TimestampMixin):
    __tablename__ = 'scenes'
    
    id = Column(Integer, primary_key=True)
    chunk_id = Column(Integer, ForeignKey('chunks.id'), nullable=False)
    scene_prompt_id = Column(Integer, ForeignKey('scene_prompts.id'), nullable=False)
    aesthetic_id = Column(Integer, ForeignKey('scene_aesthetics.id'), nullable=False)
    title = Column(Text, nullable=False)
    content = Column(Text, nullable=False)

# # Define the ImagePrompt model
# class ImagePrompt(db.Model, TimestampMixin):
#     __tablename__ = 'image_prompts'
    
#     id = db.Column(db.Integer, primary_key=True)
#     scene_id = db.Column(db.Integer, db.ForeignKey('scenes.id'), nullable=False)
#     prompt_content = db.Column(db.Text, nullable=False)
    
#     images = db.relationship('Image', backref='prompt', lazy=True)

# # Define the Image model
# class Image(db.Model, TimestampMixin):
#     __tablename__ = 'images'
    
#     id = db.Column(db.Integer, primary_key=True)
#     prompt_id = db.Column(db.Integer, db.ForeignKey('image_prompts.id'), nullable=False)
#     image_path = db.Column(db.String(255), nullable=False)

