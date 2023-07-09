## nonebot-plugin-cchess

适用于 [Nonebot2](https://github.com/nonebot/nonebot2) 的象棋插件。


### 安装

- 使用 nb-cli

```
nb plugin install nonebot_plugin_cchess
```

- 使用 pip

```
pip install nonebot_plugin_cchess
```


人机功能 需要使用遵循 [UCCI协议](https://www.xqbase.com/protocol/cchess_ucci.htm) 的引擎

需要在 `.env` 文件中添加 引擎的可执行文件的路径

```
cchess_engine_path=/path/to/your/engine
```

经试用可用的引擎：

 - [Fairy-Stockfish](https://github.com/ianfab/Fairy-Stockfish/releases)

注意，Fairy-Stockfish 支持多种游戏，需要选择支持 `Xiangqi` 的发行版，即需要选带有 `largeboard` 的版本


### 使用

**以下命令需要加[命令前缀](https://v2.nonebot.dev/docs/api/config#Config-command_start) (默认为`/`)，可自行设置为空**

@我 + “象棋人机”或“象棋对战”开始一局游戏；

可使用“lv1~8”指定AI等级，如“象棋人机lv5”，默认为“lv4”；

发送 中文纵线格式如“炮二平五” 或 起始坐标格式如“h2e2”下棋；

发送“结束下棋”结束当前棋局；

发送“显示棋盘”显示当前棋局；

发送“悔棋”可进行悔棋（人机模式可无限悔棋；对战模式只能撤销自己上一手下的棋）；


或者使用 `cchess` 指令：

可用选项：

 - `-e`, `--stop`, `--end`: 停止下棋
 - `-v`, `--show`, `--view`: 显示棋盘
 - `--repent`: 悔棋
 - `--reload`: 重新加载已停止的游戏
 - `--battle`: 对战模式，默认为人机模式
 - `--black`: 执黑，即后手
 - `-l <LEVEL>`, `--level <LEVEL>`: 人机等级，可选 1~8，默认为 4


### 示例

<div align="left">
    <img src="https://s2.loli.net/2022/04/30/RztCnIkFQqWKsUe.jpg" width="500" />
</div>


### 特别感谢

- [niklasf/python-chess](https://github.com/niklasf/python-chess) A chess library for Python
- [StevenBaby/chess](https://github.com/StevenBaby/chess) 基于 Pyside2 和 UCCI 引擎的中国象棋程序
- [walker8088/cchess](https://github.com/walker8088/cchess) cchess是一个Python版的中国象棋库
- [ianfab/Fairy-Stockfish](https://github.com/ianfab/Fairy-Stockfish) chess variant engine supporting Xiangqi and many more
