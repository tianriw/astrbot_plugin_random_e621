from itertools import chain
from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
import astrbot.api.message_components as Comp
import httpx
import base64
import random
import time
from astrbot.api import AstrBotConfig

@register("Random Post In E621", "Tianri", "随机获取 E621 上的图片", "1.0.0")
class RandE621(Star):
    cached_post = []

    def __init__(self, context: Context,config: AstrBotConfig):
        super().__init__(context)
        self.config = config
        self.api_key = self.config["api_key"]
        self.user_name = self.config["user_name"]
        self.tags = self.config["tags"]
        self.last_req_time = 0

        self.auth_header = base64.b64encode(f"{self.user_name}:{self.api_key}".encode("utf-8"))
        self.auth_header = "Basic " + self.auth_header.decode("utf-8")
        self.user_agent = f"RandE621_AstrBotPlugin/1.0 (Developed by Tianri on e621, user: {self.user_name} on e621)"


    async def initialize(self):
        """可选择实现异步的插件初始化方法，当实例化该插件类之后会自动调用该方法。"""

    # 注册指令的装饰器。指令名为 helloworld。注册成功后，发送 `/helloworld` 就会触发这个指令，并回复 `你好, {user_name}!`
    @filter.command("/rand621")
    async def rand621(self, event: AstrMessageEvent):
        """发送随机 E621 图片（标记为 S 或 Q）""" # 这是 handler 的描述，将会被解析方便用户了解插件内容。建议填写。
        post,msg = await self.get_random_post()
        chain = [
            Comp.At(qq=event.get_sender_id()),
            Comp.Plain("获取成功！" if msg == "" else msg),
            Comp.Plain(f"图片ID：{post['id']}"),
            Comp.Plain(f"获取时是否被 {self.user_name} 大人标记：{'是' if post['is_favorited'] else '否'}"),
            Comp.Image.fromURL(post["url"])
        ]
        yield event.chain_result(chain)

    async def get_random_post(self):
        if time.time() - self.last_req_time < 3 and self.cached_post:
            return (random.choice(self.cached_post),"当前处于冷却中...")

        random_page = random.randint(0,30)

        res = httpx.get(f"https://e621.net/posts.json?limit=1&tags={self.tags}", headers={"Authorization": self.auth_header, "User-Agent": self.user_agent})
        self.last_req_time = time.time()
        self.cached_post.append(res.json()["posts"][0])
        return (res.json()["posts"][0],"")

    async def terminate(self):
        """可选择实现异步的插件销毁方法，当插件被卸载/停用时会调用。"""
