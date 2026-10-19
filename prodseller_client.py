"""Client bất đồng bộ kết nối tới ProdSeller Official API v1 (https://prodseller.com/v1)."""

from __future__ import annotations

import asyncio
import logging
import os
import re
import time
from typing import Any

import httpx

BASE_URL = "https://prodseller.com/v1"
DANTE_BASE_URL = "https://dantehub.shop/api/public/v1"

# Danh sách 21 sản phẩm dùng chung giữa @ProdSellerBot (product_id) và @DanteHubBot (remote_product_id)
DEFAULT_DANTE_MAPPINGS: list[tuple[str, str, str]] = [
    ("6a5b873847b606c66fc160b2", "be463cf1-d374-4765-81e7-205fa7ded577", "DanteHub"),  # Adobe Express 12M
    ("6a2fe23a1c8697b163aedcbd", "29f62cae-b550-4047-811e-548373cba029", "DanteHub"),  # Microsoft Office 365 Plus 1Y
    ("6a31035939dc014325da2c66", "a2076639-732f-4366-87c0-cecee34b35a4", "DanteHub"),  # Gemini Pro 18 Months
    ("6aa5bafb77c587d75cbe2a8e", "def676c9-a1c5-4aea-ad6f-224b4337a71f", "DanteHub"),  # Duolingo Super 12M
    ("6ac65a53d07e0053469f477d", "00a35204-8b71-4543-bee7-c0525b3cad4b", "DanteHub"),  # Muse AI 1B Tokens
    ("6ac88922cd35776c4d2cf283", "3c20bc64-c09b-4664-9013-e33efb96c207", "DanteHub"),  # SCRIBD PREMIUM 1M FW
    ("6ad1e30eb2ca69ae7f674aff", "15d553d9-3d8e-4355-9a2a-f8e6693da3bf", "DanteHub"),  # YouTube Premium 1M
    ("6a2fda51035a6d898f2106fe", "23e46b24-0639-47b6-bc76-e9e592bc2a8e", "DanteHub"),  # CapCut Pro 1 Month FW
    ("6aa4551bc76bc3aeb2ebe88e", "59467b31-53b4-43de-b8d4-4c00b6088c1f", "DanteHub"),  # CAPCUT PRO 1600 CREDITS
    ("6abeb3210dbb401865ffe95f", "6bce5a91-b1df-4165-9c98-bb06654ad90b", "DanteHub"),  # Wispr Flow 12M Edu
    ("6a7826d9cf6984bb8ba101e8", "23aca303-4729-4f5f-be65-cbf44768819a", "DanteHub"),  # Figma Pro Edu 2yrs
    ("6a88be06fb032a73212a202b", "b4905436-e389-4c19-86b6-17a429120f3f", "DanteHub"),  # JetBrains Edu Pack 12m
    ("6a54b931351561c645a43e8c", "8bc2c2d1-75be-4d23-abf0-f11f1b7589f6", "DanteHub"),  # Notion Plus 12M
    ("6a2fdb4f035a6d898f2106ff", "19ba7788-f159-49c5-b07b-89bce8383b9e", "DanteHub"),  # Canva Pro Admin 500 invites
    ("6acf6cf6a8f487d336acb4ab", "97c3d979-e770-42e9-93a2-0a332123ea94", "DanteHub"),  # ElevenLabs 100K Credit
    ("6a495a5f02999800df961920", "4212e10e-6369-41c7-814b-778ce82a6efc", "DanteHub"),  # ChatGPT Plus K12 Edu 24M
    ("6a316a7b1777fc2347835653", "5003b154-9d14-432e-a232-e3d2be2d18e1", "DanteHub"),  # Canva Pro Team Edu 3Y
    ("6abeace70dbb401865ffb2d2", "e7dc36ba-06bf-4b5f-989d-ff7ef280a144", "DanteHub"),  # Apple TV 12 Months Link
    ("6a8ad927f870e3b3430c7b18", "ea67449c-0dac-4d45-b596-dfa0bfc9251d", "DanteHub"),  # Framer AI 1 Year
    ("6acfc869a8f487d336b13845", "a7d4b6e6-822b-418c-ae13-ca91da33c41f", "DanteHub"),  # Spotify Premium 1M
    ("6a8c8ef9f870e3b343103eb0", "f407a873-1c8a-478c-ba40-5b6a04f2f353", "DanteHub"),  # Autodesk All Apps
]

# Các ID trùng lặp hoặc mục Test nội bộ trên DanteHub không hiển thị riêng lẻ
EXTRA_SKIP_DANTE_IDS: set[str] = {
    "0015a475-163b-41cc-90e6-0fafbb6ba6e4",  # Duplicate Figma Pro Edu 2yrs
    "b665a651-4c58-4b3d-91ec-4692724a5031",  # Test API for Developers ($0.01)
}

# Custom Emoji Icon IDs + Unicode Icons cho từng nhóm và từng sản phẩm
GROUP_ICONS: dict[str, int] = {
    "ChatGPT & OpenAI": 5796185041717433060,
    "Claude AI": 6174520215376763867,
    "Gemini & Google AI": 5206660927339924387,
    "Cursor & Grok AI": 5300959605793235101,
    "Kling, Suno & Video AI": 5891219692881714411,
    "Leonardo, Gamma & Ảnh AI": 5393312805795407636,
    "ElevenLabs & Giọng Nói AI": 6219689196722854904,
    "MiniMax & Muse AI": 5891219692881714411,
    "Lovable, n8n & Dev Tools": 5300959605793235101,
    "Canva": 5879982576671657703,
    "CapCut": 6124915477706705232,
    "Figma, Adobe & Thiết Kế": 6145685845060883545,
    "Office 365, Notion & Văn Phòng": 6102808052673548025,
    "YouTube, Netflix & Giải Trí": 5926990577114550753,
    "Duolingo, Coursera & Học Tập": 5796371348808799072,
    "VPN & Bảo Mật": 5350619413533958825,
    "Gmail, Outlook & MXH": 5307602416961609760,
}

GROUP_EMOJI: dict[str, str] = {
    "ChatGPT & OpenAI": "🤖 ",
    "Claude AI": "🧠 ",
    "Gemini & Google AI": "✨ ",
    "Cursor & Grok AI": "⚡ ",
    "Kling, Suno & Video AI": "🎥 ",
    "Leonardo, Gamma & Ảnh AI": "🖼️ ",
    "ElevenLabs & Giọng Nói AI": "🎙️ ",
    "MiniMax & Muse AI": "🚀 ",
    "Lovable, n8n & Dev Tools": "💻 ",
    "Canva": "🎨 ",
    "CapCut": "🎬 ",
    "Figma, Adobe & Thiết Kế": "📐 ",
    "Office 365, Notion & Văn Phòng": "💼 ",
    "YouTube, Netflix & Giải Trí": "🍿 ",
    "Duolingo, Coursera & Học Tập": "🎓 ",
    "VPN & Bảo Mật": "🛡️ ",
    "Gmail, Outlook & MXH": "📧 ",
}

PRODUCT_KEYWORD_ICONS: list[tuple[str, int | None, str]] = [
    ("spotify", 5926990577114550753, "🎧 "),
    ("netflix", None, "🍿 "),
    ("elevenlabs", 6219689196722854904, "🎙️ "),
    ("eleven reader", 6219689196722854904, "🎙️ "),
    ("gmail", 5307602416961609760, "📧 "),
    ("scribd", None, "📚 "),
    ("muse ai", 5891219692881714411, "🎵 "),
    ("minimax", 5891219692881714411, "🚀 "),
    ("chatgpt", 5796185041717433060, "🤖 "),
    ("codex", 5796185041717433060, "🤖 "),
    ("claude", 6174520215376763867, "🧠 "),
    ("cursor", 5300959605793235101, "⚡ "),
    ("grok", None, "🔥 "),
    ("kling", None, "🎥 "),
    ("higgsfield", None, "🎥 "),
    ("heygen", None, "🎥 "),
    ("suno", 5891219692881714411, "🎵 "),
    ("leonardo", None, "🖼️ "),
    ("gamma", None, "📊 "),
    ("lovable", None, "💖 "),
    ("bolt", None, "⚡ "),
    ("n8n", None, "🔄 "),
    ("replit", None, "💻 "),
    ("wispr", 6069015112549669594, "🗣️ "),
    ("apple tv", 5469922901958346945, "🍎 "),
    ("apple music", 5469922901958346945, "🍎 "),
    ("duolingo", 5796371348808799072, "🦉 "),
    ("coursera", 5769598970816897041, "🎓 "),
    ("udemy", 5769598970816897041, "🎓 "),
    ("quizlet", 5769598970816897041, "🎓 "),
    ("capcut", 6124915477706705232, "🎬 "),
    ("hbo", 5346319945112240722, "🎞️ "),
    ("telegram", None, "✈️ "),
    ("x premium", None, "🐦 "),
    ("facebook", None, "📘 "),
    ("discord", None, "🎮 "),
    ("autodesk", 6305045014531548800, "📐 "),
    ("framer", 6312056780570499991, "⚡ "),
    ("jetbrains", 5300959605793235101, "💻 "),
    ("avira", 5350619413533958825, "🛡️ "),
    ("kaspersky", 5350619413533958825, "🛡️ "),
    ("nordvpn", 5350619413533958825, "🛡️ "),
    ("surfshark", 5350619413533958825, "🛡️ "),
    ("vpn", 5350619413533958825, "🛡️ "),
    ("edx", 5769598970816897041, "🎓 "),
    ("gemini", 5206660927339924387, "✨ "),
    ("figma", 5393312805795407636, "🎨 "),
    ("miro", None, "📝 "),
    ("ilovepdf", 6239983230729068544, "📄 "),
    ("grammarly", None, "✍️ "),
    ("outlook", 5796683820564484775, "📨 "),
    ("hotmail", 5796683820564484775, "📨 "),
    ("adobe", 6145685845060883545, "🅰️ "),
    ("notion", 5233464190441662039, "📓 "),
    ("prime video", 6111801057061374810, "📺 "),
    ("tv360", 6111801057061374810, "📺 "),
    ("canva", 5879982576671657703, "🖌️ "),
    ("office", 6102808052673548025, "💼 "),
    ("microsoft", 6102808052673548025, "💼 "),
    ("youtube", None, "▶️ "),
    ("vidiq", None, "▶️ "),
    ("hma", None, "🛡️ "),
]


def get_product_icon_and_prefix(product_name: str, use_fallback_emoji: bool = False) -> tuple[int | None, str]:
    """Trả về (custom_emoji_icon_id, text_prefix) cho từng sản phẩm."""
    low = product_name.lower()
    for kw, icon_id, prefix in PRODUCT_KEYWORD_ICONS:
        if kw in low:
            if icon_id is not None and not use_fallback_emoji:
                return icon_id, ""
            return icon_id, prefix
    return None, "📦 "


def detect_plan_group(product_name: str, category: str = "") -> str | None:
    """Phân nhóm thông minh toàn bộ 142+ sản phẩm của @ProdSellerBot và @DanteHubBot."""
    low = f"{category} {product_name}".lower()
    if any(k in low for k in ("chatgpt", "codex", "openai")):
        return "ChatGPT & OpenAI"
    if "claude" in low:
        return "Claude AI"
    if "gemini" in low:
        return "Gemini & Google AI"
    if any(k in low for k in ("cursor", "grok", "supergrok")):
        return "Cursor & Grok AI"
    if any(k in low for k in ("kling", "higgsfield", "heygen", "seedance", "suno", "descript", "vidiq")):
        return "Kling, Suno & Video AI"
    if any(k in low for k in ("leonardo", "gamma", "meitu", "magic patterns")):
        return "Leonardo, Gamma & Ảnh AI"
    if any(k in low for k in ("elevenlabs", "eleven reader", "wispr")):
        return "ElevenLabs & Giọng Nói AI"
    if any(k in low for k in ("minimax", "muse ai")):
        return "MiniMax & Muse AI"
    if any(k in low for k in ("lovable", "bolt", "replit", "jetbrains", "n8n", "linear", "gumloop", "posthog", "resend", "intercom", "pangram", "factory ai")):
        return "Lovable, n8n & Dev Tools"
    if "canva" in low:
        return "Canva"
    if any(k in low for k in ("capcut", "supercut")):
        return "CapCut"
    if any(k in low for k in ("figma", "adobe", "autodesk", "framer", "miro")):
        return "Figma, Adobe & Thiết Kế"
    if any(k in low for k in ("office", "microsoft 365", "notion", "grammarly", "ilovepdf", "scribd", "granola")):
        return "Office 365, Notion & Văn Phòng"
    if any(k in low for k in ("youtube", "netflix", "spotify", "apple tv", "apple music", "hbo", "prime video", "tv360", "discord")):
        return "YouTube, Netflix & Giải Trí"
    if any(k in low for k in ("duolingo", "coursera", "edx", "udemy", "quizlet")):
        return "Duolingo, Coursera & Học Tập"
    if any(k in low for k in ("vpn", "nordvpn", "surfshark", "kaspersky", "avira", "proton", "purevpn", "hma")):
        return "VPN & Bảo Mật"
    if any(k in low for k in ("gmail", "outlook", "hotmail", "telegram", "x premium", "facebook")):
        return "Gmail, Outlook & MXH"
    return None


def stock_badge(stock: int | None, in_stock: bool) -> str:
    """Hiển thị biểu tượng trạng thái tồn kho giống @ProdSellerBot."""
    if not in_stock or (stock is not None and stock <= 0):
        return "🔴 0"
    if stock is None:
        return "🟢 ∞"
    if stock <= 5:
        return f"🟡 {stock}"
    return f"🟢 {stock}"


class ProdSellerClient:
    def __init__(
        self,
        api_key: str,
        dante_api_key: str = "",
        dante_base_url: str = DANTE_BASE_URL,
    ) -> None:
        self.api_key = api_key.strip()
        self.dante_api_key = (
            dante_api_key
            or os.getenv("DANTE_API_KEY", "dh_live_d56175ed6a4bf6f70ac166f2efa9c7f49fc49e81e4be91e4")
        ).strip()
        self.dante_base_url = (dante_base_url or os.getenv("DANTE_BASE_URL", DANTE_BASE_URL)).strip()
        self._products_cache: list[dict[str, Any]] = []
        self._stock_cache: dict[str, int | None] = {}
        self._last_sync: float = 0.0
        self._lock = asyncio.Lock()
        self._http: httpx.AsyncClient | None = None
        self._dante_products_cache: list[dict[str, Any]] = []
        self._dante_last_sync: float = 0.0
        self._linked_dante_ids: set[str] = {dh_id for _, dh_id, _ in DEFAULT_DANTE_MAPPINGS} | set(EXTRA_SKIP_DANTE_IDS)

    def set_dante_credentials(self, api_key: str, base_url: str = DANTE_BASE_URL) -> None:
        if api_key and api_key.strip():
            self.dante_api_key = api_key.strip()
        if base_url and base_url.strip():
            self.dante_base_url = base_url.strip()

    @staticmethod
    def make_dante_short_id(dh_uuid: str) -> str:
        clean = str(dh_uuid).strip().replace("-", "")
        return f"dh_{clean[:21]}"

    def _get_http(self) -> httpx.AsyncClient:
        if self._http is None or self._http.is_closed:
            self._http = httpx.AsyncClient(
                timeout=20.0,
                limits=httpx.Limits(max_keepalive_connections=10, max_connections=20),
            )
        return self._http

    def _headers(self, idempotency_key: str | None = None) -> dict[str, str]:
        h = {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json",
            "User-Agent": "ProdSellerResellerBot/1.0",
        }
        if idempotency_key:
            h["Idempotency-Key"] = idempotency_key[:100]
        return h

    @staticmethod
    def is_dantehub_url(api_base_url: str) -> bool:
        low = (api_base_url or "").lower()
        return "dantehub" in low or "/api/public" in low

    @staticmethod
    def _normalize_external_base(api_base_url: str) -> str:
        base = (api_base_url or DANTE_BASE_URL).strip().rstrip("/")
        if not base.endswith("/v1"):
            base = f"{base}/v1"
        return base

    @staticmethod
    def _external_headers(api_key: str, idempotency_key: str | None = None) -> dict[str, str]:
        clean_key = (api_key or "").strip()
        h = {
            "X-API-Key": clean_key,
            "Authorization": f"Bearer {clean_key}",
            "Content-Type": "application/json",
            "User-Agent": "KingToolMultiSourceRouter/1.0",
        }
        if idempotency_key:
            h["Idempotency-Key"] = idempotency_key[:100]
        return h

    async def get_balance(self) -> dict[str, Any]:
        client = self._get_http()
        resp = await client.get(f"{BASE_URL}/balance", headers=self._headers())
        resp.raise_for_status()
        return resp.json()

    async def get_external_balance(
        self,
        api_base_url: str = DANTE_BASE_URL,
        api_key: str = "",
    ) -> dict[str, Any]:
        """Lấy số dư ví USDT trên @DanteHubBot hoặc cổng Reseller API ngoài."""
        base = self._normalize_external_base(api_base_url or self.dante_base_url)
        key = (api_key or self.dante_api_key).strip()
        client = self._get_http()
        resp = await client.get(
            f"{base}/balance",
            headers=self._external_headers(key),
            timeout=12.0,
        )
        resp.raise_for_status()
        return resp.json()

    async def fetch_dantehub_catalog(
        self,
        api_base_url: str = DANTE_BASE_URL,
        api_key: str = "",
        force: bool = False,
        cache_ttl: float = 60.0,
    ) -> list[dict[str, Any]]:
        """Lấy toàn bộ danh mục 124+ sản phẩm từ @DanteHubBot (có RAM Cache 60s)."""
        now = time.time()
        if not force and self._dante_products_cache and (now - self._dante_last_sync < cache_ttl):
            return self._dante_products_cache
        base = self._normalize_external_base(api_base_url or self.dante_base_url)
        key = (api_key or self.dante_api_key).strip()
        if not key:
            return self._dante_products_cache
        client = self._get_http()
        resp = await client.get(
            f"{base}/products",
            headers=self._external_headers(key),
            timeout=15.0,
        )
        resp.raise_for_status()
        data = resp.json()
        prods = data.get("products", []) if isinstance(data, dict) else []
        if prods:
            self._dante_products_cache = prods
            self._dante_last_sync = now
        return self._dante_products_cache

    async def search_dantehub_products(
        self,
        query: str,
        api_base_url: str = DANTE_BASE_URL,
        api_key: str = "",
        limit: int = 8,
    ) -> list[dict[str, Any]]:
        """Tìm nhanh các sản phẩm tương đồng trên @DanteHubBot để Admin gắn 1 chạm."""
        catalog = await self.fetch_dantehub_catalog(api_base_url, api_key, force=False)
        tokens = [
            w
            for w in re.split(r"[^a-z0-9]+", (query or "").lower())
            if len(w) >= 2 and w not in ("pro", "plus", "fw", "nw", "month", "months", "year", "years", "account", "link", "edu")
        ]
        scored: list[tuple[int, float, dict[str, Any]]] = []
        for item in catalog:
            title = str(item.get("title") or item.get("name") or "")
            cat = str(item.get("category") or "")
            hay = f"{cat} {title}".lower()
            score = sum(3 if tok in cat.lower() else (2 if tok in hay else 0) for tok in tokens)
            if score > 0 or not tokens:
                scored.append((score, -float(item.get("price", 0) or 0), item))
        scored.sort(key=lambda x: (x[0], x[1]), reverse=True)
        return [x[2] for x in scored[:limit]]

    async def fetch_product_detail(self, product_id: str) -> dict[str, Any]:
        client = self._get_http()
        resp = await client.get(f"{BASE_URL}/products/{product_id}", headers=self._headers())
        resp.raise_for_status()
        data = resp.json()
        if "stock" in data:
            self._stock_cache[product_id] = data["stock"]
        return data

    async def sync_products(self, force: bool = False, cache_ttl: float = 60.0) -> list[dict[str, Any]]:
        """Lấy danh sách sản phẩm hợp nhất từ cả @ProdSellerBot và @DanteHubBot (142+ sản phẩm).
        Sử dụng cơ chế Stale-While-Revalidate: nếu đã có cache và force=False, trả về ngay lập tức
        để người dùng không bao giờ phải chờ, đồng thời tự động làm mới ngầm nếu cache đã quá hạn.
        """
        now = time.time()
        if not force and self._products_cache:
            if (now - self._last_sync >= cache_ttl) and not self._lock.locked():
                asyncio.create_task(self._refresh_products_internal())
            return self._products_cache

        return await self._refresh_products_internal()

    async def _refresh_products_internal(self) -> list[dict[str, Any]]:
        async with self._lock:
            client = self._get_http()
            ps_products: list[dict[str, Any]] = []
            try:
                resp = await client.get(f"{BASE_URL}/products", headers=self._headers())
                resp.raise_for_status()
                products: list[dict[str, Any]] = resp.json().get("products", [])

                sem = asyncio.Semaphore(8)

                async def _fetch_stock(p: dict[str, Any]) -> None:
                    pid = p["id"]
                    p["provider"] = "prodseller"
                    if not p.get("inStock", False):
                        self._stock_cache[pid] = 0
                        p["stock"] = 0
                        return
                    async with sem:
                        try:
                            r = await client.get(f"{BASE_URL}/products/{pid}", headers=self._headers())
                            if r.status_code == 200:
                                detail = r.json()
                                st = detail.get("stock")
                                self._stock_cache[pid] = st
                                p["stock"] = st
                        except Exception as exc:
                            logging.debug("Không lấy được stock chi tiết %s: %s", pid, exc)
                            p["stock"] = self._stock_cache.get(pid)

                await asyncio.gather(*(_fetch_stock(p) for p in products))
                ps_products = list(reversed(products))
            except Exception as exc:
                logging.warning("Không đồng bộ được danh sách ProdSeller: %s", exc)
                ps_products = [p for p in self._products_cache if p.get("provider") == "prodseller"]

            dante_exclusive: list[dict[str, Any]] = []
            if self.dante_api_key:
                try:
                    dh_catalog = await self.fetch_dantehub_catalog(
                        self.dante_base_url,
                        self.dante_api_key,
                        force=True,
                    )
                    skip_ids = (
                        {dh_id for _, dh_id, _ in DEFAULT_DANTE_MAPPINGS}
                        | set(EXTRA_SKIP_DANTE_IDS)
                        | self._linked_dante_ids
                    )
                    for item in dh_catalog:
                        dh_uuid = str(item.get("id", "")).strip()
                        if not dh_uuid or dh_uuid in skip_ids:
                            continue
                        short_id = self.make_dante_short_id(dh_uuid)
                        in_st = bool(item.get("in_stock", item.get("inStock", False)))
                        raw_st = item.get("stock")
                        st_val = int(raw_st) if raw_st is not None else (50 if in_st else 0)
                        title = str(item.get("title") or item.get("name") or dh_uuid).strip()
                        cat = str(item.get("category") or "").strip()
                        desc = str(item.get("description") or "").strip()
                        price_usd = float(item.get("price", 0) or 0)
                        dante_exclusive.append(
                            {
                                "id": short_id,
                                "dante_uuid": dh_uuid,
                                "provider": "dantehub",
                                "name": title,
                                "category": cat,
                                "description": desc,
                                "price": price_usd,
                                "inStock": in_st and st_val > 0,
                                "stock": st_val if in_st else 0,
                            }
                        )
                except Exception as exc:
                    logging.warning("Không đồng bộ được danh sách độc quyền DanteHub: %s", exc)
                    dante_exclusive = [p for p in self._products_cache if p.get("provider") == "dantehub"]

            if ps_products or dante_exclusive:
                self._products_cache = ps_products + dante_exclusive
                self._last_sync = time.time()
            return self._products_cache

    async def get_product_by_id(self, product_id: str, refresh: bool = False) -> dict[str, Any] | None:
        """Lấy thông tin 1 sản phẩm (từ ProdSeller hoặc DanteHub). Nếu refresh=True chỉ làm mới đúng nguồn của sản phẩm."""
        if not self._products_cache:
            await self.sync_products(force=True)

        target = str(product_id).strip()
        for p in self._products_cache:
            if p["id"] == target or p.get("dante_uuid") == target:
                if refresh:
                    try:
                        if p.get("provider") == "dantehub":
                            dh_uuid = str(p.get("dante_uuid") or target)
                            detail = await self.fetch_external_api_product(
                                self.dante_base_url,
                                self.dante_api_key,
                                dh_uuid,
                                force_refresh=True,
                            )
                            if detail:
                                p["stock"] = detail.get("stock", p.get("stock"))
                                p["price"] = detail.get("price", p.get("price"))
                                p["inStock"] = detail.get("inStock", p.get("inStock"))
                        else:
                            detail = await self.fetch_product_detail(p["id"])
                            p["stock"] = detail.get("stock", p.get("stock"))
                            p["price"] = detail.get("price", p.get("price"))
                            if "inStock" in detail:
                                p["inStock"] = detail["inStock"]
                            elif isinstance(p.get("stock"), int):
                                p["inStock"] = p["stock"] > 0
                    except Exception:
                        pass
                return p
        return None

    async def create_order(
        self,
        product_id: str,
        quantity: int = 1,
        email: str | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        """Mua hàng tự động trên ProdSeller bằng số dư đại lý."""
        payload: dict[str, Any] = {
            "productId": product_id,
            "quantity": quantity,
        }
        if email:
            if quantity == 1:
                payload["email"] = email.strip()
            else:
                payload["emails"] = [email.strip()] * quantity

        client = self._get_http()
        resp = await client.post(
            f"{BASE_URL}/orders",
            headers=self._headers(idempotency_key=idempotency_key),
            json=payload,
            timeout=30.0,
        )
        data = resp.json()
        if resp.status_code >= 400 or "error" in data:
            err_msg = data.get("error") or f"HTTP {resp.status_code}"
            raise RuntimeError(err_msg)
        return data

    async def get_order_status(self, prodseller_order_id: str) -> dict[str, Any]:
        client = self._get_http()
        resp = await client.get(
            f"{BASE_URL}/orders/{prodseller_order_id}",
            headers=self._headers(),
        )
        resp.raise_for_status()
        return resp.json()

    async def fetch_external_api_product(
        self,
        api_base_url: str,
        api_key: str,
        remote_product_id: str,
        force_refresh: bool = False,
    ) -> dict[str, Any]:
        """Lấy tồn kho và giá từ @DanteHubBot hoặc cổng Reseller API v1 bên ngoài."""
        base = self._normalize_external_base(api_base_url)
        r_pid = remote_product_id.strip()

        if self.is_dantehub_url(base):
            catalog = await self.fetch_dantehub_catalog(base, api_key, force=force_refresh)
            for item in catalog:
                if str(item.get("id", "")).strip() == r_pid:
                    in_st = bool(item.get("in_stock", item.get("inStock", False)))
                    raw_st = item.get("stock")
                    st_val = int(raw_st) if raw_st is not None else (50 if in_st else 0)
                    return {
                        "id": r_pid,
                        "name": str(item.get("title") or item.get("name") or r_pid),
                        "category": str(item.get("category") or ""),
                        "price": float(item.get("price", 0) or 0),
                        "inStock": in_st and st_val > 0,
                        "stock": st_val if in_st else 0,
                    }
            return {}

        client = self._get_http()
        resp = await client.get(
            f"{base}/products/{r_pid}",
            headers=self._external_headers(api_key),
            timeout=15.0,
        )
        if resp.status_code == 404:
            # Fallback nếu nguồn dùng GET /products giống DanteHub
            r_all = await client.get(f"{base}/products", headers=self._external_headers(api_key), timeout=15.0)
            if r_all.status_code == 200:
                for item in r_all.json().get("products", []):
                    if str(item.get("id", "")).strip() == r_pid:
                        in_st = bool(item.get("in_stock", item.get("inStock", False)))
                        raw_st = item.get("stock")
                        st_val = int(raw_st) if raw_st is not None else (50 if in_st else 0)
                        return {
                            "id": r_pid,
                            "name": str(item.get("title") or item.get("name") or r_pid),
                            "price": float(item.get("price", 0) or 0),
                            "inStock": in_st and st_val > 0,
                            "stock": st_val if in_st else 0,
                        }
        resp.raise_for_status()
        return resp.json()

    @staticmethod
    def _extract_dante_keys(delivery_val: Any, qty: int = 1) -> list[str]:
        if not delivery_val:
            return []
        if isinstance(delivery_val, list):
            return [str(k).strip() for k in delivery_val if str(k).strip()]
        txt = str(delivery_val).strip()
        if not txt:
            return []
        lines = [ln.strip() for ln in txt.splitlines() if ln.strip()]
        if qty > 1 and len(lines) >= qty:
            return lines
        return [txt]

    async def get_external_api_order_status(
        self,
        api_base_url: str,
        api_key: str,
        remote_order_id: str,
    ) -> dict[str, Any]:
        """Kiểm tra trạng thái đơn hàng trên @DanteHubBot (`GET /orders/:order_id`) hoặc Reseller API v1."""
        base = self._normalize_external_base(api_base_url)
        client = self._get_http()
        resp = await client.get(
            f"{base}/orders/{remote_order_id.strip()}",
            headers=self._external_headers(api_key),
            timeout=15.0,
        )
        resp.raise_for_status()
        data = resp.json()
        ord_obj = data.get("order") if isinstance(data.get("order"), dict) else data
        raw_status = str(ord_obj.get("status") or "processing").lower()
        keys: list[str] = []
        if ord_obj.get("deliveredKeys"):
            keys = [str(k) for k in ord_obj["deliveredKeys"]]
        elif ord_obj.get("deliveredKey"):
            keys = [str(ord_obj["deliveredKey"])]
        elif ord_obj.get("delivery"):
            keys = self._extract_dante_keys(ord_obj.get("delivery"), int(ord_obj.get("qty", 1) or 1))

        if raw_status == "delivered" or keys:
            norm_status = "delivered"
        elif raw_status in ("cancelled", "canceled", "refunded", "failed"):
            norm_status = "cancelled"
        else:
            norm_status = "paid"

        return {
            "orderId": str(ord_obj.get("order_id") or ord_obj.get("orderId") or remote_order_id),
            "status": norm_status,
            "raw_status": raw_status,
            "deliveredKeys": keys,
            "deliveredKey": keys[0] if keys else "",
        }

    async def create_external_api_order(
        self,
        api_base_url: str,
        api_key: str,
        remote_product_id: str,
        quantity: int = 1,
        email: str | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        """Mua hàng tự động từ @DanteHubBot (`POST /orders`) hoặc cổng Reseller API v1."""
        base = self._normalize_external_base(api_base_url)
        r_pid = remote_product_id.strip()
        qty = max(1, int(quantity))
        client = self._get_http()

        if self.is_dantehub_url(base):
            raw_ref = idempotency_key or f"kt-{int(time.time() * 1000)}"
            safe_ref = re.sub(r"[^A-Za-z0-9._:-]", "-", raw_ref)[:64]
            payload_dh = {
                "product_id": r_pid,
                "qty": min(20, qty),
                "ref": safe_ref,
            }
            resp = await client.post(
                f"{base}/orders",
                headers=self._external_headers(api_key, idempotency_key=safe_ref),
                json=payload_dh,
                timeout=30.0,
            )
            data = resp.json()
            if resp.status_code >= 400 or data.get("ok") is False or "error" in data:
                err_obj = data.get("error")
                if isinstance(err_obj, dict):
                    err_msg = f"{err_obj.get('code', 'dante_error')}: {err_obj.get('message', '')}"
                else:
                    err_msg = str(err_obj or f"HTTP {resp.status_code}")
                raise RuntimeError(err_msg)

            ord_obj = data.get("order") if isinstance(data.get("order"), dict) else data
            oid = str(ord_obj.get("order_id") or ord_obj.get("orderId") or safe_ref)
            raw_st = str(ord_obj.get("status") or "processing").lower()
            keys = self._extract_dante_keys(ord_obj.get("delivery"), qty)

            # Nếu DanteHub trả status="processing", chờ nhanh 2 nhịp (1.5s + 2.0s) để lấy key ngay lập tức nếu có
            if not keys and raw_st in ("processing", "pending") and oid:
                for wait_sec in (1.5, 2.0):
                    await asyncio.sleep(wait_sec)
                    try:
                        polled = await self.get_external_api_order_status(base, api_key, oid)
                        if polled.get("deliveredKeys"):
                            keys = polled["deliveredKeys"]
                            raw_st = "delivered"
                            break
                        if polled.get("status") == "cancelled":
                            raise RuntimeError(f"Đơn hàng DanteHub {oid} đã bị hủy.")
                    except RuntimeError:
                        raise
                    except Exception:
                        pass

            norm_status = "delivered" if (keys or raw_st == "delivered") else "paid"
            return {
                "orderId": oid,
                "status": norm_status,
                "deliveredKeys": keys,
                "deliveredKey": keys[0] if keys else "",
                "amount": float(ord_obj.get("total", 0) or 0),
            }

        payload: dict[str, Any] = {
            "productId": r_pid,
            "quantity": qty,
        }
        if email:
            if qty == 1:
                payload["email"] = email.strip()
            else:
                payload["emails"] = [email.strip()] * qty
        resp = await client.post(
            f"{base}/orders",
            headers=self._external_headers(api_key, idempotency_key=idempotency_key),
            json=payload,
            timeout=30.0,
        )
        data = resp.json()
        if resp.status_code >= 400 or "error" in data:
            err_obj = data.get("error")
            if isinstance(err_obj, dict):
                err_msg = f"{err_obj.get('code', 'api_error')}: {err_obj.get('message', '')}"
            else:
                err_msg = str(err_obj or f"HTTP {resp.status_code}")
            raise RuntimeError(err_msg)
        return data

    async def sync_all_dante_backups(
        self,
        db: Any,
        dante_key: str,
        dante_url: str = DANTE_BASE_URL,
        auto_seed_defaults: bool = True,
    ) -> dict[str, int]:
        """Đồng bộ toàn bộ nguồn dự phòng @DanteHubBot trong 1 request duy nhất:
        - Nếu `auto_seed_defaults=True`, tự động đấu nối 21 sản phẩm tương đương giữa ProdSeller & DanteHub.
        - Cập nhật giá vốn VNĐ (theo tỷ giá `vnd_rate`) và tồn kho thực tế từ @DanteHubBot.
        """
        clean_key = (dante_key or self.dante_api_key).strip()
        if not clean_key:
            return {"linked": 0, "in_stock": 0, "seeded": 0}
        self.set_dante_credentials(clean_key, dante_url)

        catalog = await self.fetch_dantehub_catalog(dante_url, clean_key, force=True)
        dh_map = {str(item.get("id", "")).strip(): item for item in catalog if item.get("id")}
        rate = float(db.get_setting("vnd_rate", "25500") or 25500.0)
        bmap = db.get_all_backup_sources()

        seeded = 0
        if auto_seed_defaults:
            for ps_pid, dh_pid, src_name in DEFAULT_DANTE_MAPPINGS:
                existing_list = bmap.get(ps_pid, [])
                already_has = any(
                    s.get("source_type") == "api"
                    and (
                        str(s.get("remote_product_id", "")).strip() == dh_pid
                        or "dante" in str(s.get("source_name", "")).lower()
                    )
                    for s in existing_list
                )
                if not already_has and dh_pid in dh_map:
                    dh_item = dh_map[dh_pid]
                    usd_price = float(dh_item.get("price", 0) or 0)
                    cost_vnd = max(500, int(round(usd_price * rate)))
                    in_st = bool(dh_item.get("in_stock", False))
                    db.add_api_backup_source(
                        product_id=ps_pid,
                        source_name=src_name,
                        cost_vnd=cost_vnd,
                        api_base_url=dante_url,
                        api_key=clean_key,
                        remote_product_id=dh_pid,
                        remote_stock=50 if in_st else 0,
                    )
                    seeded += 1
            if seeded > 0:
                bmap = db.get_all_backup_sources()

        linked_cnt = 0
        in_stock_cnt = 0
        new_linked_ids: set[str] = {dh_id for _, dh_id, _ in DEFAULT_DANTE_MAPPINGS} | set(EXTRA_SKIP_DANTE_IDS)
        for _, src_list in bmap.items():
            for src in src_list:
                if src.get("source_type") != "api":
                    continue
                b_url = str(src.get("api_base_url", ""))
                if not self.is_dantehub_url(b_url) and "dante" not in str(src.get("source_name", "")).lower():
                    continue
                linked_cnt += 1
                r_pid = str(src.get("remote_product_id", "")).strip()
                if r_pid:
                    new_linked_ids.add(r_pid)
                dh_item = dh_map.get(r_pid)
                if not dh_item:
                    continue
                in_st = bool(dh_item.get("in_stock", False))
                new_st = 50 if in_st else 0
                if in_st and int(src.get("active", 0) or 0) == 1:
                    in_stock_cnt += 1
                usd_price = float(dh_item.get("price", 0) or 0)
                new_cost = max(500, int(round(usd_price * rate))) if usd_price > 0 else None
                db.update_api_backup_stock(int(src["id"]), new_st, new_cost)

        self._linked_dante_ids = new_linked_ids
        return {"linked": linked_cnt, "in_stock": in_stock_cnt, "seeded": seeded}

    async def fulfill_multi_source_order(
        self,
        db: Any,
        product: dict[str, Any],
        quantity: int = 1,
        email: str | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        """Định tuyến lấy hàng Đa Nguồn (Multi-Source Failover):
        1. Ưu tiên lấy từ Nguồn 1 (@ProdSellerBot đối với SP chung/ProdSeller, hoặc @DanteHubBot đối với SP độc quyền DanteHub) nếu còn hàng.
        2. Nếu Nguồn 1 hết hàng, thiếu số lượng hoặc gặp lỗi API đột xuất, tự động chuyển sang
           rút Key từ các Nguồn Dự Phòng (Kho Key nội bộ hoặc @DanteHubBot / API nguồn phụ, ưu tiên giá vốn rẻ nhất).
        """
        pid = str(product["id"])
        is_dante_primary = product.get("provider") == "dantehub" or pid.startswith("dh_")
        qty = max(1, int(quantity))
        unit_cost_usd = float(product.get("price", 0.0) or 0.0)
        primary_unit_cost_vnd = db.compute_wholesale_vnd(unit_cost_usd)

        _, _, primary_stock, _ = db.get_effective_product_stock(product)
        want_primary = qty if primary_stock is None else min(qty, max(0, primary_stock))

        all_keys: list[str] = []
        total_actual_cost_vnd = 0
        source_parts: list[str] = []
        ps_order_id = ""
        final_status = "delivered"
        used_backup = False
        last_primary_err: Exception | None = None
        last_backup_err: Exception | None = None

        rem_qty = qty

        # Bước 1: Thử lấy từ Nguồn 1 nếu Nguồn 1 báo còn hàng
        if want_primary > 0:
            try:
                if is_dante_primary:
                    dh_uuid = str(product.get("dante_uuid") or pid).strip()
                    dh_key = db.get_setting("dante_api_key", self.dante_api_key) or self.dante_api_key
                    dh_url = db.get_setting("dante_base_url", self.dante_base_url) or self.dante_base_url
                    p_resp = await self.create_external_api_order(
                        api_base_url=dh_url,
                        api_key=dh_key,
                        remote_product_id=dh_uuid,
                        quantity=want_primary,
                        email=email,
                        idempotency_key=idempotency_key,
                    )
                    p_keys: list[str] = []
                    if p_resp.get("deliveredKeys"):
                        p_keys = [str(k) for k in p_resp["deliveredKeys"]]
                    elif p_resp.get("deliveredKey"):
                        p_keys = [str(p_resp["deliveredKey"])]

                    oid = str(p_resp.get("orderId", ""))
                    ps_order_id = f"DANTE_{oid}" if oid else ""
                    p_status = str(p_resp.get("status", "delivered")).lower()
                    p_amt_usd = float(p_resp.get("amount", 0.0) or (unit_cost_usd * want_primary))
                    p_cost_vnd = db.compute_wholesale_vnd(p_amt_usd)

                    all_keys.extend(p_keys)
                    total_actual_cost_vnd += p_cost_vnd
                    source_parts.append(f"DanteHub (x{want_primary})")
                    if p_status in ("paid", "processing", "pending") and not p_keys:
                        final_status = "paid"
                        rem_qty -= want_primary
                    else:
                        rem_qty -= len(p_keys) if p_keys else want_primary
                else:
                    p_resp = await self.create_order(
                        product_id=pid,
                        quantity=want_primary,
                        email=email,
                        idempotency_key=idempotency_key,
                    )
                    p_keys = []
                    if p_resp.get("deliveredKeys"):
                        p_keys = [str(k) for k in p_resp["deliveredKeys"]]
                    elif p_resp.get("deliveredKey"):
                        p_keys = [str(p_resp["deliveredKey"])]

                    ps_order_id = str(p_resp.get("orderId", ""))
                    p_status = str(p_resp.get("status", "delivered"))
                    p_amt_usd = float(p_resp.get("amount", unit_cost_usd * want_primary))
                    p_cost_vnd = db.compute_wholesale_vnd(p_amt_usd)

                    all_keys.extend(p_keys)
                    total_actual_cost_vnd += p_cost_vnd
                    source_parts.append(f"ProdSeller (x{want_primary})")
                    if p_status == "paid" and not p_keys:
                        final_status = "paid"
                        rem_qty -= want_primary
                    else:
                        rem_qty -= len(p_keys) if p_keys else want_primary
            except Exception as exc:
                last_primary_err = exc
                logging.warning("Nguồn 1 lỗi khi mua %s (x%s), chuyển sang Nguồn Dự Phòng: %s", pid, want_primary, exc)

        # Bước 2: Bù số lượng còn thiếu từ các Nguồn Dự Phòng (ưu tiên giá vốn thấp nhất trước)
        popped_rollback_log: list[tuple[int, list[str]]] = []
        if rem_qty > 0:
            backup_sources = [
                s
                for s in db.get_product_backup_sources(pid)
                if int(s.get("active", 0) or 0) == 1 and int(s.get("available_stock", 0) or 0) > 0
            ]
            for b_src in backup_sources:
                if rem_qty <= 0:
                    break
                sid = int(b_src["id"])
                sname = str(b_src["source_name"])
                stype = str(b_src.get("source_type", "local_stock") or "local_stock")
                b_cost_vnd = int(b_src["cost_vnd"])
                avail = max(0, int(b_src.get("available_stock", 0) or 0))
                take_b = min(rem_qty, avail)
                if take_b <= 0:
                    continue

                if stype == "local_stock":
                    popped = db.pop_backup_keys_atomic(sid, take_b)
                    if popped:
                        used_backup = True
                        popped_rollback_log.append((sid, popped))
                        all_keys.extend(popped)
                        total_actual_cost_vnd += len(popped) * b_cost_vnd
                        source_parts.append(f"{sname} (x{len(popped)})")
                        rem_qty -= len(popped)
                elif stype == "api":
                    try:
                        ext_idem = f"{idempotency_key or 'ext'}_b{sid}"
                        ext_key = str(b_src.get("api_key", "")).strip() or db.get_setting("dante_api_key", "")
                        ext_url = str(b_src.get("api_base_url", "")).strip() or db.get_setting("dante_base_url", DANTE_BASE_URL)
                        ext_resp = await self.create_external_api_order(
                            api_base_url=ext_url,
                            api_key=ext_key,
                            remote_product_id=str(b_src.get("remote_product_id", "")),
                            quantity=take_b,
                            email=email,
                            idempotency_key=ext_idem,
                        )
                        ext_keys: list[str] = []
                        if ext_resp.get("deliveredKeys"):
                            ext_keys = [str(k) for k in ext_resp["deliveredKeys"]]
                        elif ext_resp.get("deliveredKey"):
                            ext_keys = [str(ext_resp["deliveredKey"])]
                        ext_status = str(ext_resp.get("status", "delivered")).lower()
                        got_cnt = len(ext_keys) if ext_keys else take_b
                        used_backup = True
                        all_keys.extend(ext_keys)
                        total_actual_cost_vnd += got_cnt * b_cost_vnd
                        source_parts.append(f"{sname} [API] (x{got_cnt})")
                        rem_qty -= got_cnt
                        if not self.is_dantehub_url(ext_url):
                            new_rem_stock = max(0, avail - got_cnt)
                            db.update_api_backup_stock(sid, new_rem_stock)
                        if ext_status in ("paid", "processing", "pending") and not ext_keys:
                            final_status = "paid"
                        if not ps_order_id and ext_resp.get("orderId"):
                            ps_order_id = f"EXT_{sid}_{ext_resp['orderId']}"
                    except Exception as ext_exc:
                        last_backup_err = ext_exc
                        logging.warning("Nguồn API dự phòng %s (#%s) lỗi: %s", sname, sid, ext_exc)

        if rem_qty > 0:
            # Nếu chưa mua được gì từ Nguồn 1 mà kho dự phòng cũng không đủ -> trả lại key dự phòng vào kho và báo lỗi
            if len(all_keys) == sum(len(klist) for _, klist in popped_rollback_log) and final_status != "paid":
                for sid, klist in popped_rollback_log:
                    db.restore_backup_keys(sid, klist)
                if last_backup_err is not None:
                    raise RuntimeError(f"Nguồn dự phòng báo lỗi: {last_backup_err}")
                if last_primary_err is not None:
                    raise RuntimeError(str(last_primary_err))
                raise RuntimeError("Kho hàng chính và kho dự phòng hiện không đủ số lượng yêu cầu.")

        if not ps_order_id:
            ps_order_id = f"BACKUP_{int(time.time())}"

        return {
            "deliveredKeys": all_keys,
            "deliveredKey": all_keys[0] if all_keys else "",
            "orderId": ps_order_id,
            "status": final_status,
            "actual_cost_vnd": total_actual_cost_vnd or (primary_unit_cost_vnd * qty),
            "source_summary": " + ".join(source_parts) if source_parts else ("DanteHub" if is_dante_primary else "ProdSeller"),
            "used_backup": used_backup,
        }

