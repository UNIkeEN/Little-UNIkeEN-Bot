import requests
from typing import Optional, Dict, Any, List
from .game import Game
from PIL import Image, ImageDraw, ImageFont
from utils.responseImage_beta import FONT_SYHT_M24
from .move import Move
from utils.basicEvent import warning

def queryChessdb(fen:str)->Optional[List[Dict[str, Any]]]:
    url = 'https://www.chessdb.cn/chessdb.php'
    params = {
        'action': 'queryall',
        'learn': '1',
        'showall': '1',
        'board': fen
    }
    try:
        req = requests.get(url=url, params = params)
        if req.status_code != requests.codes.ok:
            return None
        else:
            txt = req.text.strip().split('|')
            actions = []
            for x in txt:
                x = x.split(',')
                action = {}
                for kv in x:
                    k, v = kv.split(':')
                    action[k.strip()] = v.strip()
                actions.append(action)
            return actions
    except BaseException as e:
        warning("error in queryChessdb: {}".format(e))
        return None
def drawChessdb(game:Game, imgPath:str)->bool:
    chessdb = queryChessdb(game.fen())
    if chessdb == None:
        return False
    font = FONT_SYHT_M24
    try:
        img = Image.new('RGB', (775 + 400, 975), (250, 250, 200))
        img.paste(Image.open(game.draw()), (0, 0))
        draw = ImageDraw.Draw(img)
        dx = 120
        dy = 30
        marginLeft = 775 + 80
        marginUp = 50
        y = marginUp - dy
        for idxX, txt in enumerate(['着法','分数','备注']):
            x = marginLeft + dx * idxX - font.getsize(txt)[0]// 2
            draw.text((x,y), txt, fill=(0, 0, 0),font=font)
        for idxY, action in enumerate(chessdb[:30]):
            y = marginUp + dy * idxY
            for idxX, txt in enumerate([Move.from_ucci(action['move']).chinese(game), 
                                        action['score'], 
                                        action['note']]):
                x = marginLeft + dx * idxX - font.getsize(txt)[0]// 2
                draw.text((x,y), txt, fill=(0, 0, 0),font=font)
        img.save(imgPath)
        return True
    except BaseException as e:
        warning("error in drawChessDb: {}".format(e))
        return False