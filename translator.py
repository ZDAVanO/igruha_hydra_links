import requests
import re
import json
import os

import unicodedata


# Ім'я файлу для збереження кешу
# CACHE_FILE = 'translation_cache.json'

CACHE_DIR = 'cache'
CACHE_FILE = os.path.join(CACHE_DIR, 'translation_cache.json')





def load_cache():
    # """Завантажує кеш з файлу, якщо файл існує."""
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_cache(cache):
    # """Зберігає кеш у файл."""
    with open(CACHE_FILE, 'w', encoding='utf-8') as f:
        json.dump(cache, f, ensure_ascii=False, indent=4)


def translate_line(text, target_language='en', source_language='auto', cache={}):

    # Перевіряємо, чи є текст вже в кеші
    if text in cache:
        print(f'(TRANSLATE_TEXT) CACHE HIT FOR "{text}"')
        return cache[text]

    url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl={source_language}&tl={target_language}&dt=t&q={requests.utils.quote(text)}"

    print(f'(TRANSLATE_TEXT) "{text}"')
    
    try:
        response = requests.get(url)
        response.raise_for_status()  # перевіряємо на помилки
        data = response.json()

        translated_text = ''.join(part[0] for part in data[0])  # об'єднуємо перекладені частини

        cache[text] = translated_text
        return translated_text

    except requests.exceptions.RequestException as e:
        print(f'Error: {e}')
        return None






latin_pattern = re.compile(r'[A-Za-z]')
cyrillic_pattern = re.compile(r'[А-Яа-яЁё]')

# Патерн кириличних символів, які схожі на латинські
cyrillic_lookalikes = {
    'А': 'A', 'В': 'B', 'Е': 'E', 'К': 'K', 'М': 'M', 'Н': 'H', 'О': 'O', 'Р': 'P', 'С': 'C', 'Т': 'T', 'У': 'Y', 'Х': 'X',
    'а': 'a', 'в': 'b', 'е': 'e', 'к': 'k', 'м': 'm', 'н': 'h', 'о': 'o', 'р': 'p', 'с': 'c', 'т': 't', 'у': 'y', 'х': 'x'
}

# Функція заміни лише тих кириличних символів, які виглядають як англійські
def replace_specific_cyrillic_lookalikes(text):
    if latin_pattern.search(text) and cyrillic_pattern.search(text):
        return ''.join(cyrillic_lookalikes.get(char, char) for char in text)
    return text


def translate_text(text, target_language='en', source_language='auto'):

    
    # Завантажуємо кеш з файлу
    cache = load_cache()
    
    # Регулярний вираз для перевірки неанглійських букв
    non_english_pattern = re.compile(r'[^\x00-\x7F]')

    text = text.replace("’", "'")
    # text = text.replace("–", "-")
    # text_cleaned = replace_specific_cyrillic_lookalikes(text)
    
    # Перевіряємо, чи рядок містить неанглійські букви
    if non_english_pattern.search(text):

        translated_text = translate_line(text , target_language, source_language, cache=cache)
        result = translated_text
        # result = replace_specific_cyrillic_lookalikes(translated_text)
    else:
        # print(f'ALREADY IN ENGLISH ({text})')
        result = text 

    # Зберігаємо кеш у файл
    save_cache(cache)

    return result



# texts_to_translate = [
#     "ок",
#     "ok",
#     "Caribbеan Legend",
#     "SILENT HILL 2 REMAKE",
#     "Привіт, як справи?",
#     "Це тестове речення.",
#     "Python — чудова мова програмування.",
#     "Давай перекладемо це на англійську.",
#     "Сьогодні гарна погода.",
#     "Я люблю читати книги.",
#     "Цей фільм дуже цікавий.",
#     "Київ — столиця України.",
#     "Мені подобається слухати музику.",
#     "Технології швидко розвиваються.",
#     "What is your name?",
#     "I enjoy hiking in the mountains.",
#     "This is a beautiful painting.",
#     "Can you help me with this problem?",
#     "The weather is nice today.",
#     "Learning new languages is fun.",
#     "He is an excellent cook.",
#     "I have visited many countries.",
#     "She loves to dance.",
#     "The movie was fantastic!",
#     "What time is the meeting?",
#     "Let's grab lunch together.",
#     "I am working on a new project.",
#     "The cat is sleeping on the sofa.",
#     "My favorite season is autumn.",
#     "Do you like to travel?",
#     "We should watch a movie tonight.",
#     "The food in this restaurant is delicious.",
#     "He plays the guitar very well.",
#     "What are your plans for the weekend?",
#     "Я хочу подорожувати світом.",
#     "Це мій улюблений фільм.",
#     "Ми зустрінемось о п'ятій.",
#     "Вона вчиться в університеті.",
#     "Ця книга дуже пізнавальна.",
#     "Я граю в футбол щонеділі.",
#     "Where is the nearest train station?",
#     "I prefer tea over coffee.",
#     "Have you seen my keys?",
#     "They are going to the concert tomorrow.",
#     "Can you recommend a good restaurant?",
#     "What are you doing later?",
#     "Скільки часу займе поїздка?",
#     "У мене є питання до вас.",
#     "Цей продукт дуже популярний.",
#     "I want to learn how to cook.",
#     "We need to finish this project by Friday.",
#     "The view from the mountain is breathtaking.",
#     "Моя сім'я живе в Харкові.",
#     "I like to go for a walk in the park.",
#     "What time does the train arrive?",
#     "Це чудова можливість для навчання.",
#     "I have a meeting at 3 PM.",
#     "Чи можеш ти відправити мені електронного листа?",
#     "She is a talented artist.",
#     "What is your favorite book?",
#     "Я навчаюся в онлайн-університеті.",
#     "The sunset was stunning.",
#     "Do you play any musical instruments?",
#     "Цей ресторан славиться своєю кухнею.",
#     "I would like a glass of water, please.",
#     "What kind of movies do you like?",
#     "Вона подорожує по Європі цього літа.",
#     "I think it's going to rain today.",
#     "Цей комп'ютер дуже швидкий.",
#     "Can you show me how to do this?",
#     "Я відвідую курси з програмування.",
#     "What is your favorite hobby?",
#     "У вас є домашні тварини?",
#     "I have a dentist appointment tomorrow.",
#     "Цей фестиваль проходить кожного року.",
#     "What is your favorite type of music?",
#     "У мене є кілька друзів за кордоном.",
#     "У мене є кілька друзів за кордоном."
# ]



# for text in texts_to_translate:
#     print(f'Original: {text} | Translated: {translate_text(text)}')

