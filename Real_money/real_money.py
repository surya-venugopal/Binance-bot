from tradingview_ta import TA_Handler, Interval, Exchange
from binance.client import Client
from binance import ThreadedWebsocketManager
from time import sleep
import sys
import datetime
import math
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
        
        if((datetime.datetime.now() - self.previousBuyTime).total_seconds()/60 > 30 * 2):
            print("{} : Time Exceeded".format(self.coin))
            
            return True
        if((datetime.datetime.now() - self.previousBuyTime).total_seconds()/60 > 30 * 1):
            self.arr[1] = self.arr[0] - self.arr[0] * 1 /100
            self.arr[2] = self.arr[0] + self.arr[0] * 0.2 /100
            for i in range(3,20,2):
                self.arr[i] = self.arr[0] + self.arr[0] * (i-1)*1/200
            for i in range(4,20,2):
                self.arr[i] = (self.arr[i-1] + self.arr[i+1]) /2

            if(self.stopLossAt < self.arr[1]):
                self.stopLossAt = self.arr[1]
                print("{} : Stoploss : {}".format(self.coin,self.stopLossAt))
            
        # if(self.crossed1st100):
        if(self.stopLossAt==0):
            self.stopLossAt = self.arr[1]
            print("{} : Stoploss : {}, Next Target : {}".format(self.coin,self.stopLossAt,self.arr[2]))
            
        a = self.stopLossAt
        for i in range(1,20):
            if(currentPrice<self.arr[i]):
                self.stopLossAt = max(self.stopLossAt,self.arr[i-1])
                if(self.stopLossAt != a):
                    return True
                    self.previousBuyTime = datetime.datetime.now()
                    print("{} : Stoploss : {}, Next Target : {}".format(self.coin,self.stopLossAt,self.arr[i+1]))
                    
                break
        return False

    def buy(self,price,time):
        self.arr[0] = price
        self.arr[1] = price - price * 2 /100
        self.arr[2] = price + price * 0.3 /100
        for i in range(3,20,2):
            self.arr[i] = price + price * (i-1)*1/200
        for i in range(4,20,2):
            self.arr[i] = (self.arr[i-1] + self.arr[i+1]) /2
        
        self.previousAmount = self.currentAmount
        order = client.order_market_buy(
            symbol=self.coin,
            quoteOrderQty = self.currentAmount)
        print(order)
        self.currentCrypto = order['executedQty']

        print("\nBUY : {} : {} : current price {}$, current crypto : {},  current amount : {}$"
                    .format(self.coin,time,price,round(self.currentCrypto,2),round(self.currentAmount,2)))


    def sell(self,price,time):
        global tradeFinishCount,tradeAmount,initialTradeAmount
        
        order = client.order_market_sell(
            symbol=self.coin,
            quantity=self.currentCrypto)
        print(order)
        self.currentAmount = client.get_asset_balance(asset='USDT')
        try:
            client.transfer_dust(asset=self.coin)
        except:
            print("ERROR : client.transfer_dust(asset=self.coin)")
        
        print("\nSELL : {} : {} : current price {}$, current crypto : {},  current amount : {}$"
                    .format(self.coin,time,price,round(self.currentCrypto,2),round(self.currentAmount,2)))
        
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
        
            reStart()

def getProfit(h,coin):
    try:
        currentTime=datetime.datetime.now()

        timestamps = currentTime-datetime.timedelta(minutes=60 * 1)
        timestamps = datetime.datetime.timestamp(timestamps)
        timestamps = (round(timestamps)*1000)
        
        timestampe = currentTime-datetime.timedelta(minutes=60 * 0)
        timestampe = datetime.datetime.timestamp(timestampe)
        timestampe = (round(timestampe)*1000)

        trades = client.get_aggregate_trades(symbol=coin,startTime=timestamps,endTime=timestampe)

        end = float(trades[len(trades)-1]['p'])

        timestamps = currentTime-datetime.timedelta(minutes= 60 * (h + 1))
        timestamps = datetime.datetime.timestamp(timestamps)
        timestamps = (round(timestamps)*1000)
        
        timestampe = currentTime-datetime.timedelta(minutes= 60 * h)
        timestampe = datetime.datetime.timestamp(timestampe)
        timestampe = (round(timestampe)*1000)

        trades = client.get_aggregate_trades(symbol=coin,startTime=timestamps,endTime=timestampe)

        start = float(trades[len(trades)-1]['p'])

        return (end - start)*100 / start
    except:
        return False


def collectData(coin):
    try:

        # for i in range(6,1,-2):
        profit1 = getProfit(1,coin)
        profit2 = getProfit(0.5,coin)
        if((profit1 != False and profit1 > 0.3)  or (profit2 != False and profit2 > 0.3 )): # and profit2 != False and profit2 > profit1
            # print("{} : {}".format(coin,profit))
            product = TA_Handler(
                        symbol=coin,
                        screener="crypto",
                        exchange="BINANCE",
                        interval=Interval.INTERVAL_5_MINUTES
                        )
            indicators = product.get_analysis().indicators

            
            if(indicators['MACD.macd'] > indicators['MACD.signal'] and indicators['EMA100'] < indicators['EMA10'] and indicators['RSI']>70
             and (indicators['EMA10']-indicators['EMA100'])*100/indicators['EMA100'] > 0.5):
                # k < 20 and d < 20 and k > d and k1 < d1
                return True
            return False
    except:
        # print(coin,end=" ")
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
            if(float(product['volume']) * float(product['lastPrice']) < 100000 ): 
                break
            
            if((product['symbol'][len(product['symbol'])-4:] in ("USDT") or product['symbol'][len(product['symbol'])-3:] in ("BNB","BTC","ETH"))
            and (product['symbol'][:4] not in ("USDC,USDT,BUSD")) and (product['symbol'][:3] not in ("EUR")) ):
                if(collectData(product['symbol'])):
                    nc+=1
                    arr.append(product['symbol'])
                    bot(product['symbol'])
                    if(nc==no_of_coins):
                        return arr

    if(len(arr)!=0):
        while 1:
            print("REPEAT")
            for i in arr:
                nc+=1
                bot(i)
                if(nc==no_of_coins):
                    return arr
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


balance = client.get_asset_balance(asset='USDT')

tradeAmount = float(balance['free'])
initialTradeAmount = float(balance['free'])
no_of_coins = 2
tradeFinishCount = 0

reStart()