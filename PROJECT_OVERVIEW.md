# 📘 TỔNG QUAN DỰ ÁN & KIẾN TRÚC KỸ THUẬT (PROJECT OVERVIEW)
## 🤖 Dự án: KingTool Shop Telegram Reseller Bot (`@KingToolShop_bot`)

> **Tài liệu dành cho AI Agent & Developer:** File này mô tả toàn bộ cấu trúc, luồng nghiệp vụ, cơ sở dữ liệu, hạ tầng Cloud và các quy tắc bất khả xâm phạm của dự án. Bất kỳ AI Agent nào tiếp nhận dự án **BẮT BUỘC** đọc kỹ file này và `PROJECT_CHANGELOG.md` trước khi thực hiện thay đổi.

---

## 1. Mục Đích & Mô Hình Kinh Doanh

- **Mô hình:** Bot Telegram bán tài khoản/phần mềm số tự động 24/7 theo mô hình **Reseller (Đại lý trung gian)**.
- **Nguồn hàng gốc (Upstream Provider):** Kết nối trực tiếp với **ProdSeller Official API v1** (`https://prodseller.com/v1`).
- **Luồng hoạt động cốt lõi:**
  1. Bot tự động đồng bộ danh sách sản phẩm, mô tả, giá vốn (USD) và số lượng tồn kho (`stock`) từ ProdSeller.
  2. Tự động quy đổi giá vốn USD sang **Việt Nam Đồng (VNĐ)** theo tỷ giá cài đặt và cộng thêm biên lợi nhuận (`markup_percent` + `markup_fixed`) hoặc giá bán lẻ riêng từng món (`product_overrides`).
  3. Khách hàng nạp tiền vào ví trên Bot bằng **Chuyển khoản Ngân hàng VietQR** (có mã đối soát `KINGTOOL CAM ON SPX...`).
  4. Khi khách bấm mua hàng -> Bot trừ số dư ví VNĐ nguyên tử (Atomic) -> Gọi API ProdSeller mua hàng bằng số dư đại lý -> Trả Key/Tài khoản ngay lập tức cho khách (hoặc theo dõi ngầm đơn kích hoạt qua Email đến khi hoàn tất).

---

## 2. Kiến Trúc Hạ Tầng Cloud 24/7

Dự án đã được chuyển đổi hoàn toàn từ Local lên Cloud, hoạt động 24/7 không phụ thuộc máy tính cá nhân:

| Thành phần | Nền tảng | Chi tiết cấu hình & Vai trò |
| :--- | :--- | :--- |
| **Source Code & CI/CD** | **GitHub** | Repo: `https://github.com/taiketnoi-creator/kingtool-tele-bot` (nhánh `main`). Mỗi khi `git push origin main`, Render tự động build & deploy bản mới. |
| **Bot Runtime (24/7)** | **Render (Web Service)** | URL: `https://kingtool-tele-bot.onrender.com` (Region: `Singapore`, gói `Free`).<br>Chạy `python bot.py` kết nối **Telethon MTProto** kèm cổng HTTP Health-check tại `/health` và vòng lặp `keep_alive_ping_loop()` tự ping mỗi 10 phút. |
| **Cloud Database** | **Supabase (PostgreSQL)** | Project: `Base Family` (`rudmczssstjmaxhvbrnj`, Region: `ap-southeast-2` Sydney).<br>Kết nối qua cổng **IPv4 Session Pooler** (`aws-0-ap-southeast-2.pooler.supabase.com:5432`).<br>**Quan trọng:** Toàn bộ bảng của Bot nằm trong **Schema riêng biệt `telebot`** (`telebot.settings`, `telebot.users`, `telebot.orders`, `telebot.deposits`, `telebot.product_overrides`) để tách biệt 100% với Schema `public` của dự án `Base Family`. |
| **Serverless Dashboard** | **Vercel (Tùy chọn)** | File `vercel.json` + `api/index.py` cung cấp trang Web Dashboard xem thống kê trực tuyến và Cron-job ping giữ thức Render. |

---

## 3. Cấu Trúc Thư Mục Dự Án

```text
Bot Tele/
├── bot.py                 # Trái tim của Bot (Telethon MTProto, UI nút màu, luồng mua hàng, Admin Panel, HTTP Health Server)
├── database.py            # Lớp quản trị DB (Hỗ trợ song song Supabase PostgreSQL Schema 'telebot' & SQLite Local + RAM Cache)
├── prodseller_client.py   # Async HTTP Client kết nối ProdSeller API v1, phân nhóm Sub-plans, Custom Emoji Icons, Cache Stale-While-Revalidate
├── i18n.py                # Đa ngôn ngữ (Việt, Anh, Trung, Nga...) & bộ từ điển Việt hóa mô tả sản phẩm tự động
├── analyzer.py            # Công cụ phụ trợ phân tích menu bot mẫu an toàn
├── api/
│   └── index.py           # Serverless Handler cho Vercel (Web Status Dashboard & Keep-Alive Ping)
├── render.yaml            # Blueprint cấu hình tự động cho Render Web Service
├── vercel.json            # Cấu hình định tuyến & Cron cho Vercel
├── requirements.txt       # Danh sách thư viện Python (Telethon, httpx, python-dotenv, psycopg2-binary...)
├── .env.example           # Mẫu cấu hình biến môi trường
├── .gitignore             # Chặn tuyệt đối các file nhạy cảm (.env, *.session, shop.db, .venv/, *.log)
├── start_bot.bat          # Script chạy ngầm trên Windows Local (chỉ dùng khi test ở máy cá nhân)
├── stop_bot.bat           # Script dừng tiến trình Bot ở máy cá nhân
├── PROJECT_OVERVIEW.md    # Tài liệu tổng quan kiến trúc & nghiệp vụ dự án (File này)
├── PROJECT_CHANGELOG.md   # Lịch sử cập nhật & thay đổi qua các phiên bản
└── AGENTS.md              # Chỉ dẫn nhanh cho AI Agent khi làm việc với codebase
```

---

## 4. Thiết Kế Cơ Sở Dữ Liệu (`database.py` - Schema `telebot`)

Khi có biến môi trường `DATABASE_URL`, `Database` tự động dịch mọi câu lệnh SQL sang **Schema `telebot`** trên PostgreSQL:

1. **`telebot.settings` (`key TEXT PRIMARY KEY, value TEXT`)**:
   - Lưu toàn bộ cấu hình động của Shop:
     - `markup_percent` (Mặc định `25.0%`), `markup_fixed` (`0đ`), `vnd_rate` (`25500` - tỷ giá quy đổi USD -> VNĐ).
     - `bank_id` (`MB`), `bank_account_no`, `bank_account_name` (dùng để tạo ảnh QR VietQR tự động).
     - `support_admin`, `support_channel`, `methods_text`.
     - Cấu hình SePay tự động ban đêm: `sepay_api_token`, `sepay_night_start` (`23`), `sepay_night_end` (`6`), `sepay_monthly_limit` (`50`), `sepay_used_month`, `sepay_used_count`.
     - Cấu hình ưu đãi: `referral_commission_pct` (`5.0%`), `point_value_vnd` (`100đ`).
2. **`telebot.users`**:
   - `telegram_id BIGINT PRIMARY KEY`, `username`, `balance NUMERIC(18,2)`, `points INTEGER`, `tier TEXT` (`bronze`/`silver`/`gold`), `orders_count`, `total_spent NUMERIC(18,2)`, `language`, `referred_by BIGINT`, `joined_at`.
3. **`telebot.product_overrides`**:
   - `product_id TEXT PRIMARY KEY`, `custom_price NUMERIC(18,2)` (giá bán lẻ VNĐ cố định riêng nếu không dùng % chung), `hidden INTEGER` (`0` = hiện, `1` = ẩn khỏi menu khách).
4. **`telebot.deposits`**:
   - `id BIGSERIAL PRIMARY KEY`, `user_id BIGINT`, `username`, `amount_usd`, `amount_vnd BIGINT`, `method` (`vietqr`), `memo` (`KINGTOOL CAM ON SPX...`), `status` (`pending`/`approved`/`rejected`/`expired`), `created_at`, `updated_at`.
5. **`telebot.orders`**:
   - `id BIGSERIAL PRIMARY KEY`, `user_id BIGINT`, `username`, `product_id`, `product_name`, `quantity`, `wholesale_cost`, `retail_price`, `profit`, `prodseller_order_id`, `status` (`paid`/`delivered`), `delivered_keys` (JSON array), `activation_email`, `created_at`.

---

## 5. Các Nghiệp Vụ & Thuật Toán Quan Trọng

### 5.1. Công thức Giá bán, Hạng VIP & Bảo vệ Giá vốn
- **Giá vốn VNĐ (`cost_vnd`)**: `round(wholesale_usd * vnd_rate)`.
- **Giá bán lẻ niêm yết (`base_vnd`)**:
  - Nếu sản phẩm có `custom_price` trong `product_overrides` -> dùng `custom_price`.
  - Nếu không -> `cost_vnd * (1 + markup_percent / 100) + markup_fixed`, làm tròn đẹp tới `500đ` hoặc `1,000đ`.
- **Chiết khấu Hạng thành viên (`TIER_DISCOUNTS`)**:
  - `BRONZE` (< `600,000đ` chi tiêu): giảm `0%`.
  - `SILVER` (>= `600,000đ` chi tiêu): giảm `3%`.
  - `GOLD` (>= `2,500,000đ` chi tiêu): giảm `5%`.
- **🛡️ Nguyên tắc bất khả xâm phạm (Chống lỗ vốn):**
  - Mọi mức giảm giá (VIP hoặc Voucher) đều phải qua chốt chặn `final_vnd = max(cost_vnd, discounted_price)`. Giá thu của khách **không bao giờ thấp hơn giá vốn đại lý**.

### 5.2. Điểm thưởng (Cashback Points) & Link Giới Thiệu (Referral)
- **Tích điểm khi mua hàng:** Mỗi `10,000đ` chi tiêu = `+1 điểm` (tối thiểu `1 điểm`/đơn).
- **Đổi điểm:** Mặc định `1 điểm = 100đ`. Khi đủ từ `10 điểm`, khách bấm nút đổi điểm trong mục Số dư/Hồ sơ để cộng thẳng tiền VNĐ vào ví.
- **Link giới thiệu (`https://t.me/KingToolShop_bot?start=REF_<ID>`):**
  - Khách mới vào qua link được lưu `referred_by = <ID>`.
  - Mỗi khi khách mới nạp tiền thành công, người giới thiệu tự động được cộng **`5%` giá trị đơn nạp** vào số dư ví.

### 5.3. Cơ chế Duyệt Nạp Tiền Hybrid (Ban ngày Duyệt Tay + Ban đêm SePay Tự Động)
- Để tiết kiệm tối đa gói **Free 50 giao dịch/tháng của SePay**:
  - **Ban ngày (`06:00` – `22:59`):** 100% gửi thông báo kèm 2 nút `✅ Duyệt` / `❌ Từ chối` về Telegram Admin (`8110826820`) để duyệt tay 1 chạm (không tốn lượt SePay).
  - **Ban đêm (`23:00` – `05:59` sáng):** Nếu đã cài `sepay_api_token` và chưa dùng hết 50 lượt/tháng, vòng lặp `poll_night_sepay_deposits_loop` tự động quét API SePay mỗi 30 giây, khớp mã `SPX...` và số tiền để cộng số dư tự động khi Admin đang ngủ.

### 5.4. Cơ chế Tối Ưu Tốc Độ Phản Hồi (`0.15ms` RAM Cache)
- Vì Render đặt tại **Singapore** còn Supabase đặt tại **Sydney (`ap-southeast-2`)**, `database.py` sử dụng **Write-Through RAM Cache** cho `settings` (TTL 60s), `product_overrides` (TTL 60s) và `users` (TTL 45s).
- Tuyệt đối **KHÔNG** thực hiện truy vấn SQL lặp trong vòng lặp hiển thị danh sách sản phẩm (tránh lỗi N+1 Query).
- `prodseller_client.py` sử dụng cơ chế **Stale-While-Revalidate**: trả về danh sách sản phẩm từ RAM ngay lập tức (`force=False`) và đồng bộ ngầm mỗi 45 giây.

---

## 6. Định Hướng Phát Triển Tiếp Theo (Roadmap)

- **Tính năng đã thống nhất thiết kế (Sẵn sàng triển khai):**
  - **Hệ thống Mã Giảm Giá (Voucher System - bảng `telebot.vouchers` & `telebot.voucher_usages`)**:
    - Cho phép khách nhập mã Voucher tại màn hình Chi tiết sản phẩm trước khi bấm Mua.
    - Hỗ trợ giảm theo `%` hoặc giảm số tiền VNĐ cố định, giới hạn số lượt dùng tối đa, mỗi user dùng 1 lần/mã.
    - Tích hợp quản lý tạo/xóa mã ngay trong `/admin`.
    - Vẫn giữ nguyên chốt chặn bảo vệ giá vốn (`final_price >= cost_vnd`).

---

## 7. Quy Tắc Bắt Buộc Cho AI Agent Khi Chỉnh Sửa Dự Án

1. **Bảo mật:** Không bao giờ commit file `.env`, `*.session`, `shop.db` lên Git.
2. **Database Schema:** Mọi bảng mới thêm vào `database.py` phải được thêm vào biểu thức chính quy `_TABLE_NAME_RE` để tự động nằm trong Schema `telebot.*` trên Supabase (tuyệt đối không làm bẩn Schema `public` của dự án `Base Family`).
3. **Hiệu năng:** Khi đọc cấu hình hoặc tính giá trong vòng lặp, luôn dùng dữ liệu từ RAM Cache (`get_all_settings()`, `get_all_overrides()`), không gọi truy vấn mạng lẻ tẻ.
4. **Đồng bộ Cloud:** Sau mỗi lần chỉnh sửa code tại Local, cần kiểm tra cú pháp Python, chạy `git add`, `git commit`, `git push origin main` để Render tự động cập nhật bản mới và ghi chú lại vào `PROJECT_CHANGELOG.md`.
