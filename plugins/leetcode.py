from typing import Any, Union, Optional, Dict, List
from utils.basicEvent import warning, send
from utils.standardPlugin import StandardPlugin, ScheduleStandardPlugin
from utils.sqlUtils import newSqlSession
from utils.basicConfigs import ROOT_PATH, SAVE_TMP_PATH
from utils.configAPI import getPluginEnabledGroups
import requests, os, imgkit, time

def get_leetcode_question_everyday()->Optional[Dict[str, Any]]:
    LEETCODE_URL="https://leetcode-cn.com/problemset/all/"
    base_url = 'https://leetcode-cn.com'
    try:
        resp = requests.get(url=LEETCODE_URL)
        response = requests.post(base_url + "/graphql", json={
            "operationName": "questionOfToday",
            "variables": {},
            "query": "query questionOfToday { todayRecord {   question {     questionFrontendId     questionTitleSlug     __typename   }   lastSubmission {     id     __typename   }   date   userStatus   __typename }}"
        })

        leetcodeTitle = response.json().get('data').get('todayRecord')[0].get("question").get(
            'questionTitleSlug')

        # 获取今日每日一题的所有信息
        url = base_url + "/problems/" + leetcodeTitle
        response = requests.post(base_url + "/graphql",
                                 json={"operationName": "questionData", "variables": {"titleSlug": leetcodeTitle},
                                       "query": "query questionData($titleSlug: String!) {  question(titleSlug: $titleSlug) {    questionId    questionFrontendId    boundTopicId    title    titleSlug    content    translatedTitle    translatedContent    isPaidOnly    difficulty    likes    dislikes    isLiked    similarQuestions    contributors {      username      profileUrl      avatarUrl      __typename    }    langToValidPlayground    topicTags {      name      slug      translatedName      __typename    }    companyTagStats    codeSnippets {      lang      langSlug      code      __typename    }    stats    hints    solution {      id      canSeeDetail      __typename    }    status    sampleTestCase    metaData    judgerAvailable    judgeType    mysqlSchemas    enableRunCode    envInfo    book {      id      bookName      pressName      source      shortDescription      fullDescription      bookImgUrl      pressImgUrl      productUrl      __typename    }    isSubscribed    isDailyQuestion    dailyRecordStatus    editorType    ugcQuestionId    style    __typename  }}"})
        return response.json().get('data').get("question")
    except Exception as e:
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
        leetcodeResponse = get_leetcode_question_everyday()
        if leetcodeResponse == None:
            send(target, '请求失败，请稍后重试', data['message_type'])
            return 'OK'
        savePath = os.path.join(ROOT_PATH, SAVE_TMP_PATH, 'leetcode-{}.png'.format(leetcodeResponse.get('questionFrontendId')))
        result = generateMsg(leetcodeResponse)
        if not os.path.isfile(savePath):
            generateQuestionImg(leetcodeResponse, savePath)
        send(target, result+'[CQ:image,file=files:///{}]'.format(savePath), data['message_type'])
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
        leetcodeResponse = get_leetcode_question_everyday()
        while leetcodeResponse == None:
            time.sleep(180)
            leetcodeResponse = get_leetcode_question_everyday()
        savePath = os.path.join(ROOT_PATH, SAVE_TMP_PATH, 'leetcode-{}.png'.format(leetcodeResponse.get('questionFrontendId')))
        result = generateMsg(leetcodeResponse)
        if not os.path.isfile(savePath):
            generateQuestionImg(leetcodeResponse, savePath)
        for groupId in enabledGroups:
            send(groupId, '早上好，请查收今天的leetcode:\n\n'+result+'[CQ:image,file=files:///{}]'.format(savePath))
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