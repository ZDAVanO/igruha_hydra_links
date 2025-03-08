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

from utils.translator import translate_line
from utils.format_utils import date_to_iso, format_size

import logging

from tqdm import tqdm


import cloudscraper

class IgruhaParser:
    # MARK: __init__
    def __init__(self, site_name, log_file, data_file, backup_dir, cache_dir, cache_file, sitemap_url, test_problem_urls=False, problem_urls=None):

        self.site_name = site_name
        self.log_file = log_file
        self.data_file = data_file
        self.backup_dir = backup_dir
        self.cache_dir = cache_dir
        self.cache_file = cache_file
        self.sitemap_url = sitemap_url
        self.test_problem_urls = test_problem_urls
        self.problem_urls = problem_urls if problem_urls is not None else []

        logging.basicConfig(filename=self.log_file, 
                            level=logging.INFO, 
                            format='%(asctime)s - %(levelname)s - %(message)s',
                            filemode='w',
                            encoding='utf-8')

        self.cache = self._initialize_cache()

        self.data = {
            "name": self.site_name,
            "downloads": []
        }

        self.stats = {
            "added_games": [],
            "updated_games": [],
            "download_options": 0,
            "no_download_options": 0,
            "invalid_pages": 0,
            "error_connecting": [],
            "error_processing": []
        }

        self.scraper = cloudscraper.create_scraper()


    # MARK: run
    def run(self, urls=None):

        if urls is None:
            urls = self.get_urls_from_sitemap(self.sitemap_url)

        logging.info(f"Total URLs: {len(urls)}")

        if os.getenv('GITHUB_ACTIONS') == 'true':
            miniters_value = 100  # Для GitHub Actions
            maxinterval_value = 200
            logging.info('Running on GitHub Actions')
        else:
            miniters_value = None    # Для локального запуску
            maxinterval_value = 10
            logging.info('Running locally')


        for index, url in enumerate(tqdm(urls, desc="Processing pages", unit="page", miniters=miniters_value, maxinterval=maxinterval_value), start=1):
            self.process_url(index, url)  # Ваш метод обробки URL

        self._save_cache()

        # self.print_stats()

        with open(self.data_file, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=4)
        print(f"Data saved in file {self.data_file}")
        logging.info(f"Data saved in file {self.data_file}")


        os.makedirs(self.backup_dir , exist_ok=True)  # Create the directory if it doesn't exist
        current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        backup_filename  = f'ihl_{current_time}.json'
        backup_file_path  = os.path.join(self.backup_dir, backup_filename)
        # Збереження копії у JSON файл
        with open(backup_file_path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=4)
        print(f"The backup data is saved in file {backup_file_path}")
        logging.info(f"The backup data is saved in file {backup_file_path}")


    # MARK: _initialize_cache
    def _initialize_cache(self):
        os.makedirs(self.cache_dir, exist_ok=True)
        if os.path.exists(self.cache_file):
            with open(self.cache_file, 'r', encoding='utf-8') as file:
                return json.load(file)
        return {}


    # MARK: _save_cache
    def _save_cache(self):
        with open(self.cache_file, 'w', encoding='utf-8') as file:
            json.dump(self.cache, file, ensure_ascii=False, indent=4)
        print(f"Cache saved to {self.cache_file}")
        logging.info(f"Cache saved to {self.cache_file}")


    # MARK: get_urls_from_sitemap
    def get_urls_from_sitemap(self, sitemap_url):
        try:
            response = self.scraper.get(sitemap_url)  # Use cloudscraper to get the sitemap

            response.raise_for_status()  # Check the response status
            sitemap_content = response.content
        except requests.RequestException as e:
            logging.error(f"Error connecting to {sitemap_url}: {e}")
            return []
        
        # Парсинг XML для витягнення всіх URL
        root = ET.fromstring(sitemap_content)
        namespaces = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
        return [elem.text for elem in root.findall('.//ns:loc', namespaces)]


    # MARK: get_urls_from_cache
    def get_urls_from_cache(self):
        return list(self.cache.keys())


    # MARK: process_url
    def process_url(self, index, url):
        try:
            page_response = self.scraper.get(url)  # Use cloudscraper to get the page
            page_response.raise_for_status()  # Check the response status
            soup = BeautifulSoup(page_response.text, 'html.parser')
            site_update_date, site_game_name = self._parse_date_title(soup)

            # Якщо сторінка не з грою, пропускаємо
            if not site_update_date or not site_game_name:
                logging.info(f"{index}. (INVALID_PAGE) {url}")

                self.stats["invalid_pages"] += 1
                return

            # Якщо дані актуальні, беремо з кешу
            cache_entry = self.cache.get(url)
            if cache_entry and cache_entry['site_update_date'] == site_update_date:

                logging.info(f'{index}. (CACHE) {cache_entry["site_game_name"]} / {cache_entry["site_update_date"]} / {url}')

                for cached_download in cache_entry["download_options"]:

                    self.data["downloads"].append(cached_download)
                    logging.info(f'       {cached_download["title"]} / {cached_download["uploadDate"]} / {cached_download["fileSize"]}')

                self.stats["download_options"] += len(cache_entry["download_options"])
                return


            download_options = self.parse_download_options(soup)
            # Якщо немає варіантів завантаження, пропускаємо
            if not download_options:
                logging.info(f'{index}. (NO_DOWNLOAD_OPTIONS) {site_game_name} / {site_update_date} / {url}')
                self.stats["no_download_options"] += 1
                return


            if cache_entry:
                game_page_log = f'{index}. (UPDATED) {site_game_name} / {cache_entry['site_update_date']} -> {site_update_date} / {url}'   
                self.stats["updated_games"].append(game_page_log)
            else:
                game_page_log = f'{index}. (ADDED) {site_game_name} / {site_update_date} / {url}'
                self.stats["added_games"].append(game_page_log)
            logging.info(game_page_log)

            translated_name = self.translate_text(site_game_name, target_language='en', source_language='ru')
            
            # Новий запис у кеші
            cache_entry = {
                "site_update_date": site_update_date,
                "site_game_name": site_game_name,
                "download_options": []
            }

            for download_option in download_options:

                title = f"{translated_name} {download_option['info'].replace('от', 'by')}"


                if (download_option['date']):
                    uploadDate = download_option['date']
                else:
                    logging.warning(f'Date Not Available in Torrent File. Using page update date')
                    uploadDate = date_to_iso(site_update_date)


                logging.info(f'       {title} / {uploadDate} / {download_option["fileSize"]}')

                download_info = {
                    "title": title,
                    "uris": [download_option['magnet_link']],
                    "uploadDate": uploadDate,
                    "fileSize": download_option['fileSize']
                }

                self.data["downloads"].append(download_info)
                cache_entry["download_options"].append(download_info)

                self.stats["download_options"] += 1

            # Оновлюємо кеш із новими даними для поточного URL
            self.cache[url] = cache_entry


        except requests.RequestException as e:
            logging.error(f"{index}. Error connecting to {url}: {e}")
            self.stats["error_connecting"].append(f'{index}. {url}')

            cache_entry = self.cache.get(url)
            if cache_entry:

                logging.info(f'{index}. (RequestException)(CACHE) {cache_entry["site_game_name"]} / {cache_entry["site_update_date"]} / {url}')

                for cached_download in cache_entry["download_options"]:

                    self.data["downloads"].append(cached_download)
                    logging.info(f'       {cached_download["title"]} / {cached_download["uploadDate"]} / {cached_download["fileSize"]}')

                self.stats["download_options"] += len(cache_entry["download_options"])

            
        except Exception as e:
            logging.error(f"{index}. Error processing {url}: {e}")
            self.stats["error_processing"].append(f'{index}. {url}')


    # MARK: parse_download_options
    def parse_download_options(self, soup):

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
                page_response_2 = self.scraper.get(torrent['href'])  # Use cloudscraper to get the download page
                page_response_2.raise_for_status()
                soup_2 = BeautifulSoup(page_response_2.text, 'html.parser')
                download_page_link = soup_2.find('a', class_='torrent2')

                navbartor = torrent.find_parent('ul', id='navbartor')
                if not navbartor:
                    continue  # Продовжити, якщо 'navbartor' не знайдено

                center_tag = navbartor.find_previous('center')
                if not center_tag:
                    continue  # Продовжити, якщо <center> не знайдено

                size_and_info = center_tag.find('span', style="font-size:14pt;")
                if not size_and_info or not download_page_link:
                    continue


                site_size, name_details = self._parse_size_info(size_and_info.get_text(strip=True))

                # Завантаження торрент файлу
                torrent_url = download_page_link['href']
                try:
                    # Отримання контенту файлу
                    response = self.scraper.get(torrent_url)  # Use cloudscraper to get the torrent file
                    response.raise_for_status()
                    # Використання BytesIO для зберігання в пам'яті
                    torrent_bytes = BytesIO(response.content)
                    # Отримання магнет-посилання
                    magnet_link, torrent_date, torrent_size_bytes = self._torrent_to_magnet(torrent_bytes.getvalue())

                except requests.RequestException as e:
                    logging.error(f"Failed to download {torrent_url}: {e}")
                    magnet_link, torrent_date, torrent_size_bytes = None, None, None

                if magnet_link:
                    torrent_info_list.append({
                        'info': name_details,
                        'fileSize': site_size,
                        'date': torrent_date,
                        'magnet_link': magnet_link
                    })

            except Exception as e:
                logging.error(f"Failed to process {torrent['href']}: {e}")

        return torrent_info_list


    # MARK: _torrent_to_magnet
    def _torrent_to_magnet(self, torrent_bytes):
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
                # print('Date Not Available in Torrent File')
                # logging.warning(f'(_torrent_to_magnet) Date Not Available in Torrent File')
                pass

            return magnet_link, formatted_date, total_length
        
        # У випадку будь-якої помилки повертаємо None
        except Exception as e: 
            logging.error(f'TORRENT_TO_MAGNET_ERROR: {e}')
            return None, None, None


    # MARK: _parse_size_info
    def _parse_size_info(self, size_text):
        # Шаблон для регулярного виразу
        pattern = r'Размер:\s*([\d.,]+\s*(?:GB|MB|ГБ|МБ|Gb|Mb|Гб|Мб|gb|mb|гб|мб|МВ|МB|Mб))\s*(.*?)(?:\s*\|)?\s*$'
        match = re.search(pattern, size_text)
        
        if match:
            size = match.group(1)  # Витягуємо розмір
            info = match.group(2).strip()  # Витягуємо інформацію
            return size, info
        else:
            return "N/A", "NO_INFO"  # Якщо не знайдено відповідності


    # MARK: _parse_date_title
    def _parse_date_title(self, soup):
        # Витягування дати та часу
        site_update_date = None
        article_info = soup.find('div', {'id': 'article-film-full-info'})
        if article_info:
            time_element = article_info.find('time', {'class': 'published'})
            if time_element:
                site_update_date = time_element.text
        
        # Витягування назви
        site_game_title = None
        module_title_div = soup.find('div', class_='module-title')
        if module_title_div:
            h1_tag = module_title_div.find('h1')
            if h1_tag:
                site_game_title = h1_tag.text.strip()

        return site_update_date, site_game_title


    # MARK: translate_text
    def translate_text(self, text, target_language='en', source_language='ru'):
        # Регулярний вираз для перевірки неанглійських букв
        non_english_pattern = re.compile(r'[^\x00-\x7F]')

        text = text.replace("’", "'")
        # text = text.replace("–", "-")

        # Перевіряємо, чи рядок містить неанглійські букви
        if non_english_pattern.search(text):
            return translate_line(text , target_language, source_language)
        else:
            # print(f'ALREADY IN ENGLISH ({text})')
            return text 


    # MARK: print_stats
    def print_stats(self, output_file="stats_output.txt"):
        # Відкриваємо файл для запису
        with open(output_file, "w", encoding="utf-8") as file:
            # Додаємо заголовок коміта
            file.write("Update JSON file with latest torrent data\n")
            
            for stat_name, stat_value in self.stats.items():
                if isinstance(stat_value, list):

                    output_text = f"{stat_name.replace('_', ' ').title()}: {len(stat_value)}"
                    print(output_text)
                    logging.info(output_text)
                    file.write(output_text + "\n")  # Запис в файл

                    for element in stat_value:
                        element_text = f" - {element}"
                        print(element_text)
                        logging.info(element_text)
                        file.write(element_text + "\n")  # Запис кожного елемента в файл

                else:
                    output_text = f"{stat_name.replace('_', ' ').title()}: {stat_value}"
                    print(output_text)
                    logging.info(output_text)
                    file.write(output_text + "\n")  # Запис в файл
