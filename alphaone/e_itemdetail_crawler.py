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
import imgkit
import re

# from ek_orm import EKItem, EKUser, session

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
    ITEM_REQUEST_NB = 0
    lasttime = None
    MAX_BUFFER_ITEMS = 20
    buffer_items = []

    @classmethod
    def is_next(cls):
        logging.debug("Last time ITEM DETAIL called: {}".format(cls.lasttime))
        return True
        # if cls.buffer_items:
        #     return True
        # else:
        #     cls.update_buffer_items()
        #     if cls.buffer_items:
        #         return True
        #     else:
        #         return False 
    @classmethod
    def update_buffer_items(cls):
        # # Get all items need to update now
        # updating_items = session.query(EKItem).\
        #                             filter(EKItem.seller_id == None).\
        #                             limit(cls.MAX_BUFFER_ITEMS)
        # cls.buffer_items = updating_items.all()
        pass

    def __init__(self, headers=None):
        self.headers = headers or HEADERS
        self.cls = ItemDetailCrawler

    def _extract_payments(self, doc):
        payments = doc.find('div', {'class': 'app-payments-btf-wrapper__paymentmethod'})
        payments = payments.find_all('span')[::2]
        payments = [p.text for p in payments]
        return payments

    def _extract_location(self, doc):
        location = doc.find('div', {'class': 'app-location-wrapper'})
        location = location.find('div', {'class': 'cc-textblock'}).text
        return location
    
    def _extract_info(self, doc):
        info = doc.find('div', {'class': 'app-chevron-wrapper__wrapper row'})
        info = info.find_all('span')[::2]
        info = [i.text for i in info]
        info = [info[i*2] + ": " + info[i*2+1] for i in range(len(info) // 2)]
        return info
    
    def _extract_seller_name(self, doc):
        seller_name = doc.find('span', {'class': 'app-sellerpresence__sellername'}).text
        return seller_name
    
    def _extract_images(self, doc):
        image_urls = doc.find_all('script')
        image_urls = image_urls[-1].contents[-1]
        m = re.findall('"originalSize":{"height":400,"width":400},"URL":"https://i.ebayimg.com/images(.+?)"}', image_urls)
        image_urls = ["https://i.ebayimg.com/images" + m[i] for i in range(len(m)//2)]
        return image_urls, len(image_urls)
    
    def _extract_description(self, doc):
        description = doc.find('div', {"class": 'app-item-description__body cc-stdmargin__top--half'})
        description = description.find('span', {"class": "app-item-description__body--text"})
        description = description.text
        return description
    
    def _extract_detail_description(self, doc, item_id, saving=True):
        detail_description = doc.find_all('script')
        detail_description = detail_description[-1].contents[-1]
        detail_description
        m = re.findall('"URL":"http://vi.raptor.ebaydesc.com/ws/eBayISAPI.dll(.+?)"}}', detail_description)
        if m:
            detail_description = "http://vi.raptor.ebaydesc.com/ws/eBayISAPI.dll" + m[0]
            if saving:
                storage_folder = os.path.join(IMAGE_FOLDER, str(item_id))
                Path(storage_folder).mkdir(parents=True, exist_ok=True)
                try:
                    filename = os.path.join(storage_folder, "{}_detail_description.jpg".format(item_id))
                    imgkit.from_url(detail_description, filename)
                except:
                    logging.debug(":::::: Save detail description UNSUCCESSFUL :::::: {}".format(item_id))
        return detail_description

    def execute_request(self, item_url, item_id):
        try:
            response = requests.get(item_url, headers=self.headers)
            if response.status_code != 200:
                logging.debug(":::: Query ITEM DETAIL UNSUCCESSFUL:::: Code={}".format((response.status_code)))
                return [None, None, None, None, None, None, None, None]
            # _save_html(response, "test.html")
            page = response.text
            doc = soup(page, "html.parser")
            payments = self._extract_payments(doc)
            location = self._extract_location(doc)
            info = self._extract_info(doc)
            seller_name = self._extract_seller_name(doc)
            image_urls, nb_images = self._extract_images(doc)
            description = self._extract_description(doc)
            detail_description = self._extract_detail_description(doc, item_id)
            # TODO: extract buyitnow price when the option available. Not now.

            logging.debug(":::: Finish query item detail SUCCESSFUL: {}".format(item_url))
            return payments, location, info, seller_name, image_urls, nb_images, description, detail_description
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

    def run(self):
        self.cls.ITEM_REQUEST_NB += 1
        logging.info("Running ITEM DETAIL crawler ...")
        # if len(self.cls.buffer_items) > 0:
        if True:
            # item = self.cls.buffer_items.pop(0)
            # item_url = "https://www.ebay.de/itm/HP-OfficeJet-Pro-8210-Tintenstrahldrucker-Drucker-LAN-WLAN-Duplex-HP-I/264839280978?epid=2254414883&hash=item3da9a6b952%3Ag%3AKLoAAOSwbW9fP3MZ&LH_Auction=1"
            # item_id = str(264839280978)
            item_url = "https://www.ebay.de/itm/Apple-Mac-mini-7-1-i5-2-8-GHz-8-GB-RAM-1-TB-SSD/224135625477?hash=item342f863b05:g:6r4AAOSw0qFfR9Fp"
            item_id = str(224135625477)
            payments, location, info, seller_name, image_urls, nb_images, description, detail_description = self.execute_request(item_url, item_id)

            logging.debug(payments)
            logging.debug(location)
            logging.debug(info)
            logging.debug(seller_name)
            logging.debug(image_urls)
            logging.debug(nb_images)
            logging.debug(description)
            logging.debug(detail_description)
            logging.debug("*******************************")

            self.cls.lasttime = datetime.now()
            
            if seller_name: # if execute request not return None
                # item.item_category = item_category
                # item.item_subcategory = item_subcategory
                # item.item_description = item_description
                # item.image_nb = image_nb
                # item.seller_id = seller_id
                self.store_images(image_urls, item_id)
                # Get user information
                # if session.query(EKUser).filter_by(id=seller_id).scalar() is None:
                #     seller_address = item.stadt
                #     new_user = EKUser(id=seller_id, name=seller_name, address=seller_address)
                #     session.add(new_user)
                # session.commit()    # both Update item detail and add user
                # logging.info("::::SUCCESSFUL Store new item detail and user into database.")
        else:
            logging.debug(":::::WARNING: Count item buffer is empty while is_next return True:::::")
