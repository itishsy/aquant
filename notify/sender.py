from models.signal import Signal
from datetime import datetime
from notify.qywx import send_qywx
from models.component import Component
import time
import traceback


def find_notify_content():
    trs = Signal.select().where(Signal.notify == 0).order_by(Signal.id).limit(5)
    content = ''
    for tr in trs:
        sc = 'SH' if tr.code.startswith('60') else 'SZ'
        l = 'http://xueqiu.com/S/{}{}'.format(sc, tr.code)
        t = 'B' if tr.type == 0 else 'S'
        content = '【{}】{} {} {};{}'.format(t, l, tr.freq, tr.dt, content)
    return content


def update_notify_status():
    trs = Signal.select().where(Signal.notify == 0).order_by(Signal.id).limit(5)
    for tr in trs:
        tr.notify = 1
    Signal.bulk_update(trs, fields=['notify'], batch_size=50)


def do_send():
    message = find_notify_content()
    if send_qywx(message):
        Component.update(status=2, run_start=datetime.now()).where(Component.name == 'sender').execute()
        update_notify_status()
        Component.update(status=1, run_end=datetime.now()).where(Component.name == 'sender').execute()


if __name__ == '__main__':
    while True:
        try:
            Component.update(status=1, clock_time=datetime.now()).where(Component.name == 'sender').execute()
            do_send()
        except Exception:
            traceback.print_exc()
        finally:
            time.sleep(60 * 15)
