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
import ast

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

notifier = SlackNotifier(os.environ['SLACK_HOOK_URL'], 60*4) # send notification every 4'

def update_log(message):
    with open("/tmp/terminvereinbarung_log.txt", "a") as f:
        f.write(message)

# For other termines, e.g An- oder Ummeldung - Einzelperson
# TERMIN_URL = "https://www56.muenchen.de/termin/index.php?loc=BB"
# CASETYPES = 'CASETYPES[An- oder Ummeldung - Einzelperson]'
# ZONE = 'Termin Wartezone 1 P'

# For SCIF
TERMIN_URL = "https://www46.muenchen.de/termin/index.php?cts=1080627"
CASETYPES = 'CASETYPES[Aufenthaltserlaubnis Blaue Karte EU]'
ZONE = 'Termin Wartezone SCIF'

def check_KRV_SCIF_available_date(termin_url, casetypes, zone):
    available_date = None
    # Get information for KVR from
    # https://www46.muenchen.de/termin/index.php?cts=1080627"
    termin_url = termin_url
    
    # First call to get cookies and __ncforminfo
    headers1 = {
        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 11_0 like Mac OS X) AppleWebKit/604.1.38 (KHTML, like Gecko) Version/11.0 Mobile/15A372 Safari/604.1',
        'Connection' : 'keep-alive',
        'Cache-Control' : 'max-age=0',
        'Upgrade-Insecure-Requests' : '1',
        'Accept' : 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3',
        'Accept-Encoding' : 'gzip, deflate, br',
        'Accept-Language' : 'en-US,en;q=0.9,de;q=0.8,fr;q=0.7,vi;q=0.6',
        'Cookie' : '_et_coid=e32c2d08fe2aec5f79ee9875c9f20463'
    }
    r1 = requests.get(termin_url, headers=headers1)
    page = r1.content
    doc = soup(page, "html.parser")
    elements = doc.findAll('input', {"name": "__ncforminfo"})[0]
    if len(elements) == 0:
        return available_date
    element = elements[0]

    # Second call to get available dates
    data = {}
    data['step'] = 'WEB_APPOINT_SEARCH_BY_CASETYPES'
    data[casetypes] = '1'
    data['__ncforminfo'] = element['value']

    headers2 = {
        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 11_0 like Mac OS X) AppleWebKit/604.1.38 (KHTML, like Gecko) Version/11.0 Mobile/15A372 Safari/604.1',
        'Connection' : 'keep-alive',
        'Cache-Control' : 'max-age=0',
        'Upgrade-Insecure-Requests' : '1',
        'Accept' : 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3',
        'Accept-Encoding' : 'gzip, deflate, br',
        'Accept-Language' : 'en-US,en;q=0.9,de;q=0.8,fr;q=0.7,vi;q=0.6',
    }

    r2 = requests.post(termin_url, cookies=r1.cookies, headers=headers2, data=data)
    page = r2.content
    page = page.decode("utf-8")

    appoints_line = None
    for item in page.split("\n"):
        if "jsonAppoints" in item:
            appoints_line = item.strip()
            break
    if appoints_line is None:
        return available_date

    right = appoints_line.find('{')
    left = appoints_line.rfind('}')
    appoints = ast.literal_eval(appoints_line[right:left+1])
    
    appoints_dates = appoints[zone]['appoints']
    for key in appoints_dates.keys():
        if len(appoints_dates[key]) > 0:
            available_date = key
            break
    return available_date

def do_something():
    interval_in_s = 15 # check every 15s
    while True:
        try:
            start = time.time()
            available_date = check_KRV_SCIF_available_date(TERMIN_URL, CASETYPES, ZONE)
            if available_date is not None:
                notifier.call(0, "FOR KVR RESIDENCE PERMIT: new available date {}." \
                                    .format(str(available_date)))
                update_log("SEND NOTIFICATION!")
            update_log("Last check at {}, available date is {}\n" \
                                    .format(datetime.now(), str(available_date)))

            # update_log("\n")
            processing_time = time.time() - start
            time.sleep(max(0.01, interval_in_s - processing_time))
        except:
            update_log("TRY CATCH EXCEPTION checked at {} \n".format(datetime.now()))

def run():
    with daemon.DaemonContext(pidfile=lockfile.FileLock('/tmp/terminvereinbarung.pid')):
    # with daemon.DaemonContext():
        with open("/tmp/terminvereinbarung.pid", "w") as f:
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
        if os.path.exists("/tmp/terminvereinbarung.pid"):
            with open("/tmp/terminvereinbarung.pid", "r") as f:
                current_pid = f.readline()
                current_pid = current_pid.split("\n")[0]
                kill_syntax = "kill -9 {}".format(current_pid)
                os.system(kill_syntax)
                if os.path.exists("/tmp/terminvereinbarung.pid.lock"):
                    os.remove("/tmp/terminvereinbarung.pid.lock")