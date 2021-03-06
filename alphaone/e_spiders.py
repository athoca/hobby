import logging
logging.basicConfig(level=logging.DEBUG)

import time
import json
from e_search_crawler import SearchCrawler
from e_itemdetail_crawler import ItemDetailCrawler
from e_bid_crawler import BidCrawler
from e_userdetail_crawler import UserDetailCrawler


CRAWL_FREQUENCE_IN_SECONDS = 5
crawl_next_call = time.time()

def get_next_crawler():
    with open("crawler_config.json") as json_data_file:

        crawler_config = json.load(json_data_file)
        if crawler_config['ebay_search'] and SearchCrawler.is_next():
            return SearchCrawler()
        elif crawler_config['ebay_bid_detail'] and BidCrawler.is_next():
            return BidCrawler()
        elif crawler_config['ebay_item_detail'] and ItemDetailCrawler.is_next():
            return ItemDetailCrawler()
        elif crawler_config['ebay_user_detail'] and UserDetailCrawler.is_next():
            return UserDetailCrawler()
        else:
            return DoNothingCrawler()

class DoNothingCrawler():
    def run(self):
        logging.info("CONGRATULATION !!!!! I AM DO NOTHING CRAWLER ...")

if __name__ == "__main__":
    while True:
        # try:
        crawler = get_next_crawler()
        status_code = crawler.run()
        crawl_next_call = crawl_next_call + CRAWL_FREQUENCE_IN_SECONDS
        sleep_duration = max(crawl_next_call - time.time(), 0.001)
        # logging.debug("nb search: {}, nb news: {}, nb count: {}, key: {}, nb item: {}, nb user: {}.".\
        #                 format(SearchCrawler.SEARCH_REQUEST_NB, SearchCrawler.NEW_ITEM_NB, \
        #                     CountCrawler.COUNT_REQUEST_NB, CountCrawler.key, \
        #                         ItemDetailCrawler.ITEM_REQUEST_NB, UserDetailCrawler.USER_REQUEST_NB))
        logging.debug("Time to next crawling turn = {}.".format(crawl_next_call - time.time()))
        logging.info("*********************************************************************************************")
        time.sleep(sleep_duration)
        # except Exception as e:
        #     logging.debug(e)
        #     logging.info("I pass the crawling turn at {} and waiting for {}.".format(time.time(), CRAWL_FREQUENCE_IN_SECONDS))
        #     logging.info("*********************************************************************************************")
        #     time.sleep(CRAWL_FREQUENCE_IN_SECONDS)

