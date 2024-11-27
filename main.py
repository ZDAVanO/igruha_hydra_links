from igruha_parser import IgruhaParser
import config



def main():
    parser = IgruhaParser(
        site_name=config.SITE_NAME,
        log_file=config.LOG_FILE,
        data_file=config.DATA_FILE,
        backup_dir=config.BACKUP_DIR,
        cache_dir=config.CACHE_DIR,
        cache_file=config.CACHE_FILE,
        sitemap_url=config.SITEMAP_URL,
        test_problem_urls=config.test_problem_urls,
        problem_urls=config.problem_urls
    )

    urls = parser.get_urls_from_sitemap(config.SITEMAP_URL)
    # urls = urls[:200]  # 200 перших URL для тестування

    if not urls:
        print("Failed to get URL from sitemap.xml")
        return

    if config.test_problem_urls:
        urls = config.problem_urls

    parser.run(urls=urls)
    parser.print_stats()


if __name__ == "__main__":
    main()