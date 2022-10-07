欢迎来到 Little-UNIkeEN-Bot 的安装向导！

## 安装 Bot

你可以从 Github 下载 Little-UNIkeEN-Bot 项目。直接克隆我们的 Git 仓库即可完成安装：
```bash
git clone git@github.com:UNIkeEN/Little-UNIkeEN-Bot.git
```

## Python包依赖

本项目的Python包依赖都写在了根目录下的 `requirements.txt` 文件中，使用时只需输入以下命令即可安装。

```bash
pip install -r requirements.txt
```

## 推荐部署环境与详细教程
- **Linux** (Ubuntu 20.04 LTS)
- python >= 3.7
- mysql >= 8.0

### Linux

> 作者是在Linux平台部署开发的，有极少部分插件的命令是 shell 格式。由于时间精力有限， `1.0` 版本并未在其他平台开发测试，因此推荐在 Linux 部署。Windows 平台下亦可以运行大部分插件。

作者选用的是腾讯云新人优惠服务器 ( 4核/8G/10M/一年 )，系统选用 ubuntu 20.04 LTS。

拿到服务器首先进行换源，网上能搜到很多教程 [eg](https://zhuanlan.zhihu.com/p/421178143)。

然后就是常见编译工具的安装 (make/cmake) ，此步骤可跳过。

### Python

> 推荐使用 Miniconda 作为 Python 环境

首先，来到清华镜像的[miniconda页面](https://mirrors.tuna.tsinghua.edu.cn/anaconda/miniconda/)，在页面内搜索\"latest\"，找到\"Miniconda3-latest-Linux-x86_64.sh\"的下载链接。接下来在服务器命令行新建 `~/tmp ` 路径作为下载缓存路径，进入并下载之，推荐安装路径为 `/usr/local/miniconda3` ，具体命令如下：

```bash
mkdir ~/tmp
cd ~/tmp
wget https://mirrors.tuna.tsinghua.edu.cn/anaconda/miniconda/Miniconda3-latest-Linux-x86_64.sh
sudo bash Miniconda3-latest-Linux-x86_64.sh
```

安装完conda后也要对 conda/pip 进行换源，可以参见网上教程 [eg](https://zhuanlan.zhihu.com/p/87123943)。
