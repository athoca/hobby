# run periodic actions without time drifting
import requests
from bs4 import BeautifulSoup as soup
import os.path
import os
import json
from datetime import datetime
from datetime import timedelta
import os
import time
from PIL import Image
from io import BytesIO
from pathlib import Path
import threading

from ek_orm import EKMonitoringItem, session


IMAGE_FOLDER = "images"

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


def _query_items():
    search_url = "https://m.ebay-kleinanzeigen.de/s-anzeigen/multimedia-elektronik-80331/c161-l6443?distance=100"
    response = requests.get(search_url, headers=headers)
    page = response.text
    doc = soup(page, "html.parser")
    items = [element for element in doc.find_all('li', {"class": "j-adlistitem adlist--item"})]
    return items

def _extract_item_url(item):
    orign_url = "https://m.ebay-kleinanzeigen.de"
    return orign_url + item.attrs['data-href']

def _extract_item_id(item):
    return item.attrs['data-adid']

def _extract_item_stadt(item):
    # extract item_stadt
    div = item.find('div', {"class": "adlist--item--info--location"}).contents
    if len(div) == 1:
        item_stadt = div[0].strip()
    else:
        item_stadt = 'Deutschland'
    return item_stadt

def _extract_item_release_time(item):
    # div = item.find('div', {"class": "adlist--item--info--date"}).contents
    # if len(div) == 1:
    #     release_time = div[0].split(',')[-1].strip()
    #     datetime.strptime(release_time, '%H:%M')
    #     # TODO: add day, month and year
    # else:
    #     release_time = datetime.now()

    # set release_time = now() => good enough, simple logic when 23:99 => 0:00
    release_time = datetime.now() # utcnow or now?
    return release_time

def _extract_item_title(item):
    return item.find('a').text

def _extract_item_price(item):
    item_price = item.find('div', {"class": "adlist--item--price"}).text
    item_price = ''.join(filter(str.isdigit, item_price))   # keep only numerical price
    if not item_price:
        item_price = -1.0 # not specified
    return item_price 

def _extract_item_image_urls(item_doc):
    ul = item_doc.find('ul', {'id': 'vip-ad-picture-list'})
    if ul:
        return ul.findAll('li', {'class':'imagegallery--item'})
    else:
        return []

def _extract_item_description(item_doc):
    return item_doc.find('p', {'class':'ad-keydetails--ad-description'}).text

def _query_item_detail(item_url):
    response = requests.get(item_url, headers=headers)
    page = response.text
    doc = soup(page, "html.parser")
    javascript = doc.find('script',{'type':'text/javascript'})
    javascript = javascript.contents[0].split("\n")
    seller_id = ''.join(filter(str.isdigit, javascript[9]))   # magic number 9
    item_category = javascript[36].split("\"")[-2]            # magic number 36
    item_subcategory = javascript[37].split("\"")[-2]         # magic number 37
    item_description = _extract_item_description(doc)
    item_images = _extract_item_image_urls(doc)
    image_nb = len(item_images)
    image_urls = [ii.find('img').attrs['src'] for ii in item_images]
    return item_category, item_subcategory, item_description, image_nb, image_urls, seller_id

    


def crawl_items():
    items = _query_items()
    if len(items) > 0:
        n = min(2, len(items)-1)
        for item in items[:n]:
            item_url = _extract_item_url(item)
            item_id = _extract_item_id(item)
            # TODO: if item_id exists, stop here
            item_stadt = _extract_item_stadt(item)
            release_time = _extract_item_release_time(item)
            item_title = _extract_item_title(item)
            item_price = _extract_item_price(item)

            print(item_url)
            print(item_id)
            print(release_time)
            print(item_stadt)
            print(item_title)
            print(item_price)

            item_category, item_subcategory, item_description, \
            image_nb, image_urls, seller_id = _query_item_detail(item_url)

            print(item_category)
            print(item_subcategory)
            print(item_description)
            print(image_nb)
            print(image_urls)
            print(seller_id)
            print("\n")
            #TODO: skip next steps if if any exception.

            # Asynchronously download and store images
            storage_folder = os.path.join(IMAGE_FOLDER, item_id)
            Path(storage_folder).mkdir(parents=True, exist_ok=True)
            threads = []
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
            map(lambda t: t.join(), threads)
            print("Finish downloading images!")
            print("\n")

            # Get user information
            seller_url = "https://m.ebay-kleinanzeigen.de/s-anzeigen/deutschland/c0-l0?userIds={}".format(seller_id)
            response = requests.get(seller_url, headers=headers)
            page = response.text
            doc = soup(page, "html.parser")
            seller_name = doc.find('h2',{'class': 'userprofile--title'}).text
            seller_address = item_stadt
            seller_active_date = doc.find('span',{'class': 'userprofile--usersince'}).text
            seller_active_date = ''.join(c for c in seller_active_date if is_digit_or_point(c))
            print(seller_name)
            print(seller_address)
            print(seller_active_date)

            new_monitoring_item = EKMonitoringItem(item_id=int(item_id), seller_id=int(seller_id), \
                next_count_time=release_time, count_duration=0)
            session.add(new_monitoring_item)
            session.commit()
            print("store new monitoring item.")
            print("***********************************************")
            


def is_digit_or_point(c):
    return c.isdigit() or c=='.'

def _download_image(img_url, dest):
    response = requests.get(img_url)
    MAX_SIZE = 256, 256
    img = Image.open(BytesIO(response.content))
    img.thumbnail(MAX_SIZE, Image.ANTIALIAS)
    img.save(dest)

if __name__ == "__main__":
    while True:
        crawl_items()
        crawl_next_call = crawl_next_call+60
        sleep_duration = max(crawl_next_call - time.time(), 0.01)
        time.sleep(sleep_duration)
