#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from src.bot.menus.base_menu import BaseMenu

class AddPanelMenu(BaseMenu):
    """Menu for add panel process that only shows back button"""
    
    def setup_menu(self):
        """Setup add panel menu keyboard and message"""
        self._message = "در حال افزودن پنل جدید..."
        self._keyboard = [
            [self.create_button("🔙 بازگشت به بخش مدیریت")]
        ] 