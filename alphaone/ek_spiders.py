import logging
logging.basicConfig(level=logging.DEBUG)

import time
import json
from ek_search_crawler import SearchCrawler
from ek_count_crawler import CountCrawler
from ek_itemdetail_crawler import ItemDetailCrawler
from ek_userdetail_crawler import UserDetailCrawler


CRAWL_FREQUENCE_IN_SECONDS = 7.5
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
            # Co hien tuong cascade => lam cho trong 1 thoi gian ngan, call rat nhieu lan. Fix thay sleep_duration min = CRAWL_FREQUENCE_IN_SECONDS/2
            sleep_duration = max(crawl_next_call - time.time(), CRAWL_FREQUENCE_IN_SECONDS/2)
            logging.debug("nb search: {}, nb news: {}, nb count: {}, key: {}, nb item: {}, nb user: {}.".\
                            format(SearchCrawler.SEARCH_REQUEST_NB, SearchCrawler.NEW_ITEM_NB, \
                                CountCrawler.COUNT_REQUEST_NB, CountCrawler.key, \
                                    ItemDetailCrawler.ITEM_REQUEST_NB, UserDetailCrawler.USER_REQUEST_NB))
            logging.debug("Time to next crawling turn = {}.".format(crawl_next_call - time.time()))
            logging.info("*********************************************************************************************")
            time.sleep(sleep_duration)
            time.sleep(sleep_duration)
        except Exception as e:
            logging.debug(e)
            logging.info("I pass the crawling turn at {} and waiting for {}.".format(time.time(), CRAWL_FREQUENCE_IN_SECONDS))
            logging.info("*********************************************************************************************")
            time.sleep(CRAWL_FREQUENCE_IN_SECONDS)

