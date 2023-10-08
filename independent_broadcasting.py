from utils.configs_loader import load_apply_group_id
from utils.basic_configs import SAVE_TMP_PATH, ROOT_PATH
from utils.basic_event import send
from utils.config_api import get_plugin_enabled_groups

load_apply_group_id()
biliGroups = get_plugin_enabled_groups('bilibili')
for group in biliGroups:
    send(group, '小🦄的bilibili订阅功能升级了，现支持订阅动态，更新后的效果预览将稍后发出')
