try:
    import unicorn_binance_rest_api
except ImportError:
    print("Please install `unicorn-binance-rest-api`! https://pypi.org/project/unicorn-binance-rest-api/")
    sys.exit(1)

binance_com_api_key = ...
binance_com_api_secret = ...

from unicorn_binance_websocket_api.unicorn_binance_websocket_api_manager import BinanceWebSocketApiManager
from unicorn_binance_rest_api.unicorn_binance_rest_api_manager import BinanceRestApiManager
import logging
import time
import threading
import os
import math
import random
import numpy as np

# https://docs.python.org/3/library/logging.html#logging-levels
logging.basicConfig(level=logging.INFO,
                    filename=os.path.basename(__file__) + '.log',
                    format="{asctime} [{levelname:8}] {process} {thread} {module}: {message}",
                    style="{")


def print_stream_data_from_stream_buffer(binance_websocket_api_manager):
    while True:
        if binance_websocket_api_manager.is_manager_stopping():
            exit(0)
        oldest_stream_data_from_stream_buffer = binance_websocket_api_manager.pop_stream_data_from_stream_buffer()
        if oldest_stream_data_from_stream_buffer is False:
            time.sleep(0.01)
        else:
            print(oldest_stream_data_from_stream_buffer)

'''SYMBOL PARAMETERS'''
symbol = ... #символ
pr_p=... #округление цены
pr_s=... #округление сайза

# create instances of BinanceWebSocketApiManager
binance_com_websocket_api_manager = BinanceWebSocketApiManager(exchange="binance.com-futures",
                                                               throw_exception_if_unrepairable=True,
                                                               stream_buffer_maxlen=100, output_default='dict')
binance_com_rest_api_manager = BinanceRestApiManager(api_key=binance_com_api_key, api_secret=binance_com_api_secret)

# # create the userData streams
binance_com_user_data_stream_id = binance_com_websocket_api_manager.create_stream('arr', '!userData',
                                                                                  api_key=binance_com_api_key,
                                                                                  api_secret=binance_com_api_secret,
                                                                                  output="UnicornFy",
                                                                                  stream_buffer_name='user')

# create the bookticker streams
bookTicker_arr_stream_id = binance_com_websocket_api_manager.create_stream(["bookTicker"], markets=symbol,
                                                                           stream_buffer_name='book')

# start a worker process to move the received stream_data from the stream_buffer to a print function
worker_thread = threading.Thread(target=print_stream_data_from_stream_buffer, args=(binance_com_websocket_api_manager,))
worker_thread.start()
# monitor the streams

# preparation for trading
wap = 0
spread = 0
wap_window = []
spread_window = []

for i in range(8):
    data = binance_com_rest_api_manager.futures_orderbook_ticker(symbol=symbol)
    a = float(data.get('askPrice'))
    b = float(data.get('bidPrice'))
    A = float(data.get('askQty'))
    B = float(data.get('bidQty'))
    spread = a - b
    wap = (a * B + b * A) / (A + B)
    wap_window.append(wap)
    spread_window.append(spread)
    std_spread = np.std(spread_window)
    std_wap = np.std(wap_window)

print("Я ВСЁ ПОСЧИТАЛ НАЧАЛЬНИК")
'''основные параметры'''
min_size = 100
std_spread = np.std(spread_window)
mean_spread = np.mean(spread_window)

'''параметры символа'''
symbol = 'celrusdt'
pr_p=5
pr_s=0

curr_pos = 0
pos = 0
avg_price = 0
mpu = 700  # max pose usd
mos = 0.025  # max order size as % of mpu
price_buy = round(min(wap * 0.9990, wap - mean_spread * (1 + std_spread)) , pr_p)
price_sell = round(max(wap * 1.0010, wap + mean_spread * (1 + std_spread)) , pr_p)
size = math.floor(mos * mpu / wap)
d_flag = 0 #flag on dokupka
#create first trading orders
print('СТАВЛЮ ОРДЕРА, ПОГНАЛИ')

start=time.time()
binance_com_rest_api_manager.futures_create_order(symbol=symbol, quantity=size, type='LIMIT', side='BUY',
                                                  newClientOrderId='SimpleBuy1', price=price_buy, timeInForce='GTC')
finish=time.time()-start
print('delay',finish)
start=time.time()
binance_com_rest_api_manager.futures_create_order(symbol=symbol, quantity=size, type='LIMIT', side='SELL',
                                                  newClientOrderId='SimpleSell1', price=price_sell, timeInForce='GTC')
finish=time.time()-start
print('delay',finish)
print('ПОСТАВИЛ, УРА МЫ БАНКРОТЫ')

while True:
    msg2 = binance_com_websocket_api_manager.pop_stream_data_from_stream_buffer(stream_buffer_name='book', mode='LIFO')
    if msg2:
        if msg2.get('stream') is not None:
            del wap_window[0]
            del spread_window[0]
            a = float(msg2.get('data').get('a'))
            b = float(msg2.get('data').get('b'))
            A = float(msg2.get('data').get('A'))
            B = float(msg2.get('data').get('B'))
            wap = (a*B+b*A)/(A+B)
            spread = a - b
            wap_window.append(wap)
            spread_window.append(spread)
            std_spread = np.std(spread_window)
            std_wap = np.std(wap_window)

    size = round((mos*mpu/wap)*(1+(curr_pos/mpu)), pr_s)
    curr_pos = abs(pos) * avg_price
    price_buy = round(min(wap * 0.9980, wap*0.9980*(1-std_wap) - spread * (1 + std_spread)), pr_p)
    price_sell = round(max(wap * 1.0020, wap*1.0010*(1+std_wap) + spread * (1 + std_spread)), pr_p)


    msg1 = binance_com_websocket_api_manager.pop_stream_data_from_stream_buffer(stream_buffer_name='user',mode='LIFO')
    if msg1:
        if curr_pos < mpu:
            if msg1.get('stream_type') == 'ACCOUNT_UPDATE' and len(msg1.get('positions')) > 0: #quick fix index error on pos
                 pos = float(msg1.get('positions')[0].get('position_amount')) #get current position
                 tp_size=max(min_size,abs(pos))
                 avg_price = round(float(msg1.get('positions')[0].get('entry_price')) , pr_p)
                 avg_price_sell = round(float(msg1.get('positions')[0].get('entry_price')) * 0.9980, pr_p) #get position average price
                 avg_price_buy = round(float(msg1.get('positions')[0].get('entry_price')) * 1.0020, pr_p)
                 if pos < 0: #sell triggered
                     new_size = max(min_size, round(size * random.uniform(0.8, 1),pr_s))
                     i=random.randrange(1,10)
                     binance_com_rest_api_manager.futures_cancel_all_open_orders(symbol=symbol)
                     binance_com_rest_api_manager.futures_create_order(symbol=symbol,type='LIMIT',quantity = tp_size, side ='BUY',
                                                                       newClientOrderId='SellTP',price=avg_price_sell, timeInForce='GTC')
                     binance_com_rest_api_manager.futures_create_order(symbol=symbol,type='LIMIT',quantity=new_size, side='SELL',
                                                                       newClientOrderId=f'SimpleSell{i}',price=price_sell, timeInForce='GTC')
                     print("Short")
                 if pos > 0: #buy triggered
                     new_size = max(min_size, round(size * random.uniform(0.8, 1),pr_s))
                     i = random.randrange(1, 10)
                     binance_com_rest_api_manager.futures_cancel_all_open_orders(symbol=symbol)
                     binance_com_rest_api_manager.futures_create_order(symbol=symbol,type='LIMIT',quantity=tp_size, side ='SELL',
                                                                       newClientOrderId='BuyTP',price=avg_price_buy, timeInForce='GTC')
                     binance_com_rest_api_manager.futures_create_order(symbol=symbol,type='LIMIT',quantity=new_size, side='BUY',
                                                                       newClientOrderId=f'SimpleBuy{i}',price=price_buy, timeInForce='GTC')
                     print("Long")
                 if pos == 0:  # flat triggered
                     new_size = max(min_size, round(size * random.uniform(0.8, 1),pr_s))

                     binance_com_rest_api_manager.futures_cancel_all_open_orders(symbol=symbol)
                     start=time.time()
                     binance_com_rest_api_manager.futures_create_order(symbol=symbol, type='LIMIT', quantity=new_size, side='BUY',
                                                                       newClientOrderId='SimpleBuy', price=price_buy, timeInForce='GTC')
                     finish = time.time() - start
                     print('delay', finish)
                     binance_com_rest_api_manager.futures_create_order(symbol=symbol, type='LIMIT', quantity=new_size, side='SELL',
                                                                       newClientOrderId='SimpleSell', price=price_sell, timeInForce='GTC')
                     print("Flat")
        elif curr_pos >= mpu:
            if msg1.get('stream_type') == 'ACCOUNT_UPDATE' and len(msg1.get('positions')) > 0: #quick fix index error on pos
                 pos = float(msg1.get('positions')[0].get('position_amount')) #get current position
                 tp_size=max(min_size,(pos))
                 avg_price = round(float(msg1.get('positions')[0].get('entry_price')) , pr_p)
                 avg_price_sell = round(float(msg1.get('positions')[0].get('entry_price')) * 0.9980, pr_p) #get position average price
                 avg_price_buy = round(float(msg1.get('positions')[0].get('entry_price')) * 1.0020, pr_p)
                 pass

