# 配置 go-cqhttp

Little-UNIkeEN-Bot 是 QQ 机器人前端，只能处理交互逻辑，不能直接实现 QQ 机器人的所有功能。我们需要额外安装驱动器来实现与QQ服务器的信息收发与交互。

## 1. 安装 go-cqhttp

本 Bot 默认使用 go-cqhttp 作为驱动器，这是一个优秀的无头 QQ 客户端，关于其安装请见 [go-cqhttp官网 - 安装](https://docs.go-cqhttp.org/guide/quick_start.html#%E5%9F%BA%E7%A1%80%E6%95%99%E7%A8%8B) 。

## 2. 配置 go-cqhttp

安装完成后，第一次打开 go-cqhttp 时请选择“HTTP通信”，然后修改生成的 `config.yml` 文件如下：

```yaml hl_lines="9 17"
account: 
  uin: {YOUR_BOT_QQ} # 作为机器人的QQ账号
  password: {YOUR_BOT_PASSWORD} # 密码为空时使用扫码登录
  encrypt: false  # 是否开启密码加密
...
servers:

  - http: # HTTP 通信设置
      address: 127.0.0.1:5700 # HTTP监听地址(端口号可变)
      timeout: 5      # 反向 HTTP 超时时间, 单位秒，<5 时将被忽略
      long-polling:   # 长轮询拓展
        enabled: false       # 是否开启
        max-queue-size: 2000 # 消息队列大小，0 表示不限制队列大小，谨慎使用
      middlewares:
        <<: *default # 引用默认中间件
      post:           # 反向HTTP POST地址列表
      - url: http://127.0.0.1:5701/ # 地址(端口号可变)
       secret: ''                  # 密钥
       max-retries: 2             # 最大重试，0 时禁用
       retries-interval: 1000      # 重试时间，单位毫秒，0 时立即
```

请记住两处高亮处您设置的端口号，在"部署 Bot"一节，我们将再次用到。

配置文件中的其余部分（如账号登陆状态，消息发送重试次数等），你均可以参考注释，按需更改。

## 3. 启动 go-cqhttp

完成上述配置后，您可以启动 go-cqhttp。

Windows 环境下直接运行 go-cqhttp.bat

Linux 环境下，在 go-cqhttp 目录下输入以下命令以运行

```bash
./go-cqhttp
```

!!! tip "提示：后台运行与多终端管理"
    Linux环境下，推荐使用 tmux 管理终端，并在 tmux 中新建一个 session 以后台运行 go-cqhttp

## 4. 登录问题

在使用 go-cqhttp 登录你的 Bot 账号时，可能会遇到安全验证。

* 如你在本机运行，请使用扫码登录。

* 如你在服务器运行，由于扫码手机与服务器端通常不在同一网络环境下，你可能会遇到扫码失败的情况。此时，你可以在本机使用 go-cqhttp 扫码登录，并将产生的 `device.json` 和 `session.token` 文件复制到服务器的 go-cqhttp 目录下，然后重新启动 go-cqhttp 。