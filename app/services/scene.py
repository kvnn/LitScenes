import asyncio
import os
from pathlib import Path
from worker import generate_scene_prompt
from sql_app.schemas import CreateSceneRequest
from sql_app.models import Chunk, ScenePrompt, SceneAesthetic

import redis

from config_defaults import scene_prompt_format

redis_url = os.environ.get("REDIS_URL")
redis_client = redis.from_url(redis_url)

current_directory = Path(__file__).parent
root_directory = current_directory.parent
images_path = (root_directory / 'static/img/scenes').as_posix()
print(f'images_path={images_path}')


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
            print(f'scene_prompt.max_length={scene_prompt.max_length}')
            task = generate_scene_prompt.delay(
                images_path,
                prompt,
                scene_prompt.max_length,
                aesthetic.title
            )
            redis_client.set('generate_scene_task_id', task.id)
            return task.id, 'Task created'
        else:
            return False, 'Prompt or chunk not found'
        