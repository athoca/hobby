import logging

from datetime import datetime
from datetime import timedelta
import requests
from bs4 import BeautifulSoup as soup

from ek_orm import session
from ek_orm import EKMonitoringItem, EKViewCount

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 13_2_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.0.3 Mobile/15E148 Safari/604.1',
    'Connection' : 'keep-alive',
    'Cache-Control' : 'max-age=0',
    'Upgrade-Insecure-Requests' : '1',
    'Accept' : 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
    'Accept-Encoding' : 'gzip, deflate, br',
    'Accept-Language' : 'en-US,en;q=0.9,vi;q=0.8',
    }

class BidUrlException(Exception):
    """Raised when access count url failed"""
    def __init__(self, message=""):
        self.message = message
    def __str__(self):
        return ":::::::::::: Execute count crawler UNSUCCESSFUL :::::::::::: {}".format(self.message)


class BidCrawler():
    """ Crawl view count of an item
    """
    COUNT_REQUEST_NB = 0
    lasttime = None
    MAX_BUFFER_ITEMS = 10 # should not too big

    @classmethod
    def is_next(cls):
        logging.debug("Last time VIEW COUNT called: {}".format(cls.lasttime))
        return True

    @classmethod
    def update_buffer_items(cls, key):
        pass

    def __init__(self, headers=None):
        self.headers = headers or HEADERS
        self.cls = BidCrawler

    def _extract_nb_bids(self, doc):
        overall = doc.find_all('div', {'class': 'ui-label-value-list__value'})
        overall = [div.text for div in overall]
        if overall:
            nb_bids = overall[0]
            nb_bidders = overall[1]
        else:
            nb_bids = 0
            nb_bidders = 0
        return nb_bids, nb_bidders

    def _extract_bid_history(self, doc):
        bid_history = doc.find('div', {'class': 'app-bid-history__container'})
        bid_history = bid_history.find_all('span')
        bid_history = bid_history[::2]
        bid_history = [span.text for span in bid_history]
        start_price = bid_history[-1]
        bid_history = [{"bidder": bid_history[i*3], \
                        "price": bid_history[i*3+1], \
                        "datetime": bid_history[i*3+2]} \
                        for i in range(len(bid_history)//3)]
        if bid_history:
            highest_price = bid_history[0]['price']
        else:
            highest_price = start_price
        return highest_price, start_price, bid_history

    def execute_request(self, item_id):
        try:
            bid_history_url = "https://www.ebay.de/bfl/viewbids/{}".format(item_id)
            response = requests.get(bid_history_url, headers=self.headers)
            if response.status_code != 200:
                logging.debug(":::: Query BID HISTORY UNSUCCESSFUL:::: Code={}".format((response.status_code)))
                return [None, None, None, None]
            # _save_html(response, "test.html")
            page = response.text
            doc = soup(page, "html.parser")
            nb_bids, nb_bidders = self._extract_nb_bids(doc)
            highest_price, start_price, bid_history = self._extract_bid_history(doc)
            logging.debug(":::: Finish query bid history SUCCESSFUL: {}".format(bid_history_url))
            return nb_bids, nb_bidders, highest_price, start_price, bid_history
        except Exception as e:
            print(e)
            raise ItemUrlException(message=bid_history_url)
            
    def run(self):
        self.cls.COUNT_REQUEST_NB += 1

        # if len(self.cls.buffer_items[key]) > 0:
        if True:
            # item = self.cls.buffer_items[key].pop(0)
            item_id = 264839280978
            nb_bids, nb_bidders, highest_price, start_price, bid_history = self.execute_request(item_id)

            logging.debug(nb_bids)
            logging.debug(nb_bidders)
            logging.debug(highest_price)
            logging.debug(start_price)
            logging.debug(bid_history)

            self.cls.lasttime = datetime.now()
            # if highest_price:
            #     item.__setattr__(key, view_count)
            #     item.next_count_time = item.release_time + self.cls.key_2_timedelta[key]
            #     # TODO: upgrade algorithm to skip when view count small => update skip date = -2, add next_count_time correspondingly
            #     session.commit()    # update count item
            #     logging.info("::::SUCCESSFUL Store new count into database.")
        else:
            logging.debug(":::::WARNING: Count item buffer is empty while is_next return True:::::")