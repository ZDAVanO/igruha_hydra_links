import requests
import json
import os


CACHE_DIR = 'cache'
CACHE_FILE = os.path.join(CACHE_DIR, 'translation_cache.json')


def load_cache():
    # Завантажує кеш з файлу, якщо файл існує.
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_cache(cache):
    # Зберігає кеш у файл.
    os.makedirs(CACHE_DIR , exist_ok=True)  # Create the directory if it doesn't exist
    with open(CACHE_FILE, 'w', encoding='utf-8') as f:
        json.dump(cache, f, ensure_ascii=False, indent=4)


def translate_line(text, target_language='en', source_language='auto'):

    # Перевіряємо, чи є текст вже в кеші
    cache = load_cache()
    if text in cache:
        # print(f'(TRANSLATE_TEXT) CACHE HIT FOR "{text}"')
        return cache[text]

    url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl={source_language}&tl={target_language}&dt=t&q={requests.utils.quote(text)}"

    # print(f'(TRANSLATE_TEXT) "{text}"')
    
    try:
        response = requests.get(url)
        response.raise_for_status()  # перевіряємо на помилки
        data = response.json()

        translated_text = ''.join(part[0] for part in data[0])  # об'єднуємо перекладені частини

        cache[text] = translated_text
        save_cache(cache)
        return translated_text

    except requests.exceptions.RequestException as e:
        print(f'Error: {e}')
        return None



