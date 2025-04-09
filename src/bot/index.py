#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, 
    CommandHandler, 
    MessageHandler, 
    CallbackQueryHandler,
    ContextTypes,
    ConversationHandler,
    filters
)

from dotenv import load_dotenv

# Import modules
from src.bot.commands.start_command import StartCommand
from src.bot.scenes.add_panel_scene import AddPanelScene
from src.bot.middlewares.admin_middleware import AdminMiddleware

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
start_command = StartCommand()
add_panel_scene = AddPanelScene()
admin_middleware = AdminMiddleware()

# Conversation states (for adding panel)
(PANEL_NAME, PANEL_URL, PANEL_USERNAME, PANEL_PASSWORD) = range(4)

# Callback query handler
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle callbacks from inline keyboard buttons."""
    query = update.callback_query
    await query.answer()
    
    if query.data == "admin_panel":
        if admin_middleware.is_admin(query.from_user.id):
            keyboard = [
                [InlineKeyboardButton("🖥 اضافه کردن پنل", callback_data="add_panel")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.message.edit_text(
                "👨‍🔧 بخش مدیریت:\n"
                "لطفا یکی از گزینه های زیر را انتخاب کنید:",
                reply_markup=reply_markup
            )
        else:
            await query.message.edit_text("⛔ شما دسترسی به این بخش را ندارید.")
    
    elif query.data == "add_panel":
        if admin_middleware.is_admin(query.from_user.id):
            return await add_panel_scene.start_scene(update, context)
    
    return ConversationHandler.END

def main():
    """Start the bot."""
    print("🤖 Starting SMPanel Bot initialization...")
    
    # Create the Application
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Add command handlers
    application.add_handler(CommandHandler("start", start_command.handle))
    
    # Add callback query handler for main menu
    application.add_handler(
        CallbackQueryHandler(button_callback, pattern="^(admin_panel)$")
    )
    
    # Add conversation handler for panel management
    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(button_callback, pattern="^add_panel$")],
        states={
            PANEL_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_panel_scene.panel_name)],
            PANEL_URL: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_panel_scene.panel_url)],
            PANEL_USERNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_panel_scene.panel_username)],
            PANEL_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_panel_scene.panel_password)],
        },
        fallbacks=[CommandHandler("cancel", add_panel_scene.cancel)],
    )
    application.add_handler(conv_handler)
    
    # Start the Bot
    print("✅ Bot initialized successfully!")
    print("🚀 Starting bot polling...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main() 