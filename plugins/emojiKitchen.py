from typing import Any, Union, Dict, List, Tuple, Optional
from utils.basicEvent import send, warning
from utils.standardPlugin import StandardPlugin
import os, re, json
from utils.basicConfigs import ROOT_PATH, SAVE_TMP_PATH
EMOJIKITCHEN_SOURCE_PATH = 'resources/emoji/metadata.json'
class EmojiKitchen(StandardPlugin):
    def __init__(self) -> None:
        self.metadata:Dict[str, Any] = None
        self.knownSupportedEmoji:List[str] = None
        self.triggerPattern = re.compile(u'^-emoji\\s*([\U00010000-\U0010ffff])([\U00010000-\U0010ffff])')
        self.emojiDict = {}
        self.load_source()
    def emojiToCode(self, emoji:str)->Optional[str]:
        return self.emojiDict.get(emoji, None)
    def load_source(self)->None:
        with open(os.path.join(ROOT_PATH,EMOJIKITCHEN_SOURCE_PATH), 'r') as f:
            metadata = json.load(f)
            self.knownSupportedEmoji = metadata['knownSupportedEmoji']
            self.metadata = metadata['data']
        for leftCode, rightDict in self.metadata.items():
            self.emojiDict[rightDict['emoji']] = rightDict['emojiCodepoint']
            for emoji in rightDict["combinations"]:
                self.emojiDict[emoji['rightEmoji']] = emoji['rightEmojiCodepoint']
                self.emojiDict[emoji['leftEmoji']] = emoji['leftEmojiCodepoint']
            
    def queryEmoji(self, emoji1Code, emoji2Code)->Optional[str]:
        combinations = self.metadata.get(emoji1Code, {}).get("combinations", [])
        for emojiDict in combinations:
            if emojiDict["rightEmojiCodepoint"] == emoji2Code:
                return emojiDict["gStaticUrl"]
        return None
    def queryValidEmojis(self, emojiCode)->List[str]:
        combinations = self.metadata.get(emojiCode, {}).get("combinations", [])
        return [emoji['rightEmoji'] for emoji in combinations]
    def judgeTrigger(self, msg: str, data: Any) -> bool:
        return self.triggerPattern.match(msg) != None
    def executeEvent(self, msg: str, data: Any) -> Union[None, str]:
        target = data['group_id'] if data['message_type']=='group' else data['user_id']
        
        emoji1, emoji2 = self.triggerPattern.findall(msg)[0]
        emoji1Code = self.emojiToCode(emoji1)
        emoji2Code = self.emojiToCode(emoji2)
        if emoji1Code == None:
            send(target, '[CQ:reply,id=%d]不支持的emoji: %s'%(data['message_id'], emoji1, ),data['message_type'])
            return 'OK'
        if emoji2Code == None:
            send(target, '[CQ:reply,id=%d]不支持的emoji: %s'%(data['message_id'], emoji2, ),data['message_type'])
            return 'OK'
        emojiUrl = self.queryEmoji(emoji1Code, emoji2Code)
        if emojiUrl == None:
            emojiUrl = self.queryEmoji(emoji2Code, emoji1Code)
        if emojiUrl == None:
            validEmojis = self.queryValidEmojis(emoji1Code)
            send(target, '不支持的组合，%s仅可与 %s 组合'%(emoji1, ''.join(set(validEmojis))), data['message_type'])
            return 'OK'
        else:
            send(target, '[CQ:image,file=%s]'%emojiUrl, data['message_type'])
            return 'OK'
    def getPluginInfo(self, )->Any:
        return {
            'name': 'EmojiKitchen',
            'description': 'Emoji杂交',
            'commandDescription': '-emoji 😀😁',
            'usePlace': ['group', 'private'],
            'showInHelp': True,
            'pluginConfigTableNames': [],
            'version': '1.0.0',
            'author': 'Unicorn',
        }