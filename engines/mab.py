from datetime import datetime
from engines.engine import strategy_engine, Engine
from storage.dba import get_symbol, find_candles
from models.signal import Signal
from models.choice import Choice
from models.ticket import Ticket
from signals.divergence import diver_bottom, diver_top
from signals.utils import *
from common.utils import dt_format


@strategy_engine
class MAB(Engine):
    bs_freq = [30, 60]
    bp_freq = [5, 10, 15]

    def search(self, code):
        """ 日均线支撑
        REQ01. 日线发生金叉后，回落到0轴前。
        REQ02. 活跃性要求，近20交易日均换手大于2%
        REQ03. 日线近期50日未发生顶背离
        REQ04. 价格调整的幅度不能超过上涨幅度的黄金分割线
        REQ05. 调整过程中，出现次某级别的背驰买点
        :param code:
        """
        candles = find_candles(code)
        size = len(candles)
        if size < 100:
            return

        # REQ05
        for freq in self.bs_freq:
            fcs = find_candles(code, freq)
            dbs = diver_bottom(fcs)
            if len(dbs) > 0:
                sig = dbs[-1]
                lowest = get_lowest(get_section(fcs, sdt=sig.dt))
                # 剔除无效的信號
                if lowest.low >= sig.price:
                    return sig

    def watch(self, cho):
        cho = self.choice
        lowest = get_lowest(find_candles(cho.code, begin=dt_format(cho.dt)))
        sig = Signal.get_by_id(cho.sid)
        if lowest.dt != sig.dt and lowest.low > sig.price:
            fcs = find_candles(cho.code, self.bp_freq)
            dbs = diver_bottom(fcs)
            if len(dbs) > 0:
                sig = dbs[-1]
                lowest = get_lowest(get_section(fcs, sdt=sig.dt))
                # 剔除无效的信號
                if lowest.low >= sig.price:
                    return sig
        else:
            self.choice.status = Choice.Status.KICK

    def deal(self, tic):
        dt = self.ticket.bs_dt
        lowest = get_lowest(find_candles(self.ticket.code, begin=dt_format(dt)))
        if lowest.low < self.ticket.bs_price:
            self.ticket.status = Ticket.Status.KICK
