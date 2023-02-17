import baostock as bs
import pandas as pd
import numpy as np


class GetData:
    def __init__(self, start_date="2022-12-13", end_date="2022-12-19"):
        self.start_date = start_date
        self.end_date = end_date

        lg = bs.login()
        print('login respond error_code:' + lg.error_code)
        print('login respond  error_msg:' + lg.error_msg)

    def get_k_min_data(self, code):
        print("downloading k min data:  ", code)
        rs = bs.query_history_k_data_plus(code,
                                          "date,time,code,open,high,low,close,volume",
                                          start_date=self.start_date, end_date=self.end_date,
                                          frequency="5", adjustflag="2")
        if rs.error_code != '0':
            print('query_history_k_data_plus respond error_code:' + rs.error_code)
            print('query_history_k_data_plus respond  error_msg:' + rs.error_msg)

        data_list = []
        while (rs.error_code == '0') & rs.next():
            data_list.append(rs.get_row_data())

        result = pd.DataFrame(data_list, columns=rs.fields)
        return result

    def get_k_day_data(self, code):
        print("downloading k day data: ", code)
        rs = bs.query_history_k_data_plus(code,
                                          "date,code,open,high,low,close,preclose,volume,turn,pctChg,isST",
                                          start_date=self.start_date, end_date=self.end_date,
                                          frequency="d", adjustflag="2")

        if rs.error_code != '0':
            print('query_history_k_data_plus respond error_code:' + rs.error_code)
            print('query_history_k_data_plus respond  error_msg:' + rs.error_msg)

        data_list = []
        while (rs.error_code == '0') & rs.next():
            data_list.append(rs.get_row_data())

        result = pd.DataFrame(data_list, columns=rs.fields)
        return result

    @classmethod
    def get_hs300_list(cls):
        rs = bs.query_hs300_stocks()
        if rs.error_code != '0':
            print('query_hs300 error_code:' + rs.error_code)
            print('query_hs300  error_msg:' + rs.error_msg)

        hs300_stocks = []
        while (rs.error_code == '0') & rs.next():
            hs300_stocks.append(rs.get_row_data())
        result = pd.DataFrame(hs300_stocks, columns=rs.fields)
        return result.code.to_list()

