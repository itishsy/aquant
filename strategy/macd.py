import pandas as pd
from storage import upset,query
from datetime import datetime,timedelta
from storage import read
import talib as ta

"""
cross：
(down) bar.pre > 0 & bar.nxt <0  T(bar.pre)=1,T(bar.nxt)=-1
(up)   bar.pre < 0 & bar.nxt >0  T(bar.pre)=-1,T(bar.nxt)=1
turn：
(bottom) diff.pre > diff.mid & diff.nxt > diff.mid T(diff.pre)=-2,T(diff.mid)=-3,T(diff.nxt)=-2
(top) diff.pre < diff.mid & diff.nxt < diff.mid T(diff.pre)=2,T(diff.mid)=3,T(diff.nxt)=2

(bottom reverse) 
1. diff < 0 & dea < 0
2. point sequence: -3,-3
3. point(-3)[0].diff < point(-3)[1].diff
4. point(-3)[0].low > point(-3)[1].low
"""


def mark_data(stock_code, klt=101, start=datetime(2020, 1, 1)):
    if klt == 102:
        start = datetime(1900, 1, 1),
    k_data = read(stock_code, klt=klt, beg=start, field='open,high,low,close,volume,datetime')
    if len(k_data) < 50:
        return k_data
    k_data.set_index('datetime', drop=True, inplace=True)
    diff, dea, bar = ta.MACD(k_data.close, fastperiod=12, slowperiod=26, signalperiod=9)
    k_data['diff'] = diff
    k_data['dea'] = dea
    k_data['bar'] = bar * 2
    k_data['mark'] = 0
    k_data['signal'] = 0
    s = len(k_data) - 2
    for i in range(1, s):
        pre = k_data.iloc[i - 1]
        cur = k_data.iloc[i]
        nxt = k_data.iloc[i + 1]
        if (pre['bar'] < 0) & (cur['bar'] > 0):
            k_data.iloc[i - 1, k_data.columns.get_loc('mark')] = -1
            k_data.iloc[i, k_data.columns.get_loc('mark')] = 1
        if (pre['bar'] > 0) & (cur['bar'] < 0):
            k_data.iloc[i - 1, k_data.columns.get_loc('mark')] = 1
            k_data.iloc[i, k_data.columns.get_loc('mark')] = -1

        if (cur['bar'] < 0) and (pre['diff'] > cur['diff']) and (nxt['diff'] > cur['diff']):
            k_data.iloc[i - 1, k_data.columns.get_loc('mark')] = -2
            k_data.iloc[i, k_data.columns.get_loc('mark')] = -3
            k_data.iloc[i + 1, k_data.columns.get_loc('mark')] = -2
        if (cur['bar'] > 0) and (pre['diff'] < cur['diff']) and (nxt['diff'] < cur['diff']):
            k_data.iloc[i - 1, k_data.columns.get_loc('mark')] = 2
            k_data.iloc[i, k_data.columns.get_loc('mark')] = 3
            k_data.iloc[i + 1, k_data.columns.get_loc('mark')] = 2
        '''
        if  bar_pre< 0 and cur.bar < 0 and bar_nxt < 0:
            low_cur = k_data.iloc[i]['low']
            low_pre = k_data.iloc[i - 1]['low']
            low_nxt = k_data.iloc[i + 1]['low']
            if low_pre > low_cur and low_nxt > low_cur:
                k_data.iloc[i - 1, k_data.columns.get_loc('mark')] = -2
                k_data.iloc[i, k_data.columns.get_loc('mark')] = -3
                k_data.iloc[i + 1, k_data.columns.get_loc('mark')] = -2
        if bar_pre > 0 and cur.bar > 0 and bar_nxt > 0:
            high_cur = k_data.iloc[i]['high']
            high_pre = k_data.iloc[i - 1]['high']
            high_nxt = k_data.iloc[i + 1]['high']
            if high_pre < high_cur and high_nxt < high_cur:
                k_data.iloc[i - 1, k_data.columns.get_loc('mark')] = 2
                k_data.iloc[i, k_data.columns.get_loc('mark')] = 3
                k_data.iloc[i + 1, k_data.columns.get_loc('mark')] = 2
        '''
    k_mark = k_data[abs(k_data['mark']) == 3]

    s2 = len(k_mark)-1
    for i in range(1, s2):
        mark_pre = k_mark.iloc[i - 1]['mark']
        mark_cur = k_mark.iloc[i]['mark']
        if mark_pre == 3 and mark_cur == 3:
            if k_mark.iloc[i - 1]['high'] >= k_mark.iloc[i]['high']:
                k_mark.iloc[i, k_mark.columns.get_loc('mark')] = 2
            else:
                k_mark.iloc[i - 1, k_mark.columns.get_loc('mark')] = 2
        # 震荡
        #if mark_cur == 3 and k_mark.iloc[i]['diff'] > -0.1:
        #    k_mark.iloc[i, k_mark.columns.get_loc('mark')] = 1

    k_mark_new = k_mark[abs(k_mark['mark']) == 3]
    k_mark_new.to_csv('res/k_mark_{}.csv'.format(stock_code))
    return k_mark_new


def bottom_reverse(k_mark):
    size = len(k_mark)
    k_signal = pd.DataFrame()
    if size > 3 and 'mark' in k_mark:
        for i in range(2,size):
            mark_2 = k_mark.iloc[i-2, k_mark.columns.get_loc('mark')]
            mark_1 = k_mark.iloc[i-1, k_mark.columns.get_loc('mark')]
            mark_0 = k_mark.iloc[i, k_mark.columns.get_loc('mark')]
            bar0 = k_mark.iloc[i, k_mark.columns.get_loc('bar')]
            #and abs(bar0) > 0.1
            if mark_2 == -3 and mark_1 == 3 and mark_0 == -3:
                diff2 = k_mark.iloc[i - 2, k_mark.columns.get_loc('diff')]
                diff1 = k_mark.iloc[i - 1, k_mark.columns.get_loc('diff')]
                diff0 = k_mark.iloc[i, k_mark.columns.get_loc('diff')]
                low2 = k_mark.iloc[i - 2, k_mark.columns.get_loc('low')]
                low0 = k_mark.iloc[i, k_mark.columns.get_loc('low')]
                if diff1 < 0 and diff2 < diff0 and low2 > low0:
                    high1 = k_mark.iloc[i - 1, k_mark.columns.get_loc('high')]
                    if ((high1-low0)/low0) > 0.1 and ((high1-low0)/high1) > 0.1:
                        k_mark.iloc[i, k_mark.columns.get_loc('signal')] = 1
        k_signal = k_mark[k_mark['signal'] == 1]
        #k_signal.to_csv('k_signal.csv')
    return k_signal


def search(stocks=[], klt= 101,lit=-10):
    t1 = datetime.now()
    now_str = t1.strftime('%Y-%m-%d')
    with open('res/macd_search_date') as r:
        last_str = r.read(10)
        if last_str == now_str:
            print('最近一次检索时间：{}'.format(last_str))
            return
        r.close()

    #codes = pd.DataFrame()
    if len(stocks) < 1:
        codes = query('SELECT code FROM `all_realtime`')
    else:
        codes = pd.DataFrame(stocks, columns= ['code'])
    print('检索开始时间:{},记录数:{}'.format(t1.strftime('%Y-%m-%d %H:%M:%S'), len(codes)))
    start = pd.DataFrame(['开始【{}】'.format(t1.strftime('%Y-%m-%d %H:%M:%S'))])
    start.to_csv('res/macd_result_{}.csv'.format(t1.strftime('%Y%m')), index=False, header=False, mode='a')
    for idx, row in codes.iterrows():
        data = mark_data(row.code, klt=klt)
        if klt == 102:
            lately = datetime.now()+timedelta(weeks=lit)
        else:
            lately = datetime.now()+timedelta(days=lit)
        if len(data) > 0:
            signal = bottom_reverse(data)
            if len(signal) > 0:
                for i, row2 in signal.iterrows():
                    if datetime.strptime(i, '%Y-%m-%d') > lately:
                        print('[编码]{}，[日期]{}，[价格]{}'.format(row.code, i, row2.close))
                        s1 = pd.DataFrame({'create':  ['[{}]'.format(datetime.now().strftime('%H:%M:%S'))], 'code': [row.code], 'datetime': [i], 'close': [row2.close]})
                        s1.to_csv('res/macd_result_{}.csv'.format(t1.strftime('%Y%m')), index=False, header=False, mode='a')
    t2 = datetime.now()
    stop = pd.DataFrame(['结束【{}】'.format(t2.strftime('%Y-%m-%d %H:%M:%S'))])
    stop.to_csv('res/macd_result_{}.csv'.format(t2.strftime('%Y%m')), index=False, header=False, mode='a')
    with open('res/macd_search_date', 'w') as w:
        w.write(now_str)
        w.close()
    print('检索结束时间:{},共用时:{:.2f}分钟'.format(t2.strftime('%Y-%m-%d %H:%M:%S'), (t2-t1).seconds/60))
