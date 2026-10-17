"""Quản lý cơ sở dữ liệu (Hỗ trợ song song Supabase PostgreSQL & SQLite Local) cho Bot Reseller."""

from __future__ import annotations

import json
import logging
import os
import re
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterator

from dotenv import load_dotenv

try:
    import psycopg2
    import psycopg2.extras
    import psycopg2.pool
except ImportError:
    psycopg2 = None  # type: ignore[assignment]

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")

DB_PATH = ROOT / "shop.db"
VN_TZ = timezone(timedelta(hours=7))
logger = logging.getLogger("reseller_bot.db")

DEFAULT_SETTINGS: dict[str, str] = {
    "markup_percent": "25.0",            # Mặc định tăng +25% so với giá vốn ProdSeller
    "markup_fixed": "0",                 # Cộng thêm VNĐ cố định
    "vnd_rate": "25500",                 # Tỷ giá 1 USD = 25,500 VNĐ
    "bank_id": "MB",                     # Mã ngân hàng VietQR (MB, VCB, TCB, ACB, BIDV, ICB...)
    "bank_account_no": "0123456789",     # Số tài khoản nhận tiền
    "bank_account_name": "NGUYEN VAN A",
    "usdt_bep20_address": "",
    "binance_pay_id": "",
    "support_admin": "KingToolShopSupport",  # Kênh/Nhóm CSKH riêng (ẩn danh tài khoản cá nhân)
    "support_channel": "KingToolShopOfficial",
    "methods_text": "📭 Hiện chưa có tài liệu hướng dẫn (Methods) nào.",
    "sepay_api_token": "",               # API Token lấy từ my.sepay.vn (nếu dùng duyệt tự động ban đêm)
    "sepay_night_start": "23",           # Giờ bắt đầu tự động duyệt (23h00)
    "sepay_night_end": "6",              # Giờ kết thúc tự động duyệt (06h00 sáng)
    "sepay_monthly_limit": "50",         # Giới hạn gói Free SePay (50 giao dịch/tháng)
    "sepay_used_month": "",              # Tháng hiện tại (YYYY-MM)
    "sepay_used_count": "0",             # Số giao dịch đã tự động duyệt qua SePay trong tháng
    "referral_commission_pct": "5.0",    # % Hoa hồng giới thiệu khi bạn bè nạp tiền thành công
    "point_value_vnd": "100",            # Giá trị quy đổi 1 Điểm thưởng = 100 VNĐ
    "low_balance_threshold_usd": "5.0",  # Ngưỡng cảnh báo số dư vốn ProdSeller sắp hết ($ USD)
    "restock_notify_enabled": "1",       # Tự động đăng thông báo hàng về (Restock) lên kênh (1=Bật, 0=Tắt)
    "deposit_bonus_enabled": "1",        # Bật/Tắt khuyến mãi cộng thêm % khi nạp tiền theo mốc (1=Bật, 0=Tắt)
    "deposit_bonus_tiers": "200000:5,500000:10",  # Mốc nạp VNĐ : % thưởng thêm (VD: 200k +5%, 500k +10%)
    "auto_post_enabled": "1",            # Tự động đăng Bảng giá & Spotlight SP Hot theo khung giờ (1=Bật, 0=Tắt)
    "auto_post_hours": "9,14,20",        # Khung giờ vàng tự động đăng bài lên Kênh mỗi ngày (Giờ VN UTC+7)
    "last_catalog_msg_id": "0",          # ID bài Bảng giá gần nhất trên Kênh (để xóa bài cũ tránh rác kênh)
    "auto_social_proof_enabled": "1",    # Tự động đăng thông báo đơn hàng hoàn tất (Social Proof) định kỳ (1=Bật, 0=Tắt)
    "newbie_gift_enabled": "1",          # Phễu nhận Quà Tân Thủ khi tham gia Kênh @KingToolShopOfficial (1=Bật, 0=Tắt)
    "newbie_gift_voucher": "TANTHU10",   # Mã giảm giá tặng Tân thủ khi tham gia Kênh (mặc định giảm 10%)
    "newbie_gift_points": "5",           # Số điểm thưởng tặng Tân thủ khi tham gia Kênh (mặc định +5 điểm)
    "deposit_reminder_enabled": "1",     # Tự động nhắc khách hoàn tất đơn nạp VietQR bỏ dở sau 10 phút (1=Bật, 0=Tắt)
}

TIER_DISCOUNTS: dict[str, int] = {
    "bronze": 0,
    "silver": 3,
    "gold": 5,
}

_TABLE_NAME_RE = re.compile(
    r"(?<![.'\"_])\b(settings|users|product_overrides|deposits|orders|vouchers|voucher_usages|api_keys)\b(?![.'\"_])"
)


def now_str() -> str:
    return datetime.now(VN_TZ).strftime("%Y-%m-%d %H:%M:%S")


class _PgSessionWrapper:
    """Wrapper giúp cú pháp truy vấn trên psycopg2 tương thích 100% với sqlite3."""

    def __init__(self, pg_conn: Any) -> None:
        self._conn = pg_conn
        self._cur = pg_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    @staticmethod
    def _translate_sql(sql: str) -> str:
        # Đưa toàn bộ bảng vào Schema riêng 'telebot' để tách biệt 100% khỏi Schema 'public'
        translated = _TABLE_NAME_RE.sub(r"telebot.\1", sql)
        # Đổi placeholder ? sang %s của psycopg2
        translated = translated.replace("?", "%s")
        return translated

    def execute(self, sql: str, params: tuple[Any, ...] | list[Any] | None = None) -> Any:
        q = self._translate_sql(sql)
        if params:
            self._cur.execute(q, params)
        else:
            self._cur.execute(q)
        return self._cur

    def close(self) -> None:
        try:
            self._cur.close()
        except Exception:
            pass


class Database:
    def __init__(self, db_path: Path = DB_PATH, database_url: str | None = None) -> None:
        self.db_path = db_path
        raw_url = (database_url if database_url is not None else os.getenv("DATABASE_URL", "")).strip()
        self.database_url = self._normalize_pg_url(raw_url)
        self.use_postgres = bool(self.database_url and psycopg2 is not None)
        self._pg_pool: Any = None
        self._last_pg_used: float = 0.0
        # RAM Caches giúp tốc độ đọc Menu / Sản phẩm đạt 0.001 giây (Zero N+1 Query)
        self._settings_cache: dict[str, str] | None = None
        self._settings_cache_ts: float = 0.0
        self._overrides_cache: dict[str, dict[str, Any]] | None = None
        self._overrides_cache_ts: float = 0.0
        self._vouchers_cache: dict[str, dict[str, Any]] | None = None
        self._vouchers_cache_ts: float = 0.0
        self._users_cache: dict[int, tuple[float, dict[str, Any]]] = {}
        self._api_keys_by_user: dict[int, tuple[float, dict[str, Any]]] = {}
        self._api_keys_by_token: dict[str, tuple[float, int]] = {}
        self._init_db()

    @staticmethod
    def _normalize_pg_url(url: str) -> str:
        if not url:
            return ""
        if url.startswith("postgres://"):
            url = "postgresql://" + url[len("postgres://") :]
        return url

    def _get_pg_conn(self) -> Any:
        import time

        if self._pg_pool is None:
            self._pg_pool = psycopg2.pool.ThreadedConnectionPool(
                minconn=1,
                maxconn=10,
                dsn=self.database_url,
                connect_timeout=10,
                keepalives=1,
                keepalives_idle=30,
                keepalives_interval=10,
                keepalives_count=5,
            )
        conn = self._pg_pool.getconn()
        now = time.monotonic()
        # Chỉ kiểm tra kết nối nếu đã nhàn rỗi quá 20 giây (tránh tốn 2 lần mạng cho mỗi câu lệnh)
        if getattr(conn, "closed", 0) != 0 or (now - self._last_pg_used > 20.0):
            try:
                with conn.cursor() as c:
                    c.execute("SELECT 1")
            except Exception:
                try:
                    self._pg_pool.putconn(conn, close=True)
                except Exception:
                    pass
                conn = psycopg2.connect(self.database_url, connect_timeout=10)
        self._last_pg_used = now
        return conn

    @contextmanager
    def _conn(self) -> Iterator[Any]:
        if self.use_postgres:
            pg_conn = self._get_pg_conn()
            wrapper = _PgSessionWrapper(pg_conn)
            try:
                yield wrapper
                pg_conn.commit()
            except Exception:
                pg_conn.rollback()
                raise
            finally:
                wrapper.close()
                if self._pg_pool is not None:
                    try:
                        self._pg_pool.putconn(pg_conn)
                    except Exception:
                        try:
                            pg_conn.close()
                        except Exception:
                            pass
        else:
            conn = sqlite3.connect(self.db_path, timeout=15.0)
            conn.row_factory = sqlite3.Row
            try:
                yield conn
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()

    def _init_db(self) -> None:
        if self.use_postgres:
            with self._conn() as conn:
                conn.execute(
                    """
                    CREATE SCHEMA IF NOT EXISTS telebot;

                    DO $$
                    DECLARE
                        t TEXT;
                    BEGIN
                        FOREACH t IN ARRAY ARRAY['settings', 'users', 'product_overrides', 'deposits', 'orders'] LOOP
                            IF EXISTS (
                                SELECT 1 FROM information_schema.tables
                                WHERE table_schema = 'public' AND table_name = 'telebot_' || t
                            ) THEN
                                IF NOT EXISTS (
                                    SELECT 1 FROM information_schema.tables
                                    WHERE table_schema = 'telebot' AND table_name = t
                                ) THEN
                                    EXECUTE format('ALTER TABLE public.telebot_%I SET SCHEMA telebot', t);
                                    EXECUTE format('ALTER TABLE telebot.telebot_%I RENAME TO %I', t, t);
                                ELSE
                                    EXECUTE format('DROP TABLE public.telebot_%I CASCADE', t);
                                END IF;
                            END IF;
                        END LOOP;
                    END $$;

                    CREATE TABLE IF NOT EXISTS settings (
                        key TEXT PRIMARY KEY,
                        value TEXT NOT NULL
                    );

                    CREATE TABLE IF NOT EXISTS users (
                        telegram_id BIGINT PRIMARY KEY,
                        username TEXT DEFAULT '',
                        balance NUMERIC(18, 2) DEFAULT 0.0,
                        points INTEGER DEFAULT 0,
                        tier TEXT DEFAULT 'bronze',
                        orders_count INTEGER DEFAULT 0,
                        total_spent NUMERIC(18, 2) DEFAULT 0.0,
                        language TEXT DEFAULT 'vi',
                        referred_by BIGINT DEFAULT NULL,
                        gift_claimed INTEGER DEFAULT 0,
                        joined_at TEXT NOT NULL
                    );

                    ALTER TABLE users ADD COLUMN IF NOT EXISTS gift_claimed INTEGER DEFAULT 0;

                    CREATE TABLE IF NOT EXISTS product_overrides (
                        product_id TEXT PRIMARY KEY,
                        custom_price NUMERIC(18, 2) DEFAULT NULL,
                        hidden INTEGER DEFAULT 0
                    );

                    CREATE TABLE IF NOT EXISTS deposits (
                        id BIGSERIAL PRIMARY KEY,
                        user_id BIGINT NOT NULL,
                        username TEXT DEFAULT '',
                        amount_usd NUMERIC(18, 4) NOT NULL,
                        amount_vnd BIGINT NOT NULL,
                        method TEXT NOT NULL,
                        memo TEXT NOT NULL,
                        status TEXT DEFAULT 'pending',
                        created_at TEXT NOT NULL,
                        updated_at TEXT DEFAULT NULL
                    );

                    CREATE TABLE IF NOT EXISTS orders (
                        id BIGSERIAL PRIMARY KEY,
                        user_id BIGINT NOT NULL,
                        username TEXT DEFAULT '',
                        product_id TEXT NOT NULL,
                        product_name TEXT NOT NULL,
                        quantity INTEGER NOT NULL,
                        wholesale_cost NUMERIC(18, 4) NOT NULL,
                        retail_price NUMERIC(18, 2) NOT NULL,
                        profit NUMERIC(18, 4) NOT NULL,
                        prodseller_order_id TEXT DEFAULT '',
                        status TEXT NOT NULL,
                        delivered_keys TEXT DEFAULT '[]',
                        activation_email TEXT DEFAULT '',
                        created_at TEXT NOT NULL
                    );

                    CREATE TABLE IF NOT EXISTS vouchers (
                        code TEXT PRIMARY KEY,
                        discount_type TEXT NOT NULL DEFAULT 'percent',
                        discount_value NUMERIC(18, 2) NOT NULL DEFAULT 0,
                        max_uses INTEGER NOT NULL DEFAULT 0,
                        used_count INTEGER NOT NULL DEFAULT 0,
                        active INTEGER NOT NULL DEFAULT 1,
                        created_at TEXT NOT NULL
                    );

                    CREATE TABLE IF NOT EXISTS voucher_usages (
                        id BIGSERIAL PRIMARY KEY,
                        code TEXT NOT NULL,
                        user_id BIGINT NOT NULL,
                        order_id BIGINT NOT NULL DEFAULT 0,
                        discount_amount BIGINT NOT NULL DEFAULT 0,
                        used_at TEXT NOT NULL,
                        UNIQUE(code, user_id)
                    );

                    CREATE TABLE IF NOT EXISTS api_keys (
                        user_id BIGINT PRIMARY KEY,
                        api_key TEXT NOT NULL UNIQUE,
                        total_requests BIGINT NOT NULL DEFAULT 0,
                        active INTEGER NOT NULL DEFAULT 1,
                        created_at TEXT NOT NULL
                    );
                    """
                )
                for k, v in DEFAULT_SETTINGS.items():
                    conn.execute(
                        "INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT (key) DO NOTHING",
                        (k, v),
                    )
                conn.execute(
                    """
                    INSERT INTO vouchers (code, discount_type, discount_value, max_uses, used_count, active, created_at)
                    VALUES ('TANTHU10', 'percent', 10.0, 0, 0, 1, ?)
                    ON CONFLICT (code) DO NOTHING
                    """,
                    (now_str(),),
                )
            self._migrate_sqlite_to_postgres_if_needed()
            logger.info("☁️ Đã kết nối cơ sở dữ liệu đám mây Supabase PostgreSQL (Schema: telebot) thành công!")
        else:
            with self._conn() as conn:
                conn.executescript(
                    """
                    CREATE TABLE IF NOT EXISTS settings (
                        key TEXT PRIMARY KEY,
                        value TEXT NOT NULL
                    );

                    CREATE TABLE IF NOT EXISTS users (
                        telegram_id INTEGER PRIMARY KEY,
                        username TEXT DEFAULT '',
                        balance REAL DEFAULT 0.0,
                        points INTEGER DEFAULT 0,
                        tier TEXT DEFAULT 'bronze',
                        orders_count INTEGER DEFAULT 0,
                        total_spent REAL DEFAULT 0.0,
                        language TEXT DEFAULT 'vi',
                        referred_by INTEGER DEFAULT NULL,
                        gift_claimed INTEGER DEFAULT 0,
                        joined_at TEXT NOT NULL
                    );

                    CREATE TABLE IF NOT EXISTS product_overrides (
                        product_id TEXT PRIMARY KEY,
                        custom_price REAL DEFAULT NULL,
                        hidden INTEGER DEFAULT 0
                    );

                    CREATE TABLE IF NOT EXISTS deposits (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        username TEXT DEFAULT '',
                        amount_usd REAL NOT NULL,
                        amount_vnd INTEGER NOT NULL,
                        method TEXT NOT NULL,
                        memo TEXT NOT NULL,
                        status TEXT DEFAULT 'pending',
                        created_at TEXT NOT NULL,
                        updated_at TEXT DEFAULT NULL
                    );

                    CREATE TABLE IF NOT EXISTS orders (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        username TEXT DEFAULT '',
                        product_id TEXT NOT NULL,
                        product_name TEXT NOT NULL,
                        quantity INTEGER NOT NULL,
                        wholesale_cost REAL NOT NULL,
                        retail_price REAL NOT NULL,
                        profit REAL NOT NULL,
                        prodseller_order_id TEXT DEFAULT '',
                        status TEXT NOT NULL,
                        delivered_keys TEXT DEFAULT '[]',
                        activation_email TEXT DEFAULT '',
                        created_at TEXT NOT NULL
                    );

                    CREATE TABLE IF NOT EXISTS vouchers (
                        code TEXT PRIMARY KEY,
                        discount_type TEXT NOT NULL DEFAULT 'percent',
                        discount_value REAL NOT NULL DEFAULT 0,
                        max_uses INTEGER NOT NULL DEFAULT 0,
                        used_count INTEGER NOT NULL DEFAULT 0,
                        active INTEGER NOT NULL DEFAULT 1,
                        created_at TEXT NOT NULL
                    );

                    CREATE TABLE IF NOT EXISTS voucher_usages (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        code TEXT NOT NULL,
                        user_id INTEGER NOT NULL,
                        order_id INTEGER NOT NULL DEFAULT 0,
                        discount_amount INTEGER NOT NULL DEFAULT 0,
                        used_at TEXT NOT NULL,
                        UNIQUE(code, user_id)
                    );

                    CREATE TABLE IF NOT EXISTS api_keys (
                        user_id INTEGER PRIMARY KEY,
                        api_key TEXT NOT NULL UNIQUE,
                        total_requests INTEGER NOT NULL DEFAULT 0,
                        active INTEGER NOT NULL DEFAULT 1,
                        created_at TEXT NOT NULL
                    );
                    """
                )
                try:
                    conn.execute("ALTER TABLE users ADD COLUMN gift_claimed INTEGER DEFAULT 0")
                except Exception:
                    pass
                for k, v in DEFAULT_SETTINGS.items():
                    conn.execute(
                        "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
                        (k, v),
                    )
                conn.execute(
                    """
                    INSERT OR IGNORE INTO vouchers (code, discount_type, discount_value, max_uses, used_count, active, created_at)
                    VALUES ('TANTHU10', 'percent', 10.0, 0, 0, 1, ?)
                    """,
                    (now_str(),),
                )

    def _migrate_sqlite_to_postgres_if_needed(self) -> None:
        """Đồng bộ dữ liệu sẵn có từ file shop.db ở local lên Supabase trong lần chạy đầu."""
        if not self.use_postgres or not self.db_path.exists():
            return
        try:
            sq = sqlite3.connect(self.db_path)
            sq.row_factory = sqlite3.Row
            with self._conn() as pg:
                # 1. Settings (chỉ cập nhật các giá trị khác mặc định nếu chưa đồng bộ)
                already_migrated = pg.execute(
                    "SELECT value FROM settings WHERE key = ?",
                    ("_sqlite_migrated",),
                ).fetchone()
                if already_migrated:
                    sq.close()
                    return

                for r in sq.execute("SELECT key, value FROM settings").fetchall():
                    pg.execute(
                        "INSERT INTO settings (key, value) VALUES (?, ?) "
                        "ON CONFLICT (key) DO UPDATE SET value = excluded.value",
                        (r["key"], r["value"]),
                    )

                # 2. Users
                for r in sq.execute("SELECT * FROM users").fetchall():
                    d = dict(r)
                    pg.execute(
                        """
                        INSERT INTO users (
                            telegram_id, username, balance, points, tier,
                            orders_count, total_spent, language, referred_by, joined_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT (telegram_id) DO NOTHING
                        """,
                        (
                            d["telegram_id"],
                            d.get("username", ""),
                            d.get("balance", 0.0),
                            d.get("points", 0),
                            d.get("tier", "bronze"),
                            d.get("orders_count", 0),
                            d.get("total_spent", 0.0),
                            d.get("language", "vi"),
                            d.get("referred_by"),
                            d.get("joined_at", now_str()),
                        ),
                    )

                # 3. Product overrides
                for r in sq.execute("SELECT * FROM product_overrides").fetchall():
                    d = dict(r)
                    pg.execute(
                        """
                        INSERT INTO product_overrides (product_id, custom_price, hidden)
                        VALUES (?, ?, ?)
                        ON CONFLICT (product_id) DO NOTHING
                        """,
                        (d["product_id"], d.get("custom_price"), d.get("hidden", 0)),
                    )

                # 4. Deposits
                for r in sq.execute("SELECT * FROM deposits").fetchall():
                    d = dict(r)
                    pg.execute(
                        """
                        INSERT INTO deposits (
                            id, user_id, username, amount_usd, amount_vnd,
                            method, memo, status, created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT (id) DO NOTHING
                        """,
                        (
                            d["id"],
                            d["user_id"],
                            d.get("username", ""),
                            d["amount_usd"],
                            d["amount_vnd"],
                            d["method"],
                            d["memo"],
                            d.get("status", "pending"),
                            d["created_at"],
                            d.get("updated_at"),
                        ),
                    )
                pg.execute(
                    "SELECT setval(pg_get_serial_sequence('telebot.deposits', 'id'), "
                    "COALESCE((SELECT MAX(id) FROM deposits), 1), true)"
                )

                # 5. Orders
                for r in sq.execute("SELECT * FROM orders").fetchall():
                    d = dict(r)
                    pg.execute(
                        """
                        INSERT INTO orders (
                            id, user_id, username, product_id, product_name, quantity,
                            wholesale_cost, retail_price, profit, prodseller_order_id,
                            status, delivered_keys, activation_email, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT (id) DO NOTHING
                        """,
                        (
                            d["id"],
                            d["user_id"],
                            d.get("username", ""),
                            d["product_id"],
                            d["product_name"],
                            d["quantity"],
                            d["wholesale_cost"],
                            d["retail_price"],
                            d["profit"],
                            d.get("prodseller_order_id", ""),
                            d["status"],
                            d.get("delivered_keys", "[]"),
                            d.get("activation_email", ""),
                            d["created_at"],
                        ),
                    )
                pg.execute(
                    "SELECT setval(pg_get_serial_sequence('telebot.orders', 'id'), "
                    "COALESCE((SELECT MAX(id) FROM orders), 1), true)"
                )

                pg.execute(
                    "INSERT INTO settings (key, value) VALUES (?, ?) "
                    "ON CONFLICT (key) DO UPDATE SET value = excluded.value",
                    ("_sqlite_migrated", now_str()),
                )
            sq.close()
            logger.info("✅ Đã tự động chuyển dữ liệu từ shop.db (Local) lên Supabase!")
        except Exception as exc:
            logger.warning("Không thể đồng bộ tự động từ shop.db: %s", exc)

    # --- Settings (Có RAM Cache 60s + Write-Through) ---
    def get_setting(self, key: str, default: str = "") -> str:
        settings = self.get_all_settings()
        return str(settings.get(key, default))

    def set_setting(self, key: str, value: str) -> None:
        val_str = str(value)
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO settings (key, value) VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (key, val_str),
            )
        if self._settings_cache is not None:
            self._settings_cache[key] = val_str

    def get_all_settings(self) -> dict[str, str]:
        import time

        now = time.monotonic()
        if self._settings_cache is not None and (now - self._settings_cache_ts < 60.0):
            return dict(self._settings_cache)
        with self._conn() as conn:
            rows = conn.execute("SELECT key, value FROM settings").fetchall()
            result = dict(DEFAULT_SETTINGS)
            for r in rows:
                result[r["key"]] = r["value"]
            self._settings_cache = result
            self._settings_cache_ts = now
            return dict(result)

    # --- Users (Có RAM Cache 45s + Tự động xóa cache khi đổi số dư/ngôn ngữ) ---
    def get_or_create_user(self, telegram_id: int, username: str = "", referred_by: int | None = None) -> dict[str, Any]:
        import time

        now = time.monotonic()
        cached = self._users_cache.get(telegram_id)
        if cached is not None and (now - cached[0] < 45.0):
            u_cached = cached[1]
            if not username or u_cached.get("username") == username:
                return dict(u_cached)

        with self._conn() as conn:
            row = conn.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)).fetchone()
            if not row:
                conn.execute(
                    "INSERT INTO users (telegram_id, username, referred_by, joined_at) VALUES (?, ?, ?, ?)",
                    (telegram_id, username or "", referred_by, now_str()),
                )
                row = conn.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)).fetchone()
            elif username and row["username"] != username:
                conn.execute("UPDATE users SET username = ? WHERE telegram_id = ?", (username, telegram_id))
                row = conn.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)).fetchone()
            res = dict(row)
            self._users_cache[telegram_id] = (now, res)
            return dict(res)

    def find_user(self, query: str) -> dict[str, Any] | None:
        q = query.strip().lstrip("@")
        if not q:
            return None
        with self._conn() as conn:
            if q.isdigit():
                row = conn.execute("SELECT * FROM users WHERE telegram_id = ?", (int(q),)).fetchone()
                if row:
                    return dict(row)
            row = conn.execute(
                "SELECT * FROM users WHERE LOWER(username) = LOWER(?) ORDER BY total_spent DESC LIMIT 1",
                (q,),
            ).fetchone()
            return dict(row) if row else None

    def get_all_user_ids(self) -> list[int]:
        with self._conn() as conn:
            rows = conn.execute("SELECT telegram_id FROM users ORDER BY joined_at ASC").fetchall()
            return [int(r["telegram_id"]) for r in rows]

    def set_user_language(self, telegram_id: int, lang: str) -> None:
        with self._conn() as conn:
            conn.execute("UPDATE users SET language = ? WHERE telegram_id = ?", (lang, telegram_id))
        if telegram_id in self._users_cache:
            ts, u = self._users_cache[telegram_id]
            u["language"] = lang
            self._users_cache[telegram_id] = (ts, u)

    def adjust_balance(self, telegram_id: int, delta_vnd: float) -> int:
        with self._conn() as conn:
            conn.execute(
                """
                UPDATE users
                SET balance = CASE
                    WHEN balance + ? < 0 THEN 0
                    ELSE ROUND(balance + ?, 0)
                END
                WHERE telegram_id = ?
                """,
                (delta_vnd, delta_vnd, telegram_id),
            )
            row = conn.execute("SELECT balance FROM users WHERE telegram_id = ?", (telegram_id,)).fetchone()
            new_bal = int(round(float(row["balance"]))) if row else 0
        self._users_cache.pop(telegram_id, None)
        return new_bal

    def deduct_balance_atomic(self, telegram_id: int, amount_vnd: int) -> tuple[bool, int]:
        """Trừ số dư nguyên tử (Atomic). Trả về (thành_công, số_dư_hiện_tại)."""
        if amount_vnd <= 0:
            u = self.get_or_create_user(telegram_id)
            return True, int(round(float(u["balance"])))
        with self._conn() as conn:
            cur = conn.execute(
                """
                UPDATE users
                SET balance = ROUND(balance - ?, 0)
                WHERE telegram_id = ? AND ROUND(balance, 0) >= ?
                """,
                (amount_vnd, telegram_id, amount_vnd),
            )
            row = conn.execute("SELECT balance FROM users WHERE telegram_id = ?", (telegram_id,)).fetchone()
            bal = int(round(float(row["balance"]))) if row else 0
            ok = cur.rowcount == 1
        self._users_cache.pop(telegram_id, None)
        return ok, bal

    def redeem_user_points(self, telegram_id: int, min_points: int = 10) -> tuple[bool, int, int, int]:
        """Đổi toàn bộ điểm thưởng hiện có sang số dư VNĐ.
        Trả về (thành_công, số_điểm_đã_đổi, tiền_vnđ_cộng, số_dư_mới).
        """
        point_rate = max(1, int(float(self.get_setting("point_value_vnd", "100") or 100)))
        with self._conn() as conn:
            row = conn.execute(
                "SELECT points, balance FROM users WHERE telegram_id = ?",
                (telegram_id,),
            ).fetchone()
            if not row:
                return False, 0, 0, 0
            pts = int(row["points"] or 0)
            cur_bal = int(round(float(row["balance"] or 0)))
            if pts < min_points:
                return False, pts, 0, cur_bal
            bonus_vnd = pts * point_rate
            cur = conn.execute(
                """
                UPDATE users
                SET points = 0,
                    balance = ROUND(balance + ?, 0)
                WHERE telegram_id = ? AND points = ?
                """,
                (bonus_vnd, telegram_id, pts),
            )
            if cur.rowcount != 1:
                return False, 0, 0, cur_bal
            new_row = conn.execute("SELECT balance FROM users WHERE telegram_id = ?", (telegram_id,)).fetchone()
            new_bal = int(round(float(new_row["balance"]))) if new_row else cur_bal + bonus_vnd
        self._users_cache.pop(telegram_id, None)
        return True, pts, bonus_vnd, new_bal

    def record_purchase_stats(self, telegram_id: int, spent_vnd: int) -> None:
        points_earned = max(1, int(spent_vnd // 10000))
        with self._conn() as conn:
            conn.execute(
                """
                UPDATE users
                SET orders_count = orders_count + 1,
                    total_spent = ROUND(total_spent + ?, 0),
                    points = points + ?,
                    tier = CASE
                        WHEN total_spent + ? >= 2500000 THEN 'gold'
                        WHEN total_spent + ? >= 600000 THEN 'silver'
                        ELSE 'bronze'
                    END
                WHERE telegram_id = ?
                """,
                (spent_vnd, points_earned, spent_vnd, spent_vnd, telegram_id),
            )
        self._users_cache.pop(telegram_id, None)

    def get_referral_stats(self, telegram_id: int) -> int:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS cnt FROM users WHERE referred_by = ?",
                (telegram_id,),
            ).fetchone()
            return int(row["cnt"]) if row else 0

    def claim_newbie_gift(self, telegram_id: int, bonus_points: int = 5) -> tuple[bool, int]:
        """Nhận Quà Tân Thủ nguyên tử (mỗi khách chỉ được nhận 1 lần duy nhất).
        Trả về (thành_công, tổng_điểm_hiện_tại).
        """
        pts_add = max(0, int(bonus_points))
        with self._conn() as conn:
            cur = conn.execute(
                """
                UPDATE users
                SET gift_claimed = 1,
                    points = COALESCE(points, 0) + ?
                WHERE telegram_id = ? AND COALESCE(gift_claimed, 0) = 0
                """,
                (pts_add, telegram_id),
            )
            ok = cur.rowcount == 1
            row = conn.execute("SELECT points FROM users WHERE telegram_id = ?", (telegram_id,)).fetchone()
            cur_pts = int(row["points"] or 0) if row else 0
        self._users_cache.pop(telegram_id, None)
        return ok, cur_pts

    # --- Product Overrides & Retail Price Calculation (VNĐ - Có RAM Cache 60s) ---
    def get_product_override(self, product_id: str) -> dict[str, Any] | None:
        all_ov = self.get_all_overrides()
        return all_ov.get(product_id)

    def get_all_overrides(self) -> dict[str, dict[str, Any]]:
        import time

        now = time.monotonic()
        if self._overrides_cache is not None and (now - self._overrides_cache_ts < 60.0):
            return dict(self._overrides_cache)
        with self._conn() as conn:
            rows = conn.execute("SELECT * FROM product_overrides").fetchall()
            res = {r["product_id"]: dict(r) for r in rows}
            self._overrides_cache = res
            self._overrides_cache_ts = now
            return dict(res)

    def set_product_custom_price(self, product_id: str, custom_price: float | None) -> None:
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO product_overrides (product_id, custom_price, hidden)
                VALUES (?, ?, 0)
                ON CONFLICT(product_id) DO UPDATE SET custom_price = excluded.custom_price
                """,
                (product_id, custom_price),
            )
        self._overrides_cache = None

    def toggle_product_hidden(self, product_id: str) -> bool:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT hidden FROM product_overrides WHERE product_id = ?",
                (product_id,),
            ).fetchone()
            new_val = 0 if (row and row["hidden"]) else 1
            conn.execute(
                """
                INSERT INTO product_overrides (product_id, custom_price, hidden)
                VALUES (?, NULL, ?)
                ON CONFLICT(product_id) DO UPDATE SET hidden = excluded.hidden
                """,
                (product_id, new_val),
            )
        self._overrides_cache = None
        return bool(new_val)

    def compute_wholesale_vnd(self, wholesale_usd: float) -> int:
        rate = float(self.get_setting("vnd_rate", "25500") or 25500.0)
        return int(round(wholesale_usd * rate))

    def compute_retail_price(self, product_id: str, wholesale_usd: float, overrides: dict[str, dict[str, Any]] | None = None) -> int:
        """Tính giá bán lẻ niêm yết bằng VNĐ (đ)."""
        rate = float(self.get_setting("vnd_rate", "25500") or 25500.0)
        ov = (overrides or {}).get(product_id) if overrides is not None else self.get_product_override(product_id)
        if ov and ov.get("custom_price") is not None:
            cp = float(ov["custom_price"])
            return int(round(cp * rate)) if cp < 500 else int(round(cp))

        pct = float(self.get_setting("markup_percent", "25.0") or 0.0)
        fixed_vnd = float(self.get_setting("markup_fixed", "0") or 0.0)

        cost_vnd = wholesale_usd * rate
        raw_retail = cost_vnd * (1.0 + pct / 100.0) + fixed_vnd
        raw_retail = max(cost_vnd, raw_retail)
        if raw_retail < 5000:
            return max(500, int(round(raw_retail / 500.0) * 500))
        return int(round(raw_retail / 1000.0) * 1000)

    def compute_tier_unit_price(
        self,
        product_id: str,
        wholesale_usd: float,
        tier: str = "bronze",
        overrides: dict[str, dict[str, Any]] | None = None,
    ) -> tuple[int, int, int]:
        """Trả về (giá_niêm_yết_vnđ, giá_sau_ưu_đãi_hạng_vnđ, phần_trăm_giảm).
        Luôn đảm bảo giá sau giảm không bao giờ thấp hơn giá vốn đại lý.
        """
        base_vnd = self.compute_retail_price(product_id, wholesale_usd, overrides)
        disc_pct = TIER_DISCOUNTS.get((tier or "bronze").lower(), 0)
        if disc_pct <= 0:
            return base_vnd, base_vnd, 0
        cost_vnd = self.compute_wholesale_vnd(wholesale_usd)
        discounted = int(round(base_vnd * (100 - disc_pct) / 100.0 / 500.0) * 500)
        final_vnd = max(cost_vnd, discounted)
        if final_vnd >= base_vnd:
            return base_vnd, base_vnd, 0
        return base_vnd, final_vnd, disc_pct

    # --- Vouchers (Mã Giảm Giá + Chốt chặn chống lỗ vốn + RAM Cache 60s) ---
    def get_all_vouchers(self) -> dict[str, dict[str, Any]]:
        import time

        now = time.monotonic()
        if self._vouchers_cache is not None and (now - self._vouchers_cache_ts < 60.0):
            return dict(self._vouchers_cache)
        with self._conn() as conn:
            rows = conn.execute("SELECT * FROM vouchers ORDER BY created_at DESC").fetchall()
            res = {str(r["code"]).upper(): dict(r) for r in rows}
            self._vouchers_cache = res
            self._vouchers_cache_ts = now
            return dict(res)

    def get_voucher(self, code: str) -> dict[str, Any] | None:
        c = (code or "").strip().upper()
        if not c:
            return None
        return self.get_all_vouchers().get(c)

    def create_or_update_voucher(
        self,
        code: str,
        discount_type: str,
        discount_value: float,
        max_uses: int = 0,
    ) -> dict[str, Any]:
        c = code.strip().upper()
        dtype = "percent" if discount_type == "percent" else "fixed"
        dval = round(float(discount_value), 2)
        m_uses = max(0, int(max_uses))
        created = now_str()
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO vouchers (code, discount_type, discount_value, max_uses, used_count, active, created_at)
                VALUES (?, ?, ?, ?, 0, 1, ?)
                ON CONFLICT(code) DO UPDATE SET
                    discount_type = excluded.discount_type,
                    discount_value = excluded.discount_value,
                    max_uses = excluded.max_uses,
                    active = 1
                """,
                (c, dtype, dval, m_uses, created),
            )
        self._vouchers_cache = None
        return self.get_voucher(c) or {
            "code": c,
            "discount_type": dtype,
            "discount_value": dval,
            "max_uses": m_uses,
            "used_count": 0,
            "active": 1,
            "created_at": created,
        }

    def toggle_voucher_active(self, code: str) -> bool:
        c = code.strip().upper()
        with self._conn() as conn:
            row = conn.execute("SELECT active FROM vouchers WHERE code = ?", (c,)).fetchone()
            if not row:
                return False
            new_val = 0 if int(row["active"] or 0) == 1 else 1
            conn.execute("UPDATE vouchers SET active = ? WHERE code = ?", (new_val, c))
        self._vouchers_cache = None
        return bool(new_val)

    def delete_voucher(self, code: str) -> bool:
        c = code.strip().upper()
        with self._conn() as conn:
            cur = conn.execute("DELETE FROM vouchers WHERE code = ?", (c,))
            conn.execute("DELETE FROM voucher_usages WHERE code = ?", (c,))
            deleted = cur.rowcount > 0
        self._vouchers_cache = None
        return deleted

    def has_user_used_voucher(self, code: str, user_id: int) -> bool:
        c = (code or "").strip().upper()
        if not c:
            return False
        with self._conn() as conn:
            row = conn.execute(
                "SELECT 1 AS used FROM voucher_usages WHERE code = ? AND user_id = ?",
                (c, user_id),
            ).fetchone()
            return bool(row)

    def validate_voucher_for_user(
        self,
        code: str,
        user_id: int | None = None,
    ) -> tuple[bool, str, dict[str, Any] | None]:
        """Kiểm tra mã giảm giá hợp lệ cho khách hàng:
        Trả về (hợp_lệ, mã_lý_do, thông_tin_voucher).
        Các mã lý do: 'ok', 'not_found', 'inactive', 'exhausted', 'already_used'.
        """
        c = (code or "").strip().upper()
        if not c:
            return False, "not_found", None
        v = self.get_voucher(c)
        if not v:
            return False, "not_found", None
        if int(v.get("active", 0) or 0) != 1:
            return False, "inactive", v
        max_u = int(v.get("max_uses", 0) or 0)
        used_u = int(v.get("used_count", 0) or 0)
        if max_u > 0 and used_u >= max_u:
            return False, "exhausted", v
        if user_id is not None and self.has_user_used_voucher(c, user_id):
            return False, "already_used", v
        return True, "ok", v

    def redeem_voucher_atomic(
        self,
        code: str,
        user_id: int,
        order_id: int,
        discount_amount: int,
    ) -> bool:
        """Ghi nhận lượt sử dụng mã giảm giá của khách hàng sau khi mua thành công."""
        c = (code or "").strip().upper()
        if not c:
            return False
        with self._conn() as conn:
            cur = conn.execute(
                """
                INSERT INTO voucher_usages (code, user_id, order_id, discount_amount, used_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(code, user_id) DO NOTHING
                """,
                (c, user_id, order_id, int(discount_amount), now_str()),
            )
            if cur.rowcount == 1:
                conn.execute(
                    "UPDATE vouchers SET used_count = used_count + 1 WHERE code = ?",
                    (c,),
                )
                self._vouchers_cache = None
                return True
        return False

    def compute_order_pricing(
        self,
        product_id: str,
        wholesale_usd: float,
        qty: int = 1,
        tier: str = "bronze",
        voucher_code: str | None = None,
        user_id: int | None = None,
        overrides: dict[str, dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Tính toán chi tiết giá đơn hàng (kết hợp Hạng VIP + Mã Giảm Giá Voucher).
        🛡️ Chốt chặn chống lỗ vốn: Tổng tiền thanh toán cuối cùng (total_final_vnd)
        LUÔN >= Tổng giá vốn đại lý (total_cost_vnd).
        """
        qty = max(1, int(qty))
        unit_cost_vnd = self.compute_wholesale_vnd(wholesale_usd)
        total_cost_vnd = self.compute_wholesale_vnd(wholesale_usd * qty)
        base_unit_vnd, vip_unit_vnd, vip_disc_pct = self.compute_tier_unit_price(
            product_id, wholesale_usd, tier, overrides
        )
        total_base_vnd = base_unit_vnd * qty
        total_vip_vnd = max(total_cost_vnd, vip_unit_vnd * qty)

        voucher_valid = False
        voucher_reason = ""
        applied_code = ""
        voucher_discount_vnd = 0
        floor_capped = False
        total_final_vnd = total_vip_vnd

        if voucher_code:
            ok, reason, v = self.validate_voucher_for_user(voucher_code, user_id)
            voucher_reason = reason
            if ok and v:
                voucher_valid = True
                applied_code = str(v["code"]).upper()
                dtype = str(v.get("discount_type", "percent"))
                dval = float(v.get("discount_value", 0) or 0)
                if dtype == "percent":
                    raw_disc = int(round(total_vip_vnd * (dval / 100.0) / 500.0) * 500)
                    if raw_disc == 0 and dval > 0:
                        raw_disc = int(round(total_vip_vnd * (dval / 100.0)))
                else:
                    raw_disc = int(round(dval))

                raw_final = total_vip_vnd - raw_disc
                if raw_final < total_cost_vnd:
                    floor_capped = True
                    total_final_vnd = total_cost_vnd
                else:
                    total_final_vnd = raw_final
                voucher_discount_vnd = max(0, total_vip_vnd - total_final_vnd)

        return {
            "qty": qty,
            "unit_cost_vnd": unit_cost_vnd,
            "total_cost_vnd": total_cost_vnd,
            "base_unit_vnd": base_unit_vnd,
            "vip_unit_vnd": vip_unit_vnd,
            "vip_disc_pct": vip_disc_pct,
            "total_base_vnd": total_base_vnd,
            "total_vip_vnd": total_vip_vnd,
            "total_final_vnd": total_final_vnd,
            "voucher_valid": voucher_valid,
            "voucher_code": applied_code,
            "voucher_discount_vnd": voucher_discount_vnd,
            "voucher_reason": voucher_reason,
            "floor_capped": floor_capped,
        }

    # --- Deposits, Deposit Bonus Tiers & SePay Night-Shift Auto-Approval ---
    def get_deposit_bonus_tiers(self) -> list[tuple[int, float]]:
        """Trả về danh sách các mốc khuyến mãi nạp tiền [(min_vnd, bonus_pct), ...] tăng dần theo mốc."""
        enabled = str(self.get_setting("deposit_bonus_enabled", "1") or "0").strip() == "1"
        if not enabled:
            return []
        raw = str(self.get_setting("deposit_bonus_tiers", "200000:5,500000:10") or "").strip()
        if not raw:
            return []
        tiers: list[tuple[int, float]] = []
        for item in raw.split(","):
            item = item.strip()
            if ":" not in item:
                continue
            k_str, v_str = item.split(":", 1)
            try:
                min_vnd = int(float(k_str.strip()))
                pct = float(v_str.strip())
                if min_vnd > 0 and pct > 0:
                    tiers.append((min_vnd, pct))
            except ValueError:
                continue
        tiers.sort(key=lambda x: x[0])
        return tiers

    def compute_deposit_bonus(self, amount_vnd: int) -> tuple[int, float]:
        """Tính số tiền thưởng nạp thêm: Trả về (bonus_vnd, bonus_pct)."""
        tiers = self.get_deposit_bonus_tiers()
        if not tiers or amount_vnd <= 0:
            return 0, 0.0
        matched_pct = 0.0
        for min_vnd, pct in tiers:
            if amount_vnd >= min_vnd:
                matched_pct = pct
        if matched_pct <= 0:
            return 0, 0.0
        bonus_vnd = int(round(amount_vnd * matched_pct / 100.0))
        return bonus_vnd, matched_pct

    def is_in_night_auto_window(self) -> bool:
        """Kiểm tra giờ hiện tại (Giờ Việt Nam UTC+7) có nằm trong khung 23h00 -> 06h00 sáng không."""
        now_vn = datetime.now(VN_TZ)
        h = now_vn.hour
        start_h = int(float(self.get_setting("sepay_night_start", "23") or 23))
        end_h = int(float(self.get_setting("sepay_night_end", "6") or 6))
        if start_h > end_h:
            return h >= start_h or h < end_h
        return start_h <= h < end_h

    def get_sepay_quota_status(self) -> tuple[int, int, bool]:
        """Trả về (used_count, monthly_limit, can_use_sepay). Tự động reset khi sang tháng mới."""
        cur_month = datetime.now(VN_TZ).strftime("%Y-%m")
        saved_month = self.get_setting("sepay_used_month", "")
        if saved_month != cur_month:
            self.set_setting("sepay_used_month", cur_month)
            self.set_setting("sepay_used_count", "0")
            used = 0
        else:
            used = int(float(self.get_setting("sepay_used_count", "0") or 0))
        limit = int(float(self.get_setting("sepay_monthly_limit", "50") or 50))
        token = (self.get_setting("sepay_api_token", "") or os.getenv("SEPAY_API_TOKEN", "")).strip()
        can_use = bool(token) and (used < limit)
        return used, limit, can_use

    def increment_sepay_used(self) -> int:
        used, _, _ = self.get_sepay_quota_status()
        new_used = used + 1
        self.set_setting("sepay_used_count", str(new_used))
        return new_used

    def expire_old_pending_deposits(self, hours: int = 24) -> int:
        """Tự động chuyển các đơn nạp pending quá hạn (mặc định 24 giờ) sang trạng thái expired."""
        import time

        now = time.monotonic()
        if getattr(self, "_last_expire_check", 0.0) and (now - getattr(self, "_last_expire_check", 0.0) < 300.0):
            return 0
        self._last_expire_check = now
        cutoff = (datetime.now(VN_TZ) - timedelta(hours=hours)).strftime("%Y-%m-%d %H:%M:%S")
        with self._conn() as conn:
            cur = conn.execute(
                """
                UPDATE deposits
                SET status = 'expired', updated_at = ?
                WHERE status = 'pending' AND created_at < ?
                """,
                (now_str(), cutoff),
            )
            return cur.rowcount

    def create_deposit(self, user_id: int, username: str, amount_usd: float, amount_vnd: int, method: str, memo: str) -> int:
        self.expire_old_pending_deposits(hours=24)
        with self._conn() as conn:
            cur = conn.execute(
                """
                INSERT INTO deposits (user_id, username, amount_usd, amount_vnd, method, memo, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, 'pending', ?)
                RETURNING id
                """,
                (user_id, username, amount_usd, amount_vnd, method, memo, now_str()),
            )
            row = cur.fetchone()
            return int(row["id"])

    def get_deposit(self, deposit_id: int) -> dict[str, Any] | None:
        with self._conn() as conn:
            row = conn.execute("SELECT * FROM deposits WHERE id = ?", (deposit_id,)).fetchone()
            return dict(row) if row else None

    def find_deposit_by_code(self, code: str) -> dict[str, Any] | None:
        c = (code or "").strip().upper()
        if not c:
            return None
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM deposits WHERE UPPER(memo) LIKE ? ORDER BY id DESC LIMIT 1",
                (f"%{c}%",),
            ).fetchone()
            return dict(row) if row else None

    def get_pending_deposits(self, limit: int = 20) -> list[dict[str, Any]]:
        self.expire_old_pending_deposits(hours=24)
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM deposits WHERE status = 'pending' ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
            return [dict(r) for r in rows]

    def get_unreminded_pending_deposits(self, min_age_minutes: int = 10, max_age_minutes: int = 45) -> list[dict[str, Any]]:
        """Lấy các đơn nạp đang pending được tạo trong khoảng [now - max_age_minutes, now - min_age_minutes] để nhắc khách."""
        now_dt = datetime.now(VN_TZ)
        older_than = (now_dt - timedelta(minutes=min_age_minutes)).strftime("%Y-%m-%d %H:%M:%S")
        newer_than = (now_dt - timedelta(minutes=max_age_minutes)).strftime("%Y-%m-%d %H:%M:%S")
        with self._conn() as conn:
            rows = conn.execute(
                """
                SELECT * FROM deposits
                WHERE status = 'pending' AND created_at >= ? AND created_at <= ?
                ORDER BY id ASC
                """,
                (newer_than, older_than),
            ).fetchall()
            return [dict(r) for r in rows]

    def update_deposit_status(self, deposit_id: int, status: str, memo: str | None = None) -> bool:
        with self._conn() as conn:
            row = conn.execute("SELECT status FROM deposits WHERE id = ?", (deposit_id,)).fetchone()
            if not row or row["status"] != "pending":
                return False
            if memo:
                conn.execute(
                    "UPDATE deposits SET status = ?, memo = ?, updated_at = ? WHERE id = ?",
                    (status, memo, now_str(), deposit_id),
                )
            else:
                conn.execute(
                    "UPDATE deposits SET status = ?, updated_at = ? WHERE id = ?",
                    (status, now_str(), deposit_id),
                )
            return True

    # --- Orders ---
    def create_order_record(
        self,
        user_id: int,
        username: str,
        product_id: str,
        product_name: str,
        quantity: int,
        wholesale_cost: float,
        retail_price: float,
        prodseller_order_id: str,
        status: str,
        delivered_keys: list[str],
        activation_email: str = "",
    ) -> int:
        profit = round(retail_price - wholesale_cost, 4)
        with self._conn() as conn:
            cur = conn.execute(
                """
                INSERT INTO orders (
                    user_id, username, product_id, product_name, quantity,
                    wholesale_cost, retail_price, profit, prodseller_order_id,
                    status, delivered_keys, activation_email, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                RETURNING id
                """,
                (
                    user_id,
                    username,
                    product_id,
                    product_name,
                    quantity,
                    wholesale_cost,
                    retail_price,
                    profit,
                    prodseller_order_id,
                    status,
                    json.dumps(delivered_keys, ensure_ascii=False),
                    activation_email,
                    now_str(),
                ),
            )
            row = cur.fetchone()
            return int(row["id"])

    def get_user_orders(self, user_id: int, limit: int = 10) -> list[dict[str, Any]]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM orders WHERE user_id = ? ORDER BY id DESC LIMIT ?",
                (user_id, limit),
            ).fetchall()
            return [dict(r) for r in rows]

    def get_user_orders_paginated(
        self,
        user_id: int,
        page: int = 1,
        limit: int = 50,
        status: str | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        page = max(1, int(page))
        limit = max(1, min(200, int(limit)))
        offset = (page - 1) * limit
        with self._conn() as conn:
            if status and status in ("pending", "paid", "delivered", "failed"):
                cnt_row = conn.execute(
                    "SELECT COUNT(*) AS c FROM orders WHERE user_id = ? AND status = ?",
                    (user_id, status),
                ).fetchone()
                rows = conn.execute(
                    "SELECT * FROM orders WHERE user_id = ? AND status = ? ORDER BY id DESC LIMIT ? OFFSET ?",
                    (user_id, status, limit, offset),
                ).fetchall()
            else:
                cnt_row = conn.execute(
                    "SELECT COUNT(*) AS c FROM orders WHERE user_id = ?",
                    (user_id,),
                ).fetchone()
                rows = conn.execute(
                    "SELECT * FROM orders WHERE user_id = ? ORDER BY id DESC LIMIT ? OFFSET ?",
                    (user_id, limit, offset),
                ).fetchall()
            total = int(cnt_row["c"]) if cnt_row else 0
            return [dict(r) for r in rows], total

    def get_order_by_id(self, order_id: int, user_id: int | None = None) -> dict[str, Any] | None:
        with self._conn() as conn:
            if user_id is not None:
                row = conn.execute(
                    "SELECT * FROM orders WHERE id = ? AND user_id = ?",
                    (order_id, user_id),
                ).fetchone()
            else:
                row = conn.execute(
                    "SELECT * FROM orders WHERE id = ?",
                    (order_id,),
                ).fetchone()
            return dict(row) if row else None

    get_order = get_order_by_id

    # --- Reseller Public API Keys (Schema telebot.api_keys + RAM Cache) ---
    @staticmethod
    def _generate_new_key_token() -> str:
        import secrets

        return f"ktk_{secrets.token_hex(24)}"

    @staticmethod
    def mask_api_key(key_str: str) -> str:
        k = (key_str or "").strip()
        if len(k) <= 16:
            return k
        return f"{k[:10]}••••••••••••••••••{k[-4:]}"

    def get_or_create_api_key(self, user_id: int) -> dict[str, Any]:
        import time

        now = time.monotonic()
        cached = self._api_keys_by_user.get(user_id)
        if cached is not None and (now - cached[0] < 45.0):
            return dict(cached[1])

        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM api_keys WHERE user_id = ?",
                (user_id,),
            ).fetchone()
            if not row:
                new_token = self._generate_new_key_token()
                created = now_str()
                conn.execute(
                    """
                    INSERT INTO api_keys (user_id, api_key, total_requests, active, created_at)
                    VALUES (?, ?, 0, 1, ?)
                    ON CONFLICT(user_id) DO NOTHING
                    """,
                    (user_id, new_token, created),
                )
                row = conn.execute(
                    "SELECT * FROM api_keys WHERE user_id = ?",
                    (user_id,),
                ).fetchone()
            res = dict(row)
            self._api_keys_by_user[user_id] = (now, res)
            self._api_keys_by_token[str(res["api_key"])] = (now, user_id)
            return dict(res)

    def regenerate_api_key(self, user_id: int) -> dict[str, Any]:
        import time

        now = time.monotonic()
        old_cached = self._api_keys_by_user.pop(user_id, None)
        if old_cached:
            self._api_keys_by_token.pop(str(old_cached[1].get("api_key", "")), None)

        new_token = self._generate_new_key_token()
        created = now_str()
        with self._conn() as conn:
            row = conn.execute(
                "SELECT api_key FROM api_keys WHERE user_id = ?",
                (user_id,),
            ).fetchone()
            if row:
                self._api_keys_by_token.pop(str(row["api_key"]), None)
            conn.execute(
                """
                INSERT INTO api_keys (user_id, api_key, total_requests, active, created_at)
                VALUES (?, ?, 0, 1, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    api_key = excluded.api_key,
                    active = 1,
                    created_at = excluded.created_at
                """,
                (user_id, new_token, created),
            )
            new_row = conn.execute(
                "SELECT * FROM api_keys WHERE user_id = ?",
                (user_id,),
            ).fetchone()
            res = dict(new_row) if new_row else {
                "user_id": user_id,
                "api_key": new_token,
                "total_requests": 0,
                "active": 1,
                "created_at": created,
            }
        self._api_keys_by_user[user_id] = (now, res)
        self._api_keys_by_token[new_token] = (now, user_id)
        return dict(res)

    def authenticate_api_key(self, api_key: str) -> dict[str, Any] | None:
        """Xác thực X-API-Key từ HTTP Header, tăng bộ đếm total_requests và trả về thông tin user."""
        token = (api_key or "").strip()
        if not token or not token.startswith("ktk_"):
            return None
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM api_keys WHERE api_key = ? AND active = 1",
                (token,),
            ).fetchone()
            if not row:
                return None
            uid = int(row["user_id"])
            conn.execute(
                "UPDATE api_keys SET total_requests = total_requests + 1 WHERE user_id = ?",
                (uid,),
            )
        self._api_keys_by_user.pop(uid, None)
        return self.get_or_create_user(uid)

    def get_recent_orders(self, limit: int = 10) -> list[dict[str, Any]]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM orders ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
            return [dict(r) for r in rows]

    def get_pending_activation_orders(self) -> list[dict[str, Any]]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM orders WHERE status = 'paid' AND prodseller_order_id != ''"
            ).fetchall()
            return [dict(r) for r in rows]

    def mark_order_delivered(self, order_id: int, keys: list[str]) -> None:
        with self._conn() as conn:
            conn.execute(
                "UPDATE orders SET status = 'delivered', delivered_keys = ? WHERE id = ?",
                (json.dumps(keys, ensure_ascii=False), order_id),
            )

    def get_summary_stats(self) -> dict[str, Any]:
        self.expire_old_pending_deposits(hours=24)
        with self._conn() as conn:
            u_cnt = conn.execute("SELECT COUNT(*) AS c FROM users").fetchone()["c"]
            o_row = conn.execute(
                """
                SELECT COUNT(*) AS cnt,
                       COALESCE(SUM(retail_price), 0) AS rev,
                       COALESCE(SUM(wholesale_cost), 0) AS cost,
                       COALESCE(SUM(profit), 0) AS prof
                FROM orders
                WHERE status IN ('paid', 'delivered')
                """
            ).fetchone()
            d_row = conn.execute(
                "SELECT COALESCE(SUM(amount_vnd), 0) AS dep FROM deposits WHERE status = 'approved'"
            ).fetchone()
            p_row = conn.execute(
                "SELECT COUNT(*) AS pcnt FROM deposits WHERE status = 'pending'"
            ).fetchone()
            return {
                "users_count": int(u_cnt),
                "orders_count": int(o_row["cnt"]),
                "total_revenue": round(float(o_row["rev"]), 2),
                "total_cost": round(float(o_row["cost"]), 2),
                "total_profit": round(float(o_row["prof"]), 2),
                "total_deposited": round(float(d_row["dep"]), 2),
                "pending_deposits_count": int(p_row["pcnt"]),
            }
