from typing import Dict, Union, Any, List, Tuple
from utils.basicEvent import send, warning, upload_group_file, get_group_file_url, get_group_root_files
from utils.configAPI import getGroupAdmins
from utils.standardPlugin import StandardPlugin
from utils.basicConfigs import ROOT_PATH, SAVE_TMP_PATH, sqlConfig, APPLY_GROUP_ID
from utils.responseImage import PALETTE_RED, ResponseImage, PALETTE_CYAN, FONTS_PATH, ImageFont
import re, os.path, os
from pypinyin import lazy_pinyin
import mysql.connector
from pymysql.converters import escape_string
from fuzzywuzzy import process as fuzzy_process
from threading import Semaphore
import json, datetime, time
import requests

def createFaqTable(tableName: str):
    # warning: tableName may danger
    if not isinstance(tableName, str):
        tableName = str(tableName)
    mydb = mysql.connector.connect(charset='utf8mb4',**sqlConfig)
    mydb.autocommit = True
    mycursor = mydb.cursor()
    mycursor.execute("""
    create table if not exists `BOT_FAQ_DATA`.`%s` (
        `faq_seq` bigint unsigned not null auto_increment,
        `question` varchar(100) not null,
        `latest` bool not null default true,
        `answer` varchar(4000) not null,
        `modify_user_id` bigint not null,
        `modify_time` timestamp not null,
        `group_tag` varchar(100) not null default '',
        `deleted` bool not null default false,
        primary key (`faq_seq`),
        index(`question`, `latest`, `deleted`),
        index(`group_tag`, `latest`, `deleted`)
    )charset=utf8mb4, collate=utf8mb4_unicode_ci;
    """%(
        escape_string(tableName)
    ))

def createFaqDb():
    mydb = mysql.connector.connect(charset='utf8mb4',**sqlConfig)
    mydb.autocommit = True
    mycursor = mydb.cursor()
    mycursor.execute("create database if not exists `BOT_FAQ_DATA`")
    createFaqTable("globalFaq")
class HelpFAQ(StandardPlugin):
    initGuard = Semaphore()
    def __init__(self):
        if self.initGuard.acquire(blocking=False):
            createFaqDb()
            for groupId in APPLY_GROUP_ID:
                createFaqTable(str(groupId))
    def judgeTrigger(self, msg:str, data:Any) -> bool:
        return msg == '问答帮助' and data['message_type']=='group'
    def executeEvent(self, msg: str, data: Any) -> Union[None, str]:
        group_id = data['group_id']
        picPath = draw_help_pic(group_id)
        picPath = picPath if os.path.isabs(picPath) else os.path.join(ROOT_PATH, picPath)
        send(group_id, '[CQ:image,file=file:///%s]'%picPath)
        return "OK"
    def getPluginInfo(self)->Any:
        return {
            'name': 'AskFAQ',
            'description': '问答帮助',
            'commandDescription': '问答帮助',
            'usePlace': ['group', ],
            'showInHelp': True,
            'pluginConfigTableNames': [],
            'version': '1.0.4',
            'author': 'Unicorn',
        }
def get_answer(group_id: int, key: str)->Tuple[bool, str, str]:
    """获取问题答案
    @group_id: 群号
    @key:      问题

    @return:(
        bool: 是否存在问题
        str:  该问题的回答
        str:  该问题的tag
    )
    """
    mydb = mysql.connector.connect(charset='utf8mb4',**sqlConfig)
    mycursor = mydb.cursor()
    mycursor.execute("""
    select `answer`, `group_tag` from `BOT_FAQ_DATA`.`%d` where 
        `question` = '%s' and
        `latest` = true and
        `deleted` = false
    """%(
        group_id, 
        escape_string(key),
    ))
    answer = list(mycursor)
    if len(answer) == 0:
        return False, '', ''
    else:
        return True, answer[0][0], answer[0][1]
def rollback_answer(group_id:int, question:str)->bool:
    """问题回滚
    @group_id: 群号
    @question: 问题

    @return: bool: 是否回滚成功
    """
    mydb = mysql.connector.connect(charset='utf8mb4',**sqlConfig)
    mydb.autocommit = True
    mycursor = mydb.cursor()
    try:
        mycursor.execute("""
        select max(`faq_seq`) from `BOT_FAQ_DATA`.`%d` where question = '%s'
        """%(group_id, escape_string(question)))
        faq_seq = list(mycursor)[0][0]
        if faq_seq == None:
            return False
        else:
            mycursor.execute("""
            delete from `BOT_FAQ_DATA`.`%d` where `faq_seq` = %d
            """%(group_id, faq_seq))
            mycursor.execute("""
            update `BOT_FAQ_DATA`.`%d` set `latest` = true where
            `faq_seq` = (
                select * from (
                    select max(`faq_seq`) from `BOT_FAQ_DATA`.`%d`
                    where question = '%s'
                )a
            )
            """%(group_id, group_id, escape_string(question)))
    except mysql.connector.Error as e:
        warning('mysql error in faq rollback_answer: {}'.format(e))
        return False
    except KeyError as e:
        warning("key error in faq rollback_answer: {}".format(e))
        return False
    except BaseException as e:
        warning("exception in faq rollback_answer: {}".format(e))
        return False
    return True
def update_answer(group_id:int, question:str, answer:str, data:Any, tag:str = '',delete:bool= False)->bool:
    """更新回答，包括增加原本不存在的key
    @group_id: 群号
    @question: 问题
    @answer:   回答
    @data:     go-cqhttp的data
    @tag:      问题的tag
    @deleted:  问题是否被删除

    @return:   是否更新成功
    """
    mydb = mysql.connector.connect(charset='utf8mb4',**sqlConfig)
    mydb.autocommit = True
    mycursor = mydb.cursor()
    try:
        mycursor.execute("""
        update `BOT_FAQ_DATA`.`%d` 
        set
            `latest` = false
        where
            `question` = '%s' and
            `latest` = true
        """%(
            group_id,
            escape_string(question)
        ))
        mycursor.execute("""
        insert into `BOT_FAQ_DATA`.`%d` (
            `question`, `answer`, `modify_user_id`, `modify_time`, `deleted`, `group_tag`
        ) values (
            '%s', '%s', %d, from_unixtime(%d), %s, '%s'
        )"""%(
            data['group_id'],
            escape_string(question),
            escape_string(answer),
            data['user_id'],
            data['time'],
            'true' if delete else 'false',
            escape_string(tag)
        ))
    except mysql.connector.Error as e:
        warning('mysql error in faq update_answer: {}'.format(e))
        return False
    except KeyError as e:
        warning("key error in faq update_answer: {}".format(e))
        return False
    except BaseException as e:
        warning("exception in faq update_answer: {}".format(e))
        return False
    return True
def get_questions(group_id:int)->List[str]:
    mydb = mysql.connector.connect(charset='utf8mb4',**sqlConfig)
    mycursor = mydb.cursor()
    mycursor.execute("""select `question` from `BOT_FAQ_DATA`.`%d`
    where latest = true and deleted = false
    """%group_id)
    questions = [q[0] for q in list(mycursor)]
    return questions
def get_alldata(group_id:int)->List[Tuple[str, str, str]]:
    """@return: [key, value, tag]"""
    mydb = mysql.connector.connect(charset='utf8mb4',**sqlConfig)
    mycursor = mydb.cursor()
    mycursor.execute("""select `question`, `answer`, `group_tag` from `BOT_FAQ_DATA`.`%d`
    where latest = true and deleted = false
    """%group_id)
    return list(mycursor)
class AskFAQ(StandardPlugin):
    def __init__(self):
        self.pattern = re.compile(r'^(问|q)\s+(\S+)$')
    def judgeTrigger(self, msg:str, data:Any) -> bool:
        return self.pattern.match(msg) != None and data['message_type']=='group'
    def executeEvent(self, msg:str, data:Any) -> Union[None, str]:
        question = self.pattern.findall(msg)[0][1]
        group_id = data['group_id']
        hasMsg, ans, tag = get_answer(group_id, question)
        if hasMsg:
            ans = "[CQ:reply,id=%d]%s\n【%s】"%(data['message_id'], ans, question)
        else:
            questions = get_questions(group_id)
            fuzzy_ans = [fza[0] for fza in sorted(fuzzy_process.extract(question, questions, limit=5), key=lambda x:x[1], reverse=True) if fza[1]>30]
            if msg.startswith('q'):
                ans = "[CQ:reply,id=%d]未查询到信息，输入faq ls查看问题列表"%(data['message_id'])
                if len(fuzzy_ans)>0:
                    ans += "，猜你可能想问： {}".format('、'.join(fuzzy_ans))
            else:
                if len(fuzzy_ans) == 0:
                    ans = "[CQ:reply,id=%d]未查询到信息，输入faq ls查看问题列表"%(data['message_id'])
                else:
                    question = fuzzy_ans[0]
                    hasMsg, ans, tag = get_answer(group_id, question)
                    if hasMsg:
                        ans = "[CQ:reply,id=%d]%s\n【%s】"%(data['message_id'], ans, question)
                    else:
                        ans = "[CQ:reply,id=%d]未查询到信息，输入faq ls查看问题列表"%(data['message_id'])
        send(group_id, ans)

    def getPluginInfo(self)->Any:
        return {
            'name': 'AskFAQ',
            'description': '问答库',
            'commandDescription': '问 [...]',
            'usePlace': ['group', ],
            'showInHelp': True,
            'pluginConfigTableNames': [],
            'version': '1.0.4',
            'author': 'Unicorn',
        }
class MaintainFAQ(StandardPlugin):
    def __init__(self):
        self.findModPattern = re.compile(r"^\-?faq\s+(\S+)\s*(.*)$", re.DOTALL)
        self.modMap = {
            'show': MaintainFAQ.faqShow,
            'ls': MaintainFAQ.faqShow,
            'new': MaintainFAQ.faqAdd,
            'add': MaintainFAQ.faqAdd,
            'edit': MaintainFAQ.faqEdit,
            'cp': MaintainFAQ.faqCp,
            'del': MaintainFAQ.faqDel,
            'append': MaintainFAQ.faqAppend,
            'tag': MaintainFAQ.faqTag,
            'rollback': MaintainFAQ.faqRollBack,
            'history': MaintainFAQ.faqHistory,
            'export': MaintainFAQ.faqExport,
            'import': MaintainFAQ.faqImport,
            'help': MaintainFAQ.faqHelp,
        }
    def judgeTrigger(self, msg:str, data:Any) -> bool:
        return self.findModPattern.match(msg) != None and data['message_type']=='group'
    def executeEvent(self, msg:str, data:Any) -> Union[None, str]:
        mod, cmd = self.findModPattern.findall(msg)[0]
        if mod in self.modMap.keys():
            self.modMap[mod](cmd, data)
        else:
            send(data['group_id'], '输入格式不对哦，请输入【问答帮助】获取操作指南')
        return "OK"
    def onStateChange(self, nextState: bool, data: Any) -> None:
        if nextState == True: 
            groupId = data['group_id']
            createFaqTable(str(groupId))
    def getPluginInfo(self)->Any:
        return {
            'name': 'MaintainFAQ',
            'description': '维护问答库',
            'commandDescription': 'faq <mod> [...]',
            'usePlace': ['group', ],
            'showInHelp': True,
            'pluginConfigTableNames': [],
            'version': '1.0.4',
            'author': 'Unicorn',
        }
    @staticmethod
    def faqShow(cmd: str, data):
        mydb = mysql.connector.connect(charset='utf8mb4',**sqlConfig)
        mydb.autocommit = True
        mycursor = mydb.cursor()
        groupId = data['group_id']
        if cmd == '':
            mycursor.execute("""select `question` from `BOT_FAQ_DATA`.`%d`
            where latest = true and deleted = false
            """%groupId)
            questions = [q[0] for q in list(mycursor)]
            send(groupId, '问题列表：\n{}'.format('、'.join(questions)))
        elif cmd == '-1':
            mycursor.execute("""select `question` from `BOT_FAQ_DATA`.`%d`
            where latest = true and deleted = false
            """%groupId)
            questions = [q[0] for q in list(mycursor)]
            picPath = drawQuestionCardByPinyin(questions, groupId)
            picPath = picPath if os.path.isabs(picPath) else os.path.join(ROOT_PATH, picPath)
            send(groupId, '[CQ:image,file=file:///%s]'%picPath)
        elif cmd == '-2':
            mycursor.execute("""select `group_tag`, `question` from `BOT_FAQ_DATA`.`%d`
            where latest = true and deleted = false
            """%groupId)
            questions: Dict[str, List[str]] = {}
            for tag, q in list(mycursor):
                if tag not in questions.keys():
                    questions[tag] = [q]
                else:
                    questions[tag].append(q)
            picPath = drawQuestionCardByTag(questions, groupId)
            picPath = picPath if os.path.isabs(picPath) else os.path.join(ROOT_PATH, picPath)
            send(groupId, '[CQ:image,file=file:///%s]'%picPath)
        else:
            send(groupId, "语法有误，支持语句为: faq show(/ -1/ -2)")
        
    @staticmethod
    def faqAdd(cmd: str, data):
        pattern = re.compile(r'^(\S+)\s*(.*)$', re.DOTALL)
        qa = pattern.findall(cmd)
        groupId = data['group_id']
        if len(qa) == 0:
            send(groupId, '语法有误，支持语句为: faq (new/add) <key> (<ans>)')
        else:
            question, answer = qa[0]
            status, _, _ = get_answer(groupId, question)
            if status:
                send(groupId, '[CQ:reply,id=%d]问题【%s】已经存在，请输入faq edit <key> <new value>进行更改'%(data['message_id'], question))
            else:
                status = update_answer(groupId, question, answer, data)
                if status:
                    send(groupId, "[CQ:reply,id=%d]%s\n【%s】"%(data['message_id'], answer, question))
                else:
                    send(groupId, '[CQ:reply,id=%d]更新失败'%data['message_id'])
            
    @staticmethod
    def faqEdit(cmd: str, data):
        pattern = re.compile(r'^(\S+)\s*(.*)$', re.DOTALL)
        qa = pattern.findall(cmd)
        groupId = data['group_id']
        if len(qa) == 0:
            send(groupId, '语法有误，支持语句为: faq edit <key> <ans>')
        else:
            question, answer = qa[0]
            status, _, tag = get_answer(groupId, question)
            if not status:
                send(groupId, '[CQ:reply,id=%d]问题不存在，请先使用"faq add"语句创建该问题'%data['message_id'])
            else:
                status = update_answer(groupId, question, answer, data, tag=tag)
                if status:
                    send(groupId, "[CQ:reply,id=%d]%s\n【%s】"%(data['message_id'], answer, question))
                else:
                    send(groupId, '[CQ:reply,id=%d]更新失败，数据库错误'%data['message_id'])
    @staticmethod
    def faqCp(cmd: str, data):
        pattern = re.compile(r'^(\S+)\s+(\S+)$')
        qa = pattern.findall(cmd)
        groupId = data['group_id']
        if len(qa) == 0:
            send(groupId, '语法有误，支持语句为: faq cp <name> <new name>')
        else:
            prevName, newName = qa[0]
            status, answer, tag = get_answer(groupId, prevName)
            if not status:
                send(groupId,"[CQ:reply,id=%d]【%s】问题不存在，请输入faq ls查看问题列表"%(data['message_id'], prevName))
            else:
                status = update_answer(groupId, newName, answer, data, tag=tag)
                if status:
                    send(groupId, "[CQ:reply,id=%d]%s\n【%s】"%(data['message_id'], answer, newName))
                else:
                    send(groupId, '[CQ:reply,id=%d]问题复制失败，数据库错误'%data['message_id'])
    @staticmethod
    def faqDel(cmd: str, data):
        pattern = re.compile(r'^(\S+)\s*$')
        question = pattern.findall(cmd)
        groupId = data['group_id']
        if len(question) == 0:
            send(groupId, '语法有误，支持语句为: faq del <key>')
        else:
            question = question[0]
            print(question)
            status, _, tag = get_answer(groupId, question)
            if not status:
                send(groupId, "[CQ:reply,id=%d]问题不存在，请输入faq ls查看问题列表"%(data['message_id']))
            else:
                status = update_answer(groupId, question, '', data, delete=True, tag=tag)
                if status:
                    send(groupId, "[CQ:reply,id=%d]问题删除成功"%(data['message_id']))
                else:
                    send(groupId, "[CQ:reply,id=%d]问题删除失败，数据库错误"%(data['message_id']))
    @staticmethod
    def faqAppend(cmd: str, data):
        pattern = re.compile(r'^(\S+)\s(.*)$', re.DOTALL)
        qa = pattern.findall(cmd)
        groupId = data['group_id']
        if len(qa) == 0:
            send(groupId, '语法有误，支持语句为: faq append <key> <ans to append>')
        else:
            question, answer = qa[0]
            status, prevAns, tag = get_answer(groupId, question)
            if not status:
                send(groupId,"[CQ:reply,id=%d]【%s】问题不存在"%(data['message_id'], question))
            else:
                answer = prevAns + answer
                status = update_answer(groupId, question, answer, data, tag=tag)
                if status:
                    send(groupId, "[CQ:reply,id=%d]%s\n【%s】"%(data['message_id'], answer, question))
                else:
                    send(groupId, '[CQ:reply,id=%d]更新失败，数据库错误'%data['message_id'])
    @staticmethod
    def faqTag(cmd: str, data):
        pattern = re.compile(r'^(\S+)\s+(\S+)$')
        qa = pattern.findall(cmd)
        groupId = data['group_id']
        if len(qa) == 0:
            send(groupId, '语法有误，支持语句为: faq tag <key> <tag>')
        else:
            question, tag = qa[0]
            status, answer, _ = get_answer(groupId, question)
            if not status:
                send(groupId,"[CQ:reply,id=%d]【%s】问题不存在，请输入faq ls查看问题列表"%(data['message_id'], question))
            else:
                status = update_answer(groupId, question, answer, data, tag=tag)
                if status:
                    send(groupId, "[CQ:reply,id=%d]OK"%(data['message_id']))
                else:
                    send(groupId, '[CQ:reply,id=%d]更新失败，数据库错误'%data['message_id'])
    @staticmethod
    def faqRollBack(cmd: str, data):
        groupId = data['group_id']
        pattern = re.compile(r'^(\S+)$')
        question = pattern.findall(cmd)
        if len(question) == 0:
            send(groupId, '语法有误，支持语句为: faq rollback <key>')
        else:
            if data['user_id'] not in getGroupAdmins(groupId):
                send(groupId, '[CQ:reply,id=%d]您没有回滚记录权限'%(data['message_id']))
            else:
                question = question[0]
                status = rollback_answer(groupId, question)
                if status:
                    send(groupId, '[CQ:reply,id=%d]OK'%data['message_id'])
                else:
                    send(groupId, '[CQ:reply,id=%d]记录【%s】不存在，请输入faq ls查看问题列表'%(data['message_id'], question))
    @staticmethod
    def faqHistory(cmd: str, data):
        groupId = data['group_id']
        pattern = re.compile(r'^(\S+)$')
        question = pattern.findall(cmd)
        if len(question) == 0:
            send(groupId, '语法有误，支持语句为: faq history <key>')
        else:
            if data['user_id'] not in getGroupAdmins(groupId):
                send(groupId, '[CQ:reply,id=%d]您没有查看记录权限，输入faq help获取问答帮助'%(data['message_id']))
            else:
                question = question[0]
                picPath = draw_answer_history(groupId, question)
                picPath = picPath if os.path.isabs(picPath) else os.path.join(ROOT_PATH, picPath)
                send(groupId, '[CQ:image,file=file:///%s]'%picPath)
    @staticmethod
    def faqExport(cmd: str, data):
        groupId = data['group_id']
        if data['user_id'] not in getGroupAdmins(groupId):
            send(groupId, '[CQ:reply,id=%d]您没有导出权限'%(data['message_id']))
        else:
            faqData = get_alldata(groupId)
            faqData = [{'question': x[0], 'answer': x[1], 'tag': x[2]} for x in faqData]
            filePath = os.path.join(ROOT_PATH, SAVE_TMP_PATH, 'faqdata-%d.json'%groupId)
            with open(filePath, 'w') as f:
                json.dump(faqData, f, ensure_ascii=False)
            upload_group_file(groupId, filePath, datetime.datetime.now().strftime('LUBFAQ-%y%m%d.json'), '')
    @staticmethod
    def faqImport(cmd: str, data):
        groupId = data['group_id']
        if data['user_id'] not in getGroupAdmins(groupId):
            send(groupId, '[CQ:reply,id=%d]您没有导入权限'%(data['message_id']))
        else:
            fileNamePattern = re.compile(r'^LUBFAQ.*\.json$', re.DOTALL)
            rootFiles = get_group_root_files(groupId)['files']
            targetFiles = [f for f in rootFiles if fileNamePattern.match(f['file_name']) != None]
            if len(targetFiles) == 0:
                send(groupId, '[CQ:reply,id=%d]群文件根目录下没有找到任何名为LUBFAQ**.json的文件'%(data['message_id']))
                return 
            targetFile = max(targetFiles, key=lambda f:f['upload_time'])
            if targetFile['file_size'] > 10 * 1024 * 1024:
                send(groupId, '[CQ:reply,id=%d]目标文件 %s 超过10M，暂不支持'%(data['message_id'], targetFile['file_name']))
                return
            fileUrl = get_group_file_url(targetFile['group_id'], targetFile['file_id'], targetFile['busid'])
            if fileUrl == None:
                send(groupId, '[CQ:reply,id=%d]文件URL获取失败'%(data['message_id'], ))
                return 
            try:
                faqData:List[Dict[str, str]] = requests.get(fileUrl).json()
                if not isinstance(faqData, list):
                    send(groupId, '[CQ:reply,id=%d]faq内容解析失败'%(data['message_id']))
                    return
                prevKeys = get_questions(groupId)
                conflictKeys:List[str] = []
                validQAT:List[Tuple[str, str, str]] = []
                for faq in faqData:
                    if 'question' not in faq.keys() or 'answer' not in faq.keys() or 'tag' not in faq.keys():
                        send(groupId, '[CQ:reply,id=%d]faq内容解析失败'%(data['message_id']))
                        return
                    elif faq['question'] in prevKeys:
                        conflictKeys.append(faq['question'])
                    else:
                        validQAT.append((faq['question'], faq['answer'], faq['tag']))
                if len(conflictKeys) != 0:
                    send(groupId, '[CQ:reply,id=%d]检测到key冲突，冲突key为：\n%s\n\n请手动添加这些key'%(data['message_id'], '、'.join(conflictKeys)))
                failedKeys:List[str] = []
                for question, answer, tag in validQAT:
                    succ = update_answer(groupId, question, answer, data, tag=tag)
                    if not succ:
                        failedKeys.append(question)
                if len(failedKeys) != 0:
                    send(groupId, '[CQ:reply,id=%d]识别到faq文件%s，由用户 %s(%d) 上传于%s。由于数据库错误，下面的问题添加失败：\n%s\n\n，其余问题添加成功（成功添加%d个问题）'%(
                        data['message_id'], targetFile['file_name'], targetFile['uploader_name'],targetFile['uploader'],
                        time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(targetFile['upload_time'])),'、'.join(failedKeys),
                        len(validQAT) - len(failedKeys)))
                else:
                    send(groupId, '[CQ:reply,id=%d]识别到faq文件%s，由用户 %s(%d) 上传于%s。成功添加%d个问题。'%(
                        data['message_id'], targetFile['file_name'], targetFile['uploader_name'],targetFile['uploader'],
                        time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(targetFile['upload_time'])),
                        len(validQAT)))
            except requests.exceptions.JSONDecodeError as e:
                send(groupId, '[CQ:reply,id=%d]json格式解析失败'%(data['message_id']))
                return
            except BaseException as e:
                print(e)
                send(groupId, '[CQ:reply,id=%d]文件下载失败'%(data['message_id']))
                return
    @staticmethod
    def faqHelp(cmd: str, data):
        groupId = data['group_id']
        picPath = draw_help_pic(groupId)
        picPath = picPath if os.path.isabs(picPath) else os.path.join(ROOT_PATH, picPath)
        send(groupId, '[CQ:image,file=file:///%s]'%picPath)

def drawQuestionCardByPinyin(questions: List[str], group_id: int)->str:
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
        title = 'FAQ 问题列表', 
        titleColor = PALETTE_CYAN,
        layout = 'two-column',
        width = 1280,
        cardBodyFont= ImageFont.truetype(os.path.join(FONTS_PATH, 'SourceHanSansCN-Medium.otf'), 24),
        footer='群号 %d'%group_id
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
def drawQuestionCardByTag(questions:Dict[str, List[str]], group_id: int)->str:
    """根据tag来归类问题并且画图
    @questions: {
        'tag0': [question00, question01, ...],
        'tag1': [question10, question11, ...],
    }
    @group_id:  群号

    @return:    画出来的图的存储位置
    """
    helpCards = ResponseImage(
        title = 'FAQ 问题列表', 
        titleColor = PALETTE_CYAN,
        layout = 'two-column',
        width = 1280,
        cardBodyFont= ImageFont.truetype(os.path.join(FONTS_PATH, 'SourceHanSansCN-Medium.otf'), 24),
        footer='群号 %d'%group_id,
    )
    for tag, qs in questions.items():
        cardList = []
        cardList.append(('title', tag))
        cardList.append(('separator', ))
        cardList.append(('body', "、".join(qs)))
        helpCards.addCard(ResponseImage.RichContentCard(
            raw_content=cardList, titleFontColor=PALETTE_CYAN))
    savePath = os.path.join(ROOT_PATH, SAVE_TMP_PATH, '%d-faq.png'%group_id)
    helpCards.generateImage(savePath)
    return savePath
def draw_answer_history(group_id:int, question:str)->str:
    """绘制问题编辑历史
    @group_id: 群号
    @question: 问题

    @return:   问题编辑历史图片的保存位置（绝对路径）
    """
    mydb = mysql.connector.connect(charset='utf8mb4',**sqlConfig)
    mydb.autocommit = True
    mycursor = mydb.cursor()
    try:
        mycursor.execute("""select
        `faq_seq`, `question`, `answer`, `latest`, `deleted`, `modify_user_id`, `modify_time`, `group_tag`
        from `BOT_FAQ_DATA`.`%d` where `question` = '%s'
        order by `faq_seq` desc limit 20
        """%(group_id, escape_string(question)))
    except mysql.connector.Error as e:
        warning('mysql error in faq get_answer_history: {}'.format(e))
        return []
    except KeyError as e:
        warning("key error in faq get_answer_history: {}".format(e))
        return []
    except BaseException as e:
        warning("exception in faq get_answer_history: {}".format(e))
        return []
    helpCards = ResponseImage(
        title = 'FAQ 【%s】 历史记录'%question, 
        titleColor = PALETTE_CYAN,
        width = 1000,
        cardBodyFont= ImageFont.truetype(os.path.join(FONTS_PATH, 'SourceHanSansCN-Medium.otf'), 24),
        footer= '群号 %d'%group_id,
    )
    results = list(mycursor)
    for faq_seq, question, answer, latest, deleted, modify_user_id, modify_time, group_tag in results:
        cardList = []
        title = 'faq_seq = %d'% faq_seq
        if deleted:
            title += '  [DELETED]'
        if latest:
            title += '  [LATEST]'
        cardList.append(('title', title))

        cardList.append(('subtitle', '%s by %d'%(modify_time, modify_user_id)))
        cardList.append(('keyword', group_tag))
        cardList.append(('body', answer))
        helpCards.addCard(ResponseImage.RichContentCard(
            raw_content=cardList,
            titleFontColor=PALETTE_RED if deleted else PALETTE_CYAN,
        ))
    if len(results) == 0:
        helpCards.addCard(ResponseImage.NoticeCard(
            title='暂无历史记录'
        ))
    savePath = os.path.join(ROOT_PATH, SAVE_TMP_PATH, '%d-faq-history.png'%(group_id, ))
    helpCards.generateImage(savePath)
    return savePath
def draw_help_pic(group_id:int)->str:
    """绘制faq帮助
    @group_id:  群号
    @return:    图片存储路径（绝对路径）
    """
    helpWords = (
        "查询关键字： 'q <key>'(精确查询) / '问 <key>'(模糊查询)\n"
        "问题列表（纯文字）： 'faq (show|ls)'\n"
        "问题列表按拼音排序： 'faq (show|ls) -1'\n"
        "问题列表按tag排序： 'faq (show|ls) -2'\n"
        "新建问题： 'faq (new|add) <key> (<original ans>)'\n"
        "更改答案： 'faq edit <key> <new ans>'\n"
        "复制问题： 'faq cp <key> <new key>'\n"
        "删除问题： 'faq del <key>'\n"
        "附加答案： 'faq append <key> <ans to append>'\n"
        "标记分组： 'faq tag <key> <tag>'\n"
        "回滚[🔑]： 'faq rollback <key>'\n"
        "查看记录[🔑]： 'faq history <key>'\n"
        "导出库[🔑]： 'faq export'\n"
        "导入库[🔑]： 'faq import'\n"
        "获取帮助： 'faq help' / '问答帮助'\n\n"
        "【注】：\n"
        "1. 导入库会从群文件根目录下搜索名称为“LUBFAQ**.json”的文件（注意，并非子目录），找到最近一次的进行导入，文件格式见faq export的格式"
    )
    helpCards = ResponseImage(
        title = 'FAQ 帮助', 
        titleColor = PALETTE_CYAN,
        width = 1000,
        cardBodyFont= ImageFont.truetype(os.path.join(FONTS_PATH, 'SourceHanSansCN-Medium.otf'), 24),
        footer='群号 %d'%group_id
    )
    cardList = []
    cardList.append(('body', helpWords))
    helpCards.addCard(ResponseImage.RichContentCard(
        raw_content=cardList,
        titleFontColor=PALETTE_CYAN,
    ))
    savePath = os.path.join(ROOT_PATH, SAVE_TMP_PATH, '%d-faq-helper.png'%(group_id, ))
    helpCards.generateImage(savePath)
    return savePath