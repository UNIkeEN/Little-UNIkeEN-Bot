import json
import os
import random
import re
from enum import Enum
from functools import cache
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from PIL import Image, ImageDraw, ImageFont
from spellchecker import SpellChecker

from utils.accountOperation import get_user_coins, update_user_coins
from utils.basicConfigs import FONTS_PATH, ROOT_PATH, SAVE_TMP_PATH
from utils.basicEvent import send
from utils.responseImage_beta import PALETTE_CYAN, ResponseImage
from utils.sqlUtils import newSqlSession
from utils.standardPlugin import StandardPlugin

WORDLE_RESOURCE_PATH = 'resources/wordle'
DIFFICULTY_LIST = []

def createDifficultySql():
    mydb, mycursor = newSqlSession()
    mycursor.execute("""create table if not exists `wordleDifficulty` (
        `group_id` bigint unsigned not null,
        `difficulty` char(20),
        primary key (`group_id`)
    );""")

def loadDifficulty(group_id: int) -> Optional[str]:
    mydb, mycursor = newSqlSession()
    mycursor.execute("""select `difficulty` from `wordleDifficulty`
                     where `group_id` = %s
                     """, (group_id, ))
    result = list(mycursor)
    if len(result) == 0:
        return None
    return result[0][0]

def loadAllDifficulties() -> Dict[int, str]:
    mydb, mycursor = newSqlSession()
    mycursor.execute("""select `group_id`, `difficulty` from `wordleDifficulty`""")
    result = {} 
    for group_id, difficulty in list(mycursor):
        result[group_id] = difficulty
    return result

def writeDifficulty(group_id: int, difficulty: str)->None:
    mydb, mycursor = newSqlSession()
    mycursor.execute("""replace into `wordleDifficulty` (`group_id`, `difficulty`)
                     values (%s, %s)
                     """, (group_id, difficulty))

def drawHelpPic(savePath:str):
    helpWords = (
        "输入“猜单词”或者“-wordle”开始游戏：\n"
         "可用“猜单词 n”“-wordle n”指定单词长度，长度应在3到12之间\n"
        "答案为指定长度单词，发送对应长度单词即可；\n"
        "绿色块代表此单词中有此字母且位置正确；\n"
        "黄色块代表此单词中有此字母，但该字母所处位置不对；\n"
        "灰色块代表此单词中没有此字母；\n"
        "猜出单词或用光次数则游戏结束；\n"
        "发送“结束”结束游戏；发送“单词提示”查看提示；\n"
        "发送“猜单词难度 <难度>”可以改变难度设定，<难度>默认为CET4，可使用的其他难度有：\n"
        f"{'、'.join(DIFFICULTY_LIST)}\n\n"
        "游戏发起者在开始游戏时需缴30 coins，其中25 coins作为押金，5 coins为胜利者奖金。"
        "游戏胜利时，猜对的用户获得系统和发起者提供的总共15 coins奖励，"
        "同时押金退还至游戏发起者。游戏过程中每提示一次，押金和提示者各扣除5 coins，"
        "押金等于0时仍可提示，不会使之变成负数。\n"
        "游戏失败不退coins。"
    )
    helpCards = ResponseImage(
        title = '猜单词帮助', 
        titleColor = PALETTE_CYAN,
        width = 1000,
        cardBodyFont= ImageFont.truetype(os.path.join(FONTS_PATH, 'SourceHanSansCN-Medium.otf'), 24),
    )
    cardList = []
    cardList.append(('body', helpWords))
    helpCards.addCard(ResponseImage.RichContentCard(
        raw_content=cardList,
        titleFontColor=PALETTE_CYAN,
    ))
    helpCards.generateImage(savePath)

class Wordle(StandardPlugin):
    def __init__(self) -> None:
        createDifficultySql()
        self.wordPattern = re.compile(r'^[a-zA-Z]{3,12}$')
        self.difficultyPattern = re.compile(r'^猜?单词难度\s*(\S*)$')
        self.startWordsPattern = re.compile(r"^(?:猜单词|-wordle)\s*(\d*)$")
        self.hintWords = ['单词提示', '猜单词提示', '提示']
        self.stopWords = ['结束']
        
        self.games:Dict[int,Optional[WordleGame]] = {}
        self.difficulties:Dict[int,str] = loadAllDifficulties()
        self.difficultyList = []
        # words[难度][单词长度] -> [单词, 解释]
        self.words:Dict[str,Dict[int,Tuple[str,str]]] = {}
        self.deposit:Dict[int, Optional[int]] = {}
        self.initiator:Dict[int, int] = {}
        self.load_words()
        global DIFFICULTY_LIST
        DIFFICULTY_LIST = self.difficultyList
        
    def load_words(self):
        wordleResourcePath = os.path.join(ROOT_PATH, WORDLE_RESOURCE_PATH)
        for wordleResourceName in os.listdir(wordleResourcePath):
            difficulty, suffix = os.path.splitext(wordleResourceName)
            if suffix != '.json': continue
            self.difficultyList.append(difficulty)
            with open(os.path.join(wordleResourcePath, wordleResourceName),'r', encoding='utf-8') as f:
                lenDict = {l:[] for l in range(3, 13)}
                for word, interpretation in json.load(f).items():
                    l = len(word)
                    if l < 3 or l >= 13: continue
                    lenDict[l].append((word, interpretation['中释']))
                self.words[difficulty] = lenDict
    
    @staticmethod
    def randomLen():
        r = random.randint(0, 99)
        if r < 5: return 3
        elif r < 20: return 4
        elif r < 60: return 5
        elif r < 80: return 6
        elif r < 95: return 7
        else: return 8
        
    def randomSelectWord(self, difficulty:str,l:int=0)->Optional[Tuple[str, str]]:
        # 长度  概率    CDF
        # 3     5%     5%
        # 4     15%    20%
        # 5     40%    60%
        # 6     20%    80%
        # 7     15%    95%
        # 8     5%     100%
        if l==0:
            l = self.randomLen()
        wordList = self.words.get(difficulty,{}).get(l,[])
        if len(wordList) == 0: return None
        return random.choice(wordList)

    def judgeTrigger(self, msg: str, data: Any) -> bool:
        return (
            (self.startWordsPattern.match(msg) != None) or 
            (msg in self.hintWords) or
            (msg in self.stopWords) or
            (self.wordPattern.match(msg) != None) or 
            (self.difficultyPattern.match(msg) != None) 
        )
        
    def executeEvent(self, msg: str, data: Any) -> Union[str, None]:
        groupId = data['group_id']
        userId = data['user_id']
        savePath = os.path.join(ROOT_PATH, SAVE_TMP_PATH, 'wordle-%d.png'%groupId)
        if self.startWordsPattern.match(msg) != None:
            game = self.games.get(groupId)
            if game != None:
                game:WordleGame
                game.draw(savePath)
                send(groupId, '当前有正在进行的猜单词游戏\n[CQ:image,file=file:///%s]'%savePath)
            else:
                l=self.startWordsPattern.findall(msg)[0]
                if len(l)==0:
                    l=0
                else:
                    l=int(l)#l用(\d*)获取，应该不会报错
                    if (l<3 or l>=13):
                        send(groupId,"[CQ:reply,id={message_id}]单词长度应在3到12之间".format(message_id=data["message_id"]))
                        return 'OK'
                difficulty = self.difficulties.get(groupId, 'CET4')
                wordResult = self.randomSelectWord(difficulty,l)
                if wordResult == None:
                    send(groupId, '[CQ:reply,id=%d]内部错误，请输入“猜单词难度 CET4”重置难度信息'%data['message_id'])
                elif get_user_coins(userId, format=False) < 30*100:
                    send(groupId, 'coins不足30，无法发起游戏')
                else:
                    update_user_coins(userId, -30*100, '猜单词押金', format=False)
                    self.deposit[groupId] = 25*100
                    self.initiator[groupId] = userId
                    game = self.games[groupId] = WordleGame(wordResult[0], wordResult[1])
                    game.draw(savePath)
                    send(groupId, '你有%d次机会猜出单词，单词长度为%d，请发送单词[CQ:image,file=file:///%s]'%(
                        game.rows, game.length, savePath))
        elif msg in self.hintWords:
            game = self.games.get(groupId)
            if game == None:
                return None
                # send(groupId, '[CQ:reply,id=%d]群内没有正在进行的猜单词游戏，请输入“猜单词”或“-wordle”开始游戏'%data['message_id'])
            if get_user_coins(userId, format=False) < 5*100:
                send(groupId, 'coins不足，无法提示')
            else:
                hint = game.get_hint()
                if len(hint.replace("*", "")) == 0:
                    send(groupId, "你还没有猜对过一个字母哦，再猜猜吧~")
                else:
                    game.draw_hint(hint, savePath)
                    send(groupId, '[CQ:image,file=file:///%s]'%savePath)
                    self.deposit[groupId] -= 5*100
                    update_user_coins(userId, -5*100, '猜单词提示', format=False)
        elif msg in self.stopWords:
            game = self.games.pop(groupId, None)
            if game == None:
                return None
                # send(groupId, '[CQ:reply,id=%d]群内没有正在进行的猜单词游戏，输入“猜单词”或“-wordle”可以开始游戏'%data['message_id'])
            else:
                msg = "游戏已结束"
                if len(game.guessed_words) >= 1:
                    msg += f"\n{game.result}"
                send(groupId, msg)
        elif self.wordPattern.match(msg) != None:
            game = self.games.get(groupId)
            word = msg
            if game != None:
                if len(word) != game.length:
                    send(groupId, '[CQ:reply,id=%d]单词长度不正确，请发送长度为%d的单词'%(data['message_id'], game.length))
                else:
                    result = game.guess(word)
                    if result == GuessResult.WIN:
                        game.draw(savePath)
                        send(groupId, '恭喜你猜出了单词！\n%s[CQ:image,file=file:///%s]'%(
                            game.result, savePath
                        ))
                        update_user_coins(userId, 15*100, '猜单词获胜', format=False)
                        initiator = self.initiator.get(groupId, None)
                        deposit = self.deposit.get(groupId, 0)
                        if deposit > 0 and initiator != None:
                            update_user_coins(initiator, deposit, '猜单词押金退还', format=False)
                        self.initiator.pop(groupId, None)
                        self.deposit.pop(groupId, None)
                        self.games.pop(groupId, None)
                    elif result == GuessResult.LOSS:
                        game.draw(savePath)
                        send(groupId, '很遗憾，没有人猜出来呢~\n%s[CQ:image,file=file:///%s]'%(
                            game.result, savePath
                        ))
                        self.games.pop(groupId)
                    elif result == GuessResult.DUPLICATE:
                        send(groupId, '[CQ:reply,id=%d]不对哦，这个单词已经被猜过了~'%data['message_id'])
                    elif result == GuessResult.ILLEGAL:
                        send(groupId, '[CQ:reply,id=%d]你确定“%s”是一个合法的单词吗？'%(data['message_id'], word))
                    else:
                        game.draw(savePath)
                        send(groupId, '[CQ:image,file=file:///%s]'%(savePath))
            else:
                return None
        elif self.difficultyPattern.match(msg) != None:
            difficulty:str = self.difficultyPattern.findall(msg)[0]
            difficulty = difficulty.upper()
            if len(difficulty) == 0:
                difficulty = self.difficulties.get(groupId, 'CET4')
                send(groupId, '[CQ:reply,id=%d]当前难度为“%s”'%(data['message_id'], difficulty))
            elif difficulty in self.difficultyList:
                self.difficulties[groupId] = difficulty
                writeDifficulty(groupId, difficulty)
                send(groupId, '[CQ:reply,id=%d]设置成功，当前难度为%s'%(data['message_id'], difficulty))
            else:
                send(groupId,'[CQ:reply,id=%d]设置失败，可用的难度有：\n%s'%(data['message_id'], '、'.join(self.difficultyList)))
        return 'OK'
    
    def getPluginInfo(self) -> dict:
        return {
            'name': 'Wordle',
            'description': '猜单词',
            'commandDescription': '猜单词 / -wordle',
            'usePlace': ['group',],
            'showInHelp': True,
            'pluginConfigTableNames': [],
            'version': '1.0.0',
            'author': 'Unicorn',
        }
class WordleHelper(StandardPlugin):
    def judgeTrigger(self, msg: str, data: Any) -> bool:
        return msg in ['猜单词帮助', '单词帮助']
    def executeEvent(self, msg: str, data: Any) -> Union[str, None]:
        groupId = data['group_id']
        savePath = os.path.join(ROOT_PATH, SAVE_TMP_PATH, 'wordlehelp.png')
        drawHelpPic(savePath)
        send(groupId, f'[CQ:image,file=file:///{savePath}]', 'group')
        return 'OK'
    def getPluginInfo(self) -> dict:
        return {
            'name': 'WordleHelper',
            'description': '猜单词帮助',
            'commandDescription': '猜单词帮助',
            'usePlace': ['group',],
            'showInHelp': True,
            'pluginConfigTableNames': [],
            'version': '1.0.0',
            'author': 'Unicorn',
        }

class GuessResult(Enum):
    WIN = 0  # 猜出正确单词
    LOSS = 1  # 达到最大可猜次数，未猜出正确单词
    DUPLICATE = 2  # 单词重复
    ILLEGAL = 3  # 单词不合法


class WordleGame:
    @staticmethod
    def length_to_times(length: int)->int:
        return {
            3: 8,
            4: 7,
            5: 6,
            6: 6,
            7: 6,
            8: 7,
            9: 7,
            10: 7,
            11: 8,
            12: 8,
            13: 8,
        }.get(length, 6)

    def __init__(self, word: str, meaning: str):
        self.word: str = word  # 单词
        self.meaning: str = meaning  # 单词释义
        self.result = f"【单词】：{self.word}\n【释义】：{self.meaning}"
        self.word_lower: str = self.word.lower()
        self.length: int = len(word)  # 单词长度
        self.rows: int = self.length_to_times(self.length)  # 可猜次数
        self.guessed_words: List[str] = []  # 记录已猜单词

        self.block_size = (40, 40)  # 文字块尺寸
        self.block_padding = (10, 10)  # 文字块之间间距
        self.padding = (20, 20)  # 边界间距
        self.border_width = 2  # 边框宽度
        self.font_size = 20  # 字体大小
        self.font = ImageFont.truetype(os.path.join(ROOT_PATH, FONTS_PATH, "KarnakPro-Bold.ttf"), self.font_size, encoding="utf-8")

        self.correct_color = (134, 163, 115)  # 存在且位置正确时的颜色
        self.exist_color = (198, 182, 109)  # 存在但位置不正确时的颜色
        self.wrong_color = (123, 123, 124)  # 不存在时颜色
        self.border_color = (123, 123, 124)  # 边框颜色
        self.bg_color = (255, 255, 255)  # 背景颜色
        self.font_color = (255, 255, 255)  # 文字颜色

        self.spellChecker = WordleGame._get_spell_checker()
        
    def legal_word(self, word:str) -> bool:
        return not self.spellChecker.unknown((word,))
    
    def guess(self, word: str) -> Optional[GuessResult]:
        word = word.lower()
        if word == self.word_lower:
            self.guessed_words.append(word)
            return GuessResult.WIN
        if word in self.guessed_words:
            return GuessResult.DUPLICATE
        if not self.legal_word(word):
            return GuessResult.ILLEGAL
        self.guessed_words.append(word)
        if len(self.guessed_words) == self.rows:
            return GuessResult.LOSS

    def draw_block(self, color: Tuple[int, int, int], letter: str) -> Image.Image:
        block = Image.new("RGB", self.block_size, self.border_color)
        inner_w = self.block_size[0] - self.border_width * 2
        inner_h = self.block_size[1] - self.border_width * 2
        inner = Image.new("RGB", (inner_w, inner_h), color)
        block.paste(inner, (self.border_width, self.border_width))
        if letter:
            letter = letter.upper()
            draw = ImageDraw.Draw(block)
            bbox = self.font.getbbox(letter)
            x = (self.block_size[0] - bbox[2]) / 2
            y = (self.block_size[1] - bbox[3]) / 2
            draw.text((x, y), letter, font=self.font, fill=self.font_color)
        return block

    def draw(self, savePath:str):
        board_w = self.length * self.block_size[0]
        board_w += (self.length - 1) * self.block_padding[0] + 2 * self.padding[0]
        board_h = self.rows * self.block_size[1]
        board_h += (self.rows - 1) * self.block_padding[1] + 2 * self.padding[1]
        board_size = (board_w, board_h)
        board = Image.new("RGB", board_size, self.bg_color)

        for row in range(self.rows):
            if row < len(self.guessed_words):
                guessed_word = self.guessed_words[row]

                word_incorrect = ""  # 猜错的字母
                for i in range(self.length):
                    if guessed_word[i] != self.word_lower[i]:
                        word_incorrect += self.word_lower[i]
                    else:
                        word_incorrect += "_"  # 猜对的字母用下划线代替

                blocks: List[Image.Image] = []
                for i in range(self.length):
                    letter = guessed_word[i]
                    if letter == self.word_lower[i]:
                        color = self.correct_color
                    elif letter in word_incorrect:
                        """
                        一个字母的黄色和绿色数量与答案中的数量保持一致
                        以输入apple，答案adapt为例
                        结果为apple的第一个p是黄色，第二个p是灰色
                        代表答案中只有一个p，且不在第二个位置
                        """
                        word_incorrect = word_incorrect.replace(letter, "_", 1)
                        color = self.exist_color
                    else:
                        color = self.wrong_color
                    blocks.append(self.draw_block(color, letter))

            else:
                blocks = [
                    self.draw_block(self.bg_color, "") for _ in range(self.length)
                ]

            for col, block in enumerate(blocks):
                x = self.padding[0] + (self.block_size[0] + self.block_padding[0]) * col
                y = self.padding[1] + (self.block_size[1] + self.block_padding[1]) * row
                board.paste(block, (x, y))
        board.save(savePath)

    def get_hint(self) -> str:
        letters = set()
        for word in self.guessed_words:
            for letter in word:
                if letter in self.word_lower:
                    letters.add(letter)
        return "".join([i if i in letters else "*" for i in self.word_lower])

    def draw_hint(self, hint: str, savePath:str):
        board_w = self.length * self.block_size[0]
        board_w += (self.length - 1) * self.block_padding[0] + 2 * self.padding[0]
        board_h = self.block_size[1] + 2 * self.padding[1]
        board = Image.new("RGB", (board_w, board_h), self.bg_color)

        for i in range(len(hint)):
            letter = hint[i].replace("*", "")
            color = self.correct_color if letter else self.bg_color
            x = self.padding[0] + (self.block_size[0] + self.block_padding[0]) * i
            y = self.padding[1]
            board.paste(self.draw_block(color, letter), (x, y))
        board.save(savePath)

    @staticmethod
    def _get_spell_checker() -> SpellChecker:
        """
        Return a SpellChecker pre-loaded with words returned by `_get_words()`.
        """
        spell_checker = SpellChecker()
        word_set = WordleGame._get_words()
        spell_checker.word_frequency.load_words(word_set)
        return spell_checker

    @cache
    @staticmethod
    def _get_words() -> Set[str]:
        """
        Return a set of all words in the local wordle dictionaries.
        """
        wordleResourcePath = os.path.join(ROOT_PATH, WORDLE_RESOURCE_PATH)
        word_set: Set[str] = set()
        # add all keys of wordle dictionary to set
        for wordleResourceName in os.listdir(wordleResourcePath):
            _, suffix = os.path.splitext(wordleResourceName)
            if suffix != '.json': continue
            with open(
                os.path.join(wordleResourcePath, wordleResourceName),
                'r',
                encoding='utf-8'
            ) as f:
                word_set |= json.load(f).keys()
        return word_set
    