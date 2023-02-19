import json
from typing import Union, Any, List, Tuple
from utils.basicEvent import send, warning
from utils.standardPlugin import StandardPlugin
from utils.basicConfigs import ROOT_PATH, SAVE_TMP_PATH
from utils.responseImage import ResponseImage, PALETTE_CYAN, FONTS_PATH, ImageFont
import re, os.path, os
from pypinyin import lazy_pinyin
FAQ_DATA_PATH="data"
class HelpFAQ(StandardPlugin):
    def judgeTrigger(self, msg:str, data:Any) -> bool:
        return msg == '问答帮助' and data['message_type']=='group'
    def executeEvent(self, msg: str, data: Any) -> Union[None, str]:
        group_id = data['group_id']
        send(group_id, "获取问答库： '维护 show q'\n"
                       "新建答案： '维护 add <key> <original ans>'\n"
                       "更改答案： '维护 edit <key> <new ans>'\n"
                       "删除答案： '维护 del <key>'\n"
                       "附加答案： '维护 append <key> <ans to append>'")
        return "OK"
    def getPluginInfo(self)->Any:
        return {
            'name': 'AskFAQ',
            'description': '问答帮助',
            'commandDescription': '问答帮助',
            'usePlace': ['group', ],
            'showInHelp': True,
            'pluginConfigTableNames': [],
            'version': '1.0.2',
            'author': 'Unicorn',
        }
class AskFAQ(StandardPlugin):
    def __init__(self):
        self.pattern = re.compile(r'^问\s+([^\s]+)$')
    def judgeTrigger(self, msg:str, data:Any) -> bool:
        return self.pattern.match(msg) != None and data['message_type']=='group'
    def executeEvent(self, msg:str, data:Any) -> Union[None, str]:
        msg = self.pattern.findall(msg)[0]
        group_id = data['group_id']
        hasMsg, ans = get_answer(group_id, msg)
        if hasMsg:
            ans = "[CQ:reply,id=%d]%s\n【%s】"%(data['message_id'], ans, msg)
        else:
            ans = "[CQ:reply,id=%d]%s"%(data['message_id'], ans)
        send(group_id, ans)

    def getPluginInfo(self)->Any:
        return {
            'name': 'AskFAQ',
            'description': '问答库',
            'commandDescription': '问 [...]',
            'usePlace': ['group', ],
            'showInHelp': True,
            'pluginConfigTableNames': [],
            'version': '1.0.2',
            'author': 'Unicorn',
        }
class MaintainFAQ(StandardPlugin):
    def __init__(self):
        self.patterns = {
            'show': re.compile(r'^维护\s+show\s+q$'),
            'add': re.compile(r'^维护\s+add\s+([^\s]+)\s(.*)$'),
            'edit': re.compile(r'^维护\s+edit\s+([^\s]+)\s(.*)$'),
            'del': re.compile(r'^维护\s+del\s+([^\s]+)$'),
            'append': re.compile(r'^维护\s+append\s+([^\s]+)\s(.*)$'),
        }
    def judgeTrigger(self, msg:str, data:Any) -> bool:
        return msg.startswith('维护 ') and data['message_type']=='group'
    def executeEvent(self, msg:str, data:Any) -> Union[None, str]:
        group_id = data['group_id']
        message_id = data['message_id']
        if self.patterns['show'].match(msg) != None:
            questions = show_all(group_id)
            if False:
                send(group_id,"本群问题列表：\n"+",".join(questions))
            else:
                imgPath = drawQuestionCard(questions, group_id)
                imgPath = imgPath if os.path.isabs(imgPath) else os.path.join(ROOT_PATH, imgPath)
                send(group_id, '[CQ:image,file=files:///%s]'%imgPath)
        elif self.patterns['edit'].match(msg) != None:
            key, val = self.patterns['edit'].findall(msg)[0]
            succ = edit_question(group_id, key, val)
            if succ:
                msg = "[CQ:reply,id=%d]问题修改成功：\n%s\n【%s】"%(message_id, val, key)
            else:
                msg = "[CQ:reply,id=%d]问题【%s】不存在，请先添加"%(message_id, key)
            send(group_id, msg)
        elif self.patterns['add'].match(msg)!=None:
            key, val = self.patterns['add'].findall(msg)[0]
            succ = add_question(group_id, key, val)
            if succ:
                msg = "[CQ:reply,id=%d]问题新建成功：\n%s\n【%s】"%(message_id, val, key)
            else:
                msg = "[CQ:reply,id=%d]问题【%s】已存在"%(message_id, key)
            send(group_id, msg)
        elif self.patterns['del'].match(msg) != None:
            key = self.patterns['del'].findall(msg)[0]
            succ = del_question(group_id, key)
            if succ:
                msg = "[CQ:reply,id=%d]问题【%s】删除成功"%(message_id, key)
            else:
                msg = "[CQ:reply,id=%d]问题【%s】不存在"%(message_id, key)
            send(group_id, msg)
        elif self.patterns['append'].match(msg) != None:
            key, val = self.patterns['append'].findall(msg)[0]
            succ, newAns = append_question(group_id, key, val)
            if succ:
                msg = "[CQ:reply,id=%d]问题修改成功\n%s\n【%s】"%(message_id, newAns, key)
            else:
                msg = "[CQ:reply,id=%d]问题【%s】不存在，请先添加"%(message_id, key)
            send(group_id, msg)
        else:
            send(group_id, '输入格式不对哦，请输入【问答帮助】获取操作指南')
        return "OK"
    def getPluginInfo(self)->Any:
        return {
            'name': 'MaintainFAQ',
            'description': '维护问答库',
            'commandDescription': '维护 [...]',
            'usePlace': ['group', ],
            'showInHelp': True,
            'pluginConfigTableNames': [],
            'version': '1.0.2',
            'author': 'Unicorn',
        }
def loadQuestions(group_id: int)->dict:
    """获取问题列表
    @group_id: 群号
    @return: 问题列表
    """
    exact_path = os.path.join(FAQ_DATA_PATH, str(group_id), 'faq.json')
    if not os.path.isfile(exact_path):
        return {}
    else:
        with open(exact_path, 'r') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError as e:
                warning("json decode error in faq: {}".format(e))
            except BaseException as e:
                warning("base exception in faq: {}".format(e))
            return {}
def dumpQuestions(group_id: int, questions: dict):
    """存储问题列表
    @group_id: 群号
    @questions: 问题列表
    """
    save_path = os.path.join(FAQ_DATA_PATH, str(group_id))
    os.makedirs(save_path, exist_ok=True)
    exact_path = os.path.join(FAQ_DATA_PATH, str(group_id), 'faq.json')
    with open(exact_path, 'w') as f:
        json.dump(questions, f)
def get_answer(group_id,key)->Tuple[bool, str]:
    answers = loadQuestions(group_id)
    if key not in answers.keys():
        return False, "没有查询到结果喔 qwq"
    else:
        return True, answers[key]
        
def add_question(group_id,key,ans)->bool:
    answers = loadQuestions(group_id)
    if key not in answers.keys():
        answers[key] = ans
        dumpQuestions(group_id, answers)
        return True
    else:
        return False

def edit_question(group_id,key,ans)->bool:
    answers = loadQuestions(group_id)
    if key not in answers.keys():
        return False
    else:
        answers[key] = ans
        dumpQuestions(group_id, answers)
        return True

def del_question(group_id,key)->bool:
    answers = loadQuestions(group_id)
    if key not in answers.keys():
        return False
    else:
        del answers[key]
        dumpQuestions(group_id, answers)
        return True
def append_question(group_id, key, val)->Tuple[bool, str]:
    answers = loadQuestions(group_id)
    if key not in answers.keys():
        return False, ""
    else:
        answers[key] = answers[key] + val
        dumpQuestions(group_id, answers)
        return True, answers[key]
def show_all(group_id)->List[str]:
    answers = loadQuestions(group_id)
    return answers.keys()

def drawQuestionCard(questions: List[str], group_id: int)->str:
    """绘制问答列表图像
    @questions: 问题列表
    """
    questions = sorted(questions, key=lambda x: lazy_pinyin(x[0])[0].lower())
    letterGroups = {'abcde': [], 'fghij': [], 'klmno': [], 'pqrst': [], 'uvwxyz': [], '0-9': [], '#': []}
    for q in questions:
        firstLetter = lazy_pinyin(q[0])[0][0].lower()
        firstLetter = ord(firstLetter)
        if firstLetter >= ord('0') and firstLetter <= ord('9'):
            letterGroups['0-9'].append(q)
        elif firstLetter >= ord('a') and firstLetter <= ord('e'):
            letterGroups['abcde'].append(q)
        elif firstLetter >= ord('f') and firstLetter <= ord('j'):
            letterGroups['fghij'].append(q)
        elif firstLetter >= ord('k') and firstLetter <= ord('o'):
            letterGroups['klmno'].append(q)
        elif firstLetter >= ord('p') and firstLetter <= ord('t'):
            letterGroups['pqrst'].append(q)
        elif firstLetter >= ord('u') and firstLetter <= ord('z'):
            letterGroups['uvwxyz'].append(q)
        else:
            letterGroups['#'].append(q)

    helpCards = ResponseImage(
        title = '%d FAQ 问题列表'%group_id, 
        titleColor = PALETTE_CYAN,
        layout = 'two-column',
        width = 1280,
        cardBodyFont= ImageFont.truetype(os.path.join(FONTS_PATH, 'SourceHanSansCN-Medium.otf'), 24)
    )
    for k, v in letterGroups.items():
        cardList = []
        cardList.append(('title', k))
        cardList.append(('separator', ))
        cardList.append(('body', "、".join(v)))
        helpCards.addCard(ResponseImage.RichContentCard(
            raw_content=cardList, titleFontColor=PALETTE_CYAN))
    savePath = os.path.join(SAVE_TMP_PATH, '%d-faq.png'%group_id)
    helpCards.generateImage(savePath)
    return savePath