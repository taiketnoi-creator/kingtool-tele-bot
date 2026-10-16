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
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from telethon import Button, TelegramClient, events

from database import TIER_DISCOUNTS, Database
from i18n import LANGUAGES, localize_product_description, t
from prodseller_client import (
    GROUP_EMOJI,
    GROUP_ICONS,
    ProdSellerClient,
    detect_plan_group,
    get_product_icon_and_prefix,
    stock_badge,
)

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
ps_client = ProdSellerClient(os.getenv("PRODSELLER_API_KEY", ""))
ADMIN_IDS: set[int] = {
    int(x.strip())
    for x in os.getenv("ADMIN_TELEGRAM_IDS", "8110826820").split(",")
    if x.strip().isdigit()
}

USER_AWAITING: dict[int, dict[str, Any]] = {}
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
    rows = [
        [
            Button.inline(t(lang, "btn_products"), b"menu:products", style="success"),
            Button.inline(t(lang, "btn_balance"), b"menu:balance"),
        ],
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
    if is_admin(user_id):
        rows.append([Button.inline("⚙️ Quản trị Admin (Giá & Duyệt Nạp)", b"adm:home", style="primary")])
    return rows


async def get_user_info(event: Any) -> tuple[dict[str, Any], str]:
    sender = await event.get_sender()
    uid = event.sender_id
    uname = getattr(sender, "username", None) or getattr(sender, "first_name", None) or ""
    u = db.get_or_create_user(uid, uname)
    return u, u.get("language", "vi")


async def send_or_edit(event: Any, text: str, buttons: list[list[Any]] | None = None, force_new: bool = False) -> Any:
    """Tự động sửa tin nhắn hiện tại, hoặc nếu tin nhắn hiện tại là ảnh (như ảnh QR VietQR)
    thì xóa ảnh đi và gửi tin nhắn văn bản mới để không bị dính ảnh QR trên các menu sau.
    """
    if not force_new and hasattr(event, "edit"):
        try:
            msg = await event.get_message()
            if msg and getattr(msg, "media", None) is not None:
                try:
                    await event.delete()
                except Exception:
                    pass
                return await event.respond(text, buttons=buttons)
            return await event.edit(text, buttons=buttons)
        except Exception:
            pass
    return await event.respond(text, buttons=buttons)


# ==================== PRODUCTS & SUB-PLANS (HIỂN THỊ VNĐ) ====================
async def render_products_menu(event: Any, group_filter: str | None = None) -> None:
    u, lang = await get_user_info(event)
    tier = u.get("tier", "bronze")
    try:
        products = await ps_client.sync_products(force=False)
    except Exception as exc:
        logger.error("Lỗi đồng bộ sản phẩm: %s", exc)
        if hasattr(event, "answer"):
            await event.answer("❌ Không thể tải danh sách sản phẩm lúc này.", alert=True)
        return

    overrides = db.get_all_overrides()
    rows: list[list[Any]] = []
    seen_groups: set[str] = set()

    group_stats: dict[str, dict[str, int]] = {}
    for p in products:
        ov = overrides.get(p["id"], {})
        if ov.get("hidden"):
            continue
        g = detect_plan_group(p["name"])
        if g:
            st = group_stats.setdefault(g, {"plans": 0, "stock": 0})
            st["plans"] += 1
            if p.get("inStock") and isinstance(p.get("stock"), int):
                st["stock"] += int(p["stock"])

    owner_premium = os.getenv("OWNER_HAS_PREMIUM", "false").lower()
    use_fallback = owner_premium != "true"

    for p in products:
        pid = p["id"]
        ov = overrides.get(pid, {})
        if ov.get("hidden"):
            continue
        g = detect_plan_group(p["name"])

        if group_filter:
            if g != group_filter:
                continue
        else:
            if g:
                if g not in seen_groups:
                    seen_groups.add(g)
                    st = group_stats[g]
                    grp_emoji = GROUP_EMOJI.get(g, "📂 ") if use_fallback else ""
                    label = f"{grp_emoji}{g} ▸ {st['plans']} {t(lang, 'plans_label')} ({st['stock']}) »"
                    grp_icon = GROUP_ICONS.get(g)
                    rows.append([
                        Button.inline(
                            label,
                            f"grp:{g}".encode(),
                            style="primary",
                            icon=grp_icon,
                        )
                    ])
                continue

        _, unit_vnd, _ = db.compute_tier_unit_price(pid, float(p["price"]), tier, overrides)
        in_stock = bool(p.get("inStock")) and (p.get("stock") is None or int(p.get("stock", 0)) > 0)
        badge = stock_badge(p.get("stock"), bool(p.get("inStock")))
        icon_id, prefix = get_product_icon_and_prefix(p["name"], use_fallback_emoji=use_fallback)
        btn_style = "success" if in_stock else "danger"
        btn_label = f"{prefix}{p['name'].strip()} | {unit_vnd:,}đ | {badge}"
        rows.append([
            Button.inline(
                btn_label,
                f"prd:{pid}".encode(),
                style=btn_style,
                icon=icon_id,
            )
        ])

    back_target = b"menu:products" if group_filter else b"menu:home"
    rows.append([Button.inline(t(lang, "btn_back"), back_target)])

    header = t(lang, "products_title")
    if group_filter:
        header = f"{header}\n\n{group_filter}"

    await send_or_edit(event, header, buttons=rows)


async def render_product_detail(event: Any, product_id: str, qty: int = 1) -> None:
    u, lang = await get_user_info(event)
    tier = u.get("tier", "bronze")
    p = await ps_client.get_product_by_id(product_id, refresh=True)
    if not p:
        if hasattr(event, "answer"):
            await event.answer("❌ Không tìm thấy sản phẩm.", alert=True)
        return

    base_vnd, unit_retail_vnd, disc_pct = db.compute_tier_unit_price(product_id, float(p["price"]), tier)
    total_retail_vnd = unit_retail_vnd * qty
    cost_vnd = db.compute_wholesale_vnd(float(p["price"]))
    in_stock = bool(p.get("inStock"))
    stock_num = p.get("stock")
    stock_str = (
        t(lang, "stock_keys_unit", n=stock_num)
        if isinstance(stock_num, int)
        else (t(lang, "stock_available") if in_stock else t(lang, "stock_zero"))
    )
    desc = localize_product_description(product_id, p.get("description") or "", lang)

    price_line = f"{t(lang, 'price_label')}: **{unit_retail_vnd:,}đ**"
    if qty > 1:
        price_line += f" (x{qty} = **{total_retail_vnd:,}đ**)"
    if disc_pct > 0 and unit_retail_vnd < base_vnd:
        price_line += "\n" + t(
            lang,
            "tier_discount_note",
            tier=tier.upper(),
            disc_pct=disc_pct,
            base_price=base_vnd,
            unit_price=unit_retail_vnd,
        )

    text = (
        f"🛍️ **{p['name'].strip()}**\n\n"
        f"{desc}\n\n"
        f"{price_line}\n"
        f"{t(lang, 'in_stock_label')}: **{stock_str}**"
    )

    grp = detect_plan_group(p["name"])
    back_cb = f"grp:{grp}".encode() if grp else b"menu:products"

    rows: list[list[Any]] = []
    if in_stock and (stock_num is None or stock_num >= 1):
        if isinstance(stock_num, int) and qty > stock_num:
            qty = max(1, stock_num)
            total_retail_vnd = unit_retail_vnd * qty

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

        rows.append([
            Button.inline(
                t(lang, "buy_btn", price=total_retail_vnd),
                f"buy:{product_id}:{qty}".encode(),
                style="success",
            )
        ])
    else:
        rows.append([Button.inline(t(lang, "out_of_stock_btn"), b"noop", style="danger")])

    if is_admin(u["telegram_id"]):
        rows.append([
            Button.inline(
                f"⚙️ Vốn: {cost_vnd:,}đ | Sửa giá bán ({base_vnd:,}đ)",
                f"adm:editp:{product_id}".encode(),
                style="primary",
            )
        ])

    rows.append([Button.inline(t(lang, "btn_back"), back_cb)])
    await send_or_edit(event, text, buttons=rows)


# ==================== BUY & AUTO-FULFILLMENT (VNĐ + CHỐNG RACE CONDITION) ====================
async def execute_purchase(
    client: TelegramClient,
    event: Any,
    product_id: str,
    qty: int,
    activation_email: str | None = None,
) -> None:
    u, lang = await get_user_info(event)
    uid = u["telegram_id"]

    lock = USER_PURCHASE_LOCKS.setdefault(uid, asyncio.Lock())
    if lock.locked():
        if hasattr(event, "answer"):
            await event.answer(t(lang, "order_busy"), alert=True)
        else:
            await event.respond(t(lang, "order_busy"))
        return

    async with lock:
        p = await ps_client.get_product_by_id(product_id, refresh=True)
        if not p or not p.get("inStock"):
            await event.respond(t(lang, "out_of_stock_btn"))
            return

        stock_num = p.get("stock")
        if isinstance(stock_num, int) and stock_num < qty:
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

        fresh_user = db.get_or_create_user(uid)
        tier = fresh_user.get("tier", "bronze")
        unit_cost_usd = float(p["price"])
        _, unit_retail_vnd, _ = db.compute_tier_unit_price(product_id, unit_cost_usd, tier)
        total_cost_vnd = db.compute_wholesale_vnd(unit_cost_usd * qty)
        total_retail_vnd = unit_retail_vnd * qty

        # Trừ số dư VNĐ nguyên tử (Atomic SQLite check + deduct)
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
            order_resp = await ps_client.create_order(
                product_id=product_id,
                quantity=qty,
                email=activation_email,
                idempotency_key=idem_key,
            )
        except Exception as exc:
            # Hoàn tiền tự động nếu kho gốc hết hàng hoặc tài khoản đại lý hết vốn
            db.adjust_balance(uid, total_retail_vnd)
            logger.error("Lỗi mua hàng từ ProdSeller API: %s", exc)
            await status_msg.edit(
                t(lang, "order_failed_refunded", refund=total_retail_vnd, err=str(exc))
            )
            for adm_id in ADMIN_IDS:
                try:
                    await client.send_message(
                        adm_id,
                        (
                            f"⚠️ **CẢNH BÁO LỖI ĐƠN HÀNG**\n\n"
                            f"👤 Khách: `{uid}` (@{u['username']})\n"
                            f"🛍️ SP: **{p['name']}** (x{qty})\n"
                            f"💵 Giá vốn cần trừ bên ProdSeller: **{total_cost_vnd:,}đ** (`${unit_cost_usd * qty:.2f}`)\n"
                            f"❌ Lỗi từ ProdSeller API: `{exc}`\n"
                            f"*(Hãy kiểm tra số dư USDT của bạn bên @ProdSellerBot!)*"
                        ),
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
        actual_cost_usd = float(order_resp.get("amount", unit_cost_usd * qty))
        actual_cost_vnd = db.compute_wholesale_vnd(actual_cost_usd)

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
        for adm_id in ADMIN_IDS:
            try:
                await client.send_message(
                    adm_id,
                    (
                        f"🎉 **ĐƠN HÀNG MỚI #{local_order_id}**\n\n"
                        f"👤 Khách: `{uid}` (@{u['username']})\n"
                        f"🛍️ Sản phẩm: **{p['name']}** (x{qty})\n"
                        f"💰 Giá bán: **{total_retail_vnd:,}đ**\n"
                        f"📉 Giá vốn ProdSeller: **{actual_cost_vnd:,}đ** (`${actual_cost_usd:.2f}`)\n"
                        f"💵 **Lợi nhuận ròng: +{profit_vnd:,}đ**"
                    ),
                )
            except Exception:
                pass

        asyncio.create_task(
            post_order_social_proof(
                client,
                order_id=local_order_id,
                uid=uid,
                product_name=p["name"],
                qty=qty,
                total_vnd=total_retail_vnd,
            )
        )


# ==================== TỰ ĐỘNG ĐĂNG KÊNH @KingToolShopOfficial ====================
async def post_order_social_proof(
    client: TelegramClient,
    order_id: int,
    uid: int,
    product_name: str,
    qty: int,
    total_vnd: int,
) -> None:
    """Tự động đăng thông báo khách mua hàng thành công (ẩn danh ID) lên kênh @KingToolShopOfficial."""
    try:
        ch_name = db.get_setting("support_channel", "KingToolShopOfficial").lstrip("@").strip()
        if not ch_name:
            return
        uid_s = str(uid)
        masked_uid = f"{uid_s[:4]}***{uid_s[-2:]}" if len(uid_s) > 5 else f"{uid_s[:2]}***"
        support_name = db.get_setting("support_admin", "KingToolShopSupport").lstrip("@").strip()
        text = (
            f"⚡ **ĐƠN HÀNG TỰ ĐỘNG #{order_id} HOÀN TẤT**\n\n"
            f"👤 Khách hàng: `{masked_uid}`\n"
            f"🛍️ Sản phẩm: **{product_name.strip()}** (x{qty})\n"
            f"💵 Thanh toán: **{total_vnd:,}đ**\n"
            f"✅ Trạng thái: **Đã trả tài khoản tự động trong 2 giây!**"
        )
        rows = [
            [
                Button.url("🛒 Mua Hàng Tự Động 24/7", f"https://t.me/{BOT_USERNAME_CACHE}"),
                Button.url("🆘 Hỗ Trợ CSKH", f"https://t.me/{support_name}"),
            ]
        ]
        await client.send_message(ch_name, text, buttons=rows)
    except Exception as exc:
        logger.debug("Không thể đăng social proof lên kênh: %s", exc)


async def post_catalog_to_channel(client: TelegramClient, pin: bool = True) -> int | None:
    """Tổng hợp bảng giá VNĐ + tồn kho toàn bộ sản phẩm đang bán và đăng lên @KingToolShopOfficial."""
    ch_name = db.get_setting("support_channel", "KingToolShopOfficial").lstrip("@").strip()
    support_name = db.get_setting("support_admin", "KingToolShopSupport").lstrip("@").strip()
    products = await ps_client.sync_products(force=False)
    overrides = db.get_all_overrides()

    in_stock_lines: list[str] = []
    for p in products:
        pid = p["id"]
        ov = overrides.get(pid, {})
        if ov.get("hidden"):
            continue
        in_stock = bool(p.get("inStock")) and (p.get("stock") is None or int(p.get("stock", 0)) > 0)
        if not in_stock:
            continue
        price_vnd = db.compute_retail_price(pid, float(p["price"]), overrides)
        st = p.get("stock")
        st_txt = f"Còn {st}" if isinstance(st, int) else "Sẵn hàng"
        in_stock_lines.append(f"🟢 **{p['name'].strip()}** — `{price_vnd:,}đ` *({st_txt})*")

    catalog_block = "\n".join(in_stock_lines[:25]) if in_stock_lines else "Đang cập nhật kho hàng..."
    text = (
        "👑 **KINGTOOL SHOP — HỆ THỐNG PHÂN PHỐI TÀI KHOẢN & KEY AI TỰ ĐỘNG 24/7** 👑\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "✅ **Giao dịch tự động 100% qua Bot** — Nhận tài khoản/key ngay sau 2 giây!\n"
        "✅ **Thanh toán VietQR nội địa** — Quét QR tự động điền số tiền & nội dung.\n"
        "✅ **Bảo hành uy tín 1 đổi 1** — Đội ngũ CSKH hỗ trợ 24/7.\n"
        "✅ **Đặc quyền thành viên:** Giảm **3% (Hạng Silver)**, **5% (Hạng Gold)**, tích điểm đổi tiền & nhận **+5% Hoa hồng giới thiệu bạn bè**!\n\n"
        "🔥 **BẢNG GIÁ SẢN PHẨM ĐANG SẴN HÀNG:**\n"
        f"{catalog_block}\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"🤖 **Bot mua hàng tự động:** @{BOT_USERNAME_CACHE}\n"
        f"🆘 **Trung tâm Hỗ trợ CSKH:** @{support_name}"
    )
    rows = [
        [Button.url("🛒 MỞ BOT MUA HÀNG TỰ ĐỘNG NGAY", f"https://t.me/{BOT_USERNAME_CACHE}")],
        [Button.url("🆘 Trung Tâm Hỗ Trợ & Bảo Hành (CSKH)", f"https://t.me/{support_name}")],
    ]
    msg = await client.send_message(ch_name, text, buttons=rows)
    if pin and msg:
        try:
            await client.pin_message(ch_name, msg.id, notify=False)
        except Exception:
            pass
    return msg.id if msg else None



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
    rows: list[list[Any]] = []
    for i in range(0, len(amounts_vnd), 2):
        pair = amounts_vnd[i : i + 2]
        row = []
        for vnd in pair:
            lbl = f"{vnd:,}đ"
            row.append(Button.inline(lbl, f"dep:create:vietqr:{vnd}".encode(), style="success"))
        rows.append(row)
    rows.append([Button.inline(t(lang, "custom_amount_btn"), b"dep:custom:vietqr", style="primary")])
    rows.append([Button.inline(t(lang, "btn_back"), b"menu:deposit")])
    await send_or_edit(event, t(lang, "deposit_choose_amount"), buttons=rows)


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
        [Button.inline(t(lang, "btn_back"), b"menu:deposit")],
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
    new_bal = db.adjust_balance(dep["user_id"], amt_vnd)
    await reward_referrer_on_deposit(client, dep)

    target_user = db.get_or_create_user(int(dep["user_id"]))
    u_lang = target_user.get("language", "vi")
    try:
        await client.send_message(
            dep["user_id"],
            t(u_lang, "deposit_approved_msg", dep_id=dep_id, amt_vnd=amt_vnd, new_bal=new_bal),
        )
    except Exception:
        pass

    quota_warn = (
        f"\n⚠️ **Chú ý:** Đã chạm mốc **{new_used}/{limit}** giao dịch miễn phí của SePay trong tháng này. "
        f"Từ đơn tiếp theo hệ thống sẽ tự động chuyển về **Duyệt Bằng Tay**!"
        if new_used >= limit
        else ""
    )
    for adm_id in ADMIN_IDS:
        try:
            await client.send_message(
                adm_id,
                (
                    f"🌙 **[SEPAY TỰ ĐỘNG DUYỆT BAN ĐÊM #{dep_id}]**\n\n"
                    f"👤 Khách: `{dep['user_id']}` (@{dep['username']})\n"
                    f"💵 Đã cộng tự động: **+{amt_vnd:,}đ** (Số dư mới: **{new_bal:,}đ**)\n"
                    f"📊 Lượt SePay Free đã dùng tháng này: **{new_used}/{limit} giao dịch**"
                    f"{quota_warn}"
                ),
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


async def poll_products_sync_loop() -> None:
    """Đồng bộ danh mục sản phẩm và tồn kho ngầm mỗi 60 giây để khách bấm menu phản hồi tức thì."""
    while True:
        await asyncio.sleep(60)
        try:
            await ps_client.sync_products(force=True)
        except Exception as exc:
            logger.debug("Lỗi đồng bộ sản phẩm định kỳ: %s", exc)


# ==================== ADMIN PANEL (VNĐ) ====================
async def render_admin_home(event: Any, force_new: bool = False) -> None:
    uid = event.sender_id
    if not is_admin(uid):
        return
    USER_AWAITING.pop(uid, None)
    stats = db.get_summary_stats()
    settings = db.get_all_settings()
    rate = float(settings.get("vnd_rate", "25500") or 25500.0)

    ps_bal_str = "Đang kiểm tra..."
    try:
        b_info = await ps_client.get_balance()
        ps_usd = float(b_info.get("balance", 0.0))
        ps_vnd = int(round(ps_usd * rate))
        ps_bal_str = f"{ps_vnd:,}đ (${ps_usd:.2f} | Hạng: {b_info.get('membership', 'bronze')})"
    except Exception as exc:
        ps_bal_str = f"Lỗi kết nối ({exc})"

    used_sp, limit_sp, can_sp = db.get_sepay_quota_status()
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

    fixed_val = vnd_int(settings.get("markup_fixed", "0"))
    pending_cnt = stats.get("pending_deposits_count", 0)
    text = (
        "⚙️ **BẢNG ĐIỀU KHIỂN ADMIN (RESELLER PANEL)**\n\n"
        f"🏦 **Vốn bên @ProdSellerBot:** `{ps_bal_str}`\n"
        f"👥 Tổng khách hàng: **{stats['users_count']}** | 📦 Tổng đơn: **{stats['orders_count']}**\n"
        f"⏳ Đơn nạp đang chờ duyệt: **{pending_cnt}**\n"
        f"💰 Tổng doanh thu: **{vnd_int(stats['total_revenue']):,}đ**\n"
        f"📉 Tổng giá vốn: **{vnd_int(stats['total_cost']):,}đ**\n"
        f"💵 **Lợi nhuận ròng: +{vnd_int(stats['total_profit']):,}đ**\n\n"
        "🔧 **Cấu hình Giá & Ngân hàng hiện tại:**\n"
        f"• Tăng giá tự động (Markup %): **+{settings['markup_percent']}%**\n"
        f"• Cộng thêm cố định (Markup VNĐ): **+{fixed_val:,}đ**\n"
        f"• Tỷ giá quy đổi vốn: **$1 = {int(rate):,}đ**\n"
        f"• Hoa hồng giới thiệu: **+{settings.get('referral_commission_pct', '5.0')}%**\n"
        f"• VietQR: **{settings['bank_id']} - {settings['bank_account_no']} ({settings['bank_account_name']})**\n"
        f"• 🌙 SePay (23h-06h): **{sepay_status}**"
    )

    rows = [
        [
            Button.inline(f"⏳ Đơn nạp chờ duyệt ({pending_cnt})", b"adm:deplist", style="success" if pending_cnt > 0 else None),
            Button.inline("📦 10 Đơn gần nhất", b"adm:orders"),
        ],
        [
            Button.inline("🔍 Tra cứu Khách hàng", b"adm:finduser"),
            Button.inline("📣 Gửi thông báo (Broadcast)", b"adm:broadcast"),
        ],
        [
            Button.inline("📢 Đăng Bảng Giá lên @KingToolShopOfficial", b"adm:post_catalog", style="success"),
        ],
        [
            Button.inline("🏷️ Chỉnh giá riêng / Ẩn-Hiện từng SP (VNĐ)", b"adm:plist:0", style="primary"),
        ],
        [
            Button.inline("📈 Chỉnh % Lợi nhuận", b"adm:set:markup_percent"),
            Button.inline("➕ Chỉnh +VNĐ Cố định", b"adm:set:markup_fixed"),
        ],
        [
            Button.inline("🏦 Cài Ngân hàng VietQR", b"adm:bank"),
            Button.inline("🌙 Cài Token SePay (23h-06h)", b"adm:set:sepay_api_token"),
        ],
        [
            Button.inline("💵 Cộng/Trừ tiền khách (VNĐ)", b"adm:addbal"),
            Button.inline("💱 Đổi Tỷ giá USD->VNĐ", b"adm:set:vnd_rate"),
        ],
        [
            Button.inline("🔄 Đồng bộ Kho ngay", b"adm:sync"),
            Button.inline("« Về Menu Chính", b"menu:home"),
        ],
    ]
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
            lines.append(
                f"• `#{d['id']}` | Khách: `{d['user_id']}` (@{d['username']}) — **{amt:,}đ**\n"
                f"  📝 `{d['memo']}` ({d['created_at']})"
            )
            rows.append([
                Button.inline(f"✅ Duyệt #{d['id']} (+{amt:,}đ)", f"adm:dep_ok:{d['id']}".encode(), style="success"),
                Button.inline(f"❌ Từ chối #{d['id']}", f"adm:dep_no:{d['id']}".encode(), style="danger"),
            ])
        text = "\n".join(lines)
    rows.append([Button.inline("« Về Bảng Admin", b"adm:home")])
    await send_or_edit(event, text, buttons=rows)


async def render_admin_recent_orders(event: Any) -> None:
    orders = db.get_recent_orders(limit=10)
    if not orders:
        text = "📦 **Chưa có đơn hàng nào được ghi nhận.**"
    else:
        lines = ["📦 **10 ĐƠN HÀNG GẦN NHẤT TOÀN HỆ THỐNG:**\n"]
        for o in orders:
            lines.append(
                f"• `#{o['id']}` | `{o['user_id']}` (@{o['username']}) — **{o['product_name'][:22]}** (x{o['quantity']})\n"
                f"  💰 Bán: **{vnd_int(o['retail_price']):,}đ** | Vốn: {vnd_int(o['wholesale_cost']):,}đ | Lãi: **+{vnd_int(o['profit']):,}đ** [{o['status']}]"
            )
        text = "\n".join(lines)
    await send_or_edit(event, text, buttons=[[Button.inline("« Về Bảng Admin", b"adm:home")]])


async def render_admin_product_list(event: Any, page: int = 0) -> None:
    products = await ps_client.sync_products(force=False)
    overrides = db.get_all_overrides()
    per_page = 10
    total = len(products)
    start = page * per_page
    end = start + per_page
    sliced = products[start:end]

    rows: list[list[Any]] = []
    for p in sliced:
        pid = p["id"]
        cost_vnd = db.compute_wholesale_vnd(float(p["price"]))
        retail_vnd = db.compute_retail_price(pid, float(p["price"]), overrides)
        ov = overrides.get(pid, {})
        hidden_icon = "🙈 " if ov.get("hidden") else ""
        custom_tag = " 📌" if ov.get("custom_price") is not None else ""
        lbl = f"{hidden_icon}{p['name'].strip()[:18]} | Vốn:{cost_vnd:,}đ -> Bán:{retail_vnd:,}đ{custom_tag}"
        rows.append([Button.inline(lbl, f"adm:editp:{pid}".encode())])

    nav = []
    if page > 0:
        nav.append(Button.inline("⬅️ Trang trước", f"adm:plist:{page - 1}".encode()))
    if end < total:
        nav.append(Button.inline("Trang sau ➡️", f"adm:plist:{page + 1}".encode()))
    if nav:
        rows.append(nav)
    rows.append([Button.inline("« Về Bảng Admin", b"adm:home")])

    await send_or_edit(
        event,
        f"🏷️ **QUẢN LÝ GIÁ TỪNG SẢN PHẨM (Trang {page + 1}/{(total - 1) // per_page + 1})**\n"
        "• 📌 = Đang dùng giá bán cố định riêng (VNĐ)\n"
        "• 🙈 = Đang ẩn khỏi danh sách của khách\n"
        "Bấm vào sản phẩm để đặt giá bán riêng hoặc ẩn/hiện:",
        buttons=rows,
    )


async def render_admin_edit_product(event: Any, product_id: str) -> None:
    p = await ps_client.get_product_by_id(product_id, refresh=False)
    if not p:
        return
    ov = db.get_product_override(product_id) or {}
    cost_usd = float(p["price"])
    pub_usd = float(p.get("publicPrice", cost_usd))
    cost_vnd = db.compute_wholesale_vnd(cost_usd)
    pub_vnd = db.compute_wholesale_vnd(pub_usd)
    retail_vnd = db.compute_retail_price(product_id, cost_usd)
    is_hidden = bool(ov.get("hidden"))
    has_custom = ov.get("custom_price") is not None

    text = (
        f"🏷️ **TÙY CHỈNH SẢN PHẨM**\n\n"
        f"🛍️ Tên: **{p['name']}**\n"
        f"🆔 ID: `{product_id}`\n"
        f"📉 Giá vốn đại lý của bạn: **{cost_vnd:,}đ** (`${cost_usd:.2f}`)\n"
        f"🌐 Giá niêm yết bên @ProdSellerBot: **{pub_vnd:,}đ** (`${pub_usd:.2f}`)\n"
        f"💰 **Giá bán lẻ hiện tại của bạn: {retail_vnd:,}đ** "
        f"({'Giá cố định riêng 📌' if has_custom else 'Tính tự động theo % Markup'})\n"
        f"💵 Lợi nhuận mỗi đơn: **+{retail_vnd - cost_vnd:,}đ**\n"
        f"👁 Trạng thái hiển thị: **{'Đang ẨN 🙈' if is_hidden else 'Đang HIỆN ✅'}**"
    )

    rows = [
        [Button.inline("✏️ Đặt giá bán riêng (VNĐ)", f"adm:setp:{product_id}".encode(), style="primary")],
        [
            Button.inline("🔄 Dùng lại công thức % chung", f"adm:resetp:{product_id}".encode()),
            Button.inline("👁 Ẩn / Hiện SP này", f"adm:hidep:{product_id}".encode()),
        ],
        [Button.inline("« Quay lại danh sách SP", b"adm:plist:0")],
    ]
    await send_or_edit(event, text, buttons=rows)


# ==================== BACKGROUND TASK FOR ACTIVATION ORDERS ====================
async def poll_pending_activations_loop(client: TelegramClient) -> None:
    while True:
        await asyncio.sleep(60)
        pending = db.get_pending_activation_orders()
        for o in pending:
            try:
                st = await ps_client.get_order_status(o["prodseller_order_id"])
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
                            f"🎉 **Đơn hàng kích hoạt #{o['id']} đã hoàn tất!**\n\n"
                            f"🛍️ Sản phẩm: **{o['product_name']}**\n"
                            f"📧 Email: `{o['activation_email']}`\n"
                            f"🔑 Chi tiết: `{key_text}`"
                        ),
                    )
            except Exception as exc:
                logger.debug("Chưa lấy được trạng thái đơn %s: %s", o["prodseller_order_id"], exc)


# ==================== CLOUD HEALTH CHECK SERVER (RENDER / VERCEL PING) ====================
async def _handle_http_health(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    try:
        await asyncio.wait_for(reader.read(1024), timeout=5.0)
        db_mode = "supabase_postgres" if getattr(db, "use_postgres", False) else "local_sqlite"
        body = (
            f'{{"ok":true,"bot":"@{BOT_USERNAME_CACHE}","database":"{db_mode}","status":"running"}}'
        ).encode("utf-8")
        headers = (
            "HTTP/1.1 200 OK\r\n"
            "Content-Type: application/json; charset=utf-8\r\n"
            f"Content-Length: {len(body)}\r\n"
            "Connection: close\r\n\r\n"
        ).encode("utf-8")
        writer.write(headers + body)
        await writer.drain()
    except Exception:
        pass
    finally:
        try:
            writer.close()
            await writer.wait_closed()
        except Exception:
            pass


async def start_health_server() -> None:
    port_str = os.getenv("PORT", "").strip()
    if not port_str:
        return
    try:
        port = int(port_str)
        server = await asyncio.start_server(_handle_http_health, "0.0.0.0", port)
        logger.info("🌐 Cổng Health-Check HTTP đã mở tại 0.0.0.0:%s (Sẵn sàng cho Render & Vercel Ping)", port)
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
    global BOT_USERNAME_CACHE
    await start_health_server()
    api_id = int(os.getenv("TELEGRAM_API_ID", "0"))
    api_hash = os.getenv("TELEGRAM_API_HASH", "").strip()
    bot_token = os.getenv("RESELLER_BOT_TOKEN", "").strip()
    if not bot_token or ":" not in bot_token:
        raise RuntimeError("Thiếu RESELLER_BOT_TOKEN hợp lệ trong file .env!")

    client = TelegramClient(str(ROOT / "reseller-bot-session"), api_id, api_hash)
    await client.start(bot_token=bot_token)
    me = await client.get_me()
    BOT_USERNAME_CACHE = me.username or "KingToolShop_bot"
    logger.info("🚀 Bot Reseller @%s (ID: %s) đang hoạt động (Chế độ tiền tệ: VNĐ)!", BOT_USERNAME_CACHE, me.id)

    asyncio.create_task(ps_client.sync_products(force=True))
    asyncio.create_task(poll_products_sync_loop())
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
        if arg.startswith("REF_"):
            try:
                cand = int(arg.replace("REF_", ""))
                if cand != uid:
                    ref_id = cand
            except ValueError:
                pass
        sender = await event.get_sender()
        uname = getattr(sender, "username", None) or getattr(sender, "first_name", None) or ""
        u = db.get_or_create_user(uid, uname, referred_by=ref_id)
        lang = u.get("language", "vi")
        admin_user = db.get_setting("support_admin", "KingToolShopSupport").lstrip("@")
        channel_user = db.get_setting("support_channel", "KingToolShopOfficial").lstrip("@")

        await event.respond(t(lang, "welcome_banner", admin=admin_user, channel=channel_user))
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
            await render_products_menu(event, group_filter=data.split(":", 1)[1])
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
            p = await ps_client.get_product_by_id(pid, refresh=False)
            if not p:
                return
            max_q = int(p["stock"]) if isinstance(p.get("stock"), int) and p["stock"] > 0 else 100
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

        if data == "menu:deposit":
            await event.answer()
            await render_deposit_menu(event)
            return

        if data.startswith("dep:method:"):
            await event.answer()
            await render_deposit_amounts(event)
            return

        if data.startswith("dep:create:"):
            await event.answer()
            _, _, _, amt_str = data.split(":")
            await create_and_show_deposit(client, event, int(float(amt_str)))
            return

        if data.startswith("dep:custom:"):
            await event.answer()
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
                    [Button.inline(t(lang, "btn_back"), b"menu:deposit")],
                ]
                await event.edit(buttons=wait_rows)
            except Exception:
                pass

            amt_vnd = vnd_int(dep["amount_vnd"])
            mode_note = (
                f"🌙 *Đang trong khung 23h-06h (SePay {used_sp}/{limit_sp}): Bot đang tự động quét ngầm, hoặc bạn có thể bấm nút duyệt tay bên dưới:*"
                if (in_night and can_sp)
                else f"☀️ *Chế độ Duyệt Bằng Tay (SePay đã dùng {used_sp}/{limit_sp} lượt tháng này) — Kiểm tra ngân hàng và bấm nút bên dưới:*"
            )
            for adm_id in ADMIN_IDS:
                try:
                    adm_rows = [
                        [
                            Button.inline(f"✅ Duyệt +{amt_vnd:,}đ", f"adm:dep_ok:{dep_id}".encode(), style="success"),
                            Button.inline("❌ Từ chối", f"adm:dep_no:{dep_id}".encode(), style="danger"),
                        ]
                    ]
                    memo_display = dep.get("memo") or f"NAP{dep_id}"
                    await client.send_message(
                        adm_id,
                        (
                            f"🔔 **YÊU CẦU DUYỆT NẠP TIỀN #{dep_id}**\n\n"
                            f"👤 Khách: `{dep['user_id']}` (@{dep['username']})\n"
                            f"🏦 Phương thức: **VIETQR**\n"
                            f"💵 Số tiền nạp: **{amt_vnd:,}đ**\n"
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
                    username=u["username"] or "user",
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
            orders = db.get_user_orders(uid, limit=8)
            if not orders:
                txt = t(lang, "orders_empty")
            else:
                lines = [t(lang, "orders_history_title")]
                for o in orders:
                    clean_keys = format_order_keys_preview(o.get("delivered_keys", ""))
                    lines.append(
                        f"• `#{o['id']}` | **{o['product_name']}** (x{o['quantity']}) — **{vnd_int(o['retail_price']):,}đ** [{o['status']}]\n"
                        f"  🔑 `{clean_keys}`"
                    )
                txt = "\n".join(lines)
            await send_or_edit(event, txt, buttons=[[Button.inline(t(lang, "btn_back"), b"menu:profile")]])
            return

        if data == "prof:ref":
            await event.answer()
            ref_cnt = db.get_referral_stats(uid)
            ref_link = f"https://t.me/{BOT_USERNAME_CACHE}?start=REF_{uid}"
            comm_pct = float(db.get_setting("referral_commission_pct", "5.0") or 5.0)
            txt = t(lang, "referral_info", ref_link=ref_link, ref_cnt=ref_cnt, comm_pct=f"{comm_pct:g}")
            await send_or_edit(event, txt, buttons=[[Button.inline(t(lang, "btn_back"), b"menu:profile")]])
            return

        if data == "menu:api":
            await event.answer()
            admin_user = db.get_setting("support_admin", "KingToolShopSupport").lstrip("@")
            txt = t(lang, "api_info", admin=admin_user)
            await send_or_edit(event, txt, buttons=[[Button.inline(t(lang, "btn_back"), b"menu:home")]])
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
                [Button.url(f"🆘 @{admin_user}", f"https://t.me/{admin_user}")],
                [Button.url(f"📣 @{channel_user}", f"https://t.me/{channel_user}")],
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

            if data == "adm:deplist":
                await event.answer()
                await render_admin_pending_deposits(event)
                return

            if data == "adm:orders":
                await event.answer()
                await render_admin_recent_orders(event)
                return

            if data == "adm:finduser":
                await event.answer()
                USER_AWAITING[uid] = {"type": "admin_finduser"}
                await send_or_edit(
                    event,
                    "🔍 **TRA CỨU KHÁCH HÀNG**\n\nNhập `Telegram ID` hoặc `@username` của khách hàng cần kiểm tra:",
                    buttons=[[Button.inline("« Hủy", b"adm:home")]],
                )
                return

            if data == "adm:broadcast":
                await event.answer()
                USER_AWAITING[uid] = {"type": "admin_broadcast"}
                await send_or_edit(
                    event,
                    "📣 **GỬI THÔNG BÁO TOÀN BỘ KHÁCH HÀNG (BROADCAST)**\n\nNhập nội dung tin nhắn bạn muốn gửi tới toàn bộ khách đã từng dùng Bot:",
                    buttons=[[Button.inline("« Hủy", b"adm:home")]],
                )
                return

            if data == "adm:post_catalog":
                await event.answer("⏳ Đang đăng Bảng giá & Kho hàng lên @KingToolShopOfficial...")
                try:
                    msg_id = await post_catalog_to_channel(client, pin=True)
                    await event.respond(
                        f"✅ Đã đăng và ghim **Bảng giá & Tồn kho tự động** lên kênh `@KingToolShopOfficial` (Msg `#{msg_id}`)!",
                        buttons=[[Button.inline("« Về Bảng Admin", b"adm:home")]],
                    )
                except Exception as exc:
                    await event.respond(
                        f"❌ Không thể đăng lên kênh `@KingToolShopOfficial`: `{exc}`\n"
                        "*(Hãy đảm bảo @KingToolShop_bot đã được cấp quyền Admin trong kênh!)*",
                        buttons=[[Button.inline("« Về Bảng Admin", b"adm:home")]],
                    )
                return

            if data == "adm:sync":
                await event.answer("⏳ Đang đồng bộ lại toàn bộ sản phẩm & tồn kho từ ProdSeller...")
                await ps_client.sync_products(force=True)
                await render_admin_home(event)
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

            if data.startswith("adm:set:"):
                await event.answer()
                setting_key = data.split(":")[2]
                prompts = {
                    "markup_percent": "📈 Nhập **% lợi nhuận cộng thêm** so với giá vốn (ví dụ nhập `30` để tăng +30%):",
                    "markup_fixed": "➕ Nhập **số tiền VNĐ cộng thêm cố định** trên mỗi sản phẩm (ví dụ `5000` hoặc `0`):",
                    "vnd_rate": "💱 Nhập **tỷ giá quy đổi VNĐ cho $1 USD** giá vốn (ví dụ: `25500`):",
                    "methods_text": "📖 Nhập nội dung hiển thị cho mục **Hướng dẫn (Methods)**:",
                    "sepay_api_token": (
                        "🌙 **CÀI ĐẶT TOKEN SEPAY (TỰ ĐỘNG DUYỆT ĐÊM 23:00 - 06:00)**\n\n"
                        "1. Đăng ký tài khoản miễn phí tại `https://my.sepay.vn` và liên kết ngân hàng.\n"
                        "2. Vào mục **Cấu hình Công ty -> API Access** để copy **API Token**.\n"
                        "3. Dán **API Token** vào đây (hoặc gõ `off` để tắt):"
                    ),
                }
                USER_AWAITING[uid] = {"type": "set_setting", "key": setting_key}
                await send_or_edit(
                    event,
                    prompts.get(setting_key, f"Nhập giá trị mới cho `{setting_key}`:"),
                    buttons=[[Button.inline("« Hủy", b"adm:home")]],
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
                    buttons=[[Button.inline("« Hủy", b"adm:home")]],
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
                    buttons=[[Button.inline("« Hủy", b"adm:home")]],
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
                new_bal = db.adjust_balance(dep["user_id"], amt_vnd)
                await reward_referrer_on_deposit(client, dep)
                await send_or_edit(
                    event,
                    f"✅ **ĐÃ DUYỆT ĐƠN NẠP #{dep_id}**\n"
                    f"👤 Khách: `{dep['user_id']}` (@{dep['username']})\n"
                    f"💵 Đã cộng: **+{amt_vnd:,}đ** (Số dư mới: **{new_bal:,}đ**)",
                    buttons=[[Button.inline("« Về Bảng Admin", b"adm:home")]],
                )
                target_user = db.get_or_create_user(int(dep["user_id"]))
                u_lang = target_user.get("language", "vi")
                try:
                    await client.send_message(
                        dep["user_id"],
                        t(u_lang, "deposit_approved_msg", dep_id=dep_id, amt_vnd=amt_vnd, new_bal=new_bal),
                    )
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
                await send_or_edit(
                    event,
                    f"❌ **ĐÃ TỪ CHỐI ĐƠN NẠP #{dep_id}** ({amt_vnd:,}đ) của `{dep['user_id']}`.",
                    buttons=[[Button.inline("« Về Bảng Admin", b"adm:home")]],
                )
                target_user = db.get_or_create_user(int(dep["user_id"]))
                u_lang = target_user.get("language", "vi")
                try:
                    await client.send_message(
                        dep["user_id"],
                        t(u_lang, "deposit_rejected_msg", dep_id=dep_id, amt_vnd=amt_vnd),
                    )
                except Exception:
                    pass
                return

    @client.on(events.NewMessage)
    async def handle_text_input(event: events.NewMessage.Event) -> None:
        text = (event.raw_text or "").strip()
        if not event.is_private:
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
                        for adm_id in ADMIN_IDS:
                            try:
                                await client.send_message(
                                    adm_id,
                                    f"🆘 **KHÁCH ĐANG NHẮN HỖ TRỢ ĐƠN NẠP #{dep['id']} TRÊN NHÓM CSKH**\n\n"
                                    f"👤 Khách: `{dep['user_id']}` (@{dep['username']})\n"
                                    f"💵 Số tiền: **{amt_vnd:,}đ** | Nội dung: `{dep['memo']}`",
                                    buttons=[
                                        [
                                            Button.inline(f"✅ Duyệt +{amt_vnd:,}đ", f"adm:dep_ok:{dep['id']}".encode(), style="success"),
                                            Button.inline("❌ Từ chối", f"adm:dep_no:{dep['id']}".encode(), style="danger"),
                                        ]
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

        if not text or text.startswith("/"):
            if text.lower() == "/cancel":
                USER_AWAITING.pop(event.sender_id, None)
                u, lang = await get_user_info(event)
                await event.respond(
                    t(lang, "main_menu_title", balance=vnd_int(u["balance"]), points=u["points"]),
                    buttons=main_menu_buttons(lang, event.sender_id),
                )
            return

        uid = event.sender_id
        awaiting = USER_AWAITING.get(uid)
        if not awaiting:
            return

        u, lang = await get_user_info(event)
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

        if not is_admin(uid):
            return

        if atype == "admin_finduser":
            USER_AWAITING.pop(uid, None)
            found = db.find_user(text)
            if not found:
                await event.respond(
                    f"❌ Không tìm thấy khách hàng nào khớp với `{text}`.",
                    buttons=[[Button.inline("« Về Bảng Admin", b"adm:home")]],
                )
                return
            f_uid = found["telegram_id"]
            f_orders = db.get_user_orders(f_uid, limit=3)
            ord_summary = "\n".join(
                f"  • `#{o['id']}` {o['product_name'][:20]} (x{o['quantity']}) — {vnd_int(o['retail_price']):,}đ"
                for o in f_orders
            ) or "  (Chưa có đơn hàng)"
            info_txt = (
                f"👤 **THÔNG TIN KHÁCH HÀNG**\n\n"
                f"🆔 ID: `{f_uid}`\n"
                f"👤 Username: @{found['username'] or 'không_có'}\n"
                f"💎 Hạng: **{found['tier'].upper()}**\n"
                f"💵 Số dư hiện tại: **{vnd_int(found['balance']):,}đ**\n"
                f"⭐ Điểm thưởng: **{found['points']}**\n"
                f"📦 Tổng đơn đã mua: **{found['orders_count']}** (Chi tiêu: **{vnd_int(found['total_spent']):,}đ**)\n"
                f"📅 Ngày tham gia: `{found['joined_at']}`\n\n"
                f"🛍️ **Đơn gần nhất:**\n{ord_summary}"
            )
            await event.respond(
                info_txt,
                buttons=[
                    [Button.inline("💵 Cộng/Trừ số dư khách này", b"adm:addbal", style="primary")],
                    [Button.inline("« Về Bảng Admin", b"adm:home")],
                ],
            )
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
                buttons=[[Button.inline("« Về Bảng Admin", b"adm:home")]],
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
            await render_admin_home(event, force_new=True)
            return

        if atype == "set_setting":
            key = awaiting["key"]
            if key in ("markup_percent", "markup_fixed", "vnd_rate"):
                cleaned = text.lower().replace("%", "").replace("đ", "").replace("vnd", "").replace(",", "").strip()
                try:
                    val = float(cleaned)
                    db.set_setting(key, str(val))
                except ValueError:
                    await event.respond("❌ Giá trị số không hợp lệ, vui lòng nhập lại:")
                    return
            elif key == "sepay_api_token" and text.strip().lower() == "off":
                db.set_setting(key, "")
            else:
                db.set_setting(key, text)
            USER_AWAITING.pop(uid, None)
            await event.respond(f"✅ Đã cập nhật `{key}` thành công!")
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
            await render_admin_home(event, force_new=True)
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
            await render_admin_home(event, force_new=True)
            return

    await client.run_until_disconnected()


if __name__ == "__main__":
    try:
        asyncio.run(run_bot())
    except KeyboardInterrupt:
        logger.info("Đã dừng Bot theo yêu cầu người dùng.")
