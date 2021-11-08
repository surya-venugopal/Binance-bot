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
import requests
import json
# import linearRegression as LR

# import matplotlib.pyplot as plt

pd.options.mode.chained_assignment = None
invested = []


class bot:
    def __init__(self, coin,num,avg):
        
        self.num = num
        self.coin = coin
        self.avg = avg
        print("Chosen coin : {}".format(self.coin))

        self.currentAmount = initialTradeAmount[num]
        self.previousAmount = initialTradeAmount[num]

        self.currentCrypto = 0.0

        self.isBought = False

        self.previousTime = None
        self.previousPrice = 0

        self.previousBuyTime = datetime.datetime.now()

        self.rsiReached = False

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
        global initialTradeAmount

        if(self.stoploss>currentPrice):
            
            return True
        try:
            bars = client.get_klines(
                symbol=self.coin, interval=Client.KLINE_INTERVAL_5MINUTE, limit=500)
            df = pd.DataFrame(bars, columns=["time", "open", "high", "low", "close", "volume", "Close time", "Quote asset volume",
                                            "Number of trades", "Taker buy base asset volume", "Taker buy quote asset volume", "Can be ignored"])
            df['open'] = pd.Series(list(map(float, df['open'])))
            df['high'] = pd.Series(list(map(float, df['high'])))
            df['low'] = pd.Series(list(map(float, df['low'])))
            df['close'] = pd.Series(list(map(float, df['close'])))
            df['volume'] = pd.Series(list(map(float, df['volume'])))

            df = HA(df,500)
            
            df['hist'] = MACD(df['close']).macd_diff()
            
            if(round(df['rsi5o'][499]) >= 80 or round(df['rsi5h'][499]) >= 80 or round(df['rsi5l'][499]) >= 80 or round(df['rsi5c'][499]) >= 80):
                self.rsiReached = True
            
            if(self.rsiReached and df['hist'][498] >= 0 and df['hist'][498] > df['hist'][499]):
                return True
        except:
            pass

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


def getDiff(coin,temp):
    length = 50
    bars = client.get_klines(
        symbol=coin, interval=Client.KLINE_INTERVAL_4HOUR, limit=length)
    df = pd.DataFrame(bars, columns=["time", "open", "high", "low", "close", "volume", "Close time", "Quote asset volume",
                                     "Number of trades", "Taker buy base asset volume", "Taker buy quote asset volume", "Can be ignored"])
    df['open'] = pd.Series(list(map(float, df['open'])))
    df['high'] = pd.Series(list(map(float, df['high'])))
    df['low'] = pd.Series(list(map(float, df['low'])))
    df['close'] = pd.Series(list(map(float, df['close'])))
    df['volume'] = pd.Series(list(map(float, df['volume'])))

    df = HA(df,length)

    yesterday = [0.0]*length
    today = [0.0]*length
    delta = [0.0]*length
    percentage = [0.0]*length
    # print(temp)
    if(temp==0):
        for i in range(1,length):
            timestamp = int(df['time'][i]/1000)
            time = datetime.datetime.fromtimestamp(timestamp)

            if((time.minute + 60*time.hour) % 240 == 0):
                yesterday[i] = df['hclose'][i-1]
                today[i] = (df['hhigh'][i] +df['hlow'][i] +df['hopen'][i])/3
                delta[i] = today[i] - yesterday[i]
                percentage[i] = delta[i]/yesterday[i]
            else:
                yesterday[i] = yesterday[i-1]
                today[i] = today[i-1]
                delta[i] = delta[i-1]
                percentage[i] = percentage[i-1]
            
    elif(temp==1):
        for i in range(1,length):
            timestamp = int(df['time'][i]/1000)
            time = datetime.datetime.fromtimestamp(timestamp)
            if((time.minute + 60*time.hour ) % 240 == 0):
                yesterday[i] = df['hclose'][i-1]
                today[i] = df['hopen'][i]
                delta[i] = today[i] - yesterday[i]
                percentage[i] = delta[i]/yesterday[i]
            else:
                yesterday[i] = yesterday[i-1]
                today[i] = today[i-1]
                delta[i] = delta[i-1]
                percentage[i] = percentage[i-1]
    return percentage

def PineActivationFunctionLinear(v):return v
def PineActivationFunctionTanh(v):
    return (math.exp(v) - math.exp(-v))/(math.exp(v) + math.exp(-v))



def ANN(coin,temp):
    length = 50
    buying = [False] * length
    percentage = PineActivationFunctionLinear(getDiff(coin,temp))
    for i in range(1,length):
        l0_0,l0_1,l0_2,l0_3,l0_4,l0_5,l0_6,l0_7,l0_8,l0_9,l0_10,l0_11,l0_12,l0_13,l0_14 = [percentage[i]]*15
        
        l1_0 = PineActivationFunctionTanh(l0_0*5.040340774 + l0_1*-1.3025994088 + l0_2*19.4225543981 + l0_3*1.1796960423 + l0_4*2.4299395823 + l0_5*3.159003445 + l0_6*4.6844527551 + l0_7*-6.1079267196 + l0_8*-2.4952869198 + l0_9*-4.0966081154 + l0_10*-2.2432843111 + l0_11*-0.6105764807 + l0_12*-0.0775684605 + l0_13*-0.7984753138 + l0_14*3.4495907342)
        l1_1 = PineActivationFunctionTanh(l0_0*5.9559031982 + l0_1*-3.1781960056 + l0_2*-1.6337491061 + l0_3*-4.3623166512 + l0_4*0.9061990402 + l0_5*-0.731285093 + l0_6*-6.2500232251 + l0_7*0.1356087758 + l0_8*-0.8570572885 + l0_9*-4.0161353298 + l0_10*1.5095552083 + l0_11*1.324789197 + l0_12*-0.1011973878 + l0_13*-2.3642090162 + l0_14*-0.7160862442)
        l1_2 = PineActivationFunctionTanh(l0_0*4.4350881378 + l0_1*-2.8956461034 + l0_2*1.4199762607 + l0_3*-0.6436844261 + l0_4*1.1124274281 + l0_5*-4.0976954985 + l0_6*2.9317456342 + l0_7*0.0798318393 + l0_8*-5.5718144311 + l0_9*-0.6623352208 +l0_10*3.2405203222 + l0_11*-10.6253384513 + l0_12*4.7132919253 + l0_13*-5.7378151597 + l0_14*0.3164836695)
        l1_3 = PineActivationFunctionTanh(l0_0*-6.1194605467 + l0_1*7.7935605604 + l0_2*-0.7587522153 + l0_3*9.8382495905 + l0_4*0.3274314734 + l0_5*1.8424796541 + l0_6*-1.2256355427 + l0_7*-1.5968600758 + l0_8*1.9937700922 + l0_9*5.0417809111 + l0_10*-1.9369944654 + l0_11*6.1013201778 + l0_12*1.5832910747 + l0_13*-2.148403244 + l0_14*1.5449437366)
        l1_4 = PineActivationFunctionTanh(l0_0*3.5700040028 + l0_1*-4.4755892733 + l0_2*0.1526702072 + l0_3*-0.3553664401 + l0_4*-2.3777962662 + l0_5*-1.8098849587 + l0_6*-3.5198449134 + l0_7*-0.4369370497 + l0_8*2.3350169623 + l0_9*1.9328960346 + l0_10*1.1824141812 + l0_11*3.0565148049 + l0_12*-9.3253401534 + l0_13*1.6778555498 + l0_14*-3.045794332)
        l1_5 = PineActivationFunctionTanh(l0_0*3.6784907623 + l0_1*1.1623683715 + l0_2*7.1366362145 + l0_3*-5.6756546585 + l0_4*12.7019884334 + l0_5*-1.2347823331 + l0_6*2.3656619827 + l0_7*-8.7191778213 + l0_8*-13.8089238753 + l0_9*5.4335943836 + l0_10*-8.1441181338 + l0_11*-10.5688113287 + l0_12*6.3964140758 + l0_13*-8.9714236223 + l0_14*-34.0255456929)
        l1_6 = PineActivationFunctionTanh(l0_0*-0.4344517548 + l0_1*-3.8262167437 + l0_2*-0.2051098003 + l0_3*0.6844201221 + l0_4*1.1615893422 + l0_5*-0.404465314 + l0_6*-0.1465747632 + l0_7*-0.006282458 + l0_8*0.1585655487 + l0_9*1.1994484991 + l0_10*-0.9879081404 + l0_11*-0.3564970612 + l0_12*1.5814717823 + l0_13*-0.9614804676 + l0_14*0.9204822346)
        l1_7 = PineActivationFunctionTanh(l0_0*-4.2700957175 + l0_1*9.4328591157 + l0_2*-4.3045548 + l0_3*5.0616868842 + l0_4*3.3388781058 + l0_5*-2.1885073225 + l0_6*-6.506301518 + l0_7*3.8429000108 + l0_8*-1.6872237349 + l0_9*2.4107095799 + l0_10*-3.0873985314 + l0_11*-2.8358325447 + l0_12*2.4044366491 + l0_13*0.636779082 + l0_14*-13.2173215035)
        l1_8 = PineActivationFunctionTanh(l0_0*-8.3224697492 + l0_1*-9.4825530183 + l0_2*3.5294389835 + l0_3*0.1538618049 + l0_4*-13.5388631898 + l0_5*-0.1187936017 + l0_6*-8.4582741139 + l0_7*5.1566299292 + l0_8*10.345519938 + l0_9*2.9211759333 + l0_10*-5.0471804233 + l0_11*4.9255989983 + l0_12*-9.9626142544 + l0_13*23.0043143258 + l0_14*20.9391809343)
        l1_9 = PineActivationFunctionTanh(l0_0*-0.9120518654 + l0_1*0.4991807488 + l0_2*-1.877244586 + l0_3*3.1416466525 + l0_4*1.063709676 + l0_5*0.5210126835 + l0_6*-4.9755780108 + l0_7*2.0336532347 + l0_8*-1.1793121093 + l0_9*-0.730664855 + l0_10*-2.3515987428 + l0_11*-0.1916546514 + l0_12*-2.2530340504 + l0_13*-0.2331829119 + l0_14*0.7216218149)
        l1_10 = PineActivationFunctionTanh(l0_0*-5.2139618683 + l0_1*1.0663790028 + l0_2*1.8340834959 + l0_3*1.6248173447 + l0_4*-0.7663740145 + l0_5*0.1062788171 + l0_6*2.5288021501 + l0_7*-3.4066549066 + l0_8*-4.9497988755 + l0_9*-2.3060668143 + l0_10*-1.3962486274 + l0_11*0.6185583427 + l0_12*0.2625299576 + l0_13*2.0270246444 + l0_14*0.6372015811)
        l1_11 = PineActivationFunctionTanh(l0_0*0.2020072665 + l0_1*0.3885852709 + l0_2*-0.1830248843 + l0_3*-1.2408598444 + l0_4*-0.6365798088 + l0_5*1.8736534268 + l0_6*0.656206442 + l0_7*-0.2987482678 + l0_8*-0.2017485963 + l0_9*-1.0604095303 + l0_10*0.239793356 + l0_11*-0.3614172938 + l0_12*0.2614678044 + l0_13*1.0083551762 + l0_14*-0.5473833797)
        l1_12 = PineActivationFunctionTanh(l0_0*-0.4367517149 + l0_1*-10.0601304934 + l0_2*1.9240604838 + l0_3*-1.3192184047 + l0_4*-0.4564760159 + l0_5*-0.2965270368 + l0_6*-1.1407423613 + l0_7*2.0949647291 + l0_8*-5.8212599297 + l0_9*-1.3393321939 + l0_10*7.6624548265 + l0_11*1.1309391851 + l0_12*-0.141798054 + l0_13*5.1416736187 + l0_14*-1.8142503125)
        l1_13 = PineActivationFunctionTanh(l0_0*1.103948336 + l0_1*-1.4592033032 + l0_2*0.6146278432 + l0_3*0.5040966421 + l0_4*-2.4276090772 + l0_5*-0.0432902426 + l0_6*-0.0044259999 + l0_7*-0.5961347308 + l0_8*0.3821026107 + l0_9*0.6169102373 +l0_10*-0.1469847611 + l0_11*-0.0717167683 + l0_12*-0.0352403695 + l0_13*1.2481310788 + l0_14*0.1339628411)
        l1_14 = PineActivationFunctionTanh(l0_0*-9.8049980534 + l0_1*13.5481068519 + l0_2*-17.1362809025 + l0_3*0.7142100864 + l0_4*4.4759163422 + l0_5*4.5716161777 + l0_6*1.4290884628 + l0_7*8.3952862712 + l0_8*-7.1613700432 + l0_9*-3.3249489518+ l0_10*-0.7789587912 + l0_11*-1.7987628873 + l0_12*13.364752545 + l0_13*5.3947219678 + l0_14*12.5267547127)
        l1_15 = PineActivationFunctionTanh(l0_0*0.9869461803 + l0_1*1.9473351905 + l0_2*2.032925759 + l0_3*7.4092080633 + l0_4*-1.9257741399 + l0_5*1.8153585328 + l0_6*1.1427866392 + l0_7*-0.3723167449 + l0_8*5.0009927384 + l0_9*-0.2275103411 + l0_10*2.8823012914 + l0_11*-3.0633141934 + l0_12*-2.785334815 + l0_13*2.727981E-4 + l0_14*-0.1253009512)
        l1_16 = PineActivationFunctionTanh(l0_0*4.9418118585 + l0_1*-2.7538199876 + l0_2*-16.9887588104 + l0_3*8.8734475297 + l0_4*-16.3022734814 + l0_5*-4.562496601 + l0_6*-1.2944373699 + l0_7*-9.6022946986 + l0_8*-1.018393866 + l0_9*-11.4094515429 + l0_10*24.8483091382 + l0_11*-3.0031522277 + l0_12*0.1513114555 + l0_13*-6.7170487021 + l0_14*-14.7759227576)
        l1_17 = PineActivationFunctionTanh(l0_0*5.5931454656 + l0_1*2.22272078 + l0_2*2.603416897 + l0_3*1.2661196599 + l0_4*-2.842826446 + l0_5*-7.9386099121 + l0_6*2.8278849111 + l0_7*-1.2289445238 + l0_8*4.571484248 + l0_9*0.9447425595 + l0_10*4.2890688351 + l0_11*-3.3228258483 + l0_12*4.8866215526 + l0_13*1.0693412194 + l0_14*-1.963203112)
        l1_18 = PineActivationFunctionTanh(l0_0*0.2705520264 + l0_1*0.4002328199 + l0_2*0.1592515845 + l0_3*0.371893552 + l0_4*-1.6639467871 + l0_5*2.2887318884 + l0_6*-0.148633664 + l0_7*-0.6517792263 + l0_8*-0.0993032992 + l0_9*-0.964940376 + l0_10*0.1286342935 + l0_11*0.4869943595 + l0_12*1.4498648166 + l0_13*-0.3257333384 + l0_14*-1.3496419812)
        l1_19 = PineActivationFunctionTanh(l0_0*-1.3223200798 + l0_1*-2.2505204324 + l0_2*0.8142804525 + l0_3*-0.848348177 + l0_4*0.7208860589 + l0_5*1.2033423756 + l0_6*-0.1403005786 + l0_7*0.2995941644 + l0_8*-1.1440473062 + l0_9*1.067752916 + l0_10*-1.2990534679 + l0_11*1.2588583869 + l0_12*0.7670409455 + l0_13*2.7895972983 + l0_14*-0.5376152512)
        l1_20 = PineActivationFunctionTanh(l0_0*0.7382351572 + l0_1*-0.8778865631 + l0_2*1.0950766363 + l0_3*0.7312146997 + l0_4*2.844781386 + l0_5*2.4526730903 + l0_6*-1.9175165077 + l0_7*-0.7443755288 + l0_8*-3.1591419438 + l0_9*0.8441602697 + l0_10*1.1979484448 + l0_11*2.138098544 + l0_12*0.9274159536 + l0_13*-2.1573448803 + l0_14*-3.7698356464)
        l1_21 = PineActivationFunctionTanh(l0_0*5.187120117 + l0_1*-7.7525670576 + l0_2*1.9008346975 + l0_3*-1.2031603996 + l0_4*5.917669142 + l0_5*-3.1878682719 + l0_6*1.0311747828 + l0_7*-2.7529484612 + l0_8*-1.1165884578 + l0_9*2.5524942323 + l0_10*-0.38623241 + l0_11*3.7961317445 + l0_12*-6.128820883 + l0_13*-2.1470707709 + l0_14*2.0173792965)
        l1_22 = PineActivationFunctionTanh(l0_0*-6.0241676562 + l0_1*0.7474455584 + l0_2*1.7435724844 + l0_3*0.8619835076 + l0_4*-0.1138406797 + l0_5*6.5979359352 + l0_6*1.6554154348 + l0_7*-3.7969458806 + l0_8*1.1139097376 + l0_9*-1.9588417 + l0_10*3.5123392221 + l0_11*9.4443103128 + l0_12*-7.4779291395 + l0_13*3.6975940671 + l0_14*8.5134262747)
        l1_23 = PineActivationFunctionTanh(l0_0*-7.5486576471 + l0_1*-0.0281420865 + l0_2*-3.8586839454 + l0_3*-0.5648792233 + l0_4*-7.3927282026 + l0_5*-0.3857538046 + l0_6*-2.9779885698 + l0_7*4.0482279965 + l0_8*-1.1522499578 + l0_9*-4.1562500212 + l0_10*0.7813134307 + l0_11*-1.7582667612 + l0_12*1.7071109988 + l0_13*6.9270873208 + l0_14*-4.5871357362)
        l1_24 = PineActivationFunctionTanh(l0_0*-5.3603442228 + l0_1*-9.5350611629 + l0_2*1.6749984422 + l0_3*-0.6511065892 + l0_4*-0.8424823239 + l0_5*1.9946675213 + l0_6*-1.1264361638 + l0_7*0.3228676616 + l0_8*5.3562230396 + l0_9*-1.6678168952+ l0_10*1.2612580068 + l0_11*-3.5362671399 + l0_12*-9.3895191366 + l0_13*2.0169228673 + l0_14*-3.3813191557)
        l1_25 = PineActivationFunctionTanh(l0_0*1.1362866429 + l0_1*-1.8960071702 + l0_2*5.7047307243 + l0_3*-1.6049785053 + l0_4*-4.8353898931 + l0_5*-1.4865381145 + l0_6*-0.2846893475 + l0_7*2.2322095997 + l0_8*2.0930488668 + l0_9*1.7141411002 + l0_10*-3.4106032176 + l0_11*3.0593289612 + l0_12*-5.0894813904 + l0_13*-0.5316299133 + l0_14*0.4705265416)
        l1_26 = PineActivationFunctionTanh(l0_0*-0.9401400975 + l0_1*-0.9136086957 + l0_2*-3.3808688582 + l0_3*4.7200776773 + l0_4*3.686296919 + l0_5*14.2133723935 + l0_6*1.5652940954 + l0_7*-0.2921139433 + l0_8*1.0244504511 + l0_9*-7.6918299134 + l0_10*-0.594936135 + l0_11*-1.4559914156 + l0_12*2.8056435224 + l0_13*2.6103905733 + l0_14*2.3412348872)
        l1_27 = PineActivationFunctionTanh(l0_0*1.1573980186 + l0_1*2.9593661909 + l0_2*0.4512594325 + l0_3*-0.9357210858 + l0_4*-1.2445804495 + l0_5*4.2716471631 + l0_6*1.5167912375 + l0_7*1.5026853293 + l0_8*1.3574772038 + l0_9*-1.9754386842 + l0_10*6.727671436 + l0_11*8.0145772889 + l0_12*7.3108970663 + l0_13*-2.5005627841 + l0_14*8.9604502277)
        l1_28 = PineActivationFunctionTanh(l0_0*6.3576350212 + l0_1*-2.9731672725 + l0_2*-2.7763558082 + l0_3*-3.7902984555 + l0_4*-1.0065574585 + l0_5*-0.7011836061 + l0_6*-1.0298068578 + l0_7*1.201007784 + l0_8*-0.7835862254 + l0_9*-3.9863597435 + l0_10*6.7851825502 + l0_11*1.1120256721 + l0_12*-2.263287351 + l0_13*1.8314374104 + l0_14*-2.279102097)
        l1_29 = PineActivationFunctionTanh(l0_0*-7.8741911036 + l0_1*-5.3370618518 + l0_2*11.9153868964 + l0_3*-4.1237170553 + l0_4*2.9491152758 + l0_5*1.0317132502 + l0_6*2.2992199883 + l0_7*-2.0250502364 + l0_8*-11.0785995839 + l0_9*-6.3615588554 + l0_10*-1.1687644976 + l0_11*6.3323478015 + l0_12*6.0195076962 + l0_13*-2.8972208702 + l0_14*3.6107747183)

        l2_0 = PineActivationFunctionTanh(l1_0*-0.590546797 + l1_1*0.6608304658 + l1_2*-0.3358268839 + l1_3*-0.748530283 + l1_4*-0.333460383 + l1_5*-0.3409307681 + l1_6*0.1916558198 + l1_7*-0.1200399453 + l1_8*-0.5166151854 + l1_9*-0.8537164676 +l1_10*-0.0214448647 + l1_11*-0.553290271 + l1_12*-1.2333302892 + l1_13*-0.8321813811 + l1_14*-0.4527761741 + l1_15*0.9012545631 + l1_16*0.415853215 + l1_17*0.1270548319 + l1_18*0.2000460279 + l1_19*-0.1741942671 + l1_20*0.419830522 + l1_21*-0.059839291 + l1_22*-0.3383001769 + l1_23*0.1617814073 + l1_24*0.3071848006 + l1_25*-0.3191182045 + l1_26*-0.4981831822 + l1_27*-1.467478375 + l1_28*-0.1676432563 + l1_29*1.2574849126)
        l2_1 = PineActivationFunctionTanh(l1_0*-0.5514235841 + l1_1*0.4759190049 + l1_2*0.2103576983 + l1_3*-0.4754377924 + l1_4*-0.2362941295 + l1_5*0.1155082119 + l1_6*0.7424215794 + l1_7*-0.3674198672 + l1_8*0.8401574461 + l1_9*0.6096563193 + l1_10*0.7437935674 + l1_11*-0.4898638101 + l1_12*-0.4168668092 + l1_13*-0.0365111095 + l1_14*-0.342675224 + l1_15*0.1870268765 + l1_16*-0.5843050987 + l1_17*-0.4596547471 + l1_18*0.452188522 + l1_19*-0.6737126684 + l1_20*0.6876072741 + l1_21*-0.8067776704 + l1_22*0.7592979467 + l1_23*-0.0768239468 + l1_24*0.370536097 + l1_25*-0.4363884671 + l1_26*-0.419285676 + l1_27*0.4380251141 + l1_28*0.0822528948 + l1_29*-0.2333910809)
        l2_2 = PineActivationFunctionTanh(l1_0*-0.3306539521 + l1_1*-0.9382247194 + l1_2*0.0746711276 + l1_3*-0.3383838985 + l1_4*-0.0683232217 + l1_5*-0.2112358049 + l1_6*-0.9079234054 + l1_7*0.4898595603 + l1_8*-0.2039825863 + l1_9*1.0870698641+ l1_10*-1.1752901237 + l1_11*1.1406403923 + l1_12*-0.6779626786 + l1_13*0.4281048906 + l1_14*-0.6327670055 + l1_15*-0.1477678844 + l1_16*0.2693637584 + l1_17*0.7250738509 + l1_18*0.7905904504 + l1_19*-1.6417250883 + l1_20*-0.2108095534 +l1_21*-0.2698557472 + l1_22*-0.2433656685 + l1_23*-0.6289943273 + l1_24*0.436428207 + l1_25*-0.8243825184 + l1_26*-0.8583496686 + l1_27*0.0983131026 + l1_28*-0.4107462518 + l1_29*0.5641683087)
        l2_3 = PineActivationFunctionTanh(l1_0*1.7036869992 + l1_1*-0.6683507666 + l1_2*0.2589197112 + l1_3*0.032841148 + l1_4*-0.4454796342 + l1_5*-0.6196149423 + l1_6*-0.1073622976 + l1_7*-0.1926393101 + l1_8*1.5280232458 + l1_9*-0.6136527036 +l1_10*-1.2722934357 + l1_11*0.2888655811 + l1_12*-1.4338638512 + l1_13*-1.1903556863 + l1_14*-1.7659663905 + l1_15*0.3703086867 + l1_16*1.0409140889 + l1_17*0.0167382209 + l1_18*0.6045646461 + l1_19*4.2388788116 + l1_20*1.4399738234 + l1_21*0.3308571935 + l1_22*1.4501137667 + l1_23*0.0426123724 + l1_24*-0.708479795 + l1_25*-1.2100800732 + l1_26*-0.5536278651 + l1_27*1.3547250573 + l1_28*1.2906250286 + l1_29*0.0596007114)
        l2_4 = PineActivationFunctionTanh(l1_0*-0.462165126 + l1_1*-1.0996742176 + l1_2*1.0928262999 + l1_3*1.806407067 + l1_4*0.9289147669 + l1_5*0.8069022793 + l1_6*0.2374237802 + l1_7*-2.7143979019 + l1_8*-2.7779203877 + l1_9*0.214383903 + l1_10*-1.3111536623 + l1_11*-2.3148813568 + l1_12*-2.4755355804 + l1_13*-0.6819733236 + l1_14*0.4425615226 + l1_15*-0.1298218043 + l1_16*-1.1744832824 + l1_17*-0.395194848 + l1_18*-0.2803397703 + l1_19*-0.4505071197 + l1_20*-0.8934956598 + l1_21*3.3232916348 + l1_22*-1.7359534851 + l1_23*3.8540421743 + l1_24*1.4424032523 + l1_25*0.2639823693 + l1_26*0.3597053634 + l1_27*-1.0470693728 + l1_28*1.4133480357 + l1_29*0.6248098695)
        l2_5 = PineActivationFunctionTanh(l1_0*0.2215807411 + l1_1*-0.5628295071 + l1_2*-0.8795982905 + l1_3*0.9101585104 + l1_4*-1.0176831976 + l1_5*-0.0728884401 + l1_6*0.6676331658 + l1_7*-0.7342174108 + l1_8*9.4428E-4 + l1_9*0.6439774272 + l1_10*-0.0345236026 + l1_11*0.5830977027 + l1_12*-0.4058921837 + l1_13*-0.3991888077 + l1_14*-1.0090426973 + l1_15*-0.9324780698 + l1_16*-0.0888749165 + l1_17*0.2466351736 + l1_18*0.4993304601 + l1_19*-1.115408696 + l1_20*0.9914246705 + l1_21*0.9687743445 + l1_22*0.1117130875 + l1_23*0.7825109733 + l1_24*0.2217023612 + l1_25*0.3081256411 + l1_26*-0.1778007966 + l1_27*-0.3333287743 + l1_28*1.0156352461 + l1_29*-0.1456257813)
        l2_6 = PineActivationFunctionTanh(l1_0*-0.5461783383 + l1_1*0.3246015999 + l1_2*0.1450605434 + l1_3*-1.3179944349 + l1_4*-1.5481775261 + l1_5*-0.679685633 + l1_6*-0.9462335139 + l1_7*-0.6462399371 + l1_8*0.0991658683 + l1_9*0.1612892194 +l1_10*-1.037660602 + l1_11*-0.1044778824 + l1_12*0.8309203243 + l1_13*0.7714766458 + l1_14*0.2566767663 + l1_15*0.8649416329 + l1_16*-0.5847461285 + l1_17*-0.6393969272 + l1_18*0.8014049359 + l1_19*0.2279568228 + l1_20*1.0565217821 + l1_21*0.134738029 + l1_22*0.3420395576 + l1_23*-0.2417397219 + l1_24*0.3083072038 + l1_25*0.6761739059 + l1_26*-0.4653817053 + l1_27*-1.0634057566 + l1_28*-0.5658892281 + l1_29*-0.6947283681)
        l2_7 = PineActivationFunctionTanh(l1_0*-0.5450410944 + l1_1*0.3912849372 + l1_2*-0.4118641117 + l1_3*0.7124695074 + l1_4*-0.7510266122 + l1_5*1.4065673913 + l1_6*0.9870731545 + l1_7*-0.2609363107 + l1_8*-0.3583639958 + l1_9*0.5436375706 +l1_10*0.4572450099 + l1_11*-0.4651538878 + l1_12*-0.2180218212 + l1_13*0.5241262959 + l1_14*-0.8529323253 + l1_15*-0.4200378937 + l1_16*0.4997885721 + l1_17*-1.1121528189 + l1_18*0.5992411048 + l1_19*-1.0263270781 + l1_20*-1.725160642 + l1_21*-0.2653995722 + l1_22*0.6996703032 + l1_23*0.348549086 + l1_24*0.6522482482 + l1_25*-0.7931928436 + l1_26*-0.5107994359 + l1_27*0.0509642698 + l1_28*0.8711187423 + l1_29*0.8999449627)
        l2_8 = PineActivationFunctionTanh(l1_0*-0.7111081522 + l1_1*0.4296245062 + l1_2*-2.0720732038 + l1_3*-0.4071818684 + l1_4*1.0632721681 + l1_5*0.8463224325 + l1_6*-0.6083948423 + l1_7*1.1827669608 + l1_8*-0.9572307844 + l1_9*-0.9080517673 + l1_10*-0.0479029057 + l1_11*-1.1452853213 + l1_12*0.2884352688 + l1_13*0.1767851586 + l1_14*-1.089314461 + l1_15*1.2991763966 + l1_16*1.6236630806 + l1_17*-0.7720263697 + l1_18*-0.5011541755 + l1_19*-2.3919413568 + l1_20*0.0084018338 + l1_21*0.9975216139 + l1_22*0.4193541029 + l1_23*1.4623834571 + l1_24*-0.6253069691 + l1_25*0.6119677341 + l1_26*0.5423948388 + l1_27*1.0022450377 + l1_28*-1.2392984069 + l1_29*1.5021529822)
        
        l3_0 = PineActivationFunctionTanh(l2_0*0.3385061186 + l2_1*0.6218531956 + l2_2*-0.7790340983 + l2_3*0.1413078332 + l2_4*0.1857010624 + l2_5*-0.1769456351 + l2_6*-0.3242337911 + l2_7*-0.503944883 + l2_8*0.1540568869)
        
        if(l3_0 > 0.1 and temp == 0):
            buying[i] = True
        elif(l3_0 > 0.1 and temp == 1):
            buying[i] = True
        elif(l3_0<=0.1):
            buying[i] = False
        else:
            buying[i] = buying[i-1]
    # print(l3_0)
    return buying,l3_0

def HA(df, length):

    df['hopen'] = [0.0]*length
    df['hclose'] = [0.0]*length
    df['hhigh'] = [0.0]*length
    df['hlow'] = [0.0]*length
    for i in range(1, length):
        df['hopen'][i] = (df['hopen'][i-1] + df['hclose'][i-1])/2.0
        df['hclose'][i] = (df['open'][i] + df['high'][i] +
                           df['low'][i] + df['close'][i]) / 4.0
        df['hhigh'][i] = max(df['hopen'][i], df['hclose'][i], df['high'][i])
        df['hlow'][i] = min(df['hopen'][i], df['hclose'][i], df['low'][i])

    
    df['rsi5hl'] = RSIIndicator((df['high']+df['low'])/2, window=5).rsi()

    df['rsi5o'] = RSIIndicator(df['hopen'], window=5).rsi()
    df['rsi5h'] = RSIIndicator(df['hhigh'], window=5).rsi()
    df['rsi5l'] = RSIIndicator(df['hlow'], window=5).rsi()
    df['rsi5c'] = RSIIndicator(df['hclose'], window=5).rsi()
    
    df['rsio'] = RSIIndicator(df['hopen']).rsi()
    df['rsi2o'] = RSIIndicator(df['hopen'], window=2).rsi()
    df['rsic'] = RSIIndicator(df['hclose']).rsi()
    df['rsi2c'] = RSIIndicator(df['hclose'], window=2).rsi()
    

    return df


def getPerc(a, b):
    ans = (a-b)*100/b
    return ans


def gulian(df, length,coin):
    df = HA(df, length)
    # print(coin)
    buying1,l1 = ANN(coin,0)
    buying2,l2 = ANN(coin,1)
    # print()
    # df['true'] = [False]*length
    # for i in range(2,length):
    #     if(df['rsi'][i] < 30 and df['rsi'][i] > df['rsi'][i-1] and df['hopen'][i] < df['hclose'][i] and df['macd'][i] > df['signal'][i]
    #     and not (df['rsi'][i-1] < 30 and df['rsi'][i-1] > df['rsi'][i-2] and df['open'][i-1] < df['close'][i-1] and df['macd'][i-1] > df['signal'][i-1])):
    #         if(df['macd'][i-1] > df['signal'][i-1]):
    #             if(df['macd'][i-1] - df['signal'][i-1] < df['macd'][i] - df['signal'][i]):
    #                 df['true'][i] = True
    #         else:
    #             df['true'][i] = True
    canBuy = buying2[49] == True and buying1[49] == buying2[49]
#    print(canBuy)
    # print(((datetime.datetime.now().hour*60 + datetime.datetime.now().minute - (5*60+30))%240))
    if(canBuy):
        print(coin,l1,l2)
    return df,canBuy


def collectData(coin, length,temp=False):
    global hasProfitPerDayPosted,profitperday
    if(datetime.datetime.now().hour > 6):
        if(not hasProfitPerDayPosted):
            url = 'https://api.telegram.org/bot2072407643:AAEq8g8QuQe13WY1n9lhTKh5AWQNClu0w48/sendMessage?chat_id={}&text=Total Profit for today : {}$'.format(chatId,profitperday)
            requests.get(url)
            hasProfitPerDayPosted = True
            profitperday = 0
    else:
        hasProfitPerDayPosted = False

    canBuy = ((datetime.datetime.now().hour*60 + datetime.datetime.now().minute)%240 < 120)
    
    if(canBuy):
        try:
            bars = client.get_klines(
                symbol=coin, interval=Client.KLINE_INTERVAL_5MINUTE, limit=length)
            df = pd.DataFrame(bars, columns=["time", "open", "high", "low", "close", "volume", "Close time", "Quote asset volume",
                                            "Number of trades", "Taker buy base asset volume", "Taker buy quote asset volume", "Can be ignored"])
            df['open'] = pd.Series(list(map(float, df['open'])))
            df['high'] = pd.Series(list(map(float, df['high'])))
            df['low'] = pd.Series(list(map(float, df['low'])))
            df['close'] = pd.Series(list(map(float, df['close'])))
            df['volume'] = pd.Series(list(map(float, df['volume'])))
    
    
        
            # print(coin,end=" ")
            
            if(getAvg(df, length) > 0.5 ):
                df,canBuy = gulian(df, length,coin)
                if((canBuy or temp)
                    
                    # and getAvg(df, length)*2 > getPerc(df['close'][208],df['open'][208]) + getPerc(df['close'][207],df['open'][207])
                    # and (df['open'][208] >df['close'][208] or df['open'][207] >df['close'][207] or df['open'][206] >df['close'][206])
                    and (df['rsio'][length-2] < 30 and df['rsi2o'][length-2] < 5 and df['rsio'][length-2] < df['rsio'][length-1])
                    or (df['rsic'][length-2] < 30 and df['rsi2c'][length-2] < 5 and df['rsic'][length-2] < df['rsic'][length-1])
                    ):
                    
                    return True, df, getAvg(df, length)
                
        except:
            print("err")
            return False, None, None
    return False, None, None


def findBestCoin():
    global no_of_coins, chosenCoins,hasProfitPerDayPosted,profitperday

    # canBuy = ((datetime.datetime.now().hour*60 + datetime.datetime.now().minute -330)%60 < 9 and (datetime.datetime.now().hour*60 + datetime.datetime.now().minute -330)%60 >=5) and (datetime.datetime.now().hour*60 + datetime.datetime.now().minute -330)%240 < 180
    canBuy = True
    
    if canBuy:
        
        # try:
        url = "https://www.binance.com/exchange-api/v2/public/asset-service/product/get-products"
        res = requests.get(url)
        data = list(json.loads(res.content)["data"])
        # prods = {}
        # for i in range(len(data)):
        #     prods[data[i]['s']] = data[i]
        # tempArr = client.get_ticker()
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

                
        # for i in range(int(len(prods)/2)):
        #     print(prods[i]['s'])
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
                            
        # print("No coin found")
        # print("######################################################")
        # except:
        #     print("err")
    return True


def reStart():
    print("Finding coins")
    while findBestCoin():
        pass


api_key = "4ZlklEkP3tukyfak8WeYyhQVTDRcmuRL0tWzAqMLRDgQMEj50KMEOq7HSC34fqWZ"
api_secret = "lLFmGxsEAOe6PTSQGcM0M2b7vqZaVVG8Qs0o0t3iOa6RKpZXGnF3V0hcjKipu6dI"
client = Client(api_key, api_secret,{'timeout': 60})

no_of_coins = 6
# balance = float(client.get_asset_balance(asset='USDT')['free'])
balance = 1000

initialTradeAmount = [int(balance/no_of_coins)] * no_of_coins

no_of_trades = 0

chosenCoins = [""] * no_of_coins

profitperday = 0
hasProfitPerDayPosted = False
# chatId = "527450766"
chatId = "-1001590033171"

reStart()
#collectData("LINAUSDT", 1000)
