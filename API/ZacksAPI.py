import requests
from bs4 import BeautifulSoup
import re
import time
import json
from MongoDB import MongoDB
from LineNotifyMessage import line_notify_message
from SetVPN import VPN


class ZacksAPI:
    def __init__(self):
        # init MongoDB class
        self.mongodb = MongoDB("Zacks")
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
        self.waiting_time = 0.5

        # 開啟VPN
        self.vpn.start()

    def execute(self, ticker_list):
        """
        API對外唯一接口，統一名稱
        :param ticker_list: 要查詢股票代號LIST
        """
        try:

            for idx, ticker in enumerate(ticker_list):
                print("===== start getting {} news from Zacks ===== {}".format(ticker, str(idx + 1)))

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
        href_list = self.get_stock_news_href_list(ticker)

        # 跟 mongoDB 比對，沒有該 news_id 的資料再去爬蟲
        for href in href_list:
            info_list = href.split("/")
            news_id = info_list[3]
            news_title = info_list[4]

            if self.mongodb.check_news_exist(news_id):
                # true == data exist
                # print("news existed")
                time.sleep(0.1)
            else:
                # no data in db, so insert
                news_layout = self.get_news_content(news_id, news_title, href)
                if news_layout:
                    self.mongodb.insert_news(news_layout)
                    print("get news success")
                    self.update_total_news_cnt()  # 更新有抓到的新聞數量

    def get_stock_news_href_list(self, ticker):
        """
        取得該ticker的href，集成list
        :param ticker: 股票代號
        :return: href list
        """
        # return list
        href_list = []

        # data source https://www.zacks.com/
        # requests url
        url = "https://www.zacks.com/stock/research/{}/all-news/zacks".format(ticker)
        # requests header
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.114 Safari/537.36'
        }

        res = requests.get(url, headers=headers)

        if res.status_code == 200:
            content = res.text
            soup = BeautifulSoup(content, "html.parser")
            link_list = soup.find_all(href=re.compile("^/stock/news/"))
            for link in link_list:
                href_list.append(link["href"])  # 取得href

            return href_list

        else:
            # 重試連線次數
            requests.DEFAULT_RETRIES = 5
            # 關閉多餘的連接
            s = requests.session()
            s.keep_alive = False

            # IP被鎖
            self.reset_ip_lock()
            # 重新執行
            self.exec_get_news_by_ticker(ticker)
            # 回傳空值
            return []

    def get_news_content(self, news_id, news_title, href):
        """
        使用news_id取得網站資料，並匯成layout
        :param news_id:
        :param news_title:
        :param href:
        :return: insert layout
        """
        reportUrl = "https://www.zacks.com" + href

        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.93 Safari/537.36'
        }

        res = requests.get(reportUrl, headers=headers)

        if res.status_code == 200:
            content = res.text
            soup = BeautifulSoup(content, "html.parser")

            # 內容
            news_content = soup.find("div", {"id": "comtext"})

            if news_content is None:
                # 沒值就回傳空直
                return None
            else:

                # info
                dataLayer = soup.find("script", text=re.compile("dataLayer")).text

                # 資料整理
                paragraphs = dataLayer.split(" = ")[1]
                paragraphs = paragraphs.replace("\n", "")
                paragraphs = paragraphs.replace(" ", "")
                paragraphs = paragraphs.replace(";", "")
                paragraphs = paragraphs.replace("\'", '"')
                blogID = paragraphs.split("blogID")[1]
                blogID = blogID[2:-2]
                blogID = "," + blogID

                # 發布時間
                publish_date = blogID.split(',publish_date:"')[1].split('"')[0]

                news_layout = {
                    "news_id": news_id,
                    "date": publish_date,
                    "title": news_title,
                    "content": news_content.text.replace("\n", "")
                }

                # prevent web timeout
                time.sleep(self.waiting_time)

                return news_layout
        else:
            # 重試連線次數
            requests.DEFAULT_RETRIES = 5
            # 關閉多餘的連接
            s = requests.session()
            s.keep_alive = False

            # IP被鎖
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

        msg = "python get Zacks news API finished\nspend time: {} hours {} minutes {} seconds\nticker count: {}, total news count: {}".format(
            str(show_hour), str(show_minute), str(show_second), str(self.total_ticker_count), str(self.total_news_cnt))
        line_notify_message(msg)  # 提醒

    def send_fail_msg(self):
        msg = "python get Zacks news API error\ndone ticker count:{} current ticker: {}".format(str(self.total_ticker_count),
                                                                                          self.current_ticker)
        line_notify_message(msg)  # 提醒
