"""Bot Reseller Trung Gian Phân Phối Tự Động (@KingToolShop_bot) chạy trên Telethon MTProto.

Đặc điểm:
- Đồng bộ hiển thị 100% tiền tệ bằng Việt Nam Đồng (VNĐ / đ) trên toàn bộ danh sách sản phẩm, chi tiết sản phẩm, ví, lịch sử đơn hàng và nạp tiền.
- Phương thức thanh toán duy nhất: Chuyển khoản Ngân hàng tự động tạo mã QR VietQR + Admin duyệt 1 chạm (kèm SePay tự động ban đêm 23h-06h).
- Giao diện nút bấm màu sắc (Xanh lá / Xanh dương / Đỏ) và gom nhóm gói con (Sub-plans) giống hệt @ProdSellerBot.
- Khi khách mua hàng -> Tự động gọi ProdSeller Official API v1 mua hàng bằng số dư đại lý -> Trả key ngay cho khách (hỗ trợ mua sỉ & xuất file .txt).
- Hỗ trợ Ưu đãi Hạng thành viên (Silver/Gold), Đổi điểm thưởng sang VNĐ, Hoa hồng giới thiệu tự động, và Bảng Quản trị Admin toàn diện.
"""

from __future__ import annotations

import asyncio
import io
import json
import logging
import os
import random
import time
import urllib.parse
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from telethon import Button, TelegramClient, events

from channel_graphics import (
    generate_catalog_banner,
    generate_order_receipt_banner,
    generate_restock_banner,
    generate_spotlight_banner,
)
from database import TIER_DISCOUNTS, VN_TZ, Database
from i18n import LANGUAGES, localize_product_description, t
from prodseller_client import (
    BRAND_GRID_ROWS,
    DANTE_BASE_URL,
    GROUP_EMOJI,
    GROUP_ICONS,
    ProdSellerClient,
    detect_plan_group,
    get_product_icon_and_prefix,
    stock_badge,
)
from public_api import get_public_base_url, handle_http_request

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler(ROOT / "bot.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("reseller_bot")

db = Database()
ps_client = ProdSellerClient(
    os.getenv("PRODSELLER_API_KEY", ""),
    dante_api_key=db.get_setting("dante_api_key", ""),
    dante_base_url=db.get_setting("dante_base_url", DANTE_BASE_URL),
)
ADMIN_IDS: set[int] = {
    int(x.strip())
    for x in os.getenv("ADMIN_TELEGRAM_IDS", "8110826820").split(",")
    if x.strip().isdigit()
}

USER_AWAITING: dict[int, dict[str, Any]] = {}
USER_ACTIVE_VOUCHER: dict[int, str] = {}
USER_PURCHASE_LOCKS: dict[int, asyncio.Lock] = {}
DEPOSIT_NOTIFIED_AT: dict[int, float] = {}
BOT_USERNAME_CACHE: str = "KingToolShop_bot"


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


def vnd_int(val: Any) -> int:
    return int(round(float(val or 0)))


def parse_vnd_input(raw_text: str) -> int:
    """Hỗ trợ nhập số tiền linh hoạt: '50000', '50,000đ', '50k', '1.5m', '200k'."""
    s = raw_text.lower().replace("vnđ", "").replace("vnd", "").replace("đ", "").replace(" ", "").strip()
    multiplier = 1
    if s.endswith("k"):
        multiplier = 1000
        s = s[:-1]
    elif s.endswith("tr") or s.endswith("m"):
        multiplier = 1000000
        s = s[:-2] if s.endswith("tr") else s[:-1]

    if multiplier == 1:
        s = s.replace(",", "").replace(".", "")
    else:
        s = s.replace(",", ".")
    return int(round(float(s) * multiplier))


def format_order_keys_preview(raw_keys: str) -> str:
    """Giải mã chuỗi JSON delivered_keys để hiển thị sạch đẹp không bị dính ngoặc ['...']."""
    if not raw_keys:
        return "(Trống)"
    try:
        parsed = json.loads(raw_keys)
        if isinstance(parsed, list):
            if not parsed:
                return "(Đang chờ / Đã kích hoạt qua Email)"
            cleaned = [str(k).strip() for k in parsed if str(k).strip()]
            if len(cleaned) <= 3:
                return " | ".join(cleaned)
            return " | ".join(cleaned[:3]) + f" (+{len(cleaned) - 3} key khác)"
    except Exception:
        pass
    return str(raw_keys)


def main_menu_buttons(lang: str, user_id: int) -> list[list[Any]]:
    rows: list[list[Any]] = [
        [
            Button.inline(t(lang, "btn_products"), b"menu:products", style="success"),
            Button.inline(t(lang, "btn_balance"), b"menu:balance"),
        ],
    ]
    gift_on = str(db.get_setting("newbie_gift_enabled", "1") or "0").strip() == "1"
    if gift_on:
        cached = db._users_cache.get(user_id)
        claimed = int(cached[1].get("gift_claimed", 0) or 0) == 1 if cached else False
        if not claimed:
            rows.append([Button.inline(t(lang, "btn_newbie_gift"), b"menu:gift", style="success")])
    rows.extend(
        [
            [
                Button.inline(t(lang, "btn_deposit"), b"menu:deposit"),
                Button.inline(t(lang, "btn_methods"), b"menu:methods"),
            ],
            [
                Button.inline(t(lang, "btn_profile"), b"menu:profile"),
                Button.inline(f"🔌 {t(lang, 'btn_api')}", b"menu:api", style="primary", icon=6206497372176913599),
            ],
            [
                Button.inline(t(lang, "btn_language"), b"menu:language"),
                Button.inline(t(lang, "btn_support"), b"menu:support", style="danger"),
            ],
        ]
    )
    if is_admin(user_id):
        rows.append([Button.inline("⚙️ Quản trị Admin (Giá & Duyệt Nạp)", b"adm:home", style="primary")])
    return rows


def extract_sender_identity(sender: Any, uid: int) -> tuple[str, str]:
    """Trích xuất tách biệt (real_username, full_name) từ đối tượng User của Telethon.
    Tuyệt đối không gán first_name vào username (tránh lỗi hiển thị @Tên_Khách không tìm thấy trên Telegram).
    """
    if sender is None:
        return "", f"Khách #{uid}"
    raw_u = (getattr(sender, "username", None) or "").strip().lstrip("@")
    real_u = raw_u if db.is_valid_tg_username(raw_u) else ""
    first = (getattr(sender, "first_name", None) or "").strip()
    last = (getattr(sender, "last_name", None) or "").strip()
    full_name = f"{first} {last}".strip()
    if not full_name:
        full_name = real_u or f"Khách #{uid}"
    return real_u, full_name


def get_user_display_parts(
    uid: int,
    user_dict: dict[str, Any] | None = None,
    fallback_name: str = "",
) -> tuple[str, str, str]:
    """Trả về (clean_full_name, clickable_markdown_name, username_display)."""
    u = user_dict or db._users_cache.get(uid, (0.0, {}))[1] or db.get_or_create_user(uid)
    raw_u = str(u.get("username") or "").strip().lstrip("@")
    raw_f = str(u.get("full_name") or fallback_name or "").strip()
    if raw_u and not db.is_valid_tg_username(raw_u):
        if not raw_f:
            raw_f = raw_u
        raw_u = ""
    if not raw_f:
        raw_f = raw_u or f"Khách #{uid}"
    safe_name = raw_f.replace("[", "(").replace("]", ")").replace("*", "").replace("`", "")
    clickable_name = f"**{safe_name}**"
    uname_display = f"`@{raw_u}`" if raw_u else "*(Chưa đặt @username — Dùng nút 💬 Mở Phiên Chat để @KingToolShop_bot nhắn tin)*"
    return safe_name, clickable_name, uname_display


def format_admin_user_line(
    uid: int,
    user_dict: dict[str, Any] | None = None,
    fallback_name: str = "",
) -> str:
    """Hiển thị rõ Tên khách hàng (gắn link mở chat trực tiếp), Telegram ID và @username thực tế cho Admin."""
    _, clickable_name, uname_display = get_user_display_parts(uid, user_dict, fallback_name)
    return f"👤 Tên khách: {clickable_name} | 🆔 ID: `{uid}`\n🏷️ Username: {uname_display}"


def format_customer_orders_summary_block(target_uid: int, limit: int = 5) -> str:
    """Hiển thị tóm tắt danh sách đơn hàng gần nhất của khách ngay trong phiên trò chuyện."""
    orders = db.get_user_orders(target_uid, limit=limit)
    if not orders:
        return "📦 **ĐƠN HÀNG CỦA KHÁCH:** *(Chưa có đơn hàng nào)*"
    lines = [f"📦 **ĐƠN HÀNG GẦN ĐÂY CỦA KHÁCH ({len(orders)} đơn):**"]
    for o in orders:
        ts_short = str(o.get("created_at", ""))[:16]
        w_unlocked = int(o.get("warranty_unlocked", 0) or 0) == 1
        w_tag = "🔓 Đã mở BH" if w_unlocked else "🔒 Chưa mở BH"
        lines.append(
            f"• Đơn `#{o['id']}` | **{o['product_name']}** (x{o['quantity']}) — **{vnd_int(o.get('retail_price', 0)):,}đ** | {w_tag} (`{ts_short}`)"
        )
    return "\n".join(lines)


def format_customer_chat_history_block(target_uid: int, limit: int = 10) -> str:
    """Hiển thị lịch sử tin nhắn trò chuyện (cũ -> mới) giữa @KingToolShop_bot và Khách hàng."""
    history = db.get_chat_history(target_uid, limit=limit)
    if not history:
        return "📜 **LỊCH SỬ TRÒ CHUYỆN (@KingToolShop_bot ↔ KHÁCH):**\n  *(Chưa có lịch sử tin nhắn nào)*"
    lines = [f"📜 **LỊCH SỬ TRÒ CHUYỆN (@KingToolShop_bot ↔ KHÁCH — {len(history)} tin gần nhất):**"]
    for item in history:
        ts_short = str(item.get("created_at", ""))[5:16]  # MM-DD HH:MM
        role = str(item.get("sender_role", "admin")).lower()
        role_lbl = "🤖 **@KingToolShop_bot**" if role in ("admin", "bot") else "👤 **Khách hàng**"
        body = str(item.get("content", "")).strip()
        if len(body) > 340:
            body = body[:337] + "..."
        lines.append(f"• `[{ts_short}]` {role_lbl}: {body}")
    return "\n".join(lines)


def build_admin_user_buttons(uid: int, include_profile: bool = True) -> list[Any]:
    """Tạo hàng nút bấm giúp Admin mở Phiên Trò Chuyện Riêng (@KingToolShop_bot đóng vai Shop) hoặc xem hồ sơ khách hàng."""
    u = db._users_cache.get(uid, (0.0, {}))[1] or db.get_or_create_user(uid)
    safe_name, _, _ = get_user_display_parts(uid, u)
    short_name = safe_name[:14]
    row: list[Any] = [
        Button.inline(f"💬 Mở Phiên Chat ({short_name})", f"adm:msg:{uid}".encode(), style="success"),
    ]
    if include_profile:
        row.append(Button.inline("👤 Hồ sơ & Đơn", f"adm:uinfo:{uid}".encode(), style="primary"))
    return row


async def send_message_to_user_safe(
    client: TelegramClient,
    target_uid: int,
    text_md: str,
    buttons: list[list[Any]] | None = None,
    html_fallback: str | None = None,
    inline_kb_fallback: list[list[dict[str, str]]] | None = None,
    media: Any = None,
    mirror_to_admin: bool = True,
    record_content: str | None = None,
) -> bool:
    """Gửi tin nhắn tới khách hàng dưới danh nghĩa @KingToolShop_bot (ẩn danh 100% tài khoản cá nhân Admin),
    lưu vào bảng lịch sử `telebot.chat_messages`, và hiển thị khung Phiên Trò Chuyện Riêng cho Admin."""
    tu = db._users_cache.get(target_uid, (0.0, {}))[1] or db.get_or_create_user(target_uid)

    if buttons is None:
        buttons = [
            [Button.inline("💬 Nhắn tin phản hồi cho Shop", b"usr:reply_adm", style="success")],
        ]
    if inline_kb_fallback is None:
        inline_kb_fallback = [
            [{"text": "💬 Nhắn tin phản hồi cho Shop", "callback_data": "usr:reply_adm"}],
        ]

    sent_ok = False
    try:
        await client.send_message(target_uid, text_md, buttons=buttons, file=media)
        sent_ok = True
    except Exception:
        import httpx

        bot_token = os.getenv("RESELLER_BOT_TOKEN", "").strip()
        if bot_token:
            payload: dict[str, Any] = {
                "chat_id": int(target_uid),
                "text": html_fallback or text_md.replace("**", ""),
            }
            if html_fallback:
                payload["parse_mode"] = "HTML"
            if inline_kb_fallback:
                payload["reply_markup"] = {"inline_keyboard": inline_kb_fallback}
            try:
                async with httpx.AsyncClient(timeout=12.0) as hc:
                    r = await hc.post(f"https://api.telegram.org/bot{bot_token}/sendMessage", json=payload)
                    sent_ok = r.status_code == 200 and bool(r.json().get("ok"))
            except Exception:
                sent_ok = False

    if sent_ok and not is_admin(target_uid):
        clean_log = (record_content or text_md).replace("**", "").strip()
        try:
            db.add_chat_message(target_uid, "admin", clean_log)
        except Exception:
            pass

    if sent_ok and mirror_to_admin and not is_admin(target_uid):
        orders_block = format_customer_orders_summary_block(target_uid, limit=5)
        history_block = format_customer_chat_history_block(target_uid, limit=10)
        mirror_md = (
            f"💬 **PHIÊN TRÒ CHUYỆN: @KingToolShop_bot ↔ KHÁCH HÀNG**\n"
            f"✅ *(@KingToolShop_bot vừa gửi tin nhắn thành công tới khách — Ẩn danh 100% Admin)*\n\n"
            f"{format_admin_user_line(target_uid, tu)}\n"
            f"💵 Số dư ví: **{vnd_int(tu.get('balance', 0)):,}đ** | 📦 Đã mua: **{tu.get('orders_count', 0)} đơn**\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"{orders_block}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"{history_block}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🟢 **ĐANG MỞ PHIÊN CHAT LIÊN TỤC:** Gõ tiếp tin nhắn hoặc gửi ảnh ngay bên dưới để `@KingToolShop_bot` gửi tiếp cho khách (hoặc bấm **🚪 Đóng phiên trò chuyện** khi xong):"
        )
        adm_buttons = [
            [
                Button.inline("🔄 Làm mới Lịch sử", f"adm:msg:{target_uid}".encode(), style="primary"),
                Button.inline("👤 Hồ sơ khách", f"adm:uinfo:{target_uid}".encode()),
            ],
            [Button.inline("🚪 Đóng phiên trò chuyện này", b"adm:close_chat", style="danger")],
        ]
        for adm_id in ADMIN_IDS:
            try:
                await client.send_message(adm_id, mirror_md, buttons=adm_buttons, file=media)
            except Exception:
                pass

    return sent_ok


async def forward_customer_chat_to_admins(
    client: TelegramClient,
    event: Any,
    uid: int,
    u: dict[str, Any],
    lang: str,
    text: str,
) -> None:
    """Lưu lịch sử tin nhắn của khách và hiển thị Phiên Trò Chuyện (@KingToolShop_bot ↔ Khách) kèm thông tin đơn hàng + lịch sử chat cho Admin."""
    msg_body = text.strip() if text and text.strip() else "*(Khách hàng gửi hình ảnh / tệp đính kèm)*"
    try:
        db.add_chat_message(uid, "customer", msg_body)
    except Exception:
        pass

    orders_block = format_customer_orders_summary_block(uid, limit=5)
    history_block = format_customer_chat_history_block(uid, limit=10)

    adm_text = (
        f"📩 **KHÁCH HÀNG NHẮN TIN TỚI @KingToolShop_bot**\n\n"
        f"{format_admin_user_line(uid, u)}\n"
        f"💵 Số dư ví: **{vnd_int(u.get('balance', 0)):,}đ** | 📦 Đã mua: **{u.get('orders_count', 0)} đơn**\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"💬 **Tin nhắn mới từ khách:**\n{msg_body}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"{orders_block}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"{history_block}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"👉 *Bấm nút **💬 Mở Phiên Chat** bên dưới (hoặc vuốt Reply tin nhắn này) để `@KingToolShop_bot` đóng vai Shop trả lời khách!*"
    )
    adm_btns = [
        build_admin_user_buttons(uid),
    ]
    for adm_id in ADMIN_IDS:
        try:
            await client.send_message(
                adm_id,
                adm_text,
                buttons=adm_btns,
                file=getattr(event, "media", None),
            )
        except Exception:
            try:
                await client.send_message(adm_id, adm_text, buttons=adm_btns)
            except Exception:
                pass
    await event.respond(
        "✅ **@KingToolShop_bot đã nhận được tin nhắn của bạn và chuyển tới bộ phận CSKH!**\n\n"
        "💬 Shop sẽ phản hồi bạn trực tiếp ngay tại khung chat này. Bạn có thể nhắn thêm thông tin hoặc gửi ảnh trực tiếp tại đây nhé:",
        buttons=[
            [Button.inline("💬 Nhắn thêm tin nhắn cho Shop", b"usr:reply_adm", style="success")],
            [Button.inline(t(lang, "btn_back"), b"menu:home")],
        ],
    )


async def get_user_info(event: Any) -> tuple[dict[str, Any], str]:
    uid = event.sender_id
    sender_obj = getattr(event, "sender", None)
    cached = db._users_cache.get(uid)
    if cached is not None:
        u_cached = dict(cached[1])
        if u_cached.get("full_name"):
            if sender_obj is not None:
                s_u, s_f = extract_sender_identity(sender_obj, uid)
                if (s_u and s_u != u_cached.get("username")) or (s_f and s_f != u_cached.get("full_name")):
                    u = db.get_or_create_user(uid, username=s_u, full_name=s_f)
                    return u, u.get("language", "vi")
            return u_cached, u_cached.get("language", "vi")
    sender = sender_obj or await event.get_sender()
    real_u, full_name = extract_sender_identity(sender, uid)
    u = db.get_or_create_user(uid, username=real_u, full_name=full_name)
    return u, u.get("language", "vi")


async def send_or_edit(event: Any, text: str, buttons: list[list[Any]] | None = None, force_new: bool = False) -> Any:
    """Sửa tin nhắn hiện tại trực tiếp siêu tốc (không tốn thêm RPC get_message)."""
    if not force_new and hasattr(event, "edit"):
        try:
            return await event.edit(text, buttons=buttons)
        except Exception:
            pass
    return await event.respond(text, buttons=buttons)


# ==================== KIỂM TRA BẮT BUỘC THAM GIA KÊNH & NHÓM TRƯỚC KHI MUA HÀNG ====================
_JOIN_VERIFIED_CACHE: dict[int, float] = {}


async def _check_single_chat_joined(client: TelegramClient, chat_username: str, uid: int) -> bool:
    clean_name = (chat_username or "").lstrip("@").strip()
    if not clean_name:
        return True
    try:
        perms = await client.get_permissions(clean_name, uid)
        if perms is None:
            return False
        if getattr(perms, "is_banned", False) or getattr(perms, "has_left", False):
            return False
        return True
    except Exception as exc:
        err_name = type(exc).__name__
        err_str = str(exc)
        if "UserNotParticipant" in err_name or "USER_NOT_PARTICIPANT" in err_str:
            return False
        logger.warning("Không thể kiểm tra thành viên %s trong @%s: %s (%s)", uid, clean_name, err_name, err_str)
        return True


async def check_user_joined_community(
    client: TelegramClient,
    uid: int,
    force_refresh: bool = False,
) -> tuple[bool, bool, bool]:
    """Kiểm tra khách hàng đã tham gia đủ cả Kênh (@KingToolShopOfficial) và Nhóm (@KingToolShopSupport) chưa.
    Trả về (all_joined, joined_channel, joined_group).
    """
    if is_admin(uid):
        return True, True, True
    if str(db.get_setting("force_join_enabled", "1") or "0").strip() != "1":
        return True, True, True

    now_mono = time.monotonic()
    if not force_refresh:
        verified_ts = _JOIN_VERIFIED_CACHE.get(uid, 0.0)
        if verified_ts > 0 and (now_mono - verified_ts < 300.0):
            return True, True, True

    ch_name = db.get_setting("support_channel", "KingToolShopOfficial").lstrip("@").strip()
    grp_name = db.get_setting("support_admin", "KingToolShopSupport").lstrip("@").strip()

    joined_ch, joined_grp = await asyncio.gather(
        _check_single_chat_joined(client, ch_name, uid),
        _check_single_chat_joined(client, grp_name, uid),
    )
    all_ok = bool(joined_ch and joined_grp)
    if all_ok:
        _JOIN_VERIFIED_CACHE[uid] = now_mono
    else:
        _JOIN_VERIFIED_CACHE.pop(uid, None)
    return all_ok, bool(joined_ch), bool(joined_grp)


async def render_force_join_gate(
    event: Any,
    joined_ch: bool,
    joined_grp: bool,
    resume_cb: str = "menu:products",
    back_cb: str = "menu:home",
    force_new: bool = False,
) -> None:
    u, lang = await get_user_info(event)
    uid = u["telegram_id"]
    safe_name, _, _ = get_user_display_parts(uid, u)
    ch_name = db.get_setting("support_channel", "KingToolShopOfficial").lstrip("@").strip()
    grp_name = db.get_setting("support_admin", "KingToolShopSupport").lstrip("@").strip()

    if lang == "vi":
        ch_status = "✅ **Đã tham gia**" if joined_ch else "❌ **Chưa tham gia (Bắt buộc)**"
        grp_status = "✅ **Đã tham gia**" if joined_grp else "❌ **Chưa tham gia (Bắt buộc)**"
    else:
        ch_status = "✅ **Joined**" if joined_ch else "❌ **Not joined (Required)**"
        grp_status = "✅ **Joined**" if joined_grp else "❌ **Not joined (Required)**"

    ch_badge = "✅" if joined_ch else "📣"
    grp_badge = "✅" if joined_grp else "💬"

    rows: list[list[Any]] = []
    if ch_name:
        rows.append([
            Button.url(
                t(lang, "force_join_ch_btn", badge=ch_badge, channel=ch_name),
                f"https://t.me/{ch_name}",
            )
        ])
    if grp_name:
        rows.append([
            Button.url(
                t(lang, "force_join_grp_btn", badge=grp_badge, group=grp_name),
                f"https://t.me/{grp_name}",
            )
        ])
    rows.append([
        Button.inline(
            t(lang, "force_join_verify_btn"),
            f"fjoin:chk:{resume_cb}".encode(),
            style="success",
        )
    ])
    rows.append([Button.inline(t(lang, "btn_back"), back_cb.encode())])

    msg_text = t(
        lang,
        "force_join_title",
        full_name=safe_name,
        uid=uid,
        channel=ch_name,
        group=grp_name,
        ch_status=ch_status,
        grp_status=grp_status,
    )
    await send_or_edit(event, msg_text, buttons=rows, force_new=force_new)


async def ensure_user_joined_community(
    client: TelegramClient,
    event: Any,
    resume_cb: str = "menu:products",
    back_cb: str = "menu:home",
) -> bool:
    """Chốt chặn bắt buộc khách hàng phải tham gia Kênh & Nhóm trước khi mua hàng hoặc nạp tiền."""
    uid = event.sender_id
    all_ok, joined_ch, joined_grp = await check_user_joined_community(client, uid, force_refresh=False)
    if all_ok:
        return True
    await render_force_join_gate(
        event,
        joined_ch=joined_ch,
        joined_grp=joined_grp,
        resume_cb=resume_cb,
        back_cb=back_cb,
    )
    return False


# ==================== PRODUCTS & SUB-PLANS (BẢNG LƯỚI 2-3 CỘT: ICON + TÊN SP, GIÁ HIỂN THỊ KHI BẤM VÀO CHI TIẾT) ====================
async def render_products_menu(event: Any, group_filter: str | None = None, page: int = 0) -> None:
    u, lang = await get_user_info(event)
    try:
        products = await ps_client.sync_products(force=False)
    except Exception as exc:
        logger.error("Lỗi đồng bộ sản phẩm: %s", exc)
        if hasattr(event, "answer"):
            await event.answer("❌ Không thể tải danh sách sản phẩm lúc này.", alert=True)
        return

    overrides = db.get_all_overrides()
    backup_map = db.get_all_backup_sources()
    rows: list[list[Any]] = []

    group_stats: dict[str, dict[str, int]] = {}
    visible_products: list[dict[str, Any]] = []

    for p in products:
        ov = overrides.get(p["id"], {})
        if ov.get("hidden"):
            continue
        visible_products.append(p)
        _, eff_in_stock, _, _ = db.get_effective_product_stock(p, backup_map)
        g = detect_plan_group(p["name"], p.get("category", ""))
        st = group_stats.setdefault(g, {"plans": 0, "in_stock": 0})
        st["plans"] += 1
        if eff_in_stock:
            st["in_stock"] += 1

    owner_premium = os.getenv("OWNER_HAS_PREMIUM", "false").lower()
    use_fallback = owner_premium != "true"

    if not group_filter:
        rendered_brands: set[str] = set()

        def _make_brand_btn(brand: str) -> Any:
            st = group_stats[brand]
            has_stock = st["in_stock"] > 0
            grp_icon = GROUP_ICONS.get(brand)
            grp_emoji = GROUP_EMOJI.get(brand, "") if (use_fallback or grp_icon is None) else ""
            lbl = f"{grp_emoji}{brand}"
            return Button.inline(
                lbl,
                f"grp:{brand}:0".encode(),
                style=None if has_stock else "danger",
                icon=grp_icon,
            )

        for grid_row in BRAND_GRID_ROWS:
            active_in_row = [b for b in grid_row if b in group_stats]
            if active_in_row:
                rows.append([_make_brand_btn(b) for b in active_in_row])
                rendered_brands.update(active_in_row)

        extra_brands = [b for b in group_stats if b not in rendered_brands]
        for i in range(0, len(extra_brands), 3):
            chunk = extra_brands[i : i + 3]
            rows.append([_make_brand_btn(b) for b in chunk])

        all_lbl = "🗂 Tất cả sản phẩm" if lang == "vi" else "🗂 All products"
        rows.append([Button.inline(all_lbl, b"grp:__ALL__:0")])
        rows.append([Button.inline(t(lang, "btn_back"), b"menu:home", icon=5257963315258204021)])
    else:
        filtered: list[dict[str, Any]] = []
        for p in visible_products:
            if group_filter == "__ALL__":
                filtered.append(p)
            else:
                g = detect_plan_group(p["name"], p.get("category", ""))
                if g == group_filter:
                    filtered.append(p)

        # Nếu thương hiệu đó chỉ có duy nhất 1 sản phẩm -> mở thẳng chi tiết sản phẩm kèm giá bán ngay!
        if group_filter != "__ALL__" and len(filtered) == 1:
            await render_product_detail(event, filtered[0]["id"], qty=1, back_to_grid=True)
            return

        # Ưu tiên hiển thị sản phẩm đang sẵn hàng lên đầu danh mục
        filtered.sort(key=lambda item: (0 if db.get_effective_product_stock(item, backup_map)[1] else 1))

        per_page = 16
        total_items = len(filtered)
        max_page = max(0, (total_items - 1) // per_page)
        page = max(0, min(page, max_page))
        start = page * per_page
        end = start + per_page
        sliced = filtered[start:end]

        for p in sliced:
            pid = p["id"]
            _, in_stock, _, _ = db.get_effective_product_stock(p, backup_map)
            icon_id, prefix = get_product_icon_and_prefix(p["name"], use_fallback_emoji=use_fallback)
            btn_style = None if in_stock else "danger"
            # Chỉ hiển thị Icon + Tên sản phẩm gọn đẹp, không kèm giá tiền trên nút bấm
            btn_label = f"{prefix}{p['name'].strip()}"
            rows.append([
                Button.inline(
                    btn_label,
                    f"prd:{pid}".encode(),
                    style=btn_style,
                    icon=icon_id,
                )
            ])

        if total_items > per_page:
            nav_row: list[Any] = []
            if page > 0:
                nav_row.append(Button.inline("⬅️ Trang trước", f"grp:{group_filter}:{page - 1}".encode()))
            nav_row.append(Button.inline(f"📄 {page + 1}/{max_page + 1}", b"noop"))
            if end < total_items:
                nav_row.append(Button.inline("Trang sau ➡️", f"grp:{group_filter}:{page + 1}".encode()))
            rows.append(nav_row)

        rows.append([
            Button.inline(t(lang, "btn_back"), b"menu:products", icon=5346112927688574301),
            Button.inline("🏠 Menu", b"menu:home", icon=5257963315258204021),
        ])

    header = t(lang, "products_title")
    if group_filter == "__ALL__":
        header = f"🛍️ **Tất cả sản phẩm ({len(visible_products)} SP)**\nChọn một sản phẩm bên dưới để xem chi tiết & giá bán:"
    elif group_filter:
        grp_emoji = GROUP_EMOJI.get(group_filter, "🛍️ ")
        header = f"{grp_emoji}**{group_filter}**\nChọn gói sản phẩm bên dưới để xem chi tiết & giá bán:"

    await send_or_edit(event, header, buttons=rows)


async def render_product_detail(
    event: Any,
    product_id: str,
    qty: int = 1,
    back_to_grid: bool = False,
) -> None:
    u, lang = await get_user_info(event)
    uid = u["telegram_id"]
    tier = u.get("tier", "bronze")
    p = await ps_client.get_product_by_id(product_id, refresh=False)
    if not p:
        if hasattr(event, "answer"):
            await event.answer("❌ Không tìm thấy sản phẩm.", alert=True)
        return
    asyncio.create_task(ps_client.get_product_by_id(product_id, refresh=True))

    backup_map = db.get_all_backup_sources()
    stock_num, in_stock, primary_stock, backup_stock = db.get_effective_product_stock(p, backup_map)
    if isinstance(stock_num, int) and stock_num >= 1 and qty > stock_num:
        qty = max(1, stock_num)

    active_vch = USER_ACTIVE_VOUCHER.get(uid)
    pricing = db.compute_order_pricing(
        product_id=product_id,
        wholesale_usd=float(p["price"]),
        qty=qty,
        tier=tier,
        voucher_code=active_vch,
        user_id=uid,
        primary_stock=primary_stock,
        backup_map=backup_map,
    )
    if active_vch and not pricing["voucher_valid"]:
        USER_ACTIVE_VOUCHER.pop(uid, None)

    base_vnd = pricing["base_unit_vnd"]
    unit_retail_vnd = pricing["vip_unit_vnd"]
    disc_pct = pricing["vip_disc_pct"]
    total_vip_vnd = pricing["total_vip_vnd"]
    total_final_vnd = pricing["total_final_vnd"]
    cost_vnd = pricing["unit_cost_vnd"]

    stock_str = (
        t(lang, "stock_keys_unit", n=stock_num)
        if isinstance(stock_num, int)
        else (t(lang, "stock_available") if in_stock else t(lang, "stock_zero"))
    )
    desc = localize_product_description(product_id, p.get("description") or "", lang)

    if pricing["voucher_valid"]:
        price_line = f"{t(lang, 'price_label')}: ~~{unit_retail_vnd:,}đ~~"
        if qty > 1:
            price_line += f" (x{qty} = ~~{total_vip_vnd:,}đ~~)"
    else:
        price_line = f"{t(lang, 'price_label')}: **{unit_retail_vnd:,}đ**"
        if qty > 1:
            price_line += f" (x{qty} = **{total_vip_vnd:,}đ**)"

    if disc_pct > 0 and unit_retail_vnd < base_vnd:
        price_line += "\n" + t(
            lang,
            "tier_discount_note",
            tier=tier.upper(),
            disc_pct=disc_pct,
            base_price=base_vnd,
            unit_price=unit_retail_vnd,
        )

    if pricing["voucher_valid"]:
        price_line += "\n" + t(
            lang,
            "voucher_applied_note",
            code=pricing["voucher_code"],
            disc=pricing["voucher_discount_vnd"],
            old_price=total_vip_vnd,
            final_price=total_final_vnd,
        )

    text = (
        f"🛍️ **{p['name'].strip()}**\n\n"
        f"{desc}\n\n"
        f"{price_line}\n"
        f"{t(lang, 'in_stock_label')}: **{stock_str}**"
    )

    grp = detect_plan_group(p["name"], p.get("category", ""))
    if back_to_grid:
        back_cb = b"menu:products"
    else:
        all_prods = ps_client._products_cache
        overrides_map = db.get_all_overrides()
        same_grp_cnt = sum(
            1
            for item in all_prods
            if not overrides_map.get(item["id"], {}).get("hidden")
            and detect_plan_group(item["name"], item.get("category", "")) == grp
        )
        back_cb = f"grp:{grp}:0".encode() if (grp and same_grp_cnt > 1) else b"menu:products"

    rows: list[list[Any]] = []
    if in_stock and (stock_num is None or stock_num >= 1):
        preset_qtys = [1, 2, 5, 10]
        if qty not in preset_qtys:
            preset_qtys.append(qty)
            preset_qtys.sort()

        qty_row = [
            Button.inline(
                f"{'✅ ' if qty == q else ''}{q}x",
                f"qty:{product_id}:{q}".encode(),
                style="primary" if qty == q else None,
            )
            for q in preset_qtys
            if stock_num is None or stock_num >= q
        ]
        if stock_num is None or stock_num > 2:
            qty_row.append(
                Button.inline(
                    t(lang, "custom_qty_btn"),
                    f"qtyc:{product_id}".encode(),
                )
            )
        if len(qty_row) > 1:
            rows.append(qty_row)

        # Nút Nhập mã giảm giá (Voucher) hoặc Đang áp mã [❌ Bỏ mã] nằm ngay trên nút Mua ngay
        if pricing["voucher_valid"]:
            rows.append([
                Button.inline(
                    t(
                        lang,
                        "voucher_applied_btn",
                        code=pricing["voucher_code"],
                        disc=pricing["voucher_discount_vnd"],
                    ),
                    f"vch:rm:{product_id}:{qty}".encode(),
                    style="primary",
                )
            ])
        else:
            rows.append([
                Button.inline(
                    t(lang, "voucher_apply_btn"),
                    f"vch:ask:{product_id}:{qty}".encode(),
                )
            ])

        rows.append([
            Button.inline(
                t(lang, "buy_btn", price=total_final_vnd),
                f"buy:{product_id}:{qty}".encode(),
                style="success",
            )
        ])
    else:
        rows.append([Button.inline(t(lang, "out_of_stock_btn"), b"noop", style="danger")])

    if is_admin(uid):
        k1_lbl = "∞" if primary_stock is None else str(primary_stock)
        rows.append([
            Button.inline(
                f"⚙️ Vốn:{cost_vnd:,}đ | Bán:{base_vnd:,}đ [K1:{k1_lbl} | Dự phòng:{backup_stock}]",
                f"adm:editp:{product_id}".encode(),
                style="primary",
            )
        ])

    rows.append([Button.inline(t(lang, "btn_back"), back_cb)])
    await send_or_edit(event, text, buttons=rows)


# ==================== BUY & AUTO-FULFILLMENT (ĐA NGUỒN HÀNG + BÌNH ỔN GIÁ + VOUCHER) ====================
async def execute_purchase(
    client: TelegramClient,
    event: Any,
    product_id: str,
    qty: int,
    activation_email: str | None = None,
) -> None:
    u, lang = await get_user_info(event)
    uid = u["telegram_id"]

    # Bắt buộc khách hàng phải tham gia đủ Kênh (@KingToolShopOfficial) & Nhóm (@KingToolShopSupport) trước khi mua hàng
    if not await ensure_user_joined_community(
        client,
        event,
        resume_cb=f"buy:{product_id}:{qty}",
        back_cb=f"prd:{product_id}",
    ):
        return

    lock = USER_PURCHASE_LOCKS.setdefault(uid, asyncio.Lock())
    if lock.locked():
        if hasattr(event, "answer"):
            await event.answer(t(lang, "order_busy"), alert=True)
        else:
            await event.respond(t(lang, "order_busy"))
        return

    async with lock:
        p = await ps_client.get_product_by_id(product_id, refresh=True)
        if not p:
            await event.respond(t(lang, "out_of_stock_btn"))
            return

        backup_map = db.get_all_backup_sources()
        stock_num, in_stock, primary_stock, _ = db.get_effective_product_stock(p, backup_map)
        if not in_stock or (isinstance(stock_num, int) and stock_num < qty):
            await event.respond(t(lang, "out_of_stock_btn"))
            return

        if p.get("requiresEmailActivation") and not activation_email:
            USER_AWAITING[uid] = {
                "type": "activation_email",
                "product_id": product_id,
                "qty": qty,
            }
            await event.respond(t(lang, "ask_activation_email", name=p["name"]))
            return

        db._users_cache.pop(uid, None)
        fresh_user = db.get_or_create_user(uid)
        tier = fresh_user.get("tier", "bronze")
        unit_cost_usd = float(p["price"])
        active_vch = USER_ACTIVE_VOUCHER.get(uid)
        pricing = db.compute_order_pricing(
            product_id=product_id,
            wholesale_usd=unit_cost_usd,
            qty=qty,
            tier=tier,
            voucher_code=active_vch,
            user_id=uid,
            primary_stock=primary_stock,
            backup_map=backup_map,
        )
        total_cost_vnd = int(pricing["total_cost_vnd"])
        total_retail_vnd = int(pricing["total_final_vnd"])
        fresh_bal_vnd = int(round(float(fresh_user.get("balance", 0) or 0)))

        if total_retail_vnd <= 0 or fresh_bal_vnd < total_retail_vnd:
            rows = [
                [Button.inline(t(lang, "deposit_now_btn"), b"menu:deposit", style="success")],
                [Button.inline(t(lang, "btn_back"), f"prd:{product_id}".encode())],
            ]
            msg_text = t(lang, "insufficient_balance", need=max(1, total_retail_vnd), have=fresh_bal_vnd)
            await send_or_edit(event, msg_text, buttons=rows)
            return

        # Trừ số dư VNĐ nguyên tử (Atomic check + deduct)
        deducted_ok, current_bal_vnd = db.deduct_balance_atomic(uid, total_retail_vnd)
        if not deducted_ok:
            rows = [
                [Button.inline(t(lang, "deposit_now_btn"), b"menu:deposit", style="success")],
                [Button.inline(t(lang, "btn_back"), f"prd:{product_id}".encode())],
            ]
            msg_text = t(lang, "insufficient_balance", need=total_retail_vnd, have=current_bal_vnd)
            await send_or_edit(event, msg_text, buttons=rows)
            return

        status_msg = await event.respond(t(lang, "order_processing"))

        idem_key = f"ord_{uid}_{uuid.uuid4().hex[:16]}"
        try:
            order_resp = await ps_client.fulfill_multi_source_order(
                db=db,
                product=p,
                quantity=qty,
                email=activation_email,
                idempotency_key=idem_key,
            )
        except Exception as exc:
            # Hoàn tiền tự động nếu kho gốc & kho dự phòng đều hết hàng hoặc hết vốn
            db.adjust_balance(uid, total_retail_vnd)
            logger.error("Lỗi mua hàng từ các nguồn cung cấp: %s", exc)
            await status_msg.edit(
                t(lang, "order_failed_refunded", refund=total_retail_vnd, err=str(exc))
            )
            user_line_adm = format_admin_user_line(uid, u)
            adm_btns = [build_admin_user_buttons(uid)]
            for adm_id in ADMIN_IDS:
                try:
                    await client.send_message(
                        adm_id,
                        (
                            f"⚠️ **CẢNH BÁO LỖI ĐƠN HÀNG**\n\n"
                            f"{user_line_adm}\n"
                            f"🛍️ SP: **{p['name']}** (x{qty})\n"
                            f"💵 Giá vốn dự kiến: **{total_cost_vnd:,}đ**\n"
                            f"❌ Lỗi từ nguồn hàng: `{exc}`\n"
                            f"*(Hãy kiểm tra số dư USDT @ProdSellerBot hoặc nạp thêm Key vào Kho Dự Phòng!)*"
                        ),
                        buttons=adm_btns,
                    )
                except Exception:
                    pass
            return

        keys: list[str] = []
        if order_resp.get("deliveredKeys"):
            keys = [str(k) for k in order_resp["deliveredKeys"]]
        elif order_resp.get("deliveredKey"):
            keys = [str(order_resp["deliveredKey"])]

        ps_order_id = str(order_resp.get("orderId", ""))
        ps_status = str(order_resp.get("status", "delivered"))
        actual_cost_vnd = int(order_resp.get("actual_cost_vnd", total_cost_vnd))
        source_summary = str(order_resp.get("source_summary", "ProdSeller"))

        local_order_id = db.create_order_record(
            user_id=uid,
            username=u["username"],
            product_id=product_id,
            product_name=p["name"],
            quantity=qty,
            wholesale_cost=float(actual_cost_vnd),
            retail_price=float(total_retail_vnd),
            prodseller_order_id=ps_order_id,
            status=ps_status,
            delivered_keys=keys,
            activation_email=activation_email or "",
        )
        db.record_purchase_stats(uid, total_retail_vnd)

        vch_admin_line = ""
        if pricing["voucher_valid"] and pricing["voucher_code"]:
            db.redeem_voucher_atomic(
                pricing["voucher_code"],
                uid,
                local_order_id,
                pricing["voucher_discount_vnd"],
            )
            USER_ACTIVE_VOUCHER.pop(uid, None)
            vch_admin_line = f"🎟️ Voucher áp dụng: **{pricing['voucher_code']}** (-{pricing['voucher_discount_vnd']:,}đ)\n"

        if ps_status == "paid" and not keys:
            await status_msg.edit(
                t(
                    lang,
                    "order_activation_paid",
                    order_id=local_order_id,
                    name=p["name"],
                    email=activation_email or "",
                )
            )
        else:
            keys_block = "\n".join(keys) if keys else "(Đã giao)"
            if len(keys_block) > 2800 or len(keys) > 15:
                preview_keys = "\n".join(keys[:10]) + f"\n... (Xem đầy đủ {len(keys)} tài khoản trong file đính kèm)"
                await status_msg.edit(
                    t(
                        lang,
                        "order_success",
                        order_id=local_order_id,
                        name=p["name"],
                        qty=qty,
                        paid=total_retail_vnd,
                        keys=preview_keys,
                    )
                )
                txt_bytes = io.BytesIO(keys_block.encode("utf-8"))
                txt_bytes.name = f"don_hang_{local_order_id}.txt"
                await client.send_file(
                    event.chat_id,
                    file=txt_bytes,
                    caption=f"📄 Danh sách {len(keys)} tài khoản/key của đơn hàng `#{local_order_id}`",
                )
            else:
                await status_msg.edit(
                    t(
                        lang,
                        "order_success",
                        order_id=local_order_id,
                        name=p["name"],
                        qty=qty,
                        paid=total_retail_vnd,
                        keys=keys_block,
                    )
                )

        profit_vnd = total_retail_vnd - actual_cost_vnd
        profit_pct = (profit_vnd / actual_cost_vnd * 100.0) if actual_cost_vnd > 0 else 0.0
        user_line_adm = format_admin_user_line(uid, u)
        adm_btns = [build_admin_user_buttons(uid)]
        for adm_id in ADMIN_IDS:
            try:
                await client.send_message(
                    adm_id,
                    (
                        f"🎉 **ĐƠN HÀNG MỚI #{local_order_id}**\n\n"
                        f"{user_line_adm}\n"
                        f"🛍️ Sản phẩm: **{p['name']}** (x{qty})\n"
                        f"📦 Nguồn xuất hàng: **{source_summary}**\n"
                        f"{vch_admin_line}"
                        f"💰 Giá thu khách: **{total_retail_vnd:,}đ**\n"
                        f"📉 Giá vốn thực tế: **{actual_cost_vnd:,}đ**\n"
                        f"💵 **Lợi nhuận ròng: +{profit_vnd:,}đ (+{profit_pct:.0f}%)**"
                    ),
                    buttons=adm_btns,
                )
            except Exception:
                pass

        asyncio.create_task(
            post_order_social_proof(
                client,
                order_id=local_order_id,
                uid=uid,
                product_id=product_id,
                product_name=p["name"],
                qty=qty,
                total_vnd=total_retail_vnd,
            )
        )
        asyncio.create_task(check_and_alert_low_prodseller_balance(client))


# ==================== CẢNH BÁO VỐN, PHỄU KHÁCH HÀNG & TỰ ĐỘNG ĐĂNG KÊNH @KingToolShopOfficial ====================
_LAST_LOW_BAL_ALERT_TS: float = 0.0
_LAST_KNOWN_STOCK: dict[str, int] = {}
_LAST_AUTO_POST_HOUR_KEY: str = ""
_LAST_SIM_SOCIAL_TS: float = 0.0
_LAST_SIM_SOCIAL_MSG_ID: int = 0
_LAST_SPOTLIGHT_MSG_ID: int = 0
_REMINDED_DEPOSIT_IDS: set[int] = set()


async def check_and_alert_low_prodseller_balance(client: TelegramClient) -> None:
    """Kiểm tra số dư vốn trên @ProdSellerBot và cảnh báo Admin nếu tụt dưới ngưỡng cài đặt."""
    global _LAST_LOW_BAL_ALERT_TS
    try:
        threshold = float(db.get_setting("low_balance_threshold_usd", "5.0") or 0.0)
        if threshold <= 0:
            return
        now_ts = time.time()
        if now_ts - _LAST_LOW_BAL_ALERT_TS < 14400.0:  # Cooldown 4 giờ tránh spam
            return
        b_info = await ps_client.get_balance()
        ps_usd = float(b_info.get("balance", 0.0))
        if ps_usd <= threshold:
            _LAST_LOW_BAL_ALERT_TS = now_ts
            rate = float(db.get_setting("vnd_rate", "25500") or 25500.0)
            ps_vnd = int(round(ps_usd * rate))
            for adm_id in ADMIN_IDS:
                try:
                    await client.send_message(
                        adm_id,
                        (
                            "🚨 **CẢNH BÁO SỐ DƯ VỐN @ProdSellerBot SẮP HẾT!**\n\n"
                            f"🏦 Số dư vốn hiện tại: **`${ps_usd:.2f}`** (~**{ps_vnd:,}đ**)\n"
                            f"⚠️ Ngưỡng cảnh báo: **`${threshold:.2f}`**\n\n"
                            "👉 Vui lòng nạp thêm USDT vào `@ProdSellerBot` sớm để không bị gián đoạn khi khách mua hàng tự động!"
                        ),
                    )
                except Exception:
                    pass
    except Exception as exc:
        logger.debug("Không thể kiểm tra cảnh báo số dư ProdSeller: %s", exc)


async def _send_channel_post_with_banner(
    client: TelegramClient,
    channel_name: str,
    text: str,
    buttons: list[list[Any]],
    banner_io: io.BytesIO | None = None,
    silent: bool = True,
) -> Any:
    """Gửi bài đăng kèm ảnh Banner HD (mặc định silent=True để không bật chuông làm phiền Admin đối với bài tự động/đơn mồi)."""
    if banner_io is not None:
        try:
            caption = text if len(text) <= 1000 else (text[:995].rsplit("\n", 1)[0] + "\n...")
            return await client.send_message(channel_name, caption, file=banner_io, buttons=buttons, silent=silent)
        except Exception as exc:
            logger.debug("Fallback gửi text lên kênh (lỗi gửi kèm ảnh %s): %s", channel_name, exc)
    return await client.send_message(channel_name, text, buttons=buttons, silent=silent)


async def post_restock_notification(client: TelegramClient, restocked_items: list[dict[str, Any]]) -> None:
    """Tự động đăng thông báo Hàng Về (Restock) kèm Banner HD lên kênh @KingToolShopOfficial."""
    try:
        if str(db.get_setting("restock_notify_enabled", "1") or "0").strip() != "1":
            return
        ch_name = db.get_setting("support_channel", "KingToolShopOfficial").lstrip("@").strip()
        if not ch_name or not restocked_items:
            return
        overrides = db.get_all_overrides()
        backup_map = db.get_all_backup_sources()
        lines = [
            "🔥 **THÔNG BÁO HÀNG VỀ (RESTOCK KHO TỰ ĐỘNG)** 🔥",
            "━━━━━━━━━━━━━━━━━━━━",
        ]
        rows: list[list[Any]] = []
        banner_tuples: list[tuple[str, int, str]] = []
        for p in restocked_items[:6]:
            pid = p["id"]
            eff_stock, eff_in_stock, p_st, _ = db.get_effective_product_stock(p, backup_map)
            price_vnd = db.compute_retail_price(pid, float(p["price"]), overrides, primary_stock=p_st, backup_map=backup_map)
            st_txt = f"Còn {eff_stock} suất" if isinstance(eff_stock, int) and eff_stock > 0 else "Sẵn hàng"
            banner_tuples.append((p["name"].strip(), price_vnd, st_txt))
            lines.append(
                f"🟢 **{p['name'].strip()}**\n"
                f"   💰 Giá: **`{price_vnd:,}đ`** — 📦 Kho: **{st_txt}**"
            )
            short_name = p["name"].strip()[:24]
            rows.append([
                Button.url(
                    f"🛒 Mua ngay: {short_name} ({price_vnd:,}đ)",
                    f"https://t.me/{BOT_USERNAME_CACHE}?start=BUY_{pid}",
                )
            ])
        rows.append([
            Button.url(
                "🎁 Nhận Quà Tân Thủ & Mã Giảm Giá (-10%)",
                f"https://t.me/{BOT_USERNAME_CACHE}?start=GIFT",
            )
        ])
        lines.append("━━━━━━━━━━━━━━━━━━━━")
        lines.append("⚡ *Giao dịch tự động 100% — Nhận tài khoản/key ngay sau 2 giây!*")
        banner_io = None
        try:
            banner_io = generate_restock_banner(banner_tuples, bot_username=BOT_USERNAME_CACHE)
        except Exception:
            pass
        await _send_channel_post_with_banner(client, ch_name, "\n".join(lines), rows, banner_io)
    except Exception as exc:
        logger.debug("Không thể đăng thông báo Restock lên kênh: %s", exc)


async def post_order_social_proof(
    client: TelegramClient,
    order_id: int | str,
    uid: int | str,
    product_name: str,
    qty: int,
    total_vnd: int,
    product_id: str = "",
    silent: bool = False,
) -> int | None:
    """Tự động đăng thông báo khách mua hàng thành công kèm ảnh Biên Lai HD lên kênh @KingToolShopOfficial.
    Khi là đơn mồi (silent=True), chỉ hiển thị tĩnh trên kênh cho khách xem chứ tuyệt đối không báo chuông làm phiền Admin."""
    try:
        ch_name = db.get_setting("support_channel", "KingToolShopOfficial").lstrip("@").strip()
        if not ch_name:
            return None
        uid_s = str(uid)
        if "***" in uid_s:
            masked_uid = uid_s
        else:
            masked_uid = f"{uid_s[:4]}***{uid_s[-2:]}" if len(uid_s) > 5 else f"{uid_s[:2]}***"
        support_name = db.get_setting("support_admin", "KingToolShopSupport").lstrip("@").strip()
        text = (
            f"⚡ **ĐƠN HÀNG TỰ ĐỘNG #{order_id} HOÀN TẤT**\n\n"
            f"👤 Khách hàng: `{masked_uid}`\n"
            f"🛍️ Sản phẩm: **{product_name.strip()}** (x{qty})\n"
            f"💵 Thanh toán: **{total_vnd:,}đ**\n"
            f"✅ Trạng thái: **Đã trả tài khoản tự động trong 2 giây!**\n"
            f"🎁 *Khách mới bấm nút bên dưới để nhận ngay Mã giảm giá `-10%` & Điểm thưởng!*"
        )
        buy_url = (
            f"https://t.me/{BOT_USERNAME_CACHE}?start=BUY_{product_id}"
            if product_id
            else f"https://t.me/{BOT_USERNAME_CACHE}"
        )
        rows = [
            [
                Button.url("🛒 Mua Sản Phẩm Này Ngay", buy_url),
                Button.url("🎁 Quà Tân Thủ (-10%)", f"https://t.me/{BOT_USERNAME_CACHE}?start=GIFT"),
            ],
            [
                Button.url("🆘 Hỗ Trợ & Bảo Hành 24/7", f"https://t.me/{support_name}"),
            ],
        ]
        banner_io = None
        try:
            banner_io = generate_order_receipt_banner(
                order_id=order_id,
                masked_uid=masked_uid,
                product_name=product_name,
                qty=qty,
                total_vnd=total_vnd,
                bot_username=BOT_USERNAME_CACHE,
            )
        except Exception:
            pass
        msg = await _send_channel_post_with_banner(client, ch_name, text, rows, banner_io, silent=silent)
        return msg.id if msg else None
    except Exception as exc:
        logger.debug("Không thể đăng social proof lên kênh: %s", exc)
        return None


async def post_simulated_social_proof(client: TelegramClient) -> int | None:
    """Tự động đăng thông báo đơn hàng hoàn tất (Social Proof) ở chế độ im lặng (silent=True):
    Khách vào kênh vẫn thấy đơn hàng sôi động nhưng tuyệt đối không hiện thông báo làm phiền Admin."""
    global _LAST_SIM_SOCIAL_MSG_ID
    try:
        if str(db.get_setting("auto_social_proof_enabled", "1") or "0").strip() != "1":
            return None
        ch_name = db.get_setting("support_channel", "KingToolShopOfficial").lstrip("@").strip()
        if not ch_name:
            return None
        products = await ps_client.sync_products(force=False)
        overrides = db.get_all_overrides()
        backup_map = db.get_all_backup_sources()
        in_stock_prods = [
            p
            for p in products
            if not overrides.get(p["id"], {}).get("hidden")
            and db.get_effective_product_stock(p, backup_map)[1]
        ]
        if not in_stock_prods:
            return None

        chosen = random.choice(in_stock_prods)
        pid = str(chosen["id"])
        qty = 1
        _, _, p_st, _ = db.get_effective_product_stock(chosen, backup_map)
        unit_vnd = db.compute_retail_price(pid, float(chosen["price"]), overrides, primary_stock=p_st, backup_map=backup_map)
        prefixes = ["5182", "6094", "7128", "8041", "6839", "5910", "7482", "1984", "6527", "8135"]
        masked_uid = f"{random.choice(prefixes)}***{random.randint(10, 99)}"
        stats = db.get_summary_stats()
        sim_oid = max(108, int(stats.get("orders_count", 0)) + random.randint(120, 380))

        # Xóa thông báo đơn mồi trước đó để kênh luôn gọn gàng, không bị loãng
        if _LAST_SIM_SOCIAL_MSG_ID > 0:
            try:
                await client.delete_messages(ch_name, [_LAST_SIM_SOCIAL_MSG_ID])
            except Exception:
                pass

        new_mid = await post_order_social_proof(
            client,
            order_id=sim_oid,
            uid=masked_uid,
            product_name=chosen["name"],
            qty=qty,
            total_vnd=unit_vnd * qty,
            product_id=pid,
            silent=True,
        )
        if new_mid:
            _LAST_SIM_SOCIAL_MSG_ID = new_mid
        return new_mid
    except Exception as exc:
        logger.debug("Không thể đăng simulated social proof: %s", exc)
        return None


async def post_spotlight_to_channel(client: TelegramClient) -> int | None:
    """Tự động chọn 1 Sản phẩm Hot đang sẵn hàng để đăng Poster HD kèm nút Mua 1 chạm & Quà Tân Thủ."""
    global _LAST_SPOTLIGHT_MSG_ID
    try:
        ch_name = db.get_setting("support_channel", "KingToolShopOfficial").lstrip("@").strip()
        support_name = db.get_setting("support_admin", "KingToolShopSupport").lstrip("@").strip()
        if not ch_name:
            return None
        products = await ps_client.sync_products(force=False)
        overrides = db.get_all_overrides()
        backup_map = db.get_all_backup_sources()
        in_stock_prods = [
            p
            for p in products
            if not overrides.get(p["id"], {}).get("hidden")
            and db.get_effective_product_stock(p, backup_map)[1]
        ]
        if not in_stock_prods:
            return None

        chosen = random.choice(in_stock_prods)
        pid = str(chosen["id"])
        eff_st, _, p_st, _ = db.get_effective_product_stock(chosen, backup_map)
        gift_code = db.get_setting("newbie_gift_voucher", "TANTHU10").strip().upper() or "TANTHU10"
        pricing = db.compute_order_pricing(
            product_id=pid,
            wholesale_usd=float(chosen["price"]),
            qty=1,
            tier="bronze",
            voucher_code=gift_code,
            overrides=overrides,
            primary_stock=p_st,
            backup_map=backup_map,
        )
        base_vnd = pricing["base_unit_vnd"]
        final_vnd = pricing["total_final_vnd"]
        st_txt = f"Còn {eff_st} suất" if isinstance(eff_st, int) and eff_st > 0 else "Sẵn hàng"

        raw_desc = localize_product_description(pid, chosen.get("description") or "", "vi")
        desc_lines = [ln.strip() for ln in raw_desc.splitlines() if ln.strip() and not ln.strip().startswith("━")]
        short_desc = "\n".join(desc_lines[:5])
        if len(short_desc) > 340:
            short_desc = short_desc[:337] + "..."

        price_block = (
            f"💵 Giá niêm yết: ~~`{base_vnd:,}đ`~~ ➡️ **Chỉ còn `{final_vnd:,}đ`** *(Khi áp mã `{gift_code}`)*"
            if final_vnd < base_vnd
            else f"💵 Giá ưu đãi: **`{base_vnd:,}đ`**"
        )

        text = (
            "🔥 **TIÊU ĐIỂM SẢN PHẨM HOT TRONG NGÀY — GIAO NGAY 2 GIÂY** 🔥\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"🛍️ **{chosen['name'].strip()}**\n"
            f"📦 Tình trạng kho: **{st_txt}**\n"
            f"{price_block}\n\n"
            f"{short_desc}\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "🎁 **ƯU ĐÃI ĐẶC BIỆT HÔM NAY:**\n"
            f"• Nhập mã **`{gift_code}`** hoặc bấm **Nhận Quà Tân Thủ** để được **giảm ngay 10% + tặng Điểm thưởng**!\n"
            "• Nạp từ **200,000đ** tặng thêm **+5%**, từ **500,000đ** tặng thêm **+10%** vào ví!\n"
            "• Bảo hành 1 chạm trực tiếp trên Bot — Hỗ trợ 24/7 tại @" + support_name
        )
        short_name = chosen["name"].strip()[:24]
        rows = [
            [
                Button.url(
                    f"🛒 Mua ngay: {short_name} ({final_vnd:,}đ)",
                    f"https://t.me/{BOT_USERNAME_CACHE}?start=BUY_{pid}",
                )
            ],
            [
                Button.url(
                    f"🎁 Nhận Quà Tân Thủ & Mã {gift_code}",
                    f"https://t.me/{BOT_USERNAME_CACHE}?start=GIFT",
                )
            ],
            [
                Button.url("🛍️ Xem Toàn Bộ Kho Hàng", f"https://t.me/{BOT_USERNAME_CACHE}"),
                Button.url("🆘 Hỗ Trợ CSKH", f"https://t.me/{support_name}"),
            ],
        ]

        if _LAST_SPOTLIGHT_MSG_ID > 0:
            try:
                await client.delete_messages(ch_name, [_LAST_SPOTLIGHT_MSG_ID])
            except Exception:
                pass

        banner_io = None
        try:
            banner_io = generate_spotlight_banner(
                product_name=chosen["name"],
                category=chosen.get("category", ""),
                base_vnd=base_vnd,
                final_vnd=final_vnd,
                gift_code=gift_code,
                stock_text=st_txt,
                bot_username=BOT_USERNAME_CACHE,
            )
        except Exception as b_exc:
            logger.debug("Lỗi tạo ảnh Spotlight Banner: %s", b_exc)

        msg = await _send_channel_post_with_banner(client, ch_name, text, rows, banner_io)
        if msg:
            _LAST_SPOTLIGHT_MSG_ID = msg.id
        return msg.id if msg else None
    except Exception as exc:
        logger.debug("Không thể đăng bài Spotlight lên kênh: %s", exc)
        return None


async def post_catalog_to_channel(client: TelegramClient, pin: bool = True, delete_old: bool = True) -> int | None:
    """Tổng hợp bảng giá VNĐ + tồn kho kèm Banner Bảng Giá HD và đăng lên @KingToolShopOfficial."""
    ch_name = db.get_setting("support_channel", "KingToolShopOfficial").lstrip("@").strip()
    support_name = db.get_setting("support_admin", "KingToolShopSupport").lstrip("@").strip()
    products = await ps_client.sync_products(force=False)
    overrides = db.get_all_overrides()
    backup_map = db.get_all_backup_sources()

    in_stock_lines: list[str] = []
    featured_tuples: list[tuple[str, int, str]] = []
    for p in products:
        pid = p["id"]
        ov = overrides.get(pid, {})
        if ov.get("hidden"):
            continue
        eff_st, eff_in_stock, p_st, _ = db.get_effective_product_stock(p, backup_map)
        if not eff_in_stock:
            continue
        price_vnd = db.compute_retail_price(pid, float(p["price"]), overrides, primary_stock=p_st, backup_map=backup_map)
        st_txt = f"Còn {eff_st} suất" if isinstance(eff_st, int) and eff_st > 0 else "Sẵn hàng"
        featured_tuples.append((p["name"].strip(), price_vnd, st_txt))
        in_stock_lines.append(f"🟢 **{p['name'].strip()}** — `{price_vnd:,}đ`")

    now_vn_str = datetime.now(VN_TZ).strftime("%H:%M %d/%m/%Y")
    gift_code = db.get_setting("newbie_gift_voucher", "TANTHU10").strip().upper() or "TANTHU10"
    total_avail = len(in_stock_lines)
    catalog_block = "\n".join(in_stock_lines[:11]) if in_stock_lines else "Đang cập nhật kho hàng..."
    if total_avail > 11:
        catalog_block += f"\n✨ *...và hơn **{total_avail - 11} sản phẩm AI & Phần mềm khác** đang sẵn kho trong Bot!*"

    text = (
        "👑 **KINGTOOL SHOP — HỆ THỐNG TÀI KHOẢN & KEY AI TỰ ĐỘNG 24/7** 👑\n"
        f"🕒 *Cập nhật kho: `{now_vn_str}` — 🟢 Sẵn hàng: `{total_avail}+ SP`*\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "✅ **Giao dịch tự động 100%** — Nhận tài khoản/key sau **2 giây**!\n"
        "✅ **Thanh toán VietQR nội địa** — Tự động cộng thưởng nạp tới **+10%**.\n"
        f"🎁 **Ưu đãi Tân Thủ:** Nhận ngay **Điểm thưởng + Mã `{gift_code}` (-10%)**!\n\n"
        "🔥 **TIÊU ĐIỂM SẢN PHẨM ĐANG SẴN HÀNG:**\n"
        f"{catalog_block}\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"🤖 **Mua tự động:** @{BOT_USERNAME_CACHE} | 🆘 **CSKH:** @{support_name}"
    )
    rows = [
        [Button.url(f"🛒 MỞ BOT XEM TOÀN BỘ {total_avail}+ SẢN PHẨM", f"https://t.me/{BOT_USERNAME_CACHE}")],
        [Button.url(f"🎁 NHẬN QUÀ TÂN THỦ & MÃ GIẢM GIÁ ({gift_code})", f"https://t.me/{BOT_USERNAME_CACHE}?start=GIFT")],
        [Button.url("🆘 Trung Tâm Hỗ Trợ & Bảo Hành (CSKH)", f"https://t.me/{support_name}")],
    ]

    if delete_old:
        old_mid = int(float(db.get_setting("last_catalog_msg_id", "0") or 0))
        if old_mid > 0:
            try:
                await client.delete_messages(ch_name, [old_mid])
            except Exception:
                pass

    banner_io = None
    try:
        banner_io = generate_catalog_banner(
            featured_items=featured_tuples[:8],
            total_in_stock=total_avail,
            updated_str=now_vn_str,
            gift_code=gift_code,
            bot_username=BOT_USERNAME_CACHE,
        )
    except Exception as b_exc:
        logger.debug("Lỗi tạo ảnh Catalog Banner: %s", b_exc)

    msg = await _send_channel_post_with_banner(client, ch_name, text, rows, banner_io)
    if msg:
        db.set_setting("last_catalog_msg_id", str(msg.id))
        if pin:
            try:
                await client.pin_message(ch_name, msg.id, notify=False)
            except Exception:
                pass
        return msg.id
    return None


async def check_and_remind_abandoned_deposits(client: TelegramClient) -> None:
    """Nhắc nhở nhẹ nhàng cho khách tạo mã QR nạp tiền sau 10-45 phút mà chưa hoàn tất chuyển khoản."""
    try:
        if str(db.get_setting("deposit_reminder_enabled", "1") or "0").strip() != "1":
            return
        pending_list = db.get_unreminded_pending_deposits(min_age_minutes=10, max_age_minutes=45)
        if not pending_list:
            return
        support_name = db.get_setting("support_admin", "KingToolShopSupport").lstrip("@").strip()
        for dep in pending_list:
            dep_id = int(dep["id"])
            if dep_id in _REMINDED_DEPOSIT_IDS:
                continue
            _REMINDED_DEPOSIT_IDS.add(dep_id)
            uid = int(dep["user_id"])
            amt_vnd = vnd_int(dep["amount_vnd"])
            memo = dep.get("memo") or f"NAP{dep_id}"
            u = db.get_or_create_user(uid)
            u_lang = u.get("language", "vi")
            rows = [
                [Button.inline(t(u_lang, "vietqr_paid_btn"), f"dep:Paid:{dep_id}".encode(), style="success")],
                [Button.inline(t(u_lang, "deposit_now_btn"), b"menu:deposit", style="primary")],
                [Button.url(f"🆘 @{support_name}", f"https://t.me/{support_name}")],
            ]
            try:
                await client.send_message(
                    uid,
                    t(u_lang, "deposit_reminder_msg", dep_id=dep_id, amount_vnd=amt_vnd, memo=memo),
                    buttons=rows,
                )
            except Exception:
                pass
    except Exception as exc:
        logger.debug("Lỗi kiểm tra nhắc đơn nạp bỏ dở: %s", exc)


async def render_newbie_gift_funnel(event: Any, force_new: bool = False) -> None:
    """Hiển thị màn hình Phễu Quà Tân Thủ yêu cầu tham gia Kênh @KingToolShopOfficial & Nhóm @KingToolShopSupport."""
    u, lang = await get_user_info(event)
    channel_user = db.get_setting("support_channel", "KingToolShopOfficial").lstrip("@").strip()
    group_user = db.get_setting("support_admin", "KingToolShopSupport").lstrip("@").strip()
    gift_pts = max(1, int(float(db.get_setting("newbie_gift_points", "5") or 5)))
    gift_code = db.get_setting("newbie_gift_voucher", "TANTHU10").strip().upper() or "TANTHU10"

    rows = [
        [Button.url(t(lang, "newbie_gift_join_btn", channel=channel_user), f"https://t.me/{channel_user}")],
        [Button.url(t(lang, "newbie_gift_group_btn", group=group_user), f"https://t.me/{group_user}")],
        [Button.inline(t(lang, "newbie_gift_claim_btn"), b"gift:claim", style="success")],
        [Button.inline(t(lang, "btn_back"), b"menu:home")],
    ]
    await send_or_edit(
        event,
        t(lang, "newbie_gift_title", channel=channel_user, group=group_user, pts=gift_pts, code=gift_code),
        buttons=rows,
        force_new=force_new,
    )


async def handle_claim_newbie_gift(client: TelegramClient, event: Any) -> None:
    """Kiểm tra khách đã tham gia Kênh @KingToolShopOfficial & Nhóm @KingToolShopSupport chưa và trao Quà Tân Thủ."""
    u, lang = await get_user_info(event)
    uid = u["telegram_id"]
    if int(u.get("gift_claimed", 0) or 0) == 1:
        await event.answer(t(lang, "newbie_gift_already_claimed"), alert=True)
        return

    channel_user = db.get_setting("support_channel", "KingToolShopOfficial").lstrip("@").strip()
    group_user = db.get_setting("support_admin", "KingToolShopSupport").lstrip("@").strip()
    all_ok, joined_ch, joined_grp = await check_user_joined_community(client, uid, force_refresh=True)

    if not all_ok:
        if not joined_ch and not joined_grp:
            await event.answer(t(lang, "newbie_gift_not_joined", channel=channel_user, group=group_user), alert=True)
        elif not joined_ch:
            await event.answer(t(lang, "force_join_missing_channel", channel=channel_user), alert=True)
        else:
            await event.answer(t(lang, "force_join_missing_group", group=group_user), alert=True)
        return

    gift_pts = max(1, int(float(db.get_setting("newbie_gift_points", "5") or 5)))
    gift_code = db.get_setting("newbie_gift_voucher", "TANTHU10").strip().upper() or "TANTHU10"
    if not db.get_voucher(gift_code):
        db.create_or_update_voucher(gift_code, "percent", 10.0, max_uses=0)

    claimed, total_pts = db.claim_newbie_gift(uid, bonus_points=gift_pts)
    if not claimed:
        await event.answer(t(lang, "newbie_gift_already_claimed"), alert=True)
        return

    # Tự động gắn sẵn mã giảm giá Tân thủ vào giỏ hàng để khách bấm vào SP nào cũng thấy giá đã giảm ngay!
    USER_ACTIVE_VOUCHER[uid] = gift_code
    await event.answer("🎉", alert=False)
    rows = [
        [Button.inline(t(lang, "newbie_gift_shop_btn", code=gift_code), b"menu:products", style="success")],
        [Button.inline(t(lang, "btn_back"), b"menu:home")],
    ]
    await send_or_edit(
        event,
        t(lang, "newbie_gift_success", pts_added=gift_pts, total_pts=total_pts, code=gift_code),
        buttons=rows,
    )



# ==================== DEPOSIT & HOA HỒNG GIỚI THIỆU (VIETQR VNĐ) ====================
async def reward_referrer_on_deposit(client: TelegramClient, dep: dict[str, Any]) -> None:
    """Cộng hoa hồng tự động cho người giới thiệu khi khách nạp tiền thành công."""
    try:
        u = db.get_or_create_user(int(dep["user_id"]))
        ref_id = u.get("referred_by")
        if not ref_id:
            return
        comm_pct = float(db.get_setting("referral_commission_pct", "5.0") or 0.0)
        if comm_pct <= 0:
            return
        amt_vnd = vnd_int(dep["amount_vnd"])
        comm_vnd = int(round(amt_vnd * comm_pct / 100.0))
        if comm_vnd <= 0:
            return
        ref_new_bal = db.adjust_balance(int(ref_id), comm_vnd)
        await client.send_message(
            int(ref_id),
            (
                f"🎁 **HOA HỒNG GIỚI THIỆU (+{comm_pct:g}%)**\n\n"
                f"👤 Bạn bè của bạn (`{dep['user_id']}`) vừa nạp **{amt_vnd:,}đ**.\n"
                f"💵 Bạn nhận được: **+{comm_vnd:,}đ** vào số dư ví!\n"
                f"💰 Số dư mới của bạn: **{ref_new_bal:,}đ**"
            ),
        )
    except Exception as exc:
        logger.debug("Không thể cộng hoa hồng giới thiệu: %s", exc)


async def render_deposit_menu(event: Any) -> None:
    u, lang = await get_user_info(event)
    rows = [
        [Button.inline(t(lang, "vietqr_method_btn"), b"dep:method:vietqr", style="success")],
        [Button.inline(t(lang, "btn_back"), b"menu:home")],
    ]
    await send_or_edit(event, t(lang, "deposit_title"), buttons=rows)


async def render_deposit_amounts(event: Any) -> None:
    u, lang = await get_user_info(event)
    amounts_vnd = [20000, 50000, 100000, 200000, 500000, 1000000]
    tiers = db.get_deposit_bonus_tiers()
    bonus_banner = ""
    if tiers:
        if lang == "vi":
            tiers_str = " | ".join(f"Nạp từ **{m:,}đ** tặng **+{p:g}%**" for m, p in tiers)
        else:
            tiers_str = " | ".join(f"From **{m:,}đ** get **+{p:g}%**" for m, p in tiers)
        bonus_banner = t(lang, "deposit_bonus_banner", tiers_text=tiers_str)

    rows: list[list[Any]] = []
    for i in range(0, len(amounts_vnd), 2):
        pair = amounts_vnd[i : i + 2]
        row = []
        for vnd in pair:
            _, b_pct = db.compute_deposit_bonus(vnd)
            lbl = f"🎁 {vnd:,}đ (+{b_pct:g}%)" if b_pct > 0 else f"{vnd:,}đ"
            row.append(Button.inline(lbl, f"dep:create:vietqr:{vnd}".encode(), style="success"))
        rows.append(row)
    rows.append([Button.inline(t(lang, "custom_amount_btn"), b"dep:custom:vietqr", style="primary")])
    rows.append([Button.inline(t(lang, "btn_back"), b"menu:deposit")])
    await send_or_edit(event, t(lang, "deposit_choose_amount", bonus_banner=bonus_banner), buttons=rows)


async def create_and_show_deposit(
    client: TelegramClient,
    event: Any,
    amount_vnd: int,
) -> None:
    u, lang = await get_user_info(event)
    uid = u["telegram_id"]
    spx_suffix = "".join(random.choices("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ", k=6))
    spx_code = f"SPX{spx_suffix}"
    memo = f"KINGTOOL CAM ON {spx_code}"

    dep_id = db.create_deposit(
        user_id=uid,
        username=u["username"],
        amount_usd=float(amount_vnd),
        amount_vnd=amount_vnd,
        method="vietqr",
        memo=memo,
    )

    rows = [
        [Button.inline(t(lang, "vietqr_paid_btn"), f"dep:Paid:{dep_id}".encode(), style="success")],
        [Button.inline(t(lang, "btn_back"), b"menu:deposit_qr")],
    ]

    bank_id = db.get_setting("bank_id", "MB").strip()
    acc_no = db.get_setting("bank_account_no", "0123456789").strip()
    acc_name = db.get_setting("bank_account_name", "NGUYEN VAN A").strip()
    qr_url = (
        f"https://img.vietqr.io/image/{urllib.parse.quote(bank_id)}-{urllib.parse.quote(acc_no)}-compact2.png"
        f"?amount={amount_vnd}&addInfo={urllib.parse.quote(memo)}&accountName={urllib.parse.quote(acc_name)}"
    )
    caption = t(
        lang,
        "vietqr_caption",
        dep_id=dep_id,
        bank_id=bank_id,
        acc_no=acc_no,
        acc_name=acc_name,
        amount_vnd=amount_vnd,
        memo=memo,
    )
    try:
        await client.send_file(
            event.chat_id,
            file=qr_url,
            caption=caption,
            buttons=rows,
        )
    except Exception:
        await send_or_edit(event, caption + f"\n\n🔗 [Mở ảnh QR VietQR]({qr_url})", buttons=rows, force_new=True)


# ==================== SEPAY TỰ ĐỘNG BAN ĐÊM (23:00 - 06:00) ====================
def extract_spx_code(memo_str: str, dep_id: int) -> str:
    """Trích xuất mã SPX... từ nội dung chuyển khoản để đối soát chính xác."""
    for part in (memo_str or "").upper().split():
        if part.startswith("SPX") and len(part) > 3:
            return part
    return f"NAP{dep_id}".upper()


async def check_sepay_transaction(dep: dict[str, Any]) -> str | None:
    """Kiểm tra trên SePay API xem đã có giao dịch tiền vào khớp mã SPX... và số tiền chưa."""
    token = (db.get_setting("sepay_api_token", "") or os.getenv("SEPAY_API_TOKEN", "")).strip()
    if not token:
        return None
    import httpx

    memo_full = (dep.get("memo") or f"NAP{dep['id']}").strip().upper()
    target_code = extract_spx_code(memo_full, int(dep["id"]))
    need_vnd = float(dep["amount_vnd"])
    try:
        async with httpx.AsyncClient(timeout=15.0) as hc:
            resp = await hc.get(
                "https://my.sepay.vn/userapi/transactions/list?limit=20",
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            )
            if resp.status_code != 200:
                return None
            tx_list = resp.json().get("transactions", [])
            for tx in tx_list:
                amt_in = float(tx.get("amount_in", 0) or 0)
                content = f"{tx.get('transaction_content', '')} {tx.get('code', '')}".upper()
                if amt_in >= need_vnd and (target_code in content or memo_full in content):
                    return str(tx.get("id") or tx.get("reference_number") or "SEPAY_OK")
    except Exception as exc:
        logger.debug("Lỗi kiểm tra SePay API: %s", exc)
    return None


async def try_night_sepay_auto_approve(client: TelegramClient, dep: dict[str, Any]) -> bool:
    """Tự động duyệt trong khung giờ ngủ (23h00 -> 06h00 sáng) qua SePay."""
    if not db.is_in_night_auto_window():
        return False
    used, limit, can_use = db.get_sepay_quota_status()
    if not can_use:
        return False

    tx_id = await check_sepay_transaction(dep)
    if not tx_id:
        return False

    dep_id = int(dep["id"])
    amt_vnd = vnd_int(dep["amount_vnd"])
    orig_memo = dep.get("memo") or f"NAP{dep_id}"
    if not db.update_deposit_status(dep_id, "approved", memo=f"{orig_memo} [SEPAY:{tx_id}]"):
        return True

    new_used = db.increment_sepay_used()
    bonus_vnd, bonus_pct = db.compute_deposit_bonus(amt_vnd)
    total_added = amt_vnd + bonus_vnd
    new_bal = db.adjust_balance(dep["user_id"], total_added)
    await reward_referrer_on_deposit(client, dep)

    target_user = db.get_or_create_user(int(dep["user_id"]))
    u_lang = target_user.get("language", "vi")
    try:
        if bonus_vnd > 0:
            msg_txt = t(
                u_lang,
                "deposit_approved_bonus_msg",
                dep_id=dep_id,
                amt_vnd=amt_vnd,
                bonus_pct=f"{bonus_pct:g}",
                bonus_vnd=bonus_vnd,
                total_added=total_added,
                new_bal=new_bal,
            )
        else:
            msg_txt = t(u_lang, "deposit_approved_msg", dep_id=dep_id, amt_vnd=amt_vnd, new_bal=new_bal)
        await client.send_message(dep["user_id"], msg_txt)
    except Exception:
        pass

    quota_warn = (
        f"\n⚠️ **Chú ý:** Đã chạm mốc **{new_used}/{limit}** giao dịch miễn phí của SePay trong tháng này. "
        f"Từ đơn tiếp theo hệ thống sẽ tự động chuyển về **Duyệt Bằng Tay**!"
        if new_used >= limit
        else ""
    )
    bonus_adm = f" (+KM `{bonus_vnd:,}đ`)" if bonus_vnd > 0 else ""
    user_line_adm = format_admin_user_line(int(dep["user_id"]), target_user, str(dep.get("username") or ""))
    adm_btns = [build_admin_user_buttons(int(dep["user_id"]))]
    for adm_id in ADMIN_IDS:
        try:
            await client.send_message(
                adm_id,
                (
                    f"🌙 **[SEPAY TỰ ĐỘNG DUYỆT BAN ĐÊM #{dep_id}]**\n\n"
                    f"{user_line_adm}\n"
                    f"💵 Đã cộng tự động: **+{total_added:,}đ**{bonus_adm} (Số dư mới: **{new_bal:,}đ**)\n"
                    f"📊 Lượt SePay Free đã dùng tháng này: **{new_used}/{limit} giao dịch**"
                    f"{quota_warn}"
                ),
                buttons=adm_btns,
            )
        except Exception:
            pass
    return True


async def poll_night_sepay_deposits_loop(client: TelegramClient) -> None:
    """Quét ngầm mỗi 30 giây trong khung 23h00 - 06h00 sáng nếu có đơn nạp đang chờ."""
    while True:
        await asyncio.sleep(30)
        try:
            if not db.is_in_night_auto_window():
                continue
            _, _, can_use = db.get_sepay_quota_status()
            if not can_use:
                continue
            pending_deps = db.get_pending_deposits()
            for dep in pending_deps:
                await try_night_sepay_auto_approve(client, dep)
        except Exception as exc:
            logger.debug("Lỗi vòng lặp SePay ban đêm: %s", exc)


async def poll_products_sync_loop(client: TelegramClient) -> None:
    """Đồng bộ danh mục sản phẩm và tồn kho ngầm mỗi 60 giây, phát hiện Restock, kiểm tra vốn & chạy Phễu Tự Động."""
    global _LAST_KNOWN_STOCK, _LAST_AUTO_POST_HOUR_KEY, _LAST_SIM_SOCIAL_TS
    try:
        d_key_init = (db.get_setting("dante_api_key", "") or os.getenv("DANTE_API_KEY", "")).strip()
        d_url_init = (db.get_setting("dante_base_url", DANTE_BASE_URL) or DANTE_BASE_URL).strip()
        if d_key_init:
            await ps_client.sync_all_dante_backups(db, d_key_init, d_url_init, auto_seed_defaults=True)
        init_prods = await ps_client.sync_products(force=False)
        init_bmap = db.get_all_backup_sources()
        for p in init_prods:
            pid = str(p.get("id", ""))
            if pid:
                eff_st, eff_in_stock, _, _ = db.get_effective_product_stock(p, init_bmap)
                _LAST_KNOWN_STOCK[pid] = int(eff_st or 1) if eff_in_stock else 0
    except Exception:
        pass

    _LAST_SIM_SOCIAL_TS = time.time()
    loop_cnt = 0
    while True:
        await asyncio.sleep(60)
        loop_cnt += 1
        try:
            # Đồng bộ tồn kho các nguồn API dự phòng (@DanteHubBot & các API khác) + làm mới bộ đệm DB ngầm mỗi 5 phút
            if loop_cnt % 5 == 1:
                d_key = (db.get_setting("dante_api_key", "") or os.getenv("DANTE_API_KEY", "")).strip()
                d_url = (db.get_setting("dante_base_url", DANTE_BASE_URL) or DANTE_BASE_URL).strip()
                if d_key:
                    try:
                        await ps_client.sync_all_dante_backups(db, d_key, d_url, auto_seed_defaults=False)
                    except Exception as d_exc:
                        logger.debug("Không thể đồng bộ định kỳ @DanteHubBot: %s", d_exc)

                bmap_now = db.get_all_backup_sources()
                rate_now = float(db.get_setting("vnd_rate", "25500") or 25500.0)
                ext_updates: list[tuple[int, int, int | None]] = []
                for _, src_list in bmap_now.items():
                    for src in src_list:
                        if src.get("source_type") == "api" and int(src.get("active", 0) or 0) == 1:
                            b_url = str(src.get("api_base_url", ""))
                            if ps_client.is_dantehub_url(b_url):
                                continue
                            info = await ps_client.fetch_external_api_product(
                                b_url,
                                str(src.get("api_key", "")),
                                str(src.get("remote_product_id", "")),
                            )
                            if info:
                                new_st = int(info.get("stock", 0) or 0) if info.get("inStock") else 0
                                r_price = float(info.get("price", 0) or 0)
                                new_cost = None
                                if r_price > 0:
                                    new_cost = int(round(r_price)) if r_price >= 500 else int(round(r_price * rate_now))
                                old_st = int(src.get("remote_stock", 0) or 0)
                                old_cost = int(src.get("cost_vnd", 0) or 0)
                                if old_st != new_st or (new_cost is not None and abs(old_cost - new_cost) >= 10):
                                    ext_updates.append((int(src["id"]), new_st, new_cost))
                if ext_updates:
                    db.bulk_update_api_backup_stocks(ext_updates)
                db.warm_all_caches()

            products = await ps_client.sync_products(force=True)
            overrides = db.get_all_overrides()
            backup_map = db.get_all_backup_sources()
            restocked: list[dict[str, Any]] = []
            for p in products:
                pid = str(p.get("id", ""))
                if not pid:
                    continue
                eff_st, eff_in_stock, _, _ = db.get_effective_product_stock(p, backup_map)
                cur_stock = int(eff_st or 1) if eff_in_stock else 0
                prev_stock = _LAST_KNOWN_STOCK.get(pid)
                _LAST_KNOWN_STOCK[pid] = cur_stock

                ov = overrides.get(pid, {})
                if ov.get("hidden"):
                    continue
                if prev_stock is not None and prev_stock == 0 and cur_stock > 0:
                    restocked.append(p)

            if restocked:
                await post_restock_notification(client, restocked)

            # 1. Nhắc nhở khách hàng bỏ dở đơn nạp VietQR sau 10-45 phút
            await check_and_remind_abandoned_deposits(client)

            # 2. Tự động đăng Bảng giá & Spotlight SP Hot theo khung giờ vàng (VD: 9h, 14h, 20h)
            now_vn = datetime.now(VN_TZ)
            if str(db.get_setting("auto_post_enabled", "1") or "0").strip() == "1":
                raw_hours = db.get_setting("auto_post_hours", "9,14,20")
                target_hours = {
                    int(x.strip())
                    for x in raw_hours.split(",")
                    if x.strip().isdigit() and 0 <= int(x.strip()) <= 23
                }
                hour_key = now_vn.strftime("%Y-%m-%d-%H")
                if now_vn.hour in target_hours and hour_key != _LAST_AUTO_POST_HOUR_KEY:
                    _LAST_AUTO_POST_HOUR_KEY = hour_key
                    await post_catalog_to_channel(client, pin=True, delete_old=True)
                    await asyncio.sleep(2)
                    await post_spotlight_to_channel(client)

            # 3. Tự động đăng thông báo đơn hàng hoàn tất (Social Proof) định kỳ trong khung 08h - 22h
            if (
                str(db.get_setting("auto_social_proof_enabled", "1") or "0").strip() == "1"
                and 8 <= now_vn.hour <= 22
                and (time.time() - _LAST_SIM_SOCIAL_TS >= 12600.0)
            ):
                _LAST_SIM_SOCIAL_TS = time.time()
                await post_simulated_social_proof(client)

            if loop_cnt % 15 == 0:
                await check_and_alert_low_prodseller_balance(client)
        except Exception as exc:
            logger.debug("Lỗi đồng bộ sản phẩm định kỳ: %s", exc)


# ==================== ADMIN PANEL (VNĐ - GIAO DIỆN GOM NHÓM THƯ MỤC GỌN ĐẸP) ====================
SETTING_PARENT_FOLDER: dict[str, str] = {
    "markup_percent": "pricing",
    "min_profit_percent": "pricing",
    "markup_fixed": "pricing",
    "vnd_rate": "pricing",
    "dante_api_key": "catalog",
    "low_balance_threshold_usd": "catalog",
    "deposit_bonus_tiers": "promos",
    "sepay_api_token": "payment",
    "methods_text": "users",
}


async def _fetch_admin_supplier_balances(settings: dict[str, str], rate: float) -> tuple[str, str]:
    dante_key = (settings.get("dante_api_key", "") or os.getenv("DANTE_API_KEY", "")).strip()
    dante_url = (settings.get("dante_base_url", DANTE_BASE_URL) or DANTE_BASE_URL).strip()

    async def _get_ps() -> str:
        try:
            b_info = await ps_client.get_balance()
            ps_usd = float(b_info.get("balance", 0.0))
            ps_vnd = int(round(ps_usd * rate))
            return f"{ps_vnd:,}đ (${ps_usd:.2f} | Hạng: {b_info.get('membership', 'bronze')})"
        except Exception as exc:
            return f"Lỗi kết nối ({exc})"

    async def _get_dh() -> str:
        if not dante_key:
            return "Chưa cài API Key (Vào 📁 Kho Hàng -> 🔑 Key @DanteHubBot)"
        try:
            d_info = await ps_client.get_external_balance(dante_url, dante_key)
            d_usd = float(d_info.get("balance", 0.0) or 0.0)
            d_vnd = int(round(d_usd * rate))
            return f"{d_vnd:,}đ (${d_usd:.2f} {d_info.get('currency', 'USDT')} | Đã kết nối 🟢)"
        except Exception as exc:
            return f"Lỗi kết nối ({exc})"

    return await asyncio.gather(_get_ps(), _get_dh())


async def render_admin_home(event: Any, force_new: bool = False) -> None:
    uid = event.sender_id
    if not is_admin(uid):
        return
    USER_AWAITING.pop(uid, None)
    stats = db.get_summary_stats()
    settings = db.get_all_settings()
    rate = float(settings.get("vnd_rate", "25500") or 25500.0)
    ps_bal_str, dante_bal_str = await _fetch_admin_supplier_balances(settings, rate)

    min_profit_pct = float(settings.get("min_profit_percent", "150.0") or 150.0)
    active_src_cnt, total_backup_keys = db.get_backup_summary_stats()
    pending_cnt = stats.get("pending_deposits_count", 0)

    text = (
        "⚙️ **BẢNG ĐIỀU KHIỂN ADMIN (RESELLER PANEL)**\n\n"
        f"🏦 **Vốn Nguồn 1 (@ProdSellerBot):** `{ps_bal_str}`\n"
        f"🏦 **Vốn Nguồn 2 (@DanteHubBot):** `{dante_bal_str}`\n"
        f"📦 **Kho dự phòng đa nguồn:** **{active_src_cnt} nguồn** đang bật (**{total_backup_keys} key** sẵn sàng)\n"
        f"👥 Khách hàng: **{stats['users_count']}** | 📦 Tổng đơn: **{stats['orders_count']}** | ⏳ Chờ duyệt nạp: **{pending_cnt}**\n"
        f"💰 Doanh thu: **{vnd_int(stats['total_revenue']):,}đ** | 📉 Giá vốn: **{vnd_int(stats['total_cost']):,}đ**\n"
        f"💵 **Lợi nhuận ròng: +{vnd_int(stats['total_profit']):,}đ**\n"
        f"🛡️ *Định giá: Chuẩn `+{settings['markup_percent']}%` | Sàn lãi `>={min_profit_pct:g}%` | Tỷ giá `$1 = {int(rate):,}đ`*\n\n"
        "📂 **Chọn thư mục quản trị bên dưới:**"
    )

    rows = [
        [
            Button.inline(
                f"⏳ Đơn nạp chờ duyệt ({pending_cnt})",
                b"adm:deplist",
                style="success" if pending_cnt > 0 else None,
            ),
            Button.inline("📦 10 Đơn gần nhất", b"adm:orders"),
        ],
        [
            Button.inline(f"🔑 Kho Key & Link Thu Hồi ({total_backup_keys})", b"adm:local_keys", style="success"),
        ],
        [
            Button.inline("📁 Kho Hàng & Nguồn Cung", b"adm:dir:catalog", style="primary"),
            Button.inline("📁 Cài Đặt Giá & Lãi", b"adm:dir:pricing", style="primary"),
        ],
        [
            Button.inline("📁 Kênh & Auto Đăng Bài", b"adm:dir:marketing", style="primary"),
            Button.inline("📁 Voucher & KM Nạp", b"adm:dir:promos", style="primary"),
        ],
        [
            Button.inline("📁 Ngân Hàng & SePay", b"adm:dir:payment", style="primary"),
            Button.inline("📁 Quản Lý Khách Hàng", b"adm:dir:users", style="primary"),
        ],
        [
            Button.inline("« Về Menu Chính", b"menu:home"),
        ],
    ]
    await send_or_edit(event, text, buttons=rows, force_new=force_new)


async def render_admin_folder(event: Any, folder: str, force_new: bool = False) -> None:
    uid = event.sender_id
    if not is_admin(uid):
        return
    USER_AWAITING.pop(uid, None)
    settings = db.get_all_settings()
    rate = float(settings.get("vnd_rate", "25500") or 25500.0)
    fixed_val = vnd_int(settings.get("markup_fixed", "0"))
    min_profit_pct = float(settings.get("min_profit_percent", "150.0") or 150.0)

    if folder == "catalog":
        ps_bal_str, dante_bal_str = await _fetch_admin_supplier_balances(settings, rate)
        active_src_cnt, total_backup_keys = db.get_backup_summary_stats()
        low_bal_usd = float(settings.get("low_balance_threshold_usd", "5.0") or 0.0)
        total_prods = len(ps_client._products_cache)
        text = (
            "📁 **THƯ MỤC: KHO HÀNG & NGUỒN CUNG CẤP**\n\n"
            f"🛍️ Tổng sản phẩm trên Shop: **{total_prods} SP**\n"
            f"🏦 **Vốn Nguồn 1 (@ProdSellerBot):** `{ps_bal_str}`\n"
            f"🏦 **Vốn Nguồn 2 (@DanteHubBot):** `{dante_bal_str}`\n"
            f"📦 **Kho dự phòng đa nguồn:** **{active_src_cnt} nguồn** đang bật (**{total_backup_keys} key** sẵn sàng)\n"
            f"🔔 Cảnh báo sắp hết vốn: **Khi dưới `${low_bal_usd:.2f}`**"
        )
        rows = [
            [Button.inline(f"🔑 Xem Kho Key Nội Bộ & Link Thu Hồi ({total_backup_keys} key)", b"adm:local_keys", style="success")],
            [Button.inline("🏷️ Quản lý SP & Nguồn Hàng Dự Phòng", b"adm:plist:0", style="primary")],
            [
                Button.inline("🔄 Đồng bộ Kho ngay", b"adm:sync", style="success"),
                Button.inline("🔄 Đồng Bộ @DanteHubBot", b"adm:dante_sync", style="success"),
            ],
            [
                Button.inline("🔑 Key @DanteHubBot", b"adm:set:dante_api_key"),
                Button.inline("🔔 Mốc Báo Hết Vốn ($)", b"adm:set:low_balance_threshold_usd"),
            ],
            [Button.inline("« Về Bảng Quản Trị Admin", b"adm:home")],
        ]

    elif folder == "pricing":
        text = (
            "📁 **THƯ MỤC: CÀI ĐẶT GIÁ BÁN & LỢI NHUẬN**\n\n"
            f"• 📈 Tăng giá chuẩn (Markup %): **+{settings['markup_percent']}%**\n"
            f"• 🛡️ Sàn lãi tối thiểu (Khi bù hàng nguồn phụ): **>= +{min_profit_pct:g}%** *(Giữ nguyên giá nếu lãi >= {min_profit_pct:g}%)*\n"
            f"• ➕ Cộng thêm cố định mỗi SP: **+{fixed_val:,}đ**\n"
            f"• 💱 Tỷ giá quy đổi USD -> VNĐ: **$1 = {int(rate):,}đ**"
        )
        rows = [
            [
                Button.inline(f"📈 Markup Chuẩn (+{settings['markup_percent']}%)", b"adm:set:markup_percent", style="primary"),
                Button.inline(f"🛡️ Sàn Lãi Tối Thiểu (>={min_profit_pct:g}%)", b"adm:set:min_profit_percent", style="primary"),
            ],
            [
                Button.inline("➕ Chỉnh +VNĐ Cố định", b"adm:set:markup_fixed"),
                Button.inline("💱 Đổi Tỷ giá USD->VNĐ", b"adm:set:vnd_rate"),
            ],
            [Button.inline("🏷️ Đặt giá bán riêng từng Sản phẩm", b"adm:plist:0")],
            [Button.inline("« Về Bảng Quản Trị Admin", b"adm:home")],
        ]

    elif folder == "marketing":
        autopost_on = str(settings.get("auto_post_enabled", "1") or "0").strip() == "1"
        autopost_hours = settings.get("auto_post_hours", "9,14,20")
        autopost_status = f"🟢 Đang BẬT (`{autopost_hours}h`)" if autopost_on else "🔴 Đang TẮT"

        restock_on = str(settings.get("restock_notify_enabled", "1") or "0").strip() == "1"
        restock_status = "🟢 Đang BẬT" if restock_on else "🔴 Đang TẮT"

        social_on = str(settings.get("auto_social_proof_enabled", "1") or "0").strip() == "1"
        social_status = "🟢 Đang BẬT" if social_on else "🔴 Đang TẮT"

        gift_on = str(settings.get("newbie_gift_enabled", "1") or "0").strip() == "1"
        gift_vch = settings.get("newbie_gift_voucher", "TANTHU10")
        gift_pts = settings.get("newbie_gift_points", "5")
        gift_status = f"🟢 Đang BẬT (`+{gift_pts} điểm & {gift_vch}`)" if gift_on else "🔴 Đang TẮT"

        fjoin_on = str(settings.get("force_join_enabled", "1") or "0").strip() == "1"
        fjoin_status = "🟢 Đang BẬT (Bắt buộc trước khi mua)" if fjoin_on else "🔴 Đang TẮT"

        ch_name = settings.get("support_channel", "KingToolShopOfficial").lstrip("@")
        grp_name = settings.get("support_admin", "KingToolShopSupport").lstrip("@")

        text = (
            "📁 **THƯ MỤC: KÊNH, NHÓM & TỰ ĐỘNG ĐĂNG BÀI**\n\n"
            f"• 📣 Kênh liên kết: **@{ch_name}** | 💬 Nhóm CSKH: **@{grp_name}**\n"
            f"• 🔒 Bắt buộc Join Kênh & Nhóm trước khi mua: **{fjoin_status}**\n"
            f"• ⏰ Tự động đăng bài Kênh theo giờ: **{autopost_status}**\n"
            f"• 📣 Tự động báo Hàng Về (Restock): **{restock_status}**\n"
            f"• 🤖 Tạo hiệu ứng Đơn Mồi (Social Proof): **{social_status}**\n"
            f"• 🎁 Phễu Quà Tân Thủ Join Kênh & Nhóm: **{gift_status}**"
        )
        rows = [
            [
                Button.inline("📢 Đăng Bảng Giá Kênh", b"adm:post_catalog", style="success"),
                Button.inline("🔥 Đăng Bài SP Hot Ngay", b"adm:post_spotlight", style="primary"),
            ],
            [
                Button.inline(
                    f"🔒 {'Tắt' if fjoin_on else 'Bật'} Bắt Buộc Join Kênh & Nhóm",
                    b"adm:tog_forcejoin",
                    style="primary" if fjoin_on else None,
                ),
            ],
            [
                Button.inline(f"⏰ {'Tắt' if autopost_on else 'Bật'} Auto Đăng Kênh", b"adm:tog_autopost"),
                Button.inline(f"📣 {'Tắt' if restock_on else 'Bật'} Báo Restock", b"adm:tog_restock"),
            ],
            [
                Button.inline(f"🤖 {'Tắt' if social_on else 'Bật'} Đơn Mồi Kênh", b"adm:tog_social"),
                Button.inline(f"🎁 {'Tắt' if gift_on else 'Bật'} Quà Tân Thủ", b"adm:tog_gift"),
            ],
            [Button.inline("« Về Bảng Quản Trị Admin", b"adm:home")],
        ]

    elif folder == "promos":
        vouchers = db.get_all_vouchers()
        bonus_on = str(settings.get("deposit_bonus_enabled", "1") or "0").strip() == "1"
        tiers_raw = settings.get("deposit_bonus_tiers", "200000:5,500000:10")
        bonus_status = f"🟢 Đang BẬT (`{tiers_raw}`)" if bonus_on else "🔴 Đang TẮT"

        remind_on = str(settings.get("deposit_reminder_enabled", "1") or "0").strip() == "1"
        remind_status = "🟢 Đang BẬT (sau 10p)" if remind_on else "🔴 Đang TẮT"

        text = (
            "📁 **THƯ MỤC: VOUCHER & KHUYẾN MÃI NẠP**\n\n"
            f"• 🎟️ Tổng số mã Voucher: **{len(vouchers)} mã** *(Chốt chặn chống lỗ vốn `>= cost_vnd` tự động)*\n"
            f"• 🎁 Khuyến mãi nạp tiền: **{bonus_status}**\n"
            f"• 💡 Nhắc khách hoàn tất đơn nạp bỏ dở: **{remind_status}**"
        )
        rows = [
            [
                Button.inline("🎟️ Quản lý Voucher", b"adm:vouchers", style="primary"),
                Button.inline("➕ Tạo Voucher Mới", b"adm:vch_add", style="success"),
            ],
            [
                Button.inline(f"🎁 {'Tắt' if bonus_on else 'Bật'} KM Nạp", b"adm:tog_bonus"),
                Button.inline("⚙️ Chỉnh Mốc KM Nạp", b"adm:set:deposit_bonus_tiers"),
            ],
            [
                Button.inline(f"💡 {'Tắt' if remind_on else 'Bật'} Nhắc Đơn Nạp", b"adm:tog_depremind"),
            ],
            [Button.inline("« Về Bảng Quản Trị Admin", b"adm:home")],
        ]

    elif folder == "payment":
        stats = db.get_summary_stats()
        pending_cnt = stats.get("pending_deposits_count", 0)
        used_sp, limit_sp, _ = db.get_sepay_quota_status()
        in_night = db.is_in_night_auto_window()
        has_token = bool((settings.get("sepay_api_token", "") or os.getenv("SEPAY_API_TOKEN", "")).strip())
        if not has_token:
            sepay_status = "Chưa cài Token (Đang Duyệt Tay 24/7)"
        elif used_sp >= limit_sp:
            sepay_status = f"Đã hết {used_sp}/{limit_sp} lượt Free -> Đã chuyển về Duyệt Tay"
        elif in_night:
            sepay_status = f"🟢 Đang BẬT Tự Động Đêm ({used_sp}/{limit_sp} lượt Free)"
        else:
            sepay_status = f"☀️ Ban ngày: Duyệt Tay (Đêm 23h-06h sẽ Tự Động | Đã dùng {used_sp}/{limit_sp})"

        text = (
            "📁 **THƯ MỤC: NGÂN HÀNG VIETQR & SEPAY**\n\n"
            f"• 🏦 Ngân hàng VietQR: **{settings['bank_id']} - {settings['bank_account_no']} ({settings['bank_account_name']})**\n"
            f"• 🌙 SePay (23h-06h): **{sepay_status}**\n"
            f"• ⏳ Đơn nạp đang chờ duyệt: **{pending_cnt} đơn**"
        )
        rows = [
            [
                Button.inline(
                    f"⏳ Đơn nạp chờ duyệt ({pending_cnt})",
                    b"adm:deplist",
                    style="success" if pending_cnt > 0 else "primary",
                )
            ],
            [
                Button.inline("🏦 Cài Ngân hàng VietQR", b"adm:bank"),
                Button.inline("🌙 Cài Token SePay (23h-06h)", b"adm:set:sepay_api_token"),
            ],
            [Button.inline("« Về Bảng Quản Trị Admin", b"adm:home")],
        ]

    else:  # "users"
        stats = db.get_summary_stats()
        adm_user = settings.get("support_admin", "KingToolShopSupport").lstrip("@")
        text = (
            "📁 **THƯ MỤC: QUẢN LÝ KHÁCH HÀNG & THÔNG BÁO**\n\n"
            f"• 👥 Tổng khách hàng: **{stats['users_count']} khách**\n"
            f"• 📦 Tổng đơn hàng: **{stats['orders_count']} đơn**\n"
            f"• 🆘 Nhóm CSKH: **@{adm_user}**\n"
            "💡 *Mẹo: Bấm **👥 Danh sách Khách hàng** bên dưới để xem tên hiển thị đầy đủ và nhắn tin trực tiếp 1 chạm tới bất kỳ khách nào (kể cả khách không đặt `@username`)!*"
        )
        rows = [
            [
                Button.inline("👥 Danh sách Khách hàng (Nhắn tin 1 chạm)", b"adm:userlist:0", style="success"),
            ],
            [
                Button.inline("🔍 Tra cứu theo Tên / ID", b"adm:finduser", style="primary"),
                Button.inline("💵 Cộng/Trừ tiền khách (VNĐ)", b"adm:addbal", style="primary"),
            ],
            [
                Button.inline("📣 Gửi thông báo (Broadcast)", b"adm:broadcast"),
                Button.inline("📦 10 Đơn gần nhất", b"adm:orders"),
            ],
            [Button.inline("📖 Sửa bài Hướng dẫn (Methods)", b"adm:set:methods_text")],
            [Button.inline("« Về Bảng Quản Trị Admin", b"adm:home")],
        ]

    await send_or_edit(event, text, buttons=rows, force_new=force_new)


async def render_admin_vouchers(event: Any, force_new: bool = False) -> None:
    vouchers = db.get_all_vouchers()
    rows: list[list[Any]] = [
        [Button.inline("➕ Tạo Mã Giảm Giá Mới (5 giây)", b"adm:vch_add", style="success")],
    ]
    if not vouchers:
        text = (
            "🎟️ **QUẢN LÝ MÃ GIẢM GIÁ (VOUCHER)**\n\n"
            "📭 Hiện chưa có mã giảm giá nào.\n"
            "🛡️ *Chốt chặn an toàn: Mọi mã giảm giá đều tự động chặn sàn ở Giá vốn đại lý (`cost_vnd`), đảm bảo bạn không bao giờ bị lỗ vốn!*\n\n"
            "👉 Bấm **➕ Tạo Mã Giảm Giá Mới** bên dưới để tạo nhanh trong 5 giây."
        )
    else:
        lines = [
            "🎟️ **DANH SÁCH MÃ GIẢM GIÁ (VOUCHER)**\n"
            "🛡️ *Chốt chặn chống lỗ vốn (`>= Giá vốn ProdSeller`) đang BẬT tự động 100%.*\n"
        ]
        for code, v in vouchers.items():
            is_act = int(v.get("active", 0) or 0) == 1
            dtype = v.get("discount_type", "percent")
            dval = float(v.get("discount_value", 0) or 0)
            disc_str = f"-{dval:g}%" if dtype == "percent" else f"-{int(round(dval)):,}đ"
            max_u = int(v.get("max_uses", 0) or 0)
            used_u = int(v.get("used_count", 0) or 0)
            usage_str = f"{used_u}/{max_u} lượt" if max_u > 0 else f"{used_u}/∞ lượt"
            st_badge = "🟢 Đang BẬT" if is_act else "🔴 Đã TẮT"
            lines.append(f"• `{code}` | Giảm: **{disc_str}** | Đã dùng: **{usage_str}** [{st_badge}]")
            rows.append([
                Button.inline(
                    f"{'🔴 Tắt' if is_act else '🟢 Bật'} {code} ({usage_str})",
                    f"adm:vch_tog:{code}".encode(),
                    style="primary" if is_act else None,
                ),
                Button.inline(
                    f"🗑️ Xóa {code}",
                    f"adm:vch_del:{code}".encode(),
                    style="danger",
                ),
            ])
        text = "\n".join(lines)
    rows.append([
        Button.inline("« Về Thư mục Voucher & KM", b"adm:dir:promos"),
        Button.inline("⚙️ Bảng Admin", b"adm:home"),
    ])
    await send_or_edit(event, text, buttons=rows, force_new=force_new)


async def render_admin_pending_deposits(event: Any) -> None:
    deps = db.get_pending_deposits(limit=10)
    rows: list[list[Any]] = []
    if not deps:
        text = "✅ **Hiện không có đơn nạp tiền nào đang chờ duyệt!**"
    else:
        lines = ["⏳ **DANH SÁCH ĐƠN NẠP ĐANG CHỜ DUYỆT:**\n"]
        for d in deps:
            amt = vnd_int(d["amount_vnd"])
            d_uid = int(d["user_id"])
            safe_name, clickable_name, uname_disp = get_user_display_parts(d_uid, fallback_name=str(d.get("username") or ""))
            lines.append(
                f"• `#{d['id']}` | Khách: {clickable_name} (`{d_uid}` | {uname_disp}) — **{amt:,}đ**\n"
                f"  📝 `{d['memo']}` ({d['created_at']})"
            )
            rows.append([
                Button.inline(f"✅ Duyệt #{d['id']} (+{amt:,}đ)", f"adm:dep_ok:{d['id']}".encode(), style="success"),
                Button.inline(f"❌ Từ chối #{d['id']}", f"adm:dep_no:{d['id']}".encode(), style="danger"),
                Button.inline(f"💬 Nhắn {safe_name[:10]}", f"adm:msg:{d_uid}".encode(), style="primary"),
            ])
        text = "\n".join(lines)
    rows.append([
        Button.inline("📁 Ngân Hàng & SePay", b"adm:dir:payment"),
        Button.inline("« Về Bảng Admin", b"adm:home"),
    ])
    await send_or_edit(event, text, buttons=rows)


async def render_admin_recent_orders(event: Any) -> None:
    orders = db.get_recent_orders(limit=10)
    rows: list[list[Any]] = []
    if not orders:
        text = "📦 **Chưa có đơn hàng nào được ghi nhận.**"
    else:
        lines = ["📦 **10 ĐƠN HÀNG GẦN NHẤT TOÀN HỆ THỐNG:**\n"]
        seen_uids: list[tuple[int, str]] = []
        for o in orders:
            o_uid = int(o["user_id"])
            safe_name, clickable_name, uname_disp = get_user_display_parts(o_uid, fallback_name=str(o.get("username") or ""))
            if not any(x[0] == o_uid for x in seen_uids):
                seen_uids.append((o_uid, safe_name))
            lines.append(
                f"• `#{o['id']}` | {clickable_name} (`{o_uid}` | {uname_disp}) — **{o['product_name'][:22]}** (x{o['quantity']})\n"
                f"  💰 Bán: **{vnd_int(o['retail_price']):,}đ** | Vốn: {vnd_int(o['wholesale_cost']):,}đ | Lãi: **+{vnd_int(o['profit']):,}đ** [{o['status']}]"
            )
        for o_uid, s_name in seen_uids[:6]:
            rows.append([
                Button.inline(f"💬 Nhắn tin cho {s_name[:16]} ({o_uid})", f"adm:msg:{o_uid}".encode(), style="primary"),
                Button.inline("👤 Hồ sơ", f"adm:uinfo:{o_uid}".encode()),
            ])
        text = "\n".join(lines)
    rows.append([
        Button.inline("📁 Quản Lý Khách Hàng", b"adm:dir:users"),
        Button.inline("« Về Bảng Admin", b"adm:home"),
    ])
    await send_or_edit(event, text, buttons=rows)


async def render_admin_user_list(event: Any, page: int = 0) -> None:
    per_page = 10
    offset = max(0, page) * per_page
    users_list, total = db.get_recent_users(limit=per_page, offset=offset)
    max_page = max(0, (total - 1) // per_page)
    rows: list[list[Any]] = []
    if not users_list:
        text = "👥 **Chưa có khách hàng nào trong hệ thống.**"
    else:
        lines = [
            f"👥 **DANH SÁCH KHÁCH HÀNG ({total} KHÁCH — Trang {page + 1}/{max_page + 1})**\n"
            "💡 *Bấm vào tên khách để mở hồ sơ chi tiết, hoặc bấm nút **💬 Nhắn tin** để nhắn trực tiếp qua Bot:*"
        ]
        for u_item in users_list:
            t_uid = int(u_item["telegram_id"])
            safe_name, clickable_name, uname_disp = get_user_display_parts(t_uid, u_item)
            bal_vnd = vnd_int(u_item.get("balance", 0))
            ord_cnt = int(u_item.get("orders_count", 0) or 0)
            lines.append(
                f"• {clickable_name} | ID: `{t_uid}` | {uname_disp}\n"
                f"  💵 Ví: **{bal_vnd:,}đ** | 📦 Đã mua: **{ord_cnt} đơn** | 📅 `{str(u_item.get('joined_at', ''))[:10]}`"
            )
            rows.append([
                Button.inline(
                    f"👤 {safe_name[:16]} ({bal_vnd // 1000}k | {ord_cnt} đơn)",
                    f"adm:uinfo:{t_uid}".encode(),
                ),
                Button.inline(
                    "💬 Nhắn tin",
                    f"adm:msg:{t_uid}".encode(),
                    style="primary",
                ),
            ])
        text = "\n".join(lines)

    nav: list[Any] = []
    if page > 0:
        nav.append(Button.inline("⬅️ Trang trước", f"adm:userlist:{page - 1}".encode()))
    if offset + per_page < total:
        nav.append(Button.inline("Trang sau ➡️", f"adm:userlist:{page + 1}".encode()))
    if nav:
        rows.append(nav)
    rows.append([
        Button.inline("🔍 Tìm theo Tên / ID", b"adm:finduser", style="success"),
        Button.inline("« Về Thư mục Khách Hàng", b"adm:dir:users"),
    ])
    await send_or_edit(event, text, buttons=rows)


async def render_admin_user_detail(
    client: TelegramClient,
    event: Any,
    target_uid: int,
    force_new: bool = False,
) -> None:
    found = db.find_user(str(target_uid))
    if not found:
        await send_or_edit(
            event,
            f"❌ Không tìm thấy khách hàng có ID `{target_uid}`.",
            buttons=[[Button.inline("« Về Thư mục Khách Hàng", b"adm:dir:users")]],
            force_new=force_new,
        )
        return

    f_uid = int(found["telegram_id"])
    safe_name, clickable_name, uname_disp = get_user_display_parts(f_uid, found)
    all_ok, joined_ch, joined_grp = await check_user_joined_community(client, f_uid, force_refresh=True)
    ch_name = db.get_setting("support_channel", "KingToolShopOfficial").lstrip("@")
    grp_name = db.get_setting("support_admin", "KingToolShopSupport").lstrip("@")
    ch_badge = "✅ Đã vào" if joined_ch else "❌ Chưa vào"
    grp_badge = "✅ Đã vào" if joined_grp else "❌ Chưa vào"

    f_orders = db.get_user_orders(f_uid, limit=5)
    ord_summary = "\n".join(
        f"  • `#{o['id']}` **{o['product_name'][:22]}** (x{o['quantity']}) — **{vnd_int(o['retail_price']):,}đ** [{o['status']}]"
        for o in f_orders
    ) or "  *(Chưa có đơn hàng)*"

    history_block = format_customer_chat_history_block(f_uid, limit=8)

    info_txt = (
        f"👤 **HỒ SƠ CHI TIẾT & LỊCH SỬ TRÒ CHUYỆN KHÁCH HÀNG**\n\n"
        f"📛 Tên hiển thị: **{safe_name}**\n"
        f"🆔 Telegram ID: `{f_uid}`\n"
        f"🏷️ Username: {uname_disp}\n"
        f"📣 Kênh `@{ch_name}`: **{ch_badge}** | 💬 Nhóm `@{grp_name}`: **{grp_badge}**\n"
        f"💎 Hạng: **{str(found.get('tier', 'bronze')).upper()}**\n"
        f"💵 Số dư hiện tại: **{vnd_int(found.get('balance', 0)):,}đ**\n"
        f"⭐ Điểm thưởng: **{found.get('points', 0)}**\n"
        f"📦 Tổng đơn đã mua: **{found.get('orders_count', 0)}** (Chi tiêu: **{vnd_int(found.get('total_spent', 0)):,}đ**)\n"
        f"📅 Ngày tham gia: `{found.get('joined_at', '')}`\n\n"
        f"🛍️ **Đơn hàng gần nhất:**\n{ord_summary}\n\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"{history_block}"
    )
    rows: list[list[Any]] = [
        [Button.inline(f"💬 Mở Phiên Trò Chuyện Riêng (@KingToolShop_bot ↔ {safe_name[:12]})", f"adm:msg:{f_uid}".encode(), style="success")],
        [Button.inline("💵 Cộng / Trừ số dư khách này", f"adm:addbal_u:{f_uid}".encode(), style="primary")],
        [
            Button.inline("👥 Danh sách Khách hàng", b"adm:userlist:0"),
            Button.inline("« Thư mục Khách Hàng", b"adm:dir:users"),
        ],
    ]
    await send_or_edit(event, info_txt, buttons=rows, force_new=force_new)


async def render_admin_product_list(event: Any, page: int = 0) -> None:
    products = await ps_client.sync_products(force=False)
    overrides = db.get_all_overrides()
    backup_map = db.get_all_backup_sources()
    per_page = 10
    total = len(products)
    start = page * per_page
    end = start + per_page
    sliced = products[start:end]

    rows: list[list[Any]] = []
    for p in sliced:
        pid = p["id"]
        is_dh = p.get("provider") == "dantehub"
        _, _, p_st, b_st = db.get_effective_product_stock(p, backup_map)
        retail_vnd = db.compute_retail_price(pid, float(p["price"]), overrides, primary_stock=p_st, backup_map=backup_map)
        ov = overrides.get(pid, {})
        hidden_icon = "🙈 " if ov.get("hidden") else ""
        custom_tag = " 📌" if ov.get("custom_price") is not None else ""
        p_st_lbl = "∞" if p_st is None else str(p_st)
        src_tag = "DH" if is_dh else ("PS+DH" if b_st > 0 else "PS")
        b_tag = f"+{b_st}" if b_st > 0 else ""
        lbl = f"{hidden_icon}[{src_tag}] {p['name'].strip()[:14]} | K:{p_st_lbl}{b_tag} | {retail_vnd // 1000}k{custom_tag}"
        rows.append([Button.inline(lbl, f"adm:editp:{pid}".encode())])

    nav = []
    if page > 0:
        nav.append(Button.inline("⬅️ Trang trước", f"adm:plist:{page - 1}".encode()))
    if end < total:
        nav.append(Button.inline("Trang sau ➡️", f"adm:plist:{page + 1}".encode()))
    if nav:
        rows.append(nav)
    rows.append([
        Button.inline("« Về Thư mục Kho Hàng", b"adm:dir:catalog"),
        Button.inline("⚙️ Bảng Admin", b"adm:home"),
    ])

    await send_or_edit(
        event,
        f"🏷️ **QUẢN LÝ {total} SẢN PHẨM HỢP NHẤT (Trang {page + 1}/{max(1, (total - 1) // per_page + 1)})**\n"
        "• `[PS+DH]` = SP chung (Ưu tiên `@ProdSellerBot` + Tự động bù `@DanteHubBot`)\n"
        "• `[DH]` = SP độc quyền từ `@DanteHubBot` | `[PS]` = SP từ `@ProdSellerBot`\n"
        "• 📌 = Giá cố định riêng | 🙈 = Đang ẩn\n"
        "👉 Bấm vào sản phẩm để **Nạp Key Dự Phòng / Đấu API Bot khác** hoặc chỉnh giá:",
        buttons=rows,
    )


async def render_admin_local_keys_inventory(event: Any) -> None:
    """Hiển thị toàn bộ Key/Link đang nằm trong Kho Dự Phòng Nội Bộ (local_stock) bao gồm cả Link Thu Hồi."""
    backup_map = db.get_all_backup_sources()
    products = await ps_client.sync_products(force=False)
    prod_names = {str(p["id"]): str(p["name"]) for p in products}

    local_entries: list[tuple[str, str, dict[str, Any]]] = []
    for pid, src_list in backup_map.items():
        for s in src_list:
            if s.get("source_type") == "local_stock":
                keys_list = s.get("stock_keys_list") or []
                if keys_list:
                    p_name = prod_names.get(pid, f"SP {pid}")
                    local_entries.append((pid, p_name, s))

    rows: list[list[Any]] = []
    if not local_entries:
        text = (
            "🔑 **KHO KEY NỘI BỘ & LINK THU HỒI (`local_stock`)**\n\n"
            "📭 Hiện tại không có Key/Link nội bộ nào đang tồn trong kho."
        )
    else:
        lines = [
            "🔑 **DANH SÁCH KEY NỘI BỘ & LINK THU HỒI ĐANG LƯU TRONG KHO**\n"
            "⚡ *Các Key/Link này được ưu tiên xuất tự động trước tiên khi khách mua hoặc mở khóa đơn (không tốn thêm USDT bên ProdSeller):*\n"
        ]
        for pid, p_name, s in local_entries:
            sid = int(s["id"])
            is_act = int(s.get("active", 0) or 0) == 1
            st_icon = "🟢 Đang BẬT" if is_act else "🔴 Đang TẮT"
            keys_list = s.get("stock_keys_list") or []
            cost_vnd = int(s.get("cost_vnd", 0) or 0)
            lines.append(
                f"🛍️ **{p_name}** (`{pid}`)\n"
                f"📦 Nguồn `#{sid}`: **{s['source_name']}** [{st_icon}] — Vốn: `{cost_vnd:,}đ` | Tồn: **{len(keys_list)}**"
            )
            for idx_k, k_val in enumerate(keys_list[:10], 1):
                lines.append(f"  {idx_k}. `{k_val}`")
            lines.append("")
            rows.append([
                Button.inline(f"🏷️ Mở SP: {p_name[:18]}", f"adm:editp:{pid}".encode(), style="primary"),
                Button.inline(
                    f"{'🔴 Tắt' if is_act else '🟢 Bật'} #{sid}",
                    f"adm:bsrc_tog:{sid}:{pid}".encode(),
                ),
                Button.inline(f"🗑️ Xóa #{sid}", f"adm:bsrc_del:{sid}:{pid}".encode(), style="danger"),
            ])
        text = "\n".join(lines)

    rows.append([
        Button.inline("📁 Kho Hàng & Nguồn Cung", b"adm:dir:catalog"),
        Button.inline("« Về Bảng Admin", b"adm:home"),
    ])
    await send_or_edit(event, text, buttons=rows)


async def render_admin_edit_product(event: Any, product_id: str) -> None:
    p = await ps_client.get_product_by_id(product_id, refresh=False)
    if not p:
        return
    is_dh_primary = p.get("provider") == "dantehub"
    ov = db.get_product_override(product_id) or {}
    backup_map = db.get_all_backup_sources()
    eff_st, _, p_st, b_st = db.get_effective_product_stock(p, backup_map)
    cost_usd = float(p["price"])
    cost_vnd = db.compute_wholesale_vnd(cost_usd)
    primary_base_vnd = db.compute_primary_base_price(product_id, cost_usd)
    alloc = db.resolve_supply_allocation(
        product_id,
        cost_usd,
        qty=1,
        primary_stock=p_st,
        backup_map=backup_map,
    )
    active_cost_vnd = int(alloc["unit_cost_vnd"])
    retail_vnd = int(alloc["base_unit_vnd"])
    profit_vnd = retail_vnd - active_cost_vnd
    margin_pct = (profit_vnd / active_cost_vnd * 100.0) if active_cost_vnd > 0 else 200.0
    min_profit_pct = float(db.get_setting("min_profit_percent", "150.0") or 150.0)
    is_hidden = bool(ov.get("hidden"))
    has_custom = ov.get("custom_price") is not None

    b_sources = backup_map.get(product_id, [])
    if not b_sources:
        b_lines = ["  • *(Chưa có nguồn dự phòng — Bấm nút bên dưới để thêm từ Bot khác)*"]
    else:
        b_lines = []
        for s in b_sources:
            sid = int(s["id"])
            s_act = "🟢" if int(s.get("active", 0) or 0) == 1 else "🔴"
            s_type = "Kho Key" if s.get("source_type") == "local_stock" else "API"
            s_cost = int(s.get("cost_vnd", 0) or 0)
            s_st = int(s.get("available_stock", 0) or 0)
            s_stab_price = db.compute_stabilized_unit_price(primary_base_vnd, s_cost, min_profit_pct)
            s_prof_pct = ((s_stab_price - s_cost) / s_cost * 100.0) if s_cost > 0 else 200.0
            b_lines.append(
                f"  {s_act} `#{sid}` **{s['source_name']}** ({s_type}) — Vốn: `{s_cost:,}đ` | Kho: **{s_st}** "
                f"➡️ Giá bán khi bù: **`{s_stab_price:,}đ`** *(Lãi `+{s_prof_pct:.0f}%`)*"
            )
            if s.get("source_type") == "local_stock":
                for idx_k, k_val in enumerate(s.get("stock_keys_list") or [], 1):
                    b_lines.append(f"     🔑 Key/Link {idx_k}: `{k_val}`")
    b_block = "\n".join(b_lines)
    p_st_val = 1 if p_st is None else int(p_st)
    k1_name = "@DanteHubBot (Độc quyền)" if is_dh_primary else "@ProdSellerBot"
    active_src_note = (
        f"🟢 Đang lấy từ **Kho chính {k1_name}**"
        if p_st_val > 0
        else ("🟡 Kho chính hết hàng ➡️ **Đang tự động lấy từ Nguồn Dự Phòng!**" if b_st > 0 else "🔴 Cả kho chính & dự phòng đều đang hết hàng")
    )
    eff_st_lbl = "∞" if eff_st is None else str(eff_st)
    p_st_lbl = "∞" if p_st is None else str(p_st)

    text = (
        f"🏷️ **QUẢN LÝ SẢN PHẨM & ĐA NGUỒN HÀNG**\n\n"
        f"🛍️ Tên: **{p['name']}**\n"
        f"🆔 ID: `{product_id}`" + (f" *(UUID: `{p.get('dante_uuid')}`)*\n" if is_dh_primary else "\n") +
        f"📡 Trạng thái cấp hàng: {active_src_note}\n"
        f"📦 Tồn kho: **Tổng `{eff_st_lbl}`** (Kho chính K1: `{p_st_lbl}` | Dự phòng: `{b_st}`)\n"
        f"📉 Giá vốn K1 ({k1_name}): **{cost_vnd:,}đ** (`${cost_usd:.2f}`)\n"
        f"🎯 Giá chuẩn K1 (+{db.get_setting('markup_percent', '200')}%): **{primary_base_vnd:,}đ**\n"
        f"💰 **Giá bán thực tế hiện tại (Bình ổn): `{retail_vnd:,}đ`** "
        f"({'Giá cố định riêng 📌' if has_custom else f'Cam kết lãi >= +{min_profit_pct:g}%'})\n"
        f"💵 Lợi nhuận trên nguồn đang chạy: **+{profit_vnd:,}đ (+{margin_pct:.0f}%)**\n"
        f"👁 Hiển thị: **{'Đang ẨN 🙈' if is_hidden else 'Đang HIỆN ✅'}**\n\n"
        f"📦 **DANH SÁCH NGUỒN HÀNG DỰ PHÒNG ({len(b_sources)}):**\n"
        f"{b_block}"
    )

    rows: list[list[Any]] = [
        [
            Button.inline("⚡ Gắn Nhanh Từ @DanteHubBot (1 Chạm)", f"adm:bsrc_dante:{product_id}".encode(), style="success"),
        ],
        [
            Button.inline("➕ Nạp Key Dự Phòng (Thủ công)", f"adm:bsrc_add:{product_id}".encode()),
            Button.inline("🔌 Đấu API Khác", f"adm:bsrc_api:{product_id}".encode(), style="primary"),
        ],
    ]
    for s in b_sources[:6]:
        sid = int(s["id"])
        is_act = int(s.get("active", 0) or 0) == 1
        rows.append([
            Button.inline(
                f"{'🔴 Tắt' if is_act else '🟢 Bật'} #{sid} {s['source_name'][:14]} ({s.get('available_stock', 0)})",
                f"adm:bsrc_tog:{sid}:{product_id}".encode(),
            ),
            Button.inline(
                f"🗑️ Xóa #{sid}",
                f"adm:bsrc_del:{sid}:{product_id}".encode(),
                style="danger",
            ),
        ])
    rows.extend([
        [Button.inline("✏️ Đặt giá bán riêng (VNĐ)", f"adm:setp:{product_id}".encode())],
        [
            Button.inline("🔄 Dùng lại công thức % chung", f"adm:resetp:{product_id}".encode()),
            Button.inline("👁 Ẩn / Hiện SP này", f"adm:hidep:{product_id}".encode()),
        ],
        [Button.inline("« Quay lại danh sách SP", b"adm:plist:0")],
    ])
    await send_or_edit(event, text, buttons=rows)


async def render_admin_dante_picker(event: Any, product_id: str) -> None:
    """Hiển thị danh sách sản phẩm gợi ý từ @DanteHubBot để Admin gắn làm nguồn dự phòng 1 chạm."""
    p = await ps_client.get_product_by_id(product_id, refresh=False)
    if not p:
        return
    d_key = (db.get_setting("dante_api_key", "") or os.getenv("DANTE_API_KEY", "")).strip()
    d_url = (db.get_setting("dante_base_url", DANTE_BASE_URL) or DANTE_BASE_URL).strip()
    if not d_key:
        await send_or_edit(
            event,
            "⚠️ Chưa cài đặt API Key `@DanteHubBot`. Vui lòng vào `/admin` -> **🔑 Key @DanteHubBot** để nhập Key trước!",
            buttons=[[Button.inline("« Quay lại", f"adm:editp:{product_id}".encode())]],
        )
        return

    matches = await ps_client.search_dantehub_products(p["name"], d_url, d_key, limit=8)
    rate = float(db.get_setting("vnd_rate", "25500") or 25500.0)
    min_prof = float(db.get_setting("min_profit_percent", "150.0") or 150.0)
    p_base_vnd = db.compute_primary_base_price(product_id, float(p["price"]))

    lines = [
        f"⚡ **GẮN NGUỒN @DanteHubBot (1 CHẠM) — `{p['name']}`**\n",
        f"🎯 Giá chuẩn K1 (+{db.get_setting('markup_percent', '200')}%): **`{p_base_vnd:,}đ`** | Sàn lãi: **`>= +{min_prof:g}%`**\n",
        "👇 **Chọn sản phẩm tương ứng trên `@DanteHubBot` bên dưới để đấu nối tự động:**",
    ]
    rows: list[list[Any]] = []
    for m in matches:
        dh_id = str(m["id"])
        dh_short = dh_id.replace("-", "")[:16]
        title = str(m.get("title") or m.get("name") or dh_id)
        usd_val = float(m.get("price", 0) or 0)
        cost_vnd = max(500, int(round(usd_val * rate)))
        stab_vnd = db.compute_stabilized_unit_price(p_base_vnd, cost_vnd, min_prof)
        prof_pct = ((stab_vnd - cost_vnd) / cost_vnd * 100.0) if cost_vnd > 0 else 200.0
        in_st = bool(m.get("in_stock", False))
        st_icon = "🟢" if in_st else "🔴"
        lines.append(
            f"• {st_icon} **{title}**\n"
            f"  Vốn Dante: **`{cost_vnd:,}đ`** (`${usd_val:g}`) ➡️ Giá bán bình ổn: **`{stab_vnd:,}đ`** *(Lãi `+{prof_pct:.0f}%`)*"
        )
        rows.append([
            Button.inline(
                f"{st_icon} Gắn: {title[:24]} (Vốn {cost_vnd // 1000}k -> Bán {stab_vnd // 1000}k)",
                f"adm:bsrc_dpick:{product_id}:{dh_short}".encode(),
                style="success" if in_st else None,
            )
        ])
    rows.append([Button.inline("« Quay lại sản phẩm", f"adm:editp:{product_id}".encode())])
    await send_or_edit(event, "\n".join(lines), buttons=rows)


# ==================== BACKGROUND TASK FOR ACTIVATION ORDERS ====================
async def poll_pending_activations_loop(client: TelegramClient) -> None:
    while True:
        await asyncio.sleep(60)
        pending = db.get_pending_activation_orders()
        for o in pending:
            try:
                ps_oid = str(o.get("prodseller_order_id") or "")
                if ps_oid.startswith("DANTE_"):
                    remote_oid = ps_oid[6:]
                    b_url = db.get_setting("dante_base_url", DANTE_BASE_URL)
                    b_key = db.get_setting("dante_api_key", "") or ps_client.dante_api_key
                    st = await ps_client.get_external_api_order_status(str(b_url), str(b_key), remote_oid)
                elif ps_oid.startswith("EXT_"):
                    parts = ps_oid.split("_", 2)
                    if len(parts) == 3:
                        sid = int(parts[1])
                        remote_oid = parts[2]
                        src = db.get_backup_source_by_id(sid)
                        b_url = (src.get("api_base_url") if src else "") or db.get_setting("dante_base_url", DANTE_BASE_URL)
                        b_key = (src.get("api_key") if src else "") or db.get_setting("dante_api_key", "")
                        st = await ps_client.get_external_api_order_status(str(b_url), str(b_key), remote_oid)
                    else:
                        continue
                else:
                    st = await ps_client.get_order_status(ps_oid)

                if st.get("status") == "delivered":
                    keys: list[str] = []
                    if st.get("deliveredKeys"):
                        keys = [str(k) for k in st["deliveredKeys"]]
                    elif st.get("deliveredKey"):
                        keys = [str(st["deliveredKey"])]
                    db.mark_order_delivered(o["id"], keys)
                    key_text = "\n".join(keys) if keys else "Đã kích hoạt hoàn tất trên email của bạn!"
                    await client.send_message(
                        o["user_id"],
                        (
                            f"🎉 **Đơn hàng #{o['id']} đã hoàn tất!**\n\n"
                            f"🛍️ Sản phẩm: **{o['product_name']}**\n"
                            f"🔑 Tài khoản / Key:\n`{key_text}`"
                        ),
                    )
                elif st.get("status") == "cancelled":
                    refund_vnd = vnd_int(o.get("retail_price", 0))
                    db.mark_order_delivered(o["id"], ["[CANCELLED_REFUNDED]"])
                    if refund_vnd > 0:
                        db.adjust_balance(int(o["user_id"]), refund_vnd)
                        await client.send_message(
                            o["user_id"],
                            f"⚠️ Đơn hàng `#{o['id']}` (**{o['product_name']}**) bị hủy từ nhà cung cấp. Hệ thống đã hoàn trả **+{refund_vnd:,}đ** vào ví của bạn!",
                        )
            except Exception as exc:
                logger.debug("Chưa lấy được trạng thái đơn %s: %s", o["prodseller_order_id"], exc)


# ==================== CLOUD HTTP SERVER (/health, /api-docs, /v1/* PUBLIC API) ====================
_BOT_CLIENT_REF: TelegramClient | None = None


async def _handle_http_health(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    await handle_http_request(
        reader,
        writer,
        db=db,
        ps_client=ps_client,
        bot_client=_BOT_CLIENT_REF,
        bot_username=BOT_USERNAME_CACHE,
        admin_ids=ADMIN_IDS,
    )


async def start_health_server() -> None:
    port_str = os.getenv("PORT", "").strip()
    if not port_str:
        return
    try:
        port = int(port_str)
        server = await asyncio.start_server(_handle_http_health, "0.0.0.0", port)
        logger.info("🌐 Cổng HTTP & Public Reseller API (/v1, /api-docs, /health) đã mở tại 0.0.0.0:%s", port)
        asyncio.create_task(server.serve_forever())
    except Exception as exc:
        logger.warning("Không thể mở cổng HTTP %s: %s", port_str, exc)


async def keep_alive_ping_loop() -> None:
    """Tự động ping RENDER_EXTERNAL_URL mỗi 10 phút nếu chạy trên Render Web Service."""
    ext_url = os.getenv("RENDER_EXTERNAL_URL", "").strip().rstrip("/")
    if not ext_url:
        return
    import httpx

    ping_url = f"{ext_url}/health"
    logger.info("🔄 Đã bật chế độ tự động giữ thức (Keep-Alive) cho: %s", ping_url)
    while True:
        await asyncio.sleep(600)
        try:
            async with httpx.AsyncClient(timeout=10.0) as hc:
                await hc.get(ping_url)
        except Exception:
            pass


# ==================== MAIN RUNNER ====================
async def run_bot() -> None:
    global BOT_USERNAME_CACHE, _BOT_CLIENT_REF
    await start_health_server()
    api_id = int(os.getenv("TELEGRAM_API_ID", "0"))
    api_hash = os.getenv("TELEGRAM_API_HASH", "").strip()
    bot_token = os.getenv("RESELLER_BOT_TOKEN", "").strip()
    if not bot_token or ":" not in bot_token:
        raise RuntimeError("Thiếu RESELLER_BOT_TOKEN hợp lệ trong file .env!")

    client = TelegramClient(str(ROOT / "reseller-bot-session"), api_id, api_hash)
    await client.start(bot_token=bot_token)
    _BOT_CLIENT_REF = client
    me = await client.get_me()
    BOT_USERNAME_CACHE = me.username or "KingToolShop_bot"
    logger.info("🚀 Bot Reseller @%s (ID: %s) đang hoạt động (Chế độ tiền tệ: VNĐ)!", BOT_USERNAME_CACHE, me.id)

    asyncio.create_task(ps_client.sync_products(force=True))
    asyncio.create_task(poll_products_sync_loop(client))
    asyncio.create_task(poll_pending_activations_loop(client))
    asyncio.create_task(poll_night_sepay_deposits_loop(client))
    asyncio.create_task(keep_alive_ping_loop())

    @client.on(events.NewMessage(pattern=r"^/start(?:\s+(.*))?$"))
    async def handle_start(event: events.NewMessage.Event) -> None:
        if not event.is_private:
            await event.reply(
                f"👋 Chào bạn! Vui lòng bấm vào bên dưới để mở Bot mua hàng tự động 24/7:",
                buttons=[[Button.url("🛒 Mở Bot Mua Hàng Tự Động", f"https://t.me/{BOT_USERNAME_CACHE}")]],
            )
            return
        uid = event.sender_id
        USER_AWAITING.pop(uid, None)
        arg = (event.pattern_match.group(1) or "").strip()
        ref_id: int | None = None
        buy_pid: str | None = None
        if arg.startswith("REF_"):
            try:
                cand = int(arg.replace("REF_", ""))
                if cand != uid:
                    ref_id = cand
            except ValueError:
                pass
        elif arg.startswith("BUY_"):
            buy_pid = arg[4:].strip()
        sender = await event.get_sender()
        real_u, full_name = extract_sender_identity(sender, uid)
        u = db.get_or_create_user(uid, username=real_u, referred_by=ref_id, full_name=full_name)
        lang = u.get("language", "vi")
        admin_user = db.get_setting("support_admin", "KingToolShopSupport").lstrip("@")
        channel_user = db.get_setting("support_channel", "KingToolShopOfficial").lstrip("@")

        if buy_pid:
            await render_product_detail(event, buy_pid, qty=1)
            return

        if arg.upper() == "GIFT":
            await render_newbie_gift_funnel(event, force_new=True)
            return

        all_joined, joined_ch, joined_grp = await check_user_joined_community(client, uid, force_refresh=False)
        welcome_btns = None
        if not all_joined:
            welcome_btns = [
                [Button.url(t(lang, "force_join_ch_btn", channel=channel_user, badge="✅" if joined_ch else "👉"), f"https://t.me/{channel_user}")],
                [Button.url(t(lang, "force_join_grp_btn", group=admin_user, badge="✅" if joined_grp else "👉"), f"https://t.me/{admin_user}")],
            ]
        await event.respond(
            t(lang, "welcome_banner", admin=admin_user, channel=channel_user),
            buttons=welcome_btns,
        )
        await event.respond(
            t(lang, "main_menu_title", balance=vnd_int(u["balance"]), points=u["points"]),
            buttons=main_menu_buttons(lang, uid),
        )

    @client.on(events.NewMessage(pattern=r"^/admin$"))
    async def handle_admin(event: events.NewMessage.Event) -> None:
        if event.is_private and is_admin(event.sender_id):
            await render_admin_home(event, force_new=True)

    @client.on(events.NewMessage(pattern=r"^/addbalance(?:\s+(\d+)\s+([+-]?\d+(?:\.\d+)?))?$"))
    async def handle_addbalance(event: events.NewMessage.Event) -> None:
        if not event.is_private or not is_admin(event.sender_id):
            return
        tid_s = event.pattern_match.group(1)
        amt_s = event.pattern_match.group(2)
        if not tid_s or not amt_s:
            await event.respond("Cách dùng: `/addbalance <telegram_id> <số_tiền_vnđ>`\nVí dụ: `/addbalance 8110826820 50000`")
            return
        target_id = int(tid_s)
        amount_vnd = int(round(float(amt_s)))
        db.get_or_create_user(target_id)
        new_bal = db.adjust_balance(target_id, amount_vnd)
        await event.respond(f"✅ Đã cập nhật **{amount_vnd:+,}đ** cho user `{target_id}`.\n💵 Số dư mới: **{new_bal:,}đ**")
        try:
            await client.send_message(
                target_id,
                f"💰 Số dư ví của bạn vừa được cập nhật **{amount_vnd:+,}đ**.\n💵 Số dư hiện tại: **{new_bal:,}đ**",
            )
        except Exception:
            pass

    @client.on(events.NewMessage(pattern=r"^/broadcast(?:\s+([\s\S]+))?$"))
    async def handle_broadcast_cmd(event: events.NewMessage.Event) -> None:
        if not event.is_private or not is_admin(event.sender_id):
            return
        msg_body = (event.pattern_match.group(1) or "").strip()
        if not msg_body:
            await event.respond("Cách dùng: `/broadcast <Nội dung thông báo gửi toàn bộ khách>`")
            return
        user_ids = db.get_all_user_ids()
        status_m = await event.respond(f"⏳ Đang gửi thông báo tới **{len(user_ids)}** khách hàng...")
        sent_ok = 0
        for tid in user_ids:
            try:
                await client.send_message(tid, f"📣 **THÔNG BÁO TỪ SHOP**\n\n{msg_body}")
                sent_ok += 1
                await asyncio.sleep(0.05)
            except Exception:
                pass
        await status_m.edit(f"✅ Đã gửi thông báo thành công tới **{sent_ok}/{len(user_ids)}** khách hàng!")

    @client.on(events.CallbackQuery)
    async def handle_callback(event: events.CallbackQuery.Event) -> None:
        data = event.data.decode("utf-8", errors="ignore")
        u, lang = await get_user_info(event)
        uid = u["telegram_id"]

        if data == "noop":
            await event.answer()
            return

        if data.startswith("fjoin:chk:"):
            resume_cb = data.split(":", 2)[2] or "menu:products"
            all_ok, joined_ch, joined_grp = await check_user_joined_community(client, uid, force_refresh=True)
            channel_user = db.get_setting("support_channel", "KingToolShopOfficial").strip().lstrip("@")
            group_user = db.get_setting("support_admin", "KingToolShopSupport").strip().lstrip("@")
            if not all_ok:
                if not joined_ch and not joined_grp:
                    msg = t(lang, "force_join_missing_both", channel=channel_user, group=group_user)
                elif not joined_ch:
                    msg = t(lang, "force_join_missing_channel", channel=channel_user)
                else:
                    msg = t(lang, "force_join_missing_group", group=group_user)
                await event.answer(msg, alert=True)
                await render_force_join_gate(
                    event,
                    joined_ch=joined_ch,
                    joined_grp=joined_grp,
                    resume_cb=resume_cb,
                )
                return

            # Tự động tặng luôn Quà Tân Thủ (+5 điểm + tự áp mã WELCOME15) nếu khách chưa nhận
            if str(db.get_setting("newbie_gift_enabled", "1") or "0").strip() == "1" and int(u.get("gift_claimed", 0) or 0) == 0:
                gift_pts = max(1, int(float(db.get_setting("newbie_gift_points", "5") or 5)))
                gift_code = (db.get_setting("newbie_gift_voucher", "WELCOME15") or "WELCOME15").strip().upper()
                claimed_ok, _ = db.claim_newbie_gift(uid, bonus_points=gift_pts)
                if claimed_ok:
                    USER_ACTIVE_VOUCHER[uid] = gift_code

            await event.answer(t(lang, "force_join_ok_toast"), alert=False)
            if resume_cb.startswith("buy:"):
                parts = resume_cb.split(":")
                if len(parts) >= 3:
                    await execute_purchase(client, event, parts[1], int(parts[2]))
                    return
            if resume_cb.startswith("prd:"):
                await render_product_detail(event, resume_cb.split(":", 1)[1], qty=1)
                return
            if resume_cb == "menu:deposit":
                await render_deposit_menu(event)
                return
            await render_products_menu(event)
            return

        if data == "usr:reply_adm":
            await event.answer()
            USER_AWAITING[uid] = {"type": "user_reply_admin"}
            await event.respond(
                "💬 **NHẮN TIN TRỰC TIẾP TỚI ADMIN SHOP**\n\n"
                "Hãy nhập nội dung tin nhắn hoặc câu hỏi của bạn vào đây, hệ thống sẽ chuyển thẳng tới Admin ngay lập tức (hoặc gõ `/cancel` để hủy):",
                buttons=[[Button.inline(t(lang, "btn_back"), b"menu:home")]],
            )
            return

        if data == "menu:gift":
            await event.answer()
            await render_newbie_gift_funnel(event)
            return

        if data == "gift:claim":
            await handle_claim_newbie_gift(client, event)
            return

        if data == "menu:home":
            USER_AWAITING.pop(uid, None)
            await event.answer()
            await send_or_edit(
                event,
                t(lang, "main_menu_title", balance=vnd_int(u["balance"]), points=u["points"]),
                buttons=main_menu_buttons(lang, uid),
            )
            return

        if data == "menu:products":
            await event.answer()
            await render_products_menu(event)
            return

        if data.startswith("grp:"):
            await event.answer()
            rest = data[4:]
            if ":" in rest:
                g_name, p_str = rest.rsplit(":", 1)
                page_idx = int(p_str) if p_str.isdigit() else 0
            else:
                g_name, page_idx = rest, 0
            await render_products_menu(event, group_filter=g_name, page=page_idx)
            return

        if data.startswith("prd:"):
            await event.answer()
            await render_product_detail(event, data.split(":", 1)[1], qty=1)
            return

        if data.startswith("qty:"):
            await event.answer()
            _, pid, q_str = data.split(":")
            await render_product_detail(event, pid, qty=int(q_str))
            return

        if data.startswith("qtyc:"):
            await event.answer()
            pid = data.split(":", 1)[1]
            if not await ensure_user_joined_community(client, event, uid, lang, resume_cb=f"prd:{pid}"):
                return
            p = await ps_client.get_product_by_id(pid, refresh=False)
            if not p:
                return
            eff_st, _, _, _ = db.get_effective_product_stock(p)
            max_q = int(eff_st) if isinstance(eff_st, int) and eff_st > 0 else 100
            USER_AWAITING[uid] = {
                "type": "custom_qty",
                "product_id": pid,
                "max_qty": max_q,
                "name": p["name"],
            }
            await send_or_edit(
                event,
                t(lang, "custom_qty_prompt", name=p["name"], max_qty=max_q),
                buttons=[[Button.inline(t(lang, "btn_back"), f"prd:{pid}".encode())]],
            )
            return

        if data.startswith("vch:ask:"):
            await event.answer()
            _, _, pid, q_str = data.split(":")
            qty_val = int(q_str)
            if not await ensure_user_joined_community(client, event, uid, lang, resume_cb=f"prd:{pid}"):
                return
            p = await ps_client.get_product_by_id(pid, refresh=False)
            p_name = p["name"] if p else pid
            USER_AWAITING[uid] = {
                "type": "apply_voucher",
                "product_id": pid,
                "qty": qty_val,
                "name": p_name,
            }
            await send_or_edit(
                event,
                t(lang, "voucher_prompt", name=p_name),
                buttons=[[Button.inline(t(lang, "btn_back"), f"qty:{pid}:{qty_val}".encode())]],
            )
            return

        if data.startswith("vch:rm:"):
            _, _, pid, q_str = data.split(":")
            USER_ACTIVE_VOUCHER.pop(uid, None)
            await event.answer(t(lang, "voucher_removed_toast"))
            await render_product_detail(event, pid, qty=int(q_str))
            return

        if data.startswith("buy:"):
            await event.answer()
            _, pid, q_str = data.split(":")
            await execute_purchase(client, event, pid, int(q_str))
            return

        if data == "menu:balance":
            await event.answer()
            pts = int(u.get("points", 0) or 0)
            point_rate = max(1, int(float(db.get_setting("point_value_vnd", "100") or 100)))
            tier = u.get("tier", "bronze")
            disc_pct = TIER_DISCOUNTS.get(tier.lower(), 0)
            rows = [
                [Button.inline(t(lang, "deposit_now_btn"), b"menu:deposit", style="success")],
            ]
            if pts > 0:
                rows.append([
                    Button.inline(
                        t(lang, "redeem_points_btn", points=pts, bonus=pts * point_rate),
                        b"prof:redeem",
                        style="primary",
                    )
                ])
            rows.append([Button.inline(t(lang, "btn_back"), b"menu:home")])
            await send_or_edit(
                event,
                t(
                    lang,
                    "balance_title",
                    balance=vnd_int(u["balance"]),
                    points=pts,
                    point_rate=point_rate,
                    tier=tier.upper(),
                    disc_pct=disc_pct,
                ),
                buttons=rows,
            )
            return

        if data == "prof:redeem":
            ok, pts, bonus_vnd, new_bal = db.redeem_user_points(uid, min_points=10)
            if not ok:
                await event.answer(t(lang, "redeem_points_min", min_pts=10, points=pts), alert=True)
                return
            await event.answer("✅", alert=False)
            await send_or_edit(
                event,
                t(lang, "redeem_points_success", pts=pts, bonus=bonus_vnd, new_bal=new_bal),
                buttons=[[Button.inline(t(lang, "btn_back"), b"menu:balance")]],
            )
            return

        if data in ("menu:deposit", "menu:deposit_qr"):
            await event.answer()
            if data == "menu:deposit_qr":
                try:
                    await event.delete()
                except Exception:
                    pass
            if not await ensure_user_joined_community(client, event, uid, lang, resume_cb="menu:deposit"):
                return
            await render_deposit_menu(event)
            return

        if data.startswith("dep:method:"):
            await event.answer()
            if not await ensure_user_joined_community(client, event, uid, lang, resume_cb="menu:deposit"):
                return
            await render_deposit_amounts(event)
            return

        if data.startswith("dep:create:"):
            await event.answer()
            if not await ensure_user_joined_community(client, event, uid, lang, resume_cb="menu:deposit"):
                return
            _, _, _, amt_str = data.split(":")
            await create_and_show_deposit(client, event, int(float(amt_str)))
            return

        if data.startswith("dep:custom:"):
            await event.answer()
            if not await ensure_user_joined_community(client, event, uid, lang, resume_cb="menu:deposit"):
                return
            USER_AWAITING[uid] = {"type": "custom_deposit"}
            await send_or_edit(
                event,
                t(lang, "custom_deposit_prompt"),
                buttons=[[Button.inline(t(lang, "btn_back"), b"menu:deposit")]],
            )
            return

        if data.startswith("dep:Paid:"):
            dep_id = int(data.split(":")[2])
            dep = db.get_deposit(dep_id)
            if not dep:
                await event.answer("❌ Không tìm thấy đơn nạp.", alert=True)
                return
            if dep["status"] != "pending":
                await event.answer("✅ Đơn nạp này đã được xử lý!", alert=True)
                return

            # Nếu đang trong khung giờ ban đêm (23h00 -> 06h00 sáng) và còn hạn mức SePay Free:
            if await try_night_sepay_auto_approve(client, dep):
                await event.answer("🌙 Hệ thống SePay đã xác nhận giao dịch và tự động cộng số dư cho bạn!", alert=True)
                return

            # Chống bấm spam nút báo Admin liên tục
            now_ts = time.time()
            last_notif = DEPOSIT_NOTIFIED_AT.get(dep_id, 0.0)
            if now_ts - last_notif < 120.0:
                await event.answer(t(lang, "deposit_already_notified"), alert=True)
                return
            DEPOSIT_NOTIFIED_AT[dep_id] = now_ts

            in_night = db.is_in_night_auto_window()
            used_sp, limit_sp, can_sp = db.get_sepay_quota_status()
            if in_night and can_sp:
                await event.answer(
                    "🌙 Đã ghi nhận! Hệ thống tự động ban đêm (23h-06h) đang kiểm tra giao dịch ngân hàng (tự động cộng tiền sau 30 giây), đồng thời đã báo Admin!",
                    alert=True,
                )
            else:
                await event.answer("✅ Đã gửi yêu cầu duyệt nạp tới Admin! Vui lòng chờ giây lát.", alert=True)

            # Đổi nhãn nút trên tin nhắn của khách sang trạng thái đang chờ duyệt
            try:
                wait_rows = [
                    [Button.inline(t(lang, "vietqr_notified_btn"), f"dep:Paid:{dep_id}".encode())],
                    [Button.inline(t(lang, "btn_back"), b"menu:deposit_qr")],
                ]
                await event.edit(buttons=wait_rows)
            except Exception:
                pass

            amt_vnd = vnd_int(dep["amount_vnd"])
            bonus_vnd, bonus_pct = db.compute_deposit_bonus(amt_vnd)
            bonus_line = f" (🎁 KM +{bonus_pct:g}% = `+{bonus_vnd:,}đ`)" if bonus_vnd > 0 else ""
            mode_note = (
                f"🌙 *Đang trong khung 23h-06h (SePay {used_sp}/{limit_sp}): Bot đang tự động quét ngầm, hoặc bạn có thể bấm nút duyệt tay bên dưới:*"
                if (in_night and can_sp)
                else f"☀️ *Chế độ Duyệt Bằng Tay (SePay đã dùng {used_sp}/{limit_sp} lượt tháng này) — Kiểm tra ngân hàng và bấm nút bên dưới:*"
            )
            dep_uid = int(dep["user_id"])
            dep_u = db.get_or_create_user(dep_uid)
            for adm_id in ADMIN_IDS:
                try:
                    adm_rows = [
                        [
                            Button.inline(f"✅ Duyệt +{amt_vnd + bonus_vnd:,}đ", f"adm:dep_ok:{dep_id}".encode(), style="success"),
                            Button.inline("❌ Từ chối", f"adm:dep_no:{dep_id}".encode(), style="danger"),
                        ],
                        build_admin_user_buttons(dep_uid),
                    ]
                    memo_display = dep.get("memo") or f"NAP{dep_id}"
                    await client.send_message(
                        adm_id,
                        (
                            f"🔔 **YÊU CẦU DUYỆT NẠP TIỀN #{dep_id}**\n\n"
                            f"👤 Khách hàng: {format_admin_user_line(dep_uid, dep_u)}\n"
                            f"🏦 Phương thức: **VIETQR**\n"
                            f"💵 Số tiền nạp: **{amt_vnd:,}đ**{bonus_line}\n"
                            f"📝 Nội dung CK: `{memo_display}`\n\n"
                            f"{mode_note}"
                        ),
                        buttons=adm_rows,
                    )
                except Exception as exc:
                    logger.error("Lỗi gửi thông báo nạp cho Admin: %s", exc)
            return

        if data == "menu:methods":
            await event.answer()
            raw_methods = db.get_setting("methods_text", "").strip()
            if not raw_methods or raw_methods == "📭 No methods available at the moment.":
                methods_txt = t(lang, "methods_default")
            else:
                methods_txt = raw_methods
            rows = [[Button.inline(t(lang, "btn_back"), b"menu:home")]]
            if is_admin(uid):
                rows.insert(0, [Button.inline("✏️ Sửa nội dung Hướng dẫn (Admin)", b"adm:set:methods_text")])
            await send_or_edit(event, methods_txt, buttons=rows)
            return

        if data == "menu:profile":
            await event.answer()
            pts = int(u.get("points", 0) or 0)
            point_rate = max(1, int(float(db.get_setting("point_value_vnd", "100") or 100)))
            tier = u.get("tier", "bronze")
            disc_pct = TIER_DISCOUNTS.get(tier.lower(), 0)
            safe_name, _, uname_disp = get_user_display_parts(uid, u)
            rows = [
                [
                    Button.inline(t(lang, "my_orders_btn"), b"prof:orders"),
                    Button.inline(t(lang, "referral_btn"), b"prof:ref"),
                ],
            ]
            if pts > 0:
                rows.append([
                    Button.inline(
                        t(lang, "redeem_points_btn", points=pts, bonus=pts * point_rate),
                        b"prof:redeem",
                        style="primary",
                    )
                ])
            rows.append([Button.inline(t(lang, "btn_back"), b"menu:home")])
            await send_or_edit(
                event,
                t(
                    lang,
                    "profile_title",
                    uid=uid,
                    full_name=safe_name,
                    username=uname_disp,
                    tier=tier.upper(),
                    disc_pct=disc_pct,
                    balance=vnd_int(u["balance"]),
                    points=pts,
                    orders=u["orders_count"],
                    spent=vnd_int(u["total_spent"]),
                    joined=u["joined_at"][:10],
                ),
                buttons=rows,
            )
            return

        if data == "prof:orders":
            await event.answer()
            USER_AWAITING.pop(uid, None)
            orders = db.get_user_orders(uid, limit=8)
            rows: list[list[Any]] = []
            if not orders:
                txt = t(lang, "orders_empty")
            else:
                lines = [t(lang, "orders_history_title")]
                warr_btns: list[Any] = []
                for o in orders:
                    clean_keys = format_order_keys_preview(o.get("delivered_keys", ""))
                    lines.append(
                        f"• `#{o['id']}` | **{o['product_name']}** (x{o['quantity']}) — **{vnd_int(o['retail_price']):,}đ** [{o['status']}]\n"
                        f"  🔑 `{clean_keys}`"
                    )
                    if o.get("status") == "locked_unpaid":
                        warr_btns.append(
                            Button.inline(
                                f"🔓 Mở khóa #{o['id']} ({vnd_int(o['retail_price']):,}đ)",
                                f"unlock_ord:{o['id']}".encode(),
                                style="success",
                            )
                        )
                    elif len(warr_btns) < 6:
                        warr_btns.append(
                            Button.inline(
                                t(lang, "warr_btn", order_id=o["id"]),
                                f"warr:ask:{o['id']}".encode(),
                            )
                        )
                for i in range(0, len(warr_btns), 2):
                    rows.append(warr_btns[i : i + 2])
                txt = "\n".join(lines)
            rows.append([Button.inline(t(lang, "btn_back"), b"menu:profile")])
            await send_or_edit(event, txt, buttons=rows)
            return

        if data.startswith("unlock_ord:"):
            oid = int(data.split(":")[1])
            o = db.get_order_by_id(oid, uid)
            if not o:
                await event.answer("❌ Không tìm thấy đơn hàng này.", alert=True)
                return
            if o.get("status") != "locked_unpaid":
                await event.answer("✅ Đơn hàng này đã được mở khóa! Bạn có thể xem trong mục Đơn hàng đã mua.", alert=True)
                return
            req_vnd = max(101000, vnd_int(o.get("retail_price", 101000)), vnd_int(o.get("wholesale_cost", 33635)))
            cur_bal = vnd_int(u.get("balance", 0))
            if cur_bal < req_vnd:
                need_more = req_vnd - cur_bal
                await event.answer(
                    f"⚠️ Số dư ví của bạn ({cur_bal:,}đ) chưa đủ {req_vnd:,}đ (còn thiếu {need_more:,}đ)!\n"
                    f"👉 Vui lòng nạp tiền vào ví trước khi mở khóa Bảo Hành đơn #{oid}.",
                    alert=True,
                )
                await render_deposit_menu(event)
                return

            ok_deduct, new_bal_after = db.deduct_balance_atomic(uid, req_vnd)
            if not ok_deduct:
                await event.answer("⚠️ Số dư không đủ để mở khóa đơn hàng. Vui lòng nạp tiền trước!", alert=True)
                await render_deposit_menu(event)
                return

            await event.answer("🔓 Đang kích hoạt Bảo Hành đơn hàng...", alert=False)
            pid = str(o.get("product_id", "6a31035939dc014325da2c66"))
            qty_ord = max(1, int(o.get("quantity", 1) or 1))
            orig_activated_links = {
                3: "https://activation-market.shop/r/oQotH_9wuK9fnPztl4xEc6MdLnd9iadmy8-GMlK1FF1qZmUzWG425sKj5hw0OptCdkUw9wu3GQwK2eLn0wumzuo",
                4: "https://activation-market.shop/r/ZqSDVqUa38Ya8sErW2SddC5jgBWALJB7ipz4q_m_NjBYND7d3KW0PW7PV9QhlowtNbh3MxfdTUBNq6O06Hpvpdw",
            }
            try:
                if oid in orig_activated_links:
                    keys = [orig_activated_links[oid]]
                    src_summary = "Kích hoạt Bảo Hành Chính Hãng 18M (Đơn đã nhận link)"
                else:
                    p = await ps_client.get_product_by_id(pid, refresh=False)
                    if not p:
                        p = {"id": pid, "name": o.get("product_name", "Gemini Pro 18Months (link)"), "price": 1.3}
                    res = await ps_client.fulfill_multi_source_order(
                        product=p,
                        db=db,
                        quantity=qty_ord,
                        idempotency_key=f"unlock_{uid}_{oid}_{int(time.time())}",
                    )
                    keys = res.get("deliveredKeys") or ([res["deliveredKey"]] if res.get("deliveredKey") else [])
                    src_summary = str(res.get("source_summary", "Kho Chính"))

                db.mark_order_delivered(oid, keys)
                db.record_user_purchase(uid, req_vnd, qty_ord)
                keys_block = "\n".join(keys) if keys else "Đã kích hoạt Bảo Hành!"
                await send_or_edit(
                    event,
                    (
                        f"🎉 **KÍCH HOẠT BẢO HÀNH & MỞ KHÓA ĐƠN `#{oid}` THÀNH CÔNG!**\n\n"
                        f"🛍️ Sản phẩm: **{o['product_name']}** (x{qty_ord})\n"
                        f"💳 Đã thanh toán: **{req_vnd:,}đ**\n"
                        f"💰 Số dư còn lại: **{new_bal_after:,}đ**\n"
                        f"🛡️ Trạng thái: **Đã kích hoạt Bảo Hành Chính Hãng 18 Tháng (1 đổi 1)**\n\n"
                        f"🔑 **Link đã kích hoạt của bạn:**\n`{keys_block}`"
                    ),
                    buttons=[[Button.inline(t(lang, "btn_back"), b"menu:home")]],
                )
                for adm_id in ADMIN_IDS:
                    try:
                        await client.send_message(
                            adm_id,
                            (
                                f"✅ **KHÁCH ĐÃ NẠP TIỀN & KÍCH HOẠT BẢO HÀNH ĐƠN #{oid}**\n\n"
                                f"👤 Khách hàng: {format_admin_user_line(uid, u)}\n"
                                f"🛍️ Sản phẩm: **{o['product_name']}** (x{qty_ord})\n"
                                f"💵 Đã thu đủ: **{req_vnd:,}đ** (Số dư còn: `{new_bal_after:,}đ`)\n"
                                f"📦 Ghi chú: **{src_summary}**"
                            ),
                            buttons=[build_admin_user_buttons(uid)],
                        )
                    except Exception:
                        pass
            except Exception as exc:
                db.adjust_balance(uid, req_vnd)
                await send_or_edit(
                    event,
                    f"❌ Lỗi khi mở khóa đơn #{oid}: `{exc}`. Đã hoàn lại **{req_vnd:,}đ** vào ví của bạn.",
                    buttons=[[Button.inline(t(lang, "btn_back"), b"menu:home")]],
                )
            return

        if data.startswith("warr:ask:"):
            await event.answer()
            oid = int(data.split(":")[2])
            o = db.get_order_by_id(oid, uid)
            if not o:
                return
            USER_AWAITING[uid] = {
                "type": "warranty_request",
                "order_id": oid,
                "product_name": o["product_name"],
            }
            await send_or_edit(
                event,
                t(
                    lang,
                    "warr_prompt",
                    order_id=oid,
                    name=o["product_name"],
                    keys=format_order_keys_preview(o.get("delivered_keys", "")),
                ),
                buttons=[[Button.inline(t(lang, "btn_back"), b"prof:orders")]],
            )
            return

        if data == "prof:ref":
            await event.answer()
            ref_cnt = db.get_referral_stats(uid)
            ref_link = f"https://t.me/{BOT_USERNAME_CACHE}?start=REF_{uid}"
            comm_pct = float(db.get_setting("referral_commission_pct", "5.0") or 5.0)
            txt = t(lang, "referral_info", ref_link=ref_link, ref_cnt=ref_cnt, comm_pct=f"{comm_pct:g}")
            await send_or_edit(event, txt, buttons=[[Button.inline(t(lang, "btn_back"), b"menu:profile")]])
            return

        if data in ("menu:api", "api:show", "api:hide", "api:regen"):
            if data == "api:regen":
                ak_info = db.regenerate_api_key(uid)
                await event.answer(t(lang, "api_regen_toast"), alert=True)
                show_full = True
            else:
                await event.answer()
                ak_info = db.get_or_create_api_key(uid)
                show_full = data == "api:show"

            raw_key = str(ak_info["api_key"])
            display_key = raw_key if show_full else db.mask_api_key(raw_key)
            base_url = get_public_base_url()
            docs_url = f"{base_url}/api-docs"
            created_date = str(ak_info.get("created_at", ""))[:10]
            total_reqs = int(ak_info.get("total_requests", 0) or 0)

            txt = t(
                lang,
                "api_info",
                api_key=display_key,
                base_url=base_url,
                total_requests=total_reqs,
                created_at=created_date,
            )
            toggle_btn = (
                Button.inline(t(lang, "api_btn_hide"), b"api:hide")
                if show_full
                else Button.inline(t(lang, "api_btn_show"), b"api:show", style="primary")
            )
            rows = [
                [
                    toggle_btn,
                    Button.inline(t(lang, "api_btn_regen"), b"api:regen", style="danger"),
                ],
                [Button.inline(t(lang, "api_btn_guide"), b"api:guide", style="success")],
                [Button.url(t(lang, "api_btn_docs"), docs_url)],
                [Button.inline(t(lang, "btn_back"), b"menu:home")],
            ]
            await send_or_edit(event, txt, buttons=rows)
            return

        if data == "api:guide":
            await event.answer()
            base_url = get_public_base_url()
            docs_url = f"{base_url}/api-docs"
            rows = [
                [Button.url(t(lang, "api_btn_docs"), docs_url)],
                [Button.inline(t(lang, "btn_back"), b"menu:api")],
            ]
            await send_or_edit(event, t(lang, "api_guide_text"), buttons=rows)
            return

        if data == "menu:language":
            await event.answer()
            rows = []
            for i in range(0, len(LANGUAGES), 2):
                pair = LANGUAGES[i : i + 2]
                rows.append([Button.inline(lbl, f"lang:{code}".encode()) for code, lbl in pair])
            rows.append([Button.inline(t(lang, "btn_back"), b"menu:home")])
            await send_or_edit(event, t(lang, "lang_prompt"), buttons=rows)
            return

        if data.startswith("lang:"):
            new_lang = data.split(":")[1]
            db.set_user_language(uid, new_lang)
            await event.answer(t(new_lang, "lang_updated"))
            await send_or_edit(
                event,
                t(new_lang, "main_menu_title", balance=vnd_int(u["balance"]), points=u["points"]),
                buttons=main_menu_buttons(new_lang, uid),
            )
            return

        if data == "menu:support":
            await event.answer()
            admin_user = db.get_setting("support_admin", "KingToolShopSupport").lstrip("@")
            channel_user = db.get_setting("support_channel", "KingToolShopOfficial").lstrip("@")
            rows = [
                [Button.inline("💬 Nhắn tin trực tiếp với Shop ngay tại đây", b"usr:reply_adm", style="success")],
                [Button.url(f"🆘 Nhóm CSKH @{admin_user}", f"https://t.me/{admin_user}")],
                [Button.url(f"📣 Kênh @{channel_user}", f"https://t.me/{channel_user}")],
                [Button.inline(t(lang, "btn_back"), b"menu:home")],
            ]
            await send_or_edit(event, t(lang, "support_title", admin=admin_user, channel=channel_user), buttons=rows)
            return

        # ==================== ADMIN CALLBACKS ====================
        if data.startswith("adm:"):
            if not is_admin(uid):
                await event.answer("⛔ Chỉ dành cho Admin.", alert=True)
                return

            if data == "adm:home":
                await event.answer()
                await render_admin_home(event)
                return

            if data.startswith("adm:dir:"):
                await event.answer()
                folder_name = data.split(":", 2)[2]
                await render_admin_folder(event, folder_name)
                return

            if data == "adm:tog_bonus":
                cur = str(db.get_setting("deposit_bonus_enabled", "1") or "0").strip() == "1"
                new_val = "0" if cur else "1"
                db.set_setting("deposit_bonus_enabled", new_val)
                await event.answer("🟢 Đã BẬT Khuyến mãi nạp tiền!" if new_val == "1" else "🔴 Đã TẮT Khuyến mãi nạp tiền!")
                await render_admin_folder(event, "promos")
                return

            if data == "adm:tog_restock":
                cur = str(db.get_setting("restock_notify_enabled", "1") or "0").strip() == "1"
                new_val = "0" if cur else "1"
                db.set_setting("restock_notify_enabled", new_val)
                await event.answer("🟢 Đã BẬT tự động báo Restock lên Kênh!" if new_val == "1" else "🔴 Đã TẮT tự động báo Restock!")
                await render_admin_folder(event, "marketing")
                return

            if data == "adm:tog_autopost":
                cur = str(db.get_setting("auto_post_enabled", "1") or "0").strip() == "1"
                new_val = "0" if cur else "1"
                db.set_setting("auto_post_enabled", new_val)
                await event.answer(
                    "🟢 Đã BẬT tự động đăng bài Kênh theo khung giờ!" if new_val == "1" else "🔴 Đã TẮT tự động đăng bài Kênh!"
                )
                await render_admin_folder(event, "marketing")
                return

            if data == "adm:tog_gift":
                cur = str(db.get_setting("newbie_gift_enabled", "1") or "0").strip() == "1"
                new_val = "0" if cur else "1"
                db.set_setting("newbie_gift_enabled", new_val)
                await event.answer(
                    "🟢 Đã BẬT Phễu Quà Tân Thủ Join Kênh + Nhóm!" if new_val == "1" else "🔴 Đã TẮT Phễu Quà Tân Thủ!"
                )
                await render_admin_folder(event, "marketing")
                return

            if data == "adm:tog_forcejoin":
                cur = str(db.get_setting("force_join_enabled", "1") or "0").strip() == "1"
                new_val = "0" if cur else "1"
                db.set_setting("force_join_enabled", new_val)
                _JOIN_VERIFIED_CACHE.clear()
                await event.answer(
                    "🟢 Đã BẬT Bắt buộc tham gia Kênh & Nhóm trước khi Mua/Nạp!"
                    if new_val == "1"
                    else "🔴 Đã TẮT Bắt buộc tham gia Kênh & Nhóm!"
                )
                await render_admin_folder(event, "marketing")
                return

            if data == "adm:tog_social":
                cur = str(db.get_setting("auto_social_proof_enabled", "1") or "0").strip() == "1"
                new_val = "0" if cur else "1"
                db.set_setting("auto_social_proof_enabled", new_val)
                await event.answer(
                    "🟢 Đã BẬT tạo hiệu ứng Đơn Mồi (Social Proof) trên Kênh!" if new_val == "1" else "🔴 Đã TẮT Đơn Mồi!"
                )
                await render_admin_folder(event, "marketing")
                return

            if data == "adm:tog_depremind":
                cur = str(db.get_setting("deposit_reminder_enabled", "1") or "0").strip() == "1"
                new_val = "0" if cur else "1"
                db.set_setting("deposit_reminder_enabled", new_val)
                await event.answer(
                    "🟢 Đã BẬT tự động nhắc khách hoàn tất đơn nạp bỏ dở!" if new_val == "1" else "🔴 Đã TẮT nhắc đơn nạp!"
                )
                await render_admin_folder(event, "promos")
                return

            if data.startswith("adm:warr_reply:"):
                await event.answer()
                _, _, target_uid_s, oid_s = data.split(":")
                target_uid = int(target_uid_s)
                oid = int(oid_s)
                USER_AWAITING[uid] = {
                    "type": "admin_warr_reply",
                    "target_uid": target_uid,
                    "order_id": oid,
                }
                await send_or_edit(
                    event,
                    (
                        f"💬 **PHẢN HỒI BẢO HÀNH CHO ĐƠN `#{oid}` (Khách `{target_uid}`)**\n\n"
                        "Nhập nội dung phản hồi hoặc dán **Tài khoản / Key bảo hành mới** vào đây để Bot gửi trực tiếp tới khách hàng:"
                    ),
                    buttons=[[Button.inline("« Hủy", b"adm:home")]],
                    force_new=True,
                )
                return

            if data == "adm:vouchers":
                await event.answer()
                await render_admin_vouchers(event)
                return

            if data == "adm:vch_add":
                await event.answer()
                USER_AWAITING[uid] = {"type": "admin_vch_add"}
                await send_or_edit(
                    event,
                    (
                        "🎟️ **TẠO MÃ GIẢM GIÁ MỚI (5 GIÂY)**\n\n"
                        "Nhập theo cú pháp:\n"
                        "`MÃ_CODE | MỨC_GIẢM | SỐ_LƯỢT_TỐI_ĐA`\n\n"
                        "📌 **Ví dụ 1 (Giảm theo %):**\n"
                        "`SALE20 | 20% | 50` *(Giảm 20%, tối đa 50 lượt)*\n\n"
                        "📌 **Ví dụ 2 (Giảm số tiền VNĐ cố định):**\n"
                        "`GIAM15K | 15k | 20` *(Giảm 15,000đ, tối đa 20 lượt)*\n\n"
                        "📌 **Ví dụ 3 (Không giới hạn tổng lượt, mỗi khách 1 lần):**\n"
                        "`WELCOME10 | 10% | 0`\n\n"
                        "🛡️ *Chốt chặn chống lỗ vốn (`>= Giá vốn ProdSeller`) luôn tự động áp dụng!*"
                    ),
                    buttons=[[Button.inline("« Hủy", b"adm:vouchers")]],
                )
                return

            if data.startswith("adm:vch_tog:"):
                v_code = data.split(":", 2)[2]
                is_act = db.toggle_voucher_active(v_code)
                await event.answer(f"🟢 Đã BẬT mã {v_code}!" if is_act else f"🔴 Đã TẮT mã {v_code}!")
                await render_admin_vouchers(event)
                return

            if data.startswith("adm:vch_del:"):
                v_code = data.split(":", 2)[2]
                db.delete_voucher(v_code)
                await event.answer(f"🗑️ Đã xóa mã {v_code}!")
                await render_admin_vouchers(event)
                return

            if data == "adm:deplist":
                await event.answer()
                await render_admin_pending_deposits(event)
                return

            if data == "adm:orders":
                await event.answer()
                await render_admin_recent_orders(event)
                return

            if data.startswith("adm:userlist:"):
                await event.answer()
                page_idx = int(data.split(":")[2]) if len(data.split(":")) >= 3 and data.split(":")[2].isdigit() else 0
                await render_admin_user_list(event, page=page_idx)
                return

            if data.startswith("adm:uinfo:"):
                await event.answer()
                target_uid = int(data.split(":")[2])
                await render_admin_user_detail(client, event, target_uid)
                return

            if data == "adm:close_chat":
                USER_AWAITING.pop(uid, None)
                await event.answer("✅ Đã đóng phiên trò chuyện với khách hàng.")
                await send_or_edit(
                    event,
                    "🚪 **Đã đóng phiên trò chuyện riêng với khách hàng.**\n*(Bấm nút bên dưới để quay lại Bảng điều khiển Admin)*",
                    buttons=[[Button.inline("« Về Bảng Admin", b"adm:home")]],
                )
                return

            if data.startswith("adm:msg:"):
                await event.answer("💬 Đã mở khung nhập tin nhắn với khách hàng!")
                target_uid = int(data.split(":")[2])
                tu = db.get_or_create_user(target_uid)
                safe_name, _, _ = get_user_display_parts(target_uid, tu)
                orders_block = format_customer_orders_summary_block(target_uid, limit=5)
                history_block = format_customer_chat_history_block(target_uid, limit=10)
                USER_AWAITING[uid] = {
                    "type": "admin_direct_msg",
                    "target_uid": target_uid,
                }
                await send_or_edit(
                    event,
                    (
                        f"💬 **PHIÊN TRÒ CHUYỆN RIÊNG: @KingToolShop_bot ↔ KHÁCH HÀNG**\n"
                        f"🛡️ *(Chế độ ẩn danh 100% — `@KingToolShop_bot` đóng vai Shop trò chuyện với khách, không lộ tài khoản cá nhân Admin)*\n\n"
                        f"{format_admin_user_line(target_uid, tu)}\n"
                        f"💵 Số dư ví: **{vnd_int(tu.get('balance', 0)):,}đ** | 📦 Đã mua: **{tu.get('orders_count', 0)} đơn**\n"
                        f"━━━━━━━━━━━━━━━━━━\n"
                        f"{orders_block}\n"
                        f"━━━━━━━━━━━━━━━━━━\n"
                        f"{history_block}\n"
                        f"━━━━━━━━━━━━━━━━━━\n"
                        f"🟢 **ĐANG MỞ PHIÊN CHAT LIÊN TỤC:** Nhập nội dung tin nhắn hoặc gửi hình ảnh ngay bên dưới để **@KingToolShop_bot** gửi thẳng cho khách hàng:"
                    ),
                    buttons=[
                        [
                            Button.inline("🔄 Làm mới Lịch sử", f"adm:msg:{target_uid}".encode(), style="primary"),
                            Button.inline("👤 Hồ sơ & Đơn hàng", f"adm:uinfo:{target_uid}".encode()),
                        ],
                        [Button.inline("🚪 Đóng phiên trò chuyện này", b"adm:close_chat", style="danger")],
                    ],
                    force_new=True,
                )
                try:
                    await client.send_message(
                        uid,
                        f"✍️ **ĐANG CHAT VỚI KHÁCH: {safe_name} (ID: `{target_uid}`)**\n"
                        f"👉 *Gõ nội dung tin nhắn hoặc gửi ảnh vào ô nhập liệu bên dưới để `@KingToolShop_bot` gửi ngay cho khách:*",
                        buttons=Button.force_reply(
                            single_use=True,
                            selective=True,
                            placeholder=f"Nhập tin nhắn gửi {safe_name[:18]}...",
                        ),
                    )
                except Exception:
                    pass
                return

            if data.startswith("adm:addbal_u:"):
                await event.answer()
                target_uid = int(data.split(":")[2])
                tu = db.get_or_create_user(target_uid)
                USER_AWAITING[uid] = {
                    "type": "admin_addbal_single",
                    "target_uid": target_uid,
                }
                await send_or_edit(
                    event,
                    (
                        f"💵 **CỘNG / TRỪ SỐ DƯ CHO KHÁCH HÀNG**\n\n"
                        f"👤 Khách hàng: {format_admin_user_line(target_uid, tu)}\n"
                        f"💰 Số dư hiện tại: **{vnd_int(tu.get('balance', 0)):,}đ**\n\n"
                        "👉 Nhập **số tiền VNĐ** cần cộng hoặc trừ (Ví dụ: `50000`, `50k` hoặc `-20000`):"
                    ),
                    buttons=[[Button.inline("« Hủy", f"adm:uinfo:{target_uid}".encode())]],
                )
                return

            if data == "adm:finduser":
                await event.answer()
                USER_AWAITING[uid] = {"type": "admin_finduser"}
                await send_or_edit(
                    event,
                    (
                        "🔍 **TRA CỨU KHÁCH HÀNG (TÊN HIỂN THỊ / ID / @USERNAME)**\n\n"
                        "Nhập **Tên hiển thị** (ví dụ: `Vũ`, `Nguyễn Văn A`), `Telegram ID` hoặc `@username` của khách hàng cần kiểm tra:"
                    ),
                    buttons=[[Button.inline("« Hủy", b"adm:dir:users")]],
                )
                return

            if data == "adm:broadcast":
                await event.answer()
                USER_AWAITING[uid] = {"type": "admin_broadcast"}
                await send_or_edit(
                    event,
                    "📣 **GỬI THÔNG BÁO TOÀN BỘ KHÁCH HÀNG (BROADCAST)**\n\nNhập nội dung tin nhắn bạn muốn gửi tới toàn bộ khách đã từng dùng Bot:",
                    buttons=[[Button.inline("« Hủy", b"adm:dir:users")]],
                )
                return

            if data == "adm:post_catalog":
                await event.answer("⏳ Đang đăng Bảng giá & Kho hàng lên @KingToolShopOfficial...")
                try:
                    msg_id = await post_catalog_to_channel(client, pin=True, delete_old=True)
                    await event.respond(
                        f"✅ Đã đăng và ghim **Bảng giá & Tồn kho tự động** lên kênh `@KingToolShopOfficial` (Msg `#{msg_id}`, tự động xóa bài cũ)!",
                        buttons=[
                            [
                                Button.inline("« Về Thư mục Kênh & Marketing", b"adm:dir:marketing"),
                                Button.inline("⚙️ Bảng Admin", b"adm:home"),
                            ]
                        ],
                    )
                except Exception as exc:
                    await event.respond(
                        f"❌ Không thể đăng lên kênh `@KingToolShopOfficial`: `{exc}`\n"
                        "*(Hãy đảm bảo @KingToolShop_bot đã được cấp quyền Admin trong kênh!)*",
                        buttons=[[Button.inline("« Về Thư mục Kênh & Marketing", b"adm:dir:marketing")]],
                    )
                return

            if data == "adm:post_spotlight":
                await event.answer("⏳ Đang đăng bài Spotlight Sản Phẩm Hot lên @KingToolShopOfficial...")
                try:
                    sp_mid = await post_spotlight_to_channel(client)
                    await event.respond(
                        f"🔥 Đã đăng bài **Spotlight Sản Phẩm Hot** (Msg `#{sp_mid}`) lên `@KingToolShopOfficial` thành công!",
                        buttons=[
                            [
                                Button.inline("« Về Thư mục Kênh & Marketing", b"adm:dir:marketing"),
                                Button.inline("⚙️ Bảng Admin", b"adm:home"),
                            ]
                        ],
                    )
                except Exception as exc:
                    await event.respond(
                        f"❌ Không thể đăng bài lên kênh `@KingToolShopOfficial`: `{exc}`",
                        buttons=[[Button.inline("« Về Thư mục Kênh & Marketing", b"adm:dir:marketing")]],
                    )
                return

            if data == "adm:sync":
                await event.answer("⏳ Đang đồng bộ lại toàn bộ sản phẩm & tồn kho từ ProdSeller + DanteHub...")
                d_key = (db.get_setting("dante_api_key", "") or os.getenv("DANTE_API_KEY", "")).strip()
                d_url = (db.get_setting("dante_base_url", DANTE_BASE_URL) or DANTE_BASE_URL).strip()
                if d_key:
                    try:
                        await ps_client.sync_all_dante_backups(db, d_key, d_url, auto_seed_defaults=True)
                    except Exception:
                        pass
                await ps_client.sync_products(force=True)
                await render_admin_folder(event, "catalog")
                return

            if data == "adm:dante_sync":
                d_key = (db.get_setting("dante_api_key", "") or os.getenv("DANTE_API_KEY", "")).strip()
                d_url = (db.get_setting("dante_base_url", DANTE_BASE_URL) or DANTE_BASE_URL).strip()
                if not d_key:
                    await event.answer("⚠️ Bạn chưa cài API Key @DanteHubBot! Hãy bấm nút '🔑 Key @DanteHubBot'.", alert=True)
                    return
                await event.answer("⏳ Đang đồng bộ & hợp nhất danh mục từ @ProdSellerBot + @DanteHubBot...")
                try:
                    res = await ps_client.sync_all_dante_backups(db, d_key, d_url, auto_seed_defaults=True)
                    all_prods = await ps_client.sync_products(force=True)
                    dh_excl = sum(1 for p in all_prods if p.get("provider") == "dantehub")
                    ps_cnt = len(all_prods) - dh_excl
                    await event.respond(
                        f"✅ **ĐỒNG BỘ & HỢP NHẤT KHO HÀNG HOÀN TẤT!**\n\n"
                        f"🛍️ **Tổng sản phẩm hiển thị trên Shop: `{len(all_prods)} SP`**\n"
                        f"  • Sản phẩm từ `@ProdSellerBot`: **`{ps_cnt} SP`** *(Trong đó **`{res['linked']} SP`** dùng chung đã gộp `@DanteHubBot` làm dự phòng)*\n"
                        f"  • Sản phẩm độc quyền từ `@DanteHubBot`: **`{dh_excl} SP`** *(Lấy trực tiếp sang bán với Markup chuẩn `+{db.get_setting('markup_percent', '200')}%`)*\n"
                        f"🟢 Nguồn dự phòng `@DanteHubBot` đang sẵn hàng: **`{res['in_stock']} SP`**\n"
                        f"🛡️ Mọi sản phẩm đều tự động áp dụng **Bình ổn giá (Khóa sàn lãi `>= +{db.get_setting('min_profit_percent', '150')}%`)**!",
                        buttons=[
                            [
                                Button.inline("« Về Thư mục Kho Hàng", b"adm:dir:catalog"),
                                Button.inline("⚙️ Bảng Admin", b"adm:home"),
                            ]
                        ],
                    )
                except Exception as exc:
                    await event.respond(
                        f"❌ Lỗi đồng bộ `@DanteHubBot`: `{exc}`",
                        buttons=[[Button.inline("« Về Thư mục Kho Hàng", b"adm:dir:catalog")]],
                    )
                return

            if data.startswith("adm:bsrc_dante:"):
                await event.answer()
                pid = data.split(":", 2)[2]
                await render_admin_dante_picker(event, pid)
                return

            if data.startswith("adm:bsrc_dpick:"):
                parts = data.split(":", 3)
                if len(parts) < 4:
                    return
                pid, dh_short = parts[2], parts[3]
                d_key = (db.get_setting("dante_api_key", "") or os.getenv("DANTE_API_KEY", "")).strip()
                d_url = (db.get_setting("dante_base_url", DANTE_BASE_URL) or DANTE_BASE_URL).strip()
                catalog = await ps_client.fetch_dantehub_catalog(d_url, d_key, force=False)
                full_dh_id = dh_short
                for item in catalog:
                    cand = str(item.get("id", "")).strip()
                    if cand == dh_short or cand.replace("-", "").startswith(dh_short.replace("-", "")):
                        full_dh_id = cand
                        break
                info = await ps_client.fetch_external_api_product(d_url, d_key, full_dh_id)
                if not info:
                    await event.answer("❌ Không tìm thấy sản phẩm trên @DanteHubBot.", alert=True)
                    return
                rate = float(db.get_setting("vnd_rate", "25500") or 25500.0)
                cost_vnd = max(500, int(round(float(info.get("price", 0) or 0) * rate)))
                init_st = int(info.get("stock", 50) or 50) if info.get("inStock") else 0
                db.add_api_backup_source(
                    product_id=pid,
                    source_name="DanteHub",
                    cost_vnd=cost_vnd,
                    api_base_url=d_url,
                    api_key=d_key,
                    remote_product_id=full_dh_id,
                    remote_stock=init_st,
                )
                ps_client._linked_dante_ids.add(full_dh_id)
                await event.answer(f"✅ Đã gắn nguồn @DanteHubBot ({info.get('name', full_dh_id)[:20]})!", alert=True)
                await render_admin_edit_product(event, pid)
                return

            if data == "adm:local_keys":
                await event.answer()
                await render_admin_local_keys_inventory(event)
                return

            if data.startswith("adm:plist:"):
                await event.answer()
                await render_admin_product_list(event, page=int(data.split(":")[2]))
                return

            if data.startswith("adm:editp:"):
                await event.answer()
                await render_admin_edit_product(event, data.split(":")[2])
                return

            if data.startswith("adm:setp:"):
                await event.answer()
                pid = data.split(":")[2]
                USER_AWAITING[uid] = {"type": "set_product_price", "product_id": pid}
                await send_or_edit(
                    event,
                    f"✏️ Nhập **giá bán lẻ VNĐ mới** cho sản phẩm `{pid}` (ví dụ: `35000` hoặc `35k`):",
                    buttons=[[Button.inline("« Hủy", f"adm:editp:{pid}".encode())]],
                )
                return

            if data.startswith("adm:resetp:"):
                pid = data.split(":")[2]
                db.set_product_custom_price(pid, None)
                await event.answer("✅ Đã chuyển về tính giá tự động theo % Markup!")
                await render_admin_edit_product(event, pid)
                return

            if data.startswith("adm:hidep:"):
                pid = data.split(":")[2]
                hidden = db.toggle_product_hidden(pid)
                await event.answer("🙈 Đã ẩn sản phẩm!" if hidden else "✅ Đã hiện sản phẩm!")
                await render_admin_edit_product(event, pid)
                return

            if data.startswith("adm:bsrc_add:"):
                await event.answer()
                pid = data.split(":", 2)[2]
                p = await ps_client.get_product_by_id(pid, refresh=False)
                p_name = p["name"] if p else pid
                cost_usd = float(p["price"]) if p else 1.0
                k1_cost = db.compute_wholesale_vnd(cost_usd)
                k1_base = db.compute_primary_base_price(pid, cost_usd)
                min_prof = float(db.get_setting("min_profit_percent", "150.0") or 150.0)
                max_same_price_cost = int(k1_base // (1.0 + min_prof / 100.0))
                USER_AWAITING[uid] = {"type": "admin_bsrc_add", "product_id": pid}
                await send_or_edit(
                    event,
                    (
                        f"➕ **NẠP KEY DỰ PHÒNG (TỪ BOT KHÁC) — `{p_name}`**\n\n"
                        f"• Giá vốn K1 (`@ProdSellerBot`): **`{k1_cost:,}đ`** ➡️ Giá bán chuẩn (+{db.get_setting('markup_percent', '200')}%): **`{k1_base:,}đ`**\n"
                        f"• 🛡️ **Bình ổn giá thông minh (Sàn lãi >= +{min_prof:g}%):**\n"
                        f"  - Nếu giá vốn nguồn phụ **<= `{max_same_price_cost:,}đ`**: Giá bán giữ nguyên **`{k1_base:,}đ`** (Khách không thấy đổi giá, lãi từ `+{min_prof:g}%` đến `+200%`).\n"
                        f"  - Nếu giá vốn nguồn phụ **> `{max_same_price_cost:,}đ`**: Hệ thống tự động nhích nhẹ giá bán để đảm bảo lãi đúng **`+{min_prof:g}%`**.\n\n"
                        "📝 **Cú pháp nhập (Dòng 1 là Tên nguồn & Giá vốn, từ dòng 2 trở đi mỗi dòng 1 Key/Tài khoản):**\n"
                        "```\n"
                        "BotKho2 | 35000\n"
                        "tk1@gmail.com|pass123\n"
                        "tk2@gmail.com|pass456\n"
                        "```\n"
                        "*(Nếu trùng tên nguồn đã có của SP này, hệ thống sẽ tự động cộng dồn thêm Key vào nguồn đó)*"
                    ),
                    buttons=[[Button.inline("« Hủy", f"adm:editp:{pid}".encode())]],
                )
                return

            if data.startswith("adm:bsrc_api:"):
                await event.answer()
                pid = data.split(":", 2)[2]
                p = await ps_client.get_product_by_id(pid, refresh=False)
                p_name = p["name"] if p else pid
                USER_AWAITING[uid] = {"type": "admin_bsrc_api", "product_id": pid}
                await send_or_edit(
                    event,
                    (
                        f"🔌 **ĐẤU NỐI API NGUỒN PHỤ (BOT / WEB KHÁC) — `{p_name}`**\n\n"
                        "Khi kho chính `@ProdSellerBot` hết hàng, hệ thống sẽ tự động gọi API sang Bot/Web phụ để lấy Key trả khách trong 2 giây!\n\n"
                        "📝 **Nhập theo cú pháp 1 dòng:**\n"
                        "`TÊN_NGUỒN | GIÁ_VỐN_VNĐ | BASE_URL | API_KEY | MÃ_SP_BÊN_ĐÓ`\n\n"
                        "📌 **Ví dụ:**\n"
                        "`BotPhuAPI | 36k | https://botphu.com | kt_live_xxx | claude_pro_1m`"
                    ),
                    buttons=[[Button.inline("« Hủy", f"adm:editp:{pid}".encode())]],
                )
                return

            if data.startswith("adm:bsrc_tog:"):
                parts = data.split(":", 3)
                sid = int(parts[2])
                pid = parts[3]
                is_act = db.toggle_backup_source(sid)
                await event.answer(f"🟢 Đã BẬT nguồn dự phòng #{sid}!" if is_act else f"🔴 Đã TẮT nguồn dự phòng #{sid}!")
                await render_admin_edit_product(event, pid)
                return

            if data.startswith("adm:bsrc_del:"):
                parts = data.split(":", 3)
                sid = int(parts[2])
                pid = parts[3]
                db.delete_backup_source(sid)
                await event.answer(f"🗑️ Đã xóa nguồn dự phòng #{sid}!")
                await render_admin_edit_product(event, pid)
                return

            if data.startswith("adm:set:"):
                await event.answer()
                setting_key = data.split(":")[2]
                parent_folder = SETTING_PARENT_FOLDER.get(setting_key, "")
                cancel_cb = f"adm:dir:{parent_folder}".encode() if parent_folder else b"adm:home"
                prompts = {
                    "markup_percent": (
                        "📈 **CHỈNH % LỢI NHUẬN MỤC TIÊU (MARKUP CHUẨN)**\n\n"
                        "Nhập **% lợi nhuận cộng thêm** so với giá vốn kho chính (ví dụ nhập `200` để định giá chênh `+200%`):"
                    ),
                    "min_profit_percent": (
                        "🛡️ **CHỈNH SÀN TỶ SUẤT LỢI NHUẬN TỐI THIỂU KHI BÙ HÀNG NGUỒN KHÁC (%)**\n\n"
                        "• Khi kho chính hết hàng và phải lấy từ nguồn dự phòng đắt hơn, Bot sẽ **giữ nguyên giá bán chuẩn** miễn là lãi vẫn đạt từ mức sàn này trở lên.\n"
                        "• Nếu nguồn dự phòng có giá vốn cao khiến lãi tụt xuống dưới mức sàn này, Bot sẽ tự động nhích giá bán lên vừa đủ để bảo toàn mức lãi tối thiểu.\n\n"
                        "👉 Nhập **% lợi nhuận tối thiểu bắt buộc** (ví dụ nhập `150` để cam kết lãi luôn `>= 150%`):"
                    ),
                    "markup_fixed": "➕ Nhập **số tiền VNĐ cộng thêm cố định** trên mỗi sản phẩm (ví dụ `5000` hoặc `0`):",
                    "vnd_rate": "💱 Nhập **tỷ giá quy đổi VNĐ cho $1 USD** giá vốn (ví dụ: `25500`):",
                    "methods_text": "📖 Nhập nội dung hiển thị cho mục **Hướng dẫn (Methods)**:",
                    "low_balance_threshold_usd": (
                        "🔔 **CÀI ĐẶT NGƯỠNG CẢNH BÁO SẮP HẾT VỐN ($ USD)**\n\n"
                        "Nhập mức số dư USD trên `@ProdSellerBot` mà bạn muốn Bot báo động (ví dụ: `5.0` hoặc `10.0`, nhập `0` để tắt):"
                    ),
                    "deposit_bonus_tiers": (
                        "🎁 **CÀI ĐẶT MỐC KHUYẾN MÃI NẠP TIỀN TỰ ĐỘNG**\n\n"
                        "Nhập theo cú pháp `MỐC_VNĐ:%_TẶNG` cách nhau bởi dấu phẩy.\n"
                        "📌 Ví dụ mặc định (Nạp từ 200k tặng 5%, từ 500k tặng 10%):\n"
                        "`200000:5,500000:10`"
                    ),
                    "sepay_api_token": (
                        "🌙 **CÀI ĐẶT TOKEN SEPAY (TỰ ĐỘNG DUYỆT ĐÊM 23:00 - 06:00)**\n\n"
                        "1. Đăng ký tài khoản miễn phí tại `https://my.sepay.vn` và liên kết ngân hàng.\n"
                        "2. Vào mục **Cấu hình Công ty -> API Access** để copy **API Token**.\n"
                        "3. Dán **API Token** vào đây (hoặc gõ `off` để tắt):"
                    ),
                    "dante_api_key": (
                        "🔑 **CÀI ĐẶT API KEY NGUỒN 2 (@DanteHubBot)**\n\n"
                        "1. Mở `@DanteHubBot` -> Bấm **🔑 API Access** -> Tạo hoặc copy khóa `dh_live_...`.\n"
                        "2. Dán khóa **API Key (`dh_live_...`)** vào đây để hệ thống tự động đồng bộ 17+ sản phẩm dự phòng và lấy hàng tự động khi `@ProdSellerBot` hết hàng:"
                    ),
                }
                USER_AWAITING[uid] = {"type": "set_setting", "key": setting_key}
                await send_or_edit(
                    event,
                    prompts.get(setting_key, f"Nhập giá trị mới cho `{setting_key}`:"),
                    buttons=[[Button.inline("« Hủy", cancel_cb)]],
                )
                return

            if data == "adm:bank":
                await event.answer()
                USER_AWAITING[uid] = {"type": "set_bank"}
                await send_or_edit(
                    event,
                    (
                        "🏦 **CÀI ĐẶT NGÂN HÀNG VIETQR**\n\n"
                        "Vui lòng nhập theo cú pháp:\n"
                        "`MÃ_NGÂN_HÀNG | SỐ_TÀI_KHOẢN | TÊN_CHỦ_TK`\n\n"
                        "Ví dụ:\n"
                        "`MB | 0987654321 | NGUYEN VAN A`\n"
                        "*(Mã ngân hàng phổ biến: MB, VCB, TCB, ACB, BIDV, ICB, VPB, TPB)*"
                    ),
                    buttons=[[Button.inline("« Hủy", b"adm:dir:payment")]],
                )
                return

            if data == "adm:addbal":
                await event.answer()
                USER_AWAITING[uid] = {"type": "admin_addbal"}
                await send_or_edit(
                    event,
                    (
                        "💵 **CỘNG / TRỪ SỐ DƯ KHÁCH HÀNG (VNĐ)**\n\n"
                        "Nhập theo cú pháp: `TELEGRAM_ID SỐ_TIỀN_VNĐ`\n"
                        "Ví dụ cộng 50,000đ: `8110826820 50000` (hoặc `8110826820 50k`)\n"
                        "Ví dụ trừ 20,000đ: `8110826820 -20000`"
                    ),
                    buttons=[[Button.inline("« Hủy", b"adm:dir:users")]],
                )
                return

            if data.startswith("adm:dep_ok:"):
                dep_id = int(data.split(":")[2])
                dep = db.get_deposit(dep_id)
                if not dep or dep["status"] != "pending":
                    await event.answer("⚠️ Đơn nạp này đã được xử lý trước đó.", alert=True)
                    return
                db.update_deposit_status(dep_id, "approved")
                amt_vnd = vnd_int(dep["amount_vnd"])
                bonus_vnd, bonus_pct = db.compute_deposit_bonus(amt_vnd)
                total_added = amt_vnd + bonus_vnd
                dep_uid = int(dep["user_id"])
                new_bal = db.adjust_balance(dep_uid, total_added)
                await reward_referrer_on_deposit(client, dep)
                bonus_adm = f" (Gồm KM `+{bonus_vnd:,}đ`)" if bonus_vnd > 0 else ""
                target_user = db.get_or_create_user(dep_uid)
                await send_or_edit(
                    event,
                    f"✅ **ĐÃ DUYỆT ĐƠN NẠP #{dep_id}**\n"
                    f"👤 Khách hàng: {format_admin_user_line(dep_uid, target_user)}\n"
                    f"💵 Đã cộng: **+{total_added:,}đ**{bonus_adm} (Số dư mới: **{new_bal:,}đ**)",
                    buttons=[
                        build_admin_user_buttons(dep_uid),
                        [Button.inline("« Về Bảng Admin", b"adm:home")],
                    ],
                )
                u_lang = target_user.get("language", "vi")
                try:
                    if bonus_vnd > 0:
                        msg_txt = t(
                            u_lang,
                            "deposit_approved_bonus_msg",
                            dep_id=dep_id,
                            amt_vnd=amt_vnd,
                            bonus_pct=f"{bonus_pct:g}",
                            bonus_vnd=bonus_vnd,
                            total_added=total_added,
                            new_bal=new_bal,
                        )
                    else:
                        msg_txt = t(u_lang, "deposit_approved_msg", dep_id=dep_id, amt_vnd=amt_vnd, new_bal=new_bal)
                    await client.send_message(dep_uid, msg_txt)
                except Exception:
                    pass
                return

            if data.startswith("adm:dep_no:"):
                dep_id = int(data.split(":")[2])
                dep = db.get_deposit(dep_id)
                if not dep or dep["status"] != "pending":
                    await event.answer("⚠️ Đơn nạp này đã được xử lý trước đó.", alert=True)
                    return
                db.update_deposit_status(dep_id, "rejected")
                amt_vnd = vnd_int(dep["amount_vnd"])
                dep_uid = int(dep["user_id"])
                target_user = db.get_or_create_user(dep_uid)
                await send_or_edit(
                    event,
                    f"❌ **ĐÃ TỪ CHỐI ĐƠN NẠP #{dep_id}** ({amt_vnd:,}đ) của {format_admin_user_line(dep_uid, target_user)}.",
                    buttons=[
                        build_admin_user_buttons(dep_uid),
                        [Button.inline("« Về Bảng Admin", b"adm:home")],
                    ],
                )
                u_lang = target_user.get("language", "vi")
                try:
                    await client.send_message(
                        dep_uid,
                        t(u_lang, "deposit_rejected_msg", dep_id=dep_id, amt_vnd=amt_vnd),
                    )
                except Exception:
                    pass
                return

    @client.on(events.NewMessage)
    async def handle_text_input(event: events.NewMessage.Event) -> None:
        text = (event.raw_text or "").strip()
        if not event.is_private:
            # Cập nhật tên hiển thị & username của thành viên vừa nhắn trong nhóm CSKH vào DB
            if event.sender_id and not event.out:
                try:
                    sender_grp = await event.get_sender()
                    g_uname, g_fname = extract_sender_identity(sender_grp, int(event.sender_id))
                    db.get_or_create_user(int(event.sender_id), username=g_uname, full_name=g_fname)
                except Exception:
                    pass
            # Trợ lý CSKH tự động trong nhóm @KingToolShopSupport
            if not text or event.out:
                return
            import re
            spx_match = re.search(r"\b(SPX[A-Z0-9]{4,10})\b", text.upper())
            if spx_match:
                code = spx_match.group(1)
                dep = db.find_deposit_by_code(code)
                if dep:
                    st_map = {
                        "pending": "⏳ **Đang chờ duyệt** — Bot đã gửi thông báo nhắc Admin kiểm tra ngay cho bạn!",
                        "approved": "✅ **Đã được duyệt & cộng tiền thành công** vào ví trên Bot!",
                        "rejected": "❌ **Đã bị từ chối** (Vui lòng gửi kèm ảnh biên lai chuyển khoản tại đây để CSKH kiểm tra lại).",
                        "expired": "⚠️ **Đã quá hạn 24h** — Hệ thống đã báo Admin kiểm tra thủ công cho bạn.",
                    }
                    await event.reply(
                        f"🤖 **[TRỢ LÝ CSKH TỰ ĐỘNG]**\n\n"
                        f"🧾 Tìm thấy đơn nạp: `#{dep['id']}` (Mã: `{code}`)\n"
                        f"💵 Số tiền: **{vnd_int(dep['amount_vnd']):,}đ**\n"
                        f"📌 Trạng thái: {st_map.get(dep['status'], dep['status'])}"
                    )
                    if dep["status"] == "pending":
                        amt_vnd = vnd_int(dep["amount_vnd"])
                        dep_uid = int(dep["user_id"])
                        dep_u = db.get_or_create_user(dep_uid)
                        for adm_id in ADMIN_IDS:
                            try:
                                await client.send_message(
                                    adm_id,
                                    f"🆘 **KHÁCH ĐANG NHẮN HỖ TRỢ ĐƠN NẠP #{dep['id']} TRÊN NHÓM CSKH**\n\n"
                                    f"👤 Khách hàng: {format_admin_user_line(dep_uid, dep_u)}\n"
                                    f"💵 Số tiền: **{amt_vnd:,}đ** | Nội dung: `{dep['memo']}`",
                                    buttons=[
                                        [
                                            Button.inline(f"✅ Duyệt +{amt_vnd:,}đ", f"adm:dep_ok:{dep['id']}".encode(), style="success"),
                                            Button.inline("❌ Từ chối", f"adm:dep_no:{dep['id']}".encode(), style="danger"),
                                        ],
                                        build_admin_user_buttons(dep_uid),
                                    ],
                                )
                            except Exception:
                                pass
                return

            ord_match = re.search(r"(?:#|đơn\s+|order\s+)(\d{1,6})\b", text, re.IGNORECASE)
            if ord_match:
                oid = int(ord_match.group(1))
                o = db.get_order(oid)
                if o:
                    await event.reply(
                        f"🤖 **[TRỢ LÝ CSKH TỰ ĐỘNG]**\n\n"
                        f"📦 Đơn hàng: `#{o['id']}` — **{o['product_name']}** (x{o['quantity']})\n"
                        f"💵 Thanh toán: **{vnd_int(o['retail_price']):,}đ**\n"
                        f"📌 Trạng thái: **{o['status'].upper()}** ({o['created_at']})\n"
                        f"⚡ *Đội ngũ CSKH đã nhận được thông tin và sẽ hỗ trợ bạn ngay!*"
                    )
            return

        if event.out:
            return
        if text.startswith("/"):
            if text.lower() == "/cancel":
                USER_AWAITING.pop(event.sender_id, None)
                u, lang = await get_user_info(event)
                await event.respond(
                    t(lang, "main_menu_title", balance=vnd_int(u["balance"]), points=u["points"]),
                    buttons=main_menu_buttons(lang, event.sender_id),
                )
            return

        uid = event.sender_id
        has_media = getattr(event, "media", None) is not None
        if not text and not has_media:
            return

        u, lang = await get_user_info(event)
        awaiting = USER_AWAITING.get(uid)

        # 1. Hỗ trợ Admin vuốt trả lời (Reply) trực tiếp vào bất kỳ tin nhắn nào có ID khách hàng như chat bình thường
        if is_admin(uid) and not awaiting and event.is_reply:
            try:
                import re

                reply_msg = await event.get_reply_message()
                reply_raw = (getattr(reply_msg, "raw_text", None) or "") if reply_msg else ""
                m_uid = re.search(r"(?:ID:\s*`?|Telegram ID:\s*`?|Khách\s+`?)(\d{6,15})", reply_raw)
                if not m_uid:
                    m_uid = re.search(r"\b(\d{8,15})\b", reply_raw)
                if m_uid:
                    target_uid = int(m_uid.group(1))
                    if not is_admin(target_uid):
                        tu = db.get_or_create_user(target_uid)
                        USER_AWAITING[uid] = {
                            "type": "admin_direct_msg",
                            "target_uid": target_uid,
                        }
                        body_txt = text or "*(Shop gửi hình ảnh / tệp đính kèm)*"
                        msg_md = (
                            f"💬 **TIN NHẮN TỪ KINGTOOL SHOP (@KingToolShop_bot)**\n\n"
                            f"{body_txt}\n\n"
                            "💡 *Bạn có thể nhắn trả lời trực tiếp ngay tại khung chat này hoặc bấm nút bên dưới:*"
                        )
                        msg_html = (
                            f"💬 <b>TIN NHẮN TỪ KINGTOOL SHOP (@KingToolShop_bot)</b>\n\n"
                            f"{body_txt}\n\n"
                            "💡 <i>Bạn có thể nhắn trả lời trực tiếp ngay tại khung chat này hoặc bấm nút bên dưới:</i>"
                        )
                        sent_ok = await send_message_to_user_safe(
                            client,
                            target_uid,
                            text_md=msg_md,
                            html_fallback=msg_html,
                            media=getattr(event, "media", None),
                            mirror_to_admin=True,
                            record_content=body_txt,
                        )
                        if not sent_ok:
                            await event.respond(
                                f"❌ Không thể gửi tin nhắn tới {format_admin_user_line(target_uid, tu)} (Khách có thể đã chặn Bot)."
                            )
                        return
            except Exception:
                pass

        # 2. Mọi khách hàng nhắn tin bình thường (hoặc gửi ảnh) vào Bot đều hiển thị ngay trên Telegram của Admin
        if not awaiting:
            if not is_admin(uid):
                await forward_customer_chat_to_admins(client, event, uid, u, lang, text)
            return

        atype = awaiting.get("type")

        if atype == "activation_email":
            if "@" not in text or "." not in text:
                await event.respond("❌ Email không hợp lệ. Vui lòng nhập lại địa chỉ Email (hoặc `/cancel`):")
                return
            USER_AWAITING.pop(uid, None)
            await execute_purchase(
                client,
                event,
                product_id=awaiting["product_id"],
                qty=int(awaiting["qty"]),
                activation_email=text,
            )
            return

        if atype == "custom_qty":
            max_q = int(awaiting.get("max_qty", 100))
            pid = awaiting["product_id"]
            try:
                q_val = int(text.strip())
                if q_val < 1 or q_val > max_q:
                    raise ValueError
            except ValueError:
                await event.respond(t(lang, "custom_qty_invalid", max_qty=max_q))
                return
            USER_AWAITING.pop(uid, None)
            await render_product_detail(event, pid, qty=q_val)
            return

        if atype == "apply_voucher":
            pid = awaiting["product_id"]
            qty_val = int(awaiting.get("qty", 1))
            v_code = text.strip().upper()
            ok, reason, _ = db.validate_voucher_for_user(v_code, uid)
            if not ok:
                err_key = {
                    "not_found": "voucher_err_not_found",
                    "inactive": "voucher_err_inactive",
                    "exhausted": "voucher_err_exhausted",
                    "already_used": "voucher_err_already_used",
                }.get(reason, "voucher_err_not_found")
                await event.respond(
                    t(lang, err_key, code=v_code),
                    buttons=[[Button.inline(t(lang, "btn_back"), f"qty:{pid}:{qty_val}".encode())]],
                )
                return
            USER_AWAITING.pop(uid, None)
            USER_ACTIVE_VOUCHER[uid] = v_code
            await render_product_detail(event, pid, qty=qty_val)
            return

        if atype == "custom_deposit":
            try:
                amt_vnd = parse_vnd_input(text)
                if amt_vnd < 10000:
                    raise ValueError
            except ValueError:
                await event.respond(t(lang, "custom_deposit_invalid"))
                return
            USER_AWAITING.pop(uid, None)
            await create_and_show_deposit(client, event, amt_vnd)
            return

        if atype == "user_reply_admin":
            USER_AWAITING.pop(uid, None)
            await forward_customer_chat_to_admins(client, event, uid, u, lang, text)
            return

        if atype == "warranty_request":
            oid = int(awaiting["order_id"])
            USER_AWAITING.pop(uid, None)
            o = db.get_order_by_id(oid, uid)
            if not o:
                return
            clean_keys = format_order_keys_preview(o.get("delivered_keys", ""))
            ps_oid = o.get("prodseller_order_id") or "N/A"
            for adm_id in ADMIN_IDS:
                try:
                    await client.send_message(
                        adm_id,
                        (
                            f"🛠️ **YÊU CẦU BẢO HÀNH ĐƠN HÀNG #{oid}**\n\n"
                            f"👤 Khách hàng: {format_admin_user_line(uid, u)}\n"
                            f"🛍️ Sản phẩm: **{o['product_name']}** (x{o['quantity']})\n"
                            f"🔗 Mã đơn ProdSeller: `{ps_oid}`\n"
                            f"🔑 Key đã giao: `{clean_keys}`\n"
                            f"📅 Ngày mua: `{o['created_at']}`\n\n"
                            f"📝 **Mô tả lỗi từ khách:**\n`{text}`"
                        ),
                        buttons=[
                            [
                                Button.inline(
                                    f"💬 Phản hồi / Đổi Key đơn #{oid}",
                                    f"adm:warr_reply:{uid}:{oid}".encode(),
                                    style="primary",
                                )
                            ],
                            build_admin_user_buttons(uid),
                        ],
                    )
                except Exception:
                    pass
            await event.respond(
                t(lang, "warr_sent", order_id=oid, issue=text),
                buttons=[[Button.inline(t(lang, "btn_back"), b"prof:orders")]],
            )
            return

        if not is_admin(uid):
            return

        if atype == "admin_direct_msg":
            target_uid = int(awaiting["target_uid"])
            # Giữ nguyên USER_AWAITING[uid] để Admin chat liên tục nhiều tin/ảnh trong phiên trò chuyện (@KingToolShop_bot đóng vai Shop)
            USER_AWAITING[uid] = {
                "type": "admin_direct_msg",
                "target_uid": target_uid,
            }
            tu = db.get_or_create_user(target_uid)
            body_txt = text or "*(Shop gửi hình ảnh / tệp đính kèm)*"
            msg_md = (
                f"💬 **TIN NHẮN TỪ KINGTOOL SHOP (@KingToolShop_bot)**\n\n"
                f"{body_txt}\n\n"
                "💡 *Bạn có thể nhắn trả lời trực tiếp ngay tại khung chat này hoặc bấm nút bên dưới:*"
            )
            msg_html = (
                f"💬 <b>TIN NHẮN TỪ KINGTOOL SHOP (@KingToolShop_bot)</b>\n\n"
                f"{body_txt}\n\n"
                "💡 <i>Bạn có thể nhắn trả lời trực tiếp ngay tại khung chat này hoặc bấm nút bên dưới:</i>"
            )
            sent_ok = await send_message_to_user_safe(
                client,
                target_uid,
                text_md=msg_md,
                html_fallback=msg_html,
                media=getattr(event, "media", None),
                mirror_to_admin=True,
                record_content=body_txt,
            )
            if not sent_ok:
                await event.respond(
                    f"❌ Không thể gửi tin nhắn tới {format_admin_user_line(target_uid, tu)} (Khách có thể đã chặn Bot).",
                    buttons=[
                        [Button.inline("👤 Hồ sơ khách", f"adm:uinfo:{target_uid}".encode())],
                        [Button.inline("🚪 Đóng phiên trò chuyện", b"adm:close_chat", style="danger")],
                    ],
                )
            return

        if atype == "admin_addbal_single":
            target_uid = int(awaiting["target_uid"])
            try:
                amt_vnd = parse_vnd_input(text)
                if amt_vnd == 0:
                    raise ValueError
            except ValueError:
                await event.respond(
                    "❌ Số tiền không hợp lệ. Vui lòng nhập số tiền VNĐ (ví dụ `50000`, `50k` hoặc `-20000`):",
                    buttons=[[Button.inline("« Hủy", f"adm:uinfo:{target_uid}".encode())]],
                )
                return
            USER_AWAITING.pop(uid, None)
            tu = db.get_or_create_user(target_uid)
            new_bal = db.adjust_balance(target_uid, amt_vnd)
            await event.respond(
                f"✅ Đã cập nhật **{amt_vnd:+,}đ** cho khách {format_admin_user_line(target_uid, tu)}.\n"
                f"💵 Số dư mới: **{new_bal:,}đ**"
            )
            try:
                await client.send_message(
                    target_uid,
                    f"💰 Số dư ví của bạn vừa được cập nhật **{amt_vnd:+,}đ**.\n💵 Số dư hiện tại: **{new_bal:,}đ**",
                )
            except Exception:
                pass
            await render_admin_user_detail(client, event, target_uid, force_new=True)
            return

        if atype == "admin_bsrc_add":
            pid = awaiting["product_id"]
            lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
            if len(lines) < 2 or "|" not in lines[0]:
                await event.respond(
                    "❌ Sai cú pháp! Dòng 1 phải là `TÊN_NGUỒN | GIÁ_VỐN_VNĐ`, và từ dòng 2 trở đi là danh sách Key (mỗi dòng 1 Key):",
                    buttons=[[Button.inline("« Hủy", f"adm:editp:{pid}".encode())]],
                )
                return
            header_parts = [x.strip() for x in lines[0].split("|", 1)]
            src_name = header_parts[0] or "Bot Dự Phòng"
            try:
                cost_vnd = parse_vnd_input(header_parts[1])
                if cost_vnd <= 0:
                    raise ValueError
            except ValueError:
                await event.respond(
                    "❌ Giá vốn VNĐ ở dòng 1 không hợp lệ (Ví dụ: `BotKho2 | 35000` hoặc `BotKho2 | 35k`):",
                    buttons=[[Button.inline("« Hủy", f"adm:editp:{pid}".encode())]],
                )
                return
            keys_list = lines[1:]
            USER_AWAITING.pop(uid, None)
            src_info, added_cnt = db.add_or_append_local_backup_source(pid, src_name, cost_vnd, keys_list)
            p = await ps_client.get_product_by_id(pid, refresh=False)
            cost_usd = float(p["price"]) if p else (cost_vnd / 25500.0)
            p_base_vnd = db.compute_primary_base_price(pid, cost_usd)
            stab_price = db.compute_stabilized_unit_price(p_base_vnd, cost_vnd)
            prof_pct = ((stab_price - cost_vnd) / cost_vnd * 100.0) if cost_vnd > 0 else 200.0
            await event.respond(
                f"✅ Đã nạp thành công **{added_cnt} key mới** vào nguồn **`{src_name}`** (Tổng tồn nguồn này: **{src_info.get('available_stock', 0)} key**)!\n"
                f"📉 Giá vốn nguồn này: **`{cost_vnd:,}đ`**\n"
                f"🛡️ Giá bán bình ổn khi cấp từ nguồn này: **`{stab_price:,}đ`** *(Lãi `+{stab_price - cost_vnd:,}đ` = `+{prof_pct:.0f}%`)*"
            )
            await render_admin_edit_product(event, pid)
            return

        if atype == "admin_bsrc_api":
            pid = awaiting["product_id"]
            parts = [x.strip() for x in text.split("|")]
            if len(parts) < 5:
                await event.respond(
                    "❌ Sai cú pháp! Hãy nhập đủ 5 phần cách nhau bởi dấu `|`:\n"
                    "`TÊN_NGUỒN | GIÁ_VỐN_VNĐ | BASE_URL | API_KEY | MÃ_SP_BÊN_ĐÓ`",
                    buttons=[[Button.inline("« Hủy", f"adm:editp:{pid}".encode())]],
                )
                return
            src_name, cost_raw, base_url, api_key, remote_pid = parts[0], parts[1], parts[2], parts[3], parts[4]
            try:
                cost_vnd = parse_vnd_input(cost_raw)
                if cost_vnd <= 0:
                    raise ValueError
            except ValueError:
                await event.respond(
                    "❌ Giá vốn VNĐ không hợp lệ (ví dụ: `35000` hoặc `35k`):",
                    buttons=[[Button.inline("« Hủy", f"adm:editp:{pid}".encode())]],
                )
                return
            USER_AWAITING.pop(uid, None)
            init_stock = 10
            remote_info = await ps_client.fetch_external_api_product(base_url, api_key, remote_pid)
            if remote_info:
                init_stock = int(remote_info.get("stock", 0) or 0) if remote_info.get("inStock") else 0
            src_info = db.add_api_backup_source(
                product_id=pid,
                source_name=src_name,
                cost_vnd=cost_vnd,
                api_base_url=base_url,
                api_key=api_key,
                remote_product_id=remote_pid,
                remote_stock=init_stock,
            )
            p = await ps_client.get_product_by_id(pid, refresh=False)
            cost_usd = float(p["price"]) if p else (cost_vnd / 25500.0)
            p_base_vnd = db.compute_primary_base_price(pid, cost_usd)
            stab_price = db.compute_stabilized_unit_price(p_base_vnd, cost_vnd)
            prof_pct = ((stab_price - cost_vnd) / cost_vnd * 100.0) if cost_vnd > 0 else 200.0
            await event.respond(
                f"🔌 Đã kết nối nguồn API dự phòng **`{src_name}`** (`#{src_info.get('id', 1)}`)!\n"
                f"📦 Tồn kho đồng bộ: **{init_stock}** | Giá vốn: **`{cost_vnd:,}đ`**\n"
                f"🛡️ Giá bán bình ổn khi cấp từ nguồn này: **`{stab_price:,}đ`** *(Lãi `+{stab_price - cost_vnd:,}đ` = `+{prof_pct:.0f}%`)*"
            )
            await render_admin_edit_product(event, pid)
            return

        if atype == "admin_warr_reply":
            target_uid = int(awaiting["target_uid"])
            oid = int(awaiting["order_id"])
            USER_AWAITING.pop(uid, None)
            body_txt = text or "*(Admin gửi hình ảnh / tệp bảo hành)*"
            msg_md = (
                f"🛠️ **PHẢN HỒI BẢO HÀNH ĐƠN HÀNG `#{oid}`**\n\n"
                f"{body_txt}\n\n"
                "💚 *Cảm ơn bạn đã tin tưởng sử dụng dịch vụ tại KingTool Shop! Bạn có thể nhắn trực tiếp tại đây nếu cần hỗ trợ thêm.*"
            )
            msg_html = (
                f"🛠️ <b>PHẢN HỒI BẢO HÀNH ĐƠN HÀNG <code>#{oid}</code></b>\n\n"
                f"{body_txt}\n\n"
                "💚 <i>Cảm ơn bạn đã tin tưởng sử dụng dịch vụ tại KingTool Shop! Bạn có thể nhắn trực tiếp tại đây nếu cần hỗ trợ thêm.</i>"
            )
            sent_ok = await send_message_to_user_safe(
                client,
                target_uid,
                text_md=msg_md,
                html_fallback=msg_html,
                media=getattr(event, "media", None),
                mirror_to_admin=True,
                record_content=body_txt,
            )
            if not sent_ok:
                await event.respond(
                    f"❌ Không thể gửi phản hồi bảo hành tới `{target_uid}` (Khách có thể đã chặn Bot).",
                    buttons=[[Button.inline("« Về Bảng Admin", b"adm:home")]],
                )
            return

        if atype == "admin_vch_add":
            raw_parts = [p.strip() for p in (text.split("|") if "|" in text else text.split())]
            if len(raw_parts) < 2:
                await event.respond(
                    "❌ Sai cú pháp! Hãy nhập: `MÃ_CODE | MỨC_GIẢM | SỐ_LƯỢT_TỐI_ĐA`\n"
                    "Ví dụ: `SALE20 | 20% | 50` hoặc `GIAM15K | 15k | 20`",
                    buttons=[[Button.inline("« Hủy", b"adm:vouchers")]],
                )
                return
            v_code = "".join(ch for ch in raw_parts[0].upper() if ch.isalnum() or ch in ("_", "-"))
            disc_raw = raw_parts[1].strip()
            max_u_str = raw_parts[2].strip() if len(raw_parts) >= 3 else "0"
            try:
                if not v_code:
                    raise ValueError
                if disc_raw.endswith("%"):
                    dtype = "percent"
                    dval = float(disc_raw[:-1].replace(",", ".").strip())
                    if dval <= 0 or dval >= 100:
                        raise ValueError
                else:
                    dtype = "fixed"
                    dval = float(parse_vnd_input(disc_raw))
                    if dval <= 0:
                        raise ValueError
                max_uses = max(0, int(float(max_u_str)))
            except ValueError:
                await event.respond(
                    "❌ Dữ liệu không hợp lệ! Vui lòng kiểm tra lại mức giảm (`15%` hoặc `15k`) và số lượt (`0` = không giới hạn):",
                    buttons=[[Button.inline("« Hủy", b"adm:vouchers")]],
                )
                return
            USER_AWAITING.pop(uid, None)
            db.create_or_update_voucher(v_code, dtype, dval, max_uses)
            disc_label = f"-{dval:g}%" if dtype == "percent" else f"-{int(round(dval)):,}đ"
            limit_label = f"{max_uses} lượt" if max_uses > 0 else "Không giới hạn tổng lượt"
            await event.respond(
                f"✅ Đã tạo mã giảm giá **`{v_code}`** (Giảm **{disc_label}** | Tối đa: **{limit_label}** | Mỗi khách 1 lần)!"
            )
            await render_admin_vouchers(event, force_new=True)
            return

        if atype == "admin_finduser":
            USER_AWAITING.pop(uid, None)
            found = db.find_user(text)
            if not found:
                await event.respond(
                    f"❌ Không tìm thấy khách hàng nào khớp với `{text}`.",
                    buttons=[
                        [
                            Button.inline("🔍 Thử tìm lại", b"adm:finduser", style="primary"),
                            Button.inline("👥 Danh sách khách", b"adm:userlist:0"),
                        ],
                        [
                            Button.inline("« Về Thư mục Khách Hàng", b"adm:dir:users"),
                            Button.inline("⚙️ Bảng Admin", b"adm:home"),
                        ],
                    ],
                )
                return
            f_uid = int(found["telegram_id"])
            await render_admin_user_detail(client, event, f_uid, force_new=True)
            return

        if atype == "admin_broadcast":
            USER_AWAITING.pop(uid, None)
            user_ids = db.get_all_user_ids()
            status_m = await event.respond(f"⏳ Đang gửi thông báo tới **{len(user_ids)}** khách hàng...")
            sent_ok = 0
            for tid in user_ids:
                try:
                    await client.send_message(tid, f"📣 **THÔNG BÁO TỪ SHOP**\n\n{text}")
                    sent_ok += 1
                    await asyncio.sleep(0.05)
                except Exception:
                    pass
            await status_m.edit(
                f"✅ Đã gửi thông báo thành công tới **{sent_ok}/{len(user_ids)}** khách hàng!",
                buttons=[
                    [
                        Button.inline("« Về Thư mục Khách Hàng", b"adm:dir:users"),
                        Button.inline("⚙️ Bảng Admin", b"adm:home"),
                    ]
                ],
            )
            return

        if atype == "set_product_price":
            pid = awaiting["product_id"]
            try:
                new_price_vnd = parse_vnd_input(text)
                if new_price_vnd <= 0:
                    raise ValueError
            except ValueError:
                await event.respond("❌ Giá không hợp lệ. Vui lòng nhập số tiền VNĐ (ví dụ `35000` hoặc `35k`):")
                return
            USER_AWAITING.pop(uid, None)
            db.set_product_custom_price(pid, float(new_price_vnd))
            await event.respond(f"✅ Đã đặt giá bán riêng cho `{pid}` = **{new_price_vnd:,}đ**!")
            await render_admin_edit_product(event, pid)
            return

        if atype == "set_setting":
            key = awaiting["key"]
            if key in ("markup_percent", "min_profit_percent", "markup_fixed", "vnd_rate", "low_balance_threshold_usd"):
                cleaned = text.lower().replace("%", "").replace("$", "").replace("đ", "").replace("vnd", "").replace(",", "").strip()
                try:
                    val = float(cleaned)
                    db.set_setting(key, str(val))
                except ValueError:
                    await event.respond("❌ Giá trị số không hợp lệ, vui lòng nhập lại:")
                    return
            elif key in ("sepay_api_token", "dante_api_key") and text.strip().lower() == "off":
                db.set_setting(key, "")
            else:
                db.set_setting(key, text.strip())
                if key == "dante_api_key":
                    try:
                        d_url = (db.get_setting("dante_base_url", DANTE_BASE_URL) or DANTE_BASE_URL).strip()
                        await ps_client.sync_all_dante_backups(db, text.strip(), d_url, auto_seed_defaults=True)
                    except Exception:
                        pass
            USER_AWAITING.pop(uid, None)
            await event.respond(f"✅ Đã cập nhật `{key}` thành công!")
            parent_folder = SETTING_PARENT_FOLDER.get(key)
            if parent_folder:
                await render_admin_folder(event, parent_folder, force_new=True)
            else:
                await render_admin_home(event, force_new=True)
            return

        if atype == "set_bank":
            parts = [p.strip() for p in text.split("|")]
            if len(parts) != 3:
                await event.respond("❌ Sai cú pháp! Hãy nhập: `MÃ_NGÂN_HÀNG | SỐ_TK | TÊN_CHỦ_TK`")
                return
            db.set_setting("bank_id", parts[0].upper())
            db.set_setting("bank_account_no", parts[1])
            db.set_setting("bank_account_name", parts[2].upper())
            USER_AWAITING.pop(uid, None)
            await event.respond("✅ Đã cập nhật thông tin Ngân hàng VietQR!")
            await render_admin_folder(event, "payment", force_new=True)
            return

        if atype == "admin_addbal":
            parts = text.split()
            if len(parts) != 2:
                await event.respond("❌ Hãy nhập: `TELEGRAM_ID SỐ_TIỀN_VNĐ`")
                return
            try:
                tid = int(parts[0])
                amt_vnd = parse_vnd_input(parts[1])
            except ValueError:
                await event.respond("❌ ID hoặc số tiền không hợp lệ.")
                return
            USER_AWAITING.pop(uid, None)
            db.get_or_create_user(tid)
            new_bal = db.adjust_balance(tid, amt_vnd)
            await event.respond(f"✅ Đã cập nhật **{amt_vnd:+,}đ** cho `{tid}`. Số dư mới: **{new_bal:,}đ**")
            try:
                await client.send_message(
                    tid,
                    f"💰 Số dư ví của bạn vừa được cập nhật **{amt_vnd:+,}đ**.\n💵 Số dư hiện tại: **{new_bal:,}đ**",
                )
            except Exception:
                pass
            await render_admin_folder(event, "users", force_new=True)
            return

    await client.run_until_disconnected()


if __name__ == "__main__":
    try:
        asyncio.run(run_bot())
    except KeyboardInterrupt:
        logger.info("Đã dừng Bot theo yêu cầu người dùng.")
