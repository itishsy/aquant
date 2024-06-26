from datetime import datetime
from engines.engine import strategy_engine, Engine
from candles.storage import find_candles
from models.signal import Signal
from models.choice import Choice
from models.ticket import Ticket
from signals.divergence import diver_bottom, diver_top
from signals.utils import *
from common.utils import dt_format


@strategy_engine
class UAB(Engine):
    bs_freq = [15, 30, 60]
    bp_freq = [5, 10, 15]

    def search(self, code):
        """ 上涨趋势中的调整出现背离后突破
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

        # REQ01
        cs = get_cross(candles)
        if cs[0].diff() < 0 or cs[1].diff() < 0 or cs[1].bar() < 0 or cs[0].dea9 < 0:
            print('REQ01 return')
            return

        # REQ02
        j = len(candles) - 20
        turnover = 0
        while j < len(candles):
            turnover = turnover + candles[j].turnover
            j = j + 1
        if turnover / 20 < 1.5:
            print('REQ02 return')
            return

        # REQ03
        dts = diver_top(candles)
        if len(dts) > 0 and dts[-1].dt > candles[50].dt:
            print('REQ03 return')
            return

        # REQ04
        tbs = get_top_bottom(candles)
        glb = get_lowest_bottom(tbs, -1)  # 启动低点
        lowest = get_lowest(get_stage(candles, glb.dt))
        highest = get_highest(get_section(candles, lowest.dt))  # 高点
        adjust = get_lowest(get_section(candles, highest.dt))  # 调整低点
        if (highest.high - adjust.low) / (highest.high - lowest.low) > 0.618:
            print('REQ04 return')
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
        print('REQ05 return')

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
            self.choice.status = Choice.Status.DONE

    def deal(self, tic):
        dt = self.ticket.bs_dt
        lowest = get_lowest(find_candles(self.ticket.code, begin=dt_format(dt)))
        if lowest.low < self.ticket.bs_price:
            self.ticket.status = Ticket.Status.DONE
