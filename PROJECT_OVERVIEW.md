# 📘 TỔNG QUAN DỰ ÁN & KIẾN TRÚC KỸ THUẬT (PROJECT OVERVIEW)
## 🤖 Dự án: KingTool Shop Telegram Reseller Bot (`@KingToolShop_bot`)

> **Tài liệu dành cho AI Agent & Developer:** File này mô tả toàn bộ cấu trúc, luồng nghiệp vụ, cơ sở dữ liệu, hạ tầng Cloud và các quy tắc bất khả xâm phạm của dự án. Bất kỳ AI Agent nào tiếp nhận dự án **BẮT BUỘC** đọc kỹ file này và `PROJECT_CHANGELOG.md` trước khi thực hiện thay đổi.

---

## 1. Mục Đích & Mô Hình Kinh Doanh

- **Mô hình:** Bot Telegram bán tài khoản/phần mềm số tự động 24/7 theo mô hình **Reseller Đa Nguồn (Multi-Source Reseller)**.
- **Nguồn hàng gốc (Upstream Providers):**
  - **Nguồn 1 (Kho chính):** **ProdSeller Official API v1** (`https://prodseller.com/v1` - `@ProdSellerBot`).
  - **Nguồn 2 (Kho dự phòng tự động):** **DanteHub Partner API v1** (`https://dantehub.shop/api/public/v1` - `@DanteHubBot`) cùng hệ thống Kho Key nội bộ (`telebot.backup_sources`).
- **Luồng hoạt động cốt lõi:**
  1. Bot tự động đồng bộ danh sách sản phẩm, mô tả, giá vốn (USD/USDT) và số lượng tồn kho (`stock`) từ `@ProdSellerBot` (Nguồn 1) kết hợp 17+ nguồn hàng dự phòng tự động từ `@DanteHubBot` (Nguồn 2).
  2. Tự động quy đổi giá vốn USD sang **Việt Nam Đồng (VNĐ)** theo tỷ giá cài đặt và áp dụng thuật toán **Bình Ổn Giá Thông Minh (`markup_percent = 200%`, khóa sàn lợi nhuận tối thiểu `min_profit_percent = 150%` bằng làm tròn lên `_round_ceil_nice_vnd`)**.
  3. Khách hàng nạp tiền vào ví trên Bot bằng **Chuyển khoản Ngân hàng VietQR** (có mã đối soát `KINGTOOL CAM ON SPX...`).
  4. Khi khách bấm mua hàng -> Bot trừ số dư ví VNĐ nguyên tử (Atomic) -> Tự động định tuyến đơn hàng sang Nguồn 1 (`@ProdSellerBot`), nếu Nguồn 1 hết hàng hoặc thiếu số lượng sẽ tự động bù từ Nguồn 2 (`@DanteHubBot` hoặc Kho Key dự phòng) -> Trả Key/Tài khoản ngay lập tức cho khách (hoặc theo dõi ngầm đơn `processing` đến khi hoàn tất).

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
6. **`telebot.vouchers`**:
   - `code TEXT PRIMARY KEY`, `discount_type TEXT` (`percent` / `fixed`), `discount_value NUMERIC(18,2)`, `max_uses INTEGER` (`0` = không giới hạn), `used_count INTEGER`, `active INTEGER` (`1` = bật, `0` = tắt), `created_at TEXT`.
7. **`telebot.voucher_usages`**:
   - `id BIGSERIAL PRIMARY KEY`, `code TEXT`, `user_id BIGINT`, `order_id BIGINT`, `discount_amount BIGINT`, `used_at TEXT`, `UNIQUE(code, user_id)` (mỗi khách chỉ được dùng 1 lần cho mỗi mã).
8. **`telebot.api_keys`**:
   - `user_id BIGINT PRIMARY KEY`, `api_key TEXT UNIQUE` (`ktk_...`), `total_requests BIGINT`, `active INTEGER`, `created_at TEXT`.
9. **`telebot.backup_sources`**:
   - `id BIGSERIAL PRIMARY KEY`, `product_id TEXT`, `source_name TEXT` (tên Bot/Kho phụ), `source_type TEXT` (`local_stock` = kho Key nạp sẵn từ Bot khác, `api` = đấu nối API Reseller khác), `cost_vnd BIGINT` (giá vốn VNĐ của nguồn phụ), `stock_keys TEXT` (JSON array các Key/Tài khoản dự phòng), `api_base_url TEXT`, `api_key TEXT`, `remote_product_id TEXT`, `remote_stock INTEGER`, `active INTEGER`, `created_at TEXT`.

---

## 5. Các Nghiệp Vụ & Thuật Toán Quan Trọng

### 5.1. Công thức Giá bán, Hạng VIP, Mã Giảm Giá (Voucher), Bình Ổn Giá Đa Nguồn & Khóa Sàn Lãi `>= 150%`
- **Giá vốn VNĐ Kho chính (`primary_cost_vnd`)**: `round(wholesale_usd * vnd_rate)`.
- **Giá bán lẻ chuẩn Kho chính (`primary_base_vnd`)**:
  - Nếu sản phẩm có `custom_price` trong `product_overrides` -> dùng `custom_price`.
  - Nếu không -> `primary_cost_vnd * (1 + markup_percent / 100) + markup_fixed` (Mặc định `markup_percent = 200.0%`), làm tròn đẹp tới `500đ` hoặc `1,000đ`.
- **🛡️ Bình Ổn Giá Đa Nguồn & Khóa Sàn Lợi Nhuận Tối Thiểu (`min_profit_percent = 150.0%` - `v2.7.0`):**
  - Khi Kho chính (`@ProdSellerBot`) còn hàng: Lấy hàng từ Kho chính và bán theo giá chuẩn `+200%` (`primary_base_vnd`).
  - Khi Kho chính hết hàng (`stock = 0`) hoặc thiếu số lượng: Hệ thống tự động bù hàng từ các **Nguồn Dự Phòng (`telebot.backup_sources`)** đang bật và còn hàng (ưu tiên nguồn có `cost_vnd` rẻ nhất trước).
  - **Công thức Bình ổn giá thông minh (`compute_stabilized_unit_price`):**
    $$\text{Giá bán bình ổn} = \max\Big(\text{Giá chuẩn Kho chính (+200\%)},\; \text{Giá vốn nguồn đang chạy} \times \big(1 + \frac{\text{min\_profit\_percent}}{100}\big)\Big)$$
    - Nếu giá vốn nguồn dự phòng chỉ nhỉnh hơn nhẹ so với Kho chính (sao cho bán ở mức giá chuẩn vẫn đạt lãi **`>= 150%`**): **Giữ nguyên 100% giá bán trên Bot** để khách hàng không thấy giá bị nhảy thất thường.
    - Nếu giá vốn nguồn dự phòng cao hơn khiến lãi tại giá cũ tụt xuống dưới `150%`: Tự động nhích nhẹ giá bán lên đúng ngưỡng đảm bảo **tỷ suất lợi nhuận không bao giờ thấp hơn `150%`**.
- **Chiết khấu Hạng thành viên (`TIER_DISCOUNTS`)**:
  - `BRONZE` (< `600,000đ` chi tiêu): giảm `0%`.
  - `SILVER` (>= `600,000đ` chi tiêu): giảm `3%`.
  - `GOLD` (>= `2,500,000đ` chi tiêu): giảm `5%`.
- **Mã giảm giá (`Voucher System` - `compute_order_pricing`)**:
  - Khách hàng bấm `🎟️ Nhập mã giảm giá (Voucher)` ngay trên nút `💳 Mua ngay` ở màn hình Chi tiết sản phẩm.
  - Hỗ trợ giảm theo `%` (làm tròn bậc `500đ`) hoặc giảm số tiền VNĐ cố định, kiểm tra số lượt tối đa (`max_uses`) và giới hạn mỗi khách 1 lần/mã (`telebot.voucher_usages`).
  - Admin quản lý trực tiếp trong `/admin` -> `🎟️ Quản lý Voucher` (Tạo mã nhanh 5 giây, Bật/Tắt 1 chạm, Xóa mã).
- **🛡️ Nguyên tắc bất khả xâm phạm (Chống lỗ vốn & Bảo vệ sàn lãi nguồn phụ):**
  - Mọi mức giảm giá (VIP + Voucher kết hợp, hoặc gọi qua cổng Public Reseller API `/v1/*`) đều phải qua chốt chặn `total_final_vnd >= total_cost_vnd` (và giữ vững sàn lãi `>= min_profit_percent` khi xuất từ nguồn hàng dự phòng).

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

### 5.4. Cổng Public Reseller API v1 (`public_api.py` - `/v1/*` & `/api-docs`)
- Cung cấp mã `ktk_...` riêng cho từng khách hàng tại nút `API` trên Bot (hỗ trợ `👁 Hiện toàn bộ Key`, `♻️ Tạo lại Key mới`, `💡 Hướng dẫn dễ hiểu` và trang web `/api-docs`).
- Hỗ trợ 6 cổng REST API chuẩn (`GET /v1/balance`, `GET /v1/products`, `GET /v1/products/:id`, `POST /v1/orders`, `GET /v1/orders`, `GET /v1/orders/:id`) giúp các chủ Website/Bot đại lý con đấu nối lấy hàng tự động bằng số dư ví VNĐ.

### 5.5. Bộ 4 Tính Năng Vận Hành Tự Động & CSKH (`v2.5.0`)
- **Cảnh báo sắp hết vốn ProdSeller (`low_balance_threshold_usd`):** Báo động về Telegram Admin khi số dư vốn USDT tại `@ProdSellerBot` thấp hơn ngưỡng cài đặt (mặc định `$5.00`).
- **Tự động đăng thông báo Hàng Về (Restock) lên Kênh (`restock_notify_enabled`):** Khi sản phẩm từ hết hàng (`0`) chuyển sang có hàng (`> 0`), tự động đăng thông báo lên `@KingToolShopOfficial` kèm nút Deep-link `?start=BUY_<product_id>` mở thẳng màn hình mua sản phẩm.
- **Khuyến mãi nạp tiền theo mốc (`deposit_bonus_enabled`, `deposit_bonus_tiers`):** Tự động cộng thêm `%` tiền thưởng khi khách nạp đạt mốc (mặc định `200,000đ -> +5%`, `500,000đ -> +10%`), áp dụng cho cả duyệt tay và SePay ban đêm.
- **Bảo hành 1 chạm & Phản hồi trực tiếp (`warr:ask:<id>` / `adm:warr_reply:`):** Khách bấm nút bảo hành ngay trong lịch sử đơn hàng, Admin nhận phiếu kèm mã đơn ProdSeller và bấm nút phản hồi/đổi Key trực tiếp qua Bot.

### 5.6. Hệ Thống Tự Động Đăng Bài Kênh & Phễu Thu Hút Khách Hàng (`v2.6.0`)
- **⏰ Tự động đăng bài định kỳ theo khung giờ vàng (`auto_post_enabled`, `auto_post_hours = "9,14,20"`):**
  - Tự động đăng & ghim Bảng giá + Tồn kho mới nhất lên `@KingToolShopOfficial` vào lúc `09:00`, `14:00`, `20:00` (Giờ VN) và tự động xóa bài Bảng giá cũ (`last_catalog_msg_id`) để kênh luôn sạch đẹp.
  - Đi kèm bài **🔥 Spotlight Sản Phẩm Hot Trong Ngày** (`post_spotlight_to_channel`) giới thiệu chi tiết sản phẩm kèm mức giá sau khi áp mã Tân Thủ và nút Deep-link `🛒 Mua ngay` (`?start=BUY_<pid>`).
- **🎁 Phễu "Tham gia Kênh nhận Quà Tân Thủ" (`newbie_gift_enabled`, `?start=GIFT`):**
  - Hiển thị nút `🎁 Nhận Quà Tân Thủ (Miễn Phí)` ngay trên Menu Chính cho khách mới (`users.gift_claimed = 0`).
  - Kiểm tra khách đã tham gia kênh `@KingToolShopOfficial` qua Telethon (`get_permissions`). Ngay khi khách Join kênh và bấm nhận quà, hệ thống cộng **+5 Điểm thưởng** và **tự động kích hoạt sẵn mã giảm giá `TANTHU10` (-10%)** vào giỏ hàng để khách xem bất kỳ sản phẩm nào cũng thấy giá đã được giảm ngay (vẫn tuân thủ tuyệt đối chốt chặn `>= cost_vnd`).
- **🤖 Tạo hiệu ứng đám đông tự động (`auto_social_proof_enabled`):**
  - Định kỳ trong khung `08:00 – 22:00`, tự động đăng thông báo hoàn tất đơn hàng lên kênh (kèm xóa bài mồi cũ để không làm loãng kênh), tạo niềm tin và độ sôi động cho khách mới vào xem.
- **💡 Nhắc nhở tự động khi khách bỏ dở đơn nạp tiền (`deposit_reminder_enabled`):**
  - Tự động phát hiện đơn nạp VietQR đang `pending` sau `10–45 phút` chưa hoàn tất và gửi tin nhắn nhắc nhở nhẹ nhàng kèm thông tin ưu đãi nạp tiền (`+5% / +10%`) và nút báo duyệt 1 chạm.

### 5.7. Cơ chế Tối Ưu Tốc Độ Phản Hồi (`0.15ms` RAM Cache)
- Vì Render đặt tại **Singapore** còn Supabase đặt tại **Sydney (`ap-southeast-2`)**, `database.py` sử dụng **Write-Through RAM Cache** cho `settings` (TTL 60s), `product_overrides` (TTL 60s), `vouchers` (TTL 60s), `backup_sources` (TTL 60s), `api_keys` (TTL 45s) và `users` (TTL 45s).
- Tuyệt đối **KHÔNG** thực hiện truy vấn SQL lặp trong vòng lặp hiển thị danh sách sản phẩm (tránh lỗi N+1 Query).
- `prodseller_client.py` sử dụng cơ chế **Stale-While-Revalidate**: trả về danh sách sản phẩm từ RAM ngay lập tức (`force=False`) và đồng bộ ngầm mỗi 45 giây.

---

## 6. Định Hướng Phát Triển Tiếp Theo (Roadmap)

- **Tính năng đã hoàn thành gần nhất (`v2.3.0`, `v2.4.0`, `v2.5.0`, `v2.6.0` & `v2.7.0`):**
  - **Hệ thống Mã Giảm Giá (Voucher System - bảng `telebot.vouchers` & `telebot.voucher_usages`)** kèm chốt chặn bảo vệ giá vốn (`total_final_vnd >= total_cost_vnd`).
  - **Cổng Public Reseller API v1 (`public_api.py` - bảng `telebot.api_keys`) & Trang tài liệu `/api-docs`** kèm mục giải thích dễ hiểu cho khách hàng trên Bot.
  - **Bộ 4 tính năng vận hành tự động (`v2.5.0`):** Cảnh báo hết vốn ProdSeller, Tự động đăng Restock lên Kênh kèm Deep-link mua ngay, Khuyến mãi nạp tiền theo mốc, và Bảo hành 1 chạm trong Lịch sử đơn hàng.
  - **Hệ thống Tự Động Đăng Bài Kênh & Phễu Thu Hút Khách Hàng (`v2.6.0`):** Tự động đăng Bảng giá + Spotlight SP Hot theo khung giờ (`9h, 14h, 20h`, tự xóa bài cũ), Phễu bắt buộc Join Kênh nhận Quà Tân Thủ (`+5 điểm` + tự động gắn mã `TANTHU10`), Tự động tạo hiệu ứng đơn hàng hoàn tất (Social Proof), và Tự động nhắc khách hoàn tất đơn nạp VietQR bỏ dở sau 10 phút.
  - **Hệ thống Đa Nguồn Hàng Dự Phòng Tự Động Chuyển Đổi (Multi-Source Failover) & Bình Ổn Giá Thông Minh (`v2.7.0`):** Tự động bù hàng từ Kho Key dự phòng (lấy từ các Bot khác) hoặc API phụ khi `@ProdSellerBot` hết hàng; giữ nguyên giá bán chuẩn `+200%` nếu biên lợi nhuận đạt `>= 150%` và tự động nâng sàn giá vừa đủ để khóa chặt tỷ suất lợi nhuận không bao giờ thấp hơn `150%`.

---

## 7. Quy Tắc Bắt Buộc Cho AI Agent Khi Chỉnh Sửa Dự Án

1. **Bảo mật:** Không bao giờ commit file `.env`, `*.session`, `shop.db` lên Git.
2. **Database Schema:** Mọi bảng mới thêm vào `database.py` phải được thêm vào biểu thức chính quy `_TABLE_NAME_RE` để tự động nằm trong Schema `telebot.*` trên Supabase (tuyệt đối không làm bẩn Schema `public` của dự án `Base Family`).
3. **Hiệu năng:** Khi đọc cấu hình hoặc tính giá trong vòng lặp, luôn dùng dữ liệu từ RAM Cache (`get_all_settings()`, `get_all_overrides()`, `get_all_backup_sources()`), không gọi truy vấn mạng lẻ tẻ.
4. **Đồng bộ Cloud:** Sau mỗi lần chỉnh sửa code tại Local, cần kiểm tra cú pháp Python, chạy `git add`, `git commit`, `git push origin main` để Render tự động cập nhật bản mới và ghi chú lại vào `PROJECT_CHANGELOG.md`.
