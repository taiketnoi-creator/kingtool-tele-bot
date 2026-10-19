# 📜 LỊCH SỬ CHỈNH SỬA & NÂNG CẤP DỰ ÁN (PROJECT CHANGELOG)
## 🤖 Dự án: KingTool Shop Telegram Reseller Bot (`@KingToolShop_bot`)

> Mọi thay đổi về tính năng, kiến trúc cơ sở dữ liệu, tối ưu hiệu năng và triển khai Cloud đều được ghi nhận tại đây theo thứ tự thời gian mới nhất ở trên.

---

## [v2.9.2] - 2026-10-19: Tối Ưu Giao Diện Quản Trị `/admin` Dạng Thư Mục (6 Folder Chức Năng Gọn Đẹp, Không Rối Mắt)

### 📂 Gom Nhóm 26 Nút Cài Đặt Admin Vào 6 Thư Mục Chức Năng (`bot.py`)
- **Màn hình chính `/admin` (`render_admin_home`):**
  - Rút gọn từ 14 hàng (27 nút rời rạc) xuống còn **5 hàng gọn đẹp**:
    - Hàng thao tác nhanh trên cùng: `⏳ Đơn nạp chờ duyệt` | `📦 10 Đơn gần nhất`.
    - **6 Thư mục quản trị chuyên biệt (`adm:dir:<folder>`):**
      1. `📁 Kho Hàng & Nguồn Cung` (`adm:dir:catalog`): Quản lý 143 SP & Nguồn dự phòng, Đồng bộ Kho chính, Đồng bộ `@DanteHubBot`, Cài API Key `@DanteHubBot`, Mốc cảnh báo hết vốn (`$`).
      2. `📁 Cài Đặt Giá & Lãi` (`adm:dir:pricing`): Markup chuẩn (`+200%`), Sàn lãi tối thiểu (`>=150%`), Cộng `+VNĐ` cố định, Đổi tỷ giá `USD -> VNĐ`, Đặt giá riêng từng SP.
      3. `📁 Kênh & Auto Đăng Bài` (`adm:dir:marketing`): Đăng Bảng Giá Kênh ngay, Đăng Bài SP Hot ngay, Bật/Tắt Auto Đăng Kênh (`9h,14h,20h`), Bật/Tắt Báo Restock, Bật/Tắt Đơn Mồi Kênh, Bật/Tắt Quà Tân Thủ.
      4. `📁 Voucher & KM Nạp` (`adm:dir:promos`): Quản lý Voucher, Tạo Voucher nhanh 5s, Bật/Tắt KM Nạp, Chỉnh Mốc KM Nạp, Bật/Tắt Nhắc đơn nạp bỏ dở.
      5. `📁 Ngân Hàng & SePay` (`adm:dir:payment`): Duyệt đơn nạp chờ, Cài Ngân hàng VietQR, Cài Token SePay tự động ban đêm (`23h-06h`).
      6. `📁 Quản Lý Khách Hàng` (`adm:dir:users`): Tra cứu Khách hàng, Cộng/Trừ tiền khách (VNĐ), Gửi thông báo toàn hệ thống (Broadcast), 10 Đơn gần nhất, Sửa bài Hướng dẫn (Methods).
- **Trải nghiệm mượt mà trong từng Thư mục (`render_admin_folder` & `SETTING_PARENT_FOLDER`):**
  - Khi bấm Bật/Tắt hoặc chỉnh sửa bất kỳ thông số nào bên trong thư mục, hệ thống tự động cập nhật và giữ nguyên màn hình tại thư mục đó (không bị văng ngược ra ngoài màn hình chính).

---

## [v2.9.1] - 2026-10-19: Giao Diện Lưới Thương Hiệu 2–3 Cột (Brand Grid UI) — Chỉ Hiển Thị `Icon + Tên Sản Phẩm`, Giá Bán Hiển Thị Khi Xem Chi Tiết

### 🎨 1. Bảng Lưới Thương Hiệu 2–3 Cột Chuẩn Mực (`prodseller_client.py` & `bot.py`)
- **Thiết kế lại `render_products_menu` dạng Bảng Lưới 2–3 cột (`BRAND_GRID_ROWS`):**
  - Sắp xếp 65+ thương hiệu phần mềm/AI (`ChatGPT`, `Gemini`, `Claude`, `Notion`, `Cursor`, `CapCut`, `Canva`, `YouTube`, `Spotify`, `Netflix`, `Adobe`, `Microsoft`, `Figma`, `Grammarly`, `Duolingo`, `ElevenLabs`, `Lovable`, `Coursera`, `Bolt`, `Gamma`, `Kling`, `Leonardo`, `Manus`, `Muse AI`, `Replit`, `Wispr Flow`, `Apple`, `Apple Music`, `MiniMax`, `NordVPN`, `VPN`, `Udemy`, `Higgsfield`, `Intercom`, `Suno`, `Surfshark`, `TV360`, `X`, `Autodesk`, `Descript`, `Discord Nitro`, `Facebook`, `Framer`, `Granola`, `Gumloop`, `HBO Max`, `HeyGen`, `Groq`, `Grok`, `JetBrains`, `Krea`, `Linear`, `LinkedIn`, `Make`, `Malwarebytes`, `Medium`, `Miro`, `n8n`, `Perplexity`, `Picsart`, `PlayStation`, `PostHog`, `Quizlet`, `Raycast`, `Riot Games`, `Scribd`, `Singular`, `SketchUp`, `Superhuman`, `Supabase`, `Tinder`, `TradingView`, `TypingMind`, `Veeam`, `Vercel`, `VidIQ`, `VieON`, `Voicemod`, `Warp`, `Webflow`...) thành các hàng ngang 2–3 nút bấm cân đối như ảnh mẫu của chủ shop.
  - Nút thương hiệu đang sẵn hàng dùng kiểu trong suốt mặc định của Telegram (`style=None`), nút tạm hết sạch cả 2 kho hiển thị màu đỏ (`style="danger"`).
  - Tích hợp trọn bộ **60+ Custom Emoji ID chính gốc (`GROUP_ICONS`)** kèm bộ Icon Emoji dự phòng (`GROUP_EMOJI`).

### 🏷️ 2. Tối Giản Nút Bấm (`Icon + Tên SP`) & Hiển Thị Giá Khi Xem Trực Tiếp (`render_product_detail`)
- **Loại bỏ hoàn toàn giá tiền và số lượng gói khỏi nút bấm bên ngoài:**
  - Trên cả Bảng Lưới Thương Hiệu lẫn Danh sách gói con bên trong từng thương hiệu, mỗi nút bấm chỉ hiển thị **`Icon + Tên Sản Phẩm`** giúp giao diện thoáng, sạch sẽ, không bị rối mắt khi kho hàng lên tới 143 sản phẩm.
  - **Mở thẳng 1 chạm (`1-Click Direct Detail`):** Nếu một thương hiệu chỉ có duy nhất 1 gói sản phẩm (ví dụ `Netflix`, `YouTube`, `Spotify`, `Coursera`...), khi khách bấm vào nút thương hiệu trên bảng lưới, Bot sẽ mở thẳng trang chi tiết sản phẩm kèm giá bán VNĐ ngay lập tức (và nút `« Quay lại` sẽ đưa khách về thẳng Bảng Lưới Thương Hiệu).
  - **Trang chi tiết sản phẩm (`render_product_detail`):** Hiển thị đầy đủ tên gói, mô tả quyền lợi, **Giá bán VNĐ (`💵 Giá bán: XX,XXXđ`)**, ưu đãi Hạng VIP, nút áp mã giảm giá (Voucher) và nút chọn số lượng mua (`1x`, `2x`, `5x`, `10x`).

---

## [v2.9.0] - 2026-10-19: Hợp Nhất Toàn Bộ Kho Hàng `@ProdSellerBot` + `@DanteHubBot` (143 Sản Phẩm — Gộp Chung 21 SP Trùng & Mở Bán 102 SP Độc Quyền)

### 🛍️ 1. Hợp nhất danh mục 2 nguồn thành Siêu Kho Hàng 143 Sản Phẩm (`prodseller_client.py`)
- **Nguyên tắc "Sản phẩm dùng chung thì hiển thị chung — Sản phẩm riêng của từng Bot đều lấy về bán":**
  - **21 Sản phẩm dùng chung (`DEFAULT_DANTE_MAPPINGS`):** Các mặt hàng có ở cả `@ProdSellerBot` và `@DanteHubBot` (Adobe Express, Office 365, Gemini Pro, Duolingo Super, Muse AI, Scribd, YouTube Premium, CapCut Pro, Wispr Flow, Figma Pro Edu, JetBrains Edu, Notion Plus, Canva Pro Admin/Edu, ElevenLabs, ChatGPT Plus K12, Apple TV, Surfshark VPN, Claude API, Codex API) được **hiển thị chung 1 lần duy nhất** trên `@KingToolShop_bot`. Khi khách mua, Bot ưu tiên lấy từ `@ProdSellerBot` (lãi chuẩn `+200%`) và tự động chuyển sang lấy từ `@DanteHubBot` nếu `@ProdSellerBot` hết hàng (áp dụng Bình ổn giá khóa sàn lãi `>= 150%`).
  - **102 Sản phẩm độc quyền từ `@DanteHubBot` (`provider="dantehub"`, mã định danh rút gọn `dh_<21_hex>`):** Toàn bộ các sản phẩm chỉ có trên `@DanteHubBot` (Netflix 4K, Cursor Pro/Ultra, Grok Super, Kling AI, Suno Premier, HeyGen, Higgsfield, Leonardo AI, Midjourney/Gamma, Lovable Pro, Bolt.new, n8n Cloud, Coursera, Udemy, Elsa Speak, NordVPN, Kaspersky, TradingView, LinkedIn, Discord Nitro, X Premium, TV360, VieON...) được tự động đồng bộ trực tiếp vào cửa hàng `@KingToolShop_bot`, tính giá bán lẻ VNĐ tự động theo công thức `+200%` Markup chuẩn và xuất hàng trực tiếp qua API `@DanteHubBot` (`DANTE_<order_id>`).

### 📂 2. Phân loại 17 Nhóm Dịch Vụ Thông Minh & Phân Trang Siêu Tốc (`bot.py` & `i18n.py`)
- Mở rộng hàm `detect_plan_group(product_name, category)` thành **17 nhóm dịch vụ** trực quan kèm nút **`📋 Xem Tất Cả 143 Sản Phẩm (Từng Trang)`** (`grp:__ALL__:0`) và thanh điều hướng phân trang (`16 SP/trang`), đảm bảo không bao giờ vượt giới hạn 100 nút Inline Keyboard của Telegram và ưu tiên đưa các sản phẩm đang sẵn hàng (`🟢`) lên đầu mỗi danh mục.
- Tự động bổ sung mô tả tiếng Việt/tiếng Anh chuẩn chỉnh (`localize_product_description`) cho các sản phẩm độc quyền từ `@DanteHubBot`.

---

## [v2.8.0] - 2026-10-19: Tích Hợp Trực Tiếp Nguồn Hàng Thứ 2 `@DanteHubBot` (DanteHub Partner API v1) & Đấu Nối Tự Động 17 Sản Phẩm Dự Phòng

### 🔌 1. Tích hợp Native `@DanteHubBot` Partner API v1 (`prodseller_client.py` & `database.py`)
- **Kết nối trực tiếp cổng API `@DanteHubBot` (`https://dantehub.shop/api/public/v1`):**
  - Lưu trữ `dante_api_key` (`dh_live_...`) và `dante_base_url` trong bảng `telebot.settings` trên Supabase PostgreSQL.
  - Bổ sung bộ phương thức chuyên biệt trong `ProdSellerClient`:
    - `get_external_balance()`: Kiểm tra số dư ví USDT trực tiếp trên `@DanteHubBot` (`GET /balance`).
    - `fetch_dantehub_catalog()`: Đồng bộ toàn bộ 124 sản phẩm từ `@DanteHubBot` (`GET /products`) chỉ bằng **1 request HTTP duy nhất** (kèm RAM Cache 60s), chuẩn hóa trường `title` và `in_stock` (boolean).
    - `create_external_api_order()` & `get_external_api_order_status()`: Hỗ trợ đặt hàng tự động chuẩn DanteHub (`POST /orders` với `{"product_id", "qty", "ref"}` chống trùng lặp), tự động chờ nhanh 2 nhịp (`1.5s + 2.0s`) để lấy `delivery` ngay nếu đơn ở trạng thái `processing`, đồng thời tích hợp vào vòng lặp `poll_pending_activations_loop()` (`bot.py`) để tự động gửi Key cho khách ngay khi đơn `EXT_<sid>_<order_id>` chuyển sang `delivered` (hoặc tự động hoàn tiền VNĐ nếu đơn bị `cancelled`).
- **Làm tròn lên tuyệt đối cho Khóa Sàn Lợi Nhuận (`_round_ceil_nice_vnd` trong `database.py`):**
  - Đảm bảo khi nâng giá theo sàn lợi nhuận tối thiểu (`min_profit_percent = 150%`), hệ thống luôn làm tròn lên (`math.ceil`) tới hàng nghìn VNĐ, cam kết tỷ suất lợi nhuận thực tế luôn đạt **`>= 150.0%`** (không bao giờ bị làm tròn xuống `149%`).

### 🔗 2. Tự động đấu nối 17 Sản Phẩm Dự Phòng & Gắn Nhanh 1 Chạm trong `/admin` (`bot.py`)
- **Đấu nối sẵn 17 sản phẩm tương đương (`DEFAULT_DANTE_MAPPINGS` & `sync_all_dante_backups`):**
  - Tự động liên kết 17 sản phẩm trùng khớp giữa `@ProdSellerBot` và `@DanteHubBot` (Adobe Express 12M, Office 365 1Y, Duolingo Super 12M, Gemini Pro 18M, Muse AI 1B, Scribd 1M, Canva Pro, Notion Plus 12M, YouTube Premium 1M, CapCut Pro 1M, CapCut Pro 1600 Credits, ElevenLabs Credit, Wispr Flow 12M, Figma Pro Edu 2Y, JetBrains Edu 12M, Canva Admin 500, ChatGPT Plus K12 Edu 2Y).
  - Các mặt hàng đang hết kho bên `@ProdSellerBot` (`Canva Pro`, `ElevenLabs Credit`, `ChatGPT Plus K12 Edu`) lập tức được mở bán trở lại nhờ nguồn dự phòng `@DanteHubBot`.
- **Quản trị `@DanteHubBot` trên `/admin`:**
  - Hiển thị trực tiếp số dư ví **`🏦 Vốn Nguồn 2 (@DanteHubBot)`** ngay dưới số dư `@ProdSellerBot`.
  - Bổ sung nút **`🔄 Đồng Bộ @DanteHubBot`** (`adm:dante_sync`), **`🔑 Key @DanteHubBot`** (`adm:set:dante_api_key`), và nút **`⚡ Gắn Nhanh Từ @DanteHubBot (1 Chạm)`** (`adm:bsrc_dante:<pid>`) trong từng sản phẩm để Admin chọn gắn bất kỳ sản phẩm nào từ kho 124 SP của `@DanteHubBot` mà không cần gõ tay.

---

## [v2.7.0] - 2026-10-19: Hệ Thống Đa Nguồn Hàng Dự Phòng Tự Động (Multi-Source Failover) & Bình Ổn Giá Thông Minh (Khóa Sàn Lãi `>= 150%`)

### 📦 1. Cơ chế Đa Nguồn Hàng Tự Động Bù Kho (`telebot.backup_sources`)
- **Cơ sở dữ liệu (`database.py` - Schema `telebot`):**
  - Bổ sung bảng `telebot.backup_sources` vào `_TABLE_NAME_RE` và `_init_db()` (tương thích song song Supabase PostgreSQL & SQLite Local, kèm **Write-Through RAM Cache** `_backup_sources_cache` TTL 60s).
  - Hỗ trợ 2 chế độ nguồn hàng dự phòng cho từng sản phẩm:
    - **`local_stock` (Kho Key dự phòng từ các Bot khác):** Admin dán danh sách Key/Tài khoản mua từ các Bot khác kèm mức giá vốn VNĐ (`cost_vnd`). Khi kho chính `@ProdSellerBot` hết hàng (`stock = 0`) hoặc không đủ số lượng khách đặt, Bot tự động rút Key nguyên tử (`pop_backup_keys_atomic`) từ nguồn dự phòng rẻ nhất để giao ngay cho khách trong 2 giây.
    - **`api` (Đấu nối API Reseller Bot/Web phụ):** Tự động đồng bộ tồn kho mỗi 5 phút và tự động gọi API đặt hàng (`create_external_api_order`) khi kho chính hết hàng.
  - Cộng gộp tồn kho (`get_effective_product_stock`): Hiển thị tổng tồn kho thực tế (`Kho chính K1 + Các kho dự phòng`) trên toàn bộ Menu Bot, Kênh `@KingToolShopOfficial` và cổng Public API `/v1/*`.

### 🛡️ 2. Thuật toán Bình Ổn Giá Thông Minh & Khóa Sàn Lợi Nhuận Tối Thiểu (`>= 150%`)
- **Giải quyết bài toán chênh lệch giá vốn giữa các Bot nguồn mà không làm nhảy giá đột ngột:**
  - Thiết lập mức tăng giá mục tiêu trên Kho chính (`markup_percent = 200.0%`) và **Sàn lợi nhuận tối thiểu bắt buộc (`min_profit_percent = 150.0%`)**.
  - **Công thức Bình ổn giá (`compute_stabilized_unit_price` & `resolve_supply_allocation`):**
    $$\text{Giá bán bình ổn} = \max\Big(\text{Giá chuẩn Kho chính (+200\%)},\; \text{Giá vốn nguồn đang chạy} \times \big(1 + \frac{\text{min\_profit\_percent}}{100}\big)\Big)$$
  - **Ví dụ thực tế:**
    - Kho chính `@ProdSellerBot` có giá vốn `30,000đ` $\rightarrow$ Giá bán chuẩn (`+200%`) = **`90,000đ`**.
    - Khi Kho chính hết hàng, chuyển sang **Nguồn dự phòng Bot B** có giá vốn `35,000đ`: Bán ở mức **`90,000đ`** vẫn thu lãi `+55,000đ` (**`+157% >= 150%`**) $\rightarrow$ Hệ thống **GIỮ NGUYÊN GIÁ BÁN `90,000đ`** (bình ổn giá 100%, khách hàng không thấy giá thay đổi).
    - Nếu chuyển sang **Nguồn dự phòng Bot C** có giá vốn cao `40,000đ`: Để đảm bảo sàn lãi không tụt xuống dưới `150%`, hệ thống tự động nhích nhẹ giá bán lên **`100,000đ`** (`40,000đ * 2.5`) thay vì nhảy vọt lên `120,000đ`, vừa giữ chân khách vừa khóa chặt **tỷ suất lợi nhuận `>= 150%`**.

### ⚙️ 3. Quản trị Đa Nguồn Hàng ngay trong `/admin` (`bot.py`)
- Thêm nút **`🛡️ Sàn Lãi Tối Thiểu (>=150%)`** ngay trên Bảng điều khiển `/admin` và thống kê tổng số nguồn dự phòng + tổng số Key dự phòng sẵn sàng.
- Trong mục **`🏷️ Quản lý SP & Nguồn Hàng Dự Phòng`** $\rightarrow$ bấm vào từng sản phẩm:
  - Hiển thị rõ: Tồn kho chính `K1`, Tồn kho dự phòng `+DP`, Giá vốn K1, Giá chuẩn `+200%`, Giá bán bình ổn hiện tại và danh sách từng nguồn dự phòng kèm mức giá bán & `%` lãi khi bù hàng.
  - Trang bị nút **`➕ Nạp Key Dự Phòng (Từ Bot khác)`**, **`🔌 Đấu API Nguồn Phụ`**, và các nút Bật/Tắt/Xóa từng nguồn 1 chạm.

---

## [v2.6.1] - 2026-10-18: Vá Lỗi Hiển Thị Biến Chuỗi Tin Nhắn Nạp Tiền Kèm Khuyến Mãi & Bảo Hành

### 🛠️ Sửa lỗi (Bug Fixes)
- **Tin nhắn duyệt nạp tiền có thưởng (`deposit_approved_bonus_msg` trong `i18n.py`):**
  - Khắc phục lỗi xung đột định dạng `{bonus_pct:g}` khi `bot.py` truyền chuỗi `bonus_pct=f"{bonus_pct:g}"` khiến `.format()` báo lỗi `ValueError` và trả về chuỗi thô `#{dep_id}`, `+{amt_vnd:,}đ`. Đổi sang `{bonus_pct}` đồng bộ cho cả Tiếng Việt và Tiếng Anh.
- **Hiển thị Banner Khuyến mãi nạp tiền (`deposit_choose_amount`) & Thông báo Bảo hành (`warr_prompt`, `warr_sent`):**
  - Bổ sung `{bonus_banner}` vào `deposit_choose_amount` trong `i18n.py` và truyền đầy đủ tham số `keys`, `issue` trong `bot.py` để đảm bảo 100% mẫu câu đa ngôn ngữ hiển thị chuẩn xác.

---

## [v2.6.0] - 2026-10-17: Hệ Thống Tự Động Đăng Bài Kênh Theo Lịch & Phễu Thu Hút - Chốt Khách Tự Động (4 Tầng)

### 🎯 4 Tính năng Tự động đăng bài & Phễu thu hút khách hàng (Marketing Funnel)
1. **⏰ Tự động đăng bài định kỳ theo khung giờ vàng & Tự dọn bài cũ (`auto_post_enabled`, `auto_post_hours = "9,14,20"`):**
   - Mỗi ngày vào các khung giờ vàng (`09:00`, `14:00`, `20:00` Giờ Việt Nam), Bot tự động cập nhật **Bảng giá & Tồn kho thực tế** lên `@KingToolShopOfficial` và ghim bài.
   - Tự động xóa bài Bảng giá cũ (`last_catalog_msg_id`) trước khi đăng bài mới để kênh luôn gọn đẹp, không bị rác tin nhắn.
   - Tự động chọn ngẫu nhiên sản phẩm đang sẵn hàng để đăng bài **🔥 Spotlight Sản Phẩm Hot Trong Ngày** (`post_spotlight_to_channel`) kèm mô tả Tiếng Việt, giá sau khi áp mã giảm giá Tân thủ và nút Deep-link **`🛒 Mua ngay`** (`?start=BUY_<pid>`).
   - Bổ sung nút **`🔥 Đăng Bài SP Hot Ngay`** (`adm:post_spotlight`) trong `/admin` để Admin có thể kích hoạt đăng ngay bất cứ lúc nào.
2. **🎁 Phễu "Tham gia Kênh nhận Quà Tân Thủ" (`newbie_gift_enabled`, `?start=GIFT`, `users.gift_claimed`):**
   - Khách mới vào Bot (hoặc bấm nút `🎁 Nhận Quà Tân Thủ` từ bài đăng trên kênh) sẽ thấy màn hình hướng dẫn tham gia kênh `@KingToolShopOfficial`.
   - Khi bấm **`✅ Bước 2: Đã tham gia — Nhận Quà Ngay!`**, Bot tự động kiểm tra trạng thái thành viên trên kênh (`get_permissions`), tặng ngay **`+5 Điểm thưởng`** và **tự động gắn sẵn mã giảm giá `TANTHU10` (`-10%`) vào giỏ hàng** (`USER_ACTIVE_VOUCHER`).
   - Khi khách bấm vào bất kỳ sản phẩm nào ngay sau đó, giá bán đã được gạch ngang giảm sẵn 10% (vẫn đi qua chốt chặn chống lỗ vốn `total_final_vnd >= total_cost_vnd`).
3. **🤖 Tạo hiệu ứng đám đông tự động (`auto_social_proof_enabled`):**
   - Bên cạnh thông báo đơn hàng thật (`post_order_social_proof`), trong khung giờ `08:00 – 22:00`, Bot định kỳ đăng thông báo hoàn tất đơn hàng (che ID dạng `6839***42`) kèm nút mua thẳng sản phẩm đó và tự động xóa thông báo mồi cũ trước đó để tạo uy tín cho khách mới vào kênh.
4. **💡 Nhắc nhở tự động khi khách bỏ dở đơn nạp tiền (`deposit_reminder_enabled`):**
   - Khi khách tạo mã QR VietQR mà sau `10–45 phút` đơn vẫn ở trạng thái `pending`, Bot tự động gửi tin nhắn hỗ trợ nhẹ nhàng kèm nút `✅ Tôi đã chuyển khoản`, nhắc ưu đãi nạp tiền (`+5% / +10%`) và link CSKH.

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
