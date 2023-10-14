import asyncio
import os
from pathlib import Path
import re
import time

import openai
import requests

from config import settings
from worker import generate_scene_prompt
from sql_app.schemas import CreateSceneRequest
from sql_app.models import Chunk, ScenePrompt, SceneAesthetic

from config_defaults import scene_prompt_format



openai.api_key = settings.openai_api_key
current_directory = Path(__file__).parent
root_directory = current_directory.parent
images_path = (root_directory / 'static/img/scenes').as_posix()
print(f'images_path={images_path}')

def update_scene_task(task):
    while not task.ready():
        # socketio.emit('task_generate_scene', task.info)
        print(f'update_scene_task State={task.state}, info={task.info}')


class SceneService:    
    @classmethod
    def generate_scene(cls, db, scene_request: CreateSceneRequest):
        scene_prompt = db.query(ScenePrompt).filter(ScenePrompt.id == scene_request.prompt_id).first()
        chunk = db.query(Chunk).filter(Chunk.id == scene_request.chunk_id).first()
        aesthetic = db.query(SceneAesthetic).filter(SceneAesthetic.id == scene_request.aesthetic_id).first()
        print(f'scene_prompt is {scene_prompt}')
        if scene_prompt and chunk and aesthetic:
            print('creating generate_scene task')
            prompt = scene_prompt.content.format(
                book_name=chunk.book.title,
                scene_format=scene_prompt_format,
                chunk=chunk.content,
                max_length=scene_prompt.max_length
            )
            
            task = generate_scene_prompt.delay(
                images_path,
                prompt,
                aesthetic.title
            )
            return task.id, 'Task created'
        else:
            return False, 'Prompt or chunk not found'
        