import asyncio
import os
from pathlib import Path
from worker import generate_scene

import redis

from sql_app.models import Chunk, ScenePrompt, SceneAesthetic
from sql_app.schemas import CreateSceneRequest
from sql_app.seed_values import scene_prompt_format

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
            task = generate_scene.delay(
                images_path=images_path,
                prompt=prompt,
                prompt_max_length=scene_prompt.max_length,
                aesthetic_title=aesthetic.title,
                aesthetic_id=aesthetic.id,
                chunk_id=chunk.id,
                scene_prompt_id=scene_prompt.id
            )
            # TODO: remove. Should be no need.
            redis_client.set(task.id, 'init')
            return task.id, 'Task created'
        else:
            return False, 'Prompt or chunk not found'
        