## MultiAI_PollPad

### AstrBot 插件

轮询调用配置的大语言模型，以输出多个结果。同时将ai的结果拷贝至在线文本编辑器，以便于用户复制。

### 模块配置
#### excluded_models 
需要排除的模型名称，~~注意是模型名称，不要填写成提供商id了。~~

#### use_markdown2image
使用markdown2image替代Astrbot提供的t2i
>效果并不好，markdown语法存在解析问题，不建议开启。**默认关闭。**

**如果你要使用该功能的话，你还需要额外执行下面两段命令**
```
pip install markdown2image playwright
playwright install chromium
```
