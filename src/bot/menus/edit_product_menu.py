#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from src.bot.menus.base_menu import BaseMenu

class EditProductMenu(BaseMenu):
    """Menu for edit product process"""
    
    def setup_menu(self):
        """Setup edit product menu keyboard and message"""
        self._message = "در حال ویرایش محصول..."
        self._keyboard = [
            [self.create_button("🔙 بازگشت به بخش فروشگاه")]
        ]
        
    def setup_edit_options_menu(self, product_name):
        """Setup edit options menu keyboard and message"""
        self._message = f"🖊️ ویرایش محصول: {product_name}\n\nلطفاً بخش مورد نظر برای ویرایش را انتخاب کنید:"
        self._keyboard = [
            [self.create_button("زمان"), self.create_button("حجم"), self.create_button("قیمت")],
            [self.create_button("دسته بندی"), self.create_button("نام محصول")],
            [self.create_button("🔙 بازگشت به منوی مدیریت")]
        ]
