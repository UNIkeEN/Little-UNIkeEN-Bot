from typing import Dict, Union, Any, List, Tuple, Optional
from utils.basicEvent import send, warning, parse_cqcode
from utils.standardPlugin import StandardPlugin
from utils.basicConfigs import ROOT_PATH, SAVE_TMP_PATH
from utils.responseImage_beta import PALETTE_RED, ResponseImage, PALETTE_CYAN, FONTS_PATH, ImageFont
import re, os.path, os
import requests
from utils.sqlUtils import newSqlSession
from .annImgBed import createAnnImgBedSql, dumpMsgToBed, imgUrlToImgBase64
from .muaTokenBind import getAllMuaToken
from .clientInstance import sendAnnouncement, deleteAnnouncement
from threading import Semaphore
import datetime, json, time
from dateutil import parser as timeparser
from .common.subprotocols import Announcement

def createAnnCtxSql():
    """创建mua通知发布过程中记录上下文环境的sql table
    """
    mydb, mycursor = newSqlSession()
    # token_description是MUA ID
    mycursor.execute("""
    create table if not exists `muaAnnCtx` (
        `user_id` bigint unsigned not null comment '发布者qq号',
        `ann_key` char(64) not null comment '活动标识主键，务必不含空字符',
        `create_time` timestamp not null comment '草稿创建时间',
        `title` varchar(100) default null comment '活动标题',
        `content` varchar(2000) default null comment '活动内容',
        `begin_time` timestamp default null comment '活动开始时间',
        `end_time` timestamp default null comment '活动结束时间',
        `info_source` varchar(100) default null comment '消息来源',
        `tag` varchar(200) default null comment '筛选标签，关键字以空格隔开', 
        `target` varchar(200) default null comment '通知发送目标，关键字以空格隔开',
        `channel` varchar(200) default null comment '通知发布频道',
        `released_time` timestamp default null comment '通知发布时间',
        `editing` bool not null default false comment '是否正在编辑',
        `token_description` char(20) default null comment '发布MUA ID',
        `metadata` json default null comment '其他信息，如群筛选器等，json格式',
        `aid` bigint default null comment '发通知成功后mua服务器返回的aid',
        primary key (`user_id`, `ann_key`)
    )charset=utf8mb4, collate=utf8mb4_unicode_ci;""")

def recordAidWhenSucc(aid:int, data:Any):
    """如果成功发送通知，服务器返回"RESULT" pay_load，此时需要恢复上下文，
    记录发送通知的aid、记录通知的released_time、将通知editing设为False
    
    @aid:  mua服务器返回的通知aid
    @data: 恢复出来的上下文环境
    """
    mydb, mycursor = newSqlSession()
    mycursor.execute("""update `muaAnnCtx` set
    `editing` = false, `aid` = %s, `released_time` = from_unixtime(%s)
    where user_id = %s and ann_key = %s
    """, (aid, data['time'], data['user_id'], data['ann_key']))
    result = MuaAnnEditor.getContext(data['user_id'])
    if result != None and result[0] == data['ann_key']:
        MuaAnnEditor.setContext(data['user_id'], data['ann_key'], False)


def loadAnnContext(userId:int, annKey:str)->Optional[Dict[str, Any]]:
    mydb, mycursor = newSqlSession()
    # token_description是MUA ID
    mycursor.execute("""
    select `user_id`, `ann_key`, unix_timestamp(`create_time`),
    `title`, `content`, unix_timestamp(`begin_time`), unix_timestamp(`end_time`),
    `info_source`, `tag`, unix_timestamp(`released_time`), `token_description`, 
    `metadata`, `channel`, `target`
    from `muaAnnCtx` where `user_id` = %s and `ann_key` = %s
    """, (userId, annKey))
    result = list(mycursor)
    if len(result) == 0:
        return None
    result = result[0]
    return {
        'user_id': result[0],
        'ann_key': result[1],
        'create_time': result[2],
        'title': result[3],
        'content': result[4],
        'begin_time': result[5],
        'end_time': result[6],
        'info_source': result[7],
        'tag': result[8],
        'released_time': result[9],
        'token_description': result[10],
        'metadata': result[11],
        'channel': result[12],
        'target': result[13]
    }

def makeContent(content:Optional[str])->List[Tuple[str, str]]:
    """将文字、图片CQ码混合的content转换为mua ann协议约定的content
    """
    if content == None: return []
    cqcodePattern = re.compile(r'\[CQ\:[^\[\]\s]+\]')
    cqcodes = cqcodePattern.findall(content)
    words = cqcodePattern.split(content)
    imgs = []
    for cqcode in cqcodes:
        cqtype, cqdict = parse_cqcode(cqcode)
        if cqtype != 'image':
            raise Exception('unsupported content type')
        url = cqdict['url']
        if requests.get(url=url).status_code == requests.codes.ok:
            imgs.append(['imgurl', url])
        else:
            b64img = imgUrlToImgBase64(url)
            if b64img == None:
                raise Exception('过期的图片')
            imgs.append(['imgbase64', b64img])
    content = []
    imgsIdx, wordsIdx = 0, 0
    while wordsIdx < len(words) and imgsIdx < len(imgs):
        if len(words[wordsIdx]) > 0:
            content.append(['text', words[wordsIdx]])
        content.append(imgs[imgsIdx])
        imgsIdx += 1
        wordsIdx += 1
    while wordsIdx < len(words):
        if len(words[wordsIdx]) > 0:
            content.append(['text', words[wordsIdx]])
        wordsIdx += 1
    return content
                
def makeTag(tag:Optional[str])->Optional[List[str]]:
    if tag == None:
        return None
    else:
        return tag.strip().split()

def makeTarget(target:Optional[str])->Optional[List[str]]:
    if target == None:
        return None
    else:
        return target.strip().split()

def drawHelpPic(savePath:str)->bool:
    """绘制faq帮助
    @savePath:  图片存储位置
    @return:    是否保存成功
    """
    helpWords = (
        "新建通知： -annnew  [通知关键字]\n"
        "删除通知本地记录： -annrm  [通知关键字]\n"
        "删除mua服务器上的通知： -anndel  [通知关键字]\n"
        "获取当前编辑通知的关键字： -annkey\n"
        "获取所有未被删除的通知： -annls\n"
        "复制之前通知的内容到新通知，并切换到新通知： -anncp  [前通知关键字]  [新通知关键字]\n"
        "切换到新通知： -annswt  [通知关键字]\n"
        "设置通知title： -annttl  [文字]\n"
        "将一段内容添加到content末尾： -annctt  [文字/图片]\n"
        "清空content： -annrmctt\n"
        "设置tag： -anntg  [tag,以空格隔开]\n"
        "设置channel： -anncnl  [channel文字]\n"
        "设置通信target： -anntgt  [target,以空格隔开]\n"
        # "设置活动开始时间： -annstt  [时间字符串 like '2023-07-30 23:59']\n"
        "设置结束(过期)时间： -annstp  [时间字符串 like '2023-07-30 23:59']\n"
        "设置发布身份： -anntk  [MUA ID]\n"
        "预览通知： -annprv\n"
        "发布通知： -annrls\n"
        "获取帮助： -annhelp\n"
        "测试用：   -anndmp [关键字]?\n"
        "【注】\n"
        "1. 通知关键字不能与之前通知（未删除）的关键字相同，不能包含空格或换行等空字符，长度限制在64字符内\n"
        "2. 通知title长度限制在100字符内\n"
        "3. tag关键字间以空格隔开，总长度限制在200字符内\n"
        "4. content长度限制在2000字符内\n"
    )
    helpCards = ResponseImage(
        title = 'MUA 通知发布帮助', 
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
    return True

class MuaAnnHelper(StandardPlugin):
    def judgeTrigger(self, msg:str, data:Any) -> bool:
        return msg in ['-annhelp', ]
    def executeEvent(self, msg: str, data: Any) -> Union[None, str]:
        target = data['group_id'] if data['message_type']=='group' else data['user_id']
        savePath = os.path.join(ROOT_PATH, SAVE_TMP_PATH, 'muahelp_%d.png'%target)
        if drawHelpPic(savePath):
            send(target, '[CQ:image,file=file:///%s]'%savePath, data['message_type'])
        else:
            send(target, '[CQ:reply,id=%d]帮助生成失败'%data['message_id'], data['message_type'])
        return "OK"
    def getPluginInfo(self)->Any:
        return {
            'name': 'MuaAnnHelper',
            'description': 'MUA通知发布帮助',
            'commandDescription': '-annhelp',
            'usePlace': ['group', 'private'],
            'showInHelp': True,
            'pluginConfigTableNames': [],
            'version': '1.0.0',
            'author': 'Unicorn',
        }

def parseTimeStr(timeStr:str)->Optional[datetime.datetime]:
    try:
        return timeparser.parse(timeStr)
    except:
        return None

class MuaAnnEditor(StandardPlugin):
    initGuard = Semaphore()
    # 用户ID => [当前正在编辑的通知key, 是否可编辑]
    context:Dict[int, Tuple[str, bool]] = {} # 私聊、群聊共享一个
    @staticmethod
    def getContext(userId:int)->Optional[Tuple[str, bool]]:
        return MuaAnnEditor.context.get(userId, None)

    @staticmethod
    def setContext(userId:int, editingAnnName:str, editing:bool):
        MuaAnnEditor.context[userId] = (editingAnnName, editing)

    def __init__(self):
        if self.initGuard.acquire(blocking=False):
            createAnnCtxSql()
            createAnnImgBedSql()
            self.loadContext()
        self.annnewPattern = re.compile(r'^\-annnew\s+(\S+)')
        self.annrmPattern  = re.compile(r'^\-annrm\s+(\S+)')
        self.anndelPattern  = re.compile(r'^\-anndel\s+(\S+)')
        self.anncpPattern  = re.compile(r'^\-anncp\s+(\S+)\s+(\S+)')
        self.annswtPattern = re.compile(r'^\-annswt\s+(\S+)')
        self.annttlPattern = re.compile(r'^\-annttl\s+(.*)', re.DOTALL)
        self.anncttPattern = re.compile(r'^\-annctt\s+(.*)', re.DOTALL)
        self.anntgPattern  = re.compile(r'^\-anntg\s+(.*)')
        self.anntgtPattern = re.compile(r'^\-anntgt\s+(.*)')
        self.anncnlPattern = re.compile(r'^\-anncnl\s+(.*)')
        self.annsttPattern = re.compile(r'^\-annstt\s+(.*)')
        self.annstpPattern = re.compile(r'^\-annstp\s+(.*)')
        self.anntkPattern = re.compile(r'^\-anntk\s+(\S+)')
        self.cqcodePattern = re.compile(r'\[CQ\:.*\]')

    def loadContext(self):
        mydb, mycursor = newSqlSession()
        mycursor.execute("""
        select `user_id`, `ann_key`, `released_time` from `muaAnnCtx` where `editing` = true;
        """)
        for userId, annKey, releasedTime in list(mycursor):
            self.context[userId] = (annKey, releasedTime == None)

    def judgeTrigger(self, msg:str, data:Any) -> bool:
        return msg.startswith('-ann')

    def executeEvent(self, msg: str, data: Any) -> Union[None, str]:
        target = data['group_id'] if data['message_type']=='group' else data['user_id']
        userId = data['user_id']
        if msg == '-annkey':
            annKey = self.context.get(userId, None)
            if annKey == None:
                send(target, '[CQ:reply,id=%d]当前没有正在编辑的通知'%data['message_id'], data['message_type'])
            else:
                send(target, '[CQ:reply,id=%d]当前通知的关键字为“%s”, %s'%(data['message_id'],
                annKey[0], '未发布可编辑' if annKey[1] else '已发布不可编辑'), data['message_type'])
        elif msg == '-annls':
            succ, result = self.annLs(userId, data)
            send(target, '[CQ:reply,id=%d]%s'%(data['message_id'], result), data['message_type'])
        elif msg == '-annrmctt':
            succ, result = self.annRmctt(userId, data)
            send(target, '[CQ:reply,id=%d]%s'%(data['message_id'], result), data['message_type'])
        elif msg == '-annprv':
            succ, result = self.annPrv(userId, data)
            send(target, result, data['message_type'])
        elif msg == '-annrls':
            succ, result  = self.annRls(userId, data)
            if not succ:
                send(target, '[CQ:reply,id=%d]%s'%(data['message_id'], result), data['message_type'])
        elif msg == '-annhelp':
            savePath = os.path.join(ROOT_PATH, SAVE_TMP_PATH, 'muahelp_%d.png'%target)
            if drawHelpPic(savePath):
                send(target, '[CQ:image,file=file:///%s]'%savePath, data['message_type'])
            else:
                send(target, '[CQ:reply,id=%d]帮助生成失败'%data['message_id'], data['message_type'])
        elif msg == '-anndmp':
            succ, result = self.annDmp(userId, None, data)
            if succ:
                send(target, '[CQ:reply,id=%d]OK'%(data['message_id'], ), data['message_type'])
                with open(os.path.join(ROOT_PATH, SAVE_TMP_PATH, 'anndmp.json'), 'w') as f:
                    f.write(result)
            else:
                send(target, '[CQ:reply,id=%d]%s'%(data['message_id'], result), data['message_type'])
        elif self.anntkPattern.match(msg) != None:
            tokenDescription = self.anntkPattern.findall(msg)[0]
            succ, result  = self.annTk(userId, tokenDescription, data)
            send(target, '[CQ:reply,id=%d]%s'%(data['message_id'], result), data['message_type'])
        elif self.annnewPattern.match(msg) != None:
            annKey = self.annnewPattern.findall(msg)[0]
            succ, result = self.annNew(userId, annKey, data)
            send(target, '[CQ:reply,id=%d]%s'%(data['message_id'], result), data['message_type'])
        elif self.annrmPattern.match(msg) != None:
            annKey = self.annrmPattern.findall(msg)[0]
            succ, result = self.annRm(userId, annKey, data)
            send(target, '[CQ:reply,id=%d]%s'%(data['message_id'], result), data['message_type'])
        elif self.anndelPattern.match(msg) != None:
            annKey = self.anndelPattern.findall(msg)[0]
            succ, result = self.annDel(userId, annKey, data)
            send(target, '[CQ:reply,id=%d]%s'%(data['message_id'], result), data['message_type'])
        elif self.anntgtPattern.match(msg) != None:
            tgt = self.anntgtPattern.findall(msg)[0]
            succ, result = self.annTgt(userId, tgt, data)
            send(target, '[CQ:reply,id=%d]%s'%(data['message_id'], result), data['message_type'])
        elif self.anncpPattern.match(msg) != None:
            srcKey, dstKey = self.anncpPattern.findall(msg)[0]
            succ, result = self.annCp(userId, srcKey, dstKey, data)
            send(target, '[CQ:reply,id=%d]%s'%(data['message_id'], result), data['message_type'])
        elif self.annswtPattern.match(msg) != None:
            annKey = self.annswtPattern.findall(msg)[0]
            succ, result = self.annSwt(userId, annKey, data)
            send(target, '[CQ:reply,id=%d]%s'%(data['message_id'], result), data['message_type'])
        elif self.annttlPattern.match(msg) != None:
            title = self.annttlPattern.findall(msg)[0]
            succ, result = self.annTtl(userId, title, data)
            send(target, '[CQ:reply,id=%d]%s'%(data['message_id'], result), data['message_type'])
        elif self.anncttPattern.match(msg) != None:
            content = self.anncttPattern.findall(msg)[0]
            succ, result = self.annCtt(userId, content, data)
            send(target, '[CQ:reply,id=%d]%s'%(data['message_id'], result), data['message_type'])
        elif self.anncnlPattern.match(msg) != None:
            channel = self.anncnlPattern.findall(msg)[0]
            succ, result = self.annCnl(userId, channel, data)
            send(target, '[CQ:reply,id=%d]%s'%(data['message_id'], result), data['message_type'])
        elif self.anntgPattern.match(msg) != None:
            tag = self.anntgPattern.findall(msg)[0]
            succ, result = self.annTg(userId, tag, data)
            send(target, '[CQ:reply,id=%d]%s'%(data['message_id'], result), data['message_type'])
        elif self.annsttPattern.match(msg) != None:
            timestr = self.annsttPattern.findall(msg)[0]
            succ, result = self.annStt(userId, timestr, data)
            send(target, '[CQ:reply,id=%d]%s'%(data['message_id'], result), data['message_type'])
        elif self.annstpPattern.match(msg) != None:
            timestr = self.annstpPattern.findall(msg)[0]
            succ, result = self.annStp(userId, timestr, data)
            send(target, '[CQ:reply,id=%d]%s'%(data['message_id'], result), data['message_type'])
        else:
            send(target, '[CQ:reply,id=%d]指令识别失败，请发送-annhelp获取帮助'%data['message_id'], data['message_type'])

        return "OK"

    def getPluginInfo(self)->Any:
        return {
            'name': 'MuaAnnEditor',
            'description': 'MUA通知助手',
            'commandDescription': '-annxxx ...',
            'usePlace': ['group', 'private'],
            'showInHelp': True,
            'pluginConfigTableNames': ['muaAnnCtx','muaAnnImgbed'],
            'version': '1.0.0',
            'author': 'Unicorn',
        }

    def annDmp(self, userId:int, annKey: Optional[str], data:Any)->Tuple[bool, str]:
        if annKey == None:
            curKey = self.context.get(userId, None)
            if curKey == None: return False, '没有给关键词且当前没有正在编辑的通知'
            annKey = curKey[0]
        result = loadAnnContext(userId, annKey)
        if result == None:
            return False, '关键词不存在或数据库错误'
        else:
            # print(result)
            print(json.dumps(result, ensure_ascii=False))
            return True, json.dumps(result, ensure_ascii=False)

    def annNew(self, userId:int, annKey: str, data:Any)->Tuple[bool, str]:
        if len(annKey) > 64:
            return False, '创建失败，关键词过长'
        try:
            mydb, mycursor = newSqlSession()
            mycursor.execute("""
            update `muaAnnCtx` set `editing` = false
            where `user_id` = %d and `editing` = true"""%(userId, ))
            try:
                mycursor.execute("""insert into `muaAnnCtx` 
                (`user_id`, `ann_key`, `create_time`, `editing`) values
                (%s, %s, from_unixtime(%s), true)""",
                (userId, annKey, data['time']))
                self.context[userId] = (annKey, True)
            except BaseException as e:
                print(e)
                return False, '创建失败，关键词重复或数据库错误'
            return True, ('创建成功，发送“-anntk MUAID”可为通知绑定发布身份的MUAID(若不清楚MUAID名称，发送“-muals”可获取已注册的MUAID)，'
            '绑定完MUAID后，请发送“-anncnl 目标频道”设置频道（原版/模组/小游戏/其他）')
        except BaseException as e:
            warning('exception in MuaAnnEditor.annNew: {}'.format(e))
            return False, '创建失败'

    def annRm(self, userId:int, annKey:str, data:Any)->Tuple[bool, str]:
        mydb, mycursor = newSqlSession()
        mycursor.execute("""
        select count(*) from `muaAnnCtx` 
        where user_id = %s and ann_key = %s
        """, (userId, annKey))
        result = list(mycursor)
        if result[0][0] == 0:
            return False, '删除失败，不存在该关键字'
        mycursor.execute("""
        delete from `muaAnnCtx` 
        where user_id = %s and ann_key = %s
        """, (userId, annKey))
        if userId in self.context.keys() and self.context[userId][0] == annKey:
            del self.context[userId]
        return True, '本地记录删除成功'

    def annDel(self, userId:int, annKey:str, data:Any)->Tuple[bool, str]:
        mydb, mycursor = newSqlSession()
        mycursor.execute("""
        select `aid`, `token_description` from `muaAnnCtx` 
        where user_id = %s and ann_key = %s
        """, (userId, annKey))
        result = list(mycursor)
        if len(result) == 0:
            return False, '删除失败，不存在该关键字'
        aid, tokenDescription = result[0]
        if aid == None:
            return False, '服务器未存储aid，该announcement之前可能未发送成功，如果已发送成功，请联系管理员解决该bug'
        if tokenDescription == None:
            return False, '该通知未存储MUA ID，请联系管理员解决该bug'
        tokens = getAllMuaToken(userId)
        if tokenDescription not in tokens.keys():
            return False, '发送信息时的token已被移除，请重新绑定该token'
        succ, result = deleteAnnouncement(aid, tokens[tokenDescription])
        return succ, result

    def annLs(self, userId:int, data:Any)->Tuple[bool, str]:
        try:
            mydb, mycursor = newSqlSession()
            mycursor.execute("""
            select `ann_key` from `muaAnnCtx`
            where `user_id` = %d"""%(userId, ))
            result = [annKey for annKey, in list(mycursor)]
            return True, '读取成功，往期关键字为：\n' + ', '.join(result)
        except BaseException as e:
            warning('exception in MuaAnnEditor.annLs: {}'.format(e))
            return False, '读取失败，数据库错误'

    def annSwt(self, userId:int, annKey:str, data:Any)->Tuple[bool, str]:
        curKey = self.context.get(userId, None)
        if curKey != None and annKey == curKey[0]:
            return True, '正在编辑该通知，无需切换'
        mydb, mycursor = newSqlSession()
        mycursor.execute("""
        select released_time from `muaAnnCtx` where
        user_id = %s and ann_key = %s""",(userId, annKey))
        result = list(mycursor)
        if len(result) == 0:
            return False, '切换失败，不存在以“%s”为关键词的通知'%annKey
        released = result[0][0] != None
        mycursor.execute("""update `muaAnnCtx` set
        `editing` = false where `user_id` = %s and `editing` = true""",(userId, ))
        mycursor.execute("""update `muaAnnCtx` set
        `editing` = true where `user_id` = %s and `ann_key` = %s
        """, (userId, annKey))
        self.context[userId] = (annKey, not released)
        if released:
            return True, ('切换成功，请注意该通知已经发布，无法修改，'
            '如需修改，请用“-anncp %s 新通知”命令将该通知复制到新通知，然后编辑发布'%annKey)
        else:
            return False, '切换成功'

    def annCtt(self, userId:int, content:str, data:Any)->Tuple[bool, str]:
        annKey:Tuple[str, bool] = self.context.get(userId, None)
        if annKey == None:
            return False, 'content删除失败，当前没有正在编辑的通知'
        if not annKey[1]:
            return False, ('content删除失败，当前通知已发布，无法编辑，'
            '如需修改，请用-anncp命令将该通知复制到新通知，然后编辑发布')
        annKey:str = annKey[0]
        dumpMsgToBed(content)
        cqcodes = self.cqcodePattern.findall(content)
        words = self.cqcodePattern.split(content)
        for cqcode in cqcodes:
            print(cqcode)
            cqtype, cqdict = parse_cqcode(cqcode)
            if cqtype != 'image':
                return False, 'content设置失败，检测到非图片CQ码，请确保title不含除图片外的at、QQ表情、语音等成分'
            if 'url' not in cqdict.keys():
                return False, '图片格式识别失败，请联系管理员'
            url = cqdict['url']

        try:
            mydb, mycursor = newSqlSession()
            mycursor.execute("""update `muaAnnCtx` set
            `content` = if(`content` is null, %s, concat(`content`, %s)) where `user_id` = %s and `ann_key` = %s
            """, (content, content, userId, annKey))
            return True, ('content添加成功，可以继续发送“-annctt 内容”往现有内容后面添加新图文（不会覆盖），'
            '也可以发送“-annrmctt”清空通知内容。内容编辑完成后，请发送“-annstp 失效时间字符串”设置失效时间，'
            '若不设置失效时间，则默认失效时间为15天')
        except BaseException as e:
            return False, 'content添加失败，数据库错误或字数超限'

    def annRmctt(self, userId:int, data:Any)->Tuple[bool, str]:
        annKey:Tuple[str, bool] = self.context.get(userId, None)
        if annKey == None:
            return False, 'content删除失败，当前没有正在编辑的通知'
        if not annKey[1]:
            return False, ('content删除失败，当前通知已发布，无法编辑，'
            '如需修改，请用-anncp命令将该通知复制到新通知，然后编辑发布')
        annKey:str = annKey[0]
        try:
            mydb, mycursor = newSqlSession()
            mycursor.execute("""update `muaAnnCtx` set
            `content` = null where `user_id` = %s and `ann_key` = %s
            """, (userId, annKey))
            return True, ('通知内容已清空')
        except BaseException as e:
            return False, 'content删除失败，数据库错误'
    
    def annCp(self, userId:int, srcKey:str, dstKey:str, data:Any)->Tuple[bool, str]:
        mydb, mycursor = newSqlSession()
        # 1. 看dstKey是不是被占用了
        mycursor.execute("""select count(*) from `muaAnnCtx`
        where user_id = %s and ann_key = %s""", (userId, dstKey))
        if list(mycursor)[0][0] > 0 :
            return False, '关键词“%s”被占用，请用-annrm删掉之前的通知(-annrm只会删除本地记录，不会请求服务器删除)，或换一个没有被占用的关键词'%dstKey
        # 2. 读取
        mycursor.execute("""select `title`, `content`, `begin_time`, `end_time`, `info_source`,
        `tag`, `target`, `channel`, `token_description`, `metadata` from
        `muaAnnCtx` where `user_id` = %s and `ann_key` = %s
        """, (userId, srcKey))
        result = list(mycursor)
        if len(result) == 0:
            return False, '您还没有创建过以“%s”为关键词的通知，或者该通知已被移除'%srcKey
        result = result[0]
        # 3. editing写入
        mycursor.execute("""
        update `muaAnnCtx` set `editing` = false where
        `user_id` = %s and `editing` = true""", (userId, ))
        # 4. 写入
        mycursor.execute("""insert into `muaAnnCtx` (
            `user_id`, `ann_key`,
            `title`, `content`, `begin_time`, `end_time`, `info_source`,
            `tag`, `target`, `channel`, `token_description`, `metadata`,
            `editing`, `create_time`
        ) values (
            %s,%s,
            %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s,
            true, from_unixtime(%s)
        )""", (userId, dstKey,
            result[0], result[1], result[2], result[3], result[4], 
            result[5], result[6], result[7], result[8], result[9], 
            data['time'],
        ))
        # 5. 修改内存
        self.context[userId] = (dstKey, True)
        return True, '复制成功，输入“-annprv”可预览，输入“-annrls”可发布'

    def annTtl(self, userId:int, title:str, data:Any)->Tuple[bool, str]:
        annKey:Tuple[str, bool] = self.context.get(userId, None)
        if annKey == None:
            return False, 'title设置失败，当前没有正在编辑的通知'
        if not annKey[1]:
            return False, ('title设置失败，当前通知已发布，无法编辑，'
            '如需修改，请用-anncp命令将该通知复制到新通知，然后编辑发布')
        annKey:str = annKey[0]
        if len(title) > 100:
            return False, 'title设置失败，title总长度超出100字符'
        if self.cqcodePattern.match(title) != None:
            return False, 'title设置失败，检测到CQ码，请确保title不含at、QQ表情、图片、语音等成分'
        try:
            mydb, mycursor = newSqlSession()
            mycursor.execute("""update `muaAnnCtx` set
            `title` = %s where `user_id` = %s and `ann_key` = %s
            """, (title, userId, annKey))
            return True, 'title设置成功，发送“-anntg 标签(不同标签以空格隔开)”可以编辑通知标签，发送“-annctt 内容”可以编辑通知内容'
        except BaseException as e:
            return False, 'title设置失败，数据库错误'

    def annCnl(self, userId:int, channel:str, data:Any)->Tuple[bool, str]:
        annKey:Tuple[str, bool] = self.context.get(userId, None)
        if annKey == None:
            return False, 'channel设置失败，当前没有正在编辑的通知'
        if not annKey[1]:
            return False, ('channel设置失败，当前通知已发布，无法编辑，'
            '如需修改，请用-anncp命令将该通知复制到新通知，然后编辑发布')
        annKey:str = annKey[0]
        if len(channel) > 200:
            return False, 'channel设置失败，channel总长度超出200字符'
        if self.cqcodePattern.match(channel) != None:
            return False, 'channel设置失败，检测到CQ码，请确保channel不含at、QQ表情、图片、语音等成分'
        try:
            mydb, mycursor = newSqlSession()
            mycursor.execute("""update `muaAnnCtx` set
            `channel` = %s where `user_id` = %s and `ann_key` = %s
            """, (channel, userId, annKey))
            return True, ('channel设置成功，请发送“-annttl 标题”编辑通知标题，'
            '发送“-anntg 标记”编辑通知标记，或者发送“-annctt 内容”编辑通知内容')
        except BaseException as e:
            return False, 'channel设置失败，数据库错误，请联系管理员解决该bug'

    def annTgt(self, userId:int, tgt:str, data:Any)->Tuple[bool, str]:
        # TODO: 为target设置引导
        annKey:Tuple[str, bool] = self.context.get(userId, None)
        if annKey == None:
            return False, 'target设置失败，当前没有正在编辑的通知'
        if not annKey[1]:
            return False, ('target设置失败，当前通知已发布，无法编辑，'
            '如需修改，请用-anncp命令将该通知复制到新通知，然后编辑发布')
        annKey:str = annKey[0]
        tgt = ' '.join(tgt.strip().split())
        if len(tgt) > 200:
            return False, 'target设置失败，target总长度超出200字符'
        try:
            mydb, mycursor = newSqlSession()
            mycursor.execute("""update `muaAnnCtx` set
            `target` = %s where `user_id` = %s and `ann_key` = %s
            """, (tgt, userId, annKey))
            return True, 'target设置成功'
        except BaseException as e:
            return False, 'target设置失败，数据库错误，请联系管理员解决该bug'

    def annTg(self, userId:int, tag:str, data:Any)->Tuple[bool, str]:
        annKey:Tuple[str, bool] = self.context.get(userId, None)
        if annKey == None:
            return False, 'tag设置失败，当前没有正在编辑的通知'
        if not annKey[1]:
            return False, ('tag设置失败，当前通知已发布，无法编辑，'
            '如需修改，请用-anncp命令将该通知复制到新通知，然后编辑发布')
        annKey:str = annKey[0]
        tag = ' '.join(tag.strip().split())
        if len(tag) > 200:
            return False, 'tag设置失败，tag总长度超出200字符'
        try:
            mydb, mycursor = newSqlSession()
            mycursor.execute("""update `muaAnnCtx` set
            `tag` = %s where `user_id` = %s and `ann_key` = %s
            """, (tag, userId, annKey))
            return True, ('tag设置成功，继续发送“-annctt 内容”可以编辑通知内容，'
            '发送“-annstp 截止时间字符串”可以编辑通知截止时间（如不编辑则默认15日）')
        except BaseException as e:
            return False, 'tag设置失败，数据库错误，请联系管理员解决该bug'

    def annStt(self, userId:int, timeStr:str, data:Any)->Tuple[bool, str]:
        timeParsed = parseTimeStr(timeStr)
        annKey:Tuple[str, bool] = self.context.get(userId, None)
        if annKey == None:
            return False, '开始时间设置失败，当前没有正在编辑的通知'
        if not annKey[1]:
            return False, ('开始时间设置失败，当前通知已发布，无法编辑，'
            '如需修改，请用-anncp命令将该通知复制到新通知，然后编辑发布')
        annKey:str = annKey[0]
        invalidTime=False
        if timeParsed == None:
            invalidTime = True
            timeParsed = None
        try:
            mydb, mycursor = newSqlSession()
            mycursor.execute("""update `muaAnnCtx` set
            `begin_time` = %s where `user_id` = %s and `ann_key` = %s
            """, (timeParsed, userId, annKey))
            if invalidTime:
                return False, '字符串解析失败，开始时间变为默认'
            else:
                return True, timeParsed.strftime('开始时间设置成功，为 %Y-%m-%d %H:%M:%S')
        except BaseException as e:
            print(e)
            return False, '开始时间设置失败，数据库错误'

    def annStp(self, userId:int, timeStr:str, data:Any)->Tuple[bool, str]:
        annKey:Tuple[str, bool] = self.context.get(userId, None)
        if annKey == None:
            return False, '结束时间设置失败，当前没有正在编辑的通知'
        if not annKey[1]:
            return False, ('结束时间设置失败，当前通知已发布，无法编辑，'
            '如需修改，请用-anncp命令将该通知复制到新通知，然后编辑发布')
        annKey:str = annKey[0]
        timeParsed = parseTimeStr(timeStr)
        invalidTime=False
        if timeParsed == None:
            invalidTime = True
            timeParsed = None
        try:
            mydb, mycursor = newSqlSession()
            mycursor.execute("""update `muaAnnCtx` set
            `end_time` = %s where `user_id` = %s and `ann_key` = %s
            """, (timeParsed, userId, annKey))
            if invalidTime:
                return False, '字符串解析失败，失效时间变为默认'
            else:
                return True, timeParsed.strftime('失效时间设置成功，为 %Y-%m-%d %H:%M:%S，发送“-annprv”可以预览通知，发送“-annrls”可以发布通知')
        except BaseException as e:
            print(e)
            return False, '结束时间设置失败，数据库错误'

    def annPrv(self, userId:int, data:Any)->Tuple[bool, str]:
        annKey:Tuple[str, bool] = self.context.get(userId, None)
        if annKey == None:
            return False, '预览失败，当前没有正在编辑的通知'
        annKey, editing = annKey
        result = loadAnnContext(userId, annKey)
        if result == None:
            return False, '读取失败'
        txt = result['ann_key']
        if editing:
            txt += ' [正在编辑]\n'
        else:
            txt += ' [已发布]\n'
        if result['title'] != None:
            txt += '标题：' + result['title'] + '\n\n'
        else:
            txt += '标题缺失\n\n'
        if result['content'] != None:
            txt += '正文：\n' + result['content'] + '\n\n'
        else:
            txt += '正文缺失\n\n'

        if result['channel'] != None:
            txt += 'channel: ' + result['channel'] + '\n'
        else:
            txt += 'channel缺失\n'
        if result['target'] != None:
            txt += 'target: ' + result['target'] + '\n'
        else:
            txt += 'target缺失\n'
        if result['tag'] != None:
            txt += 'tag: ' + result['tag']+'\n\n'
        else:
            txt += 'tag缺失\n\n'

        # if result['begin_time'] != None:
        #     txt += datetime.datetime.fromtimestamp(result['begin_time']).strftime('开始时间： %Y-%m-%d %H:%M:%S\n')
        # else:
        #     txt += '起始时间缺失\n'
        if result['end_time'] != None:
            txt += datetime.datetime.fromtimestamp(result['end_time']).strftime('结束时间： %Y-%m-%d %H:%M:%S\n\n')
        else:
            txt += '结束时间缺失\n\n'
        if result['token_description'] != None:
            txt += '发布MUA ID：' + result['token_description']
        else:
            txt += '发布token缺失'
        return True, txt

    def annTk(self, userId:int, tokenDescription:str, data:Any):
        if len(tokenDescription) > 20:
            return False, 'MUA ID应小于20字符'
        annKey:Tuple[str, bool] = self.context.get(userId, None)
        if annKey == None:
            return False, ('MUA ID设置失败，当前没有正在编辑的通知，'
            '请发送“-annnew 新通知关键字”创建新通知，或者发送“-anncp 已创建关键字 新通知关键字”从模板中复制新通知')
        if not annKey[1]:
            return False, ('MUA ID设置失败，当前通知已发布，无法编辑，'
            '如需修改，请用-anncp命令将该通知复制到新通知，然后编辑发布')
        annKey:str = annKey[0]
        allToken = getAllMuaToken(userId)
        if tokenDescription not in allToken:
            return False, f'绑定失败，您注册的所有MUA ID为：{"、".join(allToken)}，在其中没有发现名为“{tokenDescription}”的ID'
        try:
            mydb, mycursor = newSqlSession()
            mycursor.execute("""update `muaAnnCtx` set
            `token_description` = %s where `user_id` = %s and `ann_key` = %s
            """, (tokenDescription, userId, annKey))
            return True, ('MUA ID设置成功，请发送“-anncnl 目标频道”设置频道（原版/模组/小游戏/其他），'
            '继续发送“-annttl 标题内容”可以编辑通知标题')
        except BaseException as e:
            return False, 'MUA ID设置失败，数据库错误'

    def annRls(self, userId:int, data:Any)->Tuple[bool, str]:
        annKey:Tuple[str, bool] = self.context.get(userId, None)
        if annKey == None:
            return False, '发布失败，当前没有正在编辑的通知'
        if not annKey[1]:
            return False, ('发布失败，当前通知已发布，无法重新发布，'
            '如需重新发布，请用-anncp命令将该通知复制到新通知，然后编辑发布')
        annKey:str = annKey[0]
        # do some check
        result = loadAnnContext(userId, annKey)
        if result == None:
            return False, '数据库读取失败，请联系管理员'
        if result['token_description'] == None:
            return False, '发布失败，MUA ID未设置，请根据发布身份选择MUA ID，使用-anntk [..]语句设置'
        if result['title'] == None:
            return False, '发布失败，title未设置，请使用-annttl命令设置title'
        if result['channel'] == None:
            return False, '发布失败，channel未设置，请使用-anncnl命令设置channel'
        tokenDescription = result['token_description']
        tokens = getAllMuaToken(userId)
        if tokenDescription not in tokens.keys():
            return False, '未在bot本地找到MUA ID对应token，请用-muabind指令绑定token'
        token = tokens[tokenDescription]
        content = None
        try:
            content = makeContent(result['content'])
        except Exception as e:
            return False, str(e)
        announcement = Announcement(
            title=result['title'],
            content=content,
            author_token=token,
            channel=result['channel'],
            tags=makeTag(result['tag']),
            targets=makeTarget(result['target']),
            time_expires=result['end_time'],
            time_created=data['time'],
            meta=result['metadata'],
        )
        target = data['group_id'] if data['message_type']=='group' else data['user_id']
        send(target, '格式检查通过，等待mua服务器响应中。发送“-anndel 通知key”可以让mua服务器删除通知，发送“-annrm 通知key”可以在本地删除通知key（但不通知服务器删除）', data['message_type'])
        succ, result = sendAnnouncement(announcement, data, annKey)
        return succ, result

class MuaNotice(StandardPlugin):
    def judgeTrigger(self, msg:str, data:Any)->bool:
        return False
    def executeEvent(self, msg: str, data: Any) -> Union[None, str]:
        return None
    def getPluginInfo(self)->Any:
        return {
            'name': 'MuaNotice',
            'description': 'MUA通知广播',
            'commandDescription': '[-grpcfg驱动]',
            'usePlace': ['group',],
            'showInHelp': True,
            'pluginConfigTableNames': [],
            'version': '1.0.0',
            'author': 'Unicorn',
        }