from datetime import datetime
from storage.fetcher import fetch_all
from strategies import *
from storage.db import find_signals
import logging
import config
import time

logging.basicConfig(format='%(asctime)s %(message)s', filename='d://aquant.log'.format(config.work_path))
logging.getLogger().setLevel(logging.INFO)


def daily_task():
    print('[{}] daily task working'.format(datetime.now()))
    while True:
        now = datetime.now()
        try:
            if now.weekday() < 5 and ((now.hour == 11 and now.minute == 40) or (now.hour == 15 and now.minute == 10)):
                fetch_search_all()
        except Exception as e:
            print(e)
        finally:
            if now.minute == 1:
                print('[{}] daily task working'.format(now))
            time.sleep(60)


def fetch_search_all(sta=None):
    now = datetime.now()
    fetch_all()
    if sta is None:
        for name in strategy.factory:
            st = strategy.factory[name]()
            st.search_all()
    else:
        st = strategy.factory[sta]()
        st.search_all()
    print("==============用時：{}=================".format(datetime.now() - now))
    print(find_signals(begin=now.strftime('%Y-%m-%d')))


if __name__ == '__main__':
    daily_task()
    # fetch_search_all()
