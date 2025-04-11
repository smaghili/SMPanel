#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes
from abc import ABC, abstractmethod

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
        await update.message.reply_text(
            text=self.message,
            reply_markup=self.create_keyboard_markup()
        )
    
    def create_button(self, text: str) -> KeyboardButton:
        """Create a keyboard button"""
        return KeyboardButton(text) 