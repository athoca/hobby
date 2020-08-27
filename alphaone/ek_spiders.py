import logging
logging.basicConfig(level=logging.DEBUG)

import time
import json
import time

from ek_search_crawler import SearchCrawler
from ek_count_crawler import CountCrawler


CRAWL_FREQUENCE_IN_SECONDS = 5
crawl_next_call = time.time()

def get_next_crawler():
    with open("crawler_config.json") as json_data_file:
        crawler_config = json.load(json_data_file)
        # print(crawler_config)
        if crawler_config['search'] and SearchCrawler.is_next():
            return SearchCrawler()
        elif crawler_config['count'] and CountCrawler.is_next():
            return CountCrawler()
        elif crawler_config['item_detail']:
            return ItemDetailCrawler()
        # elif crawler_config['user_detail']:
        #     return UserDetailCrawler()
        # else:
        #     return DoNothingCrawler()


# import logging
# logging.basicConfig(level=logging.DEBUG)

# from datetime import datetime
# from datetime import timedelta
# import time
# import json
# import requests
# from bs4 import BeautifulSoup as soup

# from ek_orm import EKMonitoringItem, session
# from ek_orm import EKUser, EKItem







# class UserDetailCrawler():
#     def run(self):
#         status_code = 200
#         logging.info("Running USER DETAIL crawler ...")
#         return status_code

# class DoNothingCrawler(Crawler):
#     def run(self):
#         status_code = 200
#         logging.info("Running DO NOTHING crawler ...")
#         return status_code

if __name__ == "__main__":
    while True:
        crawler = get_next_crawler()
        status_code = crawler.run()
        # TODO: do something if status_code != 200
        crawl_next_call = crawl_next_call + CRAWL_FREQUENCE_IN_SECONDS
        sleep_duration = max(crawl_next_call - time.time(), 0.001)
        logging.debug("Time to next crawling turn = {}.".format(crawl_next_call - time.time()))
        time.sleep(sleep_duration)

# import os.path
# import os
# import json

# import os

# from PIL import Image
# from io import BytesIO
# from pathlib import Path
# import threading




# IMAGE_FOLDER = "images"

# ITEM_REQUEST_PAUSE_IN_SECONDS = 5


# class UserUrlException(Exception):
#     """Raised when the not found user url"""
#     def __init__(self, message=""):
#         self.message = message
#     def __str__(self):
#         return ":::::::::::: Query USER UNSUCCESSFUL :::::::::::: {}".format(self.message)













# 

# def _extract_item_image_urls(item_doc):
#     ul = item_doc.find('ul', {'id': 'vip-ad-picture-list'})
#     if ul:
#         return ul.findAll('li', {'class':'imagegallery--item'})
#     else:
#         return []

# def _extract_item_description(item_doc):
#     return item_doc.find('p', {'class':'ad-keydetails--ad-description'}).text

# def _query_item_detail(item_url, item_id=None):
#     try:
#         response = requests.get(item_url, headers=headers)
#         _save_item_html(response, item_id)
#         page = response.text
#         doc = soup(page, "html.parser")
#         javascript = doc.find('script',{'type':'text/javascript'})
#         javascript = javascript.contents[0].split("\n")
#         seller_id = ''.join(filter(str.isdigit, javascript[9]))   # magic number 9
#         item_category = javascript[36].split("\"")[-2]            # magic number 36
#         item_subcategory = javascript[37].split("\"")[-2]         # magic number 37
#         item_description = _extract_item_description(doc)
#         item_images = _extract_item_image_urls(doc)
#         image_nb = len(item_images)
#         image_urls = [ii.find('img').attrs['src'] for ii in item_images]
#         logging.debug(":::: Finish query items: {}".format(item_url))
#     except Exception as e:
#         print(e)
#         raise ItemUrlException(message=item_url)
#     return item_category, item_subcategory, item_description, image_nb, image_urls, seller_id

# def _save_item_html(response, item_id):
#     with open("itemhtml/"+str(item_id)+".html", "wb") as f: 
#         # Writing data to a file 
#         f.write(response.content)

# def _save_html(response, name):
#     with open(name, "wb") as f: 
#         # Writing data to a file 
#         f.write(response.content)


# def _query_user_detail(seller_id):
#     try:
#         seller_url = "https://m.ebay-kleinanzeigen.de/s-anzeigen/deutschland/c0-l0?userIds={}".format(seller_id)
#         response = requests.get(seller_url, headers=headers)
#         page = response.text
#         doc = soup(page, "html.parser")
#         seller_name = doc.find('h2',{'class': 'userprofile--title'}).text
#         seller_active_date = doc.find('span',{'class': 'userprofile--usersince'}).text
#         seller_active_date = ''.join(c for c in seller_active_date if is_digit_or_point(c))
#         seller_active_date = datetime.strptime(seller_active_date, '%d.%m.%Y').date()
#         logging.debug(":::: Finish query items: {}".format(seller_url))
#     except Exception as e:
#         print(e)
#         raise UserUrlException(message=seller_url)
#     return seller_name, seller_active_date

# lasttime_items = []
# thistime_items = []
# def crawl_items():
#     count = 0
#     global lasttime_items
#     global thistime_items
#     global access_denied_plus_in_second
#     logging.info("::::Start crawling...")
#     try:
#         lasttime_items = thistime_items
#         thistime_items = []
#         items = _query_items()
#         if len(items) > 0:
#             print(len(items))
#             print(lasttime_items)
#             # n = min(7, len(items)-1)
#             # logging.debug("Number of items after query: {}".format(n))
#             for k, item in enumerate(items[:]):
#                 # time.sleep(ITEM_REQUEST_PAUSE_IN_SECONDS)
#                 try:
#                     item_url = _extract_item_url(item)
#                     item_id = _extract_item_id(item)
#                     thistime_items.append(item_id)
#                     if item_id in lasttime_items:
#                         count += 1
#                         print("Item {} of order {} in last time".format(item_id, k))
#                     else:
#                         print("Item {} of order {} new".format(item_id, k))




#                     # if session.query(EKItem).filter_by(id=item_id).scalar() is None:
#                     #     item_stadt = _extract_item_stadt(item)
#                     #     release_time = _extract_item_release_time(item)
#                     #     item_title = _extract_item_title(item)
#                     #     item_price = _extract_item_price(item)
#                     #     logging.info(item_url)
#                     #     logging.info(item_id)
#                     #     logging.info(release_time)
#                     #     logging.info(item_stadt)
#                     #     logging.info(item_title)
#                     #     logging.info(item_price)

#                         # item_category, item_subcategory, item_description, \
#                         # image_nb, image_urls, seller_id = _query_item_detail(item_url, item_id)
#                         # logging.info(item_category)
#                         # logging.info(item_subcategory)
#                         # logging.info(item_description)
#                         # logging.info(image_nb)
#                         # logging.info(image_urls)
#                         # logging.info(seller_id)
#                         # logging.info("\n")

#                         # # Get user information
#                         # new_user = None
#                         # if session.query(EKUser).filter_by(id=seller_id).scalar() is None:
#                         #     seller_address = item_stadt
#                         #     seller_name, seller_active_date = _query_user_detail(seller_id)
#                         #     logging.info(seller_name)
#                         #     logging.info(seller_address)
#                         #     logging.info(seller_active_date)
#                         #     new_user = EKUser(id=seller_id, name=seller_name, address=seller_address, active_date=seller_active_date)
                        
#                         # # Commit new item into database, after all information exist
#                         # new_item = EKItem(id=item_id, title=item_title, price=item_price, \
#                         #     release_date=release_time, stadt=item_stadt, category=item_category, sub_category=item_subcategory, \
#                         #     description=item_description, image_nb=image_nb, seller_id=seller_id)
#                         # new_monitoring_item = EKMonitoringItem(item_id=int(item_id), seller_id=int(seller_id), \
#                         #     next_count_time=release_time, count_duration=0)
#                         # session.add(new_item)
#                         # session.add(new_monitoring_item)
#                         # if new_user:
#                         #     session.add(new_user)
#                         # session.commit()
#                         # logging.info("::::SUCCESSFUL Store new item, user and monitoring item into database.")

#                         # # Asynchronously download and store images
#                         # storage_folder = os.path.join(IMAGE_FOLDER, item_id)
#                         # Path(storage_folder).mkdir(parents=True, exist_ok=True)
#                         # threads = []
#                         # try:
#                         #     for k,img_url in enumerate(image_urls):
#                         #         filename = os.path.join(storage_folder, "{}_{}.jpg".format(item_id, k))
#                         #         t = threading.Thread(target=_download_image, args=(img_url, filename))
#                         #         t.start()
#                         #         threads.append(t)
#                         #     # wait for all threads to finish
#                         #     # You can continue doing whatever you want and
#                         #     # join the threads when you finally need the results.
#                         #     # They will fatch your urls in the background without
#                         #     # blocking your main application.
#                         #     for t in threads:
#                         #         t.join()
#                         # except Exception as e:
#                         #     logging.debug(":::: Download IMAGES UNSUCCESSFUL")
#                         #     raise e
#                         # # map(lambda t: t.join(), threads)
#                         # logging.info("::::Finish downloading images in {}!".format(release_time))
#                         # logging.info("***********************************************")
#                     # else:
#                     #     break
#                 except Exception as e:
#                     logging.debug(e)
#                     logging.debug(":::: I am continue, pass item: {}".format(item_url))
#             print("So items lap lai: {}".format(count))
#     except Exception as e:
#         logging.debug(e)
#         logging.debug(":::: I am continue, PASS A CRAWL TURN.")
#     logging.info("::::Finish a crawl turn.")
#     logging.info("**********************************************************************************************")

# def is_digit_or_point(c):
#     return c.isdigit() or c=='.'

# def _download_image(img_url, dest):
#     response = requests.get(img_url)
#     MAX_SIZE = 256, 256
#     img = Image.open(BytesIO(response.content))
#     img = img.convert("RGB") # to solve OSError: cannot write mode RGBA as JPEG
#     img.thumbnail(MAX_SIZE, Image.ANTIALIAS)
#     img.save(dest)

# if __name__ == "__main__":
#     while True:
#         crawl_items()
#         crawl_next_call = crawl_next_call + CRAWL_FREQUENCE_IN_SECONDS
#         sleep_duration = max(crawl_next_call - time.time(), 0.01)
#         logging.debug(crawl_next_call - time.time())
#         time.sleep(sleep_duration)
    

# # Add task update item detail and user after night time for items spider

# # # run count spider in day time, off in night time.