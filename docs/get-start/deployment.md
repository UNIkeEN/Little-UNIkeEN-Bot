# 部署 Bot

完成上述的一系列环境安装，终于到了 Bot 的部署环节！

## 对接驱动器

首先，你需要修改代码文件中的端口号，使 Bot 与之前所配置的驱动器（go-cqhttp）相对接。

假设在 go-cqhttp 目录下的 config.yml 中配置如下：

```yaml
- http:
      address: 127.0.0.1:5700
      ...
      post:  
      - url: http://127.0.0.1:5701/ 
```

接收端口号为 5700 ，反向 POST 端口号为 5701 。对应修改 `utils/basicConfig.py` 如下：

```python
HTTP_URL = "http://127.0.0.1:5700"
```

修改 `main.py` 中最后一行如下：

```python
if __name__ == '__main__':
    app.run(host="127.0.0.1", port=5701)
```

## 账号相关配置

完成对接后，请继续修改 `utils/basicConfig.py` 。示例如下：

```python
APPLY_GROUP_ID = [111, 222]
ROOT_ADMIN_ID = [333, 444]
BOT_SELF_QQ = 555
VERSION_TXT = '版本号1.0'
sqlConfig = {
    'host': '127.0.0.1',
    'user': 'root',
    'passwd': {YOUR_SQL_PASSWORD}
}
TXT_PERMISSION_DENIED = "该功能尚未打开哦"
```

以上各常量的具体解释如下：
<table>
     <tr>
          <th>常量名称</th>
          <th>描述</th>
          <th>取值</th>
          <th>取值说明</th>
          <th>备注</th>
	</tr>
     <tr>
          <td>APPLY_GROUP_ID</td>
          <td>响应群列表</td>
          <td>list型变量</td>
          <td>表示指定 Bot 响应的群聊号码</td>
          <td>如 Bot 加入某群但列表中无此群群号，则 Bot 对该群所有信息均不做响应</td>
     </tr>
     <tr>
          <td>ROOT_ADMIN_ID</td>
          <td>超级管理员列表</td>
          <td>list型变量</td>
          <td>表示超级管理员的 QQ 号码</td>
          <td>超级管理员可以接收运行时警告，并通过命令配置各个群聊的启用插件、为各个群聊添加 Bot 管理员</td>
     </tr>
    <tr>
          <td>BOT_SELF_QQ</td>
          <td>Bot 自身账号</td>
          <td>int型变量</td>
          <td>表示 Bot 自身 QQ 号</td>
          <td></td>
     </tr>
     <tr>
          <td>VERSION_TXT</td>
          <td>版本信息</td>
          <td>str型变量</td>
          <td>表示当前 Bot 的版本号和更新描述等</td>
          <td>该信息将在收到 -test status 信息时回复</td>
     </tr>
     <tr>
          <td>sqlConfig</td>
          <td>SQL 凭证</td>
          <td>dict型变量</td>
          <td>表示连接 MySQL 的凭证</td>
          <td>连接 MySQL 所需的地址、账号（通常是root）、密码</td>
     </tr>
     <tr>
          <td>TXT_PERMISSION_DENIED</td>
          <td>无权限信息</td>
          <td>str型变量</td>
          <td>表示 Bot 功能未开启时的回复</td>
          <td>该信息将在用户试图使用 Bot 未开启功能时回复（设置为空，可适当减少刷屏）</td>
     </tr>
</table>

## 启动 Bot

完成上述配置后，恭喜你，你可以启动 Bot 了！输入以下命令启动 Bot ：

```bash
python main.py
```

!!! tip "提示：后台运行与多终端管理"
    Linux环境下，推荐使用 tmux 管理终端，并在 tmux 中新建一个 session 以后台运行 bot

若 `main.py` 所在终端在启用 Bot 的群有新信息时有输出且切换至 go-cqhttp 所在终端不再输出“上报错误”，则说明 Bot 与驱动器连接成功。你可以在启用 Bot 的群发送 `-test status` 命令，观察 Bot 是否回应以进一步测试。