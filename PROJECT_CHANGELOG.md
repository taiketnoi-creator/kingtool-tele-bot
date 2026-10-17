# 📜 LỊCH SỬ CHỈNH SỬA & NÂNG CẤP DỰ ÁN (PROJECT CHANGELOG)
## 🤖 Dự án: KingTool Shop Telegram Reseller Bot (`@KingToolShop_bot`)

> Mọi thay đổi về tính năng, kiến trúc cơ sở dữ liệu, tối ưu hiệu năng và triển khai Cloud đều được ghi nhận tại đây theo thứ tự thời gian mới nhất ở trên.

---

## [v2.3.0] - 2026-10-17: Hệ Thống Mã Giảm Giá (Voucher System) & Chốt Chặn Chống Lỗ Vốn Tuyệt Đối

### 🎟️ Tính năng Mã Giảm Giá (Voucher System)
- **Cơ sở dữ liệu (`database.py` - Schema `telebot`):**
  - Bổ sung 2 bảng mới `telebot.vouchers` và `telebot.voucher_usages` vào `_TABLE_NAME_RE` và `_init_db()` (tương thích song song Supabase PostgreSQL & SQLite Local, giữ nguyên vẹn 100% Schema `public` của `Base Family`).
  - Tích hợp **Write-Through RAM Cache** (`_vouchers_cache`, TTL 60s) đảm bảo kiểm tra và tính giá Voucher tức thì không phát sinh truy vấn mạng lặp.
  - Xây dựng hàm `compute_order_pricing()` kết hợp đồng thời **Chiết khấu Hạng VIP (`Silver 3%`, `Gold 5%`)** + **Mã Giảm Giá Voucher (Giảm `%` hoặc Giảm tiền mặt VNĐ cố định)**.
- **🛡️ Chốt chặn chống lỗ vốn (`Anti-Loss Floor Protection`):**
  - Thiết lập khóa an toàn cứng `total_final_vnd = max(total_cost_vnd, raw_after_voucher)`: Dù khách hàng có Hạng VIP cao nhất cộng thêm mã giảm giá sâu, số tiền thanh toán cuối cùng **không bao giờ thấp hơn giá vốn đại lý (`cost_vnd`)** từ `@ProdSellerBot`.
- **Giao diện Khách hàng (`bot.py` & `i18n.py`):**
  - Ngay trên nút `💳 Mua ngay — ...đ` ở màn hình Chi tiết sản phẩm, thêm nút `🎟️ Nhập mã giảm giá (Voucher)`.
  - Kiểm tra tự động: mã tồn tại, đang bật, còn lượt sử dụng (`used_count < max_uses`), và mỗi khách chỉ được dùng 1 lần/mã (`UNIQUE(code, user_id)`).
  - Khi áp mã hợp lệ: tự động gạch ngang giá cũ (`~78,000đ~`), hiển thị mức tiết kiệm và đổi nút thành `🎟️ Đang áp mã: SALE20 (-15,000đ) [❌ Bỏ mã]`, đồng thời cập nhật ngay số tiền trên nút `💳 Mua ngay`.
- **Bảng điều khiển Admin (`/admin`):**
  - Thêm mục `🎟️ Quản lý Voucher` hỗ trợ tạo mã mới trong 5 giây theo cú pháp `MÃ_CODE | MỨC_GIẢM | SỐ_LƯỢT_TỐI_ĐA` (ví dụ: `SALE20 | 20% | 50` hoặc `GIAM15K | 15k | 20`).
  - Hiển thị danh sách mã kèm tiến độ lượt dùng (`3/20 lượt`) và các nút thao tác nhanh 1 chạm: `🔴 Tắt` / `🟢 Bật` và `🗑️ Xóa`.

---

## [v2.2.0] - 2026-10-16: Tối Ưu Hóa Tốc Độ Phản Hồi Tức Thì (`0.15ms`) & Chuẩn Hóa Tài Liệu AI Agent

### ⚡ Tối ưu hiệu năng (Performance)
- **Khắc phục triệt để lỗi N+1 Queries giữa Render (Singapore) và Supabase (Sydney):**
  - Bổ sung cơ chế **Write-Through RAM Cache** trong `database.py` cho `settings` (TTL 60s), `product_overrides` (TTL 60s) và `users` (TTL 45s). Tự động làm mới ngay lập tức khi có thay đổi số dư, ngôn ngữ hoặc cài đặt giá.
  - Loại bỏ lệnh `SELECT 1` dư thừa trên mỗi kết nối trong `_get_pg_conn()` nếu kết nối vừa hoạt động trong vòng 20 giây.
  - Giới hạn tần suất chạy `expire_old_pending_deposits()` tối đa 5 phút/lần thay vì chạy trên mỗi lượt xem thống kê.
- **Tăng tốc độ mở Menu & Chi tiết sản phẩm trong `bot.py`:**
  - Chuyển `render_product_detail()` sang đọc cache tức thì (`refresh=False`) kết hợp làm mới tồn kho ngầm (`asyncio.create_task`), loại bỏ thời gian chờ API `prodseller.com`.
  - Tối ưu `send_or_edit()` sửa tin nhắn trực tiếp mà không cần gọi thêm RPC `event.get_message()`, tách nút quay lại trên ảnh QR thành `menu:deposit_qr`.
  - **Kết quả đo thực tế:** Thời gian xử lý toàn bộ 29 sản phẩm giảm từ **~10,000 ms (10s)** xuống còn **`0.15 ms` (tức thì)**.

### 📚 Tài liệu hóa (Documentation)
- Tạo mới `PROJECT_OVERVIEW.md`, `PROJECT_CHANGELOG.md` và `AGENTS.md` để lưu trữ toàn bộ ngữ cảnh kỹ thuật cho các phiên làm việc tiếp theo của AI Agent.

---

## [v2.1.0] - 2026-10-16: Tách Biệt Cơ Sở Dữ Liệu Vào Schema Riêng `telebot`

### 🗄️ Cơ sở dữ liệu (Database Schema Isolation)
- Cập nhật `database.py` tự động khởi tạo Schema riêng **`telebot`** trên PostgreSQL (`CREATE SCHEMA IF NOT EXISTS telebot`).
- Tự động di chuyển toàn bộ 5 bảng (`settings`, `users`, `product_overrides`, `deposits`, `orders`) vào trong `telebot.*` (`telebot.settings`, `telebot.users`, `telebot.product_overrides`, `telebot.deposits`, `telebot.orders`).
- Đảm bảo Schema `public` của project Supabase `Base Family` giữ nguyên vẹn 100% (chỉ chứa 15 bảng gốc của `Base Family`, không bị lẫn bất kỳ bảng nào của Bot Tele).

---

## [v2.0.0] - 2026-10-16: Đưa Toàn Bộ Hệ Thống Lên Cloud 24/7 (GitHub + Supabase + Render + Vercel)

### ☁️ Hạ tầng Cloud & Triển khai (Cloud Migration)
- **Supabase PostgreSQL:**
  - Nâng cấp `database.py` hỗ trợ chạy song song **PostgreSQL (`psycopg2`)** qua biến môi trường `DATABASE_URL` (IPv4 Session Pooler cổng `5432`) và **SQLite (`shop.db`)** khi chạy offline.
  - Viết hàm `_migrate_sqlite_to_postgres_if_needed()` tự động chuyển toàn bộ dữ liệu sẵn có từ `shop.db` ở Local (Admin `8110826820`, cấu hình ngân hàng `MB - 882109028888 - CAO THANH TAI`, tỷ giá, đơn nạp) lên Supabase.
- **Render Web Service (`https://kingtool-tele-bot.onrender.com`):**
  - Tích hợp HTTP Health-check Server (`start_health_server()`) mở cổng `$PORT/health` trả về JSON trạng thái sống `200 OK`.
  - Tích hợp vòng lặp `keep_alive_ping_loop()` tự động ping mỗi 10 phút giúp dịch vụ Render Free hoạt động xuyên suốt 24/7.
  - Tạo file `render.yaml` cấu hình Blueprint triển khai tự động.
- **Vercel Serverless (`api/index.py` & `vercel.json`):**
  - Xây dựng trang Web Status Dashboard hiển thị thống kê trực tiếp từ Supabase và kiểm tra trạng thái Render Bot.
- **GitHub CI/CD:**
  - Khởi tạo Git repository, cấu hình `.gitignore` bảo mật tuyệt đối `.env`, `*.session`, `shop.db`, `.venv/`.
  - Đẩy mã nguồn lên `https://github.com/taiketnoi-creator/kingtool-tele-bot` và liên kết tự động với Render.

---

## [v1.0.0] - Giai Đoạn Khởi Tạo (Local Version)

### ✨ Tính năng nền tảng
- Xây dựng Bot Reseller trên **Telethon MTProto** hỗ trợ nút bấm màu sắc (`success`, `primary`, `danger`) và Custom Emoji Icons giống `@ProdSellerBot`.
- Kết nối **ProdSeller Official API v1** đồng bộ sản phẩm, gom nhóm Sub-plans (`Gmail`, `ChatGPT CODEX`, `Claude AI`, `CapCut`, `Canva`) và mua key tự động.
- Đồng bộ hiển thị 100% tiền tệ **Việt Nam Đồng (VNĐ)**, hỗ trợ nhập số lượng tùy chỉnh và kiểm tra điều kiện mua tối thiểu.
- Tích hợp thanh toán **VietQR** tự động sinh mã QR kèm nội dung đối soát `KINGTOOL CAM ON SPX...`.
- Tích hợp chế độ **Duyệt nạp Hybrid**: Duyệt tay 1 chạm qua Telegram ban ngày + Tự động đối soát qua **SePay API** ban đêm (`23h00 - 06h00`) trong giới hạn 50 giao dịch miễn phí/tháng.
- Xây dựng hệ thống **Hạng thành viên VIP** (`Bronze`/`Silver`/`Gold`), **Điểm thưởng Cashback** đổi ra số dư ví và **Link giới thiệu (`REF_`)** hưởng hoa hồng tự động khi bạn bè nạp tiền.
- Xây dựng **Bảng điều khiển Admin (`/admin`)** ngay trên Telegram: chỉnh % Markup, cộng thêm VNĐ cố định, chỉnh tỷ giá, đặt giá riêng/ẩn hiện từng sản phẩm, tìm kiếm user, cộng/trừ tiền và gửi thông báo `/broadcast`.
