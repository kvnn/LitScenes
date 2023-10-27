import re

from config import settings


gutenburg_txt_file_url_pattern = r'^https?://www\.gutenberg\.org/.*\.txt$'
gutenburg_txt_file_id_pattern = r'/(\d+)/'
gutenburg_txt_file_title_pattern = r"Title: ([^\r\n]+)"
gutenburg_txt_file_author_pattern = r"Author: ([^\r\n]+)"
gutenburg_start_marker = "START OF THE PROJECT GUTENBERG EBOOK"
gutenburg_end_marker = "END OF THE PROJECT GUTENBERG EBOOK"

def get_id_from_gutenburg_url(url):
    match = re.search(gutenburg_txt_file_id_pattern, url)
    return match.group(1)

def get_title_and_author_from_gutenburg_url(text):    
    # This assumes a standard Project Gutenberg header format
    author = 'unknown'
    title = re.search(gutenburg_txt_file_title_pattern, text).group(1)
    author_match = re.search(gutenburg_txt_file_author_pattern, text)
    if author_match:
        author = author_match.group(1)
    return title, author


def chunk_text(text, char_limit=5000):
    chunks = []
    start = 0

    while start < len(text):
        # If remaining text is less than the limit, chunk the rest of the text
        if len(text) - start <= char_limit:
            chunks.append(text[start:].strip())
            break
        
        # Find the last sentence or paragraph end within the char_limit
        end = start + char_limit
        while end > start:
            if text[end] in [".", "!", "?"] or (end < len(text) - 1 and text[end:end+2] == "\n\n"):
                break
            end -= 1

        # If no suitable end found, revert to last space or newline
        if end == start:
            end = start + char_limit
            while end > start and text[end] not in [" ", "\n"]:
                end -= 1

        # Add the chunk after stripping leading and trailing whitespace
        chunks.append(text[start:end+1].strip())
        start = end + 1

    return chunks


def get_scene_image_url(filename):
    if settings.in_cloud:
        # TODO: pull from a config setting
        return f"https://{settings.s3_bucket_name_media}.s3.amazonaws.com/{filename}"
    else:
        # TODO: /static/img/scenes should be pulled from a config
        return f'/static/img/scenes/{filename}'