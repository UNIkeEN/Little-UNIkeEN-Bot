from utils.configsLoader import loadApplyGroupId
from utils.basicConfigs import SAVE_TMP_PATH, ROOT_PATH
from utils.basicEvent import send
from utils.configAPI import getPluginEnabledGroups
loadApplyGroupId()
biliGroups = getPluginEnabledGroups('bilibili')
for group in biliGroups:
    send(group, '小🦄的bilibili订阅功能升级了，现支持订阅动态，更新后的效果预览将稍后发出')