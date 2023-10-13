import asyncio
import os
from pathlib import Path
import re
import time

from celery import shared_task
from fastapi import Depends
import requests

from sql_app.database import get_db
from sql_app.models import Book, Chunk
from sql_app.crud import create_book, create_chunk, get_book_by_gutenburg_id
from sql_app.schemas import BookCreate, ChunkCreate

from utils import (
    gutenburg_txt_file_url_pattern,
    get_id_from_gutenburg_url,
    get_title_and_author_from_gutenburg_url,
    gutenburg_start_marker,
    gutenburg_end_marker,
    chunk_text
)


class BookService:
    
    @classmethod
    async def import_from_gutenburg_url(cls, db, url):
        book = None
        status = 'Unknown'
        # Check if the URL matches the Project Gutenberg text file URL pattern
        if re.match(gutenburg_txt_file_url_pattern, url):
            # Check if the book has already been imported
            gutenburg_id = get_id_from_gutenburg_url(url)
            book = get_book_by_gutenburg_id(db, gutenburg_id)

            if book:
                return None, 'This book has already been imported'
            else:
                # Download the book
                response = requests.get(url)
                if response.status_code == 200:
                    try:
                        title, author = get_title_and_author_from_gutenburg_url(response.text[:1000])
                        book = create_book(db=db, book=BookCreate(
                            gutenburg_id=gutenburg_id,
                            gutenburg_url=url,
                            title=title,
                            author=author
                        ))
                        start_index = response.text.find(gutenburg_start_marker)
                        start_index = 0 if start_index == -1 else start_index
                        end_index = response.text.find(gutenburg_end_marker)
                        end_index = None if end_index == -1 else end_index
                        extracted_text = response.text[start_index + len(gutenburg_start_marker):end_index].strip()
                        chunks = chunk_text(extracted_text)
                        for idx, chunk in enumerate(chunks):
                            create_chunk(db=db, chunk=ChunkCreate(
                                book_id=book.id,
                                content=chunk,
                                sequence_number=idx+1
                            ))
                        status = 'success'
                    except Exception as err:
                        status = f'Failed to import the book. Error: {err}'
                else:
                    status = f'Failed to download the file. HTTP Status Code: {response.status_code}'
        else:
            status = 'Invalid URL'
        
        print(f'status={status}')

        print(f'returning book.')
        return book, status
        