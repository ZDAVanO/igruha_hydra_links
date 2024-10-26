import requests
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
import json
from datetime import datetime
import os

from io import BytesIO
import re

import bencodepy
import hashlib
import base64
from urllib.parse import quote  # Import the quote function for URL encoding

from translator import translate_text

import logging

import time

logging.basicConfig(filename='parser.log', 
                    level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    filemode='w')

# Форматує розмір у байтах у зручний формат (MB або GB).
def format_size(size_in_bytes):
    if size_in_bytes >= 2**30:  # Якщо розмір більший за 1 ГБ
        size_in_gb = size_in_bytes / (2**30)  # Перетворюємо у Гігабайти
        return f"{size_in_gb:.2f} GB"
    elif size_in_bytes >= 2**20:  # Якщо розмір більший за 1 МБ
        size_in_mb = size_in_bytes / (2**20)  # Перетворюємо у Мегабайти
        return f"{size_in_mb:.2f} MB"
    else:
        return f"{size_in_bytes} bytes"  # Якщо менше 1 МБ


def make_magnet_from_bytes(torrent_bytes):
    try:
        # Декодування метаданих без збереження у файл
        metadata = bencodepy.decode(torrent_bytes)
        subj = metadata[b'info']
        hashcontents = bencodepy.encode(subj)
        digest = hashlib.sha1(hashcontents).digest()
        b32hash = base64.b32encode(digest).decode()
        
        # Отримання назви та кодування її в URL
        name = quote(metadata[b'info'][b'name'].decode())  # URL encode the name

        # Ініціалізація довжини
        total_length = 0
        
        # Перевірка наявності 'length' (один файл)
        if b'length' in metadata[b'info']:
            total_length = metadata[b'info'][b'length']
        # Обробка багатофайлового торренту
        elif b'files' in metadata[b'info']:
            total_length = sum(file[b'length'] for file in metadata[b'info'][b'files'])
        
        # Створення магнет-посилання
        magnet_link = f'magnet:?xt=urn:btih:{b32hash}&dn={name}'
        
        # Додавання URL для анонсу
        if b'announce' in metadata:
            # print(metadata[b'announce'])
            # magnet_link += f'&tr={metadata[b'announce'].decode()}'

            announce_list = metadata.get(b'announce', [])
            
            if isinstance(announce_list, bytes):
                magnet_link += f'&tr={announce_list.decode()}'
            elif isinstance(announce_list, list) and announce_list:
                magnet_link += f'&tr={announce_list[0].decode()}'
        # else:
        #     print('Announce Not Available in Torrent File')

        # Додавання загальної довжини
        magnet_link += f'&xl={total_length}'
        
        formatted_date = None

        # Виведення дати створення торрент-файлу, якщо вона є
        if b'creation date' in metadata:
            creation_date = metadata[b'creation date']
            formatted_date = datetime.fromtimestamp(creation_date).strftime('%Y-%m-%dT%H:%M:%SZ')
        else:
            print('Date Not Available in Torrent File')

        # return magnet_link, formatted_date
        return magnet_link, formatted_date, total_length

    except Exception as e:
        # У випадку будь-якої помилки повертаємо None
        print('DEAD_TORRENT')
        logging.error(f'DEAD_TORRENT: {e}')
        return None, None, None






def extract_size_and_info(size_text):
    # Шаблон для регулярного виразу
    pattern = r'Размер:\s*([\d.,]+\s*(?:GB|MB|ГБ|МБ|Gb|Mb|Гб|Мб|gb|mb|гб|мб|МВ|МB|Mб))\s*(.*?)(?:\s*\|)?\s*$'
    match = re.search(pattern, size_text)
    
    if match:
        size = match.group(1)  # Витягуємо розмір
        info = match.group(2).strip()  # Витягуємо інформацію
        return size, info
    else:
        return "N/A", "NO_INFO"  # Якщо не знайдено відповідності


def get_download_options(soup):

    # Список для збереження результатів
    torrent_info_list = []

    # Шукаємо всі посилання з класом 'torrent'
    torrent_links = soup.find_all('a', class_='torrent')

    for torrent in torrent_links:

        # Продовжити до наступної ітерації, якщо посилання веде на '/top-online.html'
        if torrent['href'] == '/top-online.html':
            continue
        
        try:
            # Отримуємо сторінку завантаження
            page_response_2 = requests.get(torrent['href'])
            page_response_2.raise_for_status()
            soup_2 = BeautifulSoup(page_response_2.text, 'html.parser')
            download_page_link = soup_2.find('a', class_='torrent2')



            # Шукаємо ul з id 'navbartor' всередині батьківських елементів
            navbartor = torrent.find_parent('ul', id='navbartor')
            if not navbartor:
                continue  # Продовжити, якщо 'navbartor' не знайдено

            # Шукаємо найближчий попередній елемент <center>
            center_tag = navbartor.find_previous('center')
            if not center_tag:
                continue  # Продовжити, якщо <center> не знайдено

            # Витягуємо текст з <span> всередині <center>
            size_and_info = center_tag.find('span', style="font-size:14pt;")
            if not size_and_info or not download_page_link:
                continue  # Продовжити, якщо немає потрібних елементів



            site_size, name_details = extract_size_and_info(size_and_info.get_text(strip=True))

            # Завантаження торрент файлу
            torrent_url = download_page_link['href']
            try:
                # Отримання контенту файлу
                response = requests.get(torrent_url)
                response.raise_for_status()  # Перевірка на помилки завантаження

                # Використання BytesIO для зберігання в пам'яті
                torrent_bytes = BytesIO(response.content)

                # Отримання магнет-посилання
                # magnet_link, t_size, t_date = make_magnet_from_bytes(torrent_bytes.getvalue())
                magnet_link, torrent_date, torrent_size_bytes = make_magnet_from_bytes(torrent_bytes.getvalue())

            except requests.RequestException as e:
                print(f"Failed to download {torrent_url}: {e}")
                logging.error(f"Failed to download {torrent_url}: {e}")
                magnet_link, torrent_date, torrent_size_bytes = None, None, None  # Встановлюємо значення None, якщо не вдалося завантажити

            if magnet_link:
                # Додаємо інформацію про торрент до списку
                torrent_info_list.append({
                    'info': name_details,  # Текст розміру
                    'fileSize': site_size,  # Текст розміру     
                    'date': torrent_date,  # Дата створення
                    'magnet_link': magnet_link  # Магнет-посилання
                })

        except Exception as e:
            print(f"Failed to process {torrent['href']}: {e}")
            logging.error(f"Failed to process {torrent['href']}: {e}")

    return torrent_info_list




def convert_to_iso_format(date_str, date_format="%d.%m.%Y, %H:%M"):
    parsed_date = datetime.strptime(date_str, date_format)
    return parsed_date.strftime("%Y-%m-%dT%H:%M:%SZ")

def extract_info_from_page(soup):

    # Витягування дати та часу
    site_update_date = None
    article_info = soup.find('div', {'id': 'article-film-full-info'})
    if article_info:
        time_element = article_info.find('time', {'class': 'published'})
        if time_element:

            site_update_date = time_element.text

            # parsed_date = datetime.strptime(time_element.text, "%d.%m.%Y, %H:%M")
            # iso_format_date = parsed_date.strftime("%Y-%m-%dT%H:%M:%SZ")
            # site_update_date = iso_format_date
    
    # Витягування назви
    site_game_title = None
    module_title_div = soup.find('div', class_='module-title')
    if module_title_div:
        h1_tag = module_title_div.find('h1')
        if h1_tag:
            site_game_title = h1_tag.text.strip()

    return site_update_date, site_game_title






















# ----------------------------------------------------------------------------------------

# Завантаження та парсинг XML
sitemap_url = 'https://itorrents-igruha.org/sitemap.xml'

try:
    response = requests.get(sitemap_url)
    response.raise_for_status()  # Перевірка статусу відповіді, кине помилку, якщо статус не 200
    sitemap_content = response.content
except requests.exceptions.RequestException as e:
    print(f"Error connecting to {sitemap_url}: {e}")
    logging.error(f"Error connecting to {sitemap_url}: {e}")
    exit(1)  # Завершення програми з кодом 1 для позначення помилки



# Парсинг XML для витягнення всіх URL
root = ET.fromstring(sitemap_content)
namespaces = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}

urls = [elem.text for elem in root.findall('.//ns:loc', namespaces)]

urls = urls[:100] # 200 перших URL для тестування

# problem_urls = [
#     "https://itorrents-igruha.org/8095-believe.html", # DEAD_TORRENT
#     "https://itorrents-igruha.org/14496-sailing-era.html",
#     "https://itorrents-igruha.org/3671-1-126821717.html",
#     "https://itorrents-igruha.org/11642-8-99980.html",
#     "https://itorrents-igruha.org/7793-muse-dash.html",
#     "https://itorrents-igruha.org/15285-metaphor-refantazio.html",
#     "https://itorrents-igruha.org/2576-witchfire.html",
#     "https://itorrents-igruha.org/3821-126821717.html",
#     "https://itorrents-igruha.org/16170-windblown.html"

# ]
# urls = problem_urls

print(f"Total URLs: {len(urls)}\n")
logging.info(f"Total URLs: {len(urls)}")

# Структура для збереження даних
data = {
    "name": "Torrents-Igruha",
    "downloads": []
}

# Статистика
updated_games_stats = 0
download_options_stats = 0
no_download_options_stats  = 0
invalid_pages_stats = 0

error_connecting_stats = 0


# Ініціалізація кешу з файлу, якщо він існує
CACHE_DIR = 'cache'
CACHE_FILE = os.path.join(CACHE_DIR, 'parser_cache.json')

# Create the cache directory if it doesn't exist
if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)

if os.path.exists(CACHE_FILE):
    with open(CACHE_FILE, 'r', encoding='utf-8') as file:
        cache = json.load(file)
else:
    cache = {}



# Запускаємо таймер
start_time = time.time()

# Пройдемо по кожному URL та дістанемо дані
for index, url in enumerate(urls, start=1):

    try:
        page_response = requests.get(url)
        page_response.raise_for_status()  # викликає помилку, якщо статус не 200
    except requests.exceptions.RequestException as e:
        print(f'{index}. Error connecting to {url}: {e}')
        logging.error(f'{index}. Error connecting to {url}: {e}')
        error_connecting_stats += 1
        continue



    soup = BeautifulSoup(page_response.text, 'html.parser')

    site_update_date, site_game_name = extract_info_from_page(soup)


    # Якщо сторінка не з грою, пропускаємо
    if not site_update_date or not site_game_name:

        invalid_page_log = f'{index}. INVALID PAGE: {url}'
        print(invalid_page_log)
        logging.warning(invalid_page_log)

        invalid_pages_stats += 1
        continue


    cache_entry = cache.get(url)
    if cache_entry and cache_entry['site_update_date'] == site_update_date:
        # Якщо дані актуальні, беремо з кешу
        cache_game_page_log = f'{index}. (CACHE) {cache_entry["site_game_name"]} / {cache_entry["site_update_date"]} / {url}'
        print(cache_game_page_log)
        logging.info(cache_game_page_log)

        for cached_download in cache_entry["download_options"]:

            cache_dn_option_log = f'    {cached_download["title"]} / {cached_download["uploadDate"]} / {cached_download["fileSize"]}'
            print(cache_dn_option_log)
            logging.info(cache_dn_option_log)

            data["downloads"].append(cached_download)
            download_options_stats += 1
        continue


    game_page_log = f'{index}. {site_game_name} / {site_update_date} / {url}'
    print(game_page_log)
    logging.info(game_page_log)


    download_options = get_download_options(soup)
    # Якщо немає варіантів завантаження, пропускаємо
    if (not download_options):
        print("    No download options")
        logging.info("    No download options")
        no_download_options_stats += 1
        continue

    # якщо дані не збережені у кеші, та є опції завантаження
    updated_games_stats += 1

    # translated_name = translate_text(site_game_name, target_language='en', source_language='auto')
    translated_name = translate_text(site_game_name, target_language='en', source_language='ru')

    # Новий запис у кеші
    cache_entry = {
        "site_update_date": site_update_date,
        "site_game_name": site_game_name,
        "download_options": []
    }
    
    for download_option in download_options:

        # title = f"{site_game_name} {download_option['info']}"
        title = f"{translated_name} {download_option['info']}"

        if (download_option['date']):
            uploadDate = download_option['date']
        else:
            uploadDate = convert_to_iso_format(site_update_date)
        

        dn_option_log = f'    {title} / {uploadDate} / {download_option["fileSize"]}'
        print(dn_option_log)
        logging.info(dn_option_log)


        download_info = {
            "title": title,  # Назва файлу, припустимо, остання частина URL
            "uris": [download_option['magnet_link']],
            "uploadDate": uploadDate,
            "fileSize": download_option['fileSize'],  # Тут можна додати функцію для витягнення розміру файлу
        }

        data["downloads"].append(download_info)
        cache_entry["download_options"].append(download_info)
        download_options_stats += 1

    # Оновлюємо кеш із новими даними для поточного URL
    cache[url] = cache_entry


print()

# Закінчуємо таймер
end_time = time.time()
execution_time = end_time - start_time

execution_time_log = f'Execution time: {execution_time:.2f} seconds'
print(execution_time_log)
logging.info(execution_time_log)




# Збереження кешу у файл після виконання скрипту
with open(CACHE_FILE, 'w', encoding='utf-8') as file:
    json.dump(cache, file, ensure_ascii=False, indent=4)



# Виведення загальної статистики
# Функція для виведення статистики та логування
def print_and_log(stat_name, stat_value):
    output = f"{stat_name}: {stat_value}"
    print(output)
    logging.info(output)
# Зберігаємо статистику в словнику
stats = {
    "Total Updated Games": updated_games_stats,
    "Total Download Options": download_options_stats,
    "Total Pages with no download options": no_download_options_stats,
    "Total Invalid Pages": invalid_pages_stats,
    "Total Error Connecting": error_connecting_stats,
}
# Виводимо статистику
for stat_name, stat_value in stats.items():
    print_and_log(stat_name, stat_value)




file_path = 'hydra_links_igruha.json'
# Збереження у JSON файл
with open(file_path, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=4)  
print(f"\nThe data is saved in file {file_path}")
logging.info(f"The data is saved in file {file_path}")




backup_dir  = 'json'
os.makedirs(backup_dir , exist_ok=True)  # Create the directory if it doesn't exist

current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
backup_filename  = f'backup_{current_time}.json'
backup_file_path  = os.path.join(backup_dir , backup_filename)

# Збереження копії у JSON файл
with open(backup_file_path, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=4)
print(f"The backup data is saved in file {backup_file_path}")
logging.info(f"The backup data is saved in file {backup_file_path}")


# ########################################################################################

# url = "https://itorrents-igruha.org/14496-sailing-era.html"
# #     "https://itorrents-igruha.org/14496-sailing-era.html"

# page_response = requests.get(url)
# soup = BeautifulSoup(page_response.text, 'html.parser')
# torrent_data = get_download_options(soup)

# for data in torrent_data:
#     # print(f"Download Torrent page: {data['link']}")
#     print(f"Info: {data['info']}")
#     print(f"size: {data['fileSize']}")
#     print(f"Date: {data['date']}")
#     # print(f"Torrent Link: {data['torrent_link']}")
#     print(f"Magnet Link: {data['magnet_link']}\n")