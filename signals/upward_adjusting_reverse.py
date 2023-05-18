import datetime

from signals.strategy import register_strategy, Strategy
from entities.candle import Candle
from entities.signal import Signal
from typing import List
from storage.db import find_candles
import signals.signals as sig


@register_strategy
class UAR(Strategy):

    def search_signal(self, candles: List[Candle]) -> List[Signal]:
        """ 向上趋势调整出现次级别买点
        1. 前一次上叉在0轴上，到后一个下叉上涨幅度超过20%
        2. 调整回落的幅度不能超过上涨幅度的黄金分割线
        3. 调整过程中，出现次某级别的背驰买点
        :param candles:
        :return:
        """
        signals = []
        c_last = candles[-1]
        if c_last.bar() > 0 or c_last.diff() < 0 or c_last.dea9 < 0:
            return signals

        l_stage = sig.get_stage(candles, c_last.dt)
        l_low = sig.get_lowest(l_stage).low

        highest = None
        lowest = None
        for x in reversed(candles):
            if x.mark == 3:
                up_stage = sig.get_stage(candles, x.dt)
                highest = sig.get_highest(up_stage)
            if x.mark == -3:
                if x.diff() < 0 or x.dea9 < 0:
                    return signals
                else:
                    down_stage = sig.get_stage(candles, x.dt)
                    lowest = sig.get_lowest(down_stage)
                    if lowest.diff() < 0:
                        return signals
                    else:
                        break

        if (highest.high - l_low) / (highest.high - lowest.low) > 0.5:
            return signals

        sdt = highest.dt
        kls = self.get_child_klt()
        for kl in kls:
            cds = find_candles(self.code, kl, begin=sdt)
            sis = sig.deviates(cds)
            if len(sis) > 0:
                for si in sis:
                    s = Signal(si.dt, type=self.__class__.__name__, klt=self.klt, value=kl)
                    s.code = self.code
                    s.created = datetime.datetime.now()
                    print(s)
                    signals.append(s)
        return signals


if __name__ == '__main__':
    pass
