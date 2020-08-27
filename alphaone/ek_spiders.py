import logging
logging.basicConfig(level=logging.DEBUG)

import time
import json
from ek_search_crawler import SearchCrawler
from ek_count_crawler import CountCrawler
from ek_itemdetail_crawler import ItemDetailCrawler
from ek_userdetail_crawler import UserDetailCrawler


CRAWL_FREQUENCE_IN_SECONDS = 7
crawl_next_call = time.time()

def get_next_crawler():
    with open("crawler_config.json") as json_data_file:
        crawler_config = json.load(json_data_file)
        if crawler_config['search'] and SearchCrawler.is_next():
            return SearchCrawler()
        elif crawler_config['count'] and CountCrawler.is_next():
            return CountCrawler()
        elif crawler_config['item_detail'] and ItemDetailCrawler.is_next():
            return ItemDetailCrawler()
        elif crawler_config['user_detail'] and UserDetailCrawler.is_next():
            return UserDetailCrawler()
        else:
            return DoNothingCrawler()

class DoNothingCrawler():
    def run(self):
        logging.info("CONGRATULATION !!!!! I AM DO NOTHING CRAWLER ...")

if __name__ == "__main__":
    while True:
        try:
            crawler = get_next_crawler()
            status_code = crawler.run()
            crawl_next_call = crawl_next_call + CRAWL_FREQUENCE_IN_SECONDS
            sleep_duration = max(crawl_next_call - time.time(), 0.001)
            logging.debug("Time to next crawling turn = {}.".format(crawl_next_call - time.time()))
            logging.info("*********************************************************************************************")
            time.sleep(sleep_duration)
        except Exception as e:
            logging.debug(e)
            logging.info("I pass the crawling turn at {} and waiting for {}.".format(time.time(), CRAWL_FREQUENCE_IN_SECONDS))
            logging.info("*********************************************************************************************")
            time.sleep(CRAWL_FREQUENCE_IN_SECONDS)

