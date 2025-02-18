from binance.client import Client
from binance.streams import ThreadedWebsocketManager
from time import sleep
import datetime
from ta.momentum import RSIIndicator, StochRSIIndicator, StochasticOscillator
from ta.trend import EMAIndicator, SMAIndicator, WMAIndicator,MACD
from ta.volatility import AverageTrueRange
import math
import pandas as pd
import sqlite3
import json
import requests

import configparser
import json

from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError

from telethon.tl.functions.channels import GetParticipantsRequest
from telethon.tl.types import ChannelParticipantsSearch
from telethon.tl.types import (
PeerChannel
)

api_id = "18225958"
api_hash = "27a322c98d5f5f86ae6e39ebaee0acdd"

# use full phone number including + and country code
phone = "+917010450504"
username = "Surya"

client = TelegramClient(username, api_id, api_hash)
client.start()
print("Client Created")
# Ensure you're authorized
if not client.is_user_authorized():
    client.send_code_request(phone)
    try:
        client.sign_in(phone, input('Enter the code: '))
    except SessionPasswordNeededError:
        client.sign_in(password=input('Password: '))

user_input_channel = input("enter entity(telegram URL or entity id):")

if user_input_channel.isdigit():
    entity = PeerChannel(int(user_input_channel))
else:
    entity = user_input_channel

my_channel = client.get_entity(entity)

class bot:
    def __init__(self, coin,num,avg):

        self.coin = coin
        self.avg = avg

        print("Chosen coin : {}".format(self.coin))
        print(chosenCoins,initialTradeAmount,num)
        self.num = num

        # if((datetime.datetime.now().hour*60 + datetime.datetime.now().minute)%60 < 120):
        self.currentAmount = initialTradeAmount[num]
        self.previousAmount = initialTradeAmount[num]
        # else:
        #     self.currentAmount = initialTradeAmount[num] * 2/3
        #     self.previousAmount = initialTradeAmount[num] *2/3
        

        self.currentCrypto = 0.0

        self.isBought = False

        self.previousTime = None
        self.previousPrice = 0

        self.previousBuyTime = datetime.datetime.now()
        if(self.coin != None):
            self.bsm = ThreadedWebsocketManager(
                api_key=api_secret, api_secret=api_secret,requests_params={'timeout': 30})
            self.bsm.start()
            self.bsm.start_symbol_ticker_socket(
                callback=self.on_message, symbol=self.coin)

    def on_message(self, msg):
        if msg['e'] != 'error':
            self.conn = sqlite3.connect('database.db')
            try:
                self.conn.execute('''CREATE TABLE REAL
                    (TIME TEXT  NOT NULL,
                    COIN           TEXT    NOT NULL,
                    PRICE          FLOAT   NOT NULL,
                    BUYSELL        TEXT    NOT NULL,
                    PERCENTAGE FLOAT
                    );''')
            except:
                pass

            currentTime = datetime.datetime.now()
            currentPrice = float(msg['c'])

            if(self.previousTime != None and currentTime != self.previousTime):

                if(not self.isBought):
                    self.buy(currentPrice, currentTime)
                    self.isBought = True

                if(self.isBought and  currentTime.second % 5 == 0):
                    if(self.canSell(currentTime, currentPrice)):
                        self.sell(currentPrice, currentTime)
                        self.isBought = False

                if(currentTime.minute != self.previousTime.minute and currentTime.minute % 10 == 0):
                    print("{} : {} : current price {}$, current crypto : {}, current value : {}, current amount : {}$"
                          .format(self.coin, currentTime, currentPrice, round(self.currentCrypto, 2), round(currentPrice*self.currentCrypto, 2), round(self.currentAmount, 2)))
                    print("{} : Time lapsed : {}\n".format(self.coin, round(
                        (datetime.datetime.now() - self.previousBuyTime).total_seconds()/60)))
                self.previousTime = currentTime
            else:
                self.previousTime = currentTime
        else:
            print(
                "############################## ERROR RETRYING ##########################################")
            self.bsm.stop()
            del self.bsm
            sleep(300)
            self.bsm = ThreadedWebsocketManager()
            self.bsm.start()
            self.bsm.start_symbol_ticker_socket(
                callback=self.on_message, symbol=self.coin)

    def canSell(self, currentTime, currentPrice):

        if(self.target<currentPrice or self.stoploss > currentPrice):
            return True
        

        return False

    def buy(self, price, time):
        global no_of_trades
        no_of_trades += 1
        self.conn.execute("INSERT INTO REAL VALUES(?,?,?,'buy',?);", (str(time),self.coin,price,None))
        self.conn.commit()

        self.stoploss = price - price*(self.avg * 2/100)
        self.target = price + price*(self.avg * 2/100)
        initialTradeAmount[self.num] -= self.currentAmount

        msg = "\nBUY : {} : {} : current price {}$, bought for : {}$".format(self.coin, time, price, round(self.currentAmount, 2))
        print(msg)
        url = 'https://api.telegram.org/bot2072407643:AAEq8g8QuQe13WY1n9lhTKh5AWQNClu0w48/sendMessage?chat_id={}&text={}'.format(chatId,msg)
        requests.get(url)

        self.previousAmount = self.currentAmount
        self.currentAmount = self.currentAmount - \
            (self.currentAmount*0.075/100)
        self.currentCrypto = self.currentAmount / price

        self.currentAmount = 0.0
        self.previousPrice = price

    def sell(self, price, time):

        global initialTradeAmount,profitperday,no_of_trades

        self.currentAmount = price * self.currentCrypto
        self.currentAmount = self.currentAmount - \
            (self.currentAmount*0.075/100)
        self.currentCrypto = 0.0

        profit = int(self.currentAmount-self.previousAmount)
        
        msg1 = "SELL : {} : {} : current price {}$ current amount : {}$".format(self.coin, time, price, round(self.currentAmount, 2))
        print("\n"+msg1)
        msg2 = "trade profit : {}$ ({}%))".format(round(self.currentAmount-self.previousAmount, 2), round((self.currentAmount - self.previousAmount) * 100/self.previousAmount, 2))
        print(msg2)
        self.conn.execute("INSERT INTO REAL VALUES(?,?,?,'sell',?);", (str(time),self.coin,price,round((self.currentAmount - self.previousAmount) * 100/self.previousAmount, 2)))
        self.conn.commit()
        
        url = 'https://api.telegram.org/bot2072407643:AAEq8g8QuQe13WY1n9lhTKh5AWQNClu0w48/sendMessage?chat_id={}&text={}'.format(chatId,msg1+"\n"+msg2)
        requests.get(url)

        initialTradeAmount[self.num] += self.currentAmount
        profitperday += profit

        self.bsm.stop()
        
        initialTradeAmount[chosenCoins.index(self.coin)]= round(self.currentAmount, 2)
        chosenCoins[chosenCoins.index(self.coin)] = ""
        # balanceAmt(self.num,profit)

        no_of_trades -= 1
        if(no_of_trades == 0):
            balance = float(client.get_asset_balance(asset='USDT')['free'])
            balance = 1000
            initialTradeAmount = [balance/no_of_coins] * no_of_coins
        
        print(initialTradeAmount)
        sleep(30)
        del self.bsm


def getAvg(df, length):
    sum = 0
    for i in range(20):
        sum += (df['high'][length-2-i] - df['low'][length-2-i]) * \
            100 / df['low'][length-2-i]
    return sum/20



def collectData(coin, length):
    global hasProfitPerDayPosted,profitperday
    if(datetime.datetime.now().hour > 6):
        if(not hasProfitPerDayPosted):
            url = 'https://api.telegram.org/bot2072407643:AAEq8g8QuQe13WY1n9lhTKh5AWQNClu0w48/sendMessage?chat_id={}&text=Total Profit for today : {}$'.format(chatId,profitperday)
            requests.get(url)
            hasProfitPerDayPosted = True
            profitperday = 0
    else:
        hasProfitPerDayPosted = False
    
    
    return False, None, None


def findBestCoin():
    global no_of_coins, chosenCoins,hasProfitPerDayPosted,profitperday

    
    canBuy = True
    
    if canBuy:
        
        url = "https://www.binance.com/exchange-api/v2/public/asset-service/product/get-products"
        res = requests.get(url)
        data = list(json.loads(res.content)["data"])

        prods = []
        for i in range(len(data)):
            try:
                b = (float(data[i]['c']) * float(data[i]['cs']) )
                prods.append(data[i])
            except:
                pass

        for i in range(len(prods)):
            for j in range(len(prods)-1):
                a = (float(prods[j]['c']) * float(prods[j]['cs']) )

                b = (float(prods[j+1]['c']) * float(prods[j+1]['cs']) )
                if(a < b):
                    prods[j], prods[j+1] = prods[j+1], prods[j]

        for product in prods:
            
            if(True):
                if(float(product['c']) * float(product['cs']) < 500000000):
                    break
                if((product['s'][len(product['s'])-4:] in ("USDT")) and not "DOWN" in product['s']
                and (product['s'][:4] not in ("USDC,USDT,BUSD")) and (product['s'][:3] not in ("EUR"))):
                    canBuy, df, avg = collectData(product['s'], 500)
            
                    if(canBuy):
                        
                        if(product['s'] not in chosenCoins):
                            try:
                                chosenCoins[chosenCoins.index("")] = product['s']
                                bot(product['s'],chosenCoins.index(product['s']),avg)
                            except:
                                pass
                            
    return True


def reStart():
    print("Finding coins")
    while findBestCoin():
        pass

api_key = ""
api_secret = ""
client = Client(api_key, api_secret,{'timeout': 60})

no_of_coins = 2
balance = float(client.get_asset_balance(asset='USDT')['free'])
balance = 1000

initialTradeAmount = [balance/no_of_coins] * no_of_coins

no_of_trades = 0

chosenCoins = [""] * no_of_coins


profitperday = 0
hasProfitPerDayPosted = False

# chatId = "-1001590033171"   
chatId = "527450766"

# reStart()
# collectData("DNTUSDT", 1000)
