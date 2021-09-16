# binance_trading_bot
Simple trading bot for binance. I call him The Great Usrednitel'.

This bot is using unicorn-binance-suite library for websocket connection and rest api requests.
https://github.com/oliver-zehentleitner/unicorn-binance-suite

Strategy is the following:
Place buy and sell orders simultaneously with some correction : either 10 bps away from current weighted average price(wap) or wap corrected on mean spread and std of spread.

When the first order got hit - place 2 orders: 1. take profit order 20 bps away from average price of your pose 2. order that will average down/up the price of your position with price corrected for std of wap, spread and std of spread. 

Move your take profit order while averaging the price of your position.

Increase the size of your orders while increasing total current position. 

When it is working:
Most of the time crypto-markets are mean-reverting on small time-frames with significant volatility on low-cap tokens (Confession: I haven't tested it, just common sence and experience). This means that trading in the range of 20bps will result in the large number of small profit deals. Even when there is a trend in the market, the volatility of this trend makes the probability of take-profit order execution high.

When it is not working:
Fast one direction moves ( pumps without dumps, or dumps without pumps:) ), slow one direction moves with low volatility.

How to counter pitfalls:
See plans for improvement. Generally the main counter is to select tokens which are appropriate for this strategy. 

Plans for impovement:
Trade more than one symbol (though most of them are highly correlated)
Add predictor in order to get the best price of execution
