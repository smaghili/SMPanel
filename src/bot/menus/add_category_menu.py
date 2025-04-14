#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from src.bot.menus.base_menu import BaseMenu

class AddCategoryMenu(BaseMenu):
    """Menu for add category process that only shows back button"""
    
    def setup_menu(self):
        """Setup add category menu keyboard and message"""
        self._keyboard = [
            [self.create_button("🔙 بازگشت به بخش فروشگاه")]
        ] 