from typing import List, Any, Union
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from utils.standardPlugin import StandardPlugin
from utils.basicConfigs import *
from utils.basicEventForGocqhttp import *
import os



default_font, font_size = Path(__file__).parent / "font" / "consola.ttf", 14
default_font = str(default_font)
util_draw = ImageDraw.Draw(Image.new("L", (1, 1)))

class drawCharPic(StandardPlugin):
    def judgeTrigger(self, msg:str, data:Any) -> bool:
        return msg in ['字符画', '字符头像']
    
    def executeEvent(self, msg:str, data:Any) -> Union[None, str]:
        picPath = charAvatar(data['user_id'])
        picPath = picPath if os.path.isabs(picPath) else os.path.join(ROOT_PATH, picPath)
        target = data['group_id'] if data['message_type']=='group' else data['user_id']
        send(target, f'[CQ:image,file=files://{picPath}]',data['message_type'])




def get_pic_text(qq_id:int, new_w: int = 700) -> str:
    """图片按灰度映射字符"""
    str_map = "@@$$&B88QMMGW##EE93SPPDOOU**==()+^,\"--''.     "
    n = len(str_map)
    img_avatar = Image.open(BytesIO(get_avatar_pic(qq_id)))
    w, h = img_avatar.size
    if w > new_w:
        img_avatar = img_avatar.resize((new_w, int(new_w * h / w)))
    else:
        img_avatar = img_avatar.resize((w, h // 2))

    s = ""
    for x in range(img_avatar.height):
        for y in range(img_avatar.width):
            gray_v = img_avatar.getpixel((y, x))
            s += str_map[int(n * (gray_v / 256))]
        s += "\n"

    return s

#大概是设置一些画图的参数吧
async def text_wh(
    font_filename, default_font_size: int, text: str
) -> tuple[ImageFont.FreeTypeFont, int, int]:
    ttfont = ImageFont.truetype(font_filename, default_font_size)
    try:
        w, h = ttfont.getsize_multiline(text.strip())
        return ttfont, w, h
    except AttributeError:
        bbox: tuple[int, int, int, int] = util_draw.multiline_textbbox((0, 0), text, font=ttfont)
        return ttfont, bbox[2], bbox[3]

#文字转图片，模仿signIn写了储存
async def text2img(text: str, qq_id:int):
    font, w, h = await text_wh(default_font, font_size, text)
    img = Image.new("L", (w, h), "#FFFFFF")
    draw = ImageDraw.Draw(img)
    draw.text((0,0), text, fill="#000000", font=font)
    save_path = os.path.join(SAVE_TMP_PATH, f"{qq_id}_text.png")
    img.save(save_path)
    return save_path

def charAvatar(qq_id:int):
    id= qq_id if isinstance(qq_id, int) else int(qq_id)
    s:str = get_pic_text(id)
    saved_path = text2img(s, id)
    return saved_path


