import xgboost as xgb
from my_tools import *
from common_factors import *
from getdata import *
from tick_factors import *
import os

today = "2023-01-30"
# print("today: ", today)
# my_data = GetData(start_date=today, end_date=today)
#
# # 获取股票列表
# hs300_list = my_data.get_hs300_list()
# t = 1
# for code in hs300_list:
#     print("Current updating stock：", code)
#     """
#     先下载日度数据，新的日期等基础数据就有了
#     再下载分钟数据并计算当天的因子值
#     将新的日度数据+新的因子
#     合并新旧日度数据
#     合并新旧分钟数据
#     计算日度因子
#     """
#     new_day = my_data.get_k_day_data(code)
#     new_min = my_data.get_k_min_data(code)
#     if t == 1:
#         print(new_day)
#         t = 0
#     if len(new_min) == 0 or len(new_day) == 0:
#         print("数据尚未更新")
#         raise ValueError
#
#     my_factors = TickFactors(new_min)
#     ts = my_factors.trend_strength()
#     pv_corr = my_factors.price_volume()
#     mk_corr, morn_corr, after_corr = my_factors.market_corr()
#     new_day = new_day.assign(ts=ts, pv_corr=pv_corr, mk_corr=mk_corr, morn_corr=morn_corr, after_corr=after_corr)
#
#     old_day = pd.read_csv("datas/day/%s.csv" % code)
#     old_day = old_day[[col for col in old_day.columns if "Unnamed" not in col]]
#     old_min = pd.read_csv("datas/5min/%s.csv" % code)
#     old_min = old_min[[col for col in old_min.columns if "Unnamed" not in col]]
#     new_day[['open', 'high', 'low', 'close', 'preclose', 'volume', 'turn', 'pctChg', 'isST']] = new_day[
#         ['open', 'high', 'low', 'close', 'preclose', 'volume', 'turn', 'pctChg', 'isST']].astype(float)
#     new_min[['open', 'high', 'low', 'close', 'volume']] = new_min[['open', 'high', 'low', 'close', 'volume']].astype(
#         float)
#
#     new_day = pd.concat([old_day, new_day], ignore_index=True)
#     new_min = pd.concat([old_min, new_min], ignore_index=True)
#     # print(new_day)
#     # print(new_min)
#
#     new_day.to_csv("datas/day/%s.csv" % code)
#     new_min.to_csv("datas/5min/%s.csv" % code)

# 计算common因子
print("calculating factors ...")
df_lis = []
file_lis = os.listdir("datas/day")
process_bar = ShowProcess(len(file_lis), 'completed!')
for file_name in file_lis:
    process_bar.show_process(i=file_lis.index(file_name))
    df = pd.read_csv("datas/day/%s" % file_name)
    my_factors = CommonFactors(df)

    # macd
    macd, macd_diff = my_factors.cal_macd()
    df = df.assign(macd=macd, macd_diff=macd_diff)

    # fund
    fund1, fund2 = my_factors.cal_fund()
    df = df.assign(fund1=fund1, fund2=fund2)

    # return yesterday
    ret = my_factors.cal_ret()
    df = df.assign(ret=ret)

    df['pv_avg20'] = df['pv_corr'].rolling(20).mean()
    df['pv_std20'] = df['pv_corr'].rolling(20).std()
    df['ts_avg20'] = df['ts'].rolling(20).mean()
    df['ts_std20'] = df['ts'].rolling(20).std()
    df['fund2_std20'] = df['fund2'].rolling(20).std()
    df['fund2_avg20'] = df['fund2'].rolling(20).mean()

    df['fund2_std5'] = df['fund2'].rolling(5).std()
    df['fund2_avg5'] = df['fund2'].rolling(5).mean()
    df['pv_avg5'] = df['pv_corr'].rolling(5).mean()
    df['pv_std5'] = df['pv_corr'].rolling(5).std()
    df['ts_avg5'] = df['ts'].rolling(5).mean()
    df['ts_std5'] = df['ts'].rolling(5).std()

    df['ret1'] = df['open'].pct_change().shift(-2)
    df = df[[col for col in df.columns if "Unnamed" not in col]]
    df.to_csv("datas/day/%s" % file_name, index=False)
    df_lis.append(df)

df = pd.concat(df_lis)
df = df.drop(["morn_corr", "after_corr", "mk_corr"], axis=1)
df['date'] = pd.to_datetime(df['date'])
df = df.set_index('date')
df_today = df.loc[today].copy()

print(df.info(verbose=True, show_counts=True))
df = df.dropna()
df_train = df.loc[:'2022']
df_test = df.loc['2023-01-03':'2023-01-13']

print("训练集：", df_train.shape)
print("测试集：", df_test.shape)

X_train = df_train.drop(
    columns=['ret1', 'open', 'high', 'low', 'close', 'volume', 'code', 'preclose', 'turn', 'pctChg'])
print("X: ", X_train.columns)
y_train = df_train['ret1'].ravel()

X_test = df_test.drop(
    columns=['ret1', 'open', 'high', 'low', 'close', 'volume', 'code', 'preclose', 'turn', 'pctChg'])
y_test = df_test['ret1'].ravel()

X_today = df_today.drop(
    columns=['ret1', 'open', 'high', 'low', 'close', 'volume', 'code', 'preclose', 'turn', 'pctChg'])

xgb_reg = xgb.XGBRegressor(objective='reg:squarederror',
                           colsample_bylevel=0.8,
                           colsample_bynode=0.8,
                           colsample_bytree=0.8,
                           eta=0.01,
                           gamma=0.01,
                           max_depth=15,
                           min_child_weight=10,
                           n_estimators=2000,
                           reg_lambda=1,
                           random_state=666)
xgb_reg.fit(X_train, y_train)

print("----------------------------------------------样本内----------------------------------------------")
get_xgb_valuation(X_train, y_train, xgb_reg, df_train, a=0.02)
print("----------------------------------------------样本外----------------------------------------------")
get_xgb_valuation(X_test, y_test, xgb_reg, df_test, a=0.02)

# 储存结果
preds = xgb_reg.predict(X_today)
df_today['preds'] = preds
df_today = df_today[['code', 'close', 'preds']]
df_today.to_csv(r"C:\Users\Trent\Desktop\result.csv")

