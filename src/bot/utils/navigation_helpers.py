#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import logging
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

# تنظیم لاگینگ
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def handle_back_to_menu(
    update: Update, 
    context: ContextTypes.DEFAULT_TYPE,
    menu_callback,
    menu_name: str,
    target_state: str,
    user_states_dict: dict
):
    """
    یک تابع عمومی برای بازگشت به منوهای مختلف
    
    Args:
        update: شیء Update تلگرام
        context: شیء Context تلگرام
        menu_callback: تابعی که منو را نمایش می‌دهد
        menu_name: نام منو برای لاگ
        target_state: وضعیت هدف برای تغییر وضعیت کاربر
        user_states_dict: دیکشنری وضعیت‌های کاربر
    
    Returns:
        ConversationHandler.END اگر در یک مکالمه بودیم، در غیر این صورت None
    """
    logger.info(f"Handling back to {menu_name} menu")
    
    # بررسی تکراری بودن پردازش
    flag_key = f'back_to_{target_state}_handled'
    if context.user_data.get(flag_key):
        logger.debug(f"Back to {menu_name} command already handled, skipping duplicate")
        return ConversationHandler.END if context.user_data.get('in_conversation', False) else None
    
    # علامت‌گذاری پردازش
    context.user_data[flag_key] = True
    
    # پاک کردن علامت پس از مدتی
    async def reset_handler_flag():
        await asyncio.sleep(1)
        if flag_key in context.user_data:
            del context.user_data[flag_key]
    
    # شروع تایمر پاک کردن علامت
    asyncio.create_task(reset_handler_flag())
    
    # پاک کردن وضعیت مکالمه
    was_in_conversation = context.user_data.get('in_conversation', False)
    context.user_data['in_conversation'] = False
    
    # پاک کردن داده‌های موقت
    for key in list(context.user_data.keys()):
        if key.startswith('selected_'):
            del context.user_data[key]
    
    # تنظیم وضعیت کاربر
    user_id = update.effective_user.id
    user_states_dict[user_id] = target_state
    
    # نمایش پیام لغو اگر در مکالمه بودیم
    if was_in_conversation:
        await update.message.reply_text("❌ عملیات لغو شد.")
    
    # نمایش منوی هدف
    await menu_callback(update, context)
    
    # پایان مکالمه اگر در یک مکالمه بودیم
    if was_in_conversation:
        return ConversationHandler.END
    return None

async def show_menu_with_chat_id(menu_obj, chat_id, context: ContextTypes.DEFAULT_TYPE, user_id=None, user_states_dict=None, target_state=None):
    """
    نمایش منو با استفاده از chat_id
    
    Args:
        menu_obj: شیء منو که متد setup_menu و create_keyboard_markup دارد
        chat_id: شناسه چت برای ارسال منو
        context: شیء Context تلگرام
        user_id: شناسه کاربر برای تنظیم وضعیت (اختیاری)
        user_states_dict: دیکشنری وضعیت‌های کاربر (اختیاری)
        target_state: وضعیت هدف برای تنظیم (اختیاری)
    """
    # تنظیم منو
    menu_obj.setup_menu()
    
    # ایجاد کیبورد
    keyboard_markup = menu_obj.create_keyboard_markup()
    
    # تنظیم وضعیت کاربر اگر اطلاعات داده شده باشد
    if user_id is not None and user_states_dict is not None and target_state is not None:
        user_states_dict[user_id] = target_state
    
    # ارسال پیام منو
    await context.bot.send_message(
        chat_id=chat_id,
        text=menu_obj.message,
        reply_markup=keyboard_markup
    ) 