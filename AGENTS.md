# 🤖 HƯỚNG DẪN DÀNH CHO AI AGENT (AGENTS.MD)

Khi bạn (AI Coding Assistant / Agent) làm việc trong thư mục dự án này, hãy tuân thủ quy trình sau:

1. **Đọc tài liệu ngữ cảnh trước tiên:**
   - Đọc [PROJECT_OVERVIEW.md](./PROJECT_OVERVIEW.md) để nắm rõ kiến trúc Cloud (**GitHub + Supabase Schema `telebot` + Render + Vercel**), cấu trúc bảng dữ liệu và quy tắc nghiệp vụ.
   - Đọc [PROJECT_CHANGELOG.md](./PROJECT_CHANGELOG.md) để nắm được lịch sử các bản cập nhật gần nhất.

2. **Quy tắc kỹ thuật bắt buộc:**
   - **Database (`database.py`):** Mọi bảng trên Supabase PostgreSQL đều nằm trong Schema **`telebot`** (`telebot.settings`, `telebot.users`, `telebot.product_overrides`, `telebot.deposits`, `telebot.orders`). Nếu thêm bảng mới, bắt buộc cập nhật regex `_TABLE_NAME_RE` trong `database.py` để không tạo bảng tràn ra Schema `public` (vì Schema `public` đang thuộc về dự án `Base Family`).
   - **Hiệu năng:** Luôn duy trì cơ chế **Write-Through RAM Cache** trong `database.py` và **Stale-While-Revalidate** trong `prodseller_client.py`. Không gọi truy vấn SQL mạng lặp lại bên trong vòng lặp sản phẩm.
   - **Bảo vệ lợi nhuận:** Mọi tính năng giảm giá (Hạng VIP, Voucher...) phải luôn đảm bảo giá thu cuối cùng `>= cost_vnd` (giá vốn đại lý từ ProdSeller).
   - **Triển khai Cloud:** Bot đang chạy trực tiếp 24/7 trên **Render** (`https://kingtool-tele-bot.onrender.com`), tự động lấy code từ nhánh `main` trên GitHub (`https://github.com/taiketnoi-creator/kingtool-tele-bot`). Không tự ý bật tiến trình `bot.py` chạy ngầm ở máy Local khi Render đang chạy để tránh xung đột session/tin nhắn.

3. **Sau khi hoàn thành chỉnh sửa:**
   - Cập nhật mục tương ứng vào [PROJECT_CHANGELOG.md](./PROJECT_CHANGELOG.md).
   - Commit và `git push origin main` để đồng bộ lên GitHub & Render.
