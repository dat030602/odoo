#!/usr/bin/env python3
"""
Neutralize DB Odoo local (dùng SQL trực tiếp).

Cách dùng:
    python neutralize_odoo_db.py              # sẽ hỏi tên DB
    python neutralize_odoo_db.py my_db        # truyền thẳng tên DB
    python neutralize_odoo_db.py my_db --host localhost --port 5432 --pg-user odoo --pg-password odoo

Việc script làm:
  1. User admin: login = admin, password = admin (hash pbkdf2-sha512 chuẩn Odoo), tắt 2FA
  2. active = false: ir_cron, ir_mail_server, fetchmail_server, base_automation
  3. Huỷ mail/sms/mailing đang chờ gửi
  4. Tắt các model có thể bắn data ra ngoài (payment provider, OAuth, delivery carrier prod, webhook...)
  5. database.expiration_date = hôm nay + 20 năm
"""
import argparse
import base64
import hashlib
import os
import sys
from datetime import datetime

import psycopg2

ADMIN_LOGIN = "admin"
ADMIN_PASSWORD = "admin"
PBKDF2_ROUNDS = 600000  # khớp mặc định Odoo 19
# Giá trị dùng khi database.expiration_date CHƯA tồn tại (định dạng Odoo: %Y-%m-%d %H:%M:%S)
NEW_EXPIRATION_DATE = "2050-01-01 00:00:00"


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def ab64(data: bytes) -> str:
    """Định dạng adapted-base64 của passlib."""
    return base64.b64encode(data).decode().rstrip("=").replace("+", ".")


def hash_password(password: str, rounds: int = PBKDF2_ROUNDS) -> str:
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha512", password.encode(), salt, rounds)
    return "$pbkdf2-sha512$%d$%s$%s" % (rounds, ab64(salt), ab64(dk))


def table_exists(cr, table):
    cr.execute(
        "SELECT 1 FROM information_schema.tables "
        "WHERE table_schema = current_schema() AND table_name = %s",
        (table,),
    )
    return bool(cr.fetchone())


def column_exists(cr, table, column):
    cr.execute(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_schema = current_schema() AND table_name = %s AND column_name = %s",
        (table, column),
    )
    return bool(cr.fetchone())


def run(cr, label, table, sql, params=None, required_columns=()):
    """Chạy UPDATE/DELETE nếu table + column tồn tại, in số dòng bị ảnh hưởng."""
    if not table_exists(cr, table):
        print(f"  [skip] {label}: không có bảng {table}")
        return
    for col in required_columns:
        if not column_exists(cr, table, col):
            print(f"  [skip] {label}: bảng {table} không có cột {col}")
            return
    cr.execute(sql, params or ())
    print(f"  [ok]   {label}: {cr.rowcount} dòng")


# --------------------------------------------------------------------------- #
# Các bước
# --------------------------------------------------------------------------- #
def step_admin_user(cr):
    print("\n== User admin ==")
    cr.execute(
        "SELECT res_id FROM ir_model_data "
        "WHERE module = 'base' AND name = 'user_admin' AND model = 'res.users'"
    )
    row = cr.fetchone()
    uid = row[0] if row else 2

    cr.execute(
        "UPDATE res_users SET login = %s, password = %s, active = true WHERE id = %s",
        (ADMIN_LOGIN, hash_password(ADMIN_PASSWORD), uid),
    )
    print(f"  [ok]   admin (id={uid}): login={ADMIN_LOGIN}, password={ADMIN_PASSWORD}")

    # Tắt 2FA nếu có (module auth_totp)
    if column_exists(cr, "res_users", "totp_secret"):
        cr.execute("UPDATE res_users SET totp_secret = NULL WHERE id = %s", (uid,))
        print("  [ok]   tắt 2FA (totp_secret = NULL)")
    if table_exists(cr, "auth_totp_device"):
        cr.execute("DELETE FROM auth_totp_device WHERE user_id = %s", (uid,))


def step_deactivate(cr):
    print("\n== Active = false ==")
    run(cr, "Scheduled actions (ir_cron)", "ir_cron",
        "UPDATE ir_cron SET active = false WHERE active = true", required_columns=("active",))
    run(cr, "Cron triggers đang chờ", "ir_cron_trigger", "DELETE FROM ir_cron_trigger")
    run(cr, "Outgoing mail server", "ir_mail_server",
        "UPDATE ir_mail_server SET active = false WHERE active = true", required_columns=("active",))
    run(cr, "Incoming mail server (fetchmail)", "fetchmail_server",
        "UPDATE fetchmail_server SET active = false WHERE active = true", required_columns=("active",))
    run(cr, "Fetchmail state -> draft", "fetchmail_server",
        "UPDATE fetchmail_server SET state = 'draft' WHERE state <> 'draft'", required_columns=("state",))
    run(cr, "Automation rules (base_automation)", "base_automation",
        "UPDATE base_automation SET active = false WHERE active = true", required_columns=("active",))


def step_pending_messages(cr):
    print("\n== Huỷ tin nhắn đang chờ gửi ==")
    run(cr, "mail_mail outgoing -> cancel", "mail_mail",
        "UPDATE mail_mail SET state = 'cancel' WHERE state IN ('outgoing')", required_columns=("state",))
    run(cr, "sms_sms outgoing -> canceled", "sms_sms",
        "UPDATE sms_sms SET state = 'canceled' WHERE state IN ('outgoing')", required_columns=("state",))
    run(cr, "mailing_mailing in_queue/sending -> draft", "mailing_mailing",
        "UPDATE mailing_mailing SET state = 'draft' WHERE state IN ('in_queue', 'sending')",
        required_columns=("state",))


def step_external_models(cr):
    print("\n== Model có thể bắn data ra ngoài ==")
    run(cr, "Payment provider -> disabled", "payment_provider",
        "UPDATE payment_provider SET state = 'disabled' WHERE state <> 'disabled'",
        required_columns=("state",))
    run(cr, "OAuth provider -> disabled", "auth_oauth_provider",
        "UPDATE auth_oauth_provider SET enabled = false WHERE enabled = true",
        required_columns=("enabled",))
    run(cr, "Delivery carrier -> test env", "delivery_carrier",
        "UPDATE delivery_carrier SET prod_environment = false WHERE prod_environment = true",
        required_columns=("prod_environment",))
    run(cr, "Webhook server action -> xoá URL", "ir_act_server",
        "UPDATE ir_act_server SET webhook_url = NULL WHERE state = 'webhook'",
        required_columns=("webhook_url", "state"))
    run(cr, "LDAP -> xoá server", "res_company_ldap",
        "DELETE FROM res_company_ldap")
    run(cr, "IAP account -> xoá token", "iap_account",
        "UPDATE iap_account SET account_token = 'neutralized' WHERE account_token IS NOT NULL",
        required_columns=("account_token",))


def step_expiration(cr):
    print("\n== database.expiration_date ==")
    now = datetime.now()
    try:
        new_date = now.replace(year=now.year + 20)
    except ValueError:  # 29/02
        new_date = now.replace(year=now.year + 20, day=28)
    value = new_date.strftime("%Y-%m-%d %H:%M:%S")

    cr.execute("UPDATE ir_config_parameter SET value = %s WHERE key = 'database.expiration_date'", (value,))
    if cr.rowcount == 0:
        # Chưa có param -> thêm mới với năm cố định
        value = NEW_EXPIRATION_DATE
        cr.execute(
            "INSERT INTO ir_config_parameter (key, value, create_date, write_date) "
            "VALUES ('database.expiration_date', %s, now(), now())",
            (value,),
        )
        print(f"  [ok]   tạo mới database.expiration_date = {value}")
    else:
        print(f"  [ok]   database.expiration_date = {value} (+20 năm)")


# --------------------------------------------------------------------------- #
def main():
    parser = argparse.ArgumentParser(description="Neutralize Odoo local database")
    parser.add_argument("dbname", nargs="?", help="Tên database")
    parser.add_argument("--host", default=os.environ.get("PGHOST", "localhost"))
    parser.add_argument("--port", default=os.environ.get("PGPORT", "5432"))
    parser.add_argument("--pg-user", default=os.environ.get("PGUSER", "odoo"))
    parser.add_argument("--pg-password", default=os.environ.get("PGPASSWORD", "odoo"))
    args = parser.parse_args()

    dbname = args.dbname or input("Nhập tên database: ").strip()
    if not dbname:
        sys.exit("Chưa nhập tên database.")

    conn = psycopg2.connect(
        dbname=dbname, host=args.host, port=args.port,
        user=args.pg_user, password=args.pg_password,
    )
    try:
        with conn.cursor() as cr:
            step_admin_user(cr)
            step_deactivate(cr)
            step_pending_messages(cr)
            step_external_models(cr)
            step_expiration(cr)
        conn.commit()
        print(f"\nXong. Đã neutralize DB '{dbname}'.")
    except Exception as e:
        conn.rollback()
        print(f"\nLỗi, đã rollback: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
