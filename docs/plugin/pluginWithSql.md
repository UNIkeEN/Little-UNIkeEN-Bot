插件程序员有两种方法可以与mysql交互：

1. 通过现有 API 间接交互，例如 group config
2. 自己 import mysql.connector 直接交互

第一种方式比较简单，但是实现的功能有限。在 utils.basicEvent 中有 readGlobalConfig 等函数，它们能够读写 `BOT_DATA.globalConfig` 表中存储的数据。但是这种方式只能读取插件是否在某群中开启、某群的 bot管理员 有哪几个，无法进行更多数据的存取。

第二种方式能够自定义进行sql交互，实现更加丰富的功能。例如

!!! warning "注意：数据库交互必须防止外部数据注入"
    sql 防注入是开发者必须遵守的安全准则，插件程序员可以通过字符串转义（例如 escape_string ）或正则字符串匹配（例如 re.match ）来规避数据库注入风险。任何来自外部的数据都必须做到防注入，比如昵称、聊天记录、头像 url 等。

关于 mysql 交互插件编写的样例，可以参考：

- [群 bot 权限管理 API](../api/auth-config.md)（读写群 bot 管理员、插件开启信息）
- [SJTU canvas 插件](./plugins/canvasIcsPlugin.md) （ics url 的存取）
- [聊天记录存档插件](./plugins/messageRecorderPlugin.md)（聊天记录的存储）
- [accountOperation API](../api/account-operation.md) 金币系统