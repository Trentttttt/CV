# -*- coding: UTF-8 -*-
import kungfu.yijinjing.time as kft
from kungfu.wingchun.constants import *
import numpy as np
import time

QNT = {
    "name": "QNTUSDT",
    "L": 2132.700394,
    "pa": 0.073544,
    "pb": 0.14229,
    "decimal_p": 2,
    "decimal_v": 1,
    "range": 4.5 / 100,

    "proportion": None,
    "future_pos": 0,
    "x": 0,
    "price": None
}

ENS = {
    "name": "ENSUSDT",
    "L": 9482.259289,
    "pa": 0.008431703,
    "pb": 0.01338276,
    "decimal_p": 3,
    "decimal_v": 1,
    "range": 4.5/100,

    "proportion": None,
    "future_pos": 0,
    "x": 0,
    "price": None
}

MATIC = {
    "name": "MATICUSDT",
    "L": 20866.29212,
    "pa": 0.00045119,
    "pb": 0.00068668,
    "decimal_p": 4,
    "decimal_v": 0,
    "range": 5 / 100,

    "proportion": None,
    "future_pos": 0,
    "x": 0,
    "price": None
}

LINK = {
    "name": "LINKUSDT",
    "L": 6394.857032,
    "pa": 0.0037963,
    "pb": 0.0060618,
    "decimal_p": 3,
    "decimal_v": 2,
    "range": 3.5 / 100,

    "proportion": None,
    "future_pos": 0,
    "x": 0,
    "price": None
}


ETH = {
    "name": "ETHUSDT",
    "decimal_p": 2,
    "decimal_v": 3,
    "future_pos": 0,
    "price": None
}

pairs = [QNT, ENS, MATIC, LINK]

account = {
    "source": "exbian",
    "account": "f010",
    "exchange": "BIAN"
}


# 定义调仓计算
def _get_theory_x(make_order):
    # 初始化参数
    p = np.array([i["proportion"] for i in pairs])
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
    return x, x_v, y, y_v


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
    context.subscribe(account["source"], [i["name"] for i in pairs + [ETH]], account["exchange"])
    context.x = np.array([])
    context.future_pos = np.array([])
    context.future_id = None
    context.x_v = None
    context.mode_ = "test"
    context.future_cancelled = [1, 2]
    context.eth_cancelled = [1, 2]
    context.trade_vol = 0
    context.start = context.now() * 2
    context.start2 = context.now() * 2
    context.eth_id = None
    context.y = None
    context.y_a = None
    context.delta_y = None
    context.one_time = 1


# 启动后调用函数，策略连接上行情交易柜台后调用，本函数回调后，策略可以执行添加时间回调、获取策略持仓、报单等操作
def post_start(context):
    # 初始仓位更新——合约
    for i in pairs + [ETH]:
        i["future_pos"] = _get_position_ok(i["name"], context) - 50
        context.log.info(f"[{i['name']} initial_position: {i['future_pos']}]")
    context.future_pos = np.array([i["future_pos"] for i in pairs])


# 收到快照行情时回调，行情信息通过quote对象获取
def on_quote(context, quote):
    # 过滤为0的价格行情
    if quote.best_ask == 0 or quote.best_bid == 0:
        return

    # 记录价格——U本位
    for dic in pairs + [ETH]:
        if quote.instrument_id == dic["name"]:
            dic["price"] = (quote.best_ask + quote.best_bid) / 2
            # context.log.info(f"[{dic['name']}], price: {dic['price']}")

    # context.log.info(f"{quote}")
    for dic in pairs + [ETH]:
        if dic['price'] is None:
            return

    # 计算价格——ETH本位
    for dic in pairs:
        dic["proportion"] = dic["price"] / ETH["price"]

    # 记录初始的ETH现货
    if context.one_time == 1:
        context.one_time = 0
        _, _, context.y, _ = _get_theory_x(1)
        context.log.info(f"initial y is {context.y}")

    # 价格变动时，现货数量改变
    context.x, context.x_v, _, _ = _get_theory_x(0)
    for i, j in enumerate(context.x):
        pairs[i]["x"] = j
    # 现货数量发生改变，则《净头寸》和《虚拟库存》改变
    net_pos = context.x + context.future_pos
    total_x = context.x + context.x_v
    # 则比例发生改变
    delta_x = abs(net_pos) / total_x

    # 计算下单数量
    context.x, context.x_v, _y, _yv = _get_theory_x(1)
    for i, j in enumerate(context.x):
        pairs[i]["x"] = j
    # 现货数量发生改变，则《净头寸》和《虚拟库存》改变
    net_pos = context.x + context.future_pos

    if context.mode_ == "test":
        context.log.info(f"context.x:{context.x},future_pos{context.future_pos},x_v{context.x_v}")
        context.log.info(f"net_pos:{net_pos},total_x{total_x},delta_x{delta_x}")
        context.log.info(f"context.y:{_y}, context.y_v:{_yv}")

    if context.mode_ == "trade":
        # 迭代比列
        for i, delta in enumerate(delta_x):
            # 比例超过允许范围
            if delta_x[i] > pairs[i]["range"] and context.future_id is None:
                context.trade_vol = int(round(abs(net_pos[i]), pairs[i]["decimal_v"]) * 1000)
                context.y_a = _get_theory_x(make_order=1)[2]
                context.log.info(f"y_a is {context.y_a}")
                # 净头寸小于0——买平
                if net_pos[i] < 0 and context.trade_vol != 0:
                    take_price = round(pairs[i]["price"] * 1.01, pairs[i]["decimal_p"])
                    order_id = context.insert_order(pairs[i]['name'], account['exchange'], account["account"],
                                                    take_price, context.trade_vol,
                                                    PriceType.Limit, Side.Buy, Offset.Close)
                    context.future_id = order_id
                    context.log.info(f"order_id_now: {context.future_id}")
                    context.log.info(
                        f"{pairs[i]['name']}[MAKE ORDER BUY CLOSE]:[{order_id}], [VOLUME:] {context.trade_vol} [PRICE] {take_price} ")
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
                        f"{pairs[i]['name']}[MAKE ORDER SELL OPEN]:[{order_id}], [VOLUME:] {context.trade_vol} [PRICE] {take_price}")
                    context.start = context.now()

    # 订单超时
    if context.now() - context.start > (4 * (10 ** 9)) and context.future_id is not None:
        # 撤单
        action_id = context.cancel_order(context.future_id)
        context.log.info(f"THE RETURN OF CANCEL_ORDER: [{action_id}]")
        context.log.info(f"[CANCEL ORDER COMMAND SENT]: [{context.future_id}]")
        context.start = context.now() * 2

    # ETH撤单计时
    if context.now() - context.start2 > (4 * (10 ** 9)) and context.eth_id is not None:
        # 撤单
        action_id = context.cancel_order(context.eth_id)
        context.log.info(f"THE RETURN OF CANCEL_ORDER: [{action_id}]")
        context.log.info(f"[CANCEL ORDER COMMAND SENT]: [{context.eth_id}]")
        context.start2 = context.now() * 2


# 收到订单状态回报时回调
def on_order(context, order):
    context.log.info(order.status)
    # 非本位币成交
    if order.status == OrderStatus.Filled and order.order_id == context.future_id:
        # 结束计时
        context.start = context.now() * 2
        context.log.info(
            f"{order.instrument_id} ORDER [{order.order_id}] SUCCESS TRADED, VOLUME:{order.volume_traded / 1000}")

        # 成交信息
        k = list(map(lambda x: x['name'], pairs)).index(order.instrument_id)
        pair_side = order.side

        # ETH报单数量
        eth_vol = int(round(abs(context.y[k] - context.y_a[k]), ETH["decimal_v"]) * 1000)

        if pair_side == Side.Buy:
            eth_price = round(ETH["price"] * 0.99, ETH["decimal_p"])
            eth_order_id = context.insert_order(ETH["name"], account['exchange'], account["account"],
                                                eth_price, eth_vol,
                                                PriceType.Limit, Side.Sell, Offset.Close)
            context.eth_id = eth_order_id
            context.log.info(f"[MAKE ORDER SELL OPEN]:[{eth_order_id}], [VOLUME:] {eth_vol} [ETH]")
            context.start2 = context.now()

        if pair_side == Side.Sell:
            eth_price = round(ETH["price"] * 1.01, ETH["decimal_p"])
            eth_order_id = context.insert_order(ETH["name"], account['exchange'], account["account"],
                                                eth_price, eth_vol,
                                                PriceType.Limit, Side.Buy, Offset.Open)
            context.eth_id = eth_order_id
            context.log.info(f"[MAKE ORDER BUY OPEN]:[{eth_order_id}], [VOLUME:] {eth_vol} [ETH]")
            context.start2 = context.now()

    # 本位币ETH成交
    if order.status == OrderStatus.Filled and order.order_id == context.eth_id:
        context.log.info(f"ETH ORDER [{order.order_id}] SUCCESS TRADED, VOLUME:{order.volume_traded / 1000}")
        context.future_id = None
        context.eth_id = None
        context.y = context.y_a.copy()
        context.log.info(f"y is updated to {context.y}")

    # 非本位币部分成交对齐ETH
    if order.status == OrderStatus.Cancelled and order.order_id == context.future_id and context.future_id is not None:
        context.log.info("[SUCCESS CANCELLED]{} ".format(order.order_id))
        context.future_cancelled.append(order.order_id)

        # 全部未成交
        if context.future_cancelled[-1] != context.future_cancelled[-2] and order.volume_left == context.trade_vol:
            context.future_id = None

        # 部分成交，不进入Filled
        if context.future_cancelled[-1] != context.future_cancelled[-2] and order.volume_left < context.trade_vol:
            vol_left = int(order.volume_left)
            k = list(map(lambda x: x['name'], pairs)).index(order.instrument_id)
            pair_side = order.side

            if pair_side == Side.Buy:
                take_price = round(pairs[k]["price"] * 1.01, pairs[k]["decimal_p"])
                order_id = context.insert_order(pairs[k]['name'], account['exchange'], account["account"],
                                                take_price, int(vol_left),
                                                PriceType.Limit, Side.Buy, Offset.Close)
                context.future_id = order_id
                context.log.info(f"order_id_now: {context.future_id}")
                context.log.info(
                    f"{pairs[k]['name']}[MAKE ORDER BUY CLOSE]:[{order_id}], [VOLUME:] {vol_left} [PRICE] {take_price}")
                context.start = context.now()

            if pair_side == Side.Sell:
                take_price = round(pairs[k]["price"] * 0.99, pairs[k]["decimal_p"])
                order_id = context.insert_order(pairs[k]['name'], account['exchange'], account["account"],
                                                take_price, int(vol_left),
                                                PriceType.Limit, Side.Sell, Offset.Open)
                context.future_id = order_id
                context.log.info(f"order_id_now: {context.future_id}")
                context.log.info(
                    f"{pairs[k]['name']}[MAKE ORDER SELL OPEN]:[{order_id}], [VOLUME:] {vol_left} [PRICE] {take_price}")
                context.start = context.now()

    # 本位币部成需确保成功
    if order.status == OrderStatus.Cancelled and order.order_id == context.eth_id and context.eth_id is not None:
        # 部分已经成交，不会进入到Filled语句中；
        if context.eth_cancelled[-1] != context.eth_cancelled[-2] and order.volume_left <= context.trade_vol:
            context.log.info(f"{order.volume_left}")
            # ETH继续发剩下没成交的量
            eth_price = round(ETH["price"], ETH["decimal_p"])
            eth_order_id = context.insert_order(ETH["name"], account['exchange'], account["account"],
                                                eth_price, int(order.volume_left),
                                                PriceType.Limit, order.side, order.offset)
            context.eth_id = eth_order_id
            context.log.info(
                f"[MAKE ORDER {order.side} {order.offset}]:[{eth_order_id}], [VOLUME:] {order.volume_left} [ETH]")
            context.start2 = context.now()


# 更新仓位时回调
def on_seldefposition(context, seldefposition):
    for i in pairs + [ETH]:
        if seldefposition.instrument_id == i["name"]:
            i["future_pos"] = seldefposition.volume / 1000 - 50
        context.log.info(f"[{i['name']}] real position is [{i['future_pos']}]")
    context.future_pos = np.array([i["future_pos"] for i in pairs])


# 订单错误信息时回调
def on_order_action_error(context, error):
    time.sleep(3)
    if error.error_msg[8:13] in ['-4016', '-4024']:
        context.start = context.now() * 2
        context.start2 = context.now() * 2
        context.future_id = None

    # 报告订单错误信息
    context.log.error("on_order_action_error:{}".format(error))
