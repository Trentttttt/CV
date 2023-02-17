from matplotlib import pyplot as plt
from getdata import *
import os
from sklearn.metrics import r2_score
from sklearn.metrics import mean_squared_error as mse
import xgboost as xgb
from numpy import *
from common_factors import *
from getdata import *
from tick_factors import *

# my_data = GetData(start_date="2019-12-13", end_date="2023-01-29")
#
# # 获取股票列表
# hs300_list = my_data.get_hs300_list()
# print(hs300_list)
# for code in hs300_list:
#     # 下载5min数据
#     my_data.get_k_min_data(code).to_csv("datas/5min/%s.csv" % code)
#     # 下载日度数据
#     my_data.get_k_day_data(code).to_csv("datas/day/%s.csv" % code)

# 计算tick因子值
for file_name in os.listdir("datas/5min"):
    if file_name == "index.csv":
        continue

    df = pd.read_csv("datas/5min/%s" % file_name)  # 某个股票5min数据
    df_write = pd.read_csv("datas/day/%s" % file_name)  # 待写入日度数据
    df_write = df_write.set_index("date")
    print("writing factors of ", file_name)
    for day in set(df.date):
        df_day = df[df['date'] == day]  # 某个股票某天的5min数据
        my_factors = TickFactors(df_day)

        ts = my_factors.trend_strength()
        pv_corr = my_factors.price_volume()
        mk_corr, morn_corr, after_corr = my_factors.market_corr()

        # 写入至日度数据
        df_write.loc[day, "ts"] = ts
        df_write.loc[day, "pv_corr"] = pv_corr
        df_write.loc[day, "mk_corr"] = mk_corr
        df_write.loc[day, "morn_corr"] = morn_corr
        df_write.loc[day, "after_corr"] = after_corr

    df_write.to_csv("datas/day/%s" % file_name)

# 计算common因子
for file_name in os.listdir("datas/day"):
    df = pd.read_csv("datas/day/%s" % file_name)
    my_factors = CommonFactors(df)

    macd, macd_diff = my_factors.cal_macd()

    df = df.assign(macd=macd, macd_diff=macd_diff)
    df.to_csv("datas/day/%s" % file_name)
    print(file_name, "is completed")
print("all datas are satisfied! Now training the model")

# 机器学习
# 数据合并
df_lis = []
csv_lis = os.listdir("datas/day")
for csv_file in csv_lis:
    print(csv_lis.index(csv_file) / len(csv_lis))
    df = pd.read_csv("datas/day/" + csv_file)
    df['pv_avg20'] = df['pv_corr'].rolling(20).mean()
    df['pv_std20'] = df['pv_corr'].rolling(20).std()
    df['ts_avg20'] = df['ts'].rolling(20).mean()
    df['ts_std20'] = df['ts'].rolling(20).std()

    df['pv_avg5'] = df['pv_corr'].rolling(5).mean()
    df['pv_std5'] = df['pv_corr'].rolling(5).std()
    df['ts_avg5'] = df['ts'].rolling(5).mean()
    df['ts_std5'] = df['ts'].rolling(5).std()

    df['ret1'] = df['open'].pct_change().shift(-2)
    df['ret20'] = df['open'].shift(-20) / df['open'].shift(-1) - 1
    df['ret5'] = df['open'].shift(-5) / df['open'].shift(-1) - 1
    df_lis.append(df)

df = pd.concat(df_lis)
df = df[[col for col in df.columns if "Unnamed" not in col]]
df = df.drop(["morn_corr", "after_corr"], axis=1)
print("before drop na: ", df.shape)
df = df.dropna()
print("after drop na: ", df.shape)

print(df.info(verbose=True, null_counts=True))

df['date'] = pd.to_datetime(df['date'])
df = df.set_index('date')
df_train = df.loc[:'2022']
df_test = df.loc['2022':]

print("训练集：", df_train.shape)
print("测试集：", df_test.shape)

X_train = df_train.drop(
    columns=['ret1', 'ret5', 'ret20', 'open', 'high', 'low', 'close', 'volume', 'code', 'preclose', 'turn', 'pctChg'])
print("X: ", X_train.columns)
y_train = df_train['ret1'].ravel()

X_test = df_test.drop(
    columns=['ret1', 'ret5', 'ret20', 'open', 'high', 'low', 'close', 'volume', 'code', 'preclose', 'turn', 'pctChg'])
y_test = df_test['ret1'].ravel()

data_train = xgb.DMatrix(data=X_train, label=y_train)
data_test = xgb.DMatrix(data=X_test, label=y_test)

xgb_reg = xgb.XGBRegressor(objective='reg:squarederror',
                           colsample_bylevel=0.8,
                           colsample_bynode=0.8,
                           colsample_bytree=0.8,
                           eta=1,
                           gamma=0,
                           max_depth=6,
                           min_child_weight=1,
                           n_estimators=1000,
                           reg_alpha=1,
                           random_state=666)
xgb_reg.fit(X_train, y_train)

print("样本内")

preds = xgb_reg.predict(X_train)
rmse = np.sqrt(mse(y_train, preds))
print("The in-sample RMSE is %0.4f." % rmse)
print("The in-sample R-squared of the XGB regression tree is %0.4f." % r2_score(y_train, preds))

d = pd.DataFrame(preds)
d = d.set_index(df_train.index)
d.columns = ['preds']
d['ret1'] = df_train['ret1']
fig, ax = plt.subplots(figsize=(20, 10))
ax2 = ax.twiny()
d['ret1'].plot(ax=ax)
d['preds'].plot(ax=ax, secondary_y=False, color='r')
plt.show()

d = pd.DataFrame(preds)
d = d.set_index(df_train.index)
d.columns = ['preds']
d['ret1'] = df_train['ret1']
fig, ax = plt.subplots(figsize=(20, 20))

x = np.linspace(-0.005, 0.005, len(d))
ax.plot([0] * len(d), x)

x = np.linspace(-0.005, 0.005, len(d))
ax.plot(x, [0] * len(d))

ax.scatter(x=d['preds'], y=d['ret1'], color='r')
# ax.plot(x,x)
plt.show()

print("样本外")

preds = xgb_reg.predict(X_test)
rmse = np.sqrt(mse(y_test, preds))
print("The out-of-sample RMSE is %0.4f." % rmse)
print("The out-of-sample R-squared of the XGB regression tree is %0.4f." % r2_score(y_test, preds))

d = pd.DataFrame(preds)
d = d.set_index(df_test.index)
d.columns = ['preds']
d['ret1'] = df_test['ret1']

fig, ax = plt.subplots(figsize=(20, 10))
ax2 = ax.twiny()
d['ret1'].plot(ax=ax)
d['preds'].plot(ax=ax, secondary_y=False, color='r')
plt.show()

d = pd.DataFrame(preds)
d = d.set_index(df_test.index)
d.columns = ['preds']
d['ret1'] = df_test['ret1']

fig, ax = plt.subplots(figsize=(20, 20))
# d = d.loc['2020-05-19']
x = np.linspace(-0.005, 0.005, len(d))
ax.plot([0] * len(d), x)

x = np.linspace(-0.005, 0.005, len(d))
ax.plot(x, [0] * len(d))
ax.scatter(x=d['preds'], y=d['ret1'], color='r')
# ax.plot(x,x)
plt.show()

a = 0.02
one = len(d[(d['preds'] > a) & (d['ret1'] > 0.0003)])
two = len(d[(d['preds'] < -a) & (d['ret1'] > 0.00003)])
three = len(d[(d['preds'] < -a) & (d['ret1'] < 0.0003)])
four = len(d[(d['preds'] > a) & (d['ret1'] < 0.0003)])

print("第一象限数量", one)
print("第二象限数量", two)
print("第三象限数量", three)
print("第四象限数量", four)
print("\n")
total = one + two + three + four

print("第一象限占比", one / total)
print("第二象限占比", two / total)
print("第三象限占比", three / total)
print("第四象限占比", four / total)
print("\n")
print("总胜率", (one + three) / total)
print("做多胜率", one / (one + four))
print("做空胜率", three / (two + three))
