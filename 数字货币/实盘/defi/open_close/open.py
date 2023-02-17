# -*- coding: UTF-8 -*-
import kungfu.yijinjing.time as kft
from kungfu.wingchun.constants import *
import numpy as np
import time

# 初始参数
tickers = ['BTCUSDT']
basis_in = [-0.129]
spot_init_price = [333]
p_decimal = [2]
vol_each = np.array([2])
vol_end = np.array([165.0+213.59-2])

spot = {
    "account": "s009",

    "ticker": tickers,
    "last": np.array([float(0)] * len(tickers)),
    "exchange": "BINANCE",
    "source": "binance"
}

future = {
    "account": "f009",

    "ticker": tickers,
    "exchange": "BIAN",
    "source": "exbian",
    "ask": np.array([float(0)] * len(tickers)),
    "bid": np.array([float(0)] * len(tickers))
}


# 获取期货初始仓位
def _get_position_ok(ticker, context):
    hold_position = 0
    book = context.get_account_book(future["source"], future["account"])
    for _, pos in book.long_positions.items():
        if pos.instrument_id == ticker:
            hold_position += pos.volume
            # context.log.info(f"[pos] {pos}")
    for _, pos in book.short_positions.items():
        if pos.instrument_id == ticker:
            hold_position += pos.volume
            # context.log.info(f"[pos] {pos}")
    return hold_position / 1000


# 启动前回调，添加交易账户，订阅行情，策略初始化计算等
def pre_start(context):
    context.add_account(spot["source"], spot["account"], 100000.0)
    context.add_account(future["source"], future["account"], 100000.0)
    context.subscribe(spot["source"], spot["ticker"], spot["exchange"])
    context.subscribe(future["source"], future["ticker"], future["exchange"])

    n = len(tickers)
    context.spot_order_id = [[1, 2] for x in range(n)]
    context.basis = np.array([float(0)] * n)
    context.real_position = np.array([float(0)] * n)
    context.future_id = np.array([None] * n)
    context.future_cancelled = [[1, 2] for x in range(n)]
    context.need_make_up = [[] for x in range(n)]
    # 目标仓位 = (账户资金/现货价格) * 1000
    context.target_position = vol_end

    context.start = np.array([[context.now() * 2] for x in range(n)])
    context.log.info(f"pre_start finished")


# 启动后调用函数，策略连接上行情交易柜台后调用，本函数回调后，策略可以执行添加时间回调、获取策略持仓、报单等操作
def post_start(context):
    context.log.info(f"{context}")
    # 初始仓位更新
    for k in range(len(tickers)):
        context.real_position[k] = _get_position_ok(tickers[k], context)
        context.log.info(f"[{tickers[k]} initial_position:] {context.real_position[k]}")
        context.log.info(f"[{tickers[k]} target_position:] {context.target_position[k]}")
        time.sleep(1)
    context.log.info("post_start finished")


# 收到快照行情时回调，行情信息通过quote对象获取
def on_quote(context, quote):
    # context.log.info(f"{quote}")
    # 记录当前ticker的位置
    k = tickers.index(quote.instrument_id)

    # 期货行情
    if quote.exchange_id == future["exchange"] and quote.instrument_id == tickers[k]:
        future["ask"][k] = quote.best_ask
        future["bid"][k] = quote.best_bid

    # 现货行情
    if quote.exchange_id == spot["exchange"]:
        spot["last"][k] = quote.last_price
        # 基差记录(期货-现货)
        context.basis = (future["ask"] + future["bid"]) / 2 - spot["last"]
        context.log.info(f"current basis : {context.basis}")

    if 0 in list(spot['last']) + list(future['ask']) + list(future['bid']):
        return

    # 期货大于现货 + 期货仓位小于目标仓位——挂单开仓/maker
    if context.basis[k] > basis_in[k] and \
            context.real_position[k] > context.target_position[k] and \
            context.future_id[k] is None:
        context.log.info(f"[{tickers[k]}] current basis in {context.basis} {int(vol_each[k])}")
        # 卖开(ask价格)期货合约
        future_id = context.insert_order(future["ticker"][k], future["exchange"], future["account"],
                                         future["ask"][k], int(vol_each[k] * 1000), PriceType.Limit,
                                         Side.Sell, Offset.Open)

        context.log.info("[basis] {}".format(context.basis))
        context.log.info(f"[order_id_now]: {future_id}")

        # 记录order_id
        context.future_id[k] = future_id
        # 计时开始
        context.start[k] = context.now()
        # context.log.info(f"[CURRENT BASIS:] {context.basis}")
        context.log.info(f"MAKE ORDER SELL OPEN:[{future_id}], [VOLUME:] {int(vol_each[k])} [FUTURE]")

    # 订单超时
    if context.now() - context.start[k] > (2 * (10 ** 9)) and context.future_id[k] is not None:
        # 撤单
        action_id = context.cancel_order(context.future_id[k])
        # context.log.info(f"THE RETURN OF CANCEL_ORDER: [{action_id}]")
        context.log.info(f"[{tickers[k]}]CANCEL ORDER COMMAND SENT: [{context.future_id[k]}]")
        context.start[k] = context.now() * 2


# 收到订单状态回报时回调
def on_order(context, order):
    k = tickers.index(order.instrument_id)
    # 成交期货
    if order.status == OrderStatus.Filled and order.exchange_id == future["exchange"]:
        # 结束计时
        context.start[k] = context.now() * 2
        # 报告期货成交数量
        context.log.info(f"FUTURE ORDER [{context.future_id[k]}] SUCCESS TRADED, VOLUME:{order.volume_traded / 1000}")
        # 买开现货(last+1价位)——taker
        order_id = context.insert_order(spot["ticker"][k], spot["exchange"], spot["account"],
                                        round(spot["last"][k] * 1.02, p_decimal[k]), int(vol_each[k] * 10000),
                                        PriceType.Limit, Side.Buy, Offset.Open)
        # 报告买入订单
        context.log.info(f"[{tickers[k]}] MAKE ORDER BUY OPEN:[{order_id}], [VOLUME:] {vol_each[k]} [SPOT]")

    # 成交现货
    if order.status == OrderStatus.Filled and order.exchange_id == spot["exchange"]:
        context.spot_order_id[k].append(order.order_id)
        if context.spot_order_id[k][-1] != context.spot_order_id[k][-2]:
            # 重置买入信号
            context.future_id[k] = None
            # 报告现货成交数量
            context.log.info(f"[{tickers[k]}] ORDER [{order.order_id}] SUCCESS TRADED "
                             f"VOLUME:{order.volume_traded / 10000} [SPOT]")

    # 撤单成功
    if order.status == OrderStatus.Cancelled and \
            order.order_id == context.future_id[k] and \
            context.future_id[k] is not None:
        context.log.info(f"[{tickers[k]}] ORDER [{order.order_id}] SUCCESS CANCELLED [FUTURE]")
        context.log.info(f"[{tickers[k]}] [volume_traded]:{order.volume_traded / 1000} "
                         f"[volume_left]:{order.volume_left / 1000}")
        context.future_cancelled[k].append(order.order_id)
        # 部分已经成交了
        if order.volume_left < vol_each[k] * 1000 and \
                context.future_cancelled[k][-1] != context.future_cancelled[k][-2]:
            # 那么本次需要补仓
            make_up1 = order.volume_traded / 1000
            make_up = make_up1 + sum(context.need_make_up[k])
            # 如果补仓的现货足够100U
            if make_up * spot_init_price[k] > 100:
                # 买开现货(last-1价位)——taker
                order_id = context.insert_order(spot["ticker"][k], spot["exchange"], spot["account"],
                                                round(spot["last"][k] * 1.02, p_decimal[k]), int(make_up * 10000),
                                                PriceType.Limit, Side.Buy, Offset.Open)
                # 报告卖出订单
                context.log.info(f"[{tickers[k]}][MAKE ORDER BUY OPEN]:[{order_id}], [VOLUME:] {make_up} [SPOT]")
                context.need_make_up[k] = []
            # 不足100U的要补仓量先记录下来
            else:
                context.need_make_up[k].append(make_up1)
                context.log.info(f"{tickers[k]} NEED TO MAKE UP {make_up1} SPOT")
                context.future_id[k] = None

        if order.volume_left == vol_each[k] * 1000:
            # 重新发单
            context.future_id[k] = None


# 更新仓位时回调
def on_seldefposition(context, seldefposition):
    k = tickers.index(seldefposition.instrument_id)
    # 期货仓位有更新
    if seldefposition.exchange_id == future["exchange"]:
        context.real_position[k] = seldefposition.volume / 1000
        # 报告期货目前仓位
        context.log.info(f"[{tickers[k]}][*******************Current position*********************:] {seldefposition.volume / 1000}")


# 订单错误信息时回调
def on_order_action_error(context, error):
    # 报告订单错误信息
    context.log.error("on_order_action_error:{}".format(error))
