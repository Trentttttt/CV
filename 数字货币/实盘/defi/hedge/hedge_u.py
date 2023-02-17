# -*- coding: UTF-8 -*-
import time

import kungfu.yijinjing.time as kft
from kungfu.wingchun.constants import *
import numpy as np


ETH = {
    "name": "ETHUSDT",
    "L": 16.94655192,
    "pa": 900,
    "pb": 1400,
    "decimal_p": 2,
    "decimal_v": 3,
    "range": 1 / 100,

    "future_pos": 0,
    "x": 0,
    "price": None
}


pairs = [ETH]

account = {
    "source": "exbian",
    "account": "wcy",
    "exchange": "BIAN"
}


# 定义调仓计算
def _get_theory_x(make_order):
    # 初始化参数
    p = np.array([i["price"] for i in pairs])
    pb = np.array([i["pb"] for i in pairs])
    pa = np.array([i["pa"] for i in pairs])
    l = np.array([i["L"] for i in pairs])

    # 虚拟仓位固定不变
    x_v = l / np.sqrt(pb)
    y_v = l * np.sqrt(pa)

    # 真实仓位随着p改变
    if make_order == 1:
        for i, j in enumerate(p):
            p[i] = min(max(p[i], pa[i]), pb[i])

    x = l / np.sqrt(p) - x_v
    y = l * np.sqrt(p) - y_v
    return x, x_v


# 定义获取期货初始仓位
def _get_position_ok(tickers, context):
    hold_position = 0
    book = context.get_account_book(account["source"], account["account"])
    for _, pos in book.long_positions.items():
        if pos.instrument_id == tickers:
            hold_position += pos.volume
            # context.log.info(f"[pos] {pos}")
    for _, pos in book.short_positions.items():
        if pos.instrument_id == tickers:
            hold_position += pos.volume
            # context.log.info(f"[pos] {pos}")
    return hold_position / 1000


# 启动前回调，添加交易账户，订阅行情，策略初始化计算等
def pre_start(context):
    context.add_account(account["source"], account["account"], 100000.0)
    context.subscribe(account["source"], [i["name"] for i in pairs], account["exchange"])
    context.x = np.array([])
    context.future_pos = np.array([])
    context.future_id = None
    context.x_v = None
    context.mode_ = "test"
    context.future_cancelled = [1, 2]
    context.trade_vol = 0
    context.start = context.now() * 2
    context.error_time = 0


# 启动后调用函数，策略连接上行情交易柜台后调用，本函数回调后，策略可以执行添加时间回调、获取策略持仓、报单等操作
def post_start(context):
    # 初始仓位更新——合约
    for i in pairs:
        i["future_pos"] = _get_position_ok(i["name"], context)
        context.log.info(f"[{i['name']} initial_position: {i['future_pos']}]")
    context.future_pos = np.array([i["future_pos"] for i in pairs])


# 收到快照行情时回调，行情信息通过quote对象获取
def on_quote(context, quote):
    # 过滤为0的价格行情
    if quote.best_ask == 0 or quote.best_bid == 0:
        return

    # 记录价格
    for dic in pairs:
        if quote.instrument_id == dic["name"]:
            dic["price"] = (quote.best_ask + quote.best_bid) / 2
            # context.log.info(f"[{dic['name']}], price: {dic['price']}")

    for dic in pairs:
        if dic['price'] is None:
            return

    # context.log.info(f"{quote}")

    # 价格变动时，现货数量改变
    context.x, context.x_v = _get_theory_x(0)
    for i, j in enumerate(context.x):
        pairs[i]["x"] = j
    # 现货数量发生改变，则《净头寸》和《虚拟库存》改变
    net_pos = context.x + context.future_pos
    total_x = context.x + context.x_v
    # 则比例发生改变
    delta_x = abs(net_pos) / total_x

    # 计算下单数量
    context.x, context.x_v = _get_theory_x(1)
    for i, j in enumerate(context.x):
        pairs[i]["x"] = j
    # 现货数量发生改变，则《净头寸》和《虚拟库存》改变
    net_pos = context.x + context.future_pos

    if context.mode_ == "test":
        context.log.info(f"context.x:{context.x},future_pos{context.future_pos},x_v{context.x_v}")
        context.log.info(f"net_pos:{net_pos},total_x{total_x},delta_x{delta_x}")

    if context.mode_ == "trade":
        # 迭代比列
        for i, delta in enumerate(delta_x):
            # 比例超过允许范围
            if delta_x[i] > pairs[i]["range"] and context.future_id is None and context.now() - context.error_time > (10 * (10 ** 9)):
                context.trade_vol = int(round(abs(net_pos[i]), pairs[i]["decimal_v"]) * 1000)
                # 净头寸小于0——买平
                if net_pos[i] < 0 and context.trade_vol != 0:
                    take_price = round(pairs[i]["price"] * 1.01, pairs[i]["decimal_p"])

                    order_id = context.insert_order(pairs[i]['name'], account['exchange'], account["account"],
                                                    take_price, context.trade_vol,
                                                    PriceType.Limit, Side.Buy, Offset.Close)
                    context.future_id = order_id
                    context.log.info(f"order_id_now: {context.future_id}")
                    context.log.info(
                        f"{pairs[i]['name']}[MAKE ORDER BUY CLOSE]:[{order_id}], [VOLUME:] {context.trade_vol} [price] {take_price} ")
                    context.start = context.now()

                # 净头寸大于0——卖开
                if net_pos[i] > 0 and context.trade_vol != 0:
                    take_price = round(pairs[i]["price"] * 0.99, pairs[i]["decimal_p"])
                    order_id = context.insert_order(pairs[i]['name'], account['exchange'], account["account"],
                                                    take_price, context.trade_vol,
                                                    PriceType.Limit, Side.Sell, Offset.Open)
                    context.future_id = order_id
                    context.log.info(f"order_id_now: {context.future_id}")
                    context.log.info(
                        f"{pairs[i]['name']}[MAKE ORDER SELL OPEN]:[{order_id}], [VOLUME:] {context.trade_vol} [price] {take_price} ")
                    context.start = context.now()

    # 订单超时
    if context.now() - context.start > (4 * (10 ** 9)) and context.future_id is not None:
        # 撤单
        action_id = context.cancel_order(context.future_id)
        context.log.info(f"THE RETURN OF CANCEL_ORDER: [{action_id}]")
        context.log.info(f"[CANCEL ORDER COMMAND SENT]: [{context.future_id}]")
        context.start = context.now() * 2


# 收到订单状态回报时回调
def on_order(context, order):
    # 全部成交
    if order.status == OrderStatus.Filled and order.order_id == context.future_id:
        context.future_id = None
        # 结束计时
        context.start = context.now() * 2
        # 报告成交数量
        context.log.info(
            f"{order.instrument_id} ORDER [{order.order_id}] SUCCESS TRADED, VOLUME:{order.volume_traded / 1000}")

    # 撤单成功（包含部分成交部分撤单）
    if order.status == OrderStatus.Cancelled and order.order_id == context.future_id and context.future_id is not None:
        context.log.error(
            f"volume_traded:{order.volume_traded}, volume_left:{order.volume_left}, volume:{order.volume}, volume_condition:{order.volume_condition}")
        context.log.info("[cancel order](rid){} ".format(order.order_id))
        context.future_cancelled.append(order.order_id)
        if context.future_cancelled[-1] != context.future_cancelled[-2]:
            context.future_id = None

    # 订单错误
    if order.status == OrderStatus.Error:
        # 报告错误
        context.log.error(f"[######################ORDER WITH ERROR##################]:{order.order_id}")


# 更新仓位时回调
def on_seldefposition(context, seldefposition):
    for i in pairs:
        if seldefposition.instrument_id == i["name"]:
            i["future_pos"] = seldefposition.volume / 1000
        context.log.info(f"[{i['name']}] real position is [{i['future_pos']}]")
    context.future_pos = np.array([i["future_pos"] for i in pairs])


# 订单错误信息时回调
def on_order_action_error(context, error):
    if error.error_msg[8:13] in ['-4016', '-4024', '-1001', '-4003']:
        context.error_timer = context.now()
        context.start = context.now() * 2
        context.future_id = None

    # 报告订单错误信息
    context.log.error("on_order_action_error:{}".format(error))
