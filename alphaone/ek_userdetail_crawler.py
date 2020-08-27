import logging
from datetime import datetime
from datetime import timedelta
import requests
from bs4 import BeautifulSoup as soup

from ek_orm import EKUser, session


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

class UserUrlException(Exception):
    """Raised when access user detail url failed"""
    def __init__(self, message=""):
        self.message = message
    def __str__(self):
        return ":::::::::::: Execute user detail crawler UNSUCCESSFUL :::::::::::: {}".format(self.message)

class UserDetailCrawler():
    """ Crawl user detail information
    """
    lasttime = None
    MAX_BUFFER_ITEMS = 5
    buffer_items = []

    @classmethod
    def is_next(cls):
        logging.debug("Last time USER DETAIL called: {}".format(cls.lasttime))
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
        # Get all user need to update now
        updating_items = session.query(EKUser).\
                                    filter(EKUser.active_date == None).\
                                    limit(cls.MAX_BUFFER_ITEMS)
        cls.buffer_items = updating_items.all()

    def __init__(self, headers=None):
        self.headers = headers or HEADERS
        self.cls = UserDetailCrawler

    
    def execute_request(self, seller_id):
        seller_url = "https://m.ebay-kleinanzeigen.de/s-anzeigen/deutschland/c0-l0?userIds={}".format(seller_id)
        try:
            response = requests.get(seller_url, headers=self.headers)
            if response.status_code != 200:
                logging.debug(":::: Query USER DETAIL UNSUCCESSFUL:::: Code={}".format((response.status_code)))
                return None
            page = response.text
            doc = soup(page, "html.parser")
            # seller_name = doc.find('h2',{'class': 'userprofile--title'}).text
            seller_active_date = doc.find('span',{'class': 'userprofile--usersince'}).text
            seller_active_date = ''.join(c for c in seller_active_date if is_digit_or_point(c))
            seller_active_date = datetime.strptime(seller_active_date, '%d.%m.%Y').date()
            logging.debug(":::: Finish query user detail SUCCESSFUL: {}".format(seller_url))
            return seller_active_date
        except Exception as e:
            print(e)
            raise UserUrlException(message=seller_url)
    
    def run(self):
        logging.info("Running USER DETAIL crawler ...")
        if len(self.cls.buffer_items) > 0:
            seller = self.cls.buffer_items.pop(0)
            seller_active_date = self.execute_request(seller.id)
            self.cls.lasttime = datetime.now()
            if seller_active_date:
                seller.active_date = seller_active_date
            session.commit()    # Update user
            logging.info("::::SUCCESSFUL Store new user detail into database.")
        else:
            logging.debug(":::::WARNING: Count item buffer is empty while is_next return True:::::")

