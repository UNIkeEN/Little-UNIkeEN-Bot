## 0. 推荐部署环境
- **Linux** (Ubuntu 20.04LTS)
- python >= 3.7
- mysql >= 8.0

## 1. Linux
> 作者是在Linux平台部署开发的，有极少部分插件(dekt)的命令是shell格式。由于时间精力有限，`1.0`版本并未在其他平台开发测试，因此推荐在Linux部署。

作者花了388在腾讯云买了一个新人优惠服务器(4核/8G/10M/一年)，系统选用ubuntu 20.04LTS。

拿到主机以后第一件事就是换源，网上能搜到很多教程 [eg](https://zhuanlan.zhihu.com/p/421178143)。

然后就是常见编译工具的安装(make/cmake)，此步骤可跳过。

## 2. python
> 作者推荐使用Miniconda作为python环境

首先，来到清华镜像的[miniconda页面](https://mirrors.tuna.tsinghua.edu.cn/anaconda/miniconda/)，在页面内搜索\"latest\"，找到\"Miniconda3-latest-Linux-x86_64.sh\"的下载链接。接下来在服务器命令行新建`~/tmp`路径作为下载缓存路径，进入并下载之，推荐安装路径为`/usr/local/miniconda3`，具体命令如下：

```bash
mkdir ~/tmp
cd ~/tmp
wget https://mirrors.tuna.tsinghua.edu.cn/anaconda/miniconda/Miniconda3-latest-Linux-x86_64.sh
sudo bash Miniconda3-latest-Linux-x86_64.sh
```

安装完conda以后也要记得对conda/pip进行换源，网上能搜到很多教程 [eg](https://zhuanlan.zhihu.com/p/87123943)。

## 3. mysql
mysql的安装，网上能找到很多教程 [eg1](https://cloud.tencent.com/developer/article/1863236) [eg2](https://www.runoob.com/mysql/mysql-install.html)。

具体来说，首先到[mysql官网](https://downloads.mysql.com/archives/community/)下载对应操作系统的包，搜索配置如下(ProductVersion选最新，OsVersion选相应)：

![](../images/mysqlSearch.png)

接下来复制下载链接(下载下来scp到服务器上也行)，输入以下命令：

```bash
# stage 1: download
cd ~/tmp
wget ${YOUR_COPIED_URL}
sudo dpkg -i ${DOWNLOADED_DEB}
sudo apt update
sudo apt install mysql-server

# stage 2: init
sudo chown -R mysql:mysql /var/lib/mysql/
mysqld --initialize
systemctl start mysqld
```

接下来就是改配置、改密码什么的，网上的教程也都有，此处不赘述。直到你输入以下命令能冒出mysql命令行后，你的mysql安装过程才算大功告成：

```bash
mysql -u root -p
```

如果你是在本机安装sql的话，推荐mysql workbench作为mysql可视化工具。

## 4. python包依赖