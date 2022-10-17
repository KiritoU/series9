import logging
import time

from settings import CONFIG
from base import Crawler_Site

logging.basicConfig(format="%(asctime)s %(levelname)s:%(message)s", level=logging.INFO)

UPDATE = Crawler_Site()

if __name__ == "__main__":
    pages = CONFIG.SERIES9_MOVIES_LAST_PAGE
    while True:
        for i in range(pages, 1, -1):
            try:
                UPDATE.crawl_page(
                    url=f"{CONFIG.SERIES9_MOVIES_LATEST_PAGE}?page={i}",
                    post_type="post",
                )

            except Exception as e:
                pass
            time.sleep(CONFIG.WAIT_BETWEEN_ALL)
