from datetime import datetime, timedelta
from abc import ABC, abstractmethod
from models.ticket import Ticket, TICKET_STATUS
from models.choice import Choice
from models.signal import Signal, SIGNAL_TYPE, SIGNAL_STRENGTH
from common.utils import *
from models.component import Component, COMPONENT_TYPE
import storage.fetcher as fet
from storage.dba import find_active_symbols, find_candles, get_symbol
from signals.utils import *

import traceback
import time

strategy = {}


def strategy_engine(cls):
    cls_name = cls.__name__

    def register(clz):
        strategy[cls_name] = clz

    return register(cls)


def is_need_fetch():
    if is_trade_time():
        # 交易时间不搜索
        return False
    co = Component.get(Component.name == COMPONENT_TYPE.FETCHER)
    ltm = co.run_end
    now = datetime.now()
    if now.weekday() < 5:
        if (now.hour > 15 or now.hour < 7) and (ltm.month < now.month or ltm.day < now.day or ltm.hour < 16):
            return True
    elif ltm.weekday() < 4:
        return True
    return False


def is_need_start(comp):
    sea = Component.get(Component.name == comp)
    if is_trade_time():
        # 交易时间不搜索
        return False
    if sea.run_end.month < datetime.now().month or sea.run_end.day < datetime.now().day:
        # 当天没搜索过，需要搜索
        return True
    elif sea.run_end.day == datetime.now().day:
        # 当天已搜索过，搜索结束时间是在工作日的16点前，仍要搜索
        return sea.run_end.weekday() < 5 and sea.run_end.hour < 16
    return False


class Engine(ABC):
    ticket = None
    signal = None

    def start(self):
        if is_trade_time():
            bss = Ticket.select().where(Ticket.status != TICKET_STATUS.ZERO, Ticket.status != TICKET_STATUS.KICK)
            for tick in bss:
                try:
                    self.ticket = tick
                    if tick.status == TICKET_STATUS.WATCH:
                        self.watch()
                        if self.signal:
                            self.ticket.status = TICKET_STATUS.DEAL
                            self.ticket.update_bp(self.signal)
                        else:
                            self.flush()
                            if self.ticket.status == TICKET_STATUS.KICK:
                                Ticket.delete_by_id(tick.get_id())
                    elif tick.status == TICKET_STATUS.DEAL:
                        self.flush()
                        if self.ticket.status == TICKET_STATUS.KICK:
                            Ticket.delete_by_id(tick.get_id())
                    elif tick.status == TICKET_STATUS.HOLD:
                        self.hold()
                except Exception as e:
                    print(e)
                finally:
                    self.ticket = None
                    self.signal = None
        else:
            if is_need_start(COMPONENT_TYPE.FETCHER):
                Component.update(status=1, run_start=datetime.now()).where(
                    Component.name == COMPONENT_TYPE.FETCHER).execute()
                fet.fetch_all()
                Component.update(status=0, run_end=datetime.now()).where(
                    Component.name == COMPONENT_TYPE.FETCHER).execute()
            if is_need_start(COMPONENT_TYPE.SEARCHER.format(self.__class__.__name__.lower())):
                Component.update(status=1, run_start=datetime.now()).where(
                    Component.name == COMPONENT_TYPE.SEARCHER.format(self.__class__.__name__.lower())).execute()
                self.search_all()
                Component.update(status=0, run_end=datetime.now()).where(
                    Component.name == COMPONENT_TYPE.SEARCHER.format(self.__class__.__name__.lower())).execute()

    def search_all(self):
        count = 0
        try:
            symbols = find_active_symbols()
            for sym in symbols:
                count = count + 1
                print('[{0}] searching... {1}({2}) '.format(datetime.now(), sym.code, count))
                self.ticket = Ticket(code=sym.code, name=sym.name)
                self.search(sym.code)
                if self.signal:
                    self.add_choice()
                self.signal = None
                self.ticket = None
        except Exception as e:
            print(e)
        finally:
            self.signal = None
            self.ticket = None
            print('[{0}] search {1} done! ({2}) '.format(datetime.now(), self.__class__.__name__, count))

    def add_choice(self):
        if not Choice.select().where(Choice.code == self.signal.code,
                                     Choice.s_dt == self.signal.dt,
                                     Choice.s_freq == self.signal.freq).exists():
            cho = Choice()
            cho.source = 'ENGINE'
            cho.strategy = self.__class__.__name__
            cho.add_by_signal(sig=self.signal)
            print('[{0}] add a choice({1}) by strategy {2}'.format(datetime.now(),
                                                                   self.signal.code,
                                                                   self.__class__.__name__))

    def add_signal(self, sig: Signal):
        if Signal.select().where(Signal.code == sig.code, Signal.freq == sig.freq, Signal.dt == sig.dt,
                                 Signal.effect is None).exists():
            si = Signal.get(Signal.code == sig.code, Signal.freq == sig.freq, Signal.dt == sig.dt)
            lowest = get_lowest(find_candles(self.ticket.code, begin=dt_format(sig.dt)))
            if lowest.low < sig.price:
                si.effect = 0
                si.updated = datetime.now()
                si.save()
            elif sig.type == SIGNAL_TYPE.BOTTOM_DIVERGENCE:
                cds = find_candles(self.ticket.code, freq=sig.freq)
                d, a, b, r, c = get_dabrc(cds, sig.dt)
                r_high = get_highest(r)
                if r_high.diff() > 0:
                    si.effect = 1
                    si.strength = SIGNAL_STRENGTH.STRONG
                    si.save()
                else:
                    a_high = get_highest(a)
                    a_low = get_lowest(a)
                    if r_high.high > a_high.high:
                        si.effect = 1
                        si.strength = SIGNAL_STRENGTH.STRONG
                        si.save()
                    elif r_high.high > (a_high.high + a_low.low) / 2:
                        si.strength = SIGNAL_STRENGTH.AVERAGE
                        si.save()
        else:
            # 信號价不能破
            lowest = get_lowest(find_candles(self.ticket.code, begin=dt_format(sig.dt)))
            if lowest.low < sig.price:
                return

            self.signal = sig
            self.signal.code = self.ticket.code
            self.signal.name = self.ticket.name
            self.signal.created = datetime.now()
            self.signal.save()

    @abstractmethod
    def search(self, code):
        pass

    @abstractmethod
    def watch(self):
        pass

    @abstractmethod
    def flush(self):
        pass

    @abstractmethod
    def hold(self):
        pass
