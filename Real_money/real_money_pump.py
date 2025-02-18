from binance.client import Client
from binance import ThreadedWebsocketManager
from time import sleep
import sys
import datetime
import ccxt
from ta.trend import MACD,EMAIndicator
import math
import pandas as pd
# import utils2 as utils

class bot:
    def __init__(self,coin):
        
        global tradeAmount
        self.coin = coin
        print("Chosen coin : {}".format(self.coin))
        
        if(self.coin != None):
            
            self.bsm = ThreadedWebsocketManager()
            self.bsm.start()
            self.bsm.start_symbol_ticker_socket(callback=self.on_message, symbol=self.coin)
        self.currentAmount = tradeAmount
        self.previousAmount = tradeAmount
        tradeAmount -= tradeAmount

        self.currentCrypto = 0.0
        
        self.isBought = False  

        self.previousTime = None

        self.previousEMA = None

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
                else:
                    self.buy(currentPrice,currentTime)
                    self.isBought = True
                if(currentTime.minute != self.previousTime.minute and currentTime.minute % 10 == 0):
                    try:
                        print("{} : {} : current price {}$, current crypto : {},  current amount : {}$\n"
                        .format(self.coin,currentTime,currentPrice,round(self.currentCrypto,2),round(self.currentAmount,2)))
                    except:
                        print("Collecting Data .. Please wait")

                    print("{} : Time lapsed : {}".format(self.coin,round((datetime.datetime.now() - self.previousBuyTime).total_seconds()/60)))

                self.previousTime = currentTime
            else: 
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
        if(self.stopLossAt!=0 and (currentPrice-self.stopLossAt)*100/self.stopLossAt < 0):
            return True
        
        if(self.stopLossAt==0):
            self.stopLossAt = self.arr[0] - self.arr[0] * 20/100
            print("{} : Stoploss : {}".format(self.coin,self.stopLossAt))
            
        a = self.stopLossAt

        if(currentPrice > self.arr[1]):
            self.stopLossAt = max(self.stopLossAt,currentPrice - currentPrice * 5/100)
            if(self.stopLossAt != a):
                print("{} : Stoploss : {}".format(self.coin,self.stopLossAt))
        

        return False

    def buy(self,price,time):
        self.arr[0] = price
        self.arr[1] = price + price * 15 / 100
        
        self.previousAmount = self.currentAmount
        order = client.order_market_buy(
            symbol=self.coin,
            quoteOrderQty = self.currentAmount)
        print(order)
        self.currentCrypto = float(order['executedQty'])

        print("\nBUY : {} : {} : current price {}$, current crypto : {},  current amount : {}$"
                    .format(self.coin,time,price,round(self.currentCrypto,2),round(self.currentAmount,2)))


    def sell(self,price,time):
        global tradeAmount
        
        order = client.order_market_sell(
            symbol=self.coin,
            quantity=self.currentCrypto)
        print(order)
        self.currentAmount = price * self.currentCrypto
        self.currentAmount = self.currentAmount - (self.currentAmount*0.1/100)
        self.currentCrypto = 0.0
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


api_key = ""
api_secret = ""
client = Client(api_key, api_secret)
exchange = ccxt.binance({
            'apiKey' : api_key,
            'secret' : api_secret
        })

balance = client.get_asset_balance(asset='USDT')

tradeAmount = 100

bot("EZUSDT")