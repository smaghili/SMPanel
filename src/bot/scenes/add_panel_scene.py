#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters
)
import logging

from src.services.panel import PanelService
from src.bot.menus.add_panel_menu import AddPanelMenu
from src.bot.menus.admin_menu import AdminMenu

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Conversation states
(PANEL_NAME, PANEL_TYPE, PANEL_URL, PANEL_USERNAME, PANEL_PASSWORD) = range(5)

class AddPanelScene:
    """Scene for adding a new panel"""
    
    def __init__(self):
        self.panel_service = PanelService()
        self.add_panel_menu = AddPanelMenu()
        self.admin_menu = AdminMenu()
    
    def get_handler(self):
        """Get the conversation handler for this scene"""
        return ConversationHandler(
            entry_points=[],  # This will be set by the caller
            states={
                PANEL_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.panel_name)],
                PANEL_TYPE: [CallbackQueryHandler(self.panel_type)],
                PANEL_URL: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.panel_url)],
                PANEL_USERNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.panel_username)],
                PANEL_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.panel_password)],
            },
            fallbacks=[CommandHandler("cancel", self.cancel)],
        )
    
    async def start_scene(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start the scene"""
        # Show menu with only back button
        await self.add_panel_menu.show(update, context)
        
        # Check if this was triggered by a callback or message
        if update.callback_query:
            await update.callback_query.message.edit_text(
                "برای اضافه کردن پنل به ربات ابتدا یک نام برای پنل خود ارسال کنید\n\n"
                "⚠️ توجه: نام پنل نامی است که در هنگام انجام عملیات جستجو نشان داده می شود."
            )
        else:
            await update.message.reply_text(
                "برای اضافه کردن پنل به ربات ابتدا یک نام برای پنل خود ارسال کنید\n\n"
                "⚠️ توجه: نام پنل نامی است که در هنگام انجام عملیات جستجو نشان داده می شود."
            )
        return PANEL_NAME
    
    async def panel_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle panel name entry"""
        panel_name = update.message.text
        
        # Check if user is trying to go back
        if panel_name == "🔙 بازگشت به بخش مدیریت":
            context.user_data['in_conversation'] = False
            await self.admin_menu.show(update, context)
            return ConversationHandler.END
            
        context.user_data['panel_name'] = panel_name
        
        # Create inline keyboard for panel type selection
        keyboard = [
            [InlineKeyboardButton("پنل 3x-ui", callback_data="panel_type_3x-ui")],
            [InlineKeyboardButton("پنل مرزبان", callback_data="panel_type_marzban")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "🔧 لطفاً نوع پنل را انتخاب کنید:",
            reply_markup=reply_markup
        )
        
        return PANEL_TYPE
    
    async def panel_type(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle panel type selection"""
        query = update.callback_query
        await query.answer()
        
        callback_data = query.data
        panel_type = callback_data.replace("panel_type_", "")
        
        # Save panel type
        context.user_data['panel_type'] = panel_type
        
        # Display message based on panel type
        if panel_type == '3x-ui':
            await query.edit_message_text(
                f"🔧 نوع پنل انتخاب شده: {panel_type}\n\n"
                f"🔗 حالا آدرس پنل خود را ارسال کنید.\n"
                f"⚠️ توجه:\n"
                f"🔹 در صورتی که پورت پنل 443 است، پورت را نباید وارد کنید. (گاهی حتما با پورت باید وارد کنید)\n"
                f"🔸 آخر آدرس نباید / داشته باشد.\n"
                f"🔹 در صورت وارد کردن آیپی، حتما http یا https باید داشته باشد."
            )
        else:
            await query.edit_message_text(
                f"🔧 نوع پنل انتخاب شده: {panel_type}\n\n"
                f"🔗 حالا آدرس پنل خود را ارسال کنید.\n"
                f"⚠️ توجه:\n"
                f"🔸 آدرس پنل باید بدون dashboard ارسال شود.\n"
                f"🔹 در صورتی که پورت پنل 443 است، پورت را نباید وارد کنید. (گاهی حتما با پورت باید وارد کنید)\n"
                f"🔸 آخر آدرس نباید / داشته باشد.\n"
                f"🔹 در صورت وارد کردن آیپی، حتما http یا https باید داشته باشد."
            )
        
        return PANEL_URL
    
    async def panel_url(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle panel URL entry"""
        panel_url = update.message.text
        
        # Check if user is trying to go back
        if panel_url == "🔙 بازگشت به بخش مدیریت":
            context.user_data['in_conversation'] = False
            await self.admin_menu.show(update, context)
            return ConversationHandler.END
            
        context.user_data['panel_url'] = panel_url
        
        await update.message.reply_text(
            "👤 آدرس پنل ذخیره شد. حالا نام کاربری را ارسال کنید."
        )
        
        return PANEL_USERNAME
    
    async def panel_username(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle panel username entry"""
        panel_username = update.message.text
        
        # Check if user is trying to go back
        if panel_username == "🔙 بازگشت به بخش مدیریت":
            context.user_data['in_conversation'] = False
            await self.admin_menu.show(update, context)
            return ConversationHandler.END
            
        context.user_data['panel_username'] = panel_username
        
        await update.message.reply_text(
            "🔑 نام کاربری ذخیره شد. حالا رمز عبور پنل خود را وارد نمایید."
        )
        
        return PANEL_PASSWORD
    
    async def panel_password(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle panel password entry"""
        panel_password = update.message.text
        
        # Check if user is trying to go back
        if panel_password == "🔙 بازگشت به بخش مدیریت":
            context.user_data['in_conversation'] = False
            await self.admin_menu.show(update, context)
            return ConversationHandler.END
            
        context.user_data['panel_password'] = panel_password
        
        # Show typing status to indicate processing
        await update.message.chat.send_action(action="typing")
        
        # First check if panel is accessible and login works
        await update.message.reply_text("🔄 در حال بررسی اتصال به پنل...")
        
        try:
            # Create a temporary panel object without saving to database
            panel_data = {
                'id': -1,  # Temporary ID
                'name': context.user_data['panel_name'],
                'url': context.user_data['panel_url'],
                'username': context.user_data['panel_username'],
                'password': context.user_data['panel_password'],
                'panel_type': context.user_data['panel_type']
            }
            
            # Send request to panel to check if login works
            url = panel_data['url']
            # Ensure URL has http:// or https:// prefix
            if not url.startswith(('http://', 'https://')):
                url = 'http://' + url
                
            # Append /login path if it doesn't have it and it's a 3x-ui panel
            if panel_data['panel_type'] == '3x-ui':
                if not url.endswith('/login'):
                    url = url.rstrip('/') + '/login'
                    
                # Prepare login payload
                payload = {
                    'username': panel_data['username'],
                    'password': panel_data['password']
                }
                
                # Send POST request to panel login URL
                import requests
                from requests.exceptions import RequestException
                import json
                
                try:
                    response = requests.post(url, data=payload, timeout=10)
                    
                    if response.status_code == 200:
                        try:
                            result = response.json()
                            if 'success' in result and result['success'] is True:
                                # Login successful, add panel to database
                                panel_id = self.panel_service.add_panel(
                                    panel_data['name'],
                                    panel_data['url'],
                                    panel_data['username'],
                                    panel_data['password'],
                                    panel_data['panel_type']
                                )
                                
                                await update.message.reply_text(
                                    f"✅ پنل با موفقیت به ربات اضافه شد.\n"
                                    f"🆔 شناسه پنل: {panel_id}\n"
                                    f"📝 نام پنل: {panel_data['name']}\n"
                                    f"🔧 نوع پنل: {panel_data['panel_type']}\n"
                                    f"🔗 آدرس پنل: {panel_data['url']}"
                                )
                                
                                # Reset conversation flag
                                context.user_data['in_conversation'] = False
                                
                                # Return to admin menu
                                await self.admin_menu.show(update, context)
                                return ConversationHandler.END
                            else:
                                await update.message.reply_text(
                                    "❌ نام کاربری یا رمز عبور اشتباه است."
                                )
                                # Ask for password again
                                return PANEL_PASSWORD
                        except json.JSONDecodeError:
                            # Response is not JSON, try to check if it's a redirection to dashboard
                            await update.message.reply_text(
                                "⚠️ پاسخ پنل قابل تشخیص نیست.\n"
                                "لطفاً آدرس پنل را بررسی کنید و دوباره تلاش کنید."
                            )
                            # Go back to URL step
                            return PANEL_URL
                    elif response.status_code == 401:
                        await update.message.reply_text(
                            "❌ نام کاربری یا رمز عبور اشتباه است."
                        )
                        # Ask for password again
                        return PANEL_PASSWORD
                    else:
                        await update.message.reply_text(
                            f"❌ خطا در اتصال به پنل. کد خطا: {response.status_code}\n"
                            f"لطفاً آدرس پنل را بررسی کنید و دوباره تلاش کنید."
                        )
                        # Go back to URL step
                        return PANEL_URL
                except RequestException as e:
                    await update.message.reply_text(
                        f"❌ خطا در اتصال به پنل: {str(e)}\n"
                        f"لطفاً آدرس پنل را بررسی کنید و دوباره تلاش کنید."
                    )
                    # Go back to URL step
                    return PANEL_URL
            elif panel_data['panel_type'] == 'marzban':
                # For Marzban panels, we'll implement the connection check later
                # For now, just add it to the database
                panel_id = self.panel_service.add_panel(
                    panel_data['name'],
                    panel_data['url'],
                    panel_data['username'],
                    panel_data['password'],
                    panel_data['panel_type']
                )
                
                await update.message.reply_text(
                    f"✅ پنل مرزبان با موفقیت به ربات اضافه شد.\n"
                    f"🆔 شناسه پنل: {panel_id}\n"
                    f"📝 نام پنل: {panel_data['name']}\n"
                    f"🔧 نوع پنل: {panel_data['panel_type']}\n"
                    f"🔗 آدرس پنل: {panel_data['url']}\n\n"
                    f"⚠️ توجه: پشتیبانی کامل از پنل مرزبان در حال توسعه است."
                )
                
                # Reset conversation flag
                context.user_data['in_conversation'] = False
                
                # Return to admin menu
                await self.admin_menu.show(update, context)
                return ConversationHandler.END
                
        except Exception as e:
            await update.message.reply_text(
                f"❌ خطا: {str(e)}\n"
                f"لطفاً دوباره تلاش کنید."
            )
            # Go back to start
            return await self.start_scene(update, context)
    
    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Cancel the conversation"""
        # Clean up user data
        for key in ['panel_name', 'panel_type', 'panel_url', 'panel_username', 'panel_password']:
            if key in context.user_data:
                del context.user_data[key]
        
        # Reset conversation flag
        context.user_data['in_conversation'] = False
        
        await update.message.reply_text("❌ عملیات لغو شد.")
        # Return to admin menu
        await self.admin_menu.show(update, context)
        return ConversationHandler.END 