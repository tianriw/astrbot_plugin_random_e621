import random
import time
from typing import Any

import astrbot.api.message_components as Comp
import httpx
from astrbot.api import AstrBotConfig, logger
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.star import Context, Star, register

# 这个虽然很长，但是一定是正确的！不必考虑可读性，因为本来就没想让人读！只有一个 POST
A_POST = {
    "id": 6024779,
    "created_at": "2025-12-06T12:08:39.970+08:00",
    "updated_at": "2025-12-06T13:26:17.455+08:00",
    "file": {
        "width": 4500,
        "height": 6000,
        "ext": "png",
        "size": 10606598,
        "md5": "1d2b323eeb03f5e619d2e3ab715d5339",
        "url": "https://static1.e621.net/data/1d/2b/1d2b323eeb03f5e619d2e3ab715d5339.png",
    },
    "preview": {
        "width": 256,
        "height": 341,
        "url": "https://static1.e621.net/data/preview/1d/2b/1d2b323eeb03f5e619d2e3ab715d5339.jpg",
        "alt": "https://static1.e621.net/data/preview/1d/2b/1d2b323eeb03f5e619d2e3ab715d5339.webp",
    },
    "sample": {
        "has": True,
        "width": 850,
        "height": 1133,
        "url": "https://static1.e621.net/data/sample/1d/2b/1d2b323eeb03f5e619d2e3ab715d5339.jpg",
        "alt": "https://static1.e621.net/data/sample/1d/2b/1d2b323eeb03f5e619d2e3ab715d5339.webp",
        "alternates": {},
    },
    "score": {"up": 4, "down": 0, "total": 4},
    "tags": {
        "general": [
            "anthro",
            "athletic_wear",
            "bottomwear",
            "clothing",
            "gym",
            "gym_bottomwear",
            "gym_shorts",
            "male",
            "male/male",
            "muscular",
            "musk",
            "shorts",
            "solo",
        ],
        "artist": ["honeyjolteon_22"],
        "contributor": [],
        "copyright": [],
        "character": [],
        "species": ["canid", "canine", "canis", "mammal", "wolf"],
        "invalid": [],
        "meta": ["3:4", "absurd_res", "hi_res"],
        "lore": [],
    },
    "locked_tags": [],
    "change_seq": 72692815,
    "flags": {
        "pending": True,
        "flagged": False,
        "note_locked": False,
        "status_locked": False,
        "rating_locked": False,
        "deleted": False,
    },
    "rating": "q",
    "fav_count": 3,
    "sources": [],
    "pools": [],
    "relationships": {
        "parent_id": None,
        "has_children": False,
        "has_active_children": False,
        "children": [],
    },
    "approver_id": None,
    "uploader_id": 952777,
    "uploader_name": "HoneyJolteon_22",
    "description": "",
    "comment_count": 0,
    "is_favorited": False,
    "has_notes": False,
    "duration": None,
}


@register("Random Post In E621", "Tianri", "随机获取 E621 上的图片", "1.1.0")
class RandE621(Star):
    MAX_PAGE_SEARCH = 30
    CACHE_SIZE = 100
    REQ_COOLDOWN = 3

    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config
        self.api_key = self._config_value("api_key")
        self.user_name = self._config_value("user_name")
        self.tags = self._config_value("tags")
        self.extra_negative_tags = self._config_value("extra_negative_tags")
        self.proxy_url = self._config_value("proxy_url")
        self.last_req_time = 0.0
        self.cached_post: list[dict[str, Any]] = [A_POST]

        client_kwargs: dict[str, Any] = {"timeout": 15.0}
        if self.proxy_url:
            client_kwargs["proxy"] = self.proxy_url
        self.client = httpx.AsyncClient(**client_kwargs)
        if self.user_name and self.api_key:
            self.client.auth = httpx.BasicAuth(self.user_name, self.api_key)

        user_name = self.user_name or "unknown"
        self.user_agent = (
            "RandE621_AstrBotPlugin/1.1 "
            f"(Developed by Tianri on e621, user: {user_name} on e621)"
        )

    async def initialize(self):
        """插件初始化。"""

    def _config_value(self, key: str, default: str = "") -> str:
        try:
            value = self.config[key]
        except Exception:
            return default
        return default if value is None else str(value)

    def _headers(self) -> dict[str, str]:
        return {"User-Agent": self.user_agent}

    def _get_cached_post(self) -> dict[str, Any]:
        return random.choice(self.cached_post)

    def _cache_post(self, post: dict[str, Any]) -> None:
        if len(self.cached_post) >= self.CACHE_SIZE:
            self.cached_post.pop(0)
        self.cached_post.append(post)

    def _get_image_url(self, post: dict[str, Any]) -> str | None:
        file_data = post.get("file", {})
        if not isinstance(file_data, dict):
            return None
        image_url = file_data.get("url")
        return image_url if isinstance(image_url, str) and image_url else None

    def _build_post_chain(
        self, event: AstrMessageEvent, post: dict[str, Any], *lines: str
    ) -> list[Any]:
        chain: list[Any] = []
        sender_id = event.get_sender_id()
        if sender_id:
            chain.append(Comp.At(qq=sender_id))
            chain.append(Comp.Plain("\n"))
        for line in lines:
            if line:
                chain.append(Comp.Plain(line))

        image_url = self._get_image_url(post)
        if image_url:
            chain.append(Comp.Image.fromURL(image_url))
        else:
            chain.append(Comp.Plain("[图片URL不存在]"))
        return chain

    def _flatten_tags(self, post: dict[str, Any]) -> set[str]:
        tags_in_post = post.get("tags", {})
        if not isinstance(tags_in_post, dict):
            return set()

        flattened_tags: set[str] = set()
        for values in tags_in_post.values():
            if isinstance(values, list):
                flattened_tags.update(str(value) for value in values)
        return flattened_tags

    def _after_process(self, post: dict[str, Any]) -> bool:
        blocked_tags = [tag for tag in self.extra_negative_tags.split(" ") if tag]
        if not blocked_tags:
            return True

        tags = self._flatten_tags(post)
        return not any(tag in tags for tag in blocked_tags)

    async def _request_json(
        self, method: str, url: str, *, update_last_req_time: bool = True
    ) -> tuple[dict[str, Any] | None, str]:
        try:
            response = await self.client.request(method, url, headers=self._headers())
            if update_last_req_time:
                self.last_req_time = time.time()

            if response.is_error:
                logger.error(
                    f"E621 请求失败，状态码：{response.status_code}，响应内容：{response.text}"
                )
                return None, "我们无法从 E621 上获取数据...\n"

            data = response.json()
            if not isinstance(data, dict):
                logger.error(f"E621 response format error: {data}")
                return None, "E621 API 响应格式错误...\n"
            return data, ""
        except httpx.ConnectError as exc:
            logger.error(f"Connect Error: {exc}")
            return None, "我们无法连接到 E621 API...\n"
        except Exception as exc:  # noqa: BLE001
            logger.error(f"Request Error: {exc}")
            return None, "请求出错...\n"

    async def _fetch_random_post_once(self) -> tuple[dict[str, Any] | None, str]:
        random_page = random.randint(0, self.MAX_PAGE_SEARCH)
        url = (
            "https://e621.net/posts.json"
            f"?limit=10&page={random_page}&tags={self.tags}"
        )
        data, error_message = await self._request_json("GET", url)
        if data is None:
            return None, error_message

        posts = data.get("posts")
        if not isinstance(posts, list):
            logger.error(f"E621 response format error: {data}")
            return None, "E621 API 响应格式错误...\n"

        if not posts:
            return None, "> 这里如此寂寥，我好害怕...\n"

        random.shuffle(posts)
        for post in posts:
            if isinstance(post, dict) and self._after_process(post):
                self._cache_post(post)
                return post, ""

        return None, "> 这里太过特殊，我不喜欢...\n"

    async def get_random_post(self) -> tuple[dict[str, Any], str]:
        if time.time() - self.last_req_time < self.REQ_COOLDOWN and self.cached_post:
            return self._get_cached_post(), "当前处于冷却中...\n"

        last_message = ""
        for _ in range(3):
            post, message = await self._fetch_random_post_once()
            if post is not None:
                return post, message
            last_message = message
            if "无法" in message or "出错" in message or "格式错误" in message:
                break

        return self._get_cached_post(), last_message or "请求出错...\n"

    async def get_fav621(
        self, user_id: str = "", *, use_cooldown: bool = True
    ) -> tuple[dict[str, Any], str]:
        if (
            use_cooldown
            and time.time() - self.last_req_time < self.REQ_COOLDOWN
            and self.cached_post
        ):
            return self._get_cached_post(), "当前处于冷却中...\n"

        url = "https://e621.net/favorites.json?limit=10"
        if user_id:
            url += f"&user_id={user_id}"

        data, error_message = await self._request_json(
            "GET", url, update_last_req_time=use_cooldown
        )
        if data is None:
            return self._get_cached_post(), error_message

        posts = data.get("posts")
        if not isinstance(posts, list):
            logger.error(f"E621 response format error: {data}")
            return self._get_cached_post(), "E621 API 响应格式错误...\n"

        if not posts:
            return self._get_cached_post(), "> 这里如此寂寥，我好害怕...\n"

        post = random.choice(posts)
        if isinstance(post, dict):
            return post, ""
        return self._get_cached_post(), "E621 API 响应格式错误...\n"

    async def _set_favorite_post(self, post_id: str) -> tuple[dict[str, Any], str]:
        url = f"https://e621.net/favorites.json?post_id={post_id}&limit=1"
        data, error_message = await self._request_json(
            "POST", url, update_last_req_time=False
        )
        if data is None:
            return self._get_cached_post(), error_message

        if "favorite_count" not in data:
            logger.error(f"E621 response format error: {data}")
            return self._get_cached_post(), "E621 API 响应格式错误...\n"

        return await self.get_fav621(use_cooldown=False)

    @filter.command("rand621")
    async def rand621(self, event: AstrMessageEvent):
        """发送随机 E621 图片。"""
        post, message = await self.get_random_post()
        is_favorited = "是" if post.get("is_favorited") else "否"
        chain = self._build_post_chain(
            event,
            post,
            "获取成功！\n" if not message else message,
            f"图片ID：{post.get('id', '未知')}\n",
            f"获取时是否被 {self.user_name or '当前账号'} 大人标记：{is_favorited}\n",
        )
        yield event.chain_result(chain)

    @filter.command("fav621")
    async def fav621(self, event: AstrMessageEvent, user_id: str = ""):
        """随机查看某个用户的 E621 收藏。"""
        post, message = await self.get_fav621(user_id)
        target_user = user_id or self.user_name or "当前账号"
        chain = self._build_post_chain(
            event,
            post,
            "获取成功！\n" if not message else message,
            f"图片ID：{post.get('id', '未知')}\n",
            f"已被 {target_user} 大人标记\n",
        )
        yield event.chain_result(chain)

    @filter.permission_type(filter.PermissionType.ADMIN)
    @filter.command("set_fav621")
    async def set_fav621(self, event: AstrMessageEvent, post_id: str = ""):
        """将指定帖子加入当前配置账号的收藏夹。"""
        if not post_id:
            yield event.plain_result(
                "> 这里空无一人\n很抱歉，你有一个参数未提供（post_id）"
            )
            return

        post, message = await self._set_favorite_post(post_id)
        chain = self._build_post_chain(
            event,
            post,
            "获取成功！\n" if not message else message,
            f"图片ID：{post.get('id', '未知')}\n",
            f"已被 {self.user_name or '当前账号'} 大人标记\n",
        )
        yield event.chain_result(chain)

    async def terminate(self):
        """插件销毁。"""
        await self.client.aclose()
