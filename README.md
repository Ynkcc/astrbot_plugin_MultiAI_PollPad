## MultiAI_PollPad

### AstrBot 插件

轮询调用配置的大语言模型，以输出多个结果。同时将ai的结果拷贝至在线文本编辑器，以便于用户复制。

# 如果你需要使用markdown2image作为markdown转图片解析器的话，你需要额外执行下面两段命令
```
pip install markdown2image playwright
playwright install chromium
```


---
以下内容来自markdown2image
#### Installing
```
pip install markdown2image
playwright install chromium
```

#### Usage
Just
```
from markdown2image import sync_api as md2img

md2img.html2image(html_code, save_path)
md2img.html2image(html_code, save_path, width=1080)
md2img.markdown2image(markdown_code, save_path)
md2img.markdown2image(markdown_code, save_path, width=1080)
```
Or in a running event loop,
```
from markdown2image import async_api as md2img

async def func():
    await md2img.html2image(html_code, save_path)
    await md2img.html2image(html_code, save_path, width=1080)
    await md2img.markdown2image(markdown_code, save_path)
    await md2img.markdown2image(markdown_code, save_path, width=1080)
```