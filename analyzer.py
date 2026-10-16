"""Khám phá menu an toàn của một Telegram bot bằng tài khoản người dùng.

Chương trình này chỉ dùng cho tài khoản Telegram của chính bạn. Nó gửi /start,
ghi log nội dung và các nút inline, sau đó chỉ bấm các nút có nhãn an toàn.
Các nút liên quan đến đặt hàng, thanh toán, nạp tiền, rút tiền hoặc cung cấp
thông tin nhạy cảm luôn bị bỏ qua.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from telethon import TelegramClient
from telethon.errors import FloodWaitError, RPCError
from telethon.tl.custom import Message


ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = ROOT / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

SAFE_LABELS = {
    "menu", "trợ giúp", "tro giup", "help", "hướng dẫn", "huong dan",
    "faq", "giới thiệu", "gioi thieu", "about", "dịch vụ", "dich vu",
    "service", "sản phẩm", "san pham", "products", "danh mục", "danh muc",
    "category", "liên hệ", "lien he", "contact", "quay lại", "quay lai",
    "back", "trang chủ", "trang chu", "home", "next", "tiếp", "tiep",
}

BLOCKED_TERMS = (
    "mua", "buy", "order", "đặt hàng", "dat hang", "thanh toán", "thanh toan",
    "payment", "pay", "nạp", "nap", "deposit", "rút", "rut", "withdraw",
    "số dư", "so du", "balance", "chuyển khoản", "chuyen khoan", "bank",
    "crypto", "usdt", "wallet", "ví", "vi", "mã otp", "ma otp", "otp",
    "mật khẩu", "mat khau", "password", "2fa", "api key", "secret",
)


def normalize(text: str) -> str:
    cleaned = re.sub(r"[^\w\s]", " ", text.casefold())
    return re.sub(r"\s+", " ", cleaned).strip()


def is_blocked(label: str) -> bool:
    value = normalize(label)
    return any(term in value for term in BLOCKED_TERMS)


def is_safe(label: str) -> bool:
    value = normalize(label)
    if not value or is_blocked(value):
        return False
    return value in SAFE_LABELS


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class ButtonRecord:
    row: int
    column: int
    text: str
    safe: bool
    blocked: bool
    clicked: bool = False
    error: str | None = None


@dataclass
class MessageRecord:
    received_at: str
    message_id: int
    sender: str
    text: str
    buttons: list[ButtonRecord]


class Analyzer:
    def __init__(self, client: TelegramClient, bot_username: str, max_depth: int, delay: float):
        self.client = client
        self.bot_username = bot_username
        self.max_depth = max_depth
        self.delay = delay
        self.visited_labels: set[str] = set()
        self.records: list[MessageRecord] = []

    async def inspect_message(self, message: Message, depth: int) -> None:
        text = (message.raw_text or "").strip()
        buttons: list[ButtonRecord] = []
        button_map: dict[tuple[int, int], ButtonRecord] = {}
        if message.buttons:
            for row_index, row in enumerate(message.buttons):
                for column_index, button in enumerate(row):
                    label = str(getattr(button, "text", "") or "").strip()
                    record = ButtonRecord(
                        row=row_index,
                        column=column_index,
                        text=label,
                        safe=is_safe(label),
                        blocked=is_blocked(label),
                    )
                    buttons.append(record)
                    button_map[(row_index, column_index)] = record

        sender = self.bot_username
        self.records.append(MessageRecord(
            received_at=now_iso(), message_id=message.id, sender=sender,
            text=text, buttons=buttons,
        ))
        logging.info("Nhận tin #%s: %s", message.id, text[:160] or "(không có văn bản)")
        for item in buttons:
            marker = "SAFE" if item.safe else "SKIP"
            logging.info("  [%s] %s", marker, item.text or "(nút không tên)")

        if depth >= self.max_depth or not message.buttons:
            return

        for row_index, row in enumerate(message.buttons):
            for column_index, button in enumerate(row):
                label = str(getattr(button, "text", "") or "").strip()
                key = normalize(label)
                if not is_safe(label) or key in self.visited_labels:
                    continue
                self.visited_labels.add(key)
                btn_record = button_map.get((row_index, column_index))
                try:
                    logging.info("Bấm mục an toàn: %s", label)
                    result = await message.click(row_index, column_index)
                    if btn_record:
                        btn_record.clicked = True
                    await asyncio.sleep(self.delay)
                    if isinstance(result, Message):
                        await self.inspect_message(result, depth + 1)
                    else:
                        latest = await self.client.get_messages(self.bot_username, limit=1)
                        if latest and latest[0].id > message.id:
                            await self.inspect_message(latest[0], depth + 1)
                        else:
                            edited = await self.client.get_messages(self.bot_username, ids=message.id)
                            if edited:
                                await self.inspect_message(edited, depth + 1)
                except FloodWaitError as exc:
                    if btn_record:
                        btn_record.error = str(exc)
                    logging.warning("Telegram yêu cầu chờ %s giây; dừng an toàn.", exc.seconds)
                    return
                except RPCError as exc:
                    if btn_record:
                        btn_record.error = str(exc)
                    logging.warning("Không thể bấm '%s': %s", label, exc)
                except Exception as exc:  # bảo đảm một nút lỗi không làm mất log
                    if btn_record:
                        btn_record.error = str(exc)
                    logging.warning("Lỗi khi xử lý '%s': %s", label, exc)

    async def run(self) -> None:
        await self.client.start()
        bot = await self.client.get_entity(self.bot_username)
        logging.info("Đang phân tích bot: %s", getattr(bot, "username", self.bot_username))
        start_msg = await self.client.send_message(bot, "/start")
        await asyncio.sleep(self.delay)
        messages = await self.client.get_messages(bot, min_id=start_msg.id, limit=5)
        if not messages:
            logging.warning("Bot chưa trả lời. Hãy kiểm tra username và quyền truy cập.")
        for message in reversed(messages):
            await self.inspect_message(message, depth=0)
        self.save()

    def save(self) -> None:
        output = OUTPUT_DIR / f"analysis-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
        payload: dict[str, Any] = {
            "bot": self.bot_username,
            "generated_at": now_iso(),
            "safety": {
                "mode": "safe-menu-exploration",
                "blocked_terms": list(BLOCKED_TERMS),
                "clicked_only_allowlist": True,
            },
            "messages": [asdict(record) for record in self.records],
        }
        output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        logging.info("Đã lưu kết quả: %s", output)


def required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Thiếu biến môi trường {name}. Hãy điền trong file .env.")
    return value


def main() -> None:
    load_dotenv(ROOT / ".env")
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
    api_id = int(required_env("TELEGRAM_API_ID"))
    api_hash = required_env("TELEGRAM_API_HASH")
    bot_username = required_env("BOT_USERNAME").lstrip("@").strip()
    session_name = os.getenv("SESSION_NAME", "safe-analyzer").strip() or "safe-analyzer"
    max_depth = int(os.getenv("MAX_DEPTH", "2"))
    delay = max(1.0, float(os.getenv("DELAY_SECONDS", "2")))
    if max_depth < 0 or max_depth > 5:
        raise ValueError("MAX_DEPTH phải nằm trong khoảng 0 đến 5.")
    if not re.fullmatch(r"[A-Za-z0-9_]{3,64}", bot_username):
        raise ValueError("BOT_USERNAME không hợp lệ.")

    client = TelegramClient(str(ROOT / session_name), api_id, api_hash)
    try:
        with client:
            client.loop.run_until_complete(Analyzer(client, bot_username, max_depth, delay).run())
    except KeyboardInterrupt:
        logging.info("Đã dừng theo yêu cầu người dùng.")


if __name__ == "__main__":
    main()
