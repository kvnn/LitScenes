import base64
import os
import time

from celery import Celery
import openai
from openai.error import InvalidRequestError
import redis

from config import settings
from sql_app.crud import (
    create_scene,
    create_scene_image,
    create_scene_image_prompt
)
from sql_app.database import SessionLocal
from sql_app.seed_values import scene_prompt_title_separator


db = SessionLocal()

redis_url = os.environ["CELERY_BROKER_URL"]
redis_client = redis.from_url(redis_url)

celery = Celery(__name__)
celery.conf.broker_url = os.environ["CELERY_BROKER_URL"]
celery.conf.result_backend = os.environ["CELERY_RESULT_BACKEND"]

openai.api_key = settings.openai_api_key

@celery.task(name="generate_scene_image", bind=True)
def generate_scene_image(
    self,
    scene_id,
    scene_title,
    scene_content,
    images_path,
    aesthetic_title,
):
    generated_images = []
    img_prompt_prompt = (
        'You are an expert generative-art prompt engineer. For the following scene, please provide a prompt that has a maximum length '
        f'of 900 characters and that will generate a fitting image for the following scene: {scene_content}. It is very important that we avoid'
        'triggering the "safety system" exception (e.g. "Your request was rejected as a result of our safety system").'
        'So if you see a potential for that to be triggered, please take a deep breath and think of a way to communicate'
        'that this is just for a fictional literature project.'
    )
    
    img_prompt_prompt = img_prompt_prompt  # dall-e requires < 1000 chars

    # TODO: we could stream this to the UI
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": img_prompt_prompt}],
        stream=True
    )
    
    img_prompt = ''
    for chunk in response:
        new = chunk['choices'][0]['delta'].get('content')
        if new:
            img_prompt += new
            print(f'{new}')
            meta = {
                'img_prompt': img_prompt
            }
            print(f'''updating state with meta={meta}''')
            self.update_state(
                state='PROGRESS',
                meta=meta
            )

    img_prompt = f'{img_prompt}, {aesthetic_title} style'

    if len(img_prompt) > 1000:
        img_prompt = img_prompt[:999]

    
    new_img_prompt = create_scene_image_prompt(
        db,
        scene_id=scene_id,
        content=img_prompt
    )

    try:
        print(f'img_prompt={img_prompt}')
        
        self.update_state(
            state='PROGRESS',
            meta={'progress':'calling image_response'}
        )

        image_response = openai.Image.create(prompt=img_prompt, n=2, size="512x512", response_format='b64_json')
    except InvalidRequestError as err :
        # TODO: cycle through a new prompt
        print(f'[error] image_response failed for with error {err}')
        return {
            'state': 'FAILED',
            'error': str(err),
            'type': 'scene_image_generate',       
        }

    self.update_state(
        state='PROGRESS',
        meta={'progress':'finished image_response'}
    )

    b64s = [base64.b64decode(obj['b64_json']) for obj in image_response['data']]

    for idx, b64_img in enumerate(b64s):
        img_path = f'{images_path}/{scene_title}-{aesthetic_title}-{idx+1:02d}.png'

        with open(img_path, "wb") as img_file:
            img_file.write(b64_img)

        new_img = create_scene_image(
            db,
            scene_image_prompt_id=new_img_prompt.id,
            image_path=img_path
        )
        generated_images.append({
            'id': new_img.id,
            'scene_image_prompt_id': new_img_prompt.id,
            'image_path': img_path
        })
        meta = {
            'type': 'scene_image_generate',
            'images': generated_images
        }
        print(f'''updating state with meta={meta}''')
        self.update_state(
            state='PROGRESS',
            meta=meta
        )

    meta = {
        'type': 'scene_image_generate',
        'images': generated_images,
        'scene_id': scene_id
    }

    print(f'generate_scene_task done. returning {meta}')

    return meta


@celery.task(name="generate_scene", bind=True)
def generate_scene(
    self,
    images_path,
    prompt,
    prompt_max_length,
    aesthetic_title,
    aesthetic_id,
    chunk_id,
    scene_prompt_id
):
    print(f'generate_scene_task for {prompt}')

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        stream=True
    )
    content = ''
    for chunk in response:
        new = chunk['choices'][0]['delta'].get('content')
        if new:
            content += new
            self.update_state(
                state='PROGRESS',
                meta={
                    'new': new,
                    'type': 'scene_generate',
                    'content': content,
                    'progress': (len(content) / prompt_max_length) if prompt_max_length else 'unknown'
                }
            )
            print(f'{new}')

    self.update_state(
        state='PROGRESS',
        meta={
            'new': new,
            'type': 'scene_generate',
            'content': content,
            'progress': (len(content) / prompt_max_length) if prompt_max_length else 'unknown'
        }
    )
    
    print(f'[generate_scene] content={content}')
    try:
        title, content = content.split(scene_prompt_title_separator)
    except ValueError as e:
        title = content[:20]
        print(f'[error] ValueError for {prompt[:20]}... with error {e}')
    
    title = title[:20]  # just in case it's too long

    new_scene = create_scene(
        db = db,
        title = title,
        content=content,
        aesthetic_id=aesthetic_id,
        chunk_id=chunk_id,
        scene_prompt_id=scene_prompt_id
    )

    scene_image_task = generate_scene_image.delay(
        scene_id=new_scene.id,
        scene_title=title,
        scene_content=content,
        images_path=images_path,
        aesthetic_title=aesthetic_title,
    )
    scene_image_task_id = scene_image_task.id
    print(f'called scene_image_task, scene_image_task.id={scene_image_task_id}')
    redis_client.set(scene_image_task_id, 'init')
    
    return {
        'scene_id': new_scene.id,
        'scene_image_task_id': scene_image_task_id,
        'new': new,
        'type': 'scene_generate',
        'content': content,
        'progress': (len(content) / prompt_max_length) if prompt_max_length else 'unknown'
    }

