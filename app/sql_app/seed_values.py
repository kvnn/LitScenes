chunk_size = 5000

scene_prompt_title_separator = '////'
scene_prompt_format = '{Title} {scene_prompt_separator} {Description}'

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

chunk_to_scene_prompt_01 = {
    "title": 'An omnipresent witness',
    "max_length": 1800,
    "content": (
        'Take the following narrative and imagine yourself as an omnipresent witness to its unfolding. '
        'Believing that it shoudl not be lost to history, you want to reiterate the narrative to allow great '
        'works of art to be created from it. '
        'Please write vividly and with specific visual details. '
        'As much as possible, describe the physical characteristics of the characters and the details of the location, and anything else that '
        'would need to be conveyed to capture what happened in a visual representation. '
        'Also generate a concise, captivating title. '
        'Please return the content in this format, in less than {max_length} characters: {scene_format} '
        'Remember, it needs to be concise, so you need to summarize the important parts of the narrative and keep it to a maximum of {max_length} letters. '
        'Here is the content: {chunk}.'
    )
}