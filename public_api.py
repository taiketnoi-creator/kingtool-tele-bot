"""Cổng Public Reseller API v1 (/v1/*) và Trang Tài Liệu (/api-docs) giống 100% @ProdSellerBot."""

from __future__ import annotations

import asyncio
import json
import logging
import math
import os
import time
import urllib.parse
from typing import Any

from database import Database, TIER_DISCOUNTS
from i18n import localize_product_description
from prodseller_client import ProdSellerClient

logger = logging.getLogger("reseller_bot.api")

# Bộ nhớ đệm chống trùng đơn (Idempotency-Key -> (timestamp, response_dict, status_code))
_IDEMPOTENCY_CACHE: dict[str, tuple[float, dict[str, Any], int]] = {}
# Khóa chống race-condition theo từng user khi gọi POST /v1/orders
_API_USER_LOCKS: dict[int, asyncio.Lock] = {}


def get_public_base_url() -> str:
    ext = os.getenv("RENDER_EXTERNAL_URL", "").strip().rstrip("/")
    if ext:
        return ext
    return "https://kingtool-tele-bot.onrender.com"


def _format_order_json(o: dict[str, Any]) -> dict[str, Any]:
    raw_keys = o.get("delivered_keys", "[]")
    keys: list[str] = []
    if isinstance(raw_keys, list):
        keys = [str(k) for k in raw_keys]
    elif isinstance(raw_keys, str) and raw_keys.strip():
        try:
            parsed = json.loads(raw_keys)
            if isinstance(parsed, list):
                keys = [str(k) for k in parsed]
            elif parsed:
                keys = [str(parsed)]
        except Exception:
            keys = [raw_keys]

    res: dict[str, Any] = {
        "orderId": str(o["id"]),
        "status": o.get("status", "delivered"),
        "product": {
            "id": str(o.get("product_id", "")),
            "name": str(o.get("product_name", "")),
        },
        "quantity": int(o.get("quantity", 1) or 1),
        "amount": int(round(float(o.get("retail_price", 0) or 0))),
        "currency": "VND",
        "createdAt": str(o.get("created_at", "")),
    }
    if o.get("activation_email"):
        res["activation"] = {
            "emails": [o["activation_email"]],
            "eta": "ASAP",
        }
    if keys:
        res["deliveredKey"] = keys[0]
        res["deliveredKeys"] = keys
    return res


def render_api_docs_html(base_url: str, bot_username: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="vi">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>KingTool Shop — Tài Liệu API Tự Động (Public API v1)</title>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    :root {{
      --bg:       #0f0f17;
      --card:     #1a1a2e;
      --border:   rgba(255,255,255,.08);
      --accent:   #7c3aed;
      --accent2:  #a78bfa;
      --text:     #e2e8f0;
      --muted:    #94a3b8;
      --green:    #22c55e;
      --blue:     #3b82f6;
      --orange:   #f97316;
      --red:      #ef4444;
      --code-bg:  #12121e;
    }}
    body {{ background: var(--bg); color: var(--text); font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; line-height: 1.65; }}
    .layout {{ display: flex; min-height: 100vh; }}
    .sidebar {{ width: 270px; background: var(--card); border-right: 1px solid var(--border); padding: 28px 0; position: sticky; top: 0; height: 100vh; overflow-y: auto; flex-shrink: 0; }}
    .content {{ flex: 1; padding: 48px 64px; max-width: 920px; }}
    .brand {{ padding: 0 24px 24px; border-bottom: 1px solid var(--border); }}
    .brand-logo {{ display: flex; align-items: center; gap: 10px; margin-bottom: 4px; }}
    .brand-icon {{ width: 32px; height: 32px; background: var(--accent); border-radius: 8px; display: flex; align-items: center; justify-content: center; font-weight: bold; color: #fff; }}
    .brand-name {{ font-weight: 700; font-size: 1.05rem; }}
    .brand-version {{ font-size: .75rem; color: var(--muted); }}
    .nav-section {{ padding: 20px 12px 8px; }}
    .nav-section-title {{ font-size: .68rem; font-weight: 600; text-transform: uppercase; letter-spacing: .08em; color: var(--muted); padding: 0 12px; margin-bottom: 6px; }}
    .nav-link {{ display: flex; align-items: center; gap: 10px; padding: 8px 12px; border-radius: 8px; text-decoration: none; color: var(--muted); font-size: .85rem; transition: all .15s; }}
    .nav-link:hover {{ background: rgba(124,58,237,.12); color: var(--accent2); }}
    .method-pill {{ font-size: .6rem; font-weight: 700; padding: 2px 6px; border-radius: 4px; flex-shrink: 0; }}
    .get {{ background: rgba(34,197,94,.15); color: var(--green); }}
    .post {{ background: rgba(59,130,246,.15); color: var(--blue); }}
    h1 {{ font-size: 2.1rem; font-weight: 800; margin-bottom: 12px; background: linear-gradient(135deg, #fff, var(--accent2)); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }}
    h2 {{ font-size: 1.35rem; font-weight: 700; margin: 44px 0 16px; padding-bottom: 10px; border-bottom: 1px solid var(--border); }}
    h3 {{ font-size: 1.02rem; font-weight: 600; margin: 24px 0 10px; }}
    p {{ color: var(--muted); margin-bottom: 14px; }}
    a {{ color: var(--accent2); text-decoration: none; }}
    .base-url {{ display: flex; align-items: center; gap: 12px; background: var(--card); border: 1px solid var(--border); border-radius: 10px; padding: 14px 18px; margin-bottom: 28px; }}
    .base-url-label {{ font-size: .75rem; font-weight: 600; color: var(--muted); text-transform: uppercase; letter-spacing: .06em; }}
    .base-url-val {{ font-family: monospace; font-size: .92rem; color: var(--accent2); }}
    .info-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; margin-bottom: 32px; }}
    .info-card {{ background: var(--card); border: 1px solid var(--border); border-radius: 10px; padding: 18px; }}
    .info-card h4 {{ font-size: .92rem; font-weight: 600; margin-bottom: 6px; color: #fff; }}
    .info-card p {{ font-size: .83rem; margin: 0; }}
    .endpoint {{ background: var(--card); border: 1px solid var(--border); border-radius: 12px; margin-bottom: 24px; overflow: hidden; }}
    .endpoint-header {{ display: flex; align-items: center; gap: 14px; padding: 15px 20px; border-bottom: 1px solid var(--border); }}
    .method-badge {{ font-size: .72rem; font-weight: 700; padding: 4px 10px; border-radius: 6px; }}
    .method-badge.get {{ background: rgba(34,197,94,.15); color: var(--green); }}
    .method-badge.post {{ background: rgba(59,130,246,.15); color: var(--blue); }}
    .endpoint-path {{ font-family: monospace; font-size: .95rem; font-weight: 600; }}
    .endpoint-desc {{ font-size: .82rem; color: var(--muted); margin-left: auto; }}
    .endpoint-body {{ padding: 20px; }}
    pre {{ background: var(--code-bg); border: 1px solid var(--border); border-radius: 8px; padding: 15px 18px; overflow-x: auto; font-family: monospace; font-size: .83rem; line-height: 1.65; margin: 12px 0; color: #e2e8f0; }}
    code {{ font-family: monospace; font-size: .85em; background: rgba(124,58,237,.15); color: var(--accent2); padding: 2px 6px; border-radius: 4px; }}
    .auth-box {{ background: rgba(124,58,237,.08); border: 1px solid rgba(124,58,237,.24); border-radius: 10px; padding: 16px 20px; margin-bottom: 24px; }}
    .auth-box h4 {{ font-size: .92rem; font-weight: 600; margin-bottom: 6px; color: var(--accent2); }}
    .error-table {{ width: 100%; border-collapse: collapse; font-size: .83rem; margin-top: 10px; }}
    .error-table th, .error-table td {{ text-align: left; padding: 10px 14px; border-top: 1px solid var(--border); }}
    .error-table th {{ background: rgba(255,255,255,.04); color: var(--muted); text-transform: uppercase; font-size: .72rem; }}
    .footer {{ margin-top: 64px; padding-top: 24px; border-top: 1px solid var(--border); font-size: .82rem; color: var(--muted); }}
    @media (max-width: 768px) {{
      .layout {{ flex-direction: column; }}
      .sidebar {{ width: 100%; height: auto; position: static; }}
      .content {{ padding: 24px 18px; }}
    }}
  </style>
</head>
<body>
<div class="layout">
  <aside class="sidebar">
    <div class="brand">
      <div class="brand-logo">
        <div class="brand-icon">⚡</div>
        <div class="brand-name">KingTool Shop</div>
      </div>
      <div class="brand-version">Public Reseller API · v1 (VNĐ)</div>
    </div>
    <div class="nav-section">
      <div class="nav-section-title">Giới thiệu</div>
      <a href="#overview" class="nav-link">Tổng quan & Cơ chế</a>
      <a href="#authentication" class="nav-link">Xác thực (X-API-Key)</a>
      <a href="#errors" class="nav-link">Mã lỗi (Error Codes)</a>
    </div>
    <div class="nav-section">
      <div class="nav-section-title">Cổng kết nối (Endpoints)</div>
      <a href="#get-products" class="nav-link"><span class="method-pill get">GET</span> Danh sách sản phẩm</a>
      <a href="#get-product" class="nav-link"><span class="method-pill get">GET</span> Chi tiết sản phẩm</a>
      <a href="#get-balance" class="nav-link"><span class="method-pill get">GET</span> Kiểm tra số dư</a>
      <a href="#post-orders" class="nav-link"><span class="method-pill post">POST</span> Mua hàng tự động</a>
      <a href="#list-orders" class="nav-link"><span class="method-pill get">GET</span> Lịch sử đơn hàng</a>
      <a href="#get-order" class="nav-link"><span class="method-pill get">GET</span> Trạng thái đơn hàng</a>
    </div>
    <div class="nav-section">
      <div class="nav-section-title">Code mẫu đấu nối</div>
      <a href="#example-python" class="nav-link">Python</a>
      <a href="#example-node" class="nav-link">Node.js</a>
    </div>
  </aside>

  <main class="content">
    <section id="overview">
      <h1>KingTool Shop Reseller API</h1>
      <p>
        Hệ thống API giúp bạn đấu nối kho tài khoản/phần mềm tự động 24/7 vào <strong>Website, Bot Telegram hoặc Tool MMO</strong> riêng của bạn.
        Thanh toán 100% bằng số dư ví <strong>VNĐ</strong> (nạp qua VietQR trên <a href="https://t.me/{bot_username}">@{bot_username}</a>), tự động áp dụng chiết khấu Hạng VIP (Silver/Gold) và nhận Key ngay lập tức.
      </p>

      <div class="base-url">
        <span class="base-url-label">Base URL</span>
        <span class="base-url-val">{base_url}/v1</span>
      </div>

      <div class="info-grid">
        <div class="info-card">
          <h4>🔑 Xác thực đơn giản</h4>
          <p>Lấy mã <code>ktk_...</code> tại mục <strong>API</strong> trên Bot và truyền vào header <code>X-API-Key</code>.</p>
        </div>
        <div class="info-card">
          <h4>💰 Trừ ví VNĐ tự động</h4>
          <p>Đơn hàng trừ trực tiếp từ số dư VNĐ của bạn trên Bot kèm ưu đãi Hạng thành viên.</p>
        </div>
        <div class="info-card">
          <h4>⚡ Giao Key tức thì</h4>
          <p>Trả về <code>deliveredKey</code> / <code>deliveredKeys</code> ngay trong phản hồi JSON.</p>
        </div>
      </div>
    </section>

    <section id="authentication">
      <h2>Xác thực (Authentication)</h2>
      <p>Mọi request gọi tới API cần đính kèm mã khóa của bạn trong HTTP Header <code>X-API-Key</code>.</p>
      <div class="auth-box">
        <h4>Định dạng Header</h4>
        <p><code>X-API-Key: ktk_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx</code></p>
      </div>
      <pre>curl -H "X-API-Key: ktk_YOUR_KEY" {base_url}/v1/balance</pre>
    </section>

    <section id="get-products">
      <h2>Các cổng API (Endpoints)</h2>
      <div class="endpoint">
        <div class="endpoint-header">
          <span class="method-badge get">GET</span>
          <span class="endpoint-path">/v1/products</span>
          <span class="endpoint-desc">Lấy danh sách sản phẩm & giá sỉ của bạn</span>
        </div>
        <div class="endpoint-body">
          <p>Trả về toàn bộ sản phẩm đang mở bán. Trường <code>price</code> là đơn giá VNĐ thực tế tài khoản của bạn sẽ thanh toán (đã trừ chiết khấu VIP của bạn). Trường <code>publicPrice</code> là giá bán lẻ niêm yết.</p>
          <pre>{{
  "products": [
    {{
      "id": "64abc...",
      "name": "Spotify premium account 1M FW",
      "description": "Bảo hành trọn thời gian sử dụng...",
      "price": 29000,
      "publicPrice": 31000,
      "currency": "VND",
      "stock": 12,
      "inStock": true,
      "requiresEmailActivation": false,
      "delivery": {{ "type": "instant" }}
    }}
  ]
}}</pre>
        </div>
      </div>
    </section>

    <section id="get-product">
      <div class="endpoint">
        <div class="endpoint-header">
          <span class="method-badge get">GET</span>
          <span class="endpoint-path">/v1/products/:id</span>
          <span class="endpoint-desc">Xem chi tiết 1 sản phẩm & tồn kho thực tế</span>
        </div>
        <div class="endpoint-body">
          <pre>curl -H "X-API-Key: ktk_YOUR_KEY" {base_url}/v1/products/64abc...</pre>
        </div>
      </div>
    </section>

    <section id="get-balance">
      <div class="endpoint">
        <div class="endpoint-header">
          <span class="method-badge get">GET</span>
          <span class="endpoint-path">/v1/balance</span>
          <span class="endpoint-desc">Kiểm tra số dư ví VNĐ & Hạng thành viên</span>
        </div>
        <div class="endpoint-body">
          <pre>{{
  "telegramId": 8110826820,
  "username": "kingtool_reseller",
  "balance": 500000,
  "currency": "VND",
  "membership": "gold"
}}</pre>
        </div>
      </div>
    </section>

    <section id="post-orders">
      <div class="endpoint">
        <div class="endpoint-header">
          <span class="method-badge post">POST</span>
          <span class="endpoint-path">/v1/orders</span>
          <span class="endpoint-desc">Mua hàng tự động (trừ số dư ví VNĐ)</span>
        </div>
        <div class="endpoint-body">
          <p>Gửi JSON body gồm <code>productId</code>, <code>quantity</code> (mặc định 1), và <code>email</code> nếu sản phẩm có <code>requiresEmailActivation: true</code>. Khuyến nghị gửi kèm header <code>Idempotency-Key</code> để chống trừ tiền trùng khi mạng chập chờn.</p>
          <pre>// Request Body:
{{
  "productId": "64abc...",
  "quantity": 1
}}

// Response (Giao key ngay lập tức):
{{
  "orderId": "105",
  "status": "delivered",
  "product": {{ "id": "64abc...", "name": "Spotify premium account 1M FW" }},
  "quantity": 1,
  "amount": 29000,
  "currency": "VND",
  "membershipDiscount": 5,
  "discountAmount": 2000,
  "deliveredKey": "user@gmail.com:pass123",
  "deliveredKeys": ["user@gmail.com:pass123"],
  "createdAt": "2026-10-17 13:00:00"
}}</pre>
        </div>
      </div>
    </section>

    <section id="list-orders">
      <div class="endpoint">
        <div class="endpoint-header">
          <span class="method-badge get">GET</span>
          <span class="endpoint-path">/v1/orders</span>
          <span class="endpoint-desc">Lịch sử đơn hàng đã mua</span>
        </div>
        <div class="endpoint-body">
          <p>Hỗ trợ query <code>?page=1&amp;limit=50&amp;status=delivered</code>.</p>
        </div>
      </div>
    </section>

    <section id="get-order">
      <div class="endpoint">
        <div class="endpoint-header">
          <span class="method-badge get">GET</span>
          <span class="endpoint-path">/v1/orders/:id</span>
          <span class="endpoint-desc">Kiểm tra trạng thái đơn hàng & Key</span>
        </div>
        <div class="endpoint-body">
          <p>Dùng để kiểm tra các đơn hàng kích hoạt qua Email chuyển từ trạng thái <code>paid</code> sang <code>delivered</code>.</p>
        </div>
      </div>
    </section>

    <section id="errors">
      <h2>Bảng Mã Lỗi Chuẩn (HTTP Status Codes)</h2>
      <table class="error-table">
        <thead><tr><th>Mã HTTP</th><th>Ý nghĩa</th></tr></thead>
        <tbody>
          <tr><td>401</td><td>Thiếu hoặc sai mã <code>X-API-Key</code></td></tr>
          <tr><td>400</td><td>Tham số đầu vào không hợp lệ (thiếu <code>productId</code>, thiếu <code>email</code> kích hoạt...)</td></tr>
          <tr><td>402</td><td>Số dư ví VNĐ không đủ để thanh toán đơn hàng</td></tr>
          <tr><td>404</td><td>Không tìm thấy sản phẩm hoặc đơn hàng</td></tr>
          <tr><td>409</td><td>Sản phẩm tạm hết hàng trong kho</td></tr>
        </tbody>
      </table>
    </section>

    <section id="example-python">
      <h2>Code Mẫu Đấu Nối (Python & Node.js)</h2>
      <h3>Python</h3>
      <pre>import requests

API_KEY  = "ktk_YOUR_KEY_HERE"
BASE_URL = "{base_url}/v1"
HEADERS  = {{"X-API-Key": API_KEY}}

# 1. Xem số dư VNĐ
bal = requests.get(f"{{BASE_URL}}/balance", headers=HEADERS).json()
print("Số dư hiện tại:", bal["balance"], "VNĐ")

# 2. Lấy danh sách sản phẩm
products = requests.get(f"{{BASE_URL}}/products", headers=HEADERS).json()["products"]
first_item = products[0]

# 3. Đặt mua tự động 1 sản phẩm
order = requests.post(
    f"{{BASE_URL}}/orders",
    headers={{**HEADERS, "Idempotency-Key": "don_hang_001"}},
    json={{"productId": first_item["id"], "quantity": 1}}
).json()
print("Key nhận được:", order.get("deliveredKey"))</pre>
    </section>

    <section id="example-node">
      <h3>Node.js</h3>
      <pre>const API_KEY  = 'ktk_YOUR_KEY_HERE';
const BASE_URL = '{base_url}/v1';
const headers  = {{ 'X-API-Key': API_KEY, 'Content-Type': 'application/json' }};

const {{ products }} = await fetch(`${{BASE_URL}}/products`, {{ headers }}).then(r => r.json());
const order = await fetch(`${{BASE_URL}}/orders`, {{
  method: 'POST',
  headers,
  body: JSON.stringify({{ productId: products[0].id, quantity: 1 }})
}}).then(r => r.json());

console.log('Key nhận được:', order.deliveredKey);</pre>
    </section>

    <div class="footer">
      <p>KingTool Shop Public API v1 · <a href="https://t.me/{bot_username}">@{bot_username}</a></p>
    </div>
  </main>
</div>
</body>
</html>"""


async def handle_http_request(
    reader: asyncio.StreamReader,
    writer: asyncio.StreamWriter,
    *,
    db: Database,
    ps_client: ProdSellerClient,
    bot_client: Any = None,
    bot_username: str = "KingToolShop_bot",
    admin_ids: set[int] | None = None,
) -> None:
    """Xử lý toàn bộ HTTP Request: /health, /api-docs và 6 cổng Public Reseller API (/v1/*)."""
    try:
        raw_head = await asyncio.wait_for(reader.readuntil(b"\r\n\r\n"), timeout=10.0)
    except asyncio.LimitOverrunError:
        raw_head = await asyncio.wait_for(reader.read(8192), timeout=5.0)
    except Exception:
        try:
            writer.close()
            await writer.wait_closed()
        except Exception:
            pass
        return

    try:
        head_Part, _, remainder = raw_head.partition(b"\r\n\r\n")
        lines = head_Part.decode("utf-8", errors="replace").split("\r\n")
        if not lines or not lines[0]:
            return
        req_parts = lines[0].split(" ")
        method = req_parts[0].upper() if len(req_parts) >= 1 else "GET"
        raw_target = req_parts[1] if len(req_parts) >= 2 else "/"

        headers: dict[str, str] = {}
        for line in lines[1:]:
            if ":" in line:
                k, v = line.split(":", 1)
                headers[k.strip().lower()] = v.strip()

        content_length = int(headers.get("content-length", "0") or 0)
        body_bytes = remainder
        while len(body_bytes) < content_length and content_length <= 65536:
            chunk = await asyncio.wait_for(reader.read(content_length - len(body_bytes)), timeout=10.0)
            if not chunk:
                break
            body_bytes += chunk

        parsed_url = urllib.parse.urlsplit(raw_target)
        path = parsed_url.path.rstrip("/") or "/"
        query_params = dict(urllib.parse.parse_qsl(parsed_url.query))

        # CORS preflight
        if method == "OPTIONS":
            await _send_response(writer, 204, b"", content_type="text/plain")
            return

        # 1. Trang Health-Check (/ và /health)
        if path in ("/", "/health") and method == "GET":
            db_mode = "supabase_postgres" if getattr(db, "use_postgres", False) else "local_sqlite"
            await _send_json(
                writer,
                200,
                {
                    "ok": True,
                    "bot": f"@{bot_username}",
                    "database": db_mode,
                    "api": "v1",
                    "docs": f"{get_public_base_url()}/api-docs",
                    "status": "running",
                },
            )
            return

        # 2. Trang Tài Liệu API (/api-docs)
        if path == "/api-docs" and method == "GET":
            html = render_api_docs_html(get_public_base_url(), bot_username)
            await _send_response(writer, 200, html.encode("utf-8"), content_type="text/html; charset=utf-8")
            return

        # 3. Các cổng Public API v1 (/v1/*)
        if path.startswith("/v1/"):
            api_key = headers.get("x-api-key", "").strip()
            user = db.authenticate_api_key(api_key)
            if not user:
                await _send_json(writer, 401, {"error": "API key missing, invalid, or disabled"})
                return

            uid = int(user["telegram_id"])
            tier = str(user.get("tier", "bronze") or "bronze").lower()
            lang = str(user.get("language", "vi") or "vi")

            # GET /v1/balance
            if path == "/v1/balance" and method == "GET":
                await _send_json(
                    writer,
                    200,
                    {
                        "telegramId": uid,
                        "username": user.get("username") or "",
                        "balance": int(round(float(user.get("balance", 0) or 0))),
                        "currency": "VND",
                        "membership": tier,
                    },
                )
                return

            # GET /v1/products
            if path == "/v1/products" and method == "GET":
                products = await ps_client.sync_products(force=False)
                overrides = db.get_all_overrides()
                backup_map = db.get_all_backup_sources()
                out_list: list[dict[str, Any]] = []
                for p in products:
                    pid = str(p["id"])
                    ov = overrides.get(pid)
                    if ov and ov.get("hidden"):
                        continue
                    w_usd = float(p.get("price", 0.0) or 0.0)
                    total_stock, eff_in_stock, primary_stock, _ = db.get_effective_product_stock(p, backup_map)
                    base_vnd, vip_vnd, _ = db.compute_tier_unit_price(
                        pid, w_usd, tier, overrides, primary_stock=primary_stock, backup_map=backup_map
                    )
                    out_list.append(
                        {
                            "id": pid,
                            "name": str(p.get("name", "")),
                            "description": localize_product_description(pid, p.get("description", ""), lang),
                            "price": vip_vnd,
                            "publicPrice": base_vnd,
                            "currency": "VND",
                            "stock": total_stock,
                            "inStock": eff_in_stock,
                            "requiresEmailActivation": bool(p.get("requiresEmailActivation", False)),
                            "delivery": p.get("delivery") or {"type": "instant"},
                        }
                    )
                await _send_json(writer, 200, {"products": out_list})
                return

            # GET /v1/products/:id
            if path.startswith("/v1/products/") and method == "GET":
                pid = path.split("/v1/products/", 1)[1].strip()
                overrides = db.get_all_overrides()
                ov = overrides.get(pid)
                if ov and ov.get("hidden"):
                    await _send_json(writer, 404, {"error": "Product not found"})
                    return
                p = await ps_client.get_product_by_id(pid, refresh=False)
                if not p:
                    await _send_json(writer, 404, {"error": "Product not found"})
                    return
                backup_map = db.get_all_backup_sources()
                total_stock, eff_in_stock, primary_stock, _ = db.get_effective_product_stock(p, backup_map)
                w_usd = float(p.get("price", 0.0) or 0.0)
                base_vnd, vip_vnd, _ = db.compute_tier_unit_price(
                    pid, w_usd, tier, overrides, primary_stock=primary_stock, backup_map=backup_map
                )
                await _send_json(
                    writer,
                    200,
                    {
                        "id": pid,
                        "name": str(p.get("name", "")),
                        "description": localize_product_description(pid, p.get("description", ""), lang),
                        "price": vip_vnd,
                        "publicPrice": base_vnd,
                        "currency": "VND",
                        "stock": total_stock,
                        "inStock": eff_in_stock,
                        "requiresEmailActivation": bool(p.get("requiresEmailActivation", False)),
                        "delivery": p.get("delivery") or {"type": "instant"},
                    },
                )
                return

            # GET /v1/orders
            if path == "/v1/orders" and method == "GET":
                try:
                    page = max(1, int(query_params.get("page", "1")))
                    limit = max(1, min(200, int(query_params.get("limit", "50"))))
                except ValueError:
                    page, limit = 1, 50
                status_filter = query_params.get("status", "").strip() or None
                rows, total = db.get_user_orders_paginated(uid, page=page, limit=limit, status=status_filter)
                pages = max(1, math.ceil(total / limit)) if total > 0 else 1
                await _send_json(
                    writer,
                    200,
                    {
                        "orders": [_format_order_json(r) for r in rows],
                        "pagination": {
                            "page": page,
                            "limit": limit,
                            "total": total,
                            "pages": pages,
                        },
                    },
                )
                return

            # GET /v1/orders/:id
            if path.startswith("/v1/orders/") and method == "GET":
                oid_str = path.split("/v1/orders/", 1)[1].strip()
                if not oid_str.isdigit():
                    await _send_json(writer, 404, {"error": "Order not found"})
                    return
                o = db.get_order_by_id(int(oid_str), user_id=uid)
                if not o:
                    await _send_json(writer, 404, {"error": "Order not found"})
                    return
                await _send_json(writer, 200, _format_order_json(o))
                return

            # POST /v1/orders
            if path == "/v1/orders" and method == "POST":
                idem_key = headers.get("idempotency-key", "").strip()[:100]
                now_ts = time.monotonic()
                if idem_key:
                    cache_key = f"{uid}:{idem_key}"
                    cached = _IDEMPOTENCY_CACHE.get(cache_key)
                    if cached and (now_ts - cached[0] < 900.0):
                        await _send_json(writer, cached[2], cached[1])
                        return

                try:
                    payload = json.loads(body_bytes.decode("utf-8")) if body_bytes else {}
                except Exception:
                    await _send_json(writer, 400, {"error": "Invalid JSON body"})
                    return

                product_id = str(payload.get("productId", "") or "").strip()
                if not product_id:
                    await _send_json(writer, 400, {"error": "Missing required field: productId"})
                    return

                try:
                    qty = int(payload.get("quantity", 1) or 1)
                except (ValueError, TypeError):
                    await _send_json(writer, 400, {"error": "Invalid quantity"})
                    return
                if qty < 1 or qty > 100:
                    await _send_json(writer, 400, {"error": "Quantity must be between 1 and 100"})
                    return

                lock = _API_USER_LOCKS.setdefault(uid, asyncio.Lock())
                if lock.locked():
                    await _send_json(writer, 429, {"error": "Another order is currently processing for your account"})
                    return

                async with lock:
                    overrides = db.get_all_overrides()
                    ov = overrides.get(product_id)
                    if ov and ov.get("hidden"):
                        await _send_json(writer, 404, {"error": "Product not found"})
                        return

                    p = await ps_client.get_product_by_id(product_id, refresh=True)
                    if not p:
                        await _send_json(writer, 404, {"error": "Product not found"})
                        return
                    backup_map = db.get_all_backup_sources()
                    total_stock, eff_in_stock, primary_stock, _ = db.get_effective_product_stock(p, backup_map)
                    if not eff_in_stock or (isinstance(total_stock, int) and total_stock < qty):
                        await _send_json(writer, 409, {"error": "Out of stock or insufficient stock quantity"})
                        return

                    email_str = str(payload.get("email", "") or "").strip()
                    emails_list = payload.get("emails")
                    if isinstance(emails_list, list) and emails_list and not email_str:
                        email_str = str(emails_list[0] or "").strip()

                    if p.get("requiresEmailActivation") and not email_str:
                        await _send_json(
                            writer,
                            400,
                            {"error": "This product requires 'email' field for activation"},
                        )
                        return

                    w_usd = float(p.get("price", 0.0) or 0.0)
                    pricing = db.compute_order_pricing(
                        product_id=product_id,
                        wholesale_usd=w_usd,
                        qty=qty,
                        tier=tier,
                        voucher_code=None,
                        user_id=uid,
                        overrides=overrides,
                        primary_stock=primary_stock,
                        backup_map=backup_map,
                    )
                    total_retail_vnd = int(pricing["total_final_vnd"])
                    total_cost_vnd = int(pricing["total_cost_vnd"])
                    total_base_vnd = int(pricing["total_base_vnd"])
                    vip_disc_pct = int(pricing["vip_disc_pct"])
                    discount_amount_vnd = max(0, total_base_vnd - total_retail_vnd)

                    db._users_cache.pop(uid, None)
                    fresh_api_user = db.get_or_create_user(uid)
                    fresh_api_bal = int(round(float(fresh_api_user.get("balance", 0) or 0)))
                    if total_retail_vnd <= 0 or fresh_api_bal < total_retail_vnd:
                        await _send_json(
                            writer,
                            402,
                            {
                                "error": f"Insufficient balance (Need {total_retail_vnd} VND, available {fresh_api_bal} VND)",
                                "required": total_retail_vnd,
                                "balance": fresh_api_bal,
                                "currency": "VND",
                            },
                        )
                        return

                    # Trừ tiền nguyên tử từ số dư ví VNĐ của đại lý
                    ok_deduct, current_bal = db.deduct_balance_atomic(uid, total_retail_vnd)
                    if not ok_deduct:
                        await _send_json(
                            writer,
                            402,
                            {
                                "error": f"Insufficient balance (Need {total_retail_vnd} VND, available {current_bal} VND)",
                                "required": total_retail_vnd,
                                "balance": current_bal,
                                "currency": "VND",
                            },
                        )
                        return

                    ps_idem = f"api_{uid}_{product_id}_{qty}_{int(time.time())}"
                    try:
                        order_data = await ps_client.fulfill_multi_source_order(
                            db=db,
                            product=p,
                            quantity=qty,
                            email=email_str or None,
                            idempotency_key=ps_idem,
                        )
                    except Exception as exc:
                        db.adjust_balance(uid, total_retail_vnd)
                        await _send_json(writer, 500, {"error": f"Upstream stock error (Refunded): {exc}"})
                        return

                    keys: list[str] = []
                    if order_data.get("deliveredKeys"):
                        keys = [str(k) for k in order_data["deliveredKeys"]]
                    elif order_data.get("deliveredKey"):
                        keys = [str(order_data["deliveredKey"])]

                    status = order_data.get("status", "delivered" if keys else "paid")
                    ps_order_id = str(order_data.get("orderId", ""))
                    actual_cost_vnd = int(order_data.get("actual_cost_vnd", total_cost_vnd))
                    src_summary = str(order_data.get("source_summary", "ProdSeller"))

                    local_order_id = db.create_order_record(
                        user_id=uid,
                        username=user.get("username") or "",
                        product_id=product_id,
                        product_name=p["name"],
                        quantity=qty,
                        wholesale_cost=float(actual_cost_vnd),
                        retail_price=float(total_retail_vnd),
                        prodseller_order_id=ps_order_id,
                        status=status,
                        delivered_keys=keys,
                        activation_email=email_str,
                    )
                    db.record_purchase_stats(uid, total_retail_vnd)

                    resp_payload: dict[str, Any] = {
                        "orderId": str(local_order_id),
                        "status": status,
                        "product": {"id": product_id, "name": p["name"]},
                        "quantity": qty,
                        "amount": total_retail_vnd,
                        "currency": "VND",
                        "membershipDiscount": vip_disc_pct,
                        "bulkDiscount": None,
                        "discountAmount": discount_amount_vnd,
                        "createdAt": db.get_order_by_id(local_order_id)["created_at"],
                    }
                    if email_str:
                        resp_payload["activation"] = {"emails": [email_str], "eta": "ASAP"}
                    if keys:
                        resp_payload["deliveredKey"] = keys[0]
                        resp_payload["deliveredKeys"] = keys

                    if idem_key:
                        _IDEMPOTENCY_CACHE[f"{uid}:{idem_key}"] = (now_ts, resp_payload, 200)

                    # Báo đơn hàng API mới về Telegram cho Admin
                    if bot_client and admin_ids:
                        profit_vnd = total_retail_vnd - actual_cost_vnd
                        profit_pct = (profit_vnd / actual_cost_vnd * 100.0) if actual_cost_vnd > 0 else 0.0
                        raw_u = str(user.get("username", "") or "").strip().lstrip("@")
                        real_u = raw_u if Database.is_valid_tg_username(raw_u) else ""
                        fname = str(user.get("full_name", "") or "").strip() or (raw_u if raw_u and not real_u else f"Khách #{uid}")
                        safe_fname = fname.replace("[", "(").replace("]", ")").replace("`", "'")
                        u_tag = f" (@{real_u})" if real_u else " *(Chưa đặt @username)*"
                        from telethon import Button
                        adm_btns = [
                            [
                                Button.inline("💬 Nhắn tin cho đại lý", f"adm:msg:{uid}".encode(), style="primary"),
                                Button.inline("👤 Hồ sơ", f"adm:uinfo:{uid}".encode()),
                            ]
                        ]
                        for adm_id in admin_ids:
                            try:
                                asyncio.create_task(
                                    bot_client.send_message(
                                        adm_id,
                                        (
                                            f"🔌 **ĐƠN HÀNG QUA API #{local_order_id}**\n\n"
                                            f"👤 Đại lý: **[{safe_fname}](tg://user?id={uid})**{u_tag} — ID: `{uid}`\n"
                                            f"🛍️ Sản phẩm: **{p['name']}** (x{qty})\n"
                                            f"📦 Nguồn xuất hàng: **{src_summary}**\n"
                                            f"💵 Thu đại lý: **{total_retail_vnd:,}đ** | Giá vốn: **{actual_cost_vnd:,}đ**\n"
                                            f"📈 **Lợi nhuận ròng: +{profit_vnd:,}đ (+{profit_pct:.0f}%)**"
                                        ),
                                        buttons=adm_btns,
                                    )
                                )
                            except Exception:
                                pass

                    await _send_json(writer, 200, resp_payload)
                    return

            await _send_json(writer, 404, {"error": "Endpoint not found"})
            return

        await _send_json(writer, 404, {"error": "Not found"})
    except Exception as exc:
        logger.debug("HTTP handler error: %s", exc)
    finally:
        try:
            writer.close()
            await writer.wait_closed()
        except Exception:
            pass


async def _send_json(writer: asyncio.StreamWriter, status_code: int, data: dict[str, Any]) -> None:
    body = json.dumps(data, ensure_ascii=False).encode("utf-8")
    await _send_response(writer, status_code, body, content_type="application/json; charset=utf-8")


async def _send_response(
    writer: asyncio.StreamWriter,
    status_code: int,
    body: bytes,
    *,
    content_type: str = "application/json; charset=utf-8",
) -> None:
    reasons = {
        200: "OK",
        204: "No Content",
        400: "Bad Request",
        401: "Unauthorized",
        402: "Payment Required",
        404: "Not Found",
        409: "Conflict",
        429: "Too Many Requests",
        500: "Internal Server Error",
    }
    reason = reasons.get(status_code, "OK")
    headers = (
        f"HTTP/1.1 {status_code} {reason}\r\n"
        f"Content-Type: {content_type}\r\n"
        f"Content-Length: {len(body)}\r\n"
        "Access-Control-Allow-Origin: *\r\n"
        "Access-Control-Allow-Headers: Content-Type, X-API-Key, Idempotency-Key\r\n"
        "Access-Control-Allow-Methods: GET, POST, OPTIONS\r\n"
        "Connection: close\r\n\r\n"
    ).encode("utf-8")
    writer.write(headers + body)
    await writer.drain()
