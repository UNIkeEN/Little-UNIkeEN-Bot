from typing import Tuple, Union

import mysql.connector
from mysql.connector.connection import MySQLConnection
from mysql.connector.cursor import MySQLCursor
from mysql.connector.pooling import PooledMySQLConnection

from .basicConfigs import BOT_SELF_QQ, sqlConfig


def createBotDataDb():
    mydb = mysql.connector.connect(**sqlConfig)
    mycursor = mydb.cursor()
    mydb.autocommit = True
    mycursor.execute("""
    create database if not exists `BOT_DATA_%d`
    """%BOT_SELF_QQ)
def newSqlSession(autocommit:bool=True)->Tuple[MySQLConnection, MySQLCursor]:
    mydb = mysql.connector.connect(charset='utf8mb4',**sqlConfig)
    mydb.autocommit = autocommit
    mycursor = mydb.cursor()
    mycursor.execute('use `BOT_DATA_%d`'%BOT_SELF_QQ)
    return mydb, mydb.cursor()