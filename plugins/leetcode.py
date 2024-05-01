from typing import Any, Union, Optional, Dict, List
from utils.basicEvent import warning, send
from utils.standardPlugin import StandardPlugin, ScheduleStandardPlugin
from utils.sqlUtils import newSqlSession
from utils.basicConfigs import ROOT_PATH, SAVE_TMP_PATH
from utils.configAPI import getPluginEnabledGroups
import requests, os, imgkit, time, datetime

def queryTopicTags(titleSlug:str)->Optional[List[str]]:
    json_data = {
        'query': '\n    query singleQuestionTopicTags($titleSlug: String!) {\n  question(titleSlug: $titleSlug) {\n    topicTags {\n      name\n      slug\n      translatedName\n    }\n  }\n}\n    ',
        'variables': {
            'titleSlug': titleSlug,
        },
        'operationName': 'singleQuestionTopicTags',
    }
    try:
        response = requests.post('https://leetcode.cn/graphql/', json=json_data)
        if not response.ok: return None
        return response.json()['data']['question']
    except Exception as e:
        print('!!!!!!!!!!!!', e)
    return None
def queryQuestion(titleSlug:str)->Optional[Dict[str, str]]:
    json_data = {
        'query': '\n    query questionTranslations($titleSlug: String!) {\n  question(titleSlug: $titleSlug) {\n    translatedTitle\n  translatedContent\n difficulty\n  }\n}\n    ',
        'variables': {
            'titleSlug': titleSlug,
        },
        'operationName': 'questionTranslations',
    }
    try:
        response = requests.post('https://leetcode.cn/graphql/', json=json_data)
        if not response.ok: return None
        return response.json()['data']['question']
    except Exception as e:
        print('!!!!!!!!!!!!', e)
    return None
def getLeetcodeDailyQuestion()->Optional[Dict[str, str]]:
    today = datetime.date.today()
    todayStr = today.strftime('%Y-%m-%d')
    json_data = {
        'query': '\n    query dailyQuestionRecords($year: Int!, $month: Int!) {\n  dailyQuestionRecords(year: $year, month: $month) {\n    date\n    question {\n      questionFrontendId\n      title\n      titleSlug\n      translatedTitle\n    }\n  }\n}\n    ',
        'variables': {
            'year': today.year,
            'month': today.month,
        },
        'operationName': 'dailyQuestionRecords',
    }
    try:
        response = requests.post('https://leetcode.cn/graphql/', json=json_data)
        if not response.ok: return None
        questions = response.json()['data']['dailyQuestionRecords']
        for q in questions:
            if q.get('date', None) == todayStr:
                question = q['question']
                questionDetail = queryQuestion(question['titleSlug'])
                if questionDetail == None: return None
                topicTags = queryTopicTags(question['titleSlug'])
                questionDetail.update(question)
                questionDetail.update(topicTags)
                return questionDetail
    except Exception as e:
        print('!!!!!!!!!!!!', e)
    return None
    
def getLeetcodeTags(leetcodeResponse:Dict[str, Any])->List[str]:
    topicTags = leetcodeResponse['topicTags']
    return [tag['translatedName'] for tag in topicTags]
        
def generateMsg(leetcodeResponse:Dict[str, Any])->str:
    # 题目题号
    no = leetcodeResponse.get('questionFrontendId')
    # 题名（中文）
    leetcodeTitle = leetcodeResponse.get('translatedTitle')
    # 提名 (英文)
    titleSlug = leetcodeResponse.get('titleSlug')
    # 题目难度级别
    level = leetcodeResponse.get('difficulty')
    # 题目内容
    context = leetcodeResponse.get('translatedContent')
    # 题目链接
    link = "https://leetcode-cn.com/problems/{}/".format(titleSlug) 
    message = "no: {}\ntitle: {}\nlevel: {}\n".format(no, leetcodeTitle, level)
    message += "tags:{}\n".format('、'.join(getLeetcodeTags(leetcodeResponse)))
    message += "link: {}".format(link)
    return message

def generateQuestionImg(leetcodeResponse:Dict[str, Any], savePath:str):
    imgkit.from_string(leetcodeResponse.get('translatedContent'), savePath)

class ShowLeetcode(StandardPlugin):
    def judgeTrigger(self, msg: str, data: Any) -> bool:
        return msg in ['-leetcode', '力扣']
    def executeEvent(self, msg: str, data: Any) -> Union[Any, str]:
        target = data['group_id'] if data['message_type']=='group' else data['user_id']
        leetcodeResponse = getLeetcodeDailyQuestion()
        if leetcodeResponse == None:
            send(target, '请求失败，请稍后重试', data['message_type'])
            return 'OK'
        savePath = os.path.join(ROOT_PATH, SAVE_TMP_PATH, 'leetcode-{}.png'.format(leetcodeResponse.get('questionFrontendId')))
        result = generateMsg(leetcodeResponse)
        if not os.path.isfile(savePath):
            generateQuestionImg(leetcodeResponse, savePath)
        send(target, '请查收今日leetcode：\n'+result+'[CQ:image,file=file:///{}]'.format(savePath), data['message_type'])
        return 'OK'
    def getPluginInfo(self) -> dict:
        return {
            'name': 'ShowLeetcode',
            'description': 'Leetcode每日一题',
            'commandDescription': '-leetcode / 力扣', 
            'usePlace': ['group', 'private', ],
            'showInHelp': True,
            'pluginConfigTableNames': [],
            'version': '1.0.0',
            'author': 'Unicorn',
        }

class LeetcodeReport(StandardPlugin, ScheduleStandardPlugin):
    def __init__(self) -> None:
        self.schedule(hour=8, minute=45)
    def judgeTrigger(self, msg: str, data: Any) -> bool:
        return False
    def executeEvent(self, msg: str, data: Any) -> Union[Any, str]:
        return None
    def tick(self) -> None:
        enabledGroups = getPluginEnabledGroups('leetcode')
        leetcodeResponse = getLeetcodeDailyQuestion()
        while leetcodeResponse == None:
            time.sleep(180)
            leetcodeResponse = getLeetcodeDailyQuestion()
        savePath = os.path.join(ROOT_PATH, SAVE_TMP_PATH, 'leetcode-{}.png'.format(leetcodeResponse.get('questionFrontendId')))
        result = generateMsg(leetcodeResponse)
        if not os.path.isfile(savePath):
            generateQuestionImg(leetcodeResponse, savePath)
        for groupId in enabledGroups:
            send(groupId, '早上好，请查收今天的leetcode:\n\n'+result+'[CQ:image,file=file:///{}]'.format(savePath))
        return 'OK'
    def getPluginInfo(self) -> dict:
        return {
            'name': 'LeetcodeReport',
            'description': 'Leetcode每日播报',
            'commandDescription': '[-grpcfg驱动]', 
            'usePlace': ['group', ],
            'showInHelp': True,
            'pluginConfigTableNames': [],
            'version': '1.0.0',
            'author': 'Unicorn',
        }