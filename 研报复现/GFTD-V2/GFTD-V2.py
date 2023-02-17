import pandas as pd
import easygui as eg
import math
import os
from main import import_csv
from main import Draw_two_lines
import matplotlib.pyplot as plt
import backtrader as bt
#策略原理:<https://www.docin.com/p-923788773.html>
'''
from WindPy import *
w.start()
msg = 'GFTD-V2择时策略'
title = '信息输入界面'
filenames = ['起始日期','截止日期','指数代码']
file_value = []
file_value = eg.multenterbox(msg,title,filenames)
start_date = file_value[0]
end_date = file_value[1]
security = file_value[2]
start_date = "2005-02-22"
end_date = "2010-12-23"
errorcode, data = w.wsd('000001.SH', "high,low,close", start_date, end_date, "Fill=Previous",usedf=True)
errorcode_temp, data_temp = w.wsd('000001.SH', "high,low,close", "ED-%dTD"%(n1), start_date, "Fill=Previous",usedf=True)
'''
n1,n2,n3 = 4,4,4
ud_count, buy_count, sell_count = 0,0,0
os.chdir(r'C:\Users\PINZESTAFF02\Desktop\王重翼\数据')
data = import_csv('沪深300')
data_temp = data.head(4)
print(data)
c = list(data.CLOSE)
h = list(data.HIGH)
l = list(data.LOW)
dt = list(data.Date)[4:]

#生成ud序列
temp1 = c[0:-4]
temp2 = c[4:]
ud = list(map(lambda x,y:x-y,temp2,temp1))
c = list(data.CLOSE)[4:]
h = list(data.HIGH)[4:]
l = list(data.LOW)[4:]


buy_list = []
sell_list = []
signal_list = []

#格式化ud
for i in range(len(ud)):
    if ud[i] > 0:
        ud[i] = 1
    elif ud[i] < 0:
        ud[i] = -1
    else:
        ud[i] = 0

buy, sell, signal = 0, 0, 0

for i in range(len(ud)):
# 买入/卖出启动
    if ud[i] == ud[i-1]:
        ud_count = ud_count + ud[i]
        if ud_count == n2:
            #print('%s卖出启动'%(dt[i]))
            sell_count = 0
            buy_count = 0
            # 卖出计数
            for j in range(i,len(ud)):
                if c[j] <= l[j - 2] and l[j] < l[j - 1] and c[j] < c[j - 1]:
                    sell_count = sell_count + 1
                    if h[j] == max(h[j-5:j+1]):
                        print('%s卖出止损' % (dt[j]))
                        sell = 1
                        sell_count = 0
                    if sell_count == n3:
                        print('%s卖出信号' % (dt[j]))
                        signal = -1
        if ud_count == -n2:
            #print('%s买入启动'%(dt[i]))
            buy_count = 0
            sell_count = 0
            #买入计数:
            for j in range(i,len(ud)):
                if c[j] >= h[j - 2] and h[j] > h[j - 1] and c[j] > c[j - 1]:
                    buy_count = buy_count + 1
                    if l[j] == min(l[j-5:j+1]):
                        print('%s买入止损' % (dt[j]))
                        buy = 1
                        buy_count = 0
                    if buy_count == n3:
                        print('%s买入信号' % (dt[j]))
                        signal = 1
    else:
        ud_count = ud[i]
    buy_list.append(buy)
    sell_list.append(sell)
    signal_list.append(signal)
data2 = data.iloc[4:,:]
data2 = data2.reset_index(drop=True)
data2['ud'] = ud
data2['buy'] = buy_list
data2['sell'] = sell_list
data2['signal'] = signal_list
print(data2)
data2.to_csv(r'C:\Users\PINZESTAFF02\Desktop\王重翼\数据\回测.csv')
bank = 100000
stock = 100
money_history = []

for i in range(len(data2)):
    money = bank + stock * data2.CLOSE[i]
    if data2.buy[i] == 1:
        trade_num = money/data2.CLOSE[i]
        stock = stock + trade_num
        bank = bank - data2.CLOSE[i] * trade_num
    elif data2.sell[i] == 1:
        trade_num = money/data2.CLOSE[i]
        bank = bank + data2.CLOSE[i] * trade_num
        stock = stock - trade_num
    #信号反转
    elif i != 0:
        if list(set(data2.signal[:i]))[-1] == 1:
            if data2.signal[i] + 1 == 0:
                trade_num = bank/data2.CLOSE[i]
                stock = stock + trade_num
                bank = bank - data2.CLOSE[i] * trade_num
        elif list(set(data2.signal[:i]))[-1] == -1:
            if data2.signal[i] - 1 == 0:
                trade_num = money / data2.CLOSE[i]
                bank = bank + data2.CLOSE[i] * trade_num
                stock = stock - trade_num
    else:
        pass


    money_history.append(money)
    print(money)

returns = list(map(lambda x:x/1-1,money_history))
index_list = list(data2.CLOSE)
x = list(data2.Date)
Draw_two_lines(x,money_history,index_list,'GFTDV2','沪深300','择时交易')




