import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from main import *
import statsmodels.api as sm
import statsmodels
if __name__ == '__main__':
    PriceDf = import_csv('上证指数')
    dt = list(PriceDf.Date)
    PriceDf.set_index('Date')
    PriceDf = PriceDf.sort_index(ascending = True)
    Asset = PriceDf.columns[4]
    AssetSeries = PriceDf[Asset]
    LLT = [0,0]
    d = 40
    alpha = 2/d+1
    for i in range(len(AssetSeries)-2-d):
        pricet_2 = np.mean(AssetSeries[i:i+d])
        pricet_1 = np.mean(AssetSeries[i+1:i+1+d])
        pricet = np.mean(AssetSeries[i+2:i+2+d])
        LLTt_2 = LLT[i]
        LLTt_1 = LLT[i+1]
        LLTt = (alpha-(alpha**2)/4)*pricet + (alpha**2)/2*pricet_1 - (alpha-3/4*(alpha**2))*pricet_2+ 2*(1-alpha)*LLTt_1 - ((1-alpha)**2)**LLTt_2
        LLT.append(LLTt)
        #print(i)
dt = dt[40:]
index_list = list(AssetSeries[40:])
Draw_two_lines(dt,index_list,LLT,'300','LLT','title')

y_arr= LLT
x_arr=np.arange(0,len(y_arr))
x_b_arr=sm.add_constant(x_arr)
model=statsmodels.regression.linear_model.OLS(y_arr, x_b_arr).fit()
rad=model.params[1]
deg_data=np.rad2deg(rad)
print(model.params)