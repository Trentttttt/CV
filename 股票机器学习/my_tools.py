from matplotlib import pyplot as plt
from sklearn.metrics import r2_score
from sklearn.metrics import mean_squared_error as mse
from numpy import *
from getdata import *
from tick_factors import *


class ShowProcess:
    """
    显示处理进度的类
    调用该类相关函数即可实现处理进度的显示
    """
    i = 0  # 当前的处理进度
    max_steps = 0  # 总共需要处理的次数
    max_arrow = 50  # 进度条的长度
    infoDone = 'done'

    # 初始化函数，需要知道总共的处理次数
    def __init__(self, max_steps, infoDone='Done'):
        self.max_steps = max_steps
        self.i = 0
        self.infoDone = infoDone

    def show_process(self, i=None):
        if i is not None:
            self.i += 1
        num_arrow = int(self.i * self.max_arrow / self.max_steps)  # 计算显示多少个'>'
        num_line = self.max_arrow - num_arrow  # 计算显示多少个'-'
        percent = self.i * 100.0 / self.max_steps  # 计算完成进度，格式为xx.xx%
        process_bar = '[' + '>' * num_arrow + '-' * num_line + ']' \
                      + '%.2f' % percent + '%'  # 带输出的字符串，'\r'表示不换行回到最左边
        print("\r" + process_bar, end='')

        if self.i >= self.max_steps:
            self.close()

    def close(self):
        print('')
        print(self.infoDone)
        self.i = 0


def get_xgb_valuation(X_test, y_test, xgb_reg, df_test, a=0.02):
    preds = xgb_reg.predict(X_test)
    rmse = np.sqrt(mse(y_test, preds))
    print("The out-of-sample RMSE is %0.4f." % rmse)
    print("The out-of-sample R-squared of the XGB regression tree is %0.4f." % r2_score(y_test, preds))

    d = pd.DataFrame(preds)
    d = d.set_index(df_test.index)
    d.columns = ['preds']
    d['ret1'] = df_test['ret1']

    fig, ax = plt.subplots(figsize=(20, 20))
    x = np.linspace(-0.1, 0.1, len(d))
    ax.plot([0] * len(d), x)
    ax.plot(x, [0] * len(d))
    ax.scatter(x=d['preds'], y=d['ret1'], color='r')
    # ax.plot(x,x)
    plt.show()

    one = len(d[(d['preds'] > a) & (d['ret1'] > 0.0003)])
    two = len(d[(d['preds'] < -a) & (d['ret1'] > 0.00003)])
    three = len(d[(d['preds'] < -a) & (d['ret1'] < 0.0003)])
    four = len(d[(d['preds'] > a) & (d['ret1'] < 0.0003)])
    total = one + two + three + four

    print("第一象限数量", one)
    print("第二象限数量", two)
    print("第三象限数量", three)
    print("第四象限数量", four)
    # print("\n")
    # print("第一象限占比", one / total)
    # print("第二象限占比", two / total)
    # print("第三象限占比", three / total)
    # print("第四象限占比", four / total)
    print("\n")
    if 0 in [one, two, three, four]:
        print("has 0")
        return
    print("总胜率", (one + three) / total)
    print("做多胜率", one / (one + four))
    print("做空胜率", three / (two + three))
