import pandas as pd
import os
import backtrader as bt
from backtrader.feeds import GenericCSVData
os.chdir(r'C:\Users\PINZESTAFF02\Desktop\王重翼\数据')
IF = pd.read_csv('IF.csv')
IC = pd.read_csv('IC.csv')

if_close = list(IF.close)
ic_close = list(IC.close)

def calculate_return(list1):
    x = list1[:-1]
    y = list1[1:]
    r = list(map(lambda x,y: y/x-1,x,y))
    return r

if_return = calculate_return(if_close)
ic_return = calculate_return(ic_close)

IF['return'] = 0
IC['return'] = 0
IF.iloc[1:,-1] = if_return
IC.iloc[1:,-1] = ic_return

#回测
IF.to_csv('IF_backtest.csv', index = False)
IC.to_csv('IC_backtest.csv', index = False)
cerebro = bt.Cerebro()
class AddCsvData(GenericCSVData):
    lines = ('returns','buy_count')
    params = (('returns',6),('buy_count',5))
feed = AddCsvData(dataname = 'IF_backtest.csv',dtformat=('%Y/%m/%d'))
cerebro.adddata(feed)
feed = AddCsvData(dataname = 'IC_backtest.csv',dtformat=('%Y/%m/%d'))
cerebro.adddata(feed)

class TestStrategy(bt.Strategy):
    def log(self, txt, dt=None):
        dt = dt or self.datas[0].datetime.date(0)
        print('%s, %s' % (dt.isoformat(), txt))

    def __init__(self):
        # 用于记录订单状态
        self.order = None
        self.buyprice = None
        self.buycomm = None

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            # 提交给代理或者由代理接收的买/卖订单 - 不做操作
            return
        # 注意：如果没有足够资金，代理会拒绝订单
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(
                    'BUY EXECUTED, Price: %.2f, Cost: %.2f, Comm %.2f' %
                    (order.executed.price,
                     order.executed.value,
                     order.executed.comm))

                self.buyprice = order.executed.price
                self.buycomm = order.executed.comm
            else:  # 卖
                self.log('SELL EXECUTED, Price: %.2f, Cost: %.2f, Comm %.2f' %
                         (order.executed.price,
                          order.executed.value,
                          order.executed.comm))
            self.bar_executed = len(self)
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('Order Canceled/Margin/Rejected')
        # 无等待处理订单
        self.order = None

    def notify_trade(self, trade):
        if not trade.isclosed:
            return
        self.log('OPERATION PROFIT, GROSS %.2f, NET %.2f' %
                 (trade.pnl, trade.pnlcomm))


    def next(self):
        # 今天平仓昨日仓位
        self.close(data = self.datas[0])
        self.close(data = self.datas[1])
        # 检查是否有订单等待处理，如果是就不再进行其他下单
        if self.order:
            return
        # 根据昨日收益率进行开仓
        if self.datas[0].returns[-1] > self.datas[1].returns[-1]:
            # 买入IF
            self.log('BUY CREATE(IF), %.2f' % self.datas[0].close[0])
            self.order = self.buy(data=self.datas[0])
            # 卖出IC
            self.log('SELL CREATE(IC), %.2f' % self.datas[1].close[0])
            self.order = self.sell(data=self.datas[1])

        if self.datas[0].returns[-1] < self.datas[1].returns[-1]:
            # 买入IC
            self.log('BUY CREATE(IC), %.2f' % self.datas[1].close[0])
            self.order = self.buy(data=self.datas[1])
            # 卖出IF
            self.log('SELL CREATE(IF), %.2f' % self.datas[0].close[0])
            self.order = self.sell(data=self.datas[0])

cerebro.addstrategy(TestStrategy)
# 设置启动资金
cerebro.broker.setcash(10000000.0)
# 设置交易单位大小
#cerebro.addsizer(bt.sizers.PercentSizer, percents = 95)
cerebro.addsizer(bt.sizers.FixedSize, stake = 100)
# 设置佣金为千分之一
cerebro.broker.setcommission(commission=0.001)
# 打印开始信息
print('Starting Portfolio Value: %.2f' % cerebro.broker.getvalue())
# 遍历所有数据
cerebro.run()
# 打印最后结果
print('Final Portfolio Value: %.2f' % cerebro.broker.getvalue())
cerebro.plot()


