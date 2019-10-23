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
from slackclient import SlackClient

# !pip install slackclient==1.3.2
# token for authentication to send message to slack. You can take it from here: https://api.slack.com/docs/oauth-test-tokens
token = "xoxp-489547421814-487977512340-792097758835-855563dc0df2666b9fc7dfc188180713"
# channel of slack you want to send message
channel = "ebay"
# name of the Notifier you want to set. This username will be the sender's name in slack
username = "automator"
slack_notifier = SlackClient(token)

def extract_today_created_time(item_time):
    if "Heute" in item_time:
        index = item_time.find("Heute,")
        created_hours = int(item_time[index+7:index + 9])
        created_minutes = int(item_time[index+10:index + 12])
        return timedelta(hours=created_hours, minutes=created_minutes)
    else:
        return False
    
def is_new(created_time, delta = 1):
    tdelta = timedelta(minutes=int(delta)) # in minute
    now_hours = datetime.now().hour
    now_minutes = datetime.now().minute
    now = timedelta(hours=now_hours, minutes=now_minutes)
    return now < created_time + tdelta


def do_something():
    lat = "48.1151649"
    lng = "11.6981558"
    queries = ["ikea skarsta", "bose revolve"]
    queries = ["+".join(query.split(" ")) for query in queries]
    distances = [20, 1000] # in km
    page_num = 0
    tdelta = 1
    assert len(distances) == len(queries), "Number of queries and distance is different."

    # Get locationID code from ebay-kleinanzeigen
    url_for_location_id = "https://m.ebay-kleinanzeigen.de/s-ort-vorschlag.json?lat="+ lat + "&lng=" + lng
    result = requests.get(url_for_location_id)
    page = result.text
    locationId = json.loads(page)[0]['id']

    while True:
        for i, query in enumerate(queries):
            dist = distances[i]
            url = "https://m.ebay-kleinanzeigen.de/s-suche-veraendern?locationId=" + str(locationId) + \
            "&distance=" + str(dist) + \
            "&categoryId=&minPrice=&maxPrice=&adType=&posterType="+ \
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
                created_time = extract_today_created_time(item_time)
                if created_time:
                    if is_new(created_time, tdelta):
                        attachments = [{}]
                        attachments[0]['color'] = "good"
                        attachments[0]['title'] = "NEW {}".format(query.upper())
                        attachments[0]['text'] = "Post at {}".format(created_time)
                        slack_notifier.api_call('chat.postMessage', channel=channel, attachments=attachments, username=username)

            with open("/tmp/ebay_kleinanzeigen_daemon_log.txt", "a") as f:
                f.write("TODAY Last item for {} checked at {} in distance {} km is posted at: {}\n" \
                        .format(query.upper(), datetime.now(), dist, str(created_time)))
        time.sleep(tdelta*60)

def run():
    with daemon.DaemonContext(pidfile=lockfile.FileLock('/tmp/ebay-kleinanzeigen.pid')):
    # with daemon.DaemonContext():
        with open("/tmp/ebay-kleinanzeigen.pid", "w") as f:
            f.write(str(os.getpid()) + "\n")
        do_something()

if __name__ == "__main__":
    action = "start"
    if len(sys.argv) > 1:
        if sys.argv[1] in ['start', 'stop']:
            action = sys.argv[1]

    if action == "start":
        run()
    elif action == "stop":
        if os.path.exists("/tmp/ebay-kleinanzeigen.pid"):
            with open("/tmp/ebay-kleinanzeigen.pid", "r") as f:
                current_pid = f.readline()
                current_pid = current_pid.split("\n")[0]
                kill_syntax = "kill -9 {}".format(current_pid)
                os.system(kill_syntax)
                if os.path.exists("/tmp/ebay-kleinanzeigen.pid.lock"):
                    os.remove("/tmp/ebay-kleinanzeigen.pid.lock")