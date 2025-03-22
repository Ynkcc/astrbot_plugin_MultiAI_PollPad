import uuid
import aiohttp
import os
import asyncio
from astrbot.api.all import *
from astrbot.api.event import filter
from astrbot.api import logger

@register("MultiAI_PollPad", "ynkcc", "一个轮询调用多个 AI 模型并回复的插件", "1.0.0")
class MultiAIPollPad(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config
        self.excluded_models = self.config.get("excluded_models", [])
        self.session = aiohttp.ClientSession()
        self.use_markdown2image=self.config.get("use_markdown2image", False)

    @filter.command("MultiAI_PollPad")
    async def auto_reply(self, event: AstrMessageEvent):
        """处理调用请求"""

        # 问题太短了，不回
        if len(event.message_str) < 5:
            return

        # 获取所有可用的大语言模型提供商
        providers = [provider for provider in self.context.get_all_providers() if provider.model_name not in self.excluded_models]
        if not providers:
            logger.info("没有可用模型")
            return

        async def get_llm_response(provider):
            try:
                llm_response = await provider.text_chat(
                    prompt=f"{event.message_str}",
                    session_id=None,
                    contexts=[],
                    image_urls=[],
                    func_tool=None,
                    system_prompt="",
                )
                if llm_response.role == "assistant":
                    return f"# [{provider.model_name}]: \n{llm_response.completion_text}\n"
                else:
                    return f"[{provider.model_name}]: 没有返回 assistant\n"
            except Exception as e:
                return f"[{provider.model_name}]: 调用失败，错误信息：{str(e)}"

        # 并行调用用户选择的大语言模型
        tasks = [get_llm_response(provider) for provider in providers]
        all_chains = await asyncio.gather(*tasks)

        final_message = "\n".join(all_chains)

        # 上传原始回复内容至在线剪贴板
        txt_url = await self.upload_txt(final_message)

        if self.use_markdown2image:
            from markdown2image import async_api as md2img
            img_path = "temp.png"
            await md2img.markdown2image(final_message, img_path)
            with open(img_path, "rb") as f:
                img_data = f.read()
            os.remove(img_path)
            image_object = Image.fromBytes(img_data)
        else:
            image_url = await self.text_to_image(final_message)
            image_object = Image.fromURL(image_url)

        yield event.chain_result(
            [
                At(qq=event.get_sender_id()),
                Plain(f"可打开地址拷贝内容，有效期一年{txt_url}"),
                image_object
            ]
        )
        await self.session.close()


    async def upload_txt(self, context: str):
        """将文本结果上传至在线文本编辑器"""
        if len(context) > 200000:
            raise ValueError("文本长度超过20万字符限制")

        key = str(uuid.uuid4()).replace('-','')
        data = {"key": key, "value": context}

        try:
            async with self.session.post(
                "https://api.textdb.online/update/", data=data
            ) as response:
                response.raise_for_status()
                result = await response.json()

                if result["status"] != 1:
                    raise Exception(f"上传: {result}")

            return result["data"]["url"]
        except aiohttp.ClientError as e:
            raise Exception(f"网络请求异常: {str(e)}") from e
