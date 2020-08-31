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
import re

# from ek_orm import EKMonitoringItem, EKItem, EKViewCount, session
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

def is_digit_or_point(c):
    return c.isdigit() or c=='.'

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
        return True # every N minutes
        # STANDARD_DURATION = 10
        # MAX_DURATION = 60*30    # 30 MINUTES
        # NB_ITEM_EACH_TURN = 30
        # if cls.time_deque:
        #     logging.debug("Last time SEARCH called: {}".format(cls.time_deque[-1]))
        # else:
        #     logging.debug("First time SEARCH called.")
        # # last_search_items = [] => last call is not succeful yet, len(time_deque) == 0 => First call
        # if not cls.last_search_items or len(cls.time_deque) == 0:
        #     return True
        # last_time = cls.time_deque[-1]
        # next_duration = STANDARD_DURATION
        # if len(cls.time_deque) < 5:
        #     return (datetime.now() - last_time).seconds > STANDARD_DURATION   # first 5 times, call every 60 seconds
        # else:
        #     # neu so news trong last 1 turn > 4/5*30 thi se giam theo ty le thoi gian de giu la 2/3
        #     if cls.nb_news_deque[-1] > NB_ITEM_EACH_TURN * 4/5:
        #         last_duration = (last_time - cls.time_deque[-2]).seconds
        #         next_duration = last_duration * (2/3*NB_ITEM_EACH_TURN)/cls.nb_news_deque[-1]
        #         logging.debug("TIME TO NEXT SEARCH: {}".format(next_duration))
        #         return (datetime.now() - last_time).seconds > min(next_duration, MAX_DURATION)
        #     # neu so news trong 1 turn < 1/3 thi se cong tong thoi gian cac turn truoc de so luong > 1/2
        #     elif cls.nb_news_deque[-1] < NB_ITEM_EACH_TURN * 1/3:
        #         enough_items = False
        #         items_sum = 0
        #         next_duration = 0
        #         for i, nb_news in enumerate(reversed(cls.nb_news_deque)):
        #             items_sum += nb_news
        #             if items_sum > NB_ITEM_EACH_TURN * 4/5:
        #                 break
        #             if i == len(cls.time_deque) - 1: # prevent out of range
        #                 break
        #             k = -1 - i
        #             next_duration += (cls.time_deque[k] - cls.time_deque[k-1]).seconds
        #             if items_sum > NB_ITEM_EACH_TURN * 1/2:
        #                 break
        #         logging.debug("TIME TO NEXT SEARCH: {}".format(next_duration))
        #         return (datetime.now() - last_time).seconds > min(next_duration, MAX_DURATION)
        #     else:
        #         next_duration = (cls.time_deque[-1] - cls.time_deque[-2]).seconds 
        #         logging.debug("TIME TO NEXT SEARCH: {}".format(next_duration))
        #         return (datetime.now() - last_time).seconds > min(next_duration, MAX_DURATION)

    def __init__(self, search_keys=None, headers=None):
        self.search_keys = search_keys
        self.headers = headers or HEADERS
        self.cls = SearchCrawler
    
    def execute_request(self, key):
        search_url = "https://www.ebay.de/sch/i.html?_from=R40&_nkw={}&LH_TitleDesc=1&LH_Auction=1&_sop=1&_ipg=200".format(key)
        try:
            response = requests.get(search_url, headers=self.headers)
            if response.status_code != 200:
                logging.debug(":::: Query SEARCH UNSUCCESSFUL:::: Code={}".format((response.status_code)))
                return []
            # _save_html(response, "test.html")
            page = response.text
            doc = soup(page, "html.parser")
            items = [element for element in doc.find_all('li', {"class": "s-item"})]
            logging.debug(":::: Finish query search SUCCESSFUL: {}".format(search_url))
            return items
        except Exception as e:
            print(e)
            raise SearchUrlException(message=search_url)
    
    def _extract_item_url(self, item):
        item_url = item.find('a', {'class': 's-item__link'}).attrs['href']
        item_id = item_url.split("?hash")[0]
        item_id = item_id.split("/")[-1]
        item_id = item_id.split("?")[0]
        return item_url, item_id

    def _extract_item_title(self, item):
        item_title = item.find('h3', {'class': 's-item__title'}).text
        return item_title

    def _extract_item_condition(self, item):
        item_condition = item.find('span', {'class': 'SECONDARY_INFO'})
        if item_condition:
            item_condition = item_condition.text
        return item_condition
    
    def _extract_buyitnow_option(self, item):
        buyitnow = item.find('span', {'class': 's-item__dynamic s-item__buyItNowOption'})
        if buyitnow:
            buyitnow = buyitnow.text
            if buyitnow == "Sofort-Kaufen":
                return True
        return False

    def _extract_shipping_price(self, item):
        shipping_price = item.find('span', {'class': 's-item__shipping s-item__logisticsCost'})
        is_shippable = False
        if shipping_price:
            shipping_price = shipping_price.text
            if shipping_price ==  "Kostenloser Versand":
                shipping_price = "0"
            shipping_price = shipping_price.replace(',','.')
            shipping_price = ''.join(c for c in shipping_price if is_digit_or_point(c))
            is_shippable = True
        return shipping_price, is_shippable
    
    def _extract_image_url(self, item):
        image_url = item.find('img', {'class': "s-item__image-img"}).attrs['src']
        return image_url
    
    def _extract_highest_price(self, item):
        highest_price = item.find('span', {'class': 's-item__price'}).text
        highest_price = highest_price.replace(',','.')
        highest_price = ''.join(c for c in highest_price if is_digit_or_point(c))
        return highest_price

    def _extract_nb_bids(self, item):
        nb_bids = item.find('span', {'class': 's-item__bids s-item__bidCount'}).text
        nb_bids = ''.join(c for c in nb_bids if c.isdigit())
        return nb_bids

    def _extract_time(self, item):
        update_time = datetime.now()
        remaining_time = item.find('span', {'class': 's-item__time-left'}).text
        seconds = 0
        minutes = 0
        hours = 0
        days = 0
        if 'Sek' in remaining_time:
            if 'Min' in remaining_time:
                seconds = int(re.findall('Min(.+?)Sek', remaining_time)[0])
            else:
                seconds = int(re.findall('(.+?)Sek', remaining_time)[0])
        if 'Min' in remaining_time:
            if 'Std' in remaining_time:
                minutes = int(re.findall('Std(.+?)Min', remaining_time)[0])
            else:
                minutes = int(re.findall('(.+?)Min', remaining_time)[0])
        if 'Std' in remaining_time:
            if 'T' in remaining_time:
                hours = int(re.findall('T(.+?)Std', remaining_time)[0])
            else:
                hours = int(re.findall('(.+?)Std', remaining_time)[0])
        if 'T' in remaining_time:
            days = int(re.findall('(.+?)T', remaining_time)[0])
        end_time = update_time + timedelta(days=days, hours=hours, minutes=minutes, seconds=seconds)
        return update_time, end_time


    def extract_item_info(self, item):
        item_url, item_id = self._extract_item_url(item)
        item_title = self._extract_item_title(item)
        item_condition = self._extract_item_condition(item)
        buyitnow = self._extract_buyitnow_option(item)
        shipping_price, is_shippable = self._extract_shipping_price(item)
        image_url = self._extract_image_url(item)
        highest_price = self._extract_highest_price(item)
        nb_bids = self._extract_nb_bids(item)
        update_time, end_time = self._extract_time(item)
        return item_url, item_id, item_title, item_condition, buyitnow, shipping_price, \
                is_shippable, image_url, highest_price, nb_bids, update_time, end_time

    def run(self):
        self.cls.SEARCH_REQUEST_NB += 1
        logging.info("Running SEARCH crawler ...")
        now_items = []
        items = self.execute_request("apple")
        logging.debug(len(items))
        if len(items) > 1:
            for k, item in enumerate(items[1:]):
                try:
                    item_url, item_id, item_title, item_condition, buyitnow, shipping_price, \
                        is_shippable, image_url, highest_price, nb_bids, update_time, end_time = self.extract_item_info(item)
                    logging.debug(item_url)
                    logging.debug(item_id)
                    logging.debug(item_title)
                    logging.debug(item_condition)
                    logging.debug(buyitnow)
                    logging.debug(shipping_price)
                    logging.debug(is_shippable)
                    logging.debug(highest_price)
                    logging.debug(nb_bids)
                    logging.debug(update_time)
                    logging.debug(end_time)
                    logging.debug("*******************************")


                    now_items.append(item_id)
                    if item_id not in self.cls.last_search_items:
                        # self.store_items_database(item_id, item_url, item_title, item_price, release_time, item_stadt)
                        # self.store_an_image(image_url, item_id)
                        self.cls.NEW_ITEM_NB += 1
                        logging.debug("New item id = {}".format(item_id))
                    else:
                        logging.debug("Existed item id = {}".format(item_id))
                except Exception as e:
                    logging.debug(e)
                    logging.debug(":::: I am continue, pass adding item: {}".format(item_url))
            self.cls.last_search_items = now_items

    # def store_items_database(self, item_id, item_url, item_title, item_price, release_time, item_stadt):
    #     if session.query(EKItem).filter_by(id=item_id).scalar() is None:
    #         # Commit new item into database, after all information exist
    #         new_item = EKItem(id=item_id, url = item_url, title=item_title, price=item_price, release_time=release_time, stadt=item_stadt)
    #         zero_count = EKViewCount(h4=-1, d1=-1, d3=-1, d5=-1, d7=-1, d10=-1, d14=-1, d28=-1, item_id=item_id,\
    #                                 next_count_time=release_time + timedelta(hours=4), \
    #                                 release_time=release_time)
    #         # new_monitoring_item = EKMonitoringItem(item_id=int(item_id), next_count_time=release_time, count_duration=0)
    #         session.add(new_item)
    #         session.add(zero_count)
    #         session.commit()
    #     logging.info("::::SUCCESSFUL Store new item and monitoring item into database.")

    

    # def store_an_image(self, image_url, item_id):
    #     # Asynchronously download and store images
    #     if image_url.endswith('35.JPG'): # magic name for not None image
    #         storage_folder = os.path.join(IMAGE_FOLDER, str(item_id))
    #         Path(storage_folder).mkdir(parents=True, exist_ok=True)
    #         try:
    #             filename = os.path.join(storage_folder, "{}_.jpg".format(item_id))
    #             _download_image(image_url, filename)
    #         except Exception as e:
    #             logging.debug(e)
    #             logging.debug(":::: Download IMAGES UNSUCCESSFUL")
    #         logging.debug("::::Finish downloading images of {}!".format(item_id))