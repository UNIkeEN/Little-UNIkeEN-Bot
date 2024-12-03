from typing import List, Tuple, Optional, Union, Any, Dict
from PIL import Image, ImageDraw, ImageFont
import os
import ast
from enum import IntEnum
import random
import itertools
from utils.basicEvent import send, warning
from utils.standardPlugin import StandardPlugin
from utils.responseImage_beta import ResponseImage, PALETTE_CYAN
from utils.basicConfigs import ROOT_PATH, SAVE_TMP_PATH, FONTS_PATH
from utils.accountOperation import get_user_coins, update_user_coins
import re

def generate_expression(length, limit: int=10_000) -> Tuple[str, int]:
    if length < 3 :
        raise ValueError("长度太短，至少需要3个字符")
    
    # 第一个模块：确定运算符
    num_operators = random.randint(1, length // 2 - 1)
    valid_operators = ['+', '-', '*', '/']
    probabilities = [0.28, 0.28, 0.28, 0.16]
    operators = random.choices(valid_operators, probabilities, k=num_operators)
    
    # 第二个模块，确定各数字长度
    num_numbers = num_operators + 1
    num_lens = [1] * num_numbers
    extra_num_len = length - num_operators - num_numbers
    for i in random.choices(list(range(num_numbers)), k=extra_num_len):
        num_lens[i] += 1

    
    # 第三个模块，根据长度生成数字
    def gen_num_by_len(len: int)->int:
        if len <= 0:
            raise ValueError('len <= 0')
        if len == 1:
            return random.randint(0, 9)
        return random.randint(10**(len-1), (10**len)-1)
    
    # 第四个模块：验证准确性
    for _ in range(80):
        nums = [str(gen_num_by_len(len)) for len in num_lens]
        result = ''.join([x for pair in itertools.zip_longest(nums, operators) for x in pair if x is not None])
        try:
            value = eval(result)
            if value == int(value) and abs(int(value)) <= limit:
                return result, int(value)
        except:
            continue
    return generate_expression(length, limit)

class GuessResult(IntEnum):
    WIN = 0  # 猜出正确算式
    LOSS = 1  # 达到最大可猜次数，未猜出正确算式
    DUPLICATE = 2  # 算式重复
    ILLEGAL = 3  # 算式不合法
    LEGAL = 4 # 合法的猜测

def calc_mathler_expr(word: str)->Tuple[bool, Union[int, str]]:
    legal_ops = [ast.Add, ast.Sub, ast.Mult, ast.Div] # no binary
    for c in word:
        if not c.isdigit() and c not in '+-*/':
            return False, '不合法字符“{}”，仅允许数字和+-*/'.format(c)

    def check_expr(expr: ast.expr) -> Tuple[bool, str]:
        if isinstance(expr, ast.BinOp):
            if type(expr.op) not in legal_ops:
                return False, '不合法运算符"{}"'.format(type(expr.op).__name__)
            result, reason = check_expr(expr.left)
            if not result:
                return False, reason
            result, reason = check_expr(expr.right)
            if not result:
                return False, reason
            return True, ""
        elif isinstance(expr, ast.Constant):
            if not isinstance(expr.value, int):
                return False, "不合法常数“{}”".format(expr.value)
            return True, ""
        else: # no unary op
            return False, "不合法运算符“{}”".format(type(expr).__name__)

    try:
        tree = ast.parse(word)
        check_result, reason = check_expr(tree.body[0].value)
        if not check_result:
            return False, reason
        value = eval(word)
        if isinstance(value, float):
            if int(value) != value:
                return False, "计算结果“{}”非整数".format(value)
        return True, int(value)
    except Exception as e:
        return False, "解析时出错：{}".format(e)

class MathlerGame:
    def __init__(self, word: str):
        legal, value = calc_mathler_expr(word)
        if not legal:
            raise ValueError('mathler word illegal: {}'.format(value))
        self.word: str = word  # 算式
        self.value: int = value # 算式的值
        self.result = f"【算式】：{self.word}\n【值】：{self.value}"
        self.word_lower: str = self.word.lower()
        self.length: int = len(word)  # 算式长度
        self.rows: int = self.length + 1  # 可猜次数
        self.guessed_words: List[str] = []  # 记录已猜算式

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
        
    def legal_word(self, word:str) -> Tuple[bool, str]:
        legal_ops = [ast.Add, ast.Sub, ast.Mult, ast.Div] # no binary
        if len(word) != self.length:
            return False, '算式长度不对，期望长度{}，实际长度{}'.format(self.length, len(word))
        legal, value = calc_mathler_expr(word)
        if not legal:
            return False, value
        if value == self.value:
            return True, '合法的猜测'
        else:
            return False, '结果不对，期望结果{}，实际结果{}'.format(self.value, value)
        
    
    def guess(self, word: str) -> Tuple[GuessResult, str]:
        word = word.lower()
        if word == self.word_lower:
            self.guessed_words.append(word)
            return GuessResult.WIN, '恭喜获胜'
        if word in self.guessed_words:
            return GuessResult.DUPLICATE, '重复的猜测'
        legal, reason = self.legal_word(word)
        if not legal:
            return GuessResult.ILLEGAL, reason
        self.guessed_words.append(word)
        if len(self.guessed_words) == self.rows:
            return GuessResult.LOSS, '用掉了所有的机会'
        return GuessResult.LEGAL, '可嘉的猜测'

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
        return "".join([i if i in letters else "@" for i in self.word_lower])

    def draw_hint(self, hint: str, savePath:str):
        board_w = self.length * self.block_size[0]
        board_w += (self.length - 1) * self.block_padding[0] + 2 * self.padding[0]
        board_h = self.block_size[1] + 2 * self.padding[1]
        board = Image.new("RGB", (board_w, board_h), self.bg_color)

        for i in range(len(hint)):
            letter = hint[i].replace("@", "")
            color = self.correct_color if letter else self.bg_color
            x = self.padding[0] + (self.block_size[0] + self.block_padding[0]) * i
            y = self.padding[1]
            board.paste(self.draw_block(color, letter), (x, y))
        board.save(savePath)

def drawHelpPic(savePath:str):
    helpWords = (
        "输入“猜算式”或者“-mathler”开始游戏：\n"
        "答案为指定长度、指定结果的算式；\n"
        "绿色块代表此算式中有此字符且位置正确；\n"
        "黄色块代表此算式中有此字符，但该字符所处位置不对；\n"
        "灰色块代表此算式中没有此字符；\n"
        "猜出算式或用光次数则游戏结束；\n"
        "发送“结束”结束游戏；发送“算式提示”查看提示；\n"
        "游戏发起者在开始游戏时需缴30 coins，其中25 coins作为押金，5 coins为胜利者奖金。"
        "游戏胜利时，猜对的用户获得系统和发起者提供的总共15 coins奖励，"
        "同时押金退还至游戏发起者。游戏过程中每提示一次，押金和提示者各扣除5 coins，"
        "押金等于0时仍可提示，不会使之变成负数。\n"
        "游戏失败不退coins。"
    )
    helpCards = ResponseImage(
        title = '猜算式帮助', 
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
    
class MathlerHelper(StandardPlugin):
    def judgeTrigger(self, msg: str, data: Any) -> bool:
        return msg in ['猜算式帮助', '算式帮助']
    def executeEvent(self, msg: str, data: Any) -> Union[str, None]:
        groupId = data['group_id']
        savePath = os.path.join(ROOT_PATH, SAVE_TMP_PATH, 'mathlerhelp.png')
        drawHelpPic(savePath)
        send(groupId, f'[CQ:image,file=file:///{savePath}]', 'group')
        return 'OK'
    def getPluginInfo(self) -> dict:
        return {
            'name': 'MathlerHelper',
            'description': '猜算式帮助',
            'commandDescription': '猜算式帮助',
            'usePlace': ['group',],
            'showInHelp': True,
            'pluginConfigTableNames': [],
            'version': '1.0.0',
            'author': 'Unicorn',
        }
        
class Mathler(StandardPlugin):
    def __init__(self):
        self.wordPattern = re.compile(r'^[0-9\+\-\*\/]{5,10}$')
        self.startWords = ['猜算式', '-mathler']
        self.hintWords = ['算式提示', '猜算式提示', '提示']
        self.stopWords = ['结束']
        
        self.games:Dict[int,Optional[MathlerGame]] = {}
        self.difficultyList = []
        # words[难度][算式长度] -> [算式, 解释]
        self.words:Dict[str,Dict[int,Tuple[str,str]]] = {}
        self.deposit:Dict[int, Optional[int]] = {}
        self.initiator:Dict[int, int] = {}
        
    def judgeTrigger(self, msg: str, data: Any) -> bool:
        return (
            (msg in self.startWords) or 
            (msg in self.hintWords) or
            (msg in self.stopWords) or
            (self.wordPattern.match(msg) != None)
        )
        
    @staticmethod
    def randomLen()->int:
        # 长度  概率    CDF
        # 5     20%    20%
        # 6     25%    45%
        # 7     30%    75%
        # 8     20%    95%
        # 9     5%    100%
        r = random.randint(0, 99)
        if r < 20: return 5
        elif r < 45: return 6
        elif r < 75: return 7
        elif r < 95: return 8
        else: return 9
    

    def executeEvent(self, msg: str, data: Any) -> Union[str, None]:
        groupId = data['group_id']
        userId = data['user_id']
        savePath = os.path.join(ROOT_PATH, SAVE_TMP_PATH, 'mathler-%d.png'%groupId)
        if msg in self.startWords:
            game = self.games.get(groupId)
            if game != None:
                game:MathlerGame
                game.draw(savePath)
                send(groupId, '当前有正在进行的猜算式游戏\n[CQ:image,file=file:///%s]'%savePath)
            else:
                if get_user_coins(userId, format=False) < 30*100:
                    send(groupId, 'coins不足30，无法发起游戏')
                else:
                    expr, value = generate_expression(self.randomLen(), limit=100)
                    update_user_coins(userId, -30*100, '猜算式押金', format=False)
                    self.deposit[groupId] = 25*100
                    self.initiator[groupId] = userId
                    game = self.games[groupId] = MathlerGame(expr)
                    game.draw(savePath)
                    send(groupId, '你有%d次机会猜出算式，算式长度为%d，值为%d，请发送算式[CQ:image,file=file:///%s]'%(
                        game.rows, game.length, game.value, savePath))
        elif msg in self.hintWords:
            game = self.games.get(groupId)
            if game == None:
                return None
                # send(groupId, '[CQ:reply,id=%d]群内没有正在进行的猜算式游戏，请输入“猜算式”或“-mathler”开始游戏'%data['message_id'])
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
                    update_user_coins(userId, -5*100, '猜算式提示', format=False)
        elif msg in self.stopWords:
            game = self.games.pop(groupId, None)
            if game == None:
                return None
                # send(groupId, '[CQ:reply,id=%d]群内没有正在进行的猜算式游戏，输入“猜算式”或“-mathler”可以开始游戏'%data['message_id'])
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
                    send(groupId, '[CQ:reply,id=%d]算式长度不正确，请发送长度为%d的算式'%(data['message_id'], game.length))
                else:
                    result, reason = game.guess(word)
                    if result == GuessResult.WIN:
                        game.draw(savePath)
                        send(groupId, '恭喜你猜出了算式！\n%s[CQ:image,file=file:///%s]'%(
                            game.result, savePath
                        ))
                        update_user_coins(userId, 15*100, '猜算式获胜', format=False)
                        initiator = self.initiator.get(groupId, None)
                        deposit = self.deposit.get(groupId, 0)
                        if deposit > 0 and initiator != None:
                            update_user_coins(initiator, deposit, '猜算式押金退还', format=False)
                        self.initiator.pop(groupId, None)
                        self.deposit.pop(groupId, None)
                        self.games.pop(groupId, None)
                    elif result == GuessResult.LOSS:
                        game.draw(savePath)
                        send(groupId, '算式是%s，很遗憾，没有人猜出来呢~\n%s[CQ:image,file=file:///%s]'%(
                            game.word, game.result, savePath
                        ))
                        self.games.pop(groupId)
                    elif result == GuessResult.DUPLICATE:
                        send(groupId, '[CQ:reply,id=%d]不对哦，这个算式已经被猜过了~'%data['message_id'])
                    elif result == GuessResult.ILLEGAL:
                        send(groupId, '[CQ:reply,id=%d]%s'%(data['message_id'], reason))
                    elif result == GuessResult.LEGAL:
                        game.draw(savePath)
                        send(groupId, '[CQ:image,file=file:///%s]'%(savePath))
                    else:
                        warning('logic error in mathler')
            else:
                return None
        return 'OK'
    
    def getPluginInfo(self) -> dict:
        return {
            'name': 'Mathler',
            'description': '猜算式',
            'commandDescription': '猜算式 / -mathler',
            'usePlace': ['group',],
            'showInHelp': True,
            'pluginConfigTableNames': [],
            'version': '1.0.0',
            'author': 'Unicorn',
        }
    