#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import logging
import requests
from flask import Flask, request, jsonify
from dotenv import load_dotenv

# تنظیم لاگینگ
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler("webhook_server.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# بارگذاری متغیرهای محیطی
load_dotenv()

# دریافت توکن بات
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
SERVER_PORT = int(os.getenv('SERVER_PORT', '8443'))
WEBHOOK_PATH = os.getenv('WEBHOOK_PATH', '/webhook')

if not TELEGRAM_BOT_TOKEN:
    logger.error("خطا: TELEGRAM_BOT_TOKEN در فایل .env یافت نشد!")
    exit(1)

# ایجاد نمونه Flask
app = Flask(__name__)

# آدرس‌های API تلگرام
API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

# ارسال پیام به تلگرام
def send_message(chat_id, text, reply_markup=None):
    """ارسال پیام به تلگرام"""
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML"
    }
    
    if reply_markup:
        payload["reply_markup"] = reply_markup
        
    try:
        response = requests.post(f"{API_URL}/sendMessage", json=payload)
        if response.status_code == 200:
            return True
        logger.error(f"خطا در ارسال پیام: {response.text}")
        return False
    except Exception as e:
        logger.error(f"خطا در ارسال پیام: {e}")
        return False

# مسیر اصلی
@app.route('/')
def index():
    """صفحه اصلی سرور"""
    return "سرور وبهوک تلگرام در حال اجراست!"

# مسیر وبهوک
@app.route(f'{WEBHOOK_PATH}/{TELEGRAM_BOT_TOKEN}', methods=['POST'])
def webhook():
    """دریافت و پردازش پیام‌های تلگرام"""
    try:
        # دریافت آپدیت از تلگرام
        update = request.get_json()
        logger.info(f"آپدیت دریافت شد: {json.dumps(update, ensure_ascii=False)}")
        
        # پردازش پیام‌ها
        if 'message' in update:
            handle_message(update['message'])
        
        # پردازش کالبک کوئری‌ها
        elif 'callback_query' in update:
            handle_callback_query(update['callback_query'])
        
        return jsonify({"status": "success"})
        
    except Exception as e:
        logger.error(f"خطا در پردازش وبهوک: {e}")
        return jsonify({"status": "error", "message": str(e)})

# پردازش پیام‌ها
def handle_message(message):
    """پردازش پیام‌های دریافتی"""
    chat_id = message.get('chat', {}).get('id')
    text = message.get('text', '')
    
    logger.info(f"پیام از کاربر {chat_id}: {text}")
    
    # پردازش دستور /start
    if text == '/start':
        from src.bot.index import main_menu
        return main_menu.show(None, {'user_data': {}, 'effective_chat': {'id': chat_id}})
    
    elif text == 'مدیریت':
        from src.bot.index import admin_menu
        return admin_menu.show(None, {'user_data': {}, 'effective_chat': {'id': chat_id}})
    
    # سایر پیام‌ها
    else:
        keyboard = [
            [{"text": "مدیریت"}],
            [{"text": "🏪 فروشگاه"}]
        ]
        reply_markup = {"keyboard": keyboard, "resize_keyboard": True}
        send_message(chat_id, f"پیام شما دریافت شد: {text}", reply_markup)

# پردازش کالبک کوئری‌ها
def handle_callback_query(callback_query):
    """پردازش کالبک‌های دریافتی"""
    chat_id = callback_query.get('message', {}).get('chat', {}).get('id')
    callback_data = callback_query.get('data', '')
    
    logger.info(f"کالبک از کاربر {chat_id}: {callback_data}")
    
    # پردازش کالبک‌ها
    if callback_data.startswith('panel_'):
        # اینجا می‌توانید منطق اختصاصی پردازش کالبک‌ها را قرار دهید
        send_message(chat_id, f"دکمه فشرده شده: {callback_data}")
    else:
        send_message(chat_id, f"کالبک ناشناخته: {callback_data}")

# راه‌اندازی سرور
if __name__ == '__main__':
    logger.info(f"سرور وبهوک در حال راه‌اندازی روی پورت {SERVER_PORT}...")
    app.run(host='0.0.0.0', port=SERVER_PORT, debug=False) 