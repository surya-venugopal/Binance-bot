from tradingview_ta import TA_Handler, Interval, Exchange
from binance.client import Client
from binance import ThreadedWebsocketManager
from time import sleep
import sys
import datetime
import ccxt
from ta.trend import MACD,EMAIndicator,SMAIndicator
from ta.volatility import AverageTrueRange
import math
import pandas as pd
# import utils2 as utils

class bot:
    def __init__(self,coin):
        
        global tradeAmount
        # try:
        #     self.coin = sys.argv[1]
        # except:
        self.coin = coin
        print("Chosen coin : {}".format(self.coin))
        
        # a = int(sys.argv[2])
        # b = int(sys.argv[3])
        # c = int(sys.argv[4])
        if(self.coin != None):
            
            self.bsm = ThreadedWebsocketManager()
            self.bsm.start()
            self.bsm.start_symbol_ticker_socket(callback=self.on_message, symbol=self.coin)
            

        
        self.currentAmount = initialTradeAmount/no_of_coins
        self.previousAmount = initialTradeAmount/no_of_coins
        tradeAmount -= initialTradeAmount/no_of_coins

        # print("{} : initial Amount".format(self.currentAmount))

        self.currentCrypto = 0.0
        
        self.isBought = False  

        self.previousTime = None

        self.previousEMA = None
        self.previousPrice = 0

        self.crossed1st100 = False
        self.stopLossAt = 0
        self.arr = [0] * 100
        self.previousBuyTime = datetime.datetime.now()

    def on_message(self, msg):
        if msg['e'] != 'error':
            
            currentTime = datetime.datetime.now()
            currentPrice = float(msg['c'])
            
            if(self.previousTime != None and currentTime != self.previousTime): #and self.previousEMA != None
                
                if(self.isBought):
                    if(self.canSell(currentTime,currentPrice)):    
                        self.sell(currentPrice,currentTime)
                        self.isBought = False
                elif(self.previousPrice > currentPrice):
                    self.buy(currentPrice,currentTime)
                    self.isBought = True
                self.previousPrice = currentPrice
                if(currentTime.minute != self.previousTime.minute and currentTime.minute % 10 == 0):
                # if(True):

                    try:
                        print("{} : {} : current price {}$, current crypto : {},  current amount : {}$\n"
                        .format(self.coin,currentTime,currentPrice,round(self.currentCrypto,2),round(self.currentAmount,2)))
                        

                    except:
                        print("Collecting Data .. Please wait")

                    print("{} : Time lapsed : {}".format(self.coin,round((datetime.datetime.now() - self.previousBuyTime).total_seconds()/60)))

                    # if(not self.isBought):
                        # product = TA_Handler(
                        #     symbol=self.coin,
                        #     screener="crypto",
                        #     exchange="BINANCE",
                        #     interval=Interval.INTERVAL_1_MINUTE
                        # )
                        # indicators = product.get_analysis().indicators
                    
                        # if(self.previousEMA < indicators['EMA10']):
                        
                        # self.changeTime = datetime.datetime.now()
                        # self.buy(currentPrice,currentTime)
                        # self.isBought = True
                    

                        # self.previousEMA = indicators['EMA10']
                self.previousTime = currentTime
            else: 
                # if(self.previousEMA == None):
                #     indicators = TA_Handler(
                #         symbol=self.coin,
                #         screener="crypto",
                #         exchange="BINANCE",
                #         interval=Interval.INTERVAL_1_MINUTE
                #     ).get_analysis().indicators
                #     self.previousEMA = indicators['EMA10']
                self.previousTime = currentTime
        else:
            print("############################## ERROR RETRYING ##########################################")
            self.bsm.stop()
            del self.bsm
            sleep(300)
            self.bsm = ThreadedWebsocketManager()
            self.bsm.start()
            self.bsm.start_symbol_ticker_socket(callback=self.on_message, symbol=self.coin)

    def canSell(self,currentTime,currentPrice):     
        # if(not self.crossed1st100):
        #     self.crossed1st100 = currentPrice > self.previousPrice + self.previousPrice * 1/100
        if(self.stopLossAt!=0 and (currentPrice-self.stopLossAt)*100/self.stopLossAt < 0):
            return True
        
        # if((datetime.datetime.now() - self.previousBuyTime).total_seconds()/60 > 60 * 1):
        #     print("{} : Time Exceeded".format(self.coin))
            
        #     return True
        # if((datetime.datetime.now() - self.previousBuyTime).total_seconds()/60 > 30 * 1):
        #     self.arr[1] = self.arr[0] - self.arr[0] * 1 /100
        #     self.arr[2] = self.arr[0] + self.arr[0] * 0.2 /100
        #     for i in range(3,20,2):
        #         self.arr[i] = self.arr[0] + self.arr[0] * (i-1)*1/200
        #     for i in range(4,20,2):
        #         self.arr[i] = (self.arr[i-1] + self.arr[i+1]) /2

        #     if(self.stopLossAt < self.arr[1]):
        #         self.stopLossAt = self.arr[1]
        #         print("{} : Stoploss : {}".format(self.coin,self.stopLossAt))
            
        # if(self.crossed1st100):
        if(self.stopLossAt==0):
            self.stopLossAt = self.arr[1]
            print("{} : Stoploss : {}, Next Target : {}".format(self.coin,self.stopLossAt,self.arr[3]))
            
        a = self.stopLossAt
        for i in range(3,20):
            if(currentPrice<self.arr[i]):
                self.stopLossAt = max(self.stopLossAt,self.arr[i-2])
                if(self.stopLossAt != a):
                    self.previousBuyTime = datetime.datetime.now()
                    print("{} : Stoploss : {}, Next Target : {}".format(self.coin,self.stopLossAt,self.arr[i+1]))
                break
        return False

    def buy(self,price,time):
        self.arr[0] = price
        self.arr[1] = price - price * 20 / 100
        self.arr[2] = price + price * 0.3/100
        for i in range(3,20):
            self.arr[i] = price + price * (i-1)*0.8/100
        
        self.previousAmount = self.currentAmount
        order = client.order_market_buy(
            symbol=self.coin,
            quoteOrderQty = self.currentAmount)
        print(order)
        self.currentCrypto = float(order['executedQty'])

        print("\nBUY : {} : {} : current price {}$, current crypto : {},  current amount : {}$"
                    .format(self.coin,time,price,round(self.currentCrypto,2),round(self.currentAmount,2)))


    def sell(self,price,time):
        global tradeFinishCount,tradeAmount,initialTradeAmount
        
        order = client.order_market_sell(
            symbol=self.coin,
            quantity=self.currentCrypto)
        print(order)
        self.currentAmount = price * self.currentCrypto
        self.currentAmount = self.currentAmount - (self.currentAmount*0.1/100)
        self.currentCrypto = 0.0
        # self.currentAmount = float(client.get_asset_balance(asset='USDT'))
        try:
            client.transfer_dust(asset=self.coin)
        except:
            print("ERROR : client.transfer_dust(asset=self.coin)")
        
        print("\nSELL : {} : {} : current price {}$  current amount : {}$"
                    .format(self.coin,time,price,round(self.currentAmount,2)))
        
        print("trade profit : {}$ ({}%))"
        .format(round(self.currentAmount-self.previousAmount,2),round((self.currentAmount - self.previousAmount)* 100/self.previousAmount,2)
        ))
        

        tradeAmount += self.currentAmount
        self.bsm.stop()
        del self.bsm
        tradeFinishCount +=1
        if(tradeFinishCount==no_of_coins):
            # tradeAmount += mainAmount
            # mainAmount = max(0,tradeAmount - 1000)
            # tradeAmount = min(1000,tradeAmount)
            initialTradeAmount = tradeAmount
            print("########################################################")
            print("Trade Amount : {}".format(tradeAmount))
            print("########################################################")
        
            # reStart()

def superTrend(coin,period = 10, mult = 3):
    try:
        # bars = exchange.fetch_ohlcv(coin.replace("USDT","/USDT"),timeframe='15m',limit=210)
        # dfL = pd.DataFrame(bars,columns=["time","open","high","low","close","volume"])
        # dfL['time'] = list(map(lambda x : str(datetime.datetime.fromtimestamp(x/1000)),[i[0] for i in bars]))
        # ATRindicatorL = AverageTrueRange(close=dfL['close'],high=dfL['high'],low=dfL['low'], window=10)
        # dfL['atr'] = ATRindicatorL.average_true_range()
        # dfL['high'] = list(map(float,dfL['high']))
        # dfL['low'] = list(map(float,dfL['low']))
        # hl2 = (dfL['high'] + dfL['low']) / 2
        # dfL['upperband'] = hl2 + (3 * dfL['atr']) 
        # dfL['lowerband'] = hl2 - (3 * dfL['atr']) 
        # dfL['in_uptrend'] = True
        # RSIIndicator(close=dfL['close']).rsi()
        # for current in range(1,len(dfL.index)):
        #     previous = current - 1
        #     if(dfL['close'][current] > dfL['upperband'][previous]):
        #         dfL['in_uptrend'][current] = True
                
        #     elif(dfL['close'][current] < dfL['lowerband'][previous]):
        #         dfL['in_uptrend'][current] = False
        #     else:
        #         dfL['in_uptrend'][current] = dfL['in_uptrend'][previous]

        #         if(dfL['in_uptrend'][current] and dfL['lowerband'][current] < dfL['lowerband'][previous]):
        #             dfL['lowerband'][current] = dfL['lowerband'][previous]

        #         if(not dfL['in_uptrend'][current] and dfL['upperband'][current] > dfL['upperband'][previous]):
        #             dfL['upperband'][current] = dfL['upperband'][previous]

        # ##############################################################
        barsH = exchange.fetch_ohlcv(coin.replace("USDT","/USDT"),timeframe='15m',limit=210)
        dfH = pd.DataFrame(barsH,columns=["time","open","high","low","close","volume"])
        dfH['time'] = list(map(lambda x : str(datetime.datetime.fromtimestamp(x/1000)),[i[0] for i in barsH]))
        ATRindicatorH = AverageTrueRange(close=dfH['close'],high=dfH['high'],low=dfH['low'], window=10)
        dfH['atr'] = ATRindicatorH.average_true_range()
        dfH['high'] = list(map(float,dfH['high']))
        dfH['low'] = list(map(float,dfH['low']))
        hl2H = (dfH['high'] + dfH['low']) / 2
        dfH['upperband'] = hl2H + (3 * dfH['atr']) 
        dfH['lowerband'] = hl2H - (3 * dfH['atr']) 
        dfH['in_uptrend'] = True

        for current in range(1,210):
            previous = current - 1
            if(dfH['close'][current] > dfH['upperband'][previous]):
                dfH['in_uptrend'][current] = True
            elif(dfH['close'][current] < dfH['lowerband'][previous]):
                dfH['in_uptrend'][current] = False
            else:
                dfH['in_uptrend'][current] = dfH['in_uptrend'][previous]

                if(dfH['in_uptrend'][current] and dfH['lowerband'][current] < dfH['lowerband'][previous]):
                    dfH['lowerband'][current] = dfH['lowerband'][previous]

                if(not dfH['in_uptrend'][current] and dfH['upperband'][current] > dfH['upperband'][previous]):
                    dfH['upperband'][current] = dfH['upperband'][previous]

        esa = EMAIndicator(close=dfH['close'],window=9).ema_indicator()
        de = EMAIndicator(close= abs(dfH['close'] - esa),window=9).ema_indicator()
        ci = (dfH['close'] - esa) / (0.015 * de)
        wt1 = EMAIndicator(close=ci,window=12).ema_indicator()
        wt2 = SMAIndicator(close=wt1,window=3).sma_indicator()
        dfH['wt1'] = wt1
        dfH['wt2'] = wt2
        MFI = SMAIndicator(( (dfH['close']-dfH['open']) / (dfH['high']-dfH['low']) ) * 150,window=60).sma_indicator() - 2.5
        dfH['MFI'] = MFI > 0
        arr= [False] * 210
        for i in range(210):
            if((dfH['wt1'][i]<0 and dfH['wt2'][i]<0 and dfH['wt2'][i] < dfH['wt1'][i] and dfH['MFI'][i])):
                arr[i] = True
        dfH['buy'] = arr
        return True,dfH
    except:
        return False,None

def collectData(coin):
    result,dfh = superTrend(coin)
    canBuy = False
    if(result):
        for i in range(209,190,-1):
            if((dfh['high'][i] - dfh['low'][i])*100/dfh['low'][i] > 1):
                canBuy = True
                break

        if(canBuy and dfh['in_uptrend'][208] and dfh['buy'][208] and not dfh['buy'][207]):
            # EMAindicator200 = EMAIndicator(dfh['close'],window=200).ema_indicator()
            # EMAindicator20 = EMAIndicator(dfh['close'],window=20).ema_indicator()
            # if(EMAindicator200[208] < EMAindicator20[208]):
            return True
    return False

def findBestCoin():
    global no_of_coins
    tempArr = client.get_ticker()
    arr = []
    for i in range(len(tempArr)):
        for j in range(len(tempArr)-1):
            a,b= float(tempArr[j]['volume']) * float(tempArr[j]['lastPrice']),float(tempArr[j+1]['volume']) * float(tempArr[j+1]['lastPrice'])
            if(a<b):
                tempArr[j], tempArr[j+1] = tempArr[j+1], tempArr[j]

    nc = 0
    
    for product in tempArr:
        if(True): 
            profitPerc = (float(product['lastPrice'])-float(product['openPrice']))*100/float(product['openPrice'])
            if(float(product['volume']) * float(product['lastPrice']) < 1000000): 
                break
            if((product['symbol'][len(product['symbol'])-4:] in ("USDT")) 
            and (product['symbol'][:4] not in ("USDC,USDT,BUSD")) and (product['symbol'][:3] not in ("BNB","BTC")) ): 
                canBuy = collectData(product['symbol'])
                if(canBuy):
                    nc+=1
                    arr.append(product['symbol'])
                    bot(product['symbol'])
                    if(nc==no_of_coins):
                        return 
    if(len(arr)!=0):
        while 1:
            print("REPEAT")
            for i in arr:
                nc+=1
                bot(i)
                if(nc==no_of_coins):
                    return 
    else:
        print("No coin found")
        findBestCoin()
    

def reStart():
    global bot,no_of_coins,tradeFinishCount
    print("Finding coins")
    tradeFinishCount = 0
    findBestCoin()
    


api_key = ""
api_secret = ""
client = Client(api_key, api_secret)
exchange = ccxt.binance({
            'apiKey' : api_key,
            'secret' : api_secret
        })

balance = client.get_asset_balance(asset='USDT')

tradeAmount = 20
initialTradeAmount = 20
no_of_coins = 1
tradeFinishCount = 0

reStart()