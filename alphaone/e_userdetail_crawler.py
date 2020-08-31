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
    USER_REQUEST_NB = 0
    lasttime = None
    MAX_BUFFER_ITEMS = 5
    buffer_items = []

    @classmethod
    def is_next(cls):
        logging.debug("Last time USER DETAIL called: {}".format(cls.lasttime))
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
        # # Get all user need to update now
        # updating_items = session.query(EKUser).\
        #                             filter(EKUser.active_date == None).\
        #                             limit(cls.MAX_BUFFER_ITEMS)
        # cls.buffer_items = updating_items.all()
        pass

    def __init__(self, headers=None):
        self.headers = headers or HEADERS
        self.cls = UserDetailCrawler

    def _extract_feedback_score(self, doc):
        feedback_score = doc.find('div',{'class':'mbg'})
        feedback_score = feedback_score.find_all('a')
        feedback_score = feedback_score[-1]
        feedback_score = feedback_score.contents[-1]
        return feedback_score
    
    def _extract_feedback_percentage(self, doc):
        feedback_percentage = doc.find('div', {'class': 'perctg'})
        feedback_percentage = feedback_percentage.text.strip()
        return feedback_percentage
    
    def _extract_registered_since(self, doc):
        registered_since = doc.find('h2', {'class': 'bio inline_value'})
        registered_since = registered_since.text.strip()
        # TODO: seperate location and time
        return registered_since
        
    def _extract_feedback_ratings(self, doc):
        feedback_ratings = doc.find('div', {'id': 'feedback_ratings'})
        feedback_ratings = feedback_ratings.find_all('span', {'class': 'num'})
        feedback_ratings = [f.text for f in feedback_ratings]
        return feedback_ratings
    
    def execute_request(self, seller_id):
        user_url = "https://www.ebay.de/usr/{}".format(seller_id)
        try:
            response = requests.get(user_url, headers=self.headers)
            if response.status_code != 200:
                logging.debug(":::: Query USER DETAIL UNSUCCESSFUL:::: Code={}".format((response.status_code)))
                return None, None, None, None, None, None
            page = response.text
            doc = soup(page, "html.parser")
            feedback_score = self._extract_feedback_score(doc)
            feedback_percentage = self._extract_feedback_percentage(doc)
            registered_since = self._extract_registered_since(doc)
            positive, neutral, negative = self._extract_feedback_ratings(doc)

            logging.debug(":::: Finish query user detail SUCCESSFUL: {}".format(user_url))
            return feedback_score, feedback_percentage, registered_since, positive, neutral, negative
        except Exception as e:
            print(e)
            raise UserUrlException(message=user_url)
    
    def run(self):
        self.cls.USER_REQUEST_NB += 1
        logging.info("Running USER DETAIL crawler ...")
        # if len(self.cls.buffer_items) > 0:
        if True:
            # seller = self.cls.buffer_items.pop(0)
            seller_id = "44190"
            feedback_score, feedback_percentage, registered_since, positive, neutral, negative = self.execute_request(seller_id)
            self.cls.lasttime = datetime.now()

            logging.debug(feedback_score)
            logging.debug(feedback_percentage)
            logging.debug(registered_since)
            logging.debug(positive)
            logging.debug(neutral)
            logging.debug(negative)

            # if seller_active_date:
            #     seller.active_date = seller_active_date
            #     session.commit()    # Update user
            #     logging.info("::::SUCCESSFUL Store new user detail into database.")
        else:
            logging.debug(":::::WARNING: Count item buffer is empty while is_next return True:::::")

