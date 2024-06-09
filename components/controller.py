from datetime import datetime
from models.component import Component
import candles.fetcher as fet
from engines import *


def start_component(name, act):
    comp = Component.get(Component.name == name)
    comp.status = Component.Status.RUNNING
    comp.run_start = datetime.now()
    comp.save()
    if act == 'fetch':
        fet.fetch_all()
    else:
        eng = engine.strategy[name.capitalize()]()
        eng.strategy = name
        if act == 'search' or act == 'all':
            print('engine', name, 'action: search, start...')
            eng.do_search()
            print('engine', name, 'action: search, done!')
        if act == 'watch' or act == 'all':
            print('engine', name, 'action: watch, start...')
            eng.do_watch()
            print('engine', name, 'action: watch, done!')
    comp.status = Component.Status.READY
    comp.run_end = datetime.now()
    comp.save()


if __name__ == '__main__':
    start_component()
