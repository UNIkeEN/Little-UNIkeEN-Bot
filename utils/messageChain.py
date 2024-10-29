from typing import List, Dict, Optional,Any
import re, base64
from PIL import Image
from io import BytesIO
import requests
from utils.imageBed import uuidToImgPath, dumpUrlToBed, dumpImageToBed, getImgFromUrl

def messagePieceQuote(text:str)->str:
    if not isinstance(text, str):
        return text
    return text.replace('&','&amp;').replace('[','&#91;').replace(']','&#93;').replace(',','&#44;')

def messagePieceUnquote(text:str)->str:
    if not isinstance(text, str):
        return text
    return text.replace('&amp;', '&').replace('&#91;', '[').replace('&#93;', ']').replace('&#44;',',')
    
def messagePieceToCqcode(messagePiece:Dict[str,Any]):
    if messagePiece['type'] == 'text':
        return messagePiece['data']['text']
    return '[CQ:%s,%s]'%(messagePiece['type'],','.join(['%s=%s'%(
        messagePieceQuote(k),messagePieceQuote(v)) for k,v in messagePiece['data'].items()]))

def cqcodeToMessagePiece(cqcode:str)->Optional[Dict[str,Any]]:
    cqcodePattern = re.compile(r'^\[(CQ\:[^\[\]\s]+)\]$')
    cqtypePattern = re.compile(r'^CQ\:([^\[\]\s\,]+)$')
    result = cqcodePattern.findall(cqcode)
    if len(result) == 0:
        return None
    result = result[0].split(',')
    cqtype = cqtypePattern.findall(result[0])
    if len(cqtype) == 0: 
        return None
    cqtype = cqtype[0]
    cqdict = {}
    for r in result[1:]:
        r = r.split('=', 1)
        if len(r) != 2:
            return None
        cqkey, cqvalue = r
        cqdict[messagePieceUnquote(cqkey)] = messagePieceUnquote(cqvalue)
    return {
        'type': cqtype,
        'data': cqdict,
    }

def imgToBase64(imgPath:str)->str:
    img = Image.open(imgPath)
    imgData = BytesIO()
    img.save(imgData, format=img.format)
    b64img = base64.b64encode(imgData.getvalue()).decode('utf-8')
    return b64img

def urlImgToBase64(imgUrl:str)->Optional[str]:
    img = getImgFromUrl(imgUrl)
    if img == None: return None
    imgData = BytesIO()
    img.save(imgData, format=img.format)
    b64img = base64.b64encode(imgData.getvalue()).decode('utf-8')
    return b64img

def base64ToImg(b64:str)->Optional[Image.Image]:
    try:
        img = Image.open(BytesIO(base64.b64decode(base64_data)))
        return img
    except Exception:
        return None
    
lagrangeImgUrlPattern = re.compile(r'^https?\:\/\/multimedia\.nt\.qq\.com\.cn\/offpic\_new\/(\d+)\/+(\S+)$')
def fixLagrangeImgUrl(url:str)->str:
    result = lagrangeImgUrlPattern.findall(url)
    if len(result) == 0:
        return url
    group_id, res_url = result[0]
    url = 'https://gchat.qpic.cn/gchatpic_new/%s/%s'%(group_id, res_url)
    return url

class MessageChain():
    supportedCqcodes = [
        'text', 'image', 'face', 
        'forward', 'node'
    ]# for Lagrange.Core
    cqPattern = re.compile(r'(\[CQ\:[^\[]*\])')
    def __init__(self, chain:List[Dict[str,Any]]) -> None:
        self.chain:List[Dict[str,Any]] = chain

    @classmethod
    def fromCqcode(cls, cqcode:str)->'MessageChain':
        pieces = cls.cqPattern.split(cqcode)
        result = []
        for idx, text in enumerate(pieces):
            if len(text) == 0: continue
            isCqcode = (idx % 2) == 1
            if isCqcode:
                piece = cqcodeToMessagePiece(text)
                if piece == None:
                    continue
            else:
                piece = {
                    'type': 'text',
                    'data': {'text': text}
                }
            result.append(piece)
        return cls(result)
    def fixLagrangeImgUrl(self):
        new_chain = []
        for piece in self.chain:
            if piece['type'].lower() == 'image':
                if 'file' in piece['data'].keys():
                    path:str = piece['data'].pop('file')
                elif 'url' in piece['data'].keys():
                    path:str = piece['data'].pop('url')
                else:
                    new_chain.append(piece)
                    continue
                # path = fixLagrangeImgUrl(path)
                if path.startswith('http'):
                    piece['data']['url'] = path
                else:
                    piece['data']['file'] = path
            new_chain.append(piece)
        self.chain = new_chain
        
    def toCqcode(self)->str:
        result = []
        for piece in self.chain:
            result.append(messagePieceToCqcode(piece))
        return ''.join(result)
    
    def supportForLagrange(self)->bool:
        if not isinstance(self.chain, list):
            return False
        for item in self.chain:
            if not isinstance(item, dict):
                return False
            if 'data' not in item.keys():
                return False
            if item.get('type', None) not in self.supportedCqcodes:
                return False
        return True

    def removeUnsupportPiece(self):
        result = []
        for piece in self.chain:
            if piece['type'].lower() in self.supportedCqcodes:
                result.append(piece)
        self.chain = result

    def convertImgPathToBase64(self):
        self.convertBedUuidToPath()
        result = []
        for piece in self.chain:
            if piece['type'].lower() == 'image':
                if 'url' in piece['data'].keys():
                    url:str = piece['data'].pop('url')
                    b64 = urlImgToBase64(url)
                    if b64!=None:
                        piece['data']['file'] = 'base64://'+b64
                    else:
                        piece['data']['url'] = url
                elif 'file' in piece['data'].keys():
                    path:str = piece['data']['file']
                    if path.startswith('file:///'):
                        path = path[len('file:///'):]
                        b64 = imgToBase64(path)
                        piece['data']['file'] = 'base64://'+b64
                    elif path.startswith('http'):
                        b64 = urlImgToBase64(path)
                        if b64 != None:
                            piece['data']['file'] = 'base64://'+b64
            result.append(piece)
        self.chain = result
        
    def convertBedUuidToPath(self)->bool:
        result = []
        succFlag = True
        for piece in self.chain:
            if piece['type'].lower() == 'image':
                if 'imgbeduuid' in piece['data'].keys():
                    uuid:str = piece['data'].pop('imgbeduuid')
                    imgPath = uuidToImgPath(uuid)
                    if imgPath!=None:
                        piece['data']['file'] = 'file:///'+imgPath
                    else:
                        piece['data']['imagebeduuid'] = uuid # convert fails
                        succFlag = False
            result.append(piece)
        self.chain = result
        return succFlag
    
    def dumpImageToBed(self):
        result = []
        for piece in self.chain:
            if piece['type'].lower() == 'image':
                if 'url' in piece['data'].keys():
                    url:str = piece['data'].pop('url')
                    img = getImgFromUrl(url)
                    if img == None: 
                        piece['data']['url'] = url
                    else:
                        uuid = dumpImageToBed(img)
                        piece['data']['imgbeduuid'] = uuid
                elif 'file' in piece['data'].keys():
                    path:str = piece['data']['file']
                    if path.startswith('file:///'):
                        path = path[len('file:///'):]
                        img = Image.open(path)
                        uuid = dumpImageToBed(img)
                        piece['data']['imgbeduuid'] = uuid
                    elif path.startswith('http'):
                        url:str = path
                        img = getImgFromUrl(url)
                        if img == None: 
                            piece['data']['file'] = url
                        else:
                            uuid = dumpImageToBed(img)
                            piece['data']['imgbeduuid'] = uuid
                    elif path.startswith('base64://'):
                        b64 = path[len('base64://'):]
                        img = base64ToImg(b64)
                        if img == None:
                            piece['data']['file'] = path
                        else:
                            uuid = dumpImageToBed(img)
                            piece['data']['imgbeduuid'] = uuid
            result.append(piece)
        self.chain = result
    def __repr__(self) -> str:
        return str(self.chain)

if __name__ == '__main__':
    testCases = [
        '21[CQ:image,file=files://123]123123[CQ:reply,id=1]',
        '[CQ:at,qq=1234][CQ:at,qq=1234][][][][][CQ:at,qq=1234][CQ:at,qq=1234]',
        '[CQ:image,file=files://123]123123[CQ:reply,id=]12',
        '123[CQ:image,file=files://123]123123[CQ:reply,id=======]123',
    ]
    for testCase in testCases:
        chain = MessageChain.fromCqcode(testCase)
        print(chain.toCqcode() == testCase)
        print(testCase, chain.toCqcode())
        print(chain.chain)