# 🤖 KingTool Shop Bot - Hệ Thống Bán Hàng Tự Động (Cloud 24/7)

Hệ thống Bot Telegram Reseller kết nối trực tiếp với **ProdSeller Official API v1**, sử dụng cơ sở dữ liệu đám mây **Supabase (PostgreSQL)**, chạy 24/7 trên **Render** và tích hợp Web Status Dashboard / Keep-Alive trên **Vercel**.

---

## 🏗️ Kiến Trúc Cloud Hoàn Chỉnh

1. **GitHub (`taiketnoi-creator/kingtool-tele-bot`)**: Lưu trữ mã nguồn, tự động đồng bộ CI/CD với Render & Vercel.
2. **Supabase (PostgreSQL - Schema `telebot`)**: Lưu trữ vĩnh viễn trong thư mục Schema riêng biệt `telebot` (`telebot.users`, `telebot.orders`, `telebot.deposits`, `telebot.settings`, `telebot.product_overrides`), tách biệt 100% với Schema `public`.
3. **Render (Web Service - Singapore)**: Chạy tiến trình [bot.py](file:///d:/Phi%C3%AAn%20b%E1%BA%A3n%20Ai%20agent/Bot%20Tele/bot.py) 24/7 kèm cổng HTTP Health-check (`/health`).
4. **Vercel (`api/index.py`)**: Cung cấp trang Web theo dõi trạng thái trực tuyến và tự động ping giữ thức Render.

---

## 🚀 Hướng Dẫn Triển Khai Trên Render (Chạy Bot 24/7)

1. Truy cập [https://dashboard.render.com](https://dashboard.render.com) → Đăng nhập bằng **GitHub**.
2. Bấm **New +** → chọn **Web Service** → Chọn repository **`kingtool-tele-bot`**.
3. Cấu hình dịch vụ:
   - **Region**: `Singapore (Southeast Asia)`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python bot.py`
   - **Instance Type**: `Free`
4. Trong mục **Environment Variables**, thêm các biến sau:
   - `TELEGRAM_API_ID`
   - `TELEGRAM_API_HASH`
   - `RESELLER_BOT_TOKEN`
   - `PRODSELLER_API_KEY`
   - `ADMIN_TELEGRAM_IDS`
   - `DATABASE_URL` *(Chuỗi kết nối Supabase Session Pooler IPv4 cổng 5432)*
5. Bấm **Deploy Web Service**.

---

## 🌐 Hướng Dẫn Triển Khai Trên Vercel (Dashboard & Giữ Thức Render)

1. Truy cập [https://vercel.com/new](https://vercel.com/new) → Import repository **`kingtool-tele-bot`**.
2. Trong mục **Environment Variables**, thêm:
   - `DATABASE_URL`: Chuỗi kết nối Supabase.
   - `RENDER_BOT_URL`: Đường link dịch vụ Render vừa tạo (ví dụ: `https://kingtool-tele-bot.onrender.com`).
3. Bấm **Deploy**.
