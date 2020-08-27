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

from ek_orm import EKItem, EKUser, session

IMAGE_FOLDER = "images"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 13_2_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.0.3 Mobile/15E148 Safari/604.1',
    'Connection' : 'keep-alive',
    'Cache-Control' : 'max-age=0',
    'Upgrade-Insecure-Requests' : '1',
    'Accept' : 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
    'Accept-Encoding' : 'gzip, deflate, br',
    'Accept-Language' : 'en-US,en;q=0.9,vi;q=0.8',
    }

def _download_image(img_url, dest):
    response = requests.get(img_url)
    MAX_SIZE = 256, 256
    img = Image.open(BytesIO(response.content))
    img = img.convert("RGB") # to solve OSError: cannot write mode RGBA as JPEG
    img.thumbnail(MAX_SIZE, Image.ANTIALIAS)
    img.save(dest)

def _save_html(response, name):
    with open(name, "wb") as f: 
        # Writing data to a file 
        f.write(response.content)

class ItemUrlException(Exception):
    """Raised when access item url failed"""
    def __init__(self, message=""):
        self.message = message
    def __str__(self):
        return ":::::::::::: Execute item detail crawler UNSUCCESSFUL :::::::::::: {}".format(self.message)

class ItemDetailCrawler():
    """ Crawl item detail information
    """
    lasttime = None
    MAX_BUFFER_ITEMS = 2
    buffer_items = []

    @classmethod
    def is_next(cls):
        logging.debug("Last time ITEM DETAIL called: {}".format(cls.lasttime))
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
        # Get all items need to count now
        updating_items = session.query(EKItem).\
                                    filter(EKItem.seller_id == None).\
                                    limit(cls.MAX_BUFFER_ITEMS)
        cls.buffer_items = updating_items.all()

    def __init__(self, headers=None):
        self.headers = headers or HEADERS
        self.cls = ItemDetailCrawler

    def _extract_item_image_urls(self, item_doc):
        ul = item_doc.find('ul', {'id': 'vip-ad-picture-list'})
        if ul:
            return ul.findAll('li', {'class':'imagegallery--item'})
        else:
            return []

    def _extract_item_description(self, item_doc):
        return item_doc.find('p', {'class':'ad-keydetails--ad-description'}).text

    def execute_request(self, item_url):
        try:
            response = requests.get(item_url, headers=self.headers)
            if response.status_code != 200:
                logging.debug(":::: Query ITEM DETAIL UNSUCCESSFUL:::: Code={}".format((response.status_code)))
                return None
            _save_html(response, "test.html")
            page = response.text
            doc = soup(page, "html.parser")
            javascript = doc.find('script',{'type':'text/javascript'})
            javascript = javascript.contents[0].split("\n")
            seller_id = ''.join(filter(str.isdigit, javascript[9]))   # magic number 9
            item_category = javascript[36].split("\"")[-2]            # magic number 36
            item_subcategory = javascript[37].split("\"")[-2]         # magic number 37
            item_description = self._extract_item_description(doc)
            item_images = self._extract_item_image_urls(doc)
            image_nb = len(item_images)
            image_urls = [ii.find('img').attrs['src'] for ii in item_images]
            seller_name = doc.find('h2', {'class':'userprofile-teaser--title'}).text
            
            logging.debug(":::: Finish query item detail SUCCESSFUL: {}".format(item_url))
            return item_category, item_subcategory, item_description, image_nb, image_urls, seller_id, seller_name
        except Exception as e:
            print(e)
            raise ItemUrlException(message=item_url)
    
    def store_images(self, image_urls, item_id):
        # Asynchronously download and store images
        storage_folder = os.path.join(IMAGE_FOLDER, str(item_id))
        Path(storage_folder).mkdir(parents=True, exist_ok=True)
        threads = []
        try:
            for k,img_url in enumerate(image_urls):
                filename = os.path.join(storage_folder, "{}_{}.jpg".format(item_id, k))
                t = threading.Thread(target=_download_image, args=(img_url, filename))
                t.start()
                threads.append(t)
            # wait for all threads to finish
            # You can continue doing whatever you want and
            # join the threads when you finally need the results.
            # They will fatch your urls in the background without
            # blocking your main application.
            for t in threads:
                t.join()
        except Exception as e:
            logging.debug(e)
            logging.debug(":::: Download IMAGES UNSUCCESSFUL")
        logging.info("::::Finish downloading images of {}!".format(item_id))
        logging.info("***********************************************")

    def run(self):
        logging.info("Running ITEM DETAIL crawler ...")
        if len(self.cls.buffer_items) > 0:
            item = self.cls.buffer_items.pop(0)
            item_category, item_subcategory, item_description, image_nb, image_urls, seller_id, seller_name = self.execute_request(item.url)
            self.cls.lasttime = datetime.now()
            item.item_category = item_category
            item.item_subcategory = item_subcategory
            item.item_description = item_description
            item.image_nb = image_nb
            item.seller_id = seller_id
            self.store_images(image_urls, item.id)
            # Get user information
            if session.query(EKUser).filter_by(id=seller_id).scalar() is None:
                seller_address = item.stadt
                new_user = EKUser(id=seller_id, name=seller_name, address=seller_address)
                session.add(new_user)
            session.commit()    # both Update item detail and add user
            logging.info("::::SUCCESSFUL Store new item detail and user into database.")

        else:
            logging.debug(":::::WARNING: Count item buffer is empty while is_next return True:::::")
