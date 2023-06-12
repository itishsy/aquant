from datetime import datetime
from strategies import *
from models.component import Component
import time


def daily_search():
    print('[{}] searcher working ...'.format(datetime.now()))
    while True:
        now = datetime.now()
        try:
            if now.weekday() < 5 and now.hour == 17 and now.minute == 10:
                search_all()
                print("==============用時：{}=================".format(datetime.now() - now))
        except Exception as e:
            print(e)
        finally:
            if now.minute == 1:
                print('[{}] searcher working ...'.format(now))
            time.sleep(60)


def search_all(sta=None):
    try:
        Component.update(status=2).where(Component.name == 'searcher').execute()
        if sta is None:
            for name in strategy.factory:
                st = strategy.factory[name]()
                st.search_all()
        else:
            st = strategy.factory[sta]()
            # st.freq = 60
            # st.codes = ['603790']
            st.search_all()
    except Exception as e:
        print(e)
    finally:
        Component.update(status=1).where(Component.name == 'searcher').execute()


def deal_all(sta=None):
    if sta is None:
        for name in strategy.factory:
            st = strategy.factory[name]()
            st.deal_all()
    else:
        st = strategy.factory[sta]()
        # st.freq = 60
        # st.codes = ['603790']
        st.deal_all()


if __name__ == '__main__':
    daily_search()
    # search_all()
