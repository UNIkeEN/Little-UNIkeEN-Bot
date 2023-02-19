# 遇到问题

如果你在部署与开发过程中遇到问题或有所建议，欢迎点击下方链接向我们提出 issue

[Github | Little-UNIkeEN-Bot](https://github.com/UNIkeEN/Little-UNIkeEN-Bot/issues)

问题请使用 Question 模板~

## 常见问题

1. QQ群中发送命令时图片解析出现错误
> 解决方法：打开plugins/help_v2.py，第46行中改为[CQ:image,file=files:///%s]（注意三斜杠）
> ps：该错误目前出现在Windows系统中，Linux未知

2. 运行main.py时报错，涉及bilibili_api的插件全部报错
> 解决方法：注意安装的是`bilibili-api`包而不是`bilibili_api`包，两个不一样

3. mysql_connector版本错误
> 报错，pip重装非unpackaged的包后报错消失，也可能是没装sql的问题。Windows上装mysql可参考[https://blog.csdn.net/qq_52232736/article/details/123407099](https://blog.csdn.net/qq_52232736/article/details/123407099)

4. config.yml中，第108-111行取消注释进行编辑后注意缩进问题（VSCode中）
