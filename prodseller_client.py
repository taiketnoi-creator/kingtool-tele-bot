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
    ("youtube", None, "▶️ "),
    ("hma", None, "🛡️ "),
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

    async def fetch_external_api_product(
        self,
        api_base_url: str,
        api_key: str,
        remote_product_id: str,
    ) -> dict[str, Any]:
        """Lấy tồn kho và giá từ cổng Reseller API v1 của nguồn dự phòng bên ngoài."""
        base = api_base_url.strip().rstrip("/")
        if not base.endswith("/v1"):
            base = f"{base}/v1"
        client = self._get_http()
        headers = {
            "X-API-Key": api_key.strip(),
            "Content-Type": "application/json",
            "User-Agent": "KingToolMultiSourceRouter/1.0",
        }
        resp = await client.get(f"{base}/products/{remote_product_id.strip()}", headers=headers, timeout=15.0)
        resp.raise_for_status()
        return resp.json()

    async def create_external_api_order(
        self,
        api_base_url: str,
        api_key: str,
        remote_product_id: str,
        quantity: int = 1,
        email: str | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        """Mua hàng tự động từ cổng Reseller API v1 của nguồn dự phòng bên ngoài."""
        base = api_base_url.strip().rstrip("/")
        if not base.endswith("/v1"):
            base = f"{base}/v1"
        payload: dict[str, Any] = {
            "productId": remote_product_id.strip(),
            "quantity": quantity,
        }
        if email:
            if quantity == 1:
                payload["email"] = email.strip()
            else:
                payload["emails"] = [email.strip()] * quantity
        headers = {
            "X-API-Key": api_key.strip(),
            "Content-Type": "application/json",
            "User-Agent": "KingToolMultiSourceRouter/1.0",
        }
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key[:100]
        client = self._get_http()
        resp = await client.post(f"{base}/orders", headers=headers, json=payload, timeout=30.0)
        data = resp.json()
        if resp.status_code >= 400 or "error" in data:
            err_msg = data.get("error") or f"HTTP {resp.status_code}"
            raise RuntimeError(err_msg)
        return data

    async def fulfill_multi_source_order(
        self,
        db: Any,
        product: dict[str, Any],
        quantity: int = 1,
        email: str | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        """Định tuyến lấy hàng Đa Nguồn (Multi-Source Failover):
        1. Ưu tiên lấy từ Nguồn 1 (@ProdSellerBot) nếu còn hàng.
        2. Nếu Nguồn 1 hết hàng, thiếu số lượng hoặc gặp lỗi API đột xuất, tự động chuyển sang
           rút Key từ các Nguồn Dự Phòng (Kho Key nội bộ hoặc API nguồn phụ, ưu tiên giá vốn rẻ nhất).
        """
        pid = str(product["id"])
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

        rem_qty = qty

        # Bước 1: Thử lấy từ Nguồn 1 (@ProdSellerBot) nếu Nguồn 1 báo còn hàng
        if want_primary > 0:
            try:
                p_resp = await self.create_order(
                    product_id=pid,
                    quantity=want_primary,
                    email=email,
                    idempotency_key=idempotency_key,
                )
                p_keys: list[str] = []
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
                logging.warning("Nguồn 1 ProdSeller lỗi khi mua %s (x%s), chuyển sang Nguồn Dự Phòng: %s", pid, want_primary, exc)

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
                        ext_resp = await self.create_external_api_order(
                            api_base_url=str(b_src.get("api_base_url", "")),
                            api_key=str(b_src.get("api_key", "")),
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
                        got_cnt = len(ext_keys) if ext_keys else take_b
                        used_backup = True
                        all_keys.extend(ext_keys)
                        total_actual_cost_vnd += got_cnt * b_cost_vnd
                        source_parts.append(f"{sname} [API] (x{got_cnt})")
                        rem_qty -= got_cnt
                        new_rem_stock = max(0, avail - got_cnt)
                        db.update_api_backup_stock(sid, new_rem_stock)
                        if not ps_order_id and ext_resp.get("orderId"):
                            ps_order_id = f"EXT_{sid}_{ext_resp['orderId']}"
                    except Exception as ext_exc:
                        logging.warning("Nguồn API dự phòng %s (#%s) lỗi: %s", sname, sid, ext_exc)

        if rem_qty > 0:
            # Nếu chưa mua được gì từ ProdSeller mà kho dự phòng cũng không đủ -> trả lại key dự phòng vào kho và báo lỗi
            if len(all_keys) == sum(len(klist) for _, klist in popped_rollback_log):
                for sid, klist in popped_rollback_log:
                    db.restore_backup_keys(sid, klist)
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
            "source_summary": " + ".join(source_parts) if source_parts else "ProdSeller",
            "used_backup": used_backup,
        }

