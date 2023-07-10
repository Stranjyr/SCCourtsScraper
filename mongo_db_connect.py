from pymongo import MongoClient
from pymongo import server_api
from pymongo import database, collection

def get_database(database_name: str = "central_index"):
    uri = "mongodb+srv://copaccountablity.ntycuia.mongodb.net/?authSource=%24external&authMechanism=MONGODB-X509&retryWrites=true&w=majority"
    client = MongoClient(uri,
                         maxPoolSize=200,
                         waitQueueTimeoutMS=200,
                         waitQueueMultiple=500,
                         tls=True,
                         tlsCertificateKeyFile='./mongodb_cert/X509-cert-1480365900099724285.pem',
                         server_api=server_api.ServerApi('1'))
    db = client[database_name]
    return db


def add_collection(db: database.Database, col_name: str):
    collect = db[col_name]
    return collect

def add_list(collect: collection.Collection, data: list):
    collect.insert_many(data)