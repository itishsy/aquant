from engines import *
from datetime import datetime
from models.user import generate_pwd
from models.ticket import Ticket
from models.base import BaseModel, db


def test_search(eng_name):
    eng = engine.strategy[eng_name]()
    eng.strategy = eng_name
    print("[{}] {} start...".format(datetime.now(), eng_name))
    eng.do_search()
    print("[{}] {} end".format(datetime.now(), eng_name))


def test_watch(eng_name):
    eng = engine.strategy[eng_name]()
    eng.strategy = eng_name
    print("[{}] {} start...".format(datetime.now(), eng_name))
    eng.start_watch()
    print("[{}] {} end".format(datetime.now(), eng_name))


def test_model():
    # generate_pwd('')
    # print('done!')
    db.connect()
    db.create_tables([Ticket])


if __name__ == '__main__':
    test_watch('p60')
    # test_search('p60')
    # test_model()
