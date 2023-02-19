# python安装与pip包依赖

## 1. python安装

### 1.1 推荐平台下(ubuntu20.04 x64)的推荐python环境(Miniconda)安装

> 推荐使用 Miniconda 作为 Python 环境

首先，来到清华镜像的[miniconda页面](https://mirrors.tuna.tsinghua.edu.cn/anaconda/miniconda/)，在页面内搜索\"latest\"，找到\"Miniconda3-latest-Linux-x86_64.sh\"的下载链接。接下来在服务器命令行新建 `~/tmp ` 路径作为下载缓存路径，进入并下载之，推荐安装路径为 `/usr/local/miniconda3` ，具体命令如下：

```bash
mkdir ~/tmp
cd ~/tmp
wget https://mirrors.tuna.tsinghua.edu.cn/anaconda/miniconda/Miniconda3-latest-Linux-x86_64.sh
sudo bash Miniconda3-latest-Linux-x86_64.sh
```

安装完conda后也要对 conda/pip 进行换源，可以参见网上教程 [eg](https://zhuanlan.zhihu.com/p/87123943)。

### 1.2 Windows下的推荐python环境(Miniconda)安装

首先，来到清华镜像的[miniconda页面](https://mirrors.tuna.tsinghua.edu.cn/anaconda/miniconda/)，在页面内搜索\"latest\"，找到\"Miniconda3-latest-Windows-x86_64.exe\"，点击下载，然后双击运行之。

安装程序运行完毕后，打开powershell，如果前面没有以`(base) C:\...> `字样大头，请用管理员权限开启powershell，输入（欲知详情，请百度 “[powershell执行脚本](https://cn.bing.com/search?q=powershell%E6%89%A7%E8%A1%8C%E8%84%9A%E6%9C%AC)”）：

```powershell
Set-ExecutionPolicy Unrestricted
```

重启powershell，如果看到以`(base) C:\...> `字样打头，且输入python能进入命令行，则大功告成。

!!! tip "将python路径注册到系统PATH"
	在执行Miniconda安装程序窗口，如果看到将python路径注册到系统PATH选项，请勾选之



### 1.3 windows下python安装

请自行百度

## 2. pip包依赖

本项目的Python包依赖都写在了根目录下的 `requirements.txt` 文件中，使用时只需输入以下命令即可安装。

```bash
pip install -r requirements.txt
```

!!! tip "插件import错误解决方法"
	如果在import插件时报错某个pip包依赖错误，可以注释先该插件，尝试先让bot跑通，然后再想解决办法QwQ
