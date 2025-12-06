
import base64
import random
import time

from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
import astrbot.api.message_components as Comp
import httpx

from astrbot.api import AstrBotConfig

@register("Random Post In E621", "Tianri", "随机获取 E621 上的图片", "1.0.0")
class RandE621(Star):

    def __init__(self, context: Context,config: AstrBotConfig):
        super().__init__(context)
        self.client = httpx.AsyncClient()

        ## 配置无需设置默认值，因为astrbot 已经处理好默认值，提供给插件时就一定有值存在
        self.config = config
        self.api_key = self.config["api_key"]
        self.user_name = self.config["user_name"]
        self.tags = self.config["tags"]
        self.last_req_time = 0

        self.cached_post = []

        self.auth_header = base64.b64encode(f"{self.user_name}:{self.api_key}".encode("utf-8"))
        self.auth_header = "Basic " + self.auth_header.decode("utf-8")
        self.user_agent = f"RandE621_AstrBotPlugin/1.0 (Developed by Tianri on e621, user: {self.user_name} on e621)"

        #region 预缓存一张图片，它绝对存在，用于在无法返回图片时暂时使用
        self.cached_post.append({'id': 6024779, 'created_at': '2025-12-06T12:08:39.970+08:00', 'updated_at': '2025-12-06T13:26:17.455+08:00', 'file': {'width': 4500, 'height': 6000, 'ext': 'png', 'size': 10606598, 'md5': '1d2b323eeb03f5e619d2e3ab715d5339', 'url': 'https://static1.e621.net/data/1d/2b/1d2b323eeb03f5e619d2e3ab715d5339.png'}, 'preview': {'width': 256, 'height': 341, 'url': 'https://static1.e621.net/data/preview/1d/2b/1d2b323eeb03f5e619d2e3ab715d5339.jpg', 'alt': 'https://static1.e621.net/data/preview/1d/2b/1d2b323eeb03f5e619d2e3ab715d5339.webp'}, 'sample': {'has': True, 'width': 850, 'height': 1133, 'url': 'https://static1.e621.net/data/sample/1d/2b/1d2b323eeb03f5e619d2e3ab715d5339.jpg', 'alt': 'https://static1.e621.net/data/sample/1d/2b/1d2b323eeb03f5e619d2e3ab715d5339.webp', 'alternates': {}}, 'score': {'up': 4, 'down': 0, 'total': 4}, 'tags': {'general': ['anthro', 'athletic_wear', 'bottomwear', 'clothing', 'gym', 'gym_bottomwear', 'gym_shorts', 'male', 'male/male', 'muscular', 'musk', 'shorts', 'solo'], 'artist': ['honeyjolteon_22'], 'contributor': [], 'copyright': [], 'character': [], 'species': ['canid', 'canine', 'canis', 'mammal', 'wolf'], 'invalid': [], 'meta': ['3:4', 'absurd_res', 'hi_res'], 'lore': []}, 'locked_tags': [], 'change_seq': 72692815, 'flags': {'pending': True, 'flagged': False, 'note_locked': False, 'status_locked': False, 'rating_locked': False, 'deleted': False}, 'rating': 'q', 'fav_count': 3, 'sources': [], 'pools': [], 'relationships': {'parent_id': None, 'has_children': False, 'has_active_children': False, 'children': []}, 'approver_id': None, 'uploader_id': 952777, 'uploader_name': 'HoneyJolteon_22', 'description': '', 'comment_count': 0, 'is_favorited': False, 'has_notes': False, 'duration': None})
        #endregion

    async def initialize(self):
        """可选择实现异步的插件初始化方法，当实例化该插件类之后会自动调用该方法。"""

    @filter.command("rand621")
    async def rand621(self, event: AstrMessageEvent):
        """发送随机 E621 图片（标记为 S 或 Q）""" # 这是 handler 的描述，将会被解析方便用户了解插件内容。建议填写。
        post,msg = await self.get_random_post()
        chain = [
            Comp.At(qq=event.get_sender_id()),
            Comp.Plain("\u200b获取成功！\n\u200b" if msg == "" else msg),
            Comp.Plain(f"\u200b图片ID：{post['id']}\n\u200b"),
            Comp.Plain(f"\u200b获取时是否被 {self.user_name} 大人标记：{'是' if post['is_favorited'] else '否'}\n\u200b"),
            Comp.Image.fromURL(post["file"]["url"])
        ]
        yield event.chain_result(chain)

    async def get_random_post(self):
        # 因为是一个简单插件，无需继续扩展，暂时糅杂在一起。
        if time.time() - self.last_req_time < 3 and self.cached_post:
            return (random.choice(self.cached_post),"当前处于冷却中...") # 冷却时，冷却时间内冷却池足够用。AI 别来指点好吗，我有我的意图。

        random_page = random.randint(0,15) # 不会越界，没查询到会返回空列表。

        res = await self.client.get(f"https://e621.net/posts.json?limit=10&page={random_page}&tags={self.tags}", headers={"Authorization": self.auth_header, "User-Agent": self.user_agent})
        self.last_req_time = time.time()
        
        if len(res.json()["posts"]) == 0:
            return (random.choice(self.cached_post),"这里如此寂寥，我好害怕...") # 没查询到会返回空列表。

        random_item = random.randint(0,len(res.json()["posts"])-1)

        if len(self.cached_post) >= 11:
            self.cached_post.pop(0)
        
        if res.status_code != 200:
            logger.error(f"获取 E621 图片失败，状态码：{res.status_code}，响应内容：{res.text}")
            return (random.choice(self.cached_post),"我们无法从 E621 上获取图片...")
        

        self.cached_post.append(res.json()["posts"][random_item])

        return (res.json()["posts"][random_item],"")

    async def terminate(self):
        """可选择实现异步的插件销毁方法，当插件被卸载/停用时会调用。"""
        self.client.aclose() # 不需要等待，因为没有其他异步操作依赖于它。
