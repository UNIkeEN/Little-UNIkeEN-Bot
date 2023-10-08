from utils.standard_plugin import StandardPlugin, Any, Union
import requests
from utils.basic_event import *
from utils.basic_configs import *
from utils.response_image_beta import *
from icalendar import Calendar
import datetime
import re
from utils.sql_utils import new_sql_session
from typing import Optional, Dict, List

# 开始时间占位符（当日程不提供开始时间时占位）
TIME_BEGIN_PLSHOLDER = datetime.datetime(1980, 1, 1, 0, 0, 0)

'''列表项示例
example_event = [title, subtitle, time_begin, time_end, font_color, back_color, icon_path]
'''

# 预置全局事件项（可用于公告/活动）
preset_eventlist = [
    # ['麦当劳每日免费雪碧', '发送命令【-icola】了解如何用小马自动领券~  (技术支持: Teruteru)',datetime.datetime(2023, 6, 28, 10, 00, 00), datetime.datetime(2023, 9, 5, 23, 59, 59), (35,210,137,255), (214,255,238,255), None],
]

TEXT_WEEK_LIST = ['一', '二', '三', '四', '五', '六', '日']


class GetUniAgenda(StandardPlugin):
    def judge_trigger(self, msg: str, data: Any) -> bool:
        return msg.strip() in ['-uag']

    def execute_event(self, msg: str, data: Any) -> Union[None, str]:
        target = data['group_id'] if data['message_type'] == 'group' else data['user_id']
        succ, info = make_agenda(qq_id=data['user_id'])
        if not succ:
            send(target, '[CQ:reply,id=%d]%s' % (data["message_id"], info), data['message_type'])
        else:
            picPath = info if os.path.isabs(info) else os.path.join(ROOT_PATH, info)
        send(target, f'[CQ:image,file=files:///{picPath}]', data['message_type'])
        return "OK"

    def get_plugin_info(self, ) -> Any:
        return {
            'name': 'Get UniAgenda',
            'description': '获取日程表',
            'commandDescription': '-uag',
            'usePlace': ['group', 'private', ],
            'showInHelp': True,
            'pluginConfigTableNames': ['canvasIcs'],
            'version': '1.0.0',
            'author': 'Unicorn',
        }


def make_agenda(qq_id: int) -> Tuple[bool, str]:
    """
    制作uag日程列表
    @qq_id: 用户qq号

    @return: (成功状态，图片地址）
    """
    events = []
    events.extend(preset_eventlist)
    canvasEvent = sync_canvas(qq_id)
    if canvasEvent == None:
        return False, 'canvas事件获取失败'
    events.extend(canvasEvent[:10])
    imgSavePath = draw_agenda(events=events, qq_id=qq_id)
    if imgSavePath == None:
        return False, '图片绘制失败'
    return True, imgSavePath


def parse_summary(courseName: str) -> Optional[Dict]:
    """
    Canvas日程名称分词
    @courseName: 原日程名称

    @return: 若失败返回None, 若成功则返回字典, 包含
        title: 作业名称,
        stage: 本科课程/研究生课程,
        semStart: 学期开始年,
        semEnd: 学期结束年,
        semIndex: 学期序号,
        courseNo: 课号,
        courseClassNo: 班级号,
        courseName: 课程名
    """
    pattern = re.compile(r'^(.*)\[(.*)\-\((\d+)\-(\d+)\-(\d+)\)\-(\S+)\-(\d+)\-(.*)\]')
    if pattern.match(courseName) == None:
        return None
    title, stage, semStart, semEnd, semIndex, courseNo, courseClassNo, courseName = pattern.findall(courseName)[0]
    return {
        'title': title,
        'stage': stage,
        'semStart': int(semStart),
        'semEnd': int(semEnd),
        'semIndex': int(semIndex),
        'courseNo': courseNo,
        'courseClassNo': int(courseClassNo),
        'courseName': courseName
    }


def sync_canvas(qq_id: int) -> Optional[List]:
    """
    同步canvas并生成uag日程项
    @qq_id: 用户qq号

    @return: 若失败返回None, 若成功返回uag日程项的列表
    """
    events = []
    if isinstance(qq_id, str):
        qq_id = int(qq_id)
    try:
        mydb, mycursor = new_sql_session(autocommit=False)
        mycursor.execute("select icsUrl from `canvasIcs` where qq=%d" % (qq_id))
        urls = list(mycursor)
        if len(urls) == 0:
            return []
        else:
            url = urls[0][0]
    except BaseException as e:
        warning("error in canvasSync, error: {}".format(e))

    try:
        ret = requests.get(url=url)
        if ret.status_code != requests.codes.ok:
            return []
        data = ret.content
        gcal = Calendar.from_ical(data)
        for component in gcal.walk():
            if component.name == "VEVENT":
                now = time.localtime()
                ddl_time = component.get('dtend').dt
                if not isinstance(ddl_time, datetime.datetime):
                    tmp = datetime.datetime.strftime(ddl_time, "%Y-%m-%d") + " 23:59:59"
                    ddl_time = datetime.datetime.strptime(tmp, "%Y-%m-%d %H:%M:%S")
                else:
                    ddl_time += datetime.timedelta(hours=8)
                    tmp = datetime.datetime.strftime(ddl_time, "%Y-%m-%d %H:%M:%S")
                if time.mktime(time.strptime(tmp, "%Y-%m-%d %H:%M:%S")) < time.mktime(now):
                    continue
                summary = parse_summary(component.get('summary'))
                title = component.get('summary') if summary == None else summary['title']
                subtitle = '' if summary == None else '%s  %s' % (summary['courseNo'], summary['courseName'])
                # print(summary)
                events.append([title, subtitle,
                               TIME_BEGIN_PLSHOLDER, ddl_time.replace(tzinfo=None),
                               (0, 142, 226, 255), (232, 242, 248, 255),
                               os.path.join(IMAGES_PATH, 'canvas_icon.png')])
        return events
    except Exception as e:
        warning('exception in uniAgenda.syncCanvas: {}'.format(e))
        return None


def draw_agenda(events: List[Tuple], qq_id: int) -> str:
    """绘制并保存日历图像，返回图像存储位置"""
    try:
        width = 1110  # 边距30*2，一天150
        height = 350 + 140 * (1 if len(events) < 1 else len(events))  # 边距30*2，日期栏150，主任务每行140，底部栏120, 栏与主任务距20*2
        cur_time = datetime.datetime.now().replace(tzinfo=None)

        img = Image.new('RGBA', (width, height), PALETTE_GREY_BACK)
        draw = ImageDraw.Draw(img)
        tmp = ResponseImage()
        img = tmp.draw_rounded_rectangle(30, 30, width - 30, height - 30, PALETTE_WHITE, border=True, borderWidth=3,
                                         target=img)

        # 日期标题栏
        h_top = 45
        for i in range(-3, 4):
            d = (cur_time + datetime.timedelta(days=i))
            x = 480 + i * 150 + (150 - draw.textsize(str(d.day), FONT_SYHT_M32)[0]) / 2
            y = h_top + (120 - draw.textsize(str(d.day), FONT_SYHT_M32)[1]) / 2
            draw.text((x, y), str(d.day), (PALETTE_BLACK if i != 0 else PALETTE_SJTU_DARKRED), FONT_SYHT_M32)
            x = 480 + i * 150 + (150 - draw.textsize(TEXT_WEEK_LIST[d.weekday()], FONT_SYHT_M24)[0]) / 2
            y_ = y + draw.textsize(str(d.day), FONT_SYHT_M32)[1] + 10
            draw.text((x, y_), TEXT_WEEK_LIST[d.weekday()], (PALETTE_BLACK if i != 0 else PALETTE_SJTU_DARKRED),
                      FONT_SYHT_M24)
            if i == 0:
                x = 480 + i * 150 + (150 - draw.textsize(str(d.month) + '月', FONT_SYHT_M24)[0]) / 2
                y -= 30
                draw.text((x, y), str(d.month) + '月', (PALETTE_SJTU_DARKRED), FONT_SYHT_M24)

        # 表格线
        h_top = 180
        draw.line((30, h_top, width - 30, h_top), (225, 225, 225, 255), 2)
        for i in range(-2, 4):
            x = 480 + i * 150
            draw.line((x, h_top, x, height - 150), (225, 225, 225, 255), 2)
        draw.line((30, height - 150, width - 30, height - 150), (225, 225, 225, 255), 2)
        x = 480 + 150 * (cur_time.hour * 60 + cur_time.minute) / 1440

        txt_cur_timetip = '当前时间: ' + datetime.datetime.strftime(cur_time, "%Y-%m-%d %H:%M")
        txt_size = draw.textsize(txt_cur_timetip, FONT_SYHT_M24)
        img = tmp.draw_rounded_rectangle(x - txt_size[0] / 2 - 10, height - 120, x + txt_size[0] / 2 + 10,
                                         height - 100 + txt_size[1], PALETTE_SJTU_DARKRED, target=img)
        draw.text((x - txt_size[0] / 2, height - 110), txt_cur_timetip, PALETTE_WHITE, FONT_SYHT_M24)

        h_top = 200
        # 画日程块
        for title, subtitle, tbegin, tend, clrborder, clrback, icon in events:
            _tbegin, _tend = tbegin, tend
            tleftbound = datetime.datetime.combine(cur_time - datetime.timedelta(days=3), datetime.time(0, 0, 0))
            trightbound = datetime.datetime.combine(cur_time + datetime.timedelta(days=3), datetime.time(23, 59, 59))
            if tbegin < tleftbound:
                _tbegin = tleftbound
            if tend > trightbound:
                _tend = trightbound
            x1 = 30 + 1050 * (_tbegin - tleftbound).total_seconds() / 604800
            x2 = 30 + 1050 * (_tend - tleftbound).total_seconds() / 604800
            img = tmp.draw_rounded_rectangle(x1, h_top, x2, h_top + 120, clrback, border=True, borderColor=clrborder,
                                             borderWidth=2, target=img)

            icon_width = 0
            if icon != None:
                icon = tmp.open_image(icon)
                if icon.height > 118:
                    icon.resize((118, icon.width * 118 / icon.height))
                icon_width = icon.width + 20
                img.paste(icon, (int(x2 - icon_width - 2), int(h_top + (120 - icon.height) / 2) + 2))

            draw.text((x1 + 20, h_top + 22), cut_line(title, FONT_SYHT_M28, x2 - x1 - 40 - icon_width), clrborder,
                      FONT_SYHT_M28)
            draw.text((x1 + 20, h_top + 60), cut_line(subtitle, FONT_SYHT_M18, x2 - x1 - 40 - icon_width),
                      PALETTE_GREY_SUBTITLE, FONT_SYHT_M18)
            tip_time = (datetime.datetime.strftime(tbegin,
                                                   "%m-%d %H:%M") if tbegin != TIME_BEGIN_PLSHOLDER else '') + '至' + datetime.datetime.strftime(
                tend, "%m-%d %H:%M")
            draw.text((x1 + 20, h_top + 82), cut_line(tip_time, FONT_SYHT_M18, x2 - x1 - 40 - icon_width),
                      PALETTE_GREY_CONTENT, FONT_SYHT_M18)
            h_top += 140

        draw.line((x, 180, x, height - 120), PALETTE_SJTU_DARKRED, 3)

        save_path = os.path.join(SAVE_TMP_PATH, f'{qq_id}_agenda.png')
        img.save(save_path)
        return save_path
    except Exception as e:
        warning('exception in uniAgenda.drawAgenda: {}'.format(e))
        return None


def cut_line(input, font, limit):
    """画图时长文本超行分割"""
    output = ''
    width = 0
    for s in input:
        if (width + font.getsize(s)[0] > limit - 30):
            output += '...'
            break
        else:
            width += font.getsize(s)[0]
            output += s
    return output
