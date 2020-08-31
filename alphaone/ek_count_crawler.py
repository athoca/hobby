import logging

from datetime import datetime
from datetime import timedelta
import requests

from ek_orm import session
from ek_orm import EKMonitoringItem, EKViewCount

import redis
# r = redis.Redis(host='localhost', port=6379, db=0)
r = redis.StrictRedis(host='localhost', port=6379, db=0, decode_responses=True)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 13_2_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.0.3 Mobile/15E148 Safari/604.1',
    'Connection' : 'keep-alive',
    'Cache-Control' : 'max-age=0',
    'Upgrade-Insecure-Requests' : '1',
    'Accept' : 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
    'Accept-Encoding' : 'gzip, deflate, br',
    'Accept-Language' : 'en-US,en;q=0.9,vi;q=0.8',
    }

class CountUrlException(Exception):
    """Raised when access count url failed"""
    def __init__(self, message=""):
        self.message = message
    def __str__(self):
        return ":::::::::::: Execute count crawler UNSUCCESSFUL :::::::::::: {}".format(self.message)


class CountCrawler():
    """ Crawl view count of an item
    """
    COUNT_REQUEST_NB = 0
    lasttime = None
    MAX_BUFFER_ITEMS = 10 # should not too big
    key = ""
    key_2_timedelta = {"h4": timedelta(days=1), "d1": timedelta(days=3), "d3": timedelta(days=5), "d5": timedelta(days=7), \
                    "d7": timedelta(days=10), "d10": timedelta(days=14), "d14": timedelta(days=28), "d28": timedelta(weeks=52)}
    buffer_items = {"h4":[], "d1":[], "d3":[], "d5":[], "d7":[], "d10":[], "d14":[], "d28":[]}
    key_list = ["h4", "d1", "d3", "d5", "d7", "d10", "d14", "d28"]

    @classmethod
    def is_next(cls):
        logging.debug("Last time VIEW COUNT called: {}".format(cls.lasttime))
        for key in cls.key_list:
            if cls.buffer_items[key]:
                cls.key = key
                return True
            else:
                cls.update_buffer_items(key)
                if cls.buffer_items[key]:
                    cls.key = key
                    return True
        return False

    @classmethod
    def update_buffer_items(cls, key):
        now = datetime.now()
        kwargs = {key: '-1'}
        items = session.query(EKViewCount).filter(EKViewCount.next_count_time < now).\
                                            filter_by(**kwargs).limit(cls.MAX_BUFFER_ITEMS)
        cls.buffer_items[key] = items.all()

    def __init__(self, headers=None):
        self.headers = headers or HEADERS
        self.cls = CountCrawler

    def execute_request(self, item_id, seller_id="12345678"):
        view_count_url = "https://m.ebay-kleinanzeigen.de/s-vac/?adId={}&userId={}".format(item_id, seller_id)
        logging.debug(view_count_url)
        try:
            if r.exists(item_id):
                res = requests.get(view_count_url, headers=self.headers, cookies=r.hgetall(item_id))
            else:
                res = requests.get(view_count_url, headers=self.headers)
                if res.status_code == 200:
                    r.hmset(item_id, res.cookies.get_dict())
            if res.status_code == 200:
                count = res.json()['counter']
                logging.debug(":::: Finish query count SUCCESSFUL: {}".format(view_count_url))
                return count
            else:
                logging.debug(":::: Query COUNT UNSUCCESSFUL:::: Code={}".format((res.status_code)))
                return None
        except Exception as e:
            print(e)
            raise CountUrlException(message=view_count_url)
            
    def run(self):
        key = self.cls.key
        self.cls.COUNT_REQUEST_NB += 1
        if len(self.cls.buffer_items[key]) > 0:
            item = self.cls.buffer_items[key].pop(0)
            view_count = self.execute_request(item.item_id)
            self.cls.lasttime = datetime.now()
            if view_count:
                item.__setattr__(key, view_count)
                item.next_count_time = item.release_time + self.cls.key_2_timedelta[key]
                # TODO: upgrade algorithm to skip when view count small => update skip date = -2, add next_count_time correspondingly
                session.commit()    # update count item
                logging.info("::::SUCCESSFUL Store new count into database.")
        else:
            logging.debug(":::::WARNING: Count item buffer is empty while is_next return True:::::")