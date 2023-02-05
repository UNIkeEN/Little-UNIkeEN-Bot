`version 1.1.1`
# 1. 简介

Little-UNIkeEN-Bot 是一个由 Python 编写的轻量级、可扩展的QQ机器人前端，底层基于 go-cqhttp、flask、mysql 等第三方依赖。

!!! warning "注意：存在很多处文档内容落后于代码的情况"
    由于此项目随缘更新、开发强度不大，因此存在很多处文档内容落后于代码的情况。建议有条件的开发者直接阅读源码进行开发。

# 2. 项目架构图

![framework](./images/framework.jpg)

1. 红框标注的是用户（插件开发者）需求
2. 蓝线标注的是需要用户自行调用或编写的逻辑
3. 绿线标注的是bot封装好的逻辑

# 3. 运行流程图

![flowchart](./images/flowchart.jpg)
