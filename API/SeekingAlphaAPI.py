import requests
import time
import json
from MongoDB import MongoDB
from LineNotifyMessage import line_notify_message
from SetVPN import VPN


class SeekingAlphaAPI:
    def __init__(self):
        # init MongoDB class
        self.mongodb = MongoDB("SeekingAlpha")
        # init VPN class
        self.vpn = VPN()
        # start time
        self.start_time = time.time()
        # current ticker
        self.current_ticker = None
        # get total ticker count
        self.total_ticker_count = 0
        # get total news count
        self.total_news_cnt = 0
        # error count in one ticker
        self.ticker_error_times = 0
        # base waiting time (second)
        self.waiting_time = 4

        # 開啟VPN
        self.vpn.start()

    def execute(self, ticker_list):
        """
        API對外唯一接口，統一名稱
        :param ticker_list: 要查詢股票代號LIST
        """
        try:

            for idx, ticker in enumerate(ticker_list):
                print("===== start getting {} news from Seeking Alpha ===== {}".format(ticker, str(idx + 1)))

                # 狀態資訊
                self.update_current_ticker(ticker)  # 當前爬新聞的股票
                self.update_ticker_error_times(True)  # 重置股票錯誤次數

                # 抓新聞
                self.exec_get_news_by_ticker(ticker)

                # 更新成功的股票數
                self.update_total_ticker_count()

                time.sleep(self.waiting_time)

            # 最後關掉VPN
            self.vpn.stop()

            # line 提醒通知 更新成功
            self.send_success_msg()

        except Exception as e:
            print(e)
            self.send_fail_msg()  # 失敗提醒
            raise e

    def exec_get_news_by_ticker(self, ticker):
        """
        使用股票代碼去抓news
        :param ticker: 股票代碼
        """
        # 取得 news_id list
        news_id_list = self.get_stock_news_id_list(ticker)

        # 跟 mongoDB 比對，沒有該 news_id 的資料再去爬蟲
        for news_id in news_id_list:
            if self.mongodb.check_news_exist(news_id):
                # true == data exist
                # print("news existed")
                time.sleep(0.1)
            else:
                # no data in db, so insert
                news_layout = self.get_news_content(news_id)
                self.mongodb.insert_news(news_layout)
                print("get news success")
                self.update_total_news_cnt()  # 更新有抓到的新聞數量

    def get_stock_news_id_list(self, ticker):
        """
        取得該ticker的news_id，集成list
        :param ticker: 股票代號
        :return: news_id list
        """
        # return list
        news_id_list = []

        # data source https://seekingalpha.com/
        # requests url
        url = "https://seekingalpha.com/api/v3/symbols/{}/news".format(
            ticker.lower())
        # requests header
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.114 Safari/537.36',
            'referer': 'https://seekingalpha.com/symbol/{}'.format(ticker)
        }

        res = requests.get(url, headers=headers)

        if res.status_code == 200:

            content = json.loads(res.text)

            if "data" in content:
                # 有值才執行
                dataList = content["data"]

                for data in dataList:
                    news_id = data["links"]["self"].split("/")[2].split("-")[0]
                    news_id_list.append(news_id)

                # prevent web timeout
                time.sleep(2 * self.waiting_time)

                return news_id_list

            else:
                # IP被鎖
                self.reset_ip_lock()
                # 重新執行
                self.exec_get_news_by_ticker(ticker)
                # 回傳空值
                return []

        else:
            # 重試連線次數
            requests.DEFAULT_RETRIES = 5
            # 關閉多餘的連接
            s = requests.session()
            s.keep_alive = False

            # 無法取得網頁資料
            self.reset_ip_lock()
            # 重新執行
            self.exec_get_news_by_ticker(ticker)
            # 回傳空值
            return []

    def get_news_content(self, news_id):
        """
        使用news_id取得網站資料，並匯成layout
        :param news_id:
        :return: insert layout
        """
        reportUrl = "https://seekingalpha.com/api/v3/news/" + news_id

        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.93 Safari/537.36'
        }

        res = requests.get(reportUrl, headers=headers)

        if res.status_code == 200:

            content = json.loads(res.text)

            if "data" in content:
                data_attributes = content["data"]["attributes"]

                news_layout = {
                    "news_id": news_id,
                    "date": data_attributes["publishOn"],
                    "title": data_attributes["title"],
                    "content": data_attributes["content"]
                }

                # prevent web timeout
                time.sleep(self.waiting_time)

                return news_layout
            else:
                # IP被鎖
                self.reset_ip_lock()
                # 重新執行
                return self.get_news_content(news_id)

        else:
            # 重試連線次數
            requests.DEFAULT_RETRIES = 5
            # 關閉多餘的連接
            s = requests.session()
            s.keep_alive = False

            # 無法取得網頁資料
            self.reset_ip_lock()
            # 重新執行
            return self.get_news_content(news_id)

    def reset_ip_lock(self):
        """
        IP被鎖，要重啟VPN
        """
        print("********** API return no data **********")
        self.update_ticker_error_times(False)  # 更新股票錯誤次數
        if self.ticker_error_times > 10:
            # 單一股票出現多次錯誤就停止爬蟲
            self.send_fail_msg()  # 失敗提醒
            # 關掉VPN
            self.vpn.stop()
            quit()
        else:
            self.vpn.re_start()  # 重啟VPN

    def update_current_ticker(self, ticker):
        self.current_ticker = ticker

    def update_total_ticker_count(self):
        self.total_ticker_count += 1

    def update_total_news_cnt(self):
        self.total_news_cnt += 1

    def update_ticker_error_times(self, is_reset=True):
        """
        更新單一股票出現錯誤次數
        :param is_reset: 是否要重置資料，否的話就加一
        """
        if is_reset:
            self.ticker_error_times = 0
        else:
            self.ticker_error_times += 1

    def send_success_msg(self):
        # 花費時間
        end_time = time.time()
        total_second = end_time - self.start_time
        total_minute = total_second // 60
        show_hour = round(total_minute // 60)  # 時
        show_minute = round(total_minute % 60)  # 分
        show_second = round(total_second % 60)  # 秒

        msg = "python get Seeking Alpha news API finished\nspend time: {} hours {} minutes {} seconds\nticker count: {}, total news count: {}".format(
            str(show_hour), str(show_minute), str(show_second), str(self.total_ticker_count), str(self.total_news_cnt))
        line_notify_message(msg)  # 提醒

    def send_fail_msg(self):
        msg = "python get Seeking Alpha news API error\ndone ticker count:{} current ticker: {}".format(str(self.total_ticker_count),
                                                                                          self.current_ticker)
        line_notify_message(msg)  # 提醒
