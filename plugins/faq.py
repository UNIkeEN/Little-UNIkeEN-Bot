import json
from pathlib import Path
from typing import Union, Any
from utils.basicEvent import *
from utils.basicConfigs import *
from utils.standardPlugin import StandardPlugin

FAQ_DATA_PATH="data"

class AskFAQ(StandardPlugin): 
    def judgeTrigger(self, msg:str, data:Any) -> bool:
        return startswith_in(msg, ['问 '])
    def executeEvent(self, msg:str, data:Any) -> Union[None, str]:
        msg=msg.replace('问 ','',1)
        send(
            data['group_id'],
            f"[CQ:reply,id={str(data['message_id'])}]{get_answer(data['group_id'],msg.strip())} 【{msg.strip()}】"
        )
        return "OK"
    def getPluginInfo(self)->Any:
        return {
            'name': 'AskFAQ',
            'description': '问答库',
            'commandDescription': '问 [...]',
            'usePlace': ['group', ],
            'showInHelp': True,
            'pluginConfigTableNames': [],
            'version': '1.0.0',
            'author': 'Unicorn',
        }
class MaintainFAQ(StandardPlugin):
    def judgeTrigger(self, msg:str, data:Any) -> bool:
        return startswith_in(msg, ['维护 '])
    def executeEvent(self, msg:str, data:Any) -> Union[None, str]:
        send(data['group_id'], maintain(data,msg))
        return "OK"
    def getPluginInfo(self)->Any:
        return {
            'name': 'MaintainFAQ',
            'description': '维护问答库',
            'commandDescription': '维护 [...]',
            'usePlace': ['group', ],
            'showInHelp': True,
            'pluginConfigTableNames': [],
            'version': '1.0.0',
            'author': 'Unicorn',
        }
def get_answer(group_id,key):
    exact_path=(f'{FAQ_DATA_PATH}/{group_id}/faq.json')
    if not Path(exact_path).is_file():
        Path(exact_path).write_text(r'[]')
        return "没有查询到结果喔 qwq"
    else:
        with open(exact_path, "r") as f:
            faq_base = json.load(f)
        for record in faq_base:
            #print(record)
            if record["key"] == key:
                return record["ans"]
        return "没有查询到结果喔 qwq"
        
def add_question(group_id,key,ans):
    exact_path=(f'{FAQ_DATA_PATH}/{group_id}/faq.json')
    if not Path(exact_path).is_file():
        Path(exact_path).write_text(r'[]')
        faq_base=[{"key":key,"ans":ans}]
        with open(exact_path, 'w') as f:
            json.dump(faq_base, f, indent=4)
        return True
    else:
        with open(exact_path, "r") as f:
            faq_base = json.load(f)
        for record in faq_base:
            if record["key"] == key:
                return False
        faq_base.append({"key":key,"ans":ans})
        with open(exact_path, 'w') as f:
            json.dump(faq_base, f, indent=4)
        return True

def edit_question(group_id,key,ans):
    exact_path=(f'{FAQ_DATA_PATH}/{group_id}/faq.json')
    if not Path(exact_path).is_file():
        Path(exact_path).write_text(r'[]')
        return False
    else:
        with open(exact_path, "r") as f:
            faq_base = json.load(f)
        for record in faq_base:
            if record["key"] == key:
                record["ans"] = ans
                with open(exact_path, 'w') as f:
                    json.dump(faq_base, f, indent=4)
                return True
        return False

def del_question(group_id,key):
    exact_path=(f'{FAQ_DATA_PATH}/{group_id}/faq.json')
    if not Path(exact_path).is_file():
        Path(exact_path).write_text(r'[]')
        return False
    else:
        with open(exact_path, "r") as f:
            faq_base = json.load(f)
        for record in faq_base:
            if record["key"] == key:
                faq_base.remove(record)
                with open(exact_path, 'w') as f:
                    json.dump(faq_base, f, indent=4)
                return True
        return False

def show_all(group_id):
    exact_path=(f'{FAQ_DATA_PATH}/{group_id}/faq.json')
    if not Path(exact_path).is_file():
        Path(exact_path).write_text(r'[]')
        return "问题列表为空"
    else:
        key_list=""
        with open(exact_path, "r") as f:
            faq_base = json.load(f)
        for record in faq_base:
            key_list=key_list+record["key"]+"、"
        if key_list=="":
            return "问题列表为空"
        else:
            return "问题列表：\n"+key_list[:-1]

def maintain(data,msg):
    msg=msg.replace('维护 ','',1)
    msg_split=msg.split()
    print(msg_split)
    if msg_split[0]=='list':
        return show_all(data['group_id'])
    if msg_split[0]=='add':  # 增加新问题
        key=msg_split[1]
        msg=msg.replace('add ','',1)
        msg=msg.replace(key,'',1)
        ans=msg.strip()
        flag=add_question(data['group_id'],key,ans)
        if flag:
            return (f"[CQ:reply,id={str(data['message_id'])}]问题添加成功\n{ans} 【{key}】")
        else:
            return (f"[CQ:reply,id={str(data['message_id'])}]问题已存在，添加失败")
    if msg_split[0]=='edit':  # 修改已有问题
        key=msg_split[1]
        msg=msg.replace('edit ','',1)
        msg=msg.replace(key,'',1)
        ans=msg.strip()
        flag=edit_question(data['group_id'],key,ans)
        if flag:
            return (f"[CQ:reply,id={str(data['message_id'])}]问题修改成功\n{ans} 【{key}】")
        else:
            return (f"[CQ:reply,id={str(data['message_id'])}]问题不存在，请先添加")
    if msg_split[0]=='del':  # 删除已有问题
        key=msg_split[1]
        msg=msg.replace('del ','',1)
        msg=msg.replace(key,'',1)
        ans=msg.strip()
        flag=del_question(data['group_id'],key)
        if flag:
            return (f"[CQ:reply,id={str(data['message_id'])}]问题删除成功 【{key}】")
        else:
            return (f"[CQ:reply,id={str(data['message_id'])}]问题不存在")


    return "维护指令错误，输入[维护 help]查询正确格式"

