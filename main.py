import uuid
import aiohttp
import os
import asyncio
from astrbot.api.all import *
from astrbot.api.event import filter
from astrbot.api import logger
from aiohttp import ClientTimeout, TCPConnector

@register("MultiAI_PollPad", "ynkcc", "一个轮询调用多个 AI 模型并回复的插件", "1.0.0")
class MultiAIPollPad(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config
        self.excluded_models = self.config.get("excluded_models", [])
        self.use_markdown2image = self.config.get("use_markdown2image", False)
        self._session = None
        self._session_lock = asyncio.Lock()

    @property
    async def session(self) -> aiohttp.ClientSession:
        """获取或创建线程安全的 session 实例"""
        async with self._session_lock:
            if self._session is None or self._session.closed:
                #logger.debug("Creating new aiohttp session")
                self._session = aiohttp.ClientSession(
                    timeout=ClientTimeout(total=30),
                    connector=TCPConnector(limit_per_host=20)
                )
            return self._session

    async def close_session(self):
        """安全关闭 session"""
        async with self._session_lock:
            if self._session and not self._session.closed:
                #logger.debug("Closing aiohttp session")
                await self._session.close()
                self._session = None

    async def terminate(self):
        """插件卸载时的清理"""
        await self.close_session()

    @filter.command("MultiAI_PollPad")
    async def auto_reply(self, event: AstrMessageEvent):
        if len(event.message_str) < 5:
            return

        providers = [
            p for p in self.context.get_all_providers()
            if p.model_name not in self.excluded_models
        ]
        if not providers:
            logger.info("没有可用模型")
            return

        async def get_llm_response(provider):
            try:
                llm_response = await provider.text_chat(
                    prompt=event.message_str,
                    session_id=None,
                    contexts=[],
                    image_urls=[],
                    func_tool=None,
                    system_prompt="",
                )
                return (
                    f"# [{provider.model_name}]:\n{llm_response.completion_text}\n"
                    if llm_response.role == "assistant"
                    else f"[{provider.model_name}]: 没有返回 assistant\n"
                )
            except Exception as e:
                logger.error(f"Model {provider.model_name} error: {str(e)}")
                return f"[{provider.model_name}]: 调用失败，错误信息：{str(e)}"

        try:
            tasks = [get_llm_response(p) for p in providers]
            all_chains = await asyncio.gather(*tasks)
            final_message = "\n".join(all_chains)

            txt_url = await self.upload_txt(final_message)

            if self.use_markdown2image:
                from markdown2image import async_api as md2img
                img_path = "temp.png"
                await md2img.markdown2image(final_message, img_path)
                try:
                    with open(img_path, "rb") as f:
                        image_object = Image.fromBytes(f.read())
                finally:
                    os.remove(img_path)
            else:
                image_url = await self.text_to_image(final_message)
                image_object = Image.fromURL(image_url)

            yield event.chain_result([
                At(qq=event.get_sender_id()),
                Plain(f"可打开地址拷贝内容，有效期一年{txt_url}"),
                image_object
            ])

        except Exception as e:
            logger.exception("处理请求时发生错误")
            yield event.chain_result([
                At(qq=event.get_sender_id()),
                Plain("请求处理失败，请稍后重试")
            ])

    async def upload_txt(self, context: str) -> str:
        """带重试机制的文件上传"""
        if len(context) > 200000:
            raise ValueError("文本长度超过20万字符限制")

        key = uuid.uuid4().hex
        data = {"key": key, "value": context}
        session = await self.session

        for attempt in range(3):
            try:
                async with session.post(
                    "https://api.textdb.online/update/",
                    data=data,
                    timeout=15
                ) as resp:
                    resp.raise_for_status()
                    result = await resp.json()

                    if result["status"] != 1:
                        raise RuntimeError(f"API 返回异常: {result}")
                    return result["data"]["url"]

            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                if attempt == 2:
                    raise RuntimeError(f"上传失败: {str(e)}") from e
                await asyncio.sleep(1 * (attempt + 1))

        raise RuntimeError("超过最大重试次数")
