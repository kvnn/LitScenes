import base64
import os
import time

from celery import Celery
import openai

from config import settings
from sql_app.crud import create_scene
from sql_app.database import SessionLocal
from sql_app.seed_values import scene_prompt_title_separator


db = SessionLocal()
celery = Celery(__name__)
celery.conf.broker_url = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379")
celery.conf.result_backend = os.environ.get("CELERY_RESULT_BACKEND", "redis://localhost:6379")

openai.api_key = settings.openai_api_key

@celery.task(name="generate_scene_prompt", bind=True)
def generate_scene_prompt(
        self,
        images_path,
        prompt,
        prompt_max_length,
        aesthetic_title,
        aesthetic_id,
        chunk_id
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
                    'content': content,
                    'progress': (len(content) / prompt_max_length) if prompt_max_length else 'unknown'
                }
            )
            print(f'{new}')
    self.update_state(
        state='PROGRESS',
        meta={
            'new': new,
            'content': content,
            'progress': (len(content) / prompt_max_length) if prompt_max_length else 'unknown'
        }
    )
    try:
        title, content = content.split(scene_prompt_title_separator)
    except ValueError as e:
        title = content[:20]
        print(f'[error] ValueError for {prompt[:20]}... with error {e}')

    create_scene(
        db = db,
        title = title,
        content=content,
        aesthetic_id=aesthetic_id,
        chunk_id=chunk_id
    )

    return {
        'new': new,
        'content': content,
        'progress': (len(content) / prompt_max_length) if prompt_max_length else 'unknown'
    }


    # img_prompt_prompt = f'''For the following scene, please provide an effective dall-e prompt (with a max-length of 400 chars),
    #                         with the goal of generating a fitting concept art work: {content}.'''

    # response = openai.ChatCompletion.create(
    #     model="gpt-3.5-turbo",
    #     messages=[{"role": "user", "content": img_prompt_prompt}],
    #     stream=True
    # )
    
    # img_prompt = ''
    # for chunk in response:
    #     new = chunk['choices'][0]['delta'].get('content')
    #     if new:
    #         img_prompt += new
    #         print(f'{new}')
    
    
    # if len(img_prompt) > 1000:
    #     img_prompt = img_prompt[len(img_prompt)-1000:]

    # img_prompt = f'{img_prompt}, {aesthetic_title} style'
    
    # image_response = openai.Image.create(prompt=img_prompt, n=2, size="512x512", response_format='b64_json')

    # b64s = [base64.b64decode(obj['b64_json']) for obj in image_response['data']]
    
    # for idx, b64_img in enumerate(b64s):
    #     img_urls_path = f'{images_path}/{title}-{aesthetic_title}-{idx+1:02d}.png'
    #     with open(img_urls_path, "wb") as img_file:
    #         img_file.write(b64_img)
    
    # print(f'img_prompt={img_prompt}')


    # print('generate_scene_task done')