from pydantic import BaseModel


class BookCreate(BaseModel):
    gutenburg_id: int
    gutenburg_url: str

    title: str
    author: str

class Book(BookCreate):
    id: int
    status: str


class GutenburgBookUrl(BaseModel):
    book_url: str

class ChunkCreate(BaseModel):
    book_id: int
    sequence_number: int
    content: str

class Chunk(ChunkCreate):
    id: int
