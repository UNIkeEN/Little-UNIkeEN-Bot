# 安装向导

欢迎来到 Little-UNIkeEN-Bot 的安装向导！

## 1. 安装 Bot

你可以从 Github 下载 Little-UNIkeEN-Bot 项目。直接克隆我们的 Git 仓库即可完成安装：
```bash
git clone git@github.com:UNIkeEN/Little-UNIkeEN-Bot.git
```

## 2. 运行平台

## 2.1 推荐平台

- **Linux** (Ubuntu 20.04 LTS)
- python >= 3.7
- mysql >= 8.0

> 作者是在Linux平台部署开发的，有极少部分插件的命令是 shell 格式。由于时间精力有限， `1.0` 版本并未在其他平台开发测试，因此推荐在 Linux 部署。Windows 平台下亦可以运行大部分插件。

作者选用的是腾讯云新人优惠服务器 ( 4核/8G/10M/一年 )，系统选用 ubuntu 20.04 LTS。

拿到服务器首先进行换源，网上能搜到很多教程 [eg](https://zhuanlan.zhihu.com/p/421178143)。

然后就是常见编译工具的安装 (make/cmake) ，此步骤可跳过。

## 2.2 Windows平台

由于作者懒得写跨平台的代码，所以bot有极少数功能在windows平台上无法使用：

- monitor
- kill browsermob in sjtuDekt plugin

## 3. 基础依赖

Little-Unicorn-Bot有以下三大基础依赖，必须安装他们仨才能运行bot：

- python
- go-cqhttp
- mysql

接下来三章将介绍如何安装这三个基础依赖