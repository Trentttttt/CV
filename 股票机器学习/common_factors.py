class CommonFactors:
    def __init__(self, df):
        self.open = df.open
        self.high = df.high
        self.low = df.low
        self.close = df.close
        self.volume = df.volume

    def cal_macd(self, short_=12, long_=26, m=9):
        """
        data是包含高开低收成交量的标准dataframe
        short_,long_,m分别是macd的三个参数
        返回值是包含原始数据和diff,dea,macd三个列的dataframe
        """
        diff = self.close.ewm(adjust=False, alpha=2 / (short_ + 1), ignore_na=True).mean() - self.close.ewm(
            adjust=False, alpha=2 / (long_ + 1), ignore_na=True).mean()
        dea = diff.ewm(adjust=False, alpha=2 / (m + 1), ignore_na=True).mean()
        macd = 2 * (diff - dea)

        """
        macd > 0，红柱
        macd < 0，绿柱
        macd_0 - macd_1 > 0, 红柱变长 or 绿柱变短
        macd_0 - macd_1 < 0, 红柱变短 or 绿柱变长
        """

        return macd, macd - macd.shift(1)

    def cal_fund(self):
        """
        成交量 * 收盘价 - 成交量 * 开盘价
        成交量 * (高开低收均值)
        :return:
        """
        fund1 = self.volume * self.close - self.volume * self.open
        fund2 = self.close * self.volume
        return fund1, fund2

    def cal_ret(self):
        """
        昨日open收益率
        :return:
        """
        return self.close.pct_change()
