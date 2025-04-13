#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import logging
import sys
from pathlib import Path
import re
import traceback

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

# Define states at module level to make them available for import
# These need to match the values in add_category_scene.py
ADD_CATEGORY_NAME, ADD_SELECT_PANELS, ADD_SELECT_INBOUNDS, ADD_CONFIRMATION = range(4)

# Import product scene states
from src.bot.scenes.add_product_scene import (
    PRODUCT_NAME, 
    SELECT_CATEGORY, 
    DATA_LIMIT, 
    DURATION, 
    PRICE, 
    CONFIRMATION as PRODUCT_CONFIRMATION
)

# Import delete scene states
from src.bot.scenes.delete_category_scene import (
    SHOW_CATEGORIES,
    CONFIRM_DELETE as CATEGORY_CONFIRM_DELETE
)

from src.bot.scenes.delete_product_scene import (
    SHOW_PRODUCTS,
    CONFIRM_DELETE as PRODUCT_CONFIRM_DELETE
)

# Import modules
from src.bot.scenes.add_panel_scene import AddPanelScene
from src.bot.scenes.add_category_scene import AddCategoryScene
from src.bot.scenes.add_product_scene import AddProductScene
from src.bot.scenes.delete_category_scene import DeleteCategoryScene
from src.bot.scenes.delete_product_scene import DeleteProductScene
from src.bot.middlewares.admin_middleware import AdminMiddleware
from src.bot.menus.main_menu import MainMenu
from src.bot.menus.admin_menu import AdminMenu
from src.bot.menus.panel_management_menu import PanelManagementMenu
from src.bot.menus.shop_menu import ShopMenu

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Environment variables
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

# Initialize
add_panel_scene = AddPanelScene()
add_category_scene = AddCategoryScene()
add_product_scene = AddProductScene()
delete_category_scene = DeleteCategoryScene()
delete_product_scene = DeleteProductScene()
admin_middleware = AdminMiddleware()
main_menu = MainMenu()
admin_menu = AdminMenu()
panel_management_menu = PanelManagementMenu()
shop_menu = ShopMenu()

# Add a state tracker to determine where the user is
user_states = {}

# Conversation states (for adding panel)
(PANEL_NAME, PANEL_TYPE, PANEL_URL, PANEL_USERNAME, PANEL_PASSWORD) = range(5)

# Message handler for menu navigation
async def handle_menu_navigation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle menu navigation"""
    try:
        # Skip processing if we're in a conversation
        if context.user_data.get('in_conversation'):
            logger.debug(f"User is in conversation, skipping menu navigation")
            return
            
        message_text = update.message.text
        user_id = update.effective_user.id
        
        # Track user state
        current_state = user_states.get(user_id, "main")
        logger.info(f"User {user_id} in state '{current_state}' sent message: '{message_text}' (hex: {message_text.encode('utf-8').hex()})")
        
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
        
        elif message_text == "🏪 بخش فروشگاه":
            if admin_middleware.is_admin(user_id):
                # Set user state to shop menu
                user_states[user_id] = "shop"
                await shop_menu.show(update, context)
        
        # Shop menu navigation
        elif current_state == "shop":
            logger.info(f"Handling shop menu option: {message_text}")
            if message_text == "🛍️ اضافه کردن محصول":
                await shop_menu.add_product(update, context)
            elif message_text == "❌ حذف محصول":
                await shop_menu.delete_product(update, context)
            elif message_text == "❌ حذف دسته بندی":
                await shop_menu.delete_category(update, context)
            elif message_text == "✏️ ویرایش محصول":
                await shop_menu.edit_product(update, context)
            elif message_text == "➕ تنظیم قیمت حجم اضافه":
                await shop_menu.set_volume_price(update, context)
            elif message_text == "🎁 ساخت کد هدیه":
                await shop_menu.create_gift_code(update, context)
            elif message_text == "❌ حذف کد هدیه":
                await shop_menu.delete_gift_code(update, context)
            elif message_text == "🏷️ ساخت کد تخفیف":
                await shop_menu.create_discount_code(update, context)
            elif message_text == "❌ حذف کد تخفیف":
                await shop_menu.delete_discount_code(update, context)
        
        elif message_text in ["📊 آمار ربات", "⚙️ تنظیمات اکانت تست", "💰 مالی"]:
            await update.message.reply_text("🚧 این بخش در حال توسعه است...")
    except Exception as e:
        logger.error(f"Error in handle_menu_navigation: {e}")
        logger.error(traceback.format_exc())
        await update.message.reply_text("❌ خطایی رخ داده است. لطفاً دوباره تلاش کنید.")

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
    logger.info(f"User {user_id} clicked inline button: {callback_data}")
    
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

async def error_handler(update, context):
    """Log errors caused by Updates."""
    logger.error(f"Update {update} caused error {context.error}")
    logger.error(traceback.format_exc())
    
    # Inform user
    if update and update.effective_message:
        await update.effective_message.reply_text("❌ خطایی رخ داده است. لطفاً دوباره تلاش کنید.")

def main():
    """Start the bot."""
    print("🤖 Starting SMPanel Bot initialization...")
    
    # Create the Application
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Add conversation handler for panel management - this must be first
    add_panel_conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^🖥 اضافه کردن پنل$"), add_panel_scene.start_scene)],
        states={
            PANEL_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_panel_scene.panel_name)],
            PANEL_TYPE: [CallbackQueryHandler(add_panel_scene.panel_type)],
            PANEL_URL: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_panel_scene.panel_url)],
            PANEL_USERNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_panel_scene.panel_username)],
            PANEL_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_panel_scene.panel_password)],
        },
        fallbacks=[CommandHandler("cancel", add_panel_scene.cancel)],
        name="add_panel_conversation",
        persistent=False
    )
    application.add_handler(add_panel_conv_handler)
    
    # Add conversation handler for category management
    add_category_conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^.+اضافه کردن دسته بندی$"), add_category_scene.start_scene)],
        states={
            ADD_CATEGORY_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_category_scene.category_name)],
            ADD_SELECT_PANELS: [CallbackQueryHandler(add_category_scene.select_panels)],
            ADD_SELECT_INBOUNDS: [CallbackQueryHandler(add_category_scene.select_inbounds)],
            ADD_CONFIRMATION: [CallbackQueryHandler(add_category_scene.confirmation)],
        },
        fallbacks=[CommandHandler("cancel", add_category_scene.cancel)],
        name="add_category_conversation",
        persistent=False
    )
    logger.info("Registering add_category_conv_handler with states: %s", add_category_conv_handler.states)
    application.add_handler(add_category_conv_handler)
    
    # Add conversation handler for product management
    add_product_conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^🛍️ اضافه کردن محصول$"), add_product_scene.start_scene)],
        states={
            PRODUCT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_product_scene.product_name)],
            SELECT_CATEGORY: [CallbackQueryHandler(add_product_scene.select_category)],
            DATA_LIMIT: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_product_scene.data_limit)],
            DURATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_product_scene.duration)],
            PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_product_scene.price)],
            PRODUCT_CONFIRMATION: [CallbackQueryHandler(add_product_scene.confirmation)],
        },
        fallbacks=[CommandHandler("cancel", add_product_scene.cancel)],
        name="add_product_conversation",
        persistent=False
    )
    logger.info("Registering add_product_conv_handler")
    application.add_handler(add_product_conv_handler)
    
    # Add conversation handler for delete category
    delete_category_conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^❌ حذف دسته بندی$"), delete_category_scene.start_scene)],
        states={
            SHOW_CATEGORIES: [CallbackQueryHandler(delete_category_scene.handle_selection)],
            CATEGORY_CONFIRM_DELETE: [CallbackQueryHandler(delete_category_scene.handle_confirmation)],
        },
        fallbacks=[CommandHandler("cancel", delete_category_scene.cancel)],
        name="delete_category_conversation",
        persistent=False
    )
    logger.info("Registering delete_category_conv_handler")
    application.add_handler(delete_category_conv_handler)
    
    # Add conversation handler for delete product
    delete_product_conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^❌ حذف محصول$"), delete_product_scene.start_scene)],
        states={
            SHOW_PRODUCTS: [CallbackQueryHandler(delete_product_scene.handle_selection)],
            PRODUCT_CONFIRM_DELETE: [CallbackQueryHandler(delete_product_scene.handle_confirmation)],
        },
        fallbacks=[CommandHandler("cancel", delete_product_scene.cancel)],
        name="delete_product_conversation",
        persistent=False
    )
    logger.info("Registering delete_product_conv_handler")
    application.add_handler(delete_product_conv_handler)
    
    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    
    # Add callback query handler for inline buttons
    application.add_handler(CallbackQueryHandler(handle_callback_query))
    
    # Add message handler for menu navigation - this must be last
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_menu_navigation))
    
    # Register error handler
    application.add_error_handler(error_handler)
    
    # Start the Bot
    print("✅ Bot initialized successfully!")
    print("🚀 Starting bot polling...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main() 