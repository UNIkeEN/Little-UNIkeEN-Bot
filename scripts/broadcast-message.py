from utils.configsLoader import loadApplyGroupId
from utils.basicConfigs import SAVE_TMP_PATH, ROOT_PATH, APPLY_GROUP_ID
from utils.basicEvent import send
from utils.configAPI import getPluginEnabledGroups
import os
loadApplyGroupId()
print(getPluginEnabledGroups('leetcode'))
# biliGroups = getPluginEnabledGroups('muanotice')
# send(548045274, '[CQ:image,file=file:///%s]'%(os.path.join(ROOT_PATH, SAVE_TMP_PATH, 'mualist_1773701277.png')), )
for group in APPLY_GROUP_ID:
    send(group, '【公告】小🦄服务已恢复。\n---\n2023-11-2停止服务原因：主进程所在服务器因root文件系统错误无法正常启动')
while True:
    pass
    # send(group, '检测到MUA通知更新：')
    # send(group, '[CQ:image,file=file:///%s]'%(os.path.join(ROOT_PATH, SAVE_TMP_PATH, 'mualist_1773701277.png')))