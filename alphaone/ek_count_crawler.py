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
    lasttime = None
    MAX_BUFFER_ITEMS = 10
    buffer_items = []

    @classmethod
    def is_next(cls):
        logging.debug("Last time called: {}".format(cls.lasttime))
        if cls.buffer_items:
            return True
        else:
            cls.update_buffer_items()
            if cls.buffer_items:
                return True
            else:
                return False 

    @classmethod
    def update_buffer_items(cls):
        now = datetime.now()
        # Get all items need to count now
        monitoring_items = session.query(EKMonitoringItem).\
                                    filter(EKMonitoringItem.next_count_time < now).\
                                    limit(cls.MAX_BUFFER_ITEMS)
        cls.buffer_items = monitoring_items.all()

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
                return res.json()['counter']
            else:
                return None
        except Exception as e:
            print(e)
            raise CountUrlException(message=view_count_url)
            
    def run(self):
        if len(self.cls.buffer_items) > 0:
            item = self.cls.buffer_items.pop(0)
            view_count = self.execute_request(item.item_id)
            self.cls.lasttime = datetime.now()
            if view_count:
                now = datetime.now()
                duration = now - item.next_count_time
                duration = item.count_duration + duration.seconds // 60 # in minute from published. Note: duration.seconds only correct when duration positive

                next_count_duration, next_count_time = self.get_next_count_time(duration, now)
                item.count_duration = next_count_duration
                item.next_count_time = next_count_time
                session.add(EKViewCount(count=view_count, at=duration, item_id=item.item_id))
                session.commit()    # both Update item and Add viewcount
                logging.info("::::SUCCESSFUL Store new count into database.")
        else:
            logging.debug(":::::WARNING: Count item buffer is empty while is_next return True:::::")
    
    #TODO: update rule to calculate next count time
    def get_next_count_time(self, count_duration, count_time):
        if count_duration < 1440:
            next_count_duration = count_duration + 60           # check every hour first day
            next_count_time = count_time + timedelta(minutes=60)
        elif count_duration < 4320:
            next_count_duration = count_duration + 120          # check every 2 hours next 2 days
            next_count_time = count_time + timedelta(minutes=120)
        elif count_duration < 10080:
            next_count_duration = count_duration + 240          # check every 4 hours next 4 days
            next_count_time = count_time + timedelta(minutes=240)
        else:
            next_count_duration = count_duration + 1440 # check everyday
            next_count_time = count_time + timedelta(minutes=1440)
        return next_count_duration, next_count_time