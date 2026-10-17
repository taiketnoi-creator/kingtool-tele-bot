"""Bộ từ điển đa ngôn ngữ đồng bộ 100% giao diện & mô tả sản phẩm theo ngôn ngữ đã chọn (VNĐ)."""

from __future__ import annotations

LANGUAGES: list[tuple[str, str]] = [
    ("vi", "🇻🇳 Tiếng Việt"),
    ("en", "🇬🇧 English"),
]

STRINGS: dict[str, dict[str, str]] = {
    "vi": {
        "welcome_banner": "👋 Chào mừng bạn đến với Shop Bot Tự Động!\n\n📣 Kênh thông báo: @{channel}\n🆘 Hỗ trợ: @{admin}",
        "main_menu_title": "🏠 Menu Chính\n\n💵 Số dư: {balance:,}đ | ⭐ Điểm: {points}",
        "btn_products": "🛍️ Sản phẩm",
        "btn_balance": "💰 Số dư",
        "btn_deposit": "💳 Nạp tiền",
        "btn_methods": "📖 Hướng dẫn",
        "btn_profile": "👤 Hồ sơ",
        "btn_api": "API",
        "btn_language": "🌐 Ngôn ngữ",
        "btn_support": "🆘 Hỗ trợ",
        "btn_back": "« Quay lại",
        "products_title": "🛍️ Danh sách sản phẩm\nChọn một sản phẩm bên dưới:",
        "plans_label": "Gói",
        "in_stock_label": "📦 Tồn kho",
        "stock_keys_unit": "{n} sản phẩm",
        "stock_available": "Còn hàng",
        "stock_zero": "0 (Hết hàng)",
        "price_label": "💵 Giá bán",
        "tier_discount_note": "💎 Ưu đãi hạng **{tier}** (-{disc_pct}%): ~~{base_price:,}đ~~ ➡️ **{unit_price:,}đ**",
        "voucher_apply_btn": "🎟️ Nhập mã giảm giá (Voucher)",
        "voucher_applied_btn": "🎟️ Đang áp mã: {code} (-{disc:,}đ) [❌ Bỏ mã]",
        "voucher_applied_note": "🎟️ Đang áp mã: **{code}** (-{disc:,}đ)\n💳 **Thanh toán chỉ còn:** ~~{old_price:,}đ~~ ➡️ **{final_price:,}đ**",
        "voucher_prompt": "🎟️ Vui lòng nhập **Mã Giảm Giá (Voucher)** của bạn cho sản phẩm **{name}** (ví dụ: `SALE20`):",
        "voucher_err_not_found": "❌ Mã giảm giá `{code}` không tồn tại! Vui lòng kiểm tra lại (hoặc bấm Quay lại):",
        "voucher_err_inactive": "❌ Mã giảm giá `{code}` hiện đã tạm ngưng hoạt động!",
        "voucher_err_exhausted": "❌ Mã giảm giá `{code}` đã hết lượt sử dụng!",
        "voucher_err_already_used": "⚠️ Bạn đã sử dụng mã `{code}` trước đó rồi (Mỗi tài khoản chỉ được dùng 1 lần/mã)!",
        "voucher_removed_toast": "✅ Đã gỡ bỏ mã giảm giá!",
        "buy_btn": "💳 Mua ngay — {price:,}đ",
        "custom_qty_btn": "🔢 Nhập SL",
        "custom_qty_prompt": "🔢 Nhập **số lượng** bạn muốn mua cho sản phẩm **{name}** (Tồn kho tối đa: `{max_qty}`):",
        "custom_qty_invalid": "❌ Số lượng không hợp lệ! Vui lòng nhập số nguyên từ `1` đến `{max_qty}`:",
        "out_of_stock_btn": "❌ Tạm hết hàng",
        "balance_title": (
            "💰 **Số dư & Điểm thưởng của bạn**\n\n"
            "💵 Số dư hiện tại: **{balance:,}đ**\n"
            "⭐ Điểm tích lũy: **{points} điểm** *(1 điểm = {point_rate:,}đ)*\n"
            "💎 Hạng thành viên: **{tier}** *(Giảm {disc_pct}% mọi đơn hàng)*"
        ),
        "deposit_now_btn": "📥 Nạp tiền ngay",
        "redeem_points_btn": "🎁 Đổi {points} điểm (+{bonus:,}đ)",
        "redeem_points_min": "⚠️ Cần tối thiểu {min_pts} điểm để đổi sang số dư VNĐ (Hiện có: {points} điểm).",
        "redeem_points_success": "🎉 Đổi thành công **{pts} điểm** lấy **+{bonus:,}đ** vào ví!\n💰 Số dư mới: **{new_bal:,}đ**",
        "deposit_title": "💳 Phương thức nạp tiền\nChọn phương thức thanh toán:",
        "vietqr_method_btn": "🏦 Chuyển khoản Ngân hàng (VietQR Tự Động)",
        "deposit_choose_amount": "💵 Chọn mệnh giá muốn nạp (VNĐ):",
        "custom_amount_btn": "✍️ Nhập số tiền khác (VNĐ)",
        "custom_deposit_prompt": "💵 Vui lòng nhập **số tiền VNĐ** bạn muốn nạp (tối thiểu `10,000đ`, ví dụ: `50000` hoặc `50k`):",
        "custom_deposit_invalid": "❌ Vui lòng nhập số tiền hợp lệ từ `10,000đ` trở lên (ví dụ: `50000` hoặc `50k`):",
        "vietqr_paid_btn": "✅ Tôi đã chuyển khoản (Báo Admin duyệt)",
        "vietqr_notified_btn": "⏳ Đã báo Admin — Đang chờ duyệt...",
        "deposit_already_notified": "⏳ Yêu cầu duyệt đơn nạp này đã được gửi tới Admin! Vui lòng chờ trong giây lát.",
        "vietqr_caption": (
            "🏦 **THÔNG TIN CHUYỂN KHOẢN VIETQR**\n\n"
            "🧾 Mã đơn nạp: `#{dep_id}`\n"
            "🏛 Ngân hàng: **{bank_id}**\n"
            "💳 Số tài khoản: `{acc_no}`\n"
            "👤 Chủ tài khoản: **{acc_name}**\n"
            "💵 Số tiền nạp: **{amount_vnd:,}đ**\n"
            "📝 Nội dung CK (Bắt buộc): `{memo}`\n\n"
            "📌 *Quét mã QR để tự động điền chính xác số tiền và nội dung. Sau khi chuyển xong, bấm nút **✅ Tôi đã chuyển khoản** bên dưới!*"
        ),
        "deposit_approved_msg": (
            "✅ **Nạp tiền thành công!**\n\n"
            "🧾 Mã đơn nạp: `#{dep_id}`\n"
            "💵 Số tiền được cộng: **+{amt_vnd:,}đ**\n"
            "💰 Số dư hiện tại: **{new_bal:,}đ**\n\n"
            "Bấm /start để bắt đầu mua hàng ngay!"
        ),
        "deposit_rejected_msg": "❌ Yêu cầu nạp tiền `#{dep_id}` ({amt_vnd:,}đ) chưa nhận được thanh toán hoặc bị từ chối.",
        "profile_title": (
            "👤 **Hồ sơ của bạn**\n\n"
            "🆔 Telegram ID: `{uid}`\n"
            "👤 Username: @{username}\n"
            "💎 Hạng: **{tier}** *(Giảm {disc_pct}% | Silver ≥ 600k, Gold ≥ 2.5M)*\n"
            "💵 Số dư: **{balance:,}đ**\n"
            "⭐ Điểm thưởng: **{points} điểm**\n"
            "📦 Đơn hàng đã mua: **{orders}**\n"
            "💸 Tổng chi tiêu: **{spent:,}đ**\n"
            "🔑 Mã giới thiệu: `REF_{uid}`\n"
            "📅 Ngày tham gia: {joined}"
        ),
        "my_orders_btn": "📦 Đơn hàng đã mua",
        "referral_btn": "👥 Giới thiệu nhận hoa hồng",
        "orders_empty": "📦 Bạn chưa có đơn hàng nào.",
        "orders_history_title": "📦 **LỊCH SỬ ĐƠN HÀNG GẦN ĐÂY:**\n",
        "referral_info": (
            "👥 **CHƯƠNG TRÌNH GIỚI THIỆU BẠN BÈ**\n\n"
            "🔗 Link giới thiệu của bạn:\n`{ref_link}`\n\n"
            "🎁 **Quyền lợi:** Nhận ngay **+{comm_pct}% hoa hồng** cộng thẳng vào số dư ví mỗi khi bạn bè nạp tiền thành công!\n"
            "👤 Số người đã giới thiệu: **{ref_cnt}**"
        ),
        "api_info": (
            "🤖 **Cổng Kết Nối API Tự Động (API Access)**\n\n"
            "Sử dụng mã API Key của bạn để đấu nối lấy hàng & mua Key tự động 24/7 trên **Website, Bot Telegram hoặc Tool** riêng của bạn.\n"
            "*(💡 Nếu bạn chỉ mua lẻ để dùng cá nhân, hãy bấm **🛍️ Sản phẩm** ở Menu chính — không cần dùng mục này)*\n\n"
            "🔑 **Mã API Key của bạn:**\n"
            "`{api_key}`\n\n"
            "🌐 **Base URL:** `{base_url}/v1`\n"
            "📊 **Tổng lượt gọi API:** `{total_requests:,}`\n"
            "📅 **Ngày khởi tạo:** `{created_at}`"
        ),
        "api_btn_show": "👁 Hiện toàn bộ Key",
        "api_btn_hide": "🙈 Ẩn bớt Key",
        "api_btn_regen": "♻️ Tạo lại Key mới",
        "api_btn_guide": "💡 API này là gì? Hướng dẫn dễ hiểu",
        "api_btn_docs": "📖 Tài liệu kỹ thuật API (API Docs)",
        "api_regen_toast": "✅ Đã tạo mã API Key mới thành công! Mã cũ đã bị vô hiệu hóa.",
        "api_guide_text": (
            "💡 **GIẢI THÍCH DỄ HIỂU: TÍNH NĂNG API DÙNG ĐỂ LÀM GÌ?**\n\n"
            "❓ **1. Tôi là khách mua lẻ bình thường thì có cần dùng API không?**\n"
            "👉 **KHÔNG CẦN.** Nếu bạn chỉ mua tài khoản/phần mềm về sử dụng cá nhân, bạn chỉ cần bấm **💳 Nạp tiền** rồi vào mục **🛍️ Sản phẩm** bấm mua trực tiếp trên Bot như bình thường.\n\n"
            "🤖 **2. Vậy API Tự Động Mua Hàng dành cho ai?**\n"
            "Tính năng này dành riêng cho:\n"
            "• **Chủ Website / Chủ Shop / Đại lý bán lại (Reseller):** Muốn mở Web hoặc Bot Telegram riêng để bán lại toàn bộ kho hàng của Shop mà không cần bỏ vốn ôm hàng trước.\n"
            "• **Người mua sỉ số lượng lớn bằng Tool (MMO):** Muốn dùng phần mềm tự động gọi lệnh mua hàng loạt mà không cần bấm tay từng đơn.\n\n"
            "⚙️ **3. Cơ chế vận hành tự động 100% như thế nào?**\n"
            "• **Bước 1:** Bạn nạp tiền **VNĐ** vào ví trên Bot này (qua chuyển khoản **VietQR**).\n"
            "• **Bước 2:** Bạn bấm **👁 Hiện toàn bộ Key** để copy mã `ktk_...` và gắn vào Website / Bot riêng của bạn.\n"
            "• **Bước 3:** Mỗi khi khách hàng của bạn đặt mua trên Web/Bot của bạn -> Hệ thống của bạn tự động gửi lệnh qua API -> Bot tự động trừ tiền VNĐ trong ví của bạn (áp dụng sẵn **Chiết khấu Hạng VIP Silver/Gold**) và **trả Key sản phẩm ngay lập tức trong 1 giây** để bạn giao cho khách và hưởng phần tiền lãi chênh lệch!\n\n"
            "🔒 **Lưu ý bảo mật:** Mã `API Key` tương đương với quyền sử dụng số dư ví của bạn để mua hàng. Tuyệt đối **không gửi mã API Key cho người lạ**. Nếu nghi ngờ lộ mã, hãy bấm **♻️ Tạo lại Key mới** ngay lập tức."
        ),
        "methods_default": "📭 Hiện chưa có bài hướng dẫn mới.",
        "lang_prompt": "🌍 Vui lòng chọn ngôn ngữ của bạn:",
        "lang_updated": "✅ Đã chuyển sang Tiếng Việt 🇻🇳",
        "support_title": "🆘 Cần hỗ trợ?\n\n💬 Kênh CSKH: @{admin}\n📣 Kênh thông báo: @{channel}",
        "insufficient_balance": "❌ Số dư không đủ! Đơn hàng cần **{need:,}đ** nhưng ví của bạn hiện có **{have:,}đ**.\nVui lòng bấm 💳 Nạp tiền để nạp thêm.",
        "ask_activation_email": "📧 Sản phẩm **{name}** yêu cầu kích hoạt qua Email.\n\nVui lòng nhập địa chỉ Email của bạn để nhận kích hoạt (hoặc gõ `/cancel` để hủy):",
        "order_processing": "⏳ Đang xử lý đơn hàng và lấy tài khoản tự động, vui lòng chờ giây lát...",
        "order_busy": "⏳ Hệ thống đang xử lý giao dịch trước đó của bạn, vui lòng chờ giây lát...",
        "order_failed_refunded": (
            "❌ Không thể hoàn tất đơn hàng từ kho tổng (Số dư của bạn đã được hoàn lại đầy đủ **{refund:,}đ**).\n"
            "Chi tiết: `{err}`"
        ),
        "order_success": (
            "✅ **Mua hàng thành công!**\n\n"
            "🧾 Mã đơn: `#{order_id}`\n"
            "🛍️ Sản phẩm: **{name}** (x{qty})\n"
            "💵 Thanh toán: **{paid:,}đ**\n\n"
            "🔑 **Thông tin tài khoản / Key của bạn:**\n"
            "```\n{keys}\n```\n"
            "Cảm ơn bạn đã ủng hộ shop!"
        ),
        "order_activation_paid": (
            "✅ **Đặt hàng kích hoạt thành công!**\n\n"
            "🧾 Mã đơn: `#{order_id}`\n"
            "🛍️ Sản phẩm: **{name}**\n"
            "📧 Email kích hoạt: `{email}`\n"
            "⏳ Trạng thái: **Đang kích hoạt (ASAP)** — Hệ thống sẽ tự động nhắn tin cho bạn ngay khi kích hoạt hoàn tất!"
        ),
    },
    "en": {
        "welcome_banner": "👋 Welcome to our Automated Shop Bot!\n\n📣 Channel: @{channel}\n🆘 Support: @{admin}",
        "main_menu_title": "🏠 Main Menu\n\n💵 Balance: {balance:,}đ | ⭐ Points: {points}",
        "btn_products": "🛍️ Products",
        "btn_balance": "💰 My Balance",
        "btn_deposit": "💳 Deposit",
        "btn_methods": "📖 Methods",
        "btn_profile": "👤 Profile",
        "btn_api": "API",
        "btn_language": "🌐 Language",
        "btn_support": "🆘 Support",
        "btn_back": "« Back",
        "products_title": "🛍️ Available Products\nChoose a product:",
        "plans_label": "Plans",
        "in_stock_label": "📦 In stock",
        "stock_keys_unit": "{n} keys",
        "stock_available": "Available",
        "stock_zero": "0 keys",
        "price_label": "💵 Price",
        "tier_discount_note": "💎 **{tier}** Tier Discount (-{disc_pct}%): ~~{base_price:,}đ~~ ➡️ **{unit_price:,}đ**",
        "voucher_apply_btn": "🎟️ Apply Discount Code (Voucher)",
        "voucher_applied_btn": "🎟️ Applied: {code} (-{disc:,}đ) [❌ Remove]",
        "voucher_applied_note": "🎟️ Applied Voucher: **{code}** (-{disc:,}đ)\n💳 **Final Price:** ~~{old_price:,}đ~~ ➡️ **{final_price:,}đ**",
        "voucher_prompt": "🎟️ Please enter your **Voucher Code** for **{name}** (e.g. `SALE20`):",
        "voucher_err_not_found": "❌ Voucher code `{code}` does not exist! Please try again (or click Back):",
        "voucher_err_inactive": "❌ Voucher code `{code}` is currently inactive!",
        "voucher_err_exhausted": "❌ Voucher code `{code}` has reached its usage limit!",
        "voucher_err_already_used": "⚠️ You have already used voucher `{code}` (Limit: 1 use per user)!",
        "voucher_removed_toast": "✅ Voucher removed!",
        "buy_btn": "💳 Buy Now — {price:,}đ",
        "custom_qty_btn": "🔢 Custom Qty",
        "custom_qty_prompt": "🔢 Enter the **quantity** you want to buy for **{name}** (Max available: `{max_qty}`):",
        "custom_qty_invalid": "❌ Invalid quantity! Please enter an integer from `1` to `{max_qty}`:",
        "out_of_stock_btn": "❌ Out of Stock",
        "balance_title": (
            "💰 **Your Balance & Rewards**\n\n"
            "💵 Current Balance: **{balance:,}đ**\n"
            "⭐ Reward Points: **{points} pts** *(1 pt = {point_rate:,}đ)*\n"
            "💎 Membership Tier: **{tier}** *({disc_pct}% off all orders)*"
        ),
        "deposit_now_btn": "📥 Deposit Now",
        "redeem_points_btn": "🎁 Redeem {points} pts (+{bonus:,}đ)",
        "redeem_points_min": "⚠️ Minimum {min_pts} points required to redeem (Current: {points} pts).",
        "redeem_points_success": "🎉 Redeemed **{pts} points** for **+{bonus:,}đ**!\n💰 New Balance: **{new_bal:,}đ**",
        "deposit_title": "💳 Deposit Methods\nChoose a payment method:",
        "vietqr_method_btn": "🏦 Bank Transfer (Automated VietQR)",
        "deposit_choose_amount": "💵 Select deposit amount (VNĐ):",
        "custom_amount_btn": "✍️ Enter custom amount (VNĐ)",
        "custom_deposit_prompt": "💵 Please enter the **amount in VNĐ** you want to deposit (minimum `10,000đ`, e.g. `50000` or `50k`):",
        "custom_deposit_invalid": "❌ Please enter a valid amount from `10,000đ` or more (e.g. `50000` or `50k`):",
        "vietqr_paid_btn": "✅ I have transferred (Notify Admin)",
        "vietqr_notified_btn": "⏳ Admin Notified — Awaiting Approval...",
        "deposit_already_notified": "⏳ Approval request for this deposit has already been sent to Admin! Please wait a moment.",
        "vietqr_caption": (
            "🏦 **VIETQR BANK TRANSFER DETAILS**\n\n"
            "🧾 Deposit ID: `#{dep_id}`\n"
            "🏛 Bank: **{bank_id}**\n"
            "💳 Account No: `{acc_no}`\n"
            "👤 Account Holder: **{acc_name}**\n"
            "💵 Amount: **{amount_vnd:,}đ**\n"
            "📝 Transfer Content (Required): `{memo}`\n\n"
            "📌 *Scan the QR code to auto-fill the exact amount and transfer content. Once transferred, click **✅ I have transferred** below!*"
        ),
        "deposit_approved_msg": (
            "✅ **Deposit Approved!**\n\n"
            "🧾 Deposit ID: `#{dep_id}`\n"
            "💵 Added: **+{amt_vnd:,}đ**\n"
            "💰 Current Balance: **{new_bal:,}đ**\n\n"
            "Send /start to start shopping now!"
        ),
        "deposit_rejected_msg": "❌ Deposit request `#{dep_id}` ({amt_vnd:,}đ) was not received or was declined.",
        "profile_title": (
            "👤 **Your Profile**\n\n"
            "🆔 Telegram ID: `{uid}`\n"
            "👤 Username: @{username}\n"
            "💎 Tier: **{tier}** *({disc_pct}% off | Silver ≥ 600k, Gold ≥ 2.5M)*\n"
            "💵 Balance: **{balance:,}đ**\n"
            "⭐ Points: **{points} pts**\n"
            "📦 Orders: **{orders}**\n"
            "💸 Total Spent: **{spent:,}đ**\n"
            "🔑 Referral: `REF_{uid}`\n"
            "📅 Joined: {joined}"
        ),
        "my_orders_btn": "📦 My Orders",
        "referral_btn": "👥 Referral & Commission",
        "orders_empty": "📦 You have no orders yet.",
        "orders_history_title": "📦 **RECENT ORDER HISTORY:**\n",
        "referral_info": (
            "👥 **REFERRAL PROGRAM**\n\n"
            "🔗 Your referral link:\n`{ref_link}`\n\n"
            "🎁 **Reward:** Earn **+{comm_pct}% commission** added directly to your balance whenever your referred friends deposit!\n"
            "👤 Total referred users: **{ref_cnt}**"
        ),
        "api_info": (
            "🤖 **API Access**\n\n"
            "Use your API key to sell products on your own bot, website, or automated tool.\n"
            "*(💡 If you only buy products for personal use, simply use **🛍️ Products** on the Main Menu)*\n\n"
            "🔑 **Your API Key:**\n"
            "`{api_key}`\n\n"
            "🌐 **Base URL:** `{base_url}/v1`\n"
            "📊 **Total requests:** `{total_requests:,}`\n"
            "📅 **Created:** `{created_at}`"
        ),
        "api_btn_show": "👁 Show Full Key",
        "api_btn_hide": "🙈 Hide Key",
        "api_btn_regen": "♻️ Regenerate",
        "api_btn_guide": "💡 What is this API? Easy Guide",
        "api_btn_docs": "📖 API Documentation",
        "api_regen_toast": "✅ New API Key generated! Previous key has been revoked.",
        "api_guide_text": (
            "💡 **WHAT IS THE AUTOMATED RESELLER API?**\n\n"
            "❓ **1. Do regular customers need this API?**\n"
            "👉 **NO.** If you are buying accounts/keys for personal use, simply tap **💳 Deposit** and buy directly from **🛍️ Products**.\n\n"
            "🤖 **2. Who is this API for?**\n"
            "• **Shop Owners / Resellers:** Connect your own Website or Telegram Bot to resell our entire inventory automatically without pre-purchasing stock.\n"
            "• **Bulk Buyers / Automation Tools:** Purchase keys programmatically in bulk.\n\n"
            "⚙️ **3. How does it work?**\n"
            "• **Step 1:** Top up your **VNĐ** wallet balance on this Bot via **VietQR**.\n"
            "• **Step 2:** Tap **👁 Show Full Key** to copy your `ktk_...` key and add it to your website/bot.\n"
            "• **Step 3:** Whenever your customer buys on your website -> Your server calls our API -> Our system deducts the price from your wallet balance (including your **Silver/Gold VIP discount**) and returns the product key instantly!\n\n"
            "🔒 **Security Warning:** Your API Key can spend your wallet balance. **Never share your API Key with anyone.** If leaked, tap **♻️ Regenerate** immediately."
        ),
        "methods_default": "📭 No methods available at the moment.",
        "lang_prompt": "🌍 Please choose your language:",
        "lang_updated": "✅ Language set to English 🇬🇧",
        "support_title": "🆘 Need help?\n\n💬 Support: @{admin}\n📣 Channel: @{channel}",
        "insufficient_balance": "❌ Insufficient balance! Needed **{need:,}đ**, available **{have:,}đ**.\nPlease use 💳 Deposit to top up.",
        "ask_activation_email": "📧 **{name}** requires email activation.\n\nPlease reply with the email address to activate (or send `/cancel`):",
        "order_processing": "⏳ Processing your order and fetching key, please wait...",
        "order_busy": "⏳ Your previous transaction is still processing, please wait a moment...",
        "order_failed_refunded": (
            "❌ Could not complete the order from stock (Your balance of **{refund:,}đ** has been fully refunded).\n"
            "Details: `{err}`"
        ),
        "order_success": (
            "✅ **Order Completed!**\n\n"
            "🧾 Order ID: `#{order_id}`\n"
            "🛍️ Product: **{name}** (x{qty})\n"
            "💵 Total Paid: **{paid:,}đ**\n\n"
            "🔑 **Your Delivered Key(s):**\n"
            "```\n{keys}\n```"
        ),
        "order_activation_paid": (
            "✅ **Activation Order Placed!**\n\n"
            "🧾 Order ID: `#{order_id}`\n"
            "🛍️ Product: **{name}**\n"
            "📧 Email: `{email}`\n"
            "⏳ Status: **Paid (Activating ASAP)** — You will be notified automatically once completed!"
        ),
    },
}


# Bản dịch Tiếng Việt chuẩn cho toàn bộ sản phẩm trong kho
PRODUCT_DESC_VI: dict[str, str] = {
    "6acfc869a8f487d336b13845": (
        "📋 **ĐIỀU KHOẢN & LƯU Ý SỬ DỤNG:**\n\n"
        "✅ Toàn quyền sử dụng cá nhân (bạn có thể đổi mật khẩu hoặc giữ nguyên tùy ý).\n\n"
        "⌛️ Vui lòng **không đổi Tên / Ảnh đại diện** trong 1 tháng đầu tiên để tài khoản hoạt động bền và ổn định nhất.\n\n"
        "⚠️ **TUYỆT ĐỐI KHÔNG ĐỔI EMAIL!** Tự ý đổi Email sẽ mất bảo hành và bị văng khỏi nhóm Family.\n\n"
        "💡 **MẸO ĐĂNG NHẬP:**\n"
        "Trước khi đăng nhập, nên Xóa dữ liệu (Clear Data) ứng dụng Spotify trên Android hoặc Gỡ/Cài lại trên iOS để tránh lỗi báo sai mật khẩu."
    ),
    "6acf6cf6a8f487d336acb4ab": (
        "💎 **Mô tả sản phẩm:**\n"
        "🔥 **Vibi.Pro** — Công cụ tạo giọng nói AI trực tuyến, đối tác chính thức của **ElevenLabs & MiniMax**.\n\n"
        "💎 **CAM KẾT CHẤT LƯỢNG:**\n"
        "✅ **Model AI chính hãng** – Truy cập trực tiếp các model giọng nói của ElevenLabs & MiniMax.\n"
        "✅ **Hơn 10,000 giọng đọc đa ngôn ngữ** – Kho giọng tự nhiên, chất lượng cao cho làm video, sáng tạo nội dung.\n"
        "✅ **Credit không bị hết hạn cuối tháng** – Dùng bao nhiêu trừ bấy nhiêu, số credit còn dư được bảo lưu lâu dài.\n"
        "✅ **Bảo vệ Credit suốt quá trình sử dụng** – Bảo hành đầy đủ trong suốt thời gian dùng.\n\n"
        "🛡️ **CHÍNH SÁCH BẢO HÀNH:**\n"
        "• Hỗ trợ 1 đổi 1 nếu mã kích hoạt lỗi hoặc cộng thiếu Credit.\n"
        "• Hỗ trợ kỹ thuật xuyên suốt quá trình sử dụng.\n\n"
        "⚠️ **LƯU Ý QUAN TRỌNG:**\n"
        "• Mỗi mã kích hoạt chỉ sử dụng 1 lần duy nhất.\n"
        "• Vui lòng kiểm tra đúng tài khoản trước khi nạp mã.\n\n"
        "🌐 Sử dụng tại: https://vibi.pro"
    ),
    "6acf2df1a8f487d336a95463": (
        "📧 **Tài khoản Gmail cổ (ngâm từ 2020/2022) - Mix IP**\n"
        "• Độ trust cao, hạn chế xác minh.\n"
        "• Định dạng giao: `gmail | mật khẩu`"
    ),
    "6ace8ab5a8f487d336a833a0": (
        "📧 **Tài khoản Gmail USA (Dùng toàn cầu)**\n"
        "• Không cần bật VPN khi đăng nhập.\n"
        "• Định dạng giao: `gmail | mật khẩu`"
    ),
    "6a612473af18a2a83bc049a0": (
        "📧 **Tài khoản Gmail mới (Fresh Gmail)**\n"
        "• Định dạng giao: `gmail | mật khẩu`"
    ),
    "6ac88922cd35776c4d2cf283": (
        "📚 **Tài khoản Scribd Premium 1 Tháng (Bảo hành Full)**\n"
        "• Tài khoản riêng tư (Full Private Account).\n"
        "• Toàn quyền truy cập hộp thư Outlook đi kèm.\n"
        "• Đăng nhập trực tiếp bằng Email & Mật khẩu."
    ),
    "6ac65a53d07e0053469f477d": (
        "🎨 **Tài khoản Muse AI (Kèm 1 Tỷ Token)**\n"
        "• Tạo ảnh AI & Tạo video AI chất lượng cao (hỗ trợ cả video ngắn và video dài trên 1 giờ).\n"
        "• Lấy mã OTP đăng nhập tại: https://dev-api.cc/muse.php\n"
        "• Video hướng dẫn sử dụng: https://www.youtube.com/watch?v=lpsRG9VSDuQ\n"
        "----------\n"
        "📌 **Cách 2 (Đối với Temp Mail):**\n"
        "• Bước 1: Đăng nhập thông tin mail tại https://www.tmail.pk/login\n"
        "• Bước 2: Vào web hoặc app `muse.ai` và nhập email.\n"
        "• Bước 3: Lấy mã OTP trong hộp thư `tmail.pk` để hoàn tất đăng nhập ✅\n\n"
        "⚠️ Khuyến khích đổi sang email cá nhân của bạn sau khi đăng nhập.\n"
        "Định dạng giao: `Mail | Hộp thư`"
    ),
    "6ac505e1d07e0053469ab075": (
        "🔑 **API CLAUDE - 50M Token - 2 Ngày**\n\n"
        "🛡️ Cam kết 100% Claude API chính hãng (Hoàn tiền 100% nếu không chuẩn).\n"
        "⚡ Tương thích mượt mà với mọi công cụ & IDE: 9router, Claude Dev, Cursor, VS Code, v.v.\n"
        "⏳ Thời hạn sử dụng: **2 Ngày** (Chỉ bắt đầu tính giờ từ lúc bạn kích hoạt mã Redeem).\n\n"
        "📋 **Hướng dẫn cài đặt nhanh:**\n"
        "🔹 **Bước 1:** Truy cập 👉 https://miraiapi.com/usage/#redeem để nhập mã Redeem (nhận trong đơn hàng).\n"
        "🔹 **Bước 2:** Truy cập 👉 https://miraiapi.com/usage/#config để cấu hình API Key, chọn App và Model muốn dùng.\n"
        "✨ Hoàn tất & sẵn sàng code!\n\n"
        "📖 **Tài liệu hướng dẫn chi tiết:** 🔗 https://docs.google.com/document/d/16smXXteTwJYdrxTfdZlJvOkSEFkVL_6UBxoXcXZH6Gc/edit?tab=t.tbg84q5rs9yi\n\n"
        "⚠️ **Lưu ý quan trọng:** Thời hạn chỉ bắt đầu tính khi mã Redeem được kích hoạt. Bạn có thể lưu trữ hoặc bán lại mã thoải mái."
    ),
    "6ac0e0ab5f3b1a835b386fe8": (
        "🔑 **API CLAUDE - 10M Token - 1 Ngày**\n\n"
        "🛡️ Cam kết 100% Claude API chính hãng (Hoàn tiền 100% nếu không chuẩn).\n"
        "⚡ Tương thích mượt mà với mọi công cụ & IDE: 9router, Claude Dev, Cursor, VS Code, v.v.\n"
        "⏳ Thời hạn sử dụng: **1 Ngày** (Chỉ bắt đầu tính giờ từ lúc bạn kích hoạt mã Redeem).\n\n"
        "📋 **Hướng dẫn cài đặt nhanh:**\n"
        "🔹 **Bước 1:** Truy cập 👉 https://miraiapi.com/usage/#redeem để nhập mã Redeem (nhận trong đơn hàng).\n"
        "🔹 **Bước 2:** Truy cập 👉 https://miraiapi.com/usage/#config để cấu hình API Key, chọn App và Model muốn dùng.\n"
        "✨ Hoàn tất & sẵn sàng code!\n\n"
        "📖 **Tài liệu hướng dẫn chi tiết:** 🔗 https://docs.google.com/document/d/16smXXteTwJYdrxTfdZlJvOkSEFkVL_6UBxoXcXZH6Gc/edit?tab=t.tbg84q5rs9yi\n\n"
        "⚠️ **Lưu ý quan trọng:** Thời hạn chỉ bắt đầu tính khi mã Redeem được kích hoạt. Bạn có thể lưu trữ hoặc bán lại mã thoải mái."
    ),
    "6ac14f2c9acfaa92a2876173": (
        "🛍️ **THÔNG TIN SẢN PHẨM**\n"
        "━━━━━━━━━━━━━━━━\n"
        "🔑 **Gói 500$ API Claude - 30 Ngày**\n\n"
        "• Cam kết 100% Claude API chính hãng (Hoàn tiền 100% nếu fake).\n"
        "• Hoạt động tốt với mọi ứng dụng: VS Code, Codex, 9router, Claude Code, Cursor, v.v.\n"
        "• Bảo hành trọn vẹn (Full warranty).\n"
        "• Hướng dẫn chi tiết (có kèm video): https://docs.google.com/document/d/1bKvZSBqpS5eIq5EsQ45nagvH6KB1ywqjcIk7BcWkVF0/edit?tab=t.tbg84q5rs9yi"
    ),
    "6ac0c65e5f3b1a835b380122": (
        "🛍️ **THÔNG TIN SẢN PHẨM**\n"
        "━━━━━━━━━━━━━━━━\n"
        "🔑 **Gói 100$ API Claude - 30 Ngày**\n\n"
        "• Cam kết 100% Claude API chính hãng (Hoàn tiền 100% nếu fake).\n"
        "• Hoạt động tốt với mọi ứng dụng: VS Code, Codex, 9router, Claude Code, Cursor, v.v.\n"
        "• Bảo hành trọn vẹn (Full warranty).\n"
        "• Hướng dẫn chi tiết (có kèm video): https://docs.google.com/document/d/1bKvZSBqpS5eIq5EsQ45nagvH6KB1ywqjcIk7BcWkVF0/edit?tab=t.tbg84q5rs9yi"
    ),
    "6ac150a19acfaa92a28798b6": (
        "🗝️ **API ChatGPT CODEX - 100M Token - 3 Ngày**\n"
        "🛡️ Cam kết 100% Codex API chính hãng (Hoàn tiền 100% nếu không chuẩn).\n"
        "⚡ Tương thích mượt mà với mọi công cụ & IDE: 9router, Codex, Cursor, VS Code, v.v.\n"
        "⏳ Thời hạn sử dụng: **3 Ngày**\n\n"
        "📋 **Hướng dẫn cài đặt nhanh:**\n"
        "🔹 **Bước 1:** Truy cập 👉 https://miraiapi.com/usage/#redeem để nhập mã Redeem nhận được trong đơn hàng.\n"
        "🔹 **Bước 2:** Truy cập 👉 https://miraiapi.com/usage/#config để cấu hình API Key, chọn App và Model.\n"
        "✨ Hoàn tất & sẵn sàng code!\n"
        "🤖 **Các Model hỗ trợ:** `gpt-6-astra`, `gpt-6-sol`, `gpt-5.6-luna`, `gpt-5.6-terra`, `gpt-5.6-sol`\n"
        "📊 Kiểm tra dung lượng & hạn dùng tại: 🔗 https://miraiapi.com/usage/\n\n"
        "📖 **Tài liệu hướng dẫn chi tiết:** 🔗 https://docs.google.com/document/d/16cKyUu_8IjzJ88IaVLtW5OvkyJDtDnMVa_foKxG5eaE/edit?tab=t.gxgg5ayizr8d\n\n"
        "⚠️ **Lưu ý quan trọng:** Thời hạn chỉ bắt đầu tính khi mã Redeem được kích hoạt. Bạn có thể lưu trữ hoặc bán lại mã."
    ),
    "6ac0ebce5f3b1a835b39bab6": (
        "🗝️ **API ChatGPT CODEX - 50M Token - 2 Ngày**\n"
        "🛡️ Cam kết 100% Codex API chính hãng (Hoàn tiền 100% nếu không chuẩn).\n"
        "⚡ Tương thích mượt mà với mọi công cụ & IDE: 9router, Codex, Cursor, VS Code, v.v.\n"
        "⏳ Thời hạn sử dụng: **2 Ngày**\n\n"
        "📋 **Hướng dẫn cài đặt nhanh:**\n"
        "🔹 **Bước 1:** Truy cập 👉 https://miraiapi.com/usage/#redeem để nhập mã Redeem nhận được trong đơn hàng.\n"
        "🔹 **Bước 2:** Truy cập 👉 https://miraiapi.com/usage/#config để cấu hình API Key, chọn App và Model.\n"
        "✨ Hoàn tất & sẵn sàng code!\n"
        "🤖 **Các Model hỗ trợ:** `gpt-6-astra`, `gpt-6-sol`, `gpt-5.6-luna`, `gpt-5.6-terra`, `gpt-5.6-sol`\n"
        "📊 Kiểm tra dung lượng & hạn dùng tại: 🔗 https://miraiapi.com/usage/\n\n"
        "📖 **Tài liệu hướng dẫn chi tiết:** 🔗 https://docs.google.com/document/d/16cKyUu_8IjzJ88IaVLtW5OvkyJDtDnMVa_foKxG5eaE/edit?tab=t.gxgg5ayizr8d\n\n"
        "⚠️ **Lưu ý quan trọng:** Thời hạn chỉ bắt đầu tính khi mã Redeem được kích hoạt. Bạn có thể lưu trữ hoặc bán lại mã."
    ),
    "6ac0ea6d5f3b1a835b398396": (
        "🗝️ **API ChatGPT CODEX - 10M Token - 1 Ngày**\n"
        "🛡️ Cam kết 100% Codex API chính hãng (Hoàn tiền 100% nếu không chuẩn).\n"
        "⚡ Tương thích mượt mà với mọi công cụ & IDE: 9router, Codex, Cursor, VS Code, v.v.\n"
        "⏳ Thời hạn sử dụng: **1 Ngày**\n\n"
        "📋 **Hướng dẫn cài đặt nhanh:**\n"
        "🔹 **Bước 1:** Truy cập 👉 https://miraiapi.com/usage/#redeem để nhập mã Redeem nhận được trong đơn hàng.\n"
        "🔹 **Bước 2:** Truy cập 👉 https://miraiapi.com/usage/#config để cấu hình API Key, chọn App và Model.\n"
        "✨ Hoàn tất & sẵn sàng code!\n"
        "🤖 **Các Model hỗ trợ:** `gpt-6-astra`, `gpt-6-sol`, `gpt-5.6-luna`, `gpt-5.6-terra`, `gpt-5.6-sol`\n"
        "📊 Kiểm tra dung lượng & hạn dùng tại: 🔗 https://miraiapi.com/usage/\n\n"
        "📖 **Tài liệu hướng dẫn chi tiết:** 🔗 https://docs.google.com/document/d/16cKyUu_8IjzJ88IaVLtW5OvkyJDtDnMVa_foKxG5eaE/edit?tab=t.gxgg5ayizr8d\n\n"
        "⚠️ **Lưu ý quan trọng:** Thời hạn chỉ bắt đầu tính khi mã Redeem được kích hoạt. Bạn có thể lưu trữ hoặc bán lại mã."
    ),
    "6abeb3210dbb401865ffe95f": (
        "🔥 **Tính năng gói Wispr Flow 12 Tháng (Edu):** 🔥\n"
        "✅ **Không giới hạn số từ:** Đọc và chuyển giọng nói thành văn bản tự do trên mọi thiết bị.\n"
        "✅ **Hỗ trợ hơn 100 ngôn ngữ:** Nhận diện và viết tiếng Việt, tiếng Anh... cực kỳ chính xác.\n"
        "✅ **Chế độ ra lệnh (Command mode):** Chỉnh sửa và định dạng văn bản nhanh chóng.\n"
        "✅ **Hỗ trợ làm việc nhóm & ưu tiên cập nhật tính năng mới nhất.**\n"
        "💡 Gói bản quyền chính hãng, bảo hành đủ 12 tháng!"
    ),
    "6abeace70dbb401865ffb2d2": (
        "📺 **LINK KÍCH HOẠT APPLE TV+ 12 THÁNG**\n\n"
        "🎁 Bảo hành kích hoạt: **48 Giờ**\n"
        "🍏 Dễ dùng như link Gemini/Duolingo — **Không cần thẻ Visa/Mastercard** ✅\n\n"
        "📱 **HƯỚNG DẪN KÍCH HOẠT:**\n"
        "• Bật VPN Mỹ (USA), truy cập website Apple TV và tạo tài khoản mới (IP Mỹ).\n"
        "• Dán link nhận được vào trình duyệt để kích hoạt gói 12 tháng.\n"
        "• Sau khi kích hoạt xong có thể tắt VPN dùng bình thường."
    ),
    "6aa5bafb77c587d75cbe2a8e": (
        "🦉 **Duolingo Super 12 Tháng (Nâng cấp chính chủ)**\n\n"
        "💡 **Hướng dẫn nhanh:**\n"
        "⚡ Đăng nhập sẵn tài khoản Duolingo của bạn trên trình duyệt web -> Mở link nhận được ở tab mới và bấm **Claim Offer** — gói Super 12 tháng sẽ tự động kích hoạt.\n\n"
        "📋 **Thông tin gói:**\n"
        "• Gói: **Duolingo Super (12 Tháng)** trên chính tài khoản của bạn.\n"
        "• Không cần thêm thẻ thanh toán.\n\n"
        "⚠️ **Lưu ý:** Nếu báo lỗi giới hạn quốc gia, hãy bật VPN sang **Ấn Độ (India 🇮🇳)** rồi bấm vào link lại:\n"
        "🔗 VPN Chrome miễn phí: https://chromewebstore.google.com/detail/nodus-vpn/hgjgkgnmflipmgmknglemhgkpfdfepbh"
    ),
    "6aa4551bc76bc3aeb2ebe88e": (
        "🎬 **Tài khoản CapCut Pro 1 Tháng + 1,600 Credits AI**\n"
        "• Bảo hành trọn vẹn (Full Warranty) suốt thời gian sử dụng."
    ),
    "6a93e9fdd46143eb34b0d774": (
        "🎬 **Tài khoản HBO MAX 3 Tháng**\n"
        "• Không cần VPN.\n"
        "• Đăng nhập trực tiếp bằng Email & Mật khẩu.\n"
        "• Tài khoản riêng tư (Full Private Account).\n"
        "• Bảo hành: 1 tháng."
    ),
    "6a920a4463bcf8795d045d0a": (
        "⚡️ **Hướng dẫn đăng nhập Tài khoản Telegram:**\n\n"
        "1. Mở ứng dụng Telegram → Nhập Số điện thoại được cấp → Bấm nhận mã OTP.\n"
        "2. Truy cập trang lấy mã OTP: https://analyzed-falling-copied-transparent.trycloudflare.com\n"
        "3. Nhập Số điện thoại vào web → Bấm **Start Fetching OTP**.\n"
        "4. Copy mã OTP hiện ra (sau khoảng 10–15 giây) và hoàn tất đăng nhập.\n\n"
        "🔒 **CHÍNH SÁCH BẢO HÀNH OTP:**\n"
        "• Bảo hành nhận mã OTP đăng nhập lần đầu tiên.\n"
        "• Sau khi vào tài khoản, vui lòng **cài đặt ngay mật khẩu 2FA và liên kết Gmail khôi phục** của bạn để bảo mật tài khoản."
    ),
    "6a8c8ef9f870e3b343103eb0": (
        "📐 **Gói Autodesk All Apps 1 Năm (Chính chủ qua Email)**\n"
        "• Nâng cấp/Mời trực tiếp vào Email khách hàng.\n"
        "• Bao gồm hầu hết toàn bộ ứng dụng Autodesk (3ds Max, AutoCAD, Fusion 360, Maya, Revit...).\n"
        "• Bảo hành trọn vẹn 1 năm (Full warranty)."
    ),
    "6a8ad927f870e3b3430c7b18": (
        "🤖 **Gói Claude AI Pro / Max (Chính hãng)**\n"
        "• Tài khoản riêng tư chất lượng cao, hỗ trợ đầy đủ các model Claude mới nhất.\n"
        "• Bảo hành đầy đủ theo thời hạn gói."
    ),
    "6a88be06fb032a73212a202b": (
        "🎬 **Tài khoản CapCut Pro (Bảo hành Full)**\n"
        "• Mở khóa toàn bộ tính năng Pro, hiệu ứng, xuất video chất lượng cao.\n"
        "• Bảo hành trọn vẹn theo thời hạn gói."
    ),
    "6a8834a1fb032a732128e7bc": (
        "🤖 **Tài khoản Claude AI (Bảo hành Full)**\n"
        "• Truy cập đầy đủ các tính năng cao cấp của Claude AI.\n"
        "• Giao tài khoản ngay lập tức sau khi thanh toán."
    ),
    "6a820a0b969a9635841ddb30": (
        "🎓 **Tài khoản edX Premium 12 Tháng**\n\n"
        "✨ **Quyền lợi bao gồm:**\n"
        "✔️ 12 tháng truy cập edX Premium (Nền tảng học tập tương tự Coursera).\n"
        "📩 Tài khoản tạo sẵn, giao trực tiếp Email & Mật khẩu.\n"
        "🌐 Học các khóa từ Harvard, MIT & các trường Đại học hàng đầu thế giới.\n"
        "🏅 Hỗ trợ cấp Chứng chỉ xác thực (Verified Certificates).\n"
        "🛡 Bảo hành trọn vẹn 12 tháng.\n\n"
        "📌 **Lưu ý quan trọng:**\n"
        "• Định dạng giao: `email outlook | mật khẩu outlook | mật khẩu edx`\n"
        "• Bạn có thể đổi mật khẩu sau khi đăng nhập lần đầu, nhưng **tuyệt đối không đổi địa chỉ email** để giữ bảo hành."
    ),
    "6a7826d9cf6984bb8ba101e8": (
        "🎨 **Tài khoản Figma Pro Education 2 Năm**\n"
        "• Tài khoản cực kỳ ổn định, kèm sẵn **3,000 credits mỗi tháng** và tính năng Make (Opus 4.7).\n"
        "• Định dạng giao: `email | password | email token`\n"
        "• Link lấy mã OTP từ hộp thư: https://hitools.pro/read-hotmail (Mật khẩu Figma và Hotmail giống nhau).\n"
        "⚠️ **Lưu ý:** Tuyệt đối không thay đổi địa chỉ email của tài khoản Figma."
    ),
    "6a75800fcf6984bb8b9bdc66": (
        "📋 **Miro Lifetime Panel (Quyền Admin - Mời tối đa 100 thành viên)**\n"
        "• **Quyền Admin tuyệt đối:** Bạn là Chủ sở hữu (Owner/Admin) của Team, toàn quyền quản lý thành viên và không gian dự án.\n"
        "• **Quy mô 100 thành viên:** Dễ dàng mời tới 100 người vào nhóm làm việc, học tập hoặc startup."
    ),
    "6a495a5f02999800df961920": (
        "🧠 **Tài khoản ChatGPT Plus K12 Edu (Thời hạn 2 Năm)**\n\n"
        "✨ **Tính năng nổi bật:**\n"
        "• Nhắn tin không giới hạn với các model mới nhất, tìm kiếm Web & Deep Research.\n"
        "• Tải file, phân tích dữ liệu, tạo ảnh, chế độ giọng nói (Voice Mode) & Codex.\n"
        "• Hỗ trợ Custom GPTs & không gian làm việc riêng tư.\n\n"
        "🚀 **Định dạng bàn giao:**\n"
        "`Email | Mật khẩu | Mã 2FA | Link Hộp thư | Hướng dẫn kích hoạt K12 Workspace`\n"
        "• Lấy mã 2FA tại: https://2fa.live/\n\n"
        "⚠️ **Lưu ý quan trọng:**\n"
        "• Vui lòng đăng nhập trên **trình duyệt web** trước khi đăng nhập trên ứng dụng điện thoại.\n"
        "• Thời hạn gói: **2 năm** | Bảo hành đăng nhập: **24 giờ**.\n"
        "• Khi cần lấy mã OTP từ email, hãy truy cập Link Hộp thư kèm theo trong đơn hàng và đăng nhập bằng chính Email + Mật khẩu của tài khoản."
    ),
    "6a2ff705dbe65bbecc0d3d9d": (
        "📨 **Tài khoản Email Outlook / Hotmail (Full quyền + OTP)**\n"
        "• Định dạng giao: `email | password | token`\n"
        "• Link đọc hộp thư lấy mã OTP: https://dongvanfb.net/read_mail_box/"
    ),
    "6a54b931351561c645a43e8c": (
        "📝 **Tài khoản Notion Education Plus 12 Tháng**\n"
        "✅ Giao đầy đủ tài khoản `Email : Mật khẩu`\n"
        "✅ Cho phép đổi Email & cài lại bảo mật sau khi đăng nhập.\n"
        "✅ Thời hạn sử dụng: **12 Tháng**.\n"
        "📌 **Hướng dẫn:** Đăng nhập vào `outlook.com` trước, sau đó dùng cùng email và mật khẩu đó để đăng nhập vào Notion.\n"
        "Định dạng giao: `Mail / Mật khẩu Hotmail / Mật khẩu Notion`"
    ),
    "6a3d636221735658e32bd2a6": (
        "🎬 **Tài khoản Amazon Prime Video 6 Tháng (180 Ngày)**\n\n"
        "• Tài khoản riêng tư (Full Private Account), kèm quyền truy cập Email.\n"
        "• Nhận tài khoản và xem phim ngay trên mọi thiết bị.\n\n"
        "⚠️ **Quy tắc bảo hành:**\n"
        "• Không đổi mật khẩu trong vòng 24 giờ đầu tiên.\n"
        "• Tuyệt đối không bấm thuê/mua phim trả phí phát sinh trên Amazon.\n"
        "• Không đăng nhập/đăng xuất liên tục bất thường."
    ),
    "6a316a7b1777fc2347835653": (
        "🖌️ **Nâng cấp Canva Pro 2 Năm (Chính chủ qua Email - Bảo hành Full)**\n"
        "• Kích hoạt trực tiếp trên Email cá nhân của bạn (Tài khoản riêng tư 100%).\n"
        "• Mở khóa toàn bộ tính năng Canva Pro Edu & công cụ AI.\n"
        "• Bảo hành trọn vẹn 2 năm."
    ),
    "6a31035939dc014325da2c66": (
        "✨ **Link kích hoạt Gemini Pro 18 Tháng + 5TB Google Cloud**\n\n"
        "• **Thời hạn:** 18 Tháng 🤖\n"
        "• **Dung lượng đi kèm:** 5TB lưu trữ đám mây 🛴\n"
        "• **Tài khoản Family chính chủ:** Có thể mời thêm tối đa 5 người dùng ⚡️\n"
        "• **100% Riêng tư** — Không cần thẻ thanh toán Visa/Mastercard 💳\n"
        "• **Bảo hành link:** 24 giờ ✔️\n\n"
        "📌 **Cách dùng:** Dán link nhận được vào trình duyệt và bấm **“Activate Offer”** để nâng cấp ngay!"
    ),
    "6a2fdb4f035a6d898f2106ff": (
        "🖌️ **Tài khoản Canva Pro Admin (Mời được 500 thành viên)**\n"
        "• Giao toàn quyền truy cập Email gốc (bạn có thể đổi mật khẩu để bảo mật).\n"
        "• Tài khoản đã xác minh hồ sơ giáo dục và kích hoạt đầy đủ.\n"
        "⚠️ **Lưu ý:** Không đổi email hoặc tên lớp học. Thực hiện đúng hướng dẫn sau để sử dụng bền vững:\n"
        "https://telegra.ph/Canva-Pro-Admin-500-Steps-to-Follow-08-18"
    ),
    "6a2fe23a1c8697b163aedcbd": (
        "💼 **Tài khoản Microsoft Office 365 Plus (1 Năm)**\n\n"
        "✨ **Bao gồm đầy đủ bộ ứng dụng:**\n"
        "• Microsoft Word, Excel, PowerPoint, OneNote, Forms\n"
        "• Kèm **1TB OneDrive** lưu trữ đám mây\n\n"
        "📋 **Chi tiết gói:**\n"
        "• Thời hạn: 12 Tháng (1 tháng cam kết + 11 tháng gia hạn quà tặng)\n"
        "• Hỗ trợ tối đa 5 thiết bị Windows/Mac\n"
        "• Giao tự động ngay sau khi mua theo định dạng: `Email : Mật khẩu`"
    ),
    "6a2fda51035a6d898f2106fe": (
        "🎬 **Tài khoản CapCut Pro 1 Tháng (Bảo hành Full 30 Ngày)**\n"
        "• Định dạng giao: `hotmail | mật khẩu capcut | mật khẩu hotmail`\n"
        "• Tài khoản Pro Team riêng tư dùng xuyên suốt 30 ngày (không phải loại 7 ngày gia hạn lại).\n"
        "• Hỗ trợ tối đa 2 thiết bị, bảo hành đủ 30 ngày.\n"
        "📌 **Cách đăng nhập:** Đăng nhập trên App điện thoại trước, sau đó quét mã QR để đăng nhập lên App máy tính (không đăng nhập trên trình duyệt web)."
    ),
    "6a5b873847b606c66fc160b2": (
        "🎨 **Link nâng cấp Adobe Express Premium 12 Tháng**\n"
        "• Bạn sẽ nhận được 1 đường link Redeem: chỉ cần mở link và đăng nhập email của bạn để nâng cấp ngay lên **Adobe Express Premium 12 tháng**.\n"
        "• Không cần thẻ VISA hay phương thức thanh toán.\n"
        "⚠️ **Lưu ý:** Nếu gặp thông báo giới hạn quốc gia khi bấm link, hãy bật VPN sang **Ấn Độ (India)** rồi thử lại."
    ),
    "6a6207cf92969197bb382958": (
        "📄 **Tài khoản iLovePDF Premium 1 Năm**\n"
        "🔻 Mở khóa toàn bộ công cụ xử lý PDF không giới hạn của iLovePDF.\n"
        "🔻 Sử dụng trên cả Web, Điện thoại và Máy tính.\n"
        "🔻 Hỗ trợ chữ ký số (Digital Signatures), không quảng cáo & tặng kèm 2,000 AI Credits.\n"
        "⚡ **Hướng dẫn:** Đăng nhập vào website iLovePDF bằng `email:password` được cấp và đổi mật khẩu của bạn."
    ),
}


FALLBACK_PHRASE_MAP_VI: list[tuple[str, str]] = [
    ("PRODUCT INFORMATION", "THÔNG TIN SẢN PHẨM"),
    ("100% Genuine Claude API (100% refund guaranteed if not authentic).", "Cam kết 100% Claude API chính hãng (Hoàn tiền 100% nếu không chuẩn)."),
    ("100% Genuine Codex API (100% refund guaranteed if not authentic).", "Cam kết 100% Codex API chính hãng (Hoàn tiền 100% nếu không chuẩn)."),
    ("100% genuine Claude API (100% refund if fake).", "Cam kết 100% Claude API chính hãng (Hoàn tiền 100% nếu fake)."),
    ("Seamlessly compatible with all tools & IDEs:", "Tương thích mượt mà với mọi công cụ & IDE:"),
    ("Works with all apps:", "Hoạt động tốt với mọi ứng dụng:"),
    ("Validity:", "Thời hạn sử dụng:"),
    ("Quick Setup Instructions:", "Hướng dẫn cài đặt nhanh:"),
    ("Step 1: Visit", "Bước 1: Truy cập"),
    ("to redeem your code (Enter the code provided in your order details).", "để kích hoạt mã Redeem (Nhập mã được cấp trong chi tiết đơn hàng)."),
    ("Step 2: Visit", "Bước 2: Truy cập"),
    ("to configure your API Key, select your target App, and choose the ideal Model.", "để cấu hình API Key, chọn ứng dụng và Model muốn sử dụng."),
    ("All done & Ready to code!", "Hoàn tất & sẵn sàng sử dụng!"),
    ("Available Models:", "Các Model hỗ trợ:"),
    ("Check quota balance & expiry date at:", "Kiểm tra số dư Token & hạn dùng tại:"),
    ("Detailed Documentation & Guide:", "Tài liệu hướng dẫn chi tiết:"),
    ("Detailed guide:", "Hướng dẫn chi tiết:"),
    ("Important Notice: The validity period only starts counting once the redeem code is activated. You can store or resell the code .", "Lưu ý quan trọng: Thời hạn chỉ bắt đầu tính từ lúc kích hoạt mã Redeem. Bạn có thể lưu trữ hoặc bán lại mã thoải mái."),
    ("Full warranty", "Bảo hành trọn vẹn"),
    ("Full Warranty", "Bảo hành trọn vẹn"),
    ("FULL PRIVATE ACCOUNT", "TÀI KHOẢN RIÊNG TƯ (PRIVATE)"),
    ("NO VPN REQUIRED", "Không cần VPN"),
]


def localize_product_description(product_id: str, raw_desc: str, lang: str) -> str:
    """Trả về mô tả sản phẩm đồng bộ theo ngôn ngữ người dùng đã chọn (vi / en)."""
    desc = (raw_desc or "").strip()
    if lang != "vi":
        return desc
    if product_id in PRODUCT_DESC_VI:
        return PRODUCT_DESC_VI[product_id]
    translated = desc
    for en_txt, vi_txt in FALLBACK_PHRASE_MAP_VI:
        translated = translated.replace(en_txt, vi_txt)
    return translated


def t(lang: str, key: str, **kwargs: object) -> str:
    bundle = STRINGS.get(lang, STRINGS["en"])
    template = bundle.get(key) or STRINGS["en"].get(key, key)
    if kwargs:
        try:
            return template.format(**kwargs)
        except Exception:
            return template
    return template
