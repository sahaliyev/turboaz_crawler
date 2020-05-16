from pymongo import MongoClient


class MongoConnection(object):
    @staticmethod
    def get_connected():
        client = MongoClient(
            'mongodb://localhost:27017/?readPreference=primary&appname=MongoDB%20Compass%20Community&ssl=false')
        return client
