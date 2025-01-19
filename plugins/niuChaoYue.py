import re, datetime, time
from typing import List, Dict, Any, Tuple, Optional, Union
from utils.basicEvent import warning, send
from utils.standardPlugin import StandardPlugin, CronStandardPlugin, NotPublishedException
from utils.sqlUtils import newSqlSession
from utils.basicConfigs import ROOT_PATH, SAVE_TMP_PATH
from utils.configAPI import getPluginEnabledGroups
from utils.responseImage_beta import *
try:
    from resources.api.sjtuCourseAPI import getCourses
except:
    raise NotPublishedException('sjtu course api not published')
    
def parseJxbmc(jxbmc:str)->Optional[Tuple[int,int,int,str,int]]:
    """parse jxbmc like '(2023-2024-2)-EE0503-11'"""
    jxbmcPattern = re.compile(r'^\((\d+)\-(\d+)\-(\d+)\)\-(\S+)\-(\d+)')
    if jxbmcPattern.match(jxbmc) == None:
        return None
    fromYear, toYear, semester, courseName, classNo = jxbmcPattern.findall(jxbmc)[0]
    return int(fromYear), int(toYear), int(semester), courseName, int(classNo)

def getNiuChaoYueCount( JAC_COOKIE:str, 
                        client_id:str, 
                        params:Dict[str, str],
                        data:Dict[str, str])->Optional[int]:
    courses = getCourses(JAC_COOKIE, client_id, params, data)
    if courses == None: return None
    for course in courses:
        jxbmc = parseJxbmc(course['jxbmc'])
        if jxbmc == None: continue
        _, _, _, courseName, classNo = jxbmc
        if classNo == 20:
            return course['xkrs'] # 选课人数
    return None

def drawNiuChaoYue(courses:List[Dict[str, Any]], savePath:str)->bool:
    targetClassNos = [13,18,24,20,23,19]
    results = []
    for course in courses:
        jxbmc = parseJxbmc(course['jxbmc'])
        if jxbmc == None: continue
        _, _, _, courseName, classNo = jxbmc
        if classNo not in targetClassNos: continue
        rkjs = course['rkjs'] # 任课教师
        xkrs = course['xkrs'] # 选课人数
        results.append((courseName, rkjs, xkrs))
    if len(results)==0: return False
    results = sorted(results, key=lambda x:x[2], reverse=True)
    maxNum = results[0][2]
    ncyCard = ResponseImage(
        titleColor = PALETTE_SJTU_BLUE,
        title = '牛哥到底行不行啊',
        layout = 'normal',
        width = 880,
        footer=datetime.datetime.now().strftime('更新于 %Y-%m-%d  %H:%M:%S'),
        cardBodyFont= ImageFont.truetype(os.path.join(FONTS_PATH, 'SourceHanSansCN-Medium.otf'), 24),
        cardSubtitleFont= ImageFont.truetype(os.path.join(FONTS_PATH, 'SourceHanSansCN-Medium.otf'), 30),
    )
    cardContent = []
    for courseName, rkjs, xkrs in results:
        cardContent.extend([
            ('subtitle', '%s  %s  选课人数： %d'%(courseName, rkjs, xkrs)),
            ('progressBar', xkrs/maxNum)
        ])
    ncyCard.addCard(
        ResponseImage.RichContentCard(
            raw_content=cardContent
        )
    )
    ncyCard.generateImage(savePath)
    return True

class GetNiuChaoYue(StandardPlugin):
    def __init__(self,
                 JAC_COOKIE:str, 
                 client_id:str, 
                 params:Dict[str, str],
                 data:Dict[str, str]):
        self.JAC_COOKIE = JAC_COOKIE
        self.client_id = client_id
        self.params = params
        self.data = data
        
    def judgeTrigger(self, msg: str, data: Any) -> bool:
        return msg in ['-ncy']
    
    def executeEvent(self, msg: str, data: Any) -> Optional[str]:
        target = data['group_id'] if data['message_type']=='group' else data['user_id']
        courses = getCourses(self.JAC_COOKIE, self.client_id, self.params, self.data)
        if courses == None:
            send(target, '课程信息更新失败', data['message_type'])
        else:
            savePath = os.path.join(ROOT_PATH,SAVE_TMP_PATH,'ncy.png')
            succ = drawNiuChaoYue(courses, savePath)
            if succ:
                send(target, '[CQ:image,file=file:///{}]'.format(savePath), data['message_type'])
            else:
                send(target, '课程内容解析失败', data['message_type'])
        return 'OK'
    def getPluginInfo(self) -> dict:
        return {
            'name': 'GetNiuChaoYue',
            'description': '获取牛哥选课情况',
            'commandDescription': '-ncy',
            'usePlace': ['group', 'private', ],
            'showInHelp': True,
            'pluginConfigTableNames': [],
            'version': '1.0.0',
            'author': 'Unicorn',
        }
        
def createNiuChaoYueSql():
    mydb, mycursor = newSqlSession()
    mycursor.execute("""create table if not exists `niuChaoYueCount` (
        `id` bigint unsigned not null auto_increment,
        `count` int not null,
        `time` timestamp default null,
        primary key (`id`)
    )""")
    
def writeNiuChaoYueCount(count:int):
    mydb, mycursor = newSqlSession()
    mycursor.execute('''insert into `niuChaoYueCount`
                     (`count`, `time`) values (%s, %s)''', (count, datetime.datetime.now()))
    
def getPrevCount()->Optional[int]:
    mydb, mycursor = newSqlSession()
    mycursor.execute("""select `count` from `niuChaoYueCount` order by `id` desc limit 1""")
    result = list(mycursor)
    if len(result)>0:
        return result[0][0]
    return None

class NiuChaoYueMonitor(StandardPlugin,CronStandardPlugin):
    initGuard = True
    def __init__(self,
                 JAC_COOKIE:str, 
                 client_id:str, 
                 params:Dict[str, str],
                 data:Dict[str, str]) -> None:
        self.failCount = 0
        self.job = None
        if self.initGuard:
            self.initGuard = False
            createNiuChaoYueSql()
            self.job = self.start(0, 60)
        self.JAC_COOKIE = JAC_COOKIE
        self.client_id = client_id
        self.params = params
        self.data = data
        
    def judgeTrigger(self, msg: str, data: Any) -> bool:
        return False
    def executeEvent(self, msg: str, data: Any) -> Optional[str]:
        return None
    def tick(self) -> None:
        ncyCount = getNiuChaoYueCount(self.JAC_COOKIE, self.client_id, self.params, self.data)
        if ncyCount == None: 
            self.failCount += 1
            if self.failCount > 3:
                for groupId in getPluginEnabledGroups('test'):
                    send(groupId, 'i.sjtu cookie过期')
                self.job.remove()
                self.job = None
            return
        self.failCount = 0
        prevCount = getPrevCount()
        writeNiuChaoYueCount(ncyCount)
        if prevCount == None or prevCount == ncyCount: return
        for groupId in getPluginEnabledGroups('test'):
            send(groupId, '牛哥选课人数发生了变化 %d -> %d'%(prevCount, ncyCount))
    def getPluginInfo(self) -> dict:
        return {
            'name': 'NiuChaoYueMonitor',
            'description': '监控牛哥选课情况',
            'commandDescription': '-grpcfg驱动',
            'usePlace': ['group', ],
            'showInHelp': True,
            'pluginConfigTableNames': [],
            'version': '1.0.0',
            'author': 'Unicorn',
        }
        