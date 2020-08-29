import logging
from datetime import datetime
from datetime import timedelta
import requests
from bs4 import BeautifulSoup as soup
import os
from PIL import Image
from io import BytesIO
from pathlib import Path
import threading
import collections

from ek_orm import EKMonitoringItem, EKItem, EKViewCount, session
from ek_itemdetail_crawler import _download_image, _save_html, IMAGE_FOLDER


HEADERS = {
    'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 13_2_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.0.3 Mobile/15E148 Safari/604.1',
    'Connection' : 'keep-alive',
    'Cache-Control' : 'max-age=0',
    'Upgrade-Insecure-Requests' : '1',
    'Accept' : 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
    'Accept-Encoding' : 'gzip, deflate, br',
    'Accept-Language' : 'en-US,en;q=0.9,vi;q=0.8',
    }

class SearchUrlException(Exception):
    """Raised when access search url failed"""
    def __init__(self, message=""):
        self.message = message
    def __str__(self):
        return ":::::::::::: Execute search crawler UNSUCCESSFUL :::::::::::: {}".format(self.message)

class SearchCrawler():
    """ Crawl list of new item_id with basic information
    """
    NEW_ITEM_NB = 0
    SEARCH_REQUEST_NB = 0
    last_search_items = []
    nb_news_deque = collections.deque(maxlen=20)
    time_deque = collections.deque(maxlen=20)
    @classmethod
    def is_next(cls):
        STANDARD_DURATION = 10
        MAX_DURATION = 60*30    # 30 MINUTES
        NB_ITEM_EACH_TURN = 30
        if cls.time_deque:
            logging.debug("Last time SEARCH called: {}".format(cls.time_deque[-1]))
        else:
            logging.debug("First time SEARCH called.")
        # last_search_items = [] => last call is not succeful yet, len(time_deque) == 0 => First call
        if not cls.last_search_items or len(cls.time_deque) == 0:
            return True
        last_time = cls.time_deque[-1]
        next_duration = STANDARD_DURATION
        if len(cls.time_deque) < 5:
            return (datetime.now() - last_time).seconds > STANDARD_DURATION   # first 5 times, call every 60 seconds
        else:
            # neu so news trong last 1 turn > 4/5*30 thi se giam theo ty le thoi gian de giu la 2/3
            if cls.nb_news_deque[-1] > NB_ITEM_EACH_TURN * 4/5:
                last_duration = (last_time - cls.time_deque[-2]).seconds
                next_duration = last_duration * (2/3*NB_ITEM_EACH_TURN)/cls.nb_news_deque[-1]
                logging.debug("TIME TO NEXT SEARCH: {}".format(next_duration))
                return (datetime.now() - last_time).seconds > min(next_duration, MAX_DURATION)
            # neu so news trong 1 turn < 1/3 thi se cong tong thoi gian cac turn truoc de so luong > 1/2
            elif cls.nb_news_deque[-1] < NB_ITEM_EACH_TURN * 1/3:
                enough_items = False
                items_sum = 0
                next_duration = 0
                for i, nb_news in enumerate(reversed(cls.nb_news_deque)):
                    items_sum += nb_news
                    if items_sum > NB_ITEM_EACH_TURN * 4/5:
                        break
                    if i == len(cls.time_deque) - 1: # prevent out of range
                        break
                    k = -1 - i
                    next_duration += (cls.time_deque[k] - cls.time_deque[k-1]).seconds
                    if items_sum > NB_ITEM_EACH_TURN * 1/2:
                        break
                logging.debug("TIME TO NEXT SEARCH: {}".format(next_duration))
                return (datetime.now() - last_time).seconds > min(next_duration, MAX_DURATION)
            else:
                next_duration = (cls.time_deque[-1] - cls.time_deque[-2]).seconds 
                logging.debug("TIME TO NEXT SEARCH: {}".format(next_duration))
                return (datetime.now() - last_time).seconds > min(next_duration, MAX_DURATION)

    def __init__(self, url=None, headers=None):
        self.url = url or "https://m.ebay-kleinanzeigen.de/s-anzeigen/multimedia-elektronik-80331/c161-l6443?distance=100"
        self.headers = headers or HEADERS
        self.cls = SearchCrawler
    
    def execute_request(self):
        try:
            response = requests.get(self.url, headers=self.headers)
            if response.status_code != 200:
                logging.debug(":::: Query SEARCH UNSUCCESSFUL:::: Code={}".format((response.status_code)))
                return []
            # _save_html(response, "test.html")
            page = response.text
            doc = soup(page, "html.parser")
            items = [element for element in doc.find_all('li', {"class": "j-adlistitem adlist--item"})]
            logging.debug(":::: Finish query search SUCCESSFUL: {}".format(self.url))
            return items
        except Exception as e:
            print(e)
            raise SearchUrlException(message=search_url)
    
    def _extract_item_url(self, item):
        orign_url = "https://m.ebay-kleinanzeigen.de"
        return orign_url + item.attrs['data-href']

    def _extract_item_id(self, item):
        return item.attrs['data-adid']
    def _extract_item_stadt(self, item):
        div = item.find('div', {"class": "adlist--item--info--location"}).contents
        if len(div) == 1:
            item_stadt = div[0].strip()
        else:
            item_stadt = 'Deutschland'
        return item_stadt

    def _extract_item_release_time(self, item):
        # div = item.find('div', {"class": "adlist--item--info--date"}).contents
        # if len(div) == 1:
        #     release_time = div[0].split(',')[-1].strip()
        #     datetime.strptime(release_time, '%H:%M')
        #     # TODO: add day, month and year
        # else:
        #     release_time = datetime.now()

        # Note: set release time = now => good enough, while simple logics e.g 23:99 => 0:00
        release_time = datetime.now() # utcnow or now?
        return release_time
    
    def _extract_item_title(self, item):
        return item.find('a').text

    def _extract_item_price(self, item):
        item_price = item.find('div', {"class": "adlist--item--price"}).text
        item_price = ''.join(filter(str.isdigit, item_price))   # keep only numerical price
        if not item_price:
            item_price = -1.0 # not specified
        return item_price 
    
    def _extract_image_url(self, item):
        image_url = item.find('img', {"class": "lazy"}).attrs['data-src']
        return image_url

    def run(self):
        self.cls.SEARCH_REQUEST_NB += 1
        logging.info("Running SEARCH crawler ...")
        news_count = 0
        now_items = []
        items = self.execute_request()
        for k, item in enumerate(items[:]):
            try:
                item_url, item_id, item_stadt, release_time, item_title, item_price, image_url = self.extract_item_info(item)
                now_items.append(item_id)
                if item_id not in self.cls.last_search_items:
                    self.store_items_database(item_id, item_url, item_title, item_price, release_time, item_stadt)
                    self.store_an_image(image_url, item_id)
                    news_count += 1
                    self.cls.NEW_ITEM_NB += 1
                    logging.debug("New item id = {}".format(item_id))
                else:
                    logging.debug("Existed item id = {}".format(item_id))
            except Exception as e:
                logging.debug(e)
                logging.debug(":::: I am continue, pass adding item: {}".format(item_url))
        self.cls.last_search_items = now_items
        self.cls.time_deque.append(datetime.now())
        self.cls.nb_news_deque.append(news_count)

    def store_items_database(self, item_id, item_url, item_title, item_price, release_time, item_stadt):
        if session.query(EKItem).filter_by(id=item_id).scalar() is None:
            # Commit new item into database, after all information exist
            new_item = EKItem(id=item_id, url = item_url, title=item_title, price=item_price, release_time=release_time, stadt=item_stadt)
            zero_count = EKViewCount(h4=-1, d1=-1, d3=-1, d5=-1, d7=-1, d10=-1, d14=-1, d28=-1, item_id=item_id,\
                                    next_count_time=release_time + timedelta(hours=4), \
                                    release_time=release_time)
            # new_monitoring_item = EKMonitoringItem(item_id=int(item_id), next_count_time=release_time, count_duration=0)
            session.add(new_item)
            session.add(zero_count)
            session.commit()
        logging.info("::::SUCCESSFUL Store new item and monitoring item into database.")

    def extract_item_info(self, item):
        item_url = self._extract_item_url(item)
        item_id = self._extract_item_id(item)
        item_stadt = self._extract_item_stadt(item)
        release_time = self._extract_item_release_time(item)
        item_title = self._extract_item_title(item)
        item_price = self._extract_item_price(item)
        image_url = self._extract_image_url(item)
        return item_url, item_id, item_stadt, release_time, item_title, item_price, image_url

    def store_an_image(self, image_url, item_id):
        # Asynchronously download and store images
        if image_url.endswith('35.JPG'): # magic name for not None image
            storage_folder = os.path.join(IMAGE_FOLDER, str(item_id))
            Path(storage_folder).mkdir(parents=True, exist_ok=True)
            try:
                filename = os.path.join(storage_folder, "{}_.jpg".format(item_id))
                _download_image(image_url, filename)
            except Exception as e:
                logging.debug(e)
                logging.debug(":::: Download IMAGES UNSUCCESSFUL")
            logging.debug("::::Finish downloading images of {}!".format(item_id))