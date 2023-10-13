import asyncio
import os
from pathlib import Path
import re
import time

from celery import shared_task
from dotenv import load_dotenv
import openai
import requests

from sql_app.models import db, Book, Chunk, ScenePrompt, SceneAesthetic

from config_defaults import scene_prompt_format


load_dotenv()


openai.api_key = os.getenv("OPENAI_API_KEY")

@shared_task(bind=True)
def generate_scene_task(self, prompt, aesthetic):
    print(f'generate_scene_task for {prompt}')
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        stream=True
    )
    content = ''
    for chunk in response:
        print(f'chunk: {chunk}')
        new = chunk['choices'][0]['delta'].get('content')
        if new:
            self.update_state(
                state='PROGRESS',
                meta={'content': content + new})
            print(f'content: {content}')

    # img_prompt = response
    # img_prompt_styling = f'with a deep, authentic {aesthetic} style'
    # img_prompt = f'{img_prompt}, {img_prompt_styling}'
    
    # print(f'img_prompt is {img_prompt}')
    
    return content


def update_scene_task(task):
    while not task.ready():
        # socketio.emit('task_generate_scene', task.info)
        print(f'update_scene_task State={task.state}, info={task.info}')


class SceneService:
    
    @classmethod
    def generate_scene(cls, chunk_id, prompt_id, aesthetic_id):
        prompt = db.session.execute(db.select(ScenePrompt).where(ScenePrompt.id == prompt_id)).scalar()
        chunk = db.session.execute(db.select(Chunk).where(Chunk.id == chunk_id)).scalar()
        aesthetic = db.session.execute(db.select(SceneAesthetic).where(SceneAesthetic.id == aesthetic_id)).scalar()
        print(f'prompt is {prompt}')
        if prompt and chunk:
            print('creating generate_scene task')
            query = prompt.content.format(
                book_name=chunk.book.title,
                scene_format=scene_prompt_format,
                chunk=chunk.content
            )
            # loop = asyncio.get_event_loop()
            # Run the track_celery_task function in the event loop
            task = generate_scene_task.delay(query, aesthetic.title)
            update_scene_task(task)
            # loop.run_until_complete(update_scene_task(task))
            return task.id, 'Task created'
        else:
            return False, 'Prompt or chunk not found'
        