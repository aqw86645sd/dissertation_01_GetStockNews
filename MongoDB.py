import pymongo
from config import get_mongodb_address


class MongoDB:
    def __init__(self, API):
        self.client = pymongo.MongoClient(get_mongodb_address())
        # database
        self.database = self.client["python_getStockNews"]
        # collection
        if API == "SeekingAlpha":
            self.collection = self.database["original_SeekingAlpha"]
        elif API == "Zacks":
            self.collection = self.database["original_Zacks"]

    def check_news_exist(self, news_id):
        key = {"news_id": news_id}

        # no data == None
        result = self.collection.find_one(key)

        return result

    def insert_news(self, news_layout):
        self.collection.insert_one(news_layout)
