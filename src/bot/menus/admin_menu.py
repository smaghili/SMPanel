#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from src.bot.menus.base_menu import BaseMenu

class AdminMenu(BaseMenu):
    """Admin menu implementation"""
    
    def setup_menu(self):
        """Setup admin menu keyboard and message"""
        self._message = "👨‍🔧 بخش مدیریت:\nلطفا یکی از گزینه های زیر را انتخاب کنید:"
        self._keyboard = [
            [self.create_button("📊 آمار ربات")],
            [self.create_button("👥 مدیریت پنل"), self.create_button("🖥 اضافه کردن پنل")],
            [self.create_button("⚙️ تنظیمات اکانت تست")],
            [self.create_button("💰 مالی"), self.create_button("🏪 بخش فروشگاه")],
            [self.create_button("🔙 بازگشت به منوی اصلی")]
        ] 