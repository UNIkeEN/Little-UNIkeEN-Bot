from typing import Union, Any
from utils.basic_event import *
from utils.standard_plugin import StandardPlugin
from utils.basic_configs import sqlConfig
import mysql.connector
from pymysql.converters import escape_string
from utils.ashare_api import get_price


def query_stocks(stock: str) -> str:
    stock = escape_string(stock)
    mydb = mysql.connector.connect(**sqlConfig)
    mycursor = mydb.cursor()
    mycursor.execute(
        """select ashareCode, name, fullName, industry from STOCKS.stockCode where regexp_like(name, '%s') or regexp_like(fullName, '%s') or regexp_like(ashareCode, '%s')""" % (
        stock, stock, stock))
    results = list(mycursor)
    resultText = ""
    for r in results[:5]:
        ashareCode, name, fullName, industry = r
        resultText += f"{ashareCode} | {name} | {fullName} | {industry}\n"
    resultText += f'共 {len(results)} 条结果'
    return resultText


def verify_stocks_code(stockCode: str) -> bool:
    stockCode = escape_string(stockCode)
    mydb = mysql.connector.connect(**sqlConfig)
    mycursor = mydb.cursor()
    mycursor.execute("""select count(*) from STOCKS.stockCode where ashareCode='%s'""" % (stockCode))
    result = list(mycursor)
    if len(result) < 1:
        return False
    return result[0][0] == 1


class QueryStocksHelper(StandardPlugin):  # 查询股票的帮助
    def judge_trigger(self, msg: str, data: Any) -> bool:
        return msg == '查股票帮助' or msg == "帮助查股票"

    def execute_event(self, msg: str, data: Any) -> Union[None, str]:
        target = data['group_id'] if data['message_type'] == 'group' else data['user_id']
        text = f'[CQ:reply,id={str(data["message_id"])}]查询股票命令格式：'
        text += '\narg0: -qstocks(alias: 查股票/查询股票/股票查询)'
        text += '\narg1: $想要查询的股票信息'
        text += '\neg: 查股票 sz300059'
        text += '\neg: 查股票 武汉'
        text += '\n\n注意: 已添加sql转义,不要做无意义的尝试'
        send(target, text, data['message_type'])
        return "OK"

    def get_plugin_info(self, ) -> Any:
        return {
            'name': 'QueryStocksHelper',
            'description': '查股票帮助',
            'commandDescription': '查股票帮助/帮助查股票',
            'usePlace': ['group', 'private', ],
            'showInHelp': True,
            'pluginConfigTableNames': [],
            'version': '1.0.0',
            'author': 'Unicorn',
        }


class QueryStocks(StandardPlugin):  # 查询股票
    def judge_trigger(self, msg: str, data: Any) -> bool:
        return msg.startswith('-qstocks') or msg.startswith('查询股票') or msg.startswith('股票查询') or msg.startswith(
            '查股票')

    def execute_event(self, msg: str, data: Any) -> Union[None, str]:
        target = data['group_id'] if data['message_type'] == 'group' else data['user_id']
        text = '[CQ:reply,id=' + str(data['message_id']) + ']'
        stock = msg.split(' ')
        if len(stock) < 2:
            text += '参数错误,请输入`查股票帮助`获取格式信息'
        else:
            result = query_stocks(stock[1])
            text += result
        send(target, text, data['message_type'])
        return "OK"

    def get_plugin_info(self, ) -> Any:
        return {
            'name': 'QueryStocks',
            'description': '查询股票',
            'commandDescription': '-qstocks/查询股票/股票查询/查股票',
            'usePlace': ['group', 'private', ],
            'showInHelp': True,
            'pluginConfigTableNames': [],
            'version': '1.0.0',
            'author': 'Unicorn',
        }


class QueryStocksPriceHelper(StandardPlugin):  # 查询股价格的帮助
    def judge_trigger(self, msg: str, data: Any) -> bool:
        return msg == '查股价帮助' or msg == "帮助查股价"

    def execute_event(self, msg: str, data: Any) -> Union[None, str]:
        target = data['group_id'] if data['message_type'] == 'group' else data['user_id']
        text = f'[CQ:reply,id={str(data["message_id"])}]查询股价格命令格式：'
        text += '\narg0: -qstockprice(alias: 查股价/查询股价/股价查询)'
        text += '\narg1: $想要查询的股票代码'
        text += '\neg: 查股价 sz300059'
        text += '\n\n注意: 已添加sql转义,不要做无意义的尝试'
        send(target, text, data['message_type'])
        return "OK"

    def get_plugin_info(self, ) -> Any:
        return {
            'name': 'QueryStocksPriceHelper',
            'description': '查股价帮助',
            'commandDescription': '查股价帮助/帮助查股价',
            'usePlace': ['group', 'private', ],
            'showInHelp': True,
            'pluginConfigTableNames': [],
            'version': '1.0.0',
            'author': 'Unicorn',
        }


class QueryStocksPrice(StandardPlugin):  # 查股价格
    def judge_trigger(self, msg: str, data: Any) -> bool:
        if msg == '查股价帮助' or msg == "帮助查股价":
            return False
        return msg.startswith("查股价") or msg.startswith("查询股价") or msg.startswith("股价查询") or msg.startswith(
            "-buystocks")

    def execute_event(self, msg: str, data: Any) -> Union[None, str]:
        target = data['group_id'] if data['message_type'] == 'group' else data['user_id']
        msg = msg.split(' ')
        text = f'[CQ:reply,id={str(data["message_id"])}]'
        if len(msg) < 2:
            text += '参数错误,请输入`查股价帮助`获取格式信息'
        else:
            stockCode = msg[1]
            if not verify_stocks_code(stockCode):
                text += "股票代码错误,请先查询正确的股票代码"
            else:
                priceData = get_price(stockCode, frequency='15m', count=3)
                text += '\n\n' + str(priceData)
        send(target, text, data['message_type'])
        return "OK"

    def get_plugin_info(self, ) -> Any:
        return {
            'name': 'QueryStocksPrice',
            'description': '查股价帮助',
            'commandDescription': '查股价/查询股价/股价查询',
            'usePlace': ['group', 'private', ],
            'showInHelp': True,
            'pluginConfigTableNames': [],
            'version': '1.0.0',
            'author': 'Unicorn',
        }


class BuyStocksHelper(StandardPlugin):  # 买股票的帮助
    def judge_trigger(self, msg: str, data: Any) -> bool:
        return msg == '买股票帮助' or msg == "帮助买股票"

    def execute_event(self, msg: str, data: Any) -> Union[None, str]:
        target = data['group_id'] if data['message_type'] == 'group' else data['user_id']
        text = f'[CQ:reply,id={str(data["message_id"])}]买股票命令格式：'
        text += '\narg0: -buystocks(alias: 买股票/购买股票/股票购买)'
        text += '\narg1: $购买股票代码(eg. sz300059)'
        text += '\narg2: $股票购买份数'
        text += '\neg: 买股票 sz300059 100'
        send(target, text, data['message_type'])
        return "OK"

    def get_plugin_info(self, ) -> Any:
        return {
            'name': 'BuyStocksHelper',
            'description': '买股票帮助',
            'commandDescription': '买股票帮助/帮助买股票',
            'usePlace': ['group', 'private', ],
            'showInHelp': True,
            'pluginConfigTableNames': [],
            'version': '1.0.0',
            'author': 'Unicorn',
        }


class BuyStocks(StandardPlugin):  # 买股票
    def judge_trigger(self, msg: str, data: Any) -> bool:
        if msg == '买股票帮助' or msg == "帮助买股票":
            return False
        return msg.startswith("买股票") or msg.startswith("购买股票") or msg.startswith("股票购买") or msg.startswith(
            "-buystocks")

    def execute_event(self, msg: str, data: Any) -> Union[None, str]:
        target = data['group_id'] if data['message_type'] == 'group' else data['user_id']
        text = f'[CQ:reply,id={data["message_id"]}]'
        msg = msg.split(' ')
        if len(msg) < 3:
            text += '参数错误,请输入`买股票帮助`获取格式信息'
        else:
            text += '目前买股票功能尚未做好'
        send(target, text, data['message_type'])
        return "OK"

    def get_plugin_info(self, ) -> Any:
        return {
            'name': 'BuyStocks',
            'description': '买股票',
            'commandDescription': '买股票/购买股票/股票购买',
            'usePlace': ['group', 'private', ],
            'showInHelp': True,
            'pluginConfigTableNames': [],
            'version': '1.0.0',
            'author': 'Unicorn',
        }
