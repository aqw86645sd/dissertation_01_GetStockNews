import requests
import re
# import random
import pymongo


class Entrance:
    def __init__(self, API):

        if API == "SeekingAlpha":
            from API.SeekingAlphaAPI import SeekingAlphaAPI
            self.news_api = SeekingAlphaAPI()
        elif API == "Zacks":
            from API.ZacksAPI import ZacksAPI
            self.news_api = ZacksAPI()

    def run(self):

        # 取得ETF全部股票
        ticker_list = self.get_etf_ticker_list("VOO")
        # ticker_list = self.get_voo_holding_list()

        # 如果要限定股票數量
        # ticker_list = ticker_list[1:]

        # 排序：重排
        # random.shuffle(ticker_list)

        self.news_api.execute(ticker_list)

    @staticmethod
    def get_etf_ticker_list(etf_symbol):
        """ getting holdings data from Zacks for the given ticker """
        url = "https://www.zacks.com/funds/etf/{}/holding".format(etf_symbol)
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.114 Safari/537.36"
        }

        with requests.Session() as req:
            req.headers.update(headers)
            r = req.get(url)
            tickerList = re.findall(r'etf\\\/(.*?)\\', r.text)

        return tickerList

    @staticmethod
    def get_voo_holding_list():
        # db setting
        client = pymongo.MongoClient("mongodb://localhost:27017/")
        voo_coll = client['python_getStockNews']['voo_holding_list']

        tickerList = list(voo_coll.find())[0]['ticker_list']

        return tickerList


if __name__ == '__main__':
    """
        SeekingAlpha
        Zacks
    """
    execute = Entrance("Zacks")
    execute.run()

    # execute2 = Entrance("SeekingAlpha")
    # execute2.run()
