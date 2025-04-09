#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from src.bot.commands.base_command import BaseCommand

class StartCommand(BaseCommand):
    """Handle /start command"""
    
    def __init__(self):
        super().__init__()
        self.admin_id = int(os.getenv('ADMIN_TELEGRAM_ID'))
    
    def is_admin(self, user_id):
        """Check if user is admin"""
        return user_id == self.admin_id
    
    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user = update.effective_user
        
        # Create keyboard with appropriate buttons
        if self.is_admin(user.id):
            keyboard = [
                [InlineKeyboardButton("👨‍🔧 بخش ادمین", callback_data="admin_panel")]
            ]
        else:
            keyboard = []
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"👋 سلام {user.first_name}!\n"
            f"به ربات مدیریت پنل های SMPanel خوش آمدید.\n\n"
            f"با استفاده از این ربات می‌توانید پنل‌های VPN خود را مدیریت کنید.",
            reply_markup=reply_markup
        ) 