import daemon
import time
import lockfile

import sys
import argparse
import os
import requests
from bs4 import BeautifulSoup as soup
import os.path
import json
from datetime import datetime
from datetime import timedelta

# https://api.slack.com/apps/APSE1SZPZ/incoming-webhooks?
class SlackNotifier():
    def __init__(self, url, interval_in_s):
        self.slack_hook_url = url
        self.tdelta = timedelta(seconds=interval_in_s)
        self.lasttime = {}
    def call(self, Id, message, forced=False):
        if forced:
            requests.post(self.slack_hook_url, json={"text":message})
            self.lasttime[Id] = datetime.now()
        elif not self.is_just_called(Id):
            requests.post(self.slack_hook_url, json={"text":message})
            self.lasttime[Id] = datetime.now()
    def is_just_called(self, Id):
        if not self.lasttime:
            return False
        elif Id in self.lasttime.keys():
            return datetime.now() < self.lasttime[Id] + self.tdelta        
        else:
            return False

notifier = SlackNotifier(os.environ['SLACK_HOOK_URL'], 60*4)

def notify_slack(message):
    """Deprecated"""
    slack_hook_url = os.environ['SLACK_HOOK_URL']
    requests.post(slack_hook_url, json={"text":message})

def extract_today_created_time(item_time):
    if "Heute" in item_time:
        index = item_time.find("Heute,")
        created_hours = int(item_time[index+7:index + 9])
        created_minutes = int(item_time[index+10:index + 12])
        return True, timedelta(hours=created_hours, minutes=created_minutes)
    else:
        return False, item_time.replace("\n","").replace(" ","")
    
def is_new(created_time, interval_in_s=240):
    """ Post can be updated later in 3 minutes => use default interval is 4' = 240"
    """
    tdelta = timedelta(seconds=int(interval_in_s))
    now_hours = datetime.now().hour
    now_minutes = datetime.now().minute
    now_seconds = datetime.now().second
    now = timedelta(hours=now_hours, minutes=now_minutes, seconds=now_seconds)
    return now < created_time + tdelta

def update_log(message):
    with open("/tmp/ebay_kleinanzeigen_daemon_log.txt", "a") as f:
        f.write(message)

if __name__ == "__main__":
    action = "start"
    with open("/tmp/ebay-kleinanzeigen.pid", "w") as f:
        f.write(str(os.getpid()) + "\n")
    
    lat = "48.1151649"
    lng = "11.6981558"
    queries = ["ikea skarsta", "bose revolve", "glasbild"]
    queries = ["+".join(query.split(" ")) for query in queries]
    distances = [20, 20, 20] # in km
    maxprices = [110, 110, 30] # in km
    page_num = 0
    interval_in_s = 30

    assert len(distances) == len(queries), "Number of queries and distance is different."
    assert len(queries) == len(maxprices), "Number of queries and maxprice is different."

    # Get locationID code from ebay-kleinanzeigen
    url_for_location_id = "https://m.ebay-kleinanzeigen.de/s-ort-vorschlag.json?lat="+ lat + "&lng=" + lng
    result = requests.get(url_for_location_id)
    page = result.text
    locationId = json.loads(page)[0]['id']

    while True:
        start = time.time()
        for i, query in enumerate(queries):
            dist = distances[i]
            maxprice = maxprices[i]
            url = "https://m.ebay-kleinanzeigen.de/s-suche-veraendern?locationId=" + str(locationId) + \
            "&distance=" + str(dist) + \
            "&categoryId=&minPrice=&maxPrice=" + str(maxprice) + \
            "&adType=&posterType="+ \
            "&q=" + query
            # print(url)
            result = requests.get(url)
            page = result.text
            doc = soup(page, "html.parser")
            links = [element.get('content') for element in doc.find_all('meta')]
            link = links[6]
            link0, link1 = link.split("distance")
            url = link0 + "page=" + str(page_num) + "&distance" + link1

            result = requests.get(url)
            page = result.text
            doc = soup(page, "html.parser")
            items = [element for element in doc.find_all('div', {"class": "adlist--item--descarea"})]

            if len(items) > 0:
                item = items[0] # get last item
                item_time = item.find('div', {"class": "adlist--item--info--date"}).contents[0]
                is_today, created_time = extract_today_created_time(item_time)
                if is_today:
                # if True:
                    if is_new(created_time):
                    # if True:
                        notifier.call(i, "FOR EBAY-KLEINANZEIGEN: new {}".format(query.upper()))
                        update_log("SEND NOTIFICATION!")
                    update_log("Last item for {} checked at {} in distance {} km is posted TODAY at: {}\n" \
                                .format(query.upper(), datetime.now(), dist, str(created_time)))
                else:
                    update_log("Last item for {} checked at {} in distance {} km is posted at: {}\n" \
                                .format(query.upper(), datetime.now(), dist, str(created_time)))
            else:
                update_log("NO ITEM FOUND for {} checked at {} in distance {} km.\n" \
                                .format(query.upper(), datetime.now(), dist))
        update_log("\n")
        processing_time = time.time() - start
        time.sleep(max(0.01, interval_in_s - processing_time))