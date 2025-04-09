#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
from telegram import Bot
import asyncio
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get bot token and admin ID from environment variables
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
ADMIN_TELEGRAM_ID = int(os.getenv('ADMIN_TELEGRAM_ID'))

async def send_welcome_message():
    """Send welcome message to admin."""
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    
    # Welcome message in Persian
    welcome_message = """
🎉 *نصب SMPanel با موفقیت انجام شد!*

سلام ادمین عزیز،
ربات SMPanel با موفقیت نصب و راه‌اندازی شد. اکنون می‌توانید از ربات برای مدیریت پنل‌های خود استفاده کنید.

برای شروع، دستور /start را ارسال کنید.

با تشکر،
تیم SMPanel
"""
    
    try:
        # Send welcome message to admin
        print("Sending welcome message to admin...")
        await bot.send_message(
            chat_id=ADMIN_TELEGRAM_ID,
            text=welcome_message,
            parse_mode='Markdown'
        )
        print("Welcome message sent successfully to admin.")
    except Exception as e:
        print(f"Error sending welcome message: {e}")

if __name__ == "__main__":
    # Run the async function
    asyncio.run(send_welcome_message())
