import storage.database as db
import storage.fetcher as fet
import storage.indicator as ind
from datetime import datetime, timedelta
import logging
import traceback
import time


def watch_all():
    code_dict = db.query("SELECT `code`, `watch_klt`  FROM `watcher` WHERE `status` = 1")
    for i, row in code_dict.iterrows():
        code = row['code']
        wkl = row['watch_klt'].split(',')
        for klt in wkl:
            klt = int(klt)
            try:
                fet.fetch_kline_data(code, klt)
                ind.update_mark(code, klt)
            except Exception as e:
                traceback.print_exc()
                logging.error('{} fetch {} error: {}'.format(i, code, e))
            else:
                ind.save_signal(code, klt, watch=True)


def read_send_data():
    dtime = (datetime.now() - timedelta(days=2)).strftime('%Y-%m-%d')
    send_data = db.query(
        "SELECT `code`, `klt`, `event_type`, `event_datetime` FROM `watcher_detail` WHERE `notify` = 0 AND `event_datetime` > '{}'".format(
            dtime))
    msg = ''
    if len(send_data) > 0:
        for i, row in send_data.iterrows():
            msg = '【{}】, klt: {}, type: {}, datetime: {}; {}' \
                .format(row['code'], row['klt'], row['event_type'], row['event_datetime'], msg)
    return msg


def update_notify():
    up_sql = 'UPDATE `watcher_detail` SET `notify` = 1'
    db.execute(db.get_connect(), up_sql)


if __name__ == '__main__':
    while True:
        try:
            now = datetime.now()
            wd = now.weekday() + 1
            hm = now.hour * 100 + now.minute
            print("{} {} {} watching".format(datetime.now().strftime('%Y-%m-%d'), wd, hm))
            if (wd in [1, 2, 3, 4, 5]) and (
                    hm in [946, 1001, 1016, 1031, 1046, 1101, 1116, 1131, 1316, 1331, 1346, 1401, 1416, 1431, 1446,
                           1501]):
                watch_all()
        except:
            pass
        finally:
            time.sleep(60)
