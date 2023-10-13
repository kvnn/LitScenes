chunk_size = 5000

scene_prompt_format = '{Title} //// {Description}'

scene_prompt_aesthetics = [
        'hyperwave',
        'romantic painting',
        'charcoul illustration',
        '3d illustration',
        'surrealism',
        'psychedelic',
        'oil panting',
        'acrylic painting',
        'pastel panting',
        'pencil drawing',
        'abstract pencil and watercolor'
    ]

chunk_to_scene_prompt_01 = (
    'You were a witness to the following scene from the book "{book_name}".'
    'You are asked to provide a detailed visual description of what you saw to a reknowned artist who will be painting it for the masses.'
    'Please write vividly and with specific visual details.'
    'As much as possible, describe the physical characteristics of the characters and the details of the location, and anything else that'
    'would need to be conveyed to capture what happened in a painting.'
    'Also generate a concise, captivating title. '
    'Please return the content in this format, in less than 1800 characters: {scene_format}'
    'Here is the content from "{book_name}" : {chunk}'
)