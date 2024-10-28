import os

SITE_NAME = "Torrents-Igruha" # "Torrents-Igruha" "Igruha" "TI"

SITEMAP_URL = 'https://itorrents-igruha.org/sitemap.xml'

CACHE_DIR = 'cache'
CACHE_FILE = os.path.join(CACHE_DIR, 'parser_cache.json')

BACKUP_DIR = 'json'

DATA_FILE = 'hydra_links_igruha.json'

LOG_FILE = 'parser.log'

# If True, the parser will only parse problem_urls
test_problem_urls = False # True False
problem_urls = [
    "https://itorrents-igruha.org/8095-believe.html", # DEAD_TORRENT
    "https://itorrents-igruha.org/14496-sailing-era.html",
    "https://itorrents-igruha.org/3671-1-126821717.html",
    "https://itorrents-igruha.org/11642-8-99980.html",
    "https://itorrents-igruha.org/7793-muse-dash.html",
    "https://itorrents-igruha.org/15285-metaphor-refantazio.html",
    "https://itorrents-igruha.org/2576-witchfire.html",
    "https://itorrents-igruha.org/3821-126821717.html",
    "https://itorrents-igruha.org/16170-windblown.html"

]