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
def notify_slack(message):
    slack_hook_url = "https://hooks.slack.com/services/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"
    requests.post(slack_hook_url, json={"text":message})

def extract_today_created_time(item_time):
    if "Heute" in item_time:
        index = item_time.find("Heute,")
        created_hours = int(item_time[index+7:index + 9])
        created_minutes = int(item_time[index+10:index + 12])
        return True, timedelta(hours=created_hours, minutes=created_minutes)
    else:
        return False, item_time.replace("\n","").replace(" ","")
    
def is_new(created_time, interval_in_s):
    tdelta = timedelta(seconds=int(interval_in_s))
    epsilon = timedelta(seconds=int(interval_in_s/5))
    now_hours = datetime.now().hour
    now_minutes = datetime.now().minute
    now = timedelta(hours=now_hours, minutes=now_minutes)
    return now < created_time + tdelta + epsilon

def update_log(message):
    with open("/tmp/ebay_kleinanzeigen_daemon_log.txt", "a") as f:
        f.write(message)

def do_something():
    lat = "48.1151649"
    lng = "11.6981558"
    queries = ["ikea skarsta", "bose revolve"]
    queries = ["+".join(query.split(" ")) for query in queries]
    distances = [20, 1000] # in km
    page_num = 0
    interval_in_s = 30000
    assert len(distances) == len(queries), "Number of queries and distance is different."

    # Get locationID code from ebay-kleinanzeigen
    url_for_location_id = "https://m.ebay-kleinanzeigen.de/s-ort-vorschlag.json?lat="+ lat + "&lng=" + lng
    result = requests.get(url_for_location_id)
    page = result.text
    locationId = json.loads(page)[0]['id']

    while True:
        start = time.time()
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
                is_today, created_time = extract_today_created_time(item_time)
                if is_today:
                    if is_new(created_time, interval_in_s):
                        notify_slack("FOR EBAY-KLEINANZEIGEN: new {}".format(query.upper()))
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