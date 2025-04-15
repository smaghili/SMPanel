#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes
from abc import ABC, abstractmethod
import asyncio

class BaseMenu(ABC):
    """Base class for all menus"""
    
    def __init__(self):
        """Initialize base menu"""
        self._keyboard = []
        self._message = ""
    
    @property
    def keyboard(self):
        """Get menu keyboard"""
        return self._keyboard
    
    @property
    def message(self):
        """Get menu message"""
        return self._message
    
    @abstractmethod
    def setup_menu(self):
        """Setup menu keyboard and message"""
        pass
    
    def create_keyboard_markup(self):
        """Create keyboard markup"""
        return ReplyKeyboardMarkup(
            self.keyboard,
            resize_keyboard=True,
            one_time_keyboard=False
        )
    
    async def show(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show menu to user"""
        self.setup_menu()
        
        # اگر این منو قبلاً در این پیام نمایش داده شده، آن را مجدداً نمایش نده
        menu_marker_key = f"showing_menu_{self.__class__.__name__}"
        if context.user_data.get(menu_marker_key, False):
            # منو قبلاً نمایش داده شده، از ارسال مجدد جلوگیری می‌کنیم
            return
        
        # علامت‌گذاری که این منو در حال نمایش است
        context.user_data[menu_marker_key] = True
        
        # Create keyboard markup
        keyboard_markup = self.create_keyboard_markup()
        
        # Check if message is empty
        if not self.message or self.message.strip() == "":
            # If message is empty, just update the keyboard without sending a new message
            await update.message.reply_text(
                text=" ",  # یک فاصله خالی برای جلوگیری از خطا
                reply_markup=keyboard_markup
            )
        else:
            # Normal case: send message with keyboard
            await update.message.reply_text(
                text=self.message,
                reply_markup=keyboard_markup
            )
        
        # با تاخیر کوتاه، علامت نمایش منو را پاک می‌کنیم
        async def reset_menu_flag():
            await asyncio.sleep(1)
            if menu_marker_key in context.user_data:
                del context.user_data[menu_marker_key]
        
        # ایجاد وظیفه برای پاکسازی علامت‌ها بعد از یک ثانیه
        asyncio.create_task(reset_menu_flag())
    
    async def show_with_chat_id(self, chat_id, context: ContextTypes.DEFAULT_TYPE, user_id=None, user_states_dict=None, target_state=None):
        """
        نمایش منو با استفاده از chat_id
        
        مناسب برای حالت‌هایی که نیاز به نمایش منو بدون update داریم
        
        Args:
            chat_id: شناسه چت برای ارسال منو
            context: شیء Context تلگرام
            user_id: شناسه کاربر برای تنظیم وضعیت (اختیاری)
            user_states_dict: دیکشنری وضعیت‌های کاربر (اختیاری)
            target_state: وضعیت هدف برای تنظیم (اختیاری)
        """
        # تنظیم منو
        self.setup_menu()
        
        # ایجاد کیبورد
        keyboard_markup = self.create_keyboard_markup()
        
        # تنظیم وضعیت کاربر اگر اطلاعات داده شده باشد
        if user_id is not None and user_states_dict is not None and target_state is not None:
            user_states_dict[user_id] = target_state
        
        # ارسال پیام منو
        await context.bot.send_message(
            chat_id=chat_id,
            text=self.message,
            reply_markup=keyboard_markup
        )
    
    def create_button(self, text: str) -> KeyboardButton:
        """Create a keyboard button"""
        return KeyboardButton(text) 