#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from src.bot.menus.base_menu import BaseMenu

class MainMenu(BaseMenu):
    """Main menu implementation"""
    
    def setup_menu(self):
        """Setup main menu keyboard and message"""
        self._message = "به ربات مدیریت پنل های SMPanel خوش آمدید.\nلطفا یکی از گزینه های زیر را انتخاب کنید:"
        self._keyboard = [
            [self.create_button("مدیریت")]
        ] 