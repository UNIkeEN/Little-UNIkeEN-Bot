# -*- coding: utf-8 -*-
from utils.accountOperation import get_user_coins, update_user_coins
from utils.basicConfigs import ROOT_PATH, FONTS_PATH
from utils.basicEvent import *
from utils.responseImage import *
from utils.standardPlugin import StandardPlugin
import random
import time
import json
import re


# 塔罗牌牌阵接口类
class TarotSpreads:
    """塔罗牌牌阵接口类"""

    description = "牌阵描述信息"
    resourcePath = "./resources/tarot"
    meaning = []  # 牌阵中每张牌对应的含义 List[str]

    def __init__(self):
        self.cards = []

    def draw_cards(self, num=1) -> None:
        """抽取牌阵对应的塔罗牌"""
        self.cards = [
            [sample_card, random.randint(0, 1)] for sample_card in random.sample(CARDS, num)  # 对每张牌，随机抽取正逆位
        ]

    def get_description(self) -> ResponseImage.Card:
        """获取牌阵描述卡片"""
        raw_content = [("title", "牌阵解读")]
        for i, (card_name, position) in enumerate(self.cards):
            position_str = "正位" if position == 0 else "逆位"
            description = INFORMATION[card_name][position_str]
            raw_content.append(("separator",))
            raw_content.append(("subtitle", self.meaning[i]))
            raw_content.append(("keyword", f"{position_str} {card_name}"))
            raw_content.append(("body", f"它代表着 {description}"))
        return ResponseImage.RichContentCard(raw_content)

    def get_image(self) -> Image.Image:
        """获取牌阵图片"""
        raise NotImplementedError("子类必须实现获取图片逻辑")

    def _get_images(self) -> List[Image.Image]:
        """辅助函数，获取所有塔罗牌图片"""
        img_series = random.choice([150, 153, 160, 164, 176, 177, 178])  # 随机选一套牌
        images = []
        for card_name, position in self.cards:
            file_name = INFORMATION[card_name]["file_name"]
            img_path = os.path.join(self.resourcePath, str(img_series), file_name)
            tarot_img = Image.open(img_path)
            if position == 1:  # 逆位翻转图片
                tarot_img = tarot_img.transpose(Image.FLIP_TOP_BOTTOM)
            images.append(tarot_img)
        return images

    def _draw_single_image(self, canvas: Image.Image, image: Image.Image, text: str, position: tuple) -> Image.Image:
        """辅助函数，在画布上绘制单张塔罗牌图片并在其下添加文字

        position为图片中心位置"""
        center_x, center_y = position
        tarot_x = center_x - image.width // 2
        tarot_y = center_y - image.height // 2
        canvas.paste(image, (tarot_x, tarot_y))  # 在画布上绘制塔罗牌图片
        draw = ImageDraw.Draw(canvas)
        # 如果 pillow 版本低于 9.0.0，使用 textsize
        text_width, text_height = draw.textsize(text, font=FONT_HYWH_18)
        text_x = center_x - text_width // 2
        # 如果 pillow 版本高于 9.0.0，使用 textbbox
        # left, top, right, bottom = draw.textbbox((center_x, center_y), text, font=FONT_HYWH_18)
        # text_x = center_x - (right - left) // 2
        # 计算文字位置，放置在塔罗牌图片下方
        text_y = center_y + image.height // 2 + 10
        draw.text((text_x, text_y), text, fill=(0, 0, 0), font=FONT_HYWH_18)
        return canvas  # 返回绘制好的画布


# 单张牌阵
class SingleCardSpread(TarotSpreads):
    """单张牌阵"""

    description = "随机抽取一张塔罗牌"
    meaning = ["这张牌代表着当前的能量和指导"]

    def draw_cards(self, num=1):
        super().draw_cards(1)  # 抽取一张牌

    def get_image(self) -> Image.Image:
        return self._get_images()[0]  # 返回抽取的单张牌图片


# 时间之流牌阵
class TimeFlowSpread(TarotSpreads):
    """时间之流牌阵"""

    description = "占卜过去、现在和未来"
    meaning = [
        "第一张牌代表着过去",
        "第二张牌代表着现在",
        "第三张牌代表着未来",
    ]

    def draw_cards(self, num=3):
        super().draw_cards(3)  # 抽取3张牌，分别代表过去、现在和未来

    def get_image(self) -> Image.Image:
        images = self._get_images()  # 获取抽取的塔罗牌图片
        # 创建画布
        width, height = images[0].size
        canvas_size = (120 + 3 * width, 60 + height)
        canvas = Image.new("RGBA", canvas_size, PALETTE_WHITE)
        # 在画布上绘制每张塔罗牌图片和对应的文字
        canvas = self._draw_single_image(canvas, images[0], "过去", (30 + width // 2, 20 + height // 2))
        canvas = self._draw_single_image(canvas, images[1], "现在", (60 + 3 * width // 2, 20 + height // 2))
        canvas = self._draw_single_image(canvas, images[2], "未来", (90 + 5 * width // 2, 20 + height // 2))
        return canvas  # 返回绘制好的画布


# 圣三角牌阵
class HolyTriangleSpread(TarotSpreads):
    """圣三角牌阵"""

    description = "占卜原因、现状和结果"
    meaning = [
        "第一张牌代表着问题的原因",
        "第二张牌代表着当前的现状",
        "第三张牌代表着未来的结果",
    ]

    def draw_cards(self, num=3):
        super().draw_cards(3)  # 抽取3张牌，分别代表原因、现状和结果

    def get_image(self) -> Image.Image:
        images = self._get_images()  # 获取抽取的塔罗牌图片
        # 创建画布
        width, height = images[0].size
        canvas_size = (120 + 3 * width, 60 + 3 * height // 2)
        canvas = Image.new("RGBA", canvas_size, PALETTE_WHITE)
        # 在画布上绘制每张塔罗牌图片和对应的文字
        canvas = self._draw_single_image(canvas, images[0], "1. 原因", (60 + 3 * width // 2, 20 + height // 2))
        canvas = self._draw_single_image(canvas, images[1], "2. 现状", (30 + width // 2, 20 + height))
        canvas = self._draw_single_image(canvas, images[2], "3. 结果", (90 + 5 * width // 2, 20 + height))
        return canvas  # 返回绘制好的画布


# 二选一牌阵
class TwoChoiceSpread(TarotSpreads):
    """二选一牌阵"""

    description = "帮助做出选择或决策"
    meaning = [
        "第一张牌代表着事件的现状",
        "第二张牌代表着选择A的发展",
        "第三张牌代表着选择B的发展",
        "第四张牌代表着选择A的结果",
        "第五张牌代表着选择B的结果",
    ]

    def draw_cards(self, num=5):
        # 5张牌，分别代表现状、选择A的发展、选择B的发展、A的结果、B的结果
        super().draw_cards(5)

    def get_image(self):
        images = self._get_images()  # 获取抽取的塔罗牌图片
        # 创建画布
        width, height = images[0].size
        half_w, half_h = width // 2, height // 2
        canvas_size = (120 + 4 * width, int(100 + 5 * height // 2))
        canvas = Image.new("RGBA", canvas_size, PALETTE_WHITE)
        # 在画布上绘制每张塔罗牌图片和对应的文字
        canvas = self._draw_single_image(canvas, images[0], "现状", (60 + 4 * half_w, 60 + 4 * half_h))
        canvas = self._draw_single_image(canvas, images[1], "选择A", (30 + 2 * half_w, 60 + 3 * half_h))
        canvas = self._draw_single_image(canvas, images[2], "选择B", (90 + 6 * half_w, 60 + 3 * half_h))
        canvas = self._draw_single_image(canvas, images[3], "A的结果", (30 + half_w, 20 + half_h))
        canvas = self._draw_single_image(canvas, images[4], "B的结果", (90 + 7 * half_w, 20 + half_h))
        return canvas  # 返回绘制好的画布


# 身心灵牌阵
class BodyMindSpiritSpread(TarotSpreads):
    """身心灵牌阵"""

    description = "占卜身心灵整体的平衡和发展"
    meaning = [
        "第一张牌为身牌，代表目前的身体状况",
        "第二张牌为心牌，代表目前的心理状态",
        "第三张牌为灵牌，给予精神方面的启示",
        "第四张牌为阴影，由前三张加和而来，表示可学习提升的元素",
    ]

    def draw_cards(self, num=3):
        nums = random.sample(range(78), 3)  # 随机抽取3张牌
        self.cards = [[CARDS[index], random.randint(0, 1)] for index in nums]  # 对每张牌，随机抽取正逆位
        forth_card_num = sum([index % 14 + 1 if index < 56 else index - 56 for index in nums])  # 牌面求和
        if forth_card_num > 21:
            forth_card_num = forth_card_num % 10 + forth_card_num // 10
        self.cards.append([CARDS[forth_card_num + 56], random.randint(0, 1)])  # 添加第四张牌

    def get_image(self) -> Image.Image:
        images = self._get_images()  # 获取抽取的塔罗牌图片
        # 创建画布
        width, height = images[0].size
        half_w, half_h = width // 2, height // 2
        canvas_size = (120 + 3 * width, 100 + 2 * height)
        canvas = Image.new("RGBA", canvas_size, PALETTE_WHITE)
        # 在画布上绘制每张塔罗牌图片和对应的文字
        canvas = self._draw_single_image(canvas, images[0], "身体", (30 + 1 * half_w, 60 + 3 * half_h))
        canvas = self._draw_single_image(canvas, images[1], "心灵", (90 + 5 * half_w, 60 + 3 * half_h))
        canvas = self._draw_single_image(canvas, images[2], "灵魂", (60 + 3 * half_w, 20 + 1 * half_h))
        canvas = self._draw_single_image(canvas, images[3], "【阴影】", (60 + 3 * half_w, 60 + 3 * half_h))
        return canvas  # 返回绘制好的画布


# 钻石展开牌阵
class DiamondSpread(TarotSpreads):
    """钻石展开牌阵"""

    description = "占卜当前的情况、挑战、过去、未来和结果"
    meaning = [
        "第一张牌代表着当前的情况",
        "第二张牌代表着即将遇到的问题，正位表示过度，逆位表示不足",
        "第三张牌代表着即将遇到的问题，正位表示过度，逆位表示不足",
        "第四张牌代表着未来的结果",
    ]

    def draw_cards(self, num=4):
        super().draw_cards(4)

    def get_image(self) -> Image.Image:
        images = self._get_images()  # 获取抽取的塔罗牌图片
        # 创建画布
        width, height = images[0].size
        half_w, half_h = width // 2, height // 2
        canvas_size = (120 + 3 * width, 60 + height * 5 // 2)
        canvas = Image.new("RGBA", canvas_size, PALETTE_WHITE)
        # 在画布上绘制每张塔罗牌图片和对应的文字
        canvas = self._draw_single_image(canvas, images[0], "当前", (60 + 3 * half_w, 20 + 4 * half_h))
        canvas = self._draw_single_image(canvas, images[1], "挑战1", (30 + 1 * half_w, 20 + 5 * half_h // 2))
        canvas = self._draw_single_image(canvas, images[2], "挑战2", (90 + 5 * half_w, 20 + 5 * half_h // 2))
        canvas = self._draw_single_image(canvas, images[3], "结果", (60 + 3 * half_w, 20 + 1 * half_h))
        return canvas  # 返回绘制好的画布


# 四元素牌阵
class FourElementsSpread(TarotSpreads):
    """四元素牌阵"""

    description = "对问题进行全面而深入探索"
    meaning = [
        "第一张牌代表火，火象征行动\n这张牌主要是提供给你行动上的建议",
        "第二张牌代表风，风象征言语、沟通\n这张牌的位置在建议你言语上应该采取的对策",
        "第三张牌代表水，水象征情绪、感情\n这张牌建议你在感情层次上应该采取的态度为何",
        "第四张牌代表土，土象征实际物质、金钱\n这张牌在告诉你物质方面应该如何处理",
    ]

    def draw_cards(self, num=4):
        super().draw_cards(4)

    def get_image(self) -> Image.Image:
        images = self._get_images()  # 获取抽取的塔罗牌图片
        # 创建画布
        width, height = images[0].size
        half_w, half_h = width // 2, height // 2
        canvas_size = (90 + 2 * width, 100 + 2 * height)
        canvas = Image.new("RGBA", canvas_size, PALETTE_WHITE)
        # 在画布上绘制每张塔罗牌图片和对应的文字
        canvas = self._draw_single_image(canvas, images[0], "1. 火", (30 + 1 * half_w, 20 + 1 * half_h))
        canvas = self._draw_single_image(canvas, images[1], "2. 风", (60 + 3 * half_w, 20 + 1 * half_h))
        canvas = self._draw_single_image(canvas, images[2], "3. 水", (60 + 3 * half_w, 60 + 3 * half_h))
        canvas = self._draw_single_image(canvas, images[3], "4. 土", (30 + 1 * half_w, 60 + 3 * half_h))
        return canvas  # 返回绘制好的画布


# 塔罗牌插件
class TarotCards(StandardPlugin):
    def __init__(self) -> None:
        self.userCooldown = {}  # 用户冷却时间
        self.pattern = re.compile(r"^\-(塔罗牌|占卜)\s+(.*)$")  # '-塔罗牌 [牌阵]' 或 '-占卜 [牌阵]'

    def judgeTrigger(self, msg: str, data) -> bool:
        match = self.pattern.match(msg)
        if not match:
            return False
        if match.group(2) in TAROT_SPREAD:  # 匹配塔罗牌抽卡
            return True
        else:  # 匹配塔罗牌抽卡，但牌阵不正确
            target_id = data["group_id"] if data["message_type"] == "group" else data["user_id"]
            message = f"[CQ:reply,id={data['message_id']}]牌阵错误，请使用以下牌阵：\n"
            for spread_name, spread in TAROT_SPREAD.items():
                message += f"- {spread_name}：{spread.description}\n"
            send(target_id, message, data["message_type"])
            return False

    def executeEvent(self, msg: str, data: Any) -> Union[None, str]:
        user_id = data["user_id"]
        group_id = data["group_id"] if data["message_type"] == "group" else 0
        target_id = group_id if data["message_type"] == "group" else user_id
        # 每个用户5分钟只能抽一次卡
        current_time = time.time()
        if user_id in self.userCooldown:
            last_time = self.userCooldown[user_id]
            if current_time - last_time < 300:  # 5min冷却时间
                send(target_id, f"[CQ:reply,id={data['message_id']}]每5min只能占卜一次哦~", data["message_type"])
                return "OK"
        # 占卜需要30金币
        if get_user_coins(user_id) < 30:
            send(
                target_id, f"[CQ:reply,id={data['message_id']}]金币不足，塔罗牌占卜需要30金币哦~", data["message_type"]
            )
            return "OK"
        update_user_coins(user_id, -30)  # 扣除30金币
        self.userCooldown[user_id] = current_time  # 更新冷却时间并开始占卜

        # Begin tarot divine!
        spread = self.pattern.match(msg).group(2)  # 获取牌阵种类
        tarot_spread: TarotSpreads = TAROT_SPREAD[spread]()  # 实例化牌阵类
        tarot_spread.draw_cards()  # 抽取塔罗牌
        tarot_img = tarot_spread.get_image()  # 获取结果图片
        desc_card = tarot_spread.get_description()  # 获取结果描述

        # 组合结果并发送
        result_img = ResponseImage(
            theme="unicorn",
            title="塔罗牌占卜结果",
            titleColor=(165, 255, 255, 255),
        )
        result_img.addCard(  # 添加结果卡片
            ResponseImage.NoticeCard(
                title="占卜结果",
                subtitle=f"牌阵：{spread}",
                illustration=tarot_img,
            )
        )
        result_img.addCard(desc_card)  # 添加描述卡片
        img_path = os.path.join(ROOT_PATH, SAVE_TMP_PATH, f"tarot_{group_id}_{user_id}.png")
        result_img.generateImage(img_path)  # 生成结果图片
        send(target_id, f"[CQ:image,file=file:///{img_path}]", data["message_type"])
        return "OK"

    def getPluginInfo(self):
        return {
            "name": "TarotCards",
            "description": "消耗30金币进行塔罗牌占卜",
            "commandDescription": "'-塔罗牌 [牌阵]' 或 '-占卜 [牌阵]'",
            "usePlace": ["group", "private"],
            "showInHelp": True,
            "version": "1.0.0",
            "author": "Lonewiser",
        }


# 添加牌阵方法：继承 TarotSpreads 类并实现抽卡和获取图片方法，然后在这里注册
TAROT_SPREAD = {
    "单张": SingleCardSpread,
    "时间之流": TimeFlowSpread,
    "圣三角": HolyTriangleSpread,
    "二选一": TwoChoiceSpread,
    "身心灵": BodyMindSpiritSpread,
    "钻石展开": DiamondSpread,
    "四元素": FourElementsSpread,
    # '六芒星': '占卜事业的情况。',
    # '爱情金字塔': '占卜爱情的各个方面。',
    # '凯尔特十字': '抽取十张牌，提供全面的洞察和指导。',
}  # 塔罗牌牌阵字典

INFORMATION = json.load(open("./resources/tarot/card_information.json", "r", encoding="utf-8"))  # 塔罗牌信息字典

CARDS = list(INFORMATION.keys())  # 所有塔罗牌 List[str]

FONT_HYWH_18 = ImageFont.truetype(os.path.join(FONTS_PATH, "汉仪文黑.ttf"), 18)  # 塔罗牌文字字体
