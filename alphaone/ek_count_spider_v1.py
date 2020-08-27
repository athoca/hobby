import logging
logging.basicConfig(level=logging.DEBUG)

from datetime import datetime, timedelta
import time
import requests
from ek_orm import EKMonitoringItem, EKViewCount, session

import redis
# r = redis.Redis(host='localhost', port=6379, db=0)
r = redis.StrictRedis(host='localhost', port=6379, db=0, decode_responses=True)

crawl_next_call = time.time()
CRAWL_FREQUENCE_IN_SECONDS = 60 # every minute
COUNT_REQUEST_PAUSE_IN_SECONDS = 2 # one each 7s OK, 1s => 429
EACH_CRAWL_MAX_COUNT = 100
sleep_time = 15

COUNT = 0

class CountUrlException(Exception):
    """Raised when the not found count url"""
    def __init__(self, message=""):
        self.message = message
    def __str__(self):
        return ":::::::::::: Query COUNT UNSUCCESSFUL :::::::::::: {}".format(self.message)

headers = {
    'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 13_2_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.0.3 Mobile/15E148 Safari/604.1',
    'Cache-Control' : 'no-cache',
    'Accept' : 'application/json',
    'Accept-Encoding' : 'gzip, deflate, br',
    'Accept-Language' : 'en-US,en;q=0.9,vi;q=0.8',
    'x-requested-with' : 'XMLHttpRequest'
    }

def _get_next_count_time(count_duration, count_time):
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

# def _query_count(item_id, seller_id):
#     view_count_url = "https://m.ebay-kleinanzeigen.de/s-vac/?adId={}&userId={}".format(item_id, seller_id)
#     try:
#         if r.exists(item_id):
#             res = requests.get(view_count_url, headers=headers, cookies=r.hgetall(item.item_id))
#         else:
#             res = requests.get(view_count_url, headers=headers)
#             if res.status_code == 200:
#                 r.hmset(item.item_id, res.cookies.get_dict())
#     except Exception as e:
#         print(e)
#         raise CountUrlException(message=view_count_url)

#     if res.status_code != 200:
#         logging.debug(":::: Response code: {}".format(res.status_code))
#         raise CountUrlException(message=view_count_url) 
#     return res.json()['counter']

def _query_count(item_id, seller_id):
    global COUNT
    view_count_url = "https://m.ebay-kleinanzeigen.de/s-vac/?adId={}&userId={}".format(item_id, seller_id)
    try:
        code = None
        while code != 200:
            if r.exists(item_id):
                res = requests.get(view_count_url, headers=headers, cookies=r.hgetall(item.item_id))
            else:
                res = requests.get(view_count_url, headers=headers)
                if res.status_code == 200:
                    r.hmset(item.item_id, res.cookies.get_dict())
            COUNT += 1
            code = res.status_code
            logging.debug(":::: {} Response code: {} at {}".format(COUNT, code, datetime.now()))
            if code != 200:
                logging.debug(res.headers)
                time.sleep(sleep_time)
    except Exception as e:
        print(e)
        raise CountUrlException(message=view_count_url)
    return res.json()['counter']


if __name__ == "__main__":
    while True:
        logging.info("::::Start crawling...")
        now = datetime.now()
        # Get all items need to count now
        monitoring_items = session.query(EKMonitoringItem).\
                                    filter(EKMonitoringItem.next_count_time < now).\
                                    limit(EACH_CRAWL_MAX_COUNT)
        items = monitoring_items.all()
        logging.info("::::Number of items to count: {}".format(len(items)))
        
        for item in items:
            time.sleep(COUNT_REQUEST_PAUSE_IN_SECONDS)
            try:
                view_count = _query_count(item.item_id, item.seller_id)
                duration = now - item.next_count_time
                duration = item.count_duration + duration.seconds // 60 # in minute from published. Note: duration.seconds only good when duration positive

                next_count_duration, next_count_time = _get_next_count_time(duration, now)
                item.count_duration = next_count_duration
                item.next_count_time = next_count_time
                session.add(EKViewCount(count=view_count, at=duration, item_id=item.item_id))
                session.commit()    # both Update item and Add viewcount
                
            except Exception as e:
                logging.debug(e)
                logging.debug(":::: I am continue, pass item count: {}".format(item.item_id))
        logging.info("::::Finish a crawl turn.")
        logging.info("**********************************************************************************************")
        
        crawl_next_call = crawl_next_call + CRAWL_FREQUENCE_IN_SECONDS
        sleep_duration = max(crawl_next_call - time.time(), 0.01)
        logging.debug(crawl_next_call - time.time())
        time.sleep(sleep_duration)
        