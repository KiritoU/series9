import logging
import time

from settings import CONFIG
from base import Crawler_Site

logging.basicConfig(format="%(asctime)s %(levelname)s:%(message)s", level=logging.INFO)


UPDATE = Crawler_Site()

if __name__ == "__main__":
    while True:
        try:
            UPDATE.crawl_page(url=CONFIG.SERIES9_MOVIES_LATEST_PAGE, post_type="post")
        except Exception as e:
            pass
        time.sleep(CONFIG.WAIT_BETWEEN_LATEST)
