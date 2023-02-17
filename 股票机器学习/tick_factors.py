import pandas as pd


class TickFactors:
    """
    when using tick factors, you should consider processing in higher frequency, like mean/std
    :return 当天一个因子一个值/非时间序列
    """

    def __init__(self, df, df_market=pd.read_csv("datas/5min/index.csv")):
        self.open = df.open.astype(float)
        self.high = df.high.astype(float)
        self.low = df.low.astype(float)
        self.close = df.close.astype(float)
        self.volume = df.volume.astype(float)
        self.market_close = df_market.close.astype(float)
        # print("In this class, you should pass a df in one particular day k lines")

    def trend_strength(self):
        s1 = abs(self.open - self.high) + abs(self.high - self.low) + abs(self.low - self.close)
        s2 = abs(self.open - self.low) + abs(self.low - self.high) + abs(self.high - self.close)
        s1 = s1.sum()
        s2 = s2.sum()
        s = max(s1, s2)

        x = self.close.values[-1] - self.close.values[0]
        ts = x / s
        return ts

    def price_volume(self):
        pv_corr = self.close.corr(self.volume)
        return pv_corr

    def market_corr(self):
        n = int(len(self.close) / 2)
        market_corr = self.close.corr(self.market_close)
        morning_corr = self.close[:n].corr(self.market_close[:n])
        afternoon_corr = self.close[n:].corr(self.market_close[n:])
        return market_corr, morning_corr, afternoon_corr
