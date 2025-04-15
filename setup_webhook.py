#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import requests
import logging
from dotenv import load_dotenv

# تنظیم لاگینگ
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# بارگذاری متغیرهای محیطی
load_dotenv()

# دریافت توکن بات و آدرس وبهوک
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
WEBHOOK_URL = os.getenv('WEBHOOK_URL')
WEBHOOK_PATH = os.getenv('WEBHOOK_PATH', '/webhook')

if not TELEGRAM_BOT_TOKEN:
    logger.error("خطا: TELEGRAM_BOT_TOKEN در فایل .env یافت نشد!")
    exit(1)

if not WEBHOOK_URL:
    logger.error("خطا: WEBHOOK_URL در فایل .env یافت نشد!")
    exit(1)

# آدرس کامل وبهوک
full_webhook_url = f"{WEBHOOK_URL}{WEBHOOK_PATH}/{TELEGRAM_BOT_TOKEN}"

# حذف وبهوک قبلی
delete_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/deleteWebhook"
response = requests.get(delete_url)
if response.status_code == 200 and response.json().get('ok'):
    logger.info("وبهوک قبلی با موفقیت حذف شد.")
else:
    logger.error(f"خطا در حذف وبهوک قبلی: {response.text}")
    exit(1)

# تنظیم وبهوک جدید
set_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/setWebhook"
params = {
    'url': full_webhook_url,
    'max_connections': 100,
    'drop_pending_updates': True
}

response = requests.post(set_url, json=params)
if response.status_code == 200 and response.json().get('ok'):
    logger.info(f"وبهوک با موفقیت تنظیم شد: {full_webhook_url}")
else:
    logger.error(f"خطا در تنظیم وبهوک: {response.text}")
    exit(1)

# بررسی وضعیت وبهوک
info_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getWebhookInfo"
response = requests.get(info_url)
if response.status_code == 200:
    webhook_info = response.json()
    logger.info(f"اطلاعات وبهوک: {webhook_info}")
else:
    logger.error(f"خطا در دریافت اطلاعات وبهوک: {response.text}")

print("\n✅ تنظیم وبهوک با موفقیت انجام شد!")
print(f"🔗 آدرس وبهوک: {full_webhook_url}")
print("🚀 حالا می‌توانید سرور وبهوک را راه‌اندازی کنید.") 