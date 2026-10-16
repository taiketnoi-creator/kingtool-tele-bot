"""Client bất đồng bộ kết nối tới ProdSeller Official API v1 (https://prodseller.com/v1)."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

import httpx

BASE_URL = "https://prodseller.com/v1"

# Custom Emoji Icon IDs + Unicode Icons cho từng nhóm và từng sản phẩm
GROUP_ICONS: dict[str, int] = {
    "Gmail": 5307602416961609760,
    "ChatGPT CODEX": 5796185041717433060,
    "Claude AI": 6174520215376763867,
    "CapCut": 6124915477706705232,
    "Canva": 5879982576671657703,
}

GROUP_EMOJI: dict[str, str] = {
    "Gmail": "📧 ",
    "ChatGPT CODEX": "🤖 ",
    "Claude AI": "🧠 ",
    "CapCut": "🎬 ",
    "Canva": "🎨 ",
}

PRODUCT_KEYWORD_ICONS: list[tuple[str, int | None, str]] = [
    ("spotify", 5926990577114550753, "🎧 "),
    ("elevenlabs", 6219689196722854904, "🎙️ "),
    ("gmail", 5307602416961609760, "📧 "),
    ("scribd", None, "📦 "),
    ("muse ai", 5891219692881714411, "🎵 "),
    ("codex", 5796185041717433060, "🤖 "),
    ("claude", 6174520215376763867, "🧠 "),
    ("wispr", 6069015112549669594, "🗣️ "),
    ("apple tv", 5469922901958346945, "🍎 "),
    ("duolingo", 5796371348808799072, "🦉 "),
    ("capcut", 6124915477706705232, "🎬 "),
    ("hbo", 5346319945112240722, "🎞️ "),
    ("telegram", None, "✈️ "),
    ("autodesk", 6305045014531548800, "📐 "),
    ("framer", 6312056780570499991, "⚡ "),
    ("jetbrains", 5300959605793235101, "💻 "),
    ("avira", 5350619413533958825, "🛡️ "),
    ("edx", 5769598970816897041, "🎓 "),
    ("gemini", 5206660927339924387, "✨ "),
    ("figma", 5393312805795407636, "🎨 "),
    ("miro", None, "📝 "),
    ("ilovepdf", 6239983230729068544, "📄 "),
    ("outlook", 5796683820564484775, "📨 "),
    ("hotmail", 5796683820564484775, "📨 "),
    ("adobe", 6145685845060883545, "🅰️ "),
    ("notion", 5233464190441662039, "📓 "),
    ("prime video", 6111801057061374810, "📺 "),
    ("canva", 5879982576671657703, "🖌️ "),
    ("office 365", 6102808052673548025, "💼 "),
    ("microsoft", 6102808052673548025, "💼 "),
]


def get_product_icon_and_prefix(product_name: str, use_fallback_emoji: bool = False) -> tuple[int | None, str]:
    """Trả về (custom_emoji_icon_id, text_prefix) giống hệt bản gốc @ProdSellerBot."""
    low = product_name.lower()
    for kw, icon_id, prefix in PRODUCT_KEYWORD_ICONS:
        if kw in low:
            if icon_id is not None and not use_fallback_emoji:
                return icon_id, ""
            return icon_id, prefix
    return None, "📦 "


def detect_plan_group(product_name: str) -> str | None:
    """Phân nhóm sản phẩm đa gói (Sub-plans) giống hệt giao diện @ProdSellerBot."""
    low = product_name.lower()
    if "gmail" in low:
        return "Gmail"
    if "codex" in low:
        return "ChatGPT CODEX"
    if "claude" in low:
        return "Claude AI"
    if "capcut" in low:
        return "CapCut"
    if "canva" in low:
        return "Canva"
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
    def __init__(self, api_key: str) -> None:
        self.api_key = api_key.strip()
        self._products_cache: list[dict[str, Any]] = []
        self._stock_cache: dict[str, int | None] = {}
        self._last_sync: float = 0.0
        self._lock = asyncio.Lock()
        self._http: httpx.AsyncClient | None = None

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

    async def get_balance(self) -> dict[str, Any]:
        client = self._get_http()
        resp = await client.get(f"{BASE_URL}/balance", headers=self._headers())
        resp.raise_for_status()
        return resp.json()

    async def fetch_product_detail(self, product_id: str) -> dict[str, Any]:
        client = self._get_http()
        resp = await client.get(f"{BASE_URL}/products/{product_id}", headers=self._headers())
        resp.raise_for_status()
        data = resp.json()
        if "stock" in data:
            self._stock_cache[product_id] = data["stock"]
        return data

    async def sync_products(self, force: bool = False, cache_ttl: float = 60.0) -> list[dict[str, Any]]:
        """Lấy danh sách sản phẩm và đồng bộ số lượng tồn kho chi tiết.
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
            resp = await client.get(f"{BASE_URL}/products", headers=self._headers())
            resp.raise_for_status()
            products: list[dict[str, Any]] = resp.json().get("products", [])

            sem = asyncio.Semaphore(8)

            async def _fetch_stock(p: dict[str, Any]) -> None:
                pid = p["id"]
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

            self._products_cache = list(reversed(products))
            self._last_sync = time.time()
            return self._products_cache

    async def get_product_by_id(self, product_id: str, refresh: bool = False) -> dict[str, Any] | None:
        """Lấy thông tin 1 sản phẩm. Nếu refresh=True chỉ gọi API chi tiết của đúng sản phẩm đó
        thay vì quét lại toàn bộ 29 sản phẩm, giúp mở trang chi tiết & mua hàng nhanh gấp 10 lần.
        """
        if not self._products_cache:
            await self.sync_products(force=True)

        for p in self._products_cache:
            if p["id"] == product_id:
                if refresh:
                    try:
                        detail = await self.fetch_product_detail(product_id)
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
