from typing import Any, Union, Dict, List, Tuple, Optional
from utils.basicConfigs import ROOT_PATH, SAVE_TMP_PATH, FONTS_PATH
from utils.basicEvent import send
from utils.standardPlugin import StandardPlugin
from utils.sqlUtils import newSqlSession
from utils.responseImage_beta import ResponseImage, PALETTE_CYAN
from utils.accountOperation import get_user_coins, update_user_coins
import os, re, json
from enum import Enum
from PIL import ImageFont, Image, ImageDraw
from dataclasses import dataclass
from pypinyin import Style, pinyin
import random
HANDLE_RESOURCE_PATH = 'resources/handle'
class GuessResult(Enum):
    WIN = 0  # 猜出正确成语
    LOSS = 1  # 达到最大可猜次数，未猜出正确成语
    DUPLICATE = 2  # 成语重复
    ILLEGAL = 3  # 成语不合法


class GuessState(Enum):
    CORRECT = 0  # 存在且位置正确
    EXIST = 1  # 存在但位置不正确
    WRONG = 2  # 不存在


@dataclass
class ColorGroup:
    bg_color: str  # 背景颜色
    block_color: str  # 方块颜色
    correct_color: str  # 存在且位置正确时的颜色
    exist_color: str  # 存在但位置不正确时的颜色
    wrong_color_pinyin: str  # 不存在时的颜色
    wrong_color_char: str  # 不存在时的颜色


NORMAL_COLOR = ColorGroup(
    "#ffffff", "#f7f8f9", "#1d9c9c", "#de7525", "#b4b8be", "#5d6673"
)

ENHANCED_COLOR = ColorGroup(
    "#ffffff", "#f7f8f9", "#5ba554", "#ff46ff", "#b4b8be", "#5d6673"
)
# 声母
INITIALS = ["zh", "z", "y", "x", "w", "t", "sh", "s", "r", "q", "p", "n", "m", "l", "k", "j", "h", "g", "f", "d", "ch", "c", "b"]
# 韵母
FINALS = [
    "ün", "üe", "üan", "ü", "uo", "un", "ui", "ue", "uang", "uan", "uai", "ua", "ou", "iu", "iong", "ong", "io", "ing",
    "in", "ie", "iao", "iang", "ian", "ia", "er", "eng", "en", "ei", "ao", "ang", "an", "ai", "u", "o", "i", "e", "a"
]
# fmt: on


def get_pinyin(idiom: str) -> List[Tuple[str, str, str]]:
    pys = pinyin(idiom, style=Style.TONE3, v_to_u=True)
    results = []
    for p in pys:
        py = p[0]
        if py[-1].isdigit():
            tone = py[-1]
            py = py[:-1]
        else:
            tone = ""
        initial = ""
        for i in INITIALS:
            if py.startswith(i):
                initial = i
                break
        final = ""
        for f in FINALS:
            if py.endswith(f):
                final = f
                break
        results.append((initial, final, tone))  # 声母，韵母，声调
    return results

class HandleGame:
    IDIOMS = []
    with open(os.path.join(ROOT_PATH, HANDLE_RESOURCE_PATH, 'idioms.txt'), 'r', encoding='utf-8') as f:
        for idiom in f.readlines():
            IDIOMS.append(idiom.strip())
    
    def __init__(self, idiom: str, explanation: str, strict: bool = False):
        self.idiom: str = idiom  # 成语
        self.explanation: str = explanation  # 释义
        self.strict: bool = strict  # 是否判断输入词语为成语
        self.result = f"【成语】：{idiom}\n【释义】：{explanation}"
        self.pinyin: List[Tuple[str, str, str]] = get_pinyin(idiom)  # 拼音
        self.length = 4
        self.times: int = 10  # 可猜次数
        self.guessed_idiom: List[str] = []  # 记录已猜成语
        self.guessed_pinyin: List[List[Tuple[str, str, str]]] = []  # 记录已猜成语的拼音

        self.block_size = (160, 160)  # 文字块尺寸
        self.block_padding = (20, 20)  # 文字块之间间距
        self.padding = (40, 40)  # 边界间距
        font_size_char = 60  # 汉字字体大小
        font_size_pinyin = 30  # 拼音字体大小
        font_size_tone = 22  # 声调字体大小
        self.font_char = ImageFont.truetype(os.path.join(ROOT_PATH, FONTS_PATH, "NotoSerifSC-Regular.otf"), font_size_char, encoding='utf-8')
        self.font_pinyin = ImageFont.truetype(os.path.join(ROOT_PATH, FONTS_PATH, "NotoSansMono-Regular.ttf"), font_size_pinyin, encoding='utf-8')
        self.font_tone = ImageFont.truetype(os.path.join(ROOT_PATH, FONTS_PATH, "NotoSansMono-Regular.ttf"), font_size_tone, encoding='utf-8')

        self.colors = ENHANCED_COLOR if False else NORMAL_COLOR

    def guess(self, idiom: str) -> Optional[GuessResult]:
        if self.strict and idiom not in self.IDIOMS:
            return GuessResult.ILLEGAL
        if idiom in self.guessed_idiom:
            return GuessResult.DUPLICATE
        self.guessed_idiom.append(idiom)
        self.guessed_pinyin.append(get_pinyin(idiom))
        if idiom == self.idiom:
            return GuessResult.WIN
        if len(self.guessed_idiom) == self.times:
            return GuessResult.LOSS

    def draw_block(
        self,
        block_color: str,
        char: str = "",
        char_color: str = "",
        initial: str = "",
        initial_color: str = "",
        final: str = "",
        final_color: str = "",
        tone: str = "",
        tone_color: str = "",
        underline: bool = False,
        underline_color: str = "",
    ) -> Image.Image:
        block = Image.new("RGB", self.block_size, block_color)
        if not char:
            return block
        draw = ImageDraw.Draw(block)

        char_size = self.font_char.getbbox(char)[2:]
        x = (self.block_size[0] - char_size[0]) / 2
        y = (self.block_size[1] - char_size[1]) / 5 * 3
        draw.text((x, y), char, font=self.font_char, fill=char_color)

        space = 5
        need_space = bool(initial and final)
        py_length = self.font_pinyin.getlength(initial + final)
        if need_space:
            py_length += space
        py_start = (self.block_size[0] - py_length) / 2
        x = py_start
        y = self.block_size[0] / 8
        draw.text((x, y), initial, font=self.font_pinyin, fill=initial_color)
        x += self.font_pinyin.getlength(initial)
        if need_space:
            x += space
        draw.text((x, y), final, font=self.font_pinyin, fill=final_color)

        tone_size = self.font_tone.getbbox(tone)[2:]
        x = (self.block_size[0] + py_length) / 2 + tone_size[0] / 3
        y -= tone_size[1] / 3
        draw.text((x, y), tone, font=self.font_tone, fill=tone_color)

        if underline:
            x = py_start
            py_size = self.font_pinyin.getbbox(initial + final)[2:]
            y = self.block_size[0] / 8 + py_size[1] + 2
            draw.line((x, y, x + py_length, y), fill=underline_color, width=1)
            y += 3
            draw.line((x, y, x + py_length, y), fill=underline_color, width=1)

        return block

    def draw(self, savePath:str) -> None:
        rows = min(len(self.guessed_idiom) + 1, self.times)
        board_w = self.length * self.block_size[0]
        board_w += (self.length - 1) * self.block_padding[0] + 2 * self.padding[0]
        board_h = rows * self.block_size[1]
        board_h += (rows - 1) * self.block_padding[1] + 2 * self.padding[1]
        board_size = (board_w, board_h)
        board = Image.new("RGB", board_size, self.colors.bg_color)

        def get_states(guessed: List[str], answer: List[str]) -> List[GuessState]:
            states = []
            incorrect = []
            for i in range(self.length):
                if guessed[i] != answer[i]:
                    incorrect.append(answer[i])
                else:
                    incorrect.append("_")
            for i in range(self.length):
                if guessed[i] == answer[i]:
                    states.append(GuessState.CORRECT)
                elif guessed[i] in incorrect:
                    states.append(GuessState.EXIST)
                    incorrect[incorrect.index(guessed[i])] = "_"
                else:
                    states.append(GuessState.WRONG)
            return states

        def get_pinyin_color(state: GuessState) -> str:
            if state == GuessState.CORRECT:
                return self.colors.correct_color
            elif state == GuessState.EXIST:
                return self.colors.exist_color
            else:
                return self.colors.wrong_color_pinyin

        def get_char_color(state: GuessState) -> str:
            if state == GuessState.CORRECT:
                return self.colors.correct_color
            elif state == GuessState.EXIST:
                return self.colors.exist_color
            else:
                return self.colors.wrong_color_char

        def block_pos(row: int, col: int) -> Tuple[int, int]:
            x = self.padding[0] + (self.block_size[0] + self.block_padding[0]) * col
            y = self.padding[1] + (self.block_size[1] + self.block_padding[1]) * row
            return x, y

        for i in range(rows - 1):
            idiom = self.guessed_idiom[i]
            pinyin = self.guessed_pinyin[i]
            char_states = get_states(list(idiom), list(self.idiom))
            initial_states = get_states(
                [p[0] for p in pinyin], [p[0] for p in self.pinyin]
            )
            final_states = get_states(
                [p[1] for p in pinyin], [p[1] for p in self.pinyin]
            )
            tone_states = get_states(
                [p[2] for p in pinyin], [p[2] for p in self.pinyin]
            )
            underline_states = get_states(
                [p[0] + p[1] for p in pinyin], [p[0] + p[1] for p in self.pinyin]
            )
            for j in range(self.length):
                char = idiom[j]
                i2, f2, t2 = pinyin[j]
                if char == self.idiom[j]:
                    block_color = self.colors.correct_color
                    char_color = (
                        initial_color
                    ) = final_color = tone_color = self.colors.bg_color
                    underline = False
                    underline_color = ""
                else:
                    block_color = self.colors.block_color
                    char_color = get_char_color(char_states[j])
                    initial_color = get_pinyin_color(initial_states[j])
                    final_color = get_pinyin_color(final_states[j])
                    tone_color = get_pinyin_color(tone_states[j])
                    underline_color = get_pinyin_color(underline_states[j])
                    underline = underline_color in (
                        self.colors.correct_color,
                        self.colors.exist_color,
                    )
                block = self.draw_block(
                    block_color,
                    char,
                    char_color,
                    i2,
                    initial_color,
                    f2,
                    final_color,
                    t2,
                    tone_color,
                    underline,
                    underline_color,
                )
                board.paste(block, block_pos(i, j))

        i = rows - 1
        for j in range(self.length):
            block = self.draw_block(self.colors.block_color)
            board.paste(block, block_pos(i, j))
        board.save(savePath)

    def draw_hint(self, savePath:str):
        guessed_char = set("".join(self.guessed_idiom))
        guessed_initial = set()
        guessed_final = set()
        guessed_tone = set()
        for pinyin in self.guessed_pinyin:
            for p in pinyin:
                guessed_initial.add(p[0])
                guessed_final.add(p[1])
                guessed_tone.add(p[2])

        board_w = self.length * self.block_size[0]
        board_w += (self.length - 1) * self.block_padding[0] + 2 * self.padding[0]
        board_h = self.block_size[1] + 2 * self.padding[1]
        board = Image.new("RGB", (board_w, board_h), self.colors.bg_color)

        for i in range(self.length):
            char = self.idiom[i]
            hi, hf, ht = self.pinyin[i]
            color = char_c = initial_c = final_c = tone_c = self.colors.correct_color
            if char not in guessed_char:
                char = "?"
                color = self.colors.block_color
                char_c = self.colors.wrong_color_char
            else:
                char_c = initial_c = final_c = tone_c = self.colors.bg_color
            if hi not in guessed_initial:
                hi = "?"
                initial_c = self.colors.wrong_color_pinyin
            if hf not in guessed_final:
                hf = "?"
                final_c = self.colors.wrong_color_pinyin
            if ht not in guessed_tone:
                ht = "?"
                tone_c = self.colors.wrong_color_pinyin
            block = self.draw_block(
                color, char, char_c, hi, initial_c, hf, final_c, ht, tone_c
            )
            x = self.padding[0] + (self.block_size[0] + self.block_padding[0]) * i
            y = self.padding[1]
            board.paste(block, (x, y))
        board.save(savePath)

def drawHelpPic(savePath:str):
    helpWords = (
        "输入“猜成语”或者“-handle”开始游戏：\n"
        "你有十次的机会猜一个四字词语；\n"
        "每次猜测后，汉字与拼音的颜色将会标识其与正确答案的区别；\n"
        "青色 表示其出现在答案中且在正确的位置；\n"
        "橙色 表示其出现在答案中但不在正确的位置；\n"
        "每个格子的 汉字、声母、韵母、声调 都会独立进行颜色的指示。\n"
        "当四个格子都为青色时，你便赢得了游戏！\n"
        "发送“结束”结束游戏；发送“提示”查看提示；\n\n"
        "游戏发起者在开始游戏时需缴30 coins，其中25 coins作为押金，5 coins为胜利者奖金。"
        "游戏胜利时，猜对的用户获得系统和发起者提供的总共15 coins奖励，"
        "同时押金退还至游戏发起者。游戏过程中每提示一次，押金和提示者各扣除5 coins，"
        "押金等于0时仍可提示，不会使之变成负数。\n"
        "游戏失败不退coins。"
    )
    helpCards = ResponseImage(
        title = '猜成语帮助', 
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

class HandleHelper(StandardPlugin):
    def judgeTrigger(self, msg: str, data: Any) -> bool:
        return msg in ['猜成语帮助', '成语帮助']
    def executeEvent(self, msg: str, data: Any) -> Union[str, None]:
        groupId = data['group_id']
        savePath = os.path.join(ROOT_PATH, SAVE_TMP_PATH, 'handlehelp.png')
        drawHelpPic(savePath)
        send(groupId, f'[CQ:image,file=file:///{savePath}]', 'group')
        return 'OK'
    def getPluginInfo(self) -> dict:
        return {
            'name': 'HandleHelper',
            'description': '猜成语帮助',
            'commandDescription': '猜成语帮助',
            'usePlace': ['group',],
            'showInHelp': True,
            'pluginConfigTableNames': [],
            'version': '1.0.0',
            'author': 'Unicorn',
        }
        
class Handle(StandardPlugin):
    def __init__(self) -> None:
        self.answers:Optional[List[Dict[str, str]]] = None
        self.wordPattern = re.compile(r'^[\u4e00-\u9fa5]{4}$')
        self.startWords = ['猜成语', '-handle']
        self.hintWords = ['成语提示', '猜成语提示', '提示']
        self.stopWords = ['结束']
        self.games:Dict[int,Optional[HandleGame]] = {}
        self.deposit:Dict[int, Optional[int]] = {}
        self.initiator:Dict[int, int] = {}
        self.load_words()
        
    def load_words(self):
        with open(os.path.join(ROOT_PATH, HANDLE_RESOURCE_PATH, 'answers.json'), 'r', encoding='utf-8') as f:
            self.answers = json.load(f)
    def random_word(self)->Tuple[str, str]:
        result = random.choice(self.answers)
        return result['word'], result['explanation']
    def judgeTrigger(self, msg: str, data: Any) -> bool:
        return (
            (msg in self.startWords) or 
            (msg in self.hintWords) or
            (msg in self.stopWords) or
            (self.wordPattern.match(msg) != None) 
        )
        
    def executeEvent(self, msg: str, data: Any) -> Union[str, None]:
        groupId = data['group_id']
        userId = data['user_id']
        savePath = os.path.join(ROOT_PATH, SAVE_TMP_PATH, 'handle-%d.png'%groupId)
        if msg in self.startWords:
            game = self.games.get(groupId)
            if game != None:
                game:HandleGame
                game.draw(savePath)
                send(groupId, '当前有正在进行的猜成语游戏\n[CQ:image,file=file:///%s]'%savePath)
            elif get_user_coins(userId,format=False) < 30 * 100:
                send(groupId, 'coins不足30，无法发起游戏')
            else:
                update_user_coins(userId, -30*100, '猜成语押金', format=False)
                self.deposit[groupId] = 25*100
                self.initiator[groupId] = userId
                word, explain = self.random_word()
                game = self.games[groupId] = HandleGame(word, explain, strict=True)
                game.draw(savePath)
                send(groupId, '你有%d次机会猜一个四字成语，请发送成语[CQ:image,file=file:///%s]'%(
                        game.times, savePath))
        elif msg in self.hintWords:
            game = self.games.get(groupId)
            if game == None: return None
            if get_user_coins(userId, format=False) < 5*100:
                send(groupId, 'coins不足，无法提示')
            else:
                game.draw_hint(savePath)
                send(groupId, '[CQ:image,file=file:///%s]'%savePath)
                self.deposit[groupId] -= 5*100
                update_user_coins(userId, -5*100, '猜成语提示', format=False)
        elif msg in self.stopWords:
            game = self.games.pop(groupId, None)
            if game == None: return None
            msg = "游戏已结束"
            if len(game.guessed_idiom) >= 1:
                msg += f"\n{game.result}"
            send(groupId, msg)
        elif self.wordPattern.match(msg) != None:
            game = self.games.get(groupId)
            word = msg
            if game == None: return None
            result = game.guess(word)
            if result == GuessResult.WIN:
                game.draw(savePath)
                send(groupId, '恭喜你猜出了成语！\n%s[CQ:image,file=file:///%s]'%(
                    game.result, savePath
                ))
                update_user_coins(userId, 15*100, '猜成语获胜', format=False)
                initiator = self.initiator.get(groupId, None)
                deposit = self.deposit.get(groupId, 0)
                if deposit > 0 and initiator != None:
                    update_user_coins(initiator, deposit, '猜成语押金退还', format=False)
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
                send(groupId, '[CQ:reply,id=%d]不对哦，这个成语已经被猜过了~'%data['message_id'])
            elif result == GuessResult.ILLEGAL:
                send(groupId, '[CQ:reply,id=%d]你确定“%s”是一个正确的成语吗？'%(data['message_id'], word))
            else:
                game.draw(savePath)
                send(groupId, '[CQ:image,file=file:///%s]'%(savePath))
            
        return 'OK'
    
    def getPluginInfo(self) -> dict:
        return {
            'name': 'Handle',
            'description': '猜成语',
            'commandDescription': '猜成语 / -handle',
            'usePlace': ['group',],
            'showInHelp': True,
            'pluginConfigTableNames': [],
            'version': '1.0.0',
            'author': 'Unicorn',
        }