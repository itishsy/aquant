from datetime import datetime
from engines import *
from models.engine import Engine
from models.component import Component
import logging
import time
import threading
from notify.notify import Notify
import os
from app import create_app

logging.basicConfig(format='%(asctime)s %(message)s', filename='d://aquant.log')
logging.getLogger().setLevel(logging.INFO)


class EngineTask(threading.Thread):
    def run(self):
        # notify = Notify()
        while True:
            Component.update(run_start=datetime.now(), status=Component.Status.RUNNING).where(
                Component.name == 'engine').execute()
            for name in engine.strategy:
                st = engine.strategy[name]()
                print("[{}] {} start...".format(datetime.now(), name))
                st.start()
            Component.update(run_start=datetime.now(), status=Component.Status.READY).where(
                Component.name == 'engine').execute()
            # notify.do_send()
            print("[{}] sleep {} min".format(datetime.now(), 5))
            time.sleep(60 * 5)


class EngineJob(threading.Thread):
    def run(self):
        while True:
            now = datetime.now()
            n_val = now.hour * 100 + now.minute
            if now.weekday() < 5:
                ens = Engine.select().where(Engine.Status == 0)
                for eng in ens:
                    if eng.job_from < n_val < eng.job_to:
                        if eng.job_times == 1 and eng.run_end > datetime.strptime(datetime.now().strftime("%Y-%m-%d 00:00:01"), "%Y-%m-%d %H:%M:%S"):
                            continue
                        try:
                            eng.status = 1
                            eng.run_start = datetime.now()
                            eng.save()
                            if eng.name == 'searcher':
                                eval(eng.name + '.' + eng.method + '.start()')
                            else:
                                eval(eng.name + '.' + eng.method + '()')
                            eng.status = 0
                            eng.run_end = datetime.now()
                            eng.save()
                        except Exception as e:
                            print(e)
                            eng.status = 2
                            eng.save()
                time.sleep(60 * 5)
            else:
                time.sleep(60 * 60 * 4)


if __name__ == '__main__':
    et = EngineJob()
    et.start()
    app = create_app(os.getenv('FLASK_CONFIG') or 'default')
    app.run(port=5000, host='172.172.4.101', debug=False)


