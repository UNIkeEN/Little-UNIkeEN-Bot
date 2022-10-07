插件在工作时难免遇到运行时错误，每次登录服务器翻找终端 log 以定位错误无疑是一个繁琐的过程。

利用 `try-except` 机制与 Bot 提供的 `warning()` 函数，你可以将运行中的错误信息通过 QQ 发送给超级管理员（即 `utils/basicConfig.py` 中 ROOT_ADMIN_ID 列表中的账号）