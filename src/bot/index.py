#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import logging
import sys
from pathlib import Path
import re

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from telegram import Update
from telegram.ext import (
    Application, 
    CommandHandler, 
    MessageHandler, 
    ContextTypes,
    ConversationHandler,
    CallbackQueryHandler,
    filters
)

from dotenv import load_dotenv

# Import modules
from src.bot.scenes.add_panel_scene import AddPanelScene
from src.bot.middlewares.admin_middleware import AdminMiddleware
from src.bot.menus.main_menu import MainMenu
from src.bot.menus.admin_menu import AdminMenu
from src.bot.menus.panel_management_menu import PanelManagementMenu

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Environment variables
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

# Initialize
add_panel_scene = AddPanelScene()
admin_middleware = AdminMiddleware()
main_menu = MainMenu()
admin_menu = AdminMenu()
panel_management_menu = PanelManagementMenu()

# Add a state tracker to determine where the user is
user_states = {}

# Conversation states (for adding panel)
(PANEL_NAME, PANEL_URL, PANEL_USERNAME, PANEL_PASSWORD) = range(4)

# Message handler for menu navigation
async def handle_menu_navigation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle menu navigation"""
    # Skip processing if we're in a conversation
    if context.user_data.get('in_conversation'):
        return
        
    message_text = update.message.text
    user_id = update.effective_user.id
    
    # Track user state
    current_state = user_states.get(user_id, "main")
    
    if message_text == "مدیریت":
        if admin_middleware.is_admin(user_id):
            # Set user state to admin menu
            user_states[user_id] = "admin"
            await admin_menu.show(update, context)
        else:
            await update.message.reply_text("⛔ شما دسترسی به این بخش را ندارید.")
    
    elif message_text == "🔙 بازگشت به منوی اصلی":
        # Always return to main menu
        user_states[user_id] = "main"
        await main_menu.show(update, context)
    
    elif message_text == "🔙 بازگشت به بخش مدیریت":
        # Return to admin menu
        user_states[user_id] = "admin"
        await admin_menu.show(update, context)
    
    elif message_text == "🖥 اضافه کردن پنل":
        if admin_middleware.is_admin(user_id):
            # Set user state to add panel
            user_states[user_id] = "add_panel"
            context.user_data['in_conversation'] = True
            return await add_panel_scene.start_scene(update, context)
    
    elif message_text == "👥 مدیریت پنل":
        if admin_middleware.is_admin(user_id):
            # Show panel management menu
            await panel_management_menu.show(update, context)
    
    elif message_text in ["📊 آمار ربات", "⚙️ تنظیمات اکانت تست", "💰 مالی", "🏪 بخش فروشگاه"]:
        await update.message.reply_text("🚧 این بخش در حال توسعه است...")

# Callback query handler
async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle callback queries from inline keyboards"""
    query = update.callback_query
    user_id = query.from_user.id
    
    # Check admin permission
    if not admin_middleware.is_admin(user_id):
        await query.answer("⛔ شما دسترسی به این بخش را ندارید.")
        return
    
    # Answer the callback query to stop loading animation
    await query.answer()
    
    # Handle different callback data
    callback_data = query.data
    
    # Handle specific callback data first - exact matches
    if callback_data == "panel_list":
        await panel_management_menu.show_panel_list(update, context)
    
    # Handle back to admin menu
    elif callback_data == "back_to_admin":
        # We can't directly call show method with a callback query,
        # so we'll show a message and prompt to use the menu again
        await query.edit_message_text(
            "برای بازگشت به منوی مدیریت، لطفاً از دکمه‌های زیر استفاده کنید."
        )
    
    # Handle pattern matches after exact matches
    # Handle panel selection
    elif callback_data.startswith("panel_"):
        panel_id = int(callback_data.split("_")[1])
        await panel_management_menu.show_panel_options(update, context, panel_id)
    
    # Handle confirmation for panel deletion
    elif callback_data.startswith("confirm_delete_"):
        panel_id = int(callback_data.split("_")[2])
        await panel_management_menu.confirm_delete_panel(update, context, panel_id)
    
    # Handle toggle panel status
    elif callback_data.startswith("toggle_panel_"):
        panel_id = int(callback_data.split("_")[2])
        await panel_management_menu.toggle_panel_status(update, context, panel_id)
    
    # Handle delete panel
    elif callback_data.startswith("delete_panel_"):
        panel_id = int(callback_data.split("_")[2])
        await panel_management_menu.delete_panel(update, context, panel_id)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command handler"""
    user_id = update.effective_user.id
    # Reset user state to main menu
    user_states[user_id] = "main"
    # Reset conversation flag
    context.user_data['in_conversation'] = False
    await main_menu.show(update, context)

def main():
    """Start the bot."""
    print("🤖 Starting SMPanel Bot initialization...")
    
    # Create the Application
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Add conversation handler for panel management - this must be first
    conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^🖥 اضافه کردن پنل$"), add_panel_scene.start_scene)],
        states={
            PANEL_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_panel_scene.panel_name)],
            PANEL_URL: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_panel_scene.panel_url)],
            PANEL_USERNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_panel_scene.panel_username)],
            PANEL_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_panel_scene.panel_password)],
        },
        fallbacks=[CommandHandler("cancel", add_panel_scene.cancel)],
        name="add_panel_conversation",
        persistent=False
    )
    application.add_handler(conv_handler)
    
    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    
    # Add callback query handler for inline buttons
    application.add_handler(CallbackQueryHandler(handle_callback_query))
    
    # Add message handler for menu navigation - this must be last
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_menu_navigation))
    
    # Start the Bot
    print("✅ Bot initialized successfully!")
    print("🚀 Starting bot polling...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main() 