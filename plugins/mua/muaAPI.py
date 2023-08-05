import requests
from typing import Tuple, Optional, Dict

def verifyMuaToken(token:str)->Tuple[bool, str]:
    """校验MUA token是否合法
    @token: MUA token
    @return:
        if token合法:
            (True, MUAID)
        else:
            (False, 'false')
    """
    url = 'https://skin.mualliance.ltd/api/union/code'
    req = requests.post(url=url, params={'token': token}).json()
    succ = req['success']
    if succ:
        return succ, req['code']
    else:
        return succ, 'false'
def getTargetGroupMapping(muaToken:str)->Optional[Dict[str, int]]:
    """获取 群号-MUAID 之间的对应关系
    @muaToken: 查询者的MUA Token
    @return:
        if 查询者合法:
            {MUAID(str): 群号(int)}
        else:
            None
    """
    url = 'https://skin.mualliance.ltd/api/union/network'
    req = requests.get(url=url, headers={'X-Union-Network-Query-Token': muaToken})
    if req.status_code != requests.codes.ok:
        return None
    try:
        result = req.json()['extra']['union_sync']['qq_groups']
        for muaId, groupId in result.items():
            result[muaId] = int(groupId)
        return result
    except Exception as e:
        print(e)
        return None
