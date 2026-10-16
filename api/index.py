"""Endpoint Serverless trên Vercel: Hiển thị Web Status Dashboard & Ping giữ thức Render Bot."""

from __future__ import annotations

import json
import os
import urllib.request
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

from database import Database


class handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        qs = parse_qs(parsed.query)
        action = (qs.get("action", [""])[0] or "").lower()

        render_url = os.getenv("RENDER_BOT_URL", "").strip().rstrip("/")
        render_status = "Chưa cấu hình RENDER_BOT_URL"
        if render_url:
            try:
                req = urllib.request.Request(
                    f"{render_url}/health",
                    headers={"User-Agent": "Vercel-KeepAlive-Monitor/1.0"},
                )
                with urllib.request.urlopen(req, timeout=8) as resp:
                    if resp.status == 200:
                        render_status = "🟢 Đang hoạt động (200 OK)"
                    else:
                        render_status = f"🟡 HTTP {resp.status}"
            except Exception as exc:
                render_status = f"🔴 Đang khởi động lại ({exc})"

        try:
            db = Database()
            stats = db.get_summary_stats()
            db_mode = "🟢 Supabase PostgreSQL (Online)" if db.use_postgres else "🟡 SQLite Local"
        except Exception as exc:
            stats = {
                "users_count": 0,
                "orders_count": 0,
                "total_revenue": 0,
                "total_profit": 0,
                "pending_deposits_count": 0,
            }
            db_mode = f"🔴 Lỗi kết nối DB ({exc})"

        if action == "ping" or parsed.path in ("/health", "/api/ping"):
            payload = json.dumps(
                {
                    "ok": True,
                    "database": db_mode,
                    "render_bot": render_status,
                    "stats": stats,
                },
                ensure_ascii=False,
            ).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(payload)
            return

        html = f"""<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>KingTool Shop Bot - Cloud Status</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: #0f172a;
            color: #f8fafc;
            margin: 0;
            padding: 32px 16px;
            display: flex;
            justify-content: center;
        }}
        .card {{
            max-width: 640px;
            width: 100%;
            background: #1e293b;
            border: 1px solid #334155;
            border-radius: 16px;
            padding: 28px;
            box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.4);
        }}
        h1 {{ margin-top: 0; font-size: 24px; color: #38bdf8; }}
        .badge {{
            display: inline-block;
            padding: 6px 12px;
            border-radius: 9999px;
            background: #064e3b;
            color: #6ee7b7;
            font-size: 13px;
            font-weight: 600;
            margin-bottom: 20px;
        }}
        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 14px;
            margin: 20px 0;
        }}
        .stat {{
            background: #0f172a;
            border: 1px solid #334155;
            border-radius: 12px;
            padding: 16px;
        }}
        .stat-label {{ font-size: 13px; color: #94a3b8; margin-bottom: 6px; }}
        .stat-val {{ font-size: 20px; font-weight: 700; color: #f1f5f9; }}
        .btn {{
            display: inline-block;
            background: #0284c7;
            color: white;
            text-decoration: none;
            padding: 12px 20px;
            border-radius: 10px;
            font-weight: 600;
            margin-top: 12px;
        }}
        .meta {{ font-size: 14px; color: #cbd5e1; line-height: 1.7; }}
    </style>
</head>
<body>
    <div class="card">
        <div class="badge">☁️ Hệ thống Cloud 24/7 (Supabase + Render + Vercel)</div>
        <h1>🤖 KingTool Shop Telegram Bot</h1>
        <div class="meta">
            <div>🗄️ <b>Cơ sở dữ liệu:</b> {db_mode}</div>
            <div>⚡ <b>Tiến trình Bot (Render):</b> {render_status}</div>
        </div>
        <div class="grid">
            <div class="stat">
                <div class="stat-label">👥 Tổng khách hàng</div>
                <div class="stat-val">{int(stats.get('users_count', 0)):,}</div>
            </div>
            <div class="stat">
                <div class="stat-label">📦 Tổng đơn hàng</div>
                <div class="stat-val">{int(stats.get('orders_count', 0)):,}</div>
            </div>
            <div class="stat">
                <div class="stat-label">💰 Tổng doanh thu</div>
                <div class="stat-val">{int(stats.get('total_revenue', 0)):,}đ</div>
            </div>
            <div class="stat">
                <div class="stat-label">⏳ Đơn nạp chờ duyệt</div>
                <div class="stat-val">{int(stats.get('pending_deposits_count', 0))}</div>
            </div>
        </div>
        <a class="btn" href="https://t.me/KingToolShop_bot" target="_blank">🚀 Mở Bot Trên Telegram</a>
    </div>
</body>
</html>"""
        body = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(body)
