# Telethon Safe Menu Analyzer

Công cụ Python để khám phá menu của `@prodsellerbot` bằng **tài khoản Telegram của chính bạn**. Công cụ gửi `/start`, ghi lại tin nhắn/nút inline và chỉ bấm một số mục menu an toàn trong allowlist.

## Giới hạn an toàn

- Không mua hàng, không thanh toán, không nạp/rút tiền.
- Không bấm các nút có từ khóa nhạy cảm như `buy`, `order`, `payment`, `wallet`, `OTP`, `password`…
- Không tự nhập số điện thoại, mã OTP, mật khẩu, thông tin thẻ hoặc dữ liệu khách hàng.
- Chạy tối đa `MAX_DEPTH` tầng menu; mặc định là 2.
- Kết quả được lưu thành JSON trong thư mục `output`.

Đây là công cụ quan sát giao diện/menu, không phải công cụ clone bot, vượt quyền, hay tự động giao dịch.

## Cài trên Windows

1. Cài Python 3.10 trở lên từ <https://www.python.org/downloads/windows/>. Khi cài, chọn **Add Python to PATH**.
2. Giải nén ZIP vào thư mục riêng, mở PowerShell tại thư mục đó.
3. Tạo môi trường ảo và cài thư viện:

   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```

4. Sao chép `.env.example` thành `.env`, rồi điền `TELEGRAM_API_ID`, `TELEGRAM_API_HASH` và `BOT_USERNAME`.
5. Chạy:

   ```powershell
   python analyzer.py
   ```

Lần chạy đầu, Telethon sẽ yêu cầu số điện thoại, mã đăng nhập Telegram và có thể hỏi mật khẩu 2FA trong cửa sổ PowerShell. Không gửi các giá trị này cho ai.

## Kết quả

Sau khi chạy, mở file `output\analysis-YYYYMMDD-HHMMSS.json`. File chứa tin nhắn đã nhận, các nút được phát hiện, nút nào được xem là an toàn và nút nào đã được bấm.

## Bảo mật bắt buộc

- Không chia sẻ `.env`, file `*.session`, mã OTP, mật khẩu 2FA, API hash hoặc JSON có dữ liệu riêng tư.
- File `*.session` có thể cho phép truy cập tài khoản Telegram; giữ như mật khẩu và xóa khỏi máy dùng chung.
- Chỉ dùng API ID/API hash của tài khoản bạn sở hữu và chỉ phân tích bot mà bạn được phép kiểm thử.
- Nếu bot hiển thị yêu cầu thanh toán hoặc thông tin nhạy cảm, dừng chương trình bằng `Ctrl+C`.
- Sau khi hoàn tất, xóa file session nếu không cần chạy lại: `safe-analyzer.session`.

## Tùy chỉnh thận trọng

`MAX_DEPTH` chỉ nên tăng khi bạn hiểu rõ menu. Allowlist nằm ở đầu `analyzer.py` trong `SAFE_LABELS`; không nên thêm các nhãn liên quan đến giao dịch, tài khoản hoặc dữ liệu cá nhân.
