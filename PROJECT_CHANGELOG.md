# 📜 LỊCH SỬ CHỈNH SỬA & NÂNG CẤP DỰ ÁN (PROJECT CHANGELOG)
## 🤖 Dự án: KingTool Shop Telegram Reseller Bot (`@KingToolShop_bot`)

> Mọi thay đổi về tính năng, kiến trúc cơ sở dữ liệu, tối ưu hiệu năng và triển khai Cloud đều được ghi nhận tại đây theo thứ tự thời gian mới nhất ở trên.

---

## [v2.5.0] - 2026-10-17: Bộ 4 Tính Năng Vận Hành Tự Động & Tăng Doanh Thu (Cảnh Báo Vốn, Báo Restock Kênh, Khuyến Mãi Nạp Tiền, Bảo Hành 1 Chạm)

### 🚀 4 Nâng cấp vận hành & bán hàng tự động
1. **🔔 Cảnh báo "Số dư Vốn ProdSeller sắp hết" cho Admin (`low_balance_threshold_usd`):**
   - Tự động kiểm tra số dư ví USDT bên `@ProdSellerBot` ngay sau mỗi đơn hàng và định kỳ trong vòng lặp đồng bộ.
   - Khi số dư vốn tụt xuống dưới ngưỡng cài đặt (mặc định `$5.00`, có cooldown 4 giờ chống spam), Bot lập tức gửi báo động khẩn cấp về Telegram Admin để kịp nạp vốn trước khi khách mua bị lỗi.
2. **📣 Tự động đăng thông báo "Hàng Về (Restock)" lên Kênh `@KingToolShopOfficial` (`restock_notify_enabled`):**
   - Vòng lặp `poll_products_sync_loop` theo dõi biến động tồn kho `_LAST_KNOWN_STOCK` mỗi 60 giây.
   - Khi phát hiện sản phẩm đang hết hàng (`0`) có hàng trở lại (`> 0`), Bot tự động đăng bài báo Restock lên kênh kèm nút **Deep-link `🛒 Mua ngay`** (`?start=BUY_<product_id>`) mở thẳng màn hình mua sản phẩm đó trong 1 chạm.
3. **🎁 Khuyến mãi Nạp Tiền tự động theo mốc (`deposit_bonus_enabled`, `deposit_bonus_tiers`):**
   - Mặc định tặng thêm **`+5%`** khi nạp từ `200,000đ` và **`+10%`** khi nạp từ `500,000đ` (hiển thị nhãn `🎁 (+5%)`, `🎁 (+10%)` trực tiếp trên nút chọn mệnh giá nạp tiền).
   - Tự động cộng tiền thưởng vào ví khách hàng cả khi Admin bấm `✅ Duyệt` lẫn khi SePay tự động duyệt ban đêm (`23h-06h`).
4. **🛠️ Nút "Bảo hành / Báo lỗi đơn hàng 1 chạm" & Phản hồi trực tiếp (`warr:ask:<id>` & `adm:warr_reply:`):**
   - Trong mục `👤 Hồ sơ -> 📦 Đơn hàng đã mua`, mỗi đơn hàng có nút `🛠️ Bảo hành #<id>`.
   - Khách bấm vào và nhập mô tả lỗi -> Bot gửi ngay phiếu yêu cầu bảo hành đầy đủ thông tin (kèm mã đơn gốc `prodseller_order_id` và Key đã giao) về Telegram Admin.
   - Admin chỉ cần bấm nút **`💬 Phản hồi / Đổi Key đơn #<id>`** ngay dưới thông báo để gửi Key bảo hành mới hoặc tin nhắn hỗ trợ trực tiếp tới khách qua Bot.

---

## [v2.4.0] - 2026-10-17: Cổng Public Reseller API v1 (`/v1/*`), Trang Tài Liệu `/api-docs` & Hướng Dẫn Dễ Hiểu Cho Khách Hàng

### 🔌 Tính năng Public Reseller API v1 (Đồng bộ 100% cấu trúc `@ProdSellerBot`)
- **Cơ sở dữ liệu (`database.py` - Schema `telebot`):**
  - Bổ sung bảng `telebot.api_keys` (`user_id`, `api_key` dạng `ktk_...`, `total_requests`, `active`, `created_at`) vào `_TABLE_NAME_RE` và `_init_db()` kèm RAM Cache.
  - Hỗ trợ tạo mã tự động (`get_or_create_api_key`), ẩn/hiện mã (`mask_api_key` dạng `ktk_763b46••••••••••••••••••2030`), cấp lại mã mới (`regenerate_api_key`), và xác thực nhanh (`authenticate_api_key`).
- **Giao diện nút `API` trên Telegram Bot (`bot.py` & `i18n.py`):**
  - Hiển thị mã API Key cá nhân của từng khách hàng, Base URL, tổng lượt gọi API (`total_requests`) và ngày tạo.
  - Trang bị 4 nút chức năng: `👁 Hiện toàn bộ Key` / `🙈 Ẩn bớt Key`, `♻️ Tạo lại Key mới`, **`💡 API này là gì? Hướng dẫn dễ hiểu`** (giải thích rõ cho cả khách mua lẻ lẫn chủ Shop/Web/MMO), và nút mở trang **`📖 Tài liệu kỹ thuật API (API Docs)`**.
- **Máy chủ HTTP Public API v1 & Tài liệu Dark-Mode (`public_api.py`):**
  - Tích hợp trực tiếp vào cổng HTTP trên Render (`https://kingtool-tele-bot.onrender.com`) với đầy đủ 6 cổng chuẩn REST:
    - `GET /v1/balance`: Kiểm tra số dư ví VNĐ và hạng VIP của đại lý.
    - `GET /v1/products` & `GET /v1/products/:id`: Lấy danh sách sản phẩm, tồn kho và đơn giá VNĐ đã trừ chiết khấu VIP của đại lý (luôn có chốt chặn chống lỗ vốn `>= cost_vnd`).
    - `POST /v1/orders`: Đặt mua hàng tự động bằng số dư ví VNĐ (hỗ trợ `Idempotency-Key` chống trùng đơn), tự động lấy Key từ kho tổng ProdSeller trả về trong 1 giây và báo đơn về Telegram Admin.
    - `GET /v1/orders` & `GET /v1/orders/:id`: Tra cứu lịch sử đơn hàng và trạng thái đơn kích hoạt Email.
  - Xây dựng trang tài liệu Dark-Mode tại `/api-docs` kèm ví dụ mẫu bằng Python và Node.js.

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
