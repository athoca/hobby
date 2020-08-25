from datetime import datetime, timedelta
import time
import requests
from ek_orm import EKMonitoringItem, EKViewCount, session

import redis
# r = redis.Redis(host='localhost', port=6379, db=0)
r = redis.StrictRedis(host='localhost', port=6379, db=0, decode_responses=True)

crawl_next_call = time.time()

headers = {
    'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 13_2_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.0.3 Mobile/15E148 Safari/604.1',
    'Connection' : 'keep-alive',
    'Cache-Control' : 'max-age=0',
    'Upgrade-Insecure-Requests' : '1',
    'Accept' : 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
    'Accept-Encoding' : 'gzip, deflate, br',
    'Accept-Language' : 'en-US,en;q=0.9,vi;q=0.8',
    }

def _get_next_count_time(count_duration, count_time):
    if count_duration < 4320: # 3 days in minutes
        next_count_duration = count_duration + 60 # check every 60'
        next_count_time = count_time + timedelta(minutes=60)
    elif count_duration < 10080: # 7 days in minutes
        next_count_duration = count_duration + 120 # check every 120'
        next_count_time = count_time + timedelta(minutes=120)
    else:
        next_count_duration = count_duration + 1440 # check everyday
        next_count_time = count_time + timedelta(minutes=1440)
    return next_count_duration, next_count_time

if __name__ == "__main__":
    while True:
        # Get all items need to count now
        now = datetime.now()
        monitoring_items = session.query(EKMonitoringItem).filter(EKMonitoringItem.next_count_time < now)
        items = monitoring_items.all()

        for item in items:
            view_count_url = "https://m.ebay-kleinanzeigen.de/s-vac/?adId={}&userId={}".format(item.item_id, item.seller_id)

            if r.exists(item.item_id):
                res = requests.get(view_count_url, headers=headers, cookies=r.hgetall(item.item_id))
            else:
                res = requests.get(view_count_url, headers=headers)
                r.hmset(item.item_id, res.cookies.get_dict())

            view_count = res.json()['counter']
            duration = now - item.next_count_time
            duration = item.count_duration + duration.seconds // 60 # in minute from published. Note: duration.seconds only good when duration positive

            next_count_duration, next_count_time = _get_next_count_time(item.count_duration, item.next_count_time)
            item.count_duration = next_count_duration
            item.next_count_time = next_count_time
            session.add(EKViewCount(count=view_count, at=duration, item_id=item.item_id))
            session.commit()
        
        print("UPDATE COUNT!")
        crawl_next_call = crawl_next_call + 60*5 # next 5 minutes
        sleep_duration = max(crawl_next_call - time.time(), 0.01)
        time.sleep(sleep_duration)