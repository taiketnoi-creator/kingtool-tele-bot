"""Bộ tạo ảnh Banner / Poster HD động (1280x720) cho kênh @KingToolShopOfficial.

Tự động thiết kế hình ảnh quảng cáo sống động trong bộ nhớ RAM (io.BytesIO) cho:
1. Bài Tiêu Điểm Sản Phẩm Hot (Spotlight Banner) — Tự động đổi màu Neon theo thương hiệu.
2. Bài Bảng Giá & Kho Hàng Tự Động (Catalog Grid Banner) — Hiển thị lưới 8 SP nổi bật kèm giá VNĐ.
3. Bài Đơn Hàng Hoàn Tất / Đơn Mồi (Order Receipt Banner) — Biên lai giao dịch thành công 2 giây.
4. Bài Thông Báo Hàng Về (Restock Alert Banner) — Danh sách sản phẩm vừa về kho.
"""

from __future__ import annotations

import io
import os
from typing import Any

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from prodseller_client import detect_plan_group

_FONT_CACHE: dict[tuple[bool, int], ImageFont.FreeTypeFont | ImageFont.ImageFont] = {}

_BOLD_FONT_CANDIDATES = [
    "C:/Windows/Fonts/segoeuib.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
    "C:/Windows/Fonts/tahomabd.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
]

_REGULAR_FONT_CANDIDATES = [
    "C:/Windows/Fonts/segoeui.ttf",
    "C:/Windows/Fonts/arial.ttf",
    "C:/Windows/Fonts/tahoma.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
]


def _get_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    key = (bold, size)
    if key in _FONT_CACHE:
        return _FONT_CACHE[key]
    candidates = _BOLD_FONT_CANDIDATES if bold else _REGULAR_FONT_CANDIDATES
    for path in candidates:
        if os.path.exists(path):
            try:
                f = ImageFont.truetype(path, size=size)
                _FONT_CACHE[key] = f
                return f
            except Exception:
                continue
    fallback = ImageFont.load_default()
    _FONT_CACHE[key] = fallback
    return fallback


def _get_brand_palette(
    product_name: str,
    category: str = "",
) -> tuple[tuple[int, int, int], tuple[int, int, int], tuple[int, int, int], str, str]:
    """Trả về (primary_rgb, secondary_rgb, dark_tint_rgb, brand_label, monogram) theo thương hiệu."""
    brand = detect_plan_group(product_name, category)
    low = f"{brand} {product_name}".lower()
    words = [w for w in brand.split() if w]
    if len(words) >= 2:
        mono = (words[0][0] + words[1][0]).upper()
    else:
        mono = brand[:2].upper()

    if any(k in low for k in ("netflix", "youtube", "adobe", "riot", "hbo", "tv360", "vieon")):
        return (239, 35, 60), (255, 117, 143), (48, 14, 24), brand.upper(), mono
    if any(k in low for k in ("chatgpt", "openai", "spotify", "duolingo", "supabase", "evernote", "acer")):
        return (16, 185, 129), (52, 211, 153), (12, 42, 34), brand.upper(), mono
    if any(k in low for k in ("canva", "figma", "lovable", "gamma", "discord", "twitch", "framer", "picsart", "krea")):
        return (139, 92, 246), (56, 189, 248), (32, 22, 62), brand.upper(), mono
    if any(k in low for k in ("claude", "suno", "coursera", "udemy", "scribd", "amazon", "higgsfield", "heygen", "kling")):
        return (245, 158, 11), (251, 191, 36), (48, 32, 12), brand.upper(), mono
    if any(k in low for k in ("gemini", "cursor", "microsoft", "nordvpn", "surfshark", "vpn", "linkedin", "perplexity", "telegram", "zoom", "1password")):
        return (59, 130, 246), (56, 189, 248), (16, 32, 64), brand.upper(), mono
    return (245, 158, 11), (56, 189, 248), (42, 30, 14), brand.upper(), mono


def _create_base_canvas(
    width: int,
    height: int,
    accent1: tuple[int, int, int],
    accent2: tuple[int, int, int],
) -> Image.Image:
    """Tạo nền Dark-Luxury kèm hiệu ứng Glow Neon và lưới điểm công nghệ."""
    base = Image.new("RGBA", (width, height), (9, 13, 24, 255))

    glow = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    g_draw = ImageDraw.Draw(glow)
    g_draw.ellipse((-180, -180, 560, 520), fill=(*accent1, 90))
    g_draw.ellipse((width - 540, height - 480, width + 180, height + 180), fill=(*accent2, 80))
    g_draw.ellipse((width // 2 - 260, -220, width // 2 + 260, 220), fill=(255, 215, 0, 35))
    glow = glow.filter(ImageFilter.GaussianBlur(radius=95))
    base = Image.alpha_composite(base, glow)

    draw = ImageDraw.Draw(base)
    for x in range(40, width - 20, 48):
        for y in range(40, height - 20, 48):
            draw.point((x, y), fill=(255, 255, 255, 24))

    draw.rounded_rectangle(
        (16, 16, width - 17, height - 17),
        radius=28,
        outline=accent1,
        width=2,
    )
    return base


def _draw_check_icon(draw: ImageDraw.ImageDraw, cx: int, cy: int, radius: int, bg_color: tuple[int, int, int]) -> None:
    """Vẽ icon dấu tích tròn vector sắc nét (không phụ thuộc font emoji)."""
    draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), fill=bg_color)
    p1 = (cx - int(radius * 0.42), cy + int(radius * 0.02))
    p2 = (cx - int(radius * 0.10), cy + int(radius * 0.36))
    p3 = (cx + int(radius * 0.46), cy - int(radius * 0.32))
    draw.line([p1, p2, p3], fill=(255, 255, 255), width=max(2, radius // 4))


def _draw_bolt_icon(draw: ImageDraw.ImageDraw, cx: int, cy: int, size: int, color: tuple[int, int, int]) -> None:
    """Vẽ biểu tượng tia sét vector sắc nét."""
    pts = [
        (cx + int(size * 0.12), cy - size),
        (cx - int(size * 0.55), cy + int(size * 0.08)),
        (cx - int(size * 0.04), cy + int(size * 0.08)),
        (cx - int(size * 0.18), cy + size),
        (cx + int(size * 0.55), cy - int(size * 0.08)),
        (cx + int(size * 0.04), cy - int(size * 0.08)),
    ]
    draw.polygon(pts, fill=color)


def _draw_crown_icon(draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int, color: tuple[int, int, int]) -> None:
    """Vẽ biểu tượng vương miện vector vàng kim."""
    pts = [
        (x, y + h),
        (x, y + int(h * 0.25)),
        (x + int(w * 0.25), y + int(h * 0.6)),
        (x + w // 2, y),
        (x + int(w * 0.75), y + int(h * 0.6)),
        (x + w, y + int(h * 0.25)),
        (x + w, y + h),
    ]
    draw.polygon(pts, fill=color)


def _wrap_text(draw: ImageDraw.ImageDraw, text: str, font: Any, max_width: int, max_lines: int = 2) -> list[str]:
    words = text.split()
    if not words:
        return [text]
    lines: list[str] = []
    cur = words[0]
    for w in words[1:]:
        test = f"{cur} {w}"
        bbox = draw.textbbox((0, 0), test, font=font)
        if (bbox[2] - bbox[0]) <= max_width:
            cur = test
        else:
            lines.append(cur)
            cur = w
            if len(lines) >= max_lines - 1:
                break
    used_words = sum(len(ln.split()) for ln in lines)
    rem_words = words[used_words:]
    last_line = " ".join(rem_words)
    while last_line:
        bbox = draw.textbbox((0, 0), last_line, font=font)
        if (bbox[2] - bbox[0]) <= max_width or len(last_line) <= 6:
            break
        last_line = last_line[:-4].rstrip() + "..."
    if last_line:
        lines.append(last_line)
    return lines[:max_lines]


def _to_bytes_io(img: Image.Image, filename: str = "kingtool_banner.png") -> io.BytesIO:
    rgb = img.convert("RGB")
    buf = io.BytesIO()
    rgb.save(buf, format="PNG", optimize=True)
    buf.seek(0)
    buf.name = filename
    return buf


def generate_spotlight_banner(
    product_name: str,
    category: str,
    base_vnd: int,
    final_vnd: int,
    gift_code: str = "TANTHU10",
    stock_text: str = "Sẵn hàng",
    bot_username: str = "KingToolShop_bot",
) -> io.BytesIO:
    """Tạo Poster HD (1280x720) cho bài Tiêu Điểm Sản Phẩm Hot trên kênh."""
    W, H = 1280, 720
    acc1, acc2, dark_tint, brand_label, mono = _get_brand_palette(product_name, category)
    canvas = _create_base_canvas(W, H, acc1, acc2)
    draw = ImageDraw.Draw(canvas)

    f_badge = _get_font(21, bold=True)
    f_brand = _get_font(24, bold=True)
    f_mono = _get_font(34, bold=True)
    f_title = _get_font(46, bold=True)
    f_sub = _get_font(22, bold=False)
    f_sub_bold = _get_font(21, bold=True)
    f_price_lbl = _get_font(21, bold=True)
    f_price_big = _get_font(62, bold=True)
    f_old_price = _get_font(25, bold=True)
    f_footer = _get_font(20, bold=True)

    # 1. Top Header Badges
    draw.rounded_rectangle((48, 40, 470, 94), radius=27, fill=(18, 25, 44), outline=(251, 191, 36), width=2)
    _draw_crown_icon(draw, 74, 55, 26, 20, (251, 191, 36))
    draw.text((112, 53), "KINGTOOL SHOP OFFICIAL", font=f_badge, fill=(251, 191, 36))

    draw.rounded_rectangle((W - 430, 40, W - 48, 94), radius=27, fill=acc1, outline=acc2, width=2)
    _draw_bolt_icon(draw, W - 396, 67, 13, (255, 255, 255))
    draw.text((W - 374, 53), "TIÊU ĐIỂM SẢN PHẨM HOT", font=f_badge, fill=(255, 255, 255))

    # 2. Main Glass Card
    draw.rounded_rectangle((48, 118, W - 48, 590), radius=28, fill=(13, 20, 38), outline=(45, 60, 92), width=2)

    # Brand Pill + Stock Pill (High Contrast Dark Emerald)
    brand_txt = f"• {brand_label} •"
    b_box = draw.textbbox((0, 0), brand_txt, font=f_brand)
    b_w = max(150, (b_box[2] - b_box[0]) + 44)
    draw.rounded_rectangle((84, 152, 84 + b_w, 206), radius=14, fill=acc1)
    draw.text((84 + 22, 164), brand_txt, font=f_brand, fill=(255, 255, 255))

    st_txt = f"● KHO: {stock_text.upper()} — GIAO TỰ ĐỘNG 2 GIÂY"
    st_box = draw.textbbox((0, 0), st_txt, font=f_badge)
    st_w = (st_box[2] - st_box[0]) + 44
    draw.rounded_rectangle((102 + b_w, 152, 102 + b_w + st_w, 206), radius=14, fill=(10, 38, 32), outline=(52, 211, 153), width=2)
    draw.text((124 + b_w, 165), st_txt, font=f_badge, fill=(110, 231, 183))

    # Brand Monogram Avatar + Product Title
    draw.rounded_rectangle((84, 230, 168, 314), radius=22, fill=dark_tint, outline=acc1, width=3)
    mb = draw.textbbox((0, 0), mono, font=f_mono)
    mx = 84 + (84 - (mb[2] - mb[0])) // 2
    my = 230 + (84 - (mb[3] - mb[1])) // 2 - 4
    draw.text((mx, my), mono, font=f_mono, fill=acc2)

    clean_name = product_name.strip()
    title_lines = _wrap_text(draw, clean_name, f_title, max_width=W - 290, max_lines=2)
    y_cur = 234 if len(title_lines) > 1 else 244
    for ln in title_lines:
        draw.text((190, y_cur), ln, font=f_title, fill=(255, 255, 255))
        y_cur += 56

    # Feature checkmarks row
    features = [
        "Bản quyền chính hãng 100%",
        "Tự động trả tài khoản / key 24/7",
        "Bảo hành uy tín 1 chạm trên Bot",
    ]
    fx_cur = 84
    fy_cur = 360
    for feat in features:
        _draw_check_icon(draw, fx_cur + 13, fy_cur + 15, 13, (16, 185, 129))
        draw.text((fx_cur + 34, fy_cur), feat, font=f_sub, fill=(203, 213, 225))
        fb_w = draw.textbbox((0, 0), feat, font=f_sub)[2]
        fx_cur += fb_w + 68

    # 3. Price Box (Left) & Promo Voucher Box (Right)
    draw.rounded_rectangle((84, 418, 728, 558), radius=20, fill=(8, 12, 24), outline=(251, 191, 36), width=2)
    if final_vnd < base_vnd:
        draw.text((112, 434), f"GIÁ ƯU ĐÃI (ÁP MÃ {gift_code}):", font=f_price_lbl, fill=(251, 191, 36))
        old_str = f"Giá gốc: {base_vnd:,}đ"
        draw.text((448, 432), old_str, font=f_old_price, fill=(148, 163, 184))
        ob = draw.textbbox((448, 432), old_str, font=f_old_price)
        mid_y = (ob[1] + ob[3]) // 2 + 2
        draw.line((ob[0], mid_y, ob[2], mid_y), fill=(239, 68, 68), width=3)
    else:
        draw.text((112, 434), "GIÁ BÁN ƯU ĐÃI HÔM NAY:", font=f_price_lbl, fill=(251, 191, 36))

    draw.text((112, 466), f"{final_vnd:,} VNĐ", font=f_price_big, fill=(74, 222, 128))

    # Right Promo Box (Dark Tinted Background for High Readability)
    draw.rounded_rectangle((752, 418, W - 84, 558), radius=20, fill=dark_tint, outline=acc2, width=2)
    draw.text((778, 434), f"[VOUCHER] MÃ: {gift_code}", font=f_brand, fill=(251, 191, 36))
    draw.text((778, 476), "• Giảm ngay 10% đơn hàng đầu tiên", font=f_sub_bold, fill=(255, 255, 255))
    draw.text((778, 512), "• Nạp 200K tặng +5%, 500K tặng +10%", font=f_sub_bold, fill=(125, 211, 252))

    # 4. Bottom Trust Bar
    draw.rounded_rectangle((48, 612, W - 48, 678), radius=18, fill=(14, 22, 42), outline=(56, 189, 248), width=1)
    footer_txt = f"NHẬN KEY TRONG 2 GIÂY   •   QUÉT MÃ VIETQR TỰ ĐỘNG   •   MUA NGAY TẠI @{bot_username}"
    fb = draw.textbbox((0, 0), footer_txt, font=f_footer)
    fx = (W - (fb[2] - fb[0])) // 2
    draw.text((fx, 633), footer_txt, font=f_footer, fill=(226, 232, 240))

    return _to_bytes_io(canvas, "spotlight_banner.png")


def generate_catalog_banner(
    featured_items: list[tuple[str, int, str]],
    total_in_stock: int,
    updated_str: str,
    gift_code: str = "TANTHU10",
    bot_username: str = "KingToolShop_bot",
) -> io.BytesIO:
    """Tạo Banner Bảng Giá Tổng Hợp HD (1280x720) hiển thị lưới 8 sản phẩm nổi bật."""
    W, H = 1280, 720
    canvas = _create_base_canvas(W, H, (245, 158, 11), (59, 130, 246))
    draw = ImageDraw.Draw(canvas)

    f_title = _get_font(32, bold=True)
    f_sub = _get_font(20, bold=True)
    f_item_name = _get_font(22, bold=True)
    f_item_price = _get_font(24, bold=True)
    f_item_stock = _get_font(18, bold=False)
    f_footer = _get_font(20, bold=True)

    # Header Card
    draw.rounded_rectangle((44, 34, W - 44, 140), radius=22, fill=(14, 21, 40), outline=(251, 191, 36), width=2)
    _draw_crown_icon(draw, 70, 52, 28, 22, (251, 191, 36))
    draw.text((110, 46), "KINGTOOL SHOP — SIÊU KHO TÀI KHOẢN AI & PHẦN MỀM 24/7", font=f_title, fill=(251, 191, 36))
    draw.text(
        (72, 94),
        f"● Đang sẵn hàng: {total_in_stock}+ Sản phẩm   |   Cập nhật kho: {updated_str}   |   Giao tự động 2 giây",
        font=f_sub,
        fill=(148, 163, 184),
    )

    # Grid 2 columns x 4 rows (8 items)
    items = featured_items[:8]
    col_w = 578
    row_h = 102
    start_x = 44
    start_y = 160
    gap_x = 36
    gap_y = 14

    for idx, (name, price_vnd, st_txt) in enumerate(items):
        col = idx % 2
        row = idx // 2
        x0 = start_x + col * (col_w + gap_x)
        y0 = start_y + row * (row_h + gap_y)
        x1 = x0 + col_w
        y1 = y0 + row_h

        acc, _, _, _, _ = _get_brand_palette(name, "")
        draw.rounded_rectangle((x0, y0, x1, y1), radius=16, fill=(15, 23, 42), outline=acc, width=2)
        draw.rounded_rectangle((x0 + 14, y0 + 18, x0 + 22, y1 - 18), radius=4, fill=acc)

        short_n = name.strip()
        while len(short_n) > 10:
            bb = draw.textbbox((0, 0), short_n, font=f_item_name)
            if (bb[2] - bb[0]) <= 355:
                break
            short_n = short_n[:-4].rstrip() + "..."

        draw.text((x0 + 36, y0 + 18), short_n, font=f_item_name, fill=(255, 255, 255))
        draw.text((x0 + 36, y0 + 54), f"● {st_txt} — Bảo hành 1 chạm", font=f_item_stock, fill=(110, 231, 183))

        p_str = f"{price_vnd:,}đ"
        pb = draw.textbbox((0, 0), p_str, font=f_item_price)
        pw = (pb[2] - pb[0]) + 32
        draw.rounded_rectangle((x1 - pw - 18, y0 + 24, x1 - 18, y0 + 76), radius=12, fill=(10, 38, 32), outline=(52, 211, 153), width=2)
        draw.text((x1 - pw - 2, y0 + 34), p_str, font=f_item_price, fill=(110, 231, 183))

    # Footer Promo Bar
    draw.rounded_rectangle((44, 622, W - 44, 686), radius=18, fill=(18, 28, 52), outline=(251, 191, 36), width=2)
    f_txt = f"MÃ TÂN THỦ: {gift_code} (-10%)   •   NẠP TỪ 200K TẶNG +5%, 500K TẶNG +10%   •   @{bot_username}"
    fb = draw.textbbox((0, 0), f_txt, font=f_footer)
    draw.text(((W - (fb[2] - fb[0])) // 2, 642), f_txt, font=f_footer, fill=(251, 191, 36))

    return _to_bytes_io(canvas, "catalog_banner.png")


def generate_order_receipt_banner(
    order_id: int | str,
    masked_uid: str,
    product_name: str,
    qty: int,
    total_vnd: int,
    bot_username: str = "KingToolShop_bot",
) -> io.BytesIO:
    """Tạo ảnh Biên Lai Giao Dịch Tự Động Hoàn Tất (1280x640) cho thông báo đơn hàng trên kênh."""
    W, H = 1280, 640
    acc1, acc2, dark_tint, brand_label, mono = _get_brand_palette(product_name, "")
    canvas = _create_base_canvas(W, H, (16, 185, 129), acc1)
    draw = ImageDraw.Draw(canvas)

    f_badge = _get_font(22, bold=True)
    f_mono = _get_font(28, bold=True)
    f_title = _get_font(38, bold=True)
    f_lbl = _get_font(23, bold=False)
    f_val = _get_font(25, bold=True)
    f_price = _get_font(38, bold=True)
    f_footer = _get_font(20, bold=True)

    # Top Header (High Contrast Dark Emerald)
    draw.rounded_rectangle((56, 40, 565, 94), radius=26, fill=(10, 38, 32), outline=(52, 211, 153), width=2)
    _draw_check_icon(draw, 88, 67, 14, (16, 185, 129))
    draw.text((114, 53), "ĐƠN HÀNG TỰ ĐỘNG HOÀN TẤT (2 GIÂY)", font=f_badge, fill=(110, 231, 183))

    oid_str = f"MÃ ĐƠN: #{order_id}"
    ob = draw.textbbox((0, 0), oid_str, font=f_badge)
    ow = (ob[2] - ob[0]) + 48
    draw.rounded_rectangle((W - 56 - ow, 40, W - 56, 94), radius=26, fill=(24, 34, 56), outline=(251, 191, 36), width=2)
    draw.text((W - 56 - ow + 24, 53), oid_str, font=f_badge, fill=(251, 191, 36))

    # Receipt Card
    draw.rounded_rectangle((56, 118, W - 56, 514), radius=26, fill=(13, 20, 38), outline=(45, 60, 92), width=2)

    # Brand Monogram + Product Title
    draw.rounded_rectangle((92, 138, 156, 202), radius=16, fill=dark_tint, outline=acc1, width=2)
    mb = draw.textbbox((0, 0), mono, font=f_mono)
    draw.text((92 + (64 - (mb[2] - mb[0])) // 2, 138 + (64 - (mb[3] - mb[1])) // 2 - 3), mono, font=f_mono, fill=acc2)

    short_prod = product_name.strip()
    if len(short_prod) > 42:
        short_prod = short_prod[:39] + "..."
    draw.text((176, 146), short_prod, font=f_title, fill=(255, 255, 255))
    draw.line((92, 216, W - 92, 216), fill=(45, 60, 92), width=2)

    rows_info = [
        ("● Khách hàng:", f"ID {masked_uid} (Đã xác thực)", (241, 245, 249)),
        ("● Số lượng & Phân loại:", f"x{qty} gói ({brand_label})", (125, 211, 252)),
        ("● Trạng thái giao hàng:", "Đã trả Tài khoản / Key tự động trong 2 giây!", (110, 231, 183)),
    ]
    y = 236
    for lbl, val, col in rows_info:
        draw.text((92, y), lbl, font=f_lbl, fill=(148, 163, 184))
        draw.text((430, y), val, font=f_val, fill=col)
        y += 56

    # Total Paid Box
    draw.rounded_rectangle((92, 408, W - 92, 488), radius=16, fill=(8, 14, 26), outline=(52, 211, 153), width=2)
    draw.text((120, 433), "TỔNG THANH TOÁN (VIETQR):", font=f_val, fill=(251, 191, 36))
    paid_str = f"{total_vnd:,} VNĐ"
    pb = draw.textbbox((0, 0), paid_str, font=f_price)
    draw.text((W - 120 - (pb[2] - pb[0]), 423), paid_str, font=f_price, fill=(74, 222, 128))

    # Footer
    draw.rounded_rectangle((56, 538, W - 56, 600), radius=16, fill=(18, 28, 52), outline=(251, 191, 36), width=1)
    ft = f"Khách mới bấm nút 'Quà Tân Thủ (-10%)' bên dưới để nhận ngay Voucher giảm giá tại @{bot_username}"
    fb = draw.textbbox((0, 0), ft, font=f_footer)
    draw.text(((W - (fb[2] - fb[0])) // 2, 557), ft, font=f_footer, fill=(251, 191, 36))

    return _to_bytes_io(canvas, "order_receipt.png")


def generate_restock_banner(
    restocked_items: list[tuple[str, int, str]],
    bot_username: str = "KingToolShop_bot",
) -> io.BytesIO:
    """Tạo Banner Thông Báo Hàng Về (1280x680) khi có sản phẩm mới restock."""
    W, H = 1280, 680
    canvas = _create_base_canvas(W, H, (16, 185, 129), (245, 158, 11))
    draw = ImageDraw.Draw(canvas)

    f_title = _get_font(34, bold=True)
    f_sub = _get_font(21, bold=True)
    f_name = _get_font(23, bold=True)
    f_price = _get_font(25, bold=True)
    f_footer = _get_font(20, bold=True)

    draw.rounded_rectangle((48, 36, W - 48, 138), radius=22, fill=(14, 21, 40), outline=(52, 211, 153), width=2)
    _draw_bolt_icon(draw, 80, 68, 16, (74, 222, 128))
    draw.text((108, 48), "THÔNG BÁO HÀNG VỀ (RESTOCK KHO TỰ ĐỘNG)", font=f_title, fill=(74, 222, 128))
    draw.text((76, 94), "● Các siêu phẩm dưới đây vừa được nạp đầy kho — Sẵn sàng giao tự động trong 2 giây!", font=f_sub, fill=(226, 232, 240))

    items = restocked_items[:6]
    y = 160
    for name, price_vnd, st_txt in items:
        draw.rounded_rectangle((48, y, W - 48, y + 66), radius=14, fill=(16, 24, 44), outline=(45, 60, 92), width=1)
        short_n = name.strip()
        if len(short_n) > 48:
            short_n = short_n[:45] + "..."
        _draw_check_icon(draw, 78, y + 33, 12, (16, 185, 129))
        draw.text((102, y + 18), short_n, font=f_name, fill=(255, 255, 255))
        right_str = f"{price_vnd:,}đ  ({st_txt})"
        rb = draw.textbbox((0, 0), right_str, font=f_price)
        draw.text((W - 76 - (rb[2] - pb_w if (pb_w := (rb[2] - rb[0])) else 0), y + 17), right_str, font=f_price, fill=(251, 191, 36))
        y += 74

    draw.rounded_rectangle((48, 608, W - 48, 654), radius=14, fill=(18, 28, 52))
    ft = f"Bấm trực tiếp vào nút sản phẩm bên dưới để mở @{bot_username} và nhận Key ngay!"
    fb = draw.textbbox((0, 0), ft, font=f_footer)
    draw.text(((W - (fb[2] - fb[0])) // 2, 619), ft, font=f_footer, fill=(125, 211, 252))

    return _to_bytes_io(canvas, "restock_banner.png")
