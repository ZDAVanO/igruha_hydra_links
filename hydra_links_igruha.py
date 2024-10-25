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

no_date_in_torrent = 0

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
            no_date_in_torrent += 1

        # return magnet_link, formatted_date
        return magnet_link, formatted_date, total_length

    except:
        # У випадку будь-якої помилки повертаємо None
        print('DEAD_TORRENT')
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

        download_page_link = None
        if (torrent['href'] != '/top-online.html'):
            page_response_2 = requests.get(torrent['href'])
            soup_2 = BeautifulSoup(page_response_2.text, 'html.parser')

            download_page_link = soup_2.find('a', class_='torrent2')


        # Шукаємо ul з id 'navbartor' всередині батьківських елементів
        navbartor = torrent.find_parent('ul', id='navbartor')
        if navbartor:

            # Шукаємо найближчий попередній елемент <center>
            center_tag = navbartor.find_previous('center')
            if center_tag:

                # Витягуємо текст з <span> всередині <center>
                size_and_info = center_tag.find('span', style="font-size:14pt;")

                if size_and_info and download_page_link:

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
                        magnet_link, torrent_date, torrent_size = make_magnet_from_bytes(torrent_bytes.getvalue())

                    except requests.RequestException as e:
                        print(f"Не вдалося завантажити {torrent_url}: {e}")
                        magnet_link, torrent_date, torrent_size = None, None, None  # Встановлюємо значення None, якщо не вдалося завантажити

                    if magnet_link:
                        # Додаємо інформацію про торрент до списку
                        torrent_info_list.append({
                            'info': name_details,  # Текст розміру
                            'size': site_size,  # Текст розміру     
                            'date': torrent_date,  # Дата створення
                            'magnet_link': magnet_link  # Магнет-посилання
                        })

    return torrent_info_list















def extract_info_from_page(soup):

    # Витягування дати та часу
    site_update_date = None
    article_info = soup.find('div', {'id': 'article-film-full-info'})
    if article_info:
        time_element = article_info.find('time', {'class': 'published'})
        if time_element:

            # site_update_date = time_element.text

            parsed_date = datetime.strptime(time_element.text, "%d.%m.%Y, %H:%M")
            iso_format_date = parsed_date.strftime("%Y-%m-%dT%H:%M:%SZ")
            site_update_date = iso_format_date
    
    # Витягування назви
    site_game_title = None
    module_title_div = soup.find('div', class_='module-title')
    if module_title_div:
        h1_tag = module_title_div.find('h1')
        if h1_tag:
            site_game_title = h1_tag.text.strip()

    return site_update_date, site_game_title
















# Завантаження та парсинг XML
sitemap_url = 'https://itorrents-igruha.org/sitemap.xml'
response = requests.get(sitemap_url)
sitemap_content = response.content

# Парсинг XML для витягнення всіх URL
root = ET.fromstring(sitemap_content)
namespaces = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}

urls = [elem.text for elem in root.findall('.//ns:loc', namespaces)]
# urls = urls[4000:4010]
print(f"\nTotal URLs: {len(urls)}")


# Структура для збереження даних
data = {
    "name": "Torrents-Igruha",
    "downloads": []
}

no_download_options = 0

# Пройдемо по кожному URL та дістанемо дані
for index, url in enumerate(urls, start=1):

    page_response = requests.get(url)
    soup = BeautifulSoup(page_response.text, 'html.parser')

    site_update_date, site_game_name = extract_info_from_page(soup)

    if not site_update_date or not site_game_name:
        print(f'{index}. INVALID PAGE: {url}')  
    else:
        print(f'{index}. {site_game_name} / {site_update_date} / {url}')
        download_options = get_download_options(soup)

        if (not download_options):
            print("    No download options")
            no_download_options += 1
        else:
            for download_option in download_options:

                title = f"{site_game_name} {download_option['info']}"

                if (download_option['date']):
                    uploadDate = download_option['date']
                else:
                    uploadDate = site_update_date
                
                print(f'    {title} / {uploadDate} / {download_option['size']}')

                download_info = {
                    "title": title,  # Назва файлу, припустимо, остання частина URL
                    "uris": [download_option['magnet_link']],
                    "uploadDate": uploadDate,
                    "fileSize": download_option['size'],  # Тут можна додати функцію для витягнення розміру файлу
                }
                data["downloads"].append(download_info)


print(f"\nTotal URLs: {len(urls)}")
print(f"Total Invalid Pages: {len(urls) - len(data['downloads'])}")
print(f"Total Pages with no download options: {no_download_options}")
print(f"Total Torrents with no date: {no_date_in_torrent}")



json_dir = 'json'
os.makedirs(json_dir, exist_ok=True)  # Create the directory if it doesn't exist

current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
filename = f'downloads_{current_time}.json'

file_path = os.path.join(json_dir, filename)

# Збереження у JSON файл
with open(file_path, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=4)  
print()
print(f"The data is saved in file {file_path}")





# url = "https://itorrents-igruha.org/8095-believe.html"
# page_response = requests.get(url)
# soup = BeautifulSoup(page_response.text, 'html.parser')
# torrent_data = get_download_options(soup)

# for data in torrent_data:
#     # print(f"Download Torrent page: {data['link']}")
#     print(f"Info: {data['info']}")
#     print(f"size: {data['size']}")
#     print(f"Date: {data['date']}")
#     # print(f"Torrent Link: {data['torrent_link']}")
#     print(f"Magnet Link: {data['magnet_link']}\n")