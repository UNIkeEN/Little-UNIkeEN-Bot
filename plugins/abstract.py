from typing import Any, Union, Dict, List, Tuple, Optional
from utils.standardPlugin import StandardPlugin
from utils.basicEvent import send, warning
from utils.basicConfigs import ROOT_PATH
import re, os, json
import jieba, pinyin
ABSTRACT_RESOURCE_PATH = 'resources/emoji'
with open(os.path.join(ROOT_PATH, ABSTRACT_RESOURCE_PATH, 'character2emoji.json'), 'r', encoding='utf-8') as f:
    emoji = json.load(f)
with open(os.path.join(ROOT_PATH, ABSTRACT_RESOURCE_PATH, 'pinyin2emoji.json'), 'r', encoding='utf-8') as f:
    emoji_py = json.load(f)
def text_to_emoji(text):
    try:
        text_with_emoji = ''
        text_jieba = jieba.cut(text, cut_all=False)
        for word in text_jieba:
            word = word.strip()
            # 分词检索
            if word in emoji.keys():
                text_with_emoji += emoji[word]
            elif word not in emoji.keys():
                word_py = pinyin.get(word, format="strip")
                # 分词拼音检索
                if word_py in emoji_py.keys():
                    text_with_emoji += emoji_py[word_py]
                else:
                    if len(word) > 0: # if the two characters or more
                        # 单字检索
                        for character in word:
                            if character in emoji.keys():
                                text_with_emoji += emoji[character]
                            else:
                                # 单字拼音检索
                                character_py = pinyin.get(character, format="strip")
                                if character_py in emoji_py.keys():
                                    text_with_emoji += emoji_py[character_py]
                                else:
                                    text_with_emoji += character
                    else: # 只有一个汉字，前面已经检测过字和拼音都不在抽象词典中，直接加词
                        text_with_emoji += word.strip()
    except Exception as e:
        warning('exception in abstract.text_to_emoji:{}'.format(e))
        return None
    return text_with_emoji

class MakeAbstract(StandardPlugin):
    def judgeTrigger(self, msg: str, data: Any) -> bool:
        return msg.startswith('-abstract') or msg.startswith('抽象')
    def executeEvent(self, msg: str, data: Any) -> Optional[str]:
        target = data['group_id'] if data['message_type']=='group' else data['user_id']
        if msg.startswith('抽象'):
            msg = msg[len('抽象'):].strip()
        elif msg.startswith('-abstract'):
            msg = msg[len('-abstract'):].strip()
        else:
            return None
        abstractMsg = text_to_emoji(msg)
        if abstractMsg == None:
            send(target, '[CQ:reply,id=%d]抽象文字生成失败QAQ'%(data['message_id']), data['message_type'])
        else:
            send(target, '[CQ:reply,id=%d]'%(data['message_id'])+abstractMsg, data['message_type'])
        return 'OK'
    def getPluginInfo(self) -> dict:
        return {
            'name': 'MakeAbstract',
            'description': '搞抽象',
            'commandDescription': '抽象 .../-abstract ...',
            'usePlace': ['group', 'private', ],
            'showInHelp': True,
            'pluginConfigTableNames': [],
            'version': '1.0.0',
            'author': 'Unicorn',
        }