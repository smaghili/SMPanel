#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import logging
import sys
from pathlib import Path
import re
import traceback
import datetime
import asyncio

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

# Import edit product scene states
from src.bot.scenes.edit_product_scene import (
    SELECT_CATEGORY as EDIT_PRODUCT_SELECT_CATEGORY,
    SELECT_PRODUCT,
    EDIT_OPTIONS,
    EDIT_NAME,
    EDIT_CATEGORY,
    EDIT_DATA_LIMIT,
    EDIT_DURATION,
    EDIT_PRICE,
    CONFIRMATION as EDIT_PRODUCT_CONFIRMATION
)

# Import modules
from src.bot.scenes.add_panel_scene import AddPanelScene
from src.bot.scenes.add_category_scene import AddCategoryScene
from src.bot.scenes.add_product_scene import AddProductScene
from src.bot.scenes.delete_category_scene import DeleteCategoryScene
from src.bot.scenes.delete_product_scene import DeleteProductScene
from src.bot.scenes.edit_product_scene import EditProductScene
from src.bot.middlewares.admin_middleware import AdminMiddleware
from src.bot.menus.main_menu import MainMenu
from src.bot.menus.admin_menu import AdminMenu
from src.bot.menus.panel_management_menu import PanelManagementMenu
from src.bot.menus.shop_menu import ShopMenu
from src.bot.utils.navigation_helpers import handle_back_to_menu

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
edit_product_scene = EditProductScene()
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
        message_text = update.message.text
        user_id = update.effective_user.id
        
        # بررسی دکمه "بازگشت به منوی مدیریت" در حالت shop به صورت ویژه
        if message_text == "🔙 بازگشت به منوی مدیریت":
            current_state = user_states.get(user_id, "main")
            if current_state == "shop":
                logger.info(f"Handling back to admin menu from shop menu")
                user_states[user_id] = "admin"
                await admin_menu.show(update, context)
                return
        
        # Skip back commands in other contexts
        if message_text in ["🔙 بازگشت به منوی اصلی", "🔙 بازگشت به بخش مدیریت"]:
            logger.debug(f"Skipping back command '{message_text}' in handle_menu_navigation")
            return
        
        # پشتیبانی از 'بازگشت به بخش فروشگاه'
        elif message_text == "🔙 بازگشت به بخش فروشگاه":
            # این دکمه احتمالاً اشتباه است و باید به منوی فروشگاه برگردد
            logger.info(f"Handling back to shop menu from message '{message_text}'")
            user_states[user_id] = "shop"
            await shop_menu.show(update, context)
            return
            
        # Skip other processing if we're in a conversation
        if context.user_data.get('in_conversation'):
            logger.debug(f"User is in conversation, skipping other menu navigation")
            return
        
        # Track user state
        current_state = user_states.get(user_id, "main")
        logger.info(f"User {user_id} in state '{current_state}' sent message: '{message_text}' (hex: {message_text.encode('utf-8').hex()})")
        
        # پیام‌هایی که توسط ConversationHandler پردازش می‌شوند را رد کن
        conversation_handled_messages = [
            "🖥 اضافه کردن پنل",
            "🛒 اضافه کردن دسته بندی",
            "🛍️ اضافه کردن محصول",
            "❌ حذف دسته بندی",
            "❌ حذف محصول"
        ]
        
        if message_text in conversation_handled_messages:
            logger.debug(f"Message '{message_text}' will be handled by a ConversationHandler, skipping")
            return
        
        if message_text == "مدیریت":
            if admin_middleware.is_admin(user_id):
                # Set user state to admin menu
                user_states[user_id] = "admin"
                await admin_menu.show(update, context)
            else:
                await update.message.reply_text("⛔ شما دسترسی به این بخش را ندارید.")
        
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
            
            # These menu items have dedicated ConversationHandlers with higher priority
            # Skip them here to avoid processing them twice
            # The duplication happens because the handler with higher priority (ConversationHandler)
            # processes the message, but then it also reaches this handler
            conversation_handled_options = [
                "❌ حذف محصول",
                "🛍️ اضافه کردن محصول",
                "❌ حذف دسته بندی",
                "🛒 اضافه کردن دسته بندی",
                "✏️ ویرایش محصول"
            ]
            
            if message_text in conversation_handled_options:
                # These should be handled by their respective ConversationHandlers
                # with higher priority, so we just return here
                logger.debug(f"Skipping menu item '{message_text}' that should be handled by a ConversationHandler")
                return
            
            # Handle other shop menu options
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
    
    # اگر کاربر در یک مکالمه است (مثلاً افزودن دسته‌بندی)، پردازش نکن
    # ConversationHandler باید اول پردازش کند
    if context.user_data.get('in_conversation', False):
        logger.info(f"Skipping handle_callback_query for user {user_id} because they are in a conversation")
        await query.answer()
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
    
    # پشتیبانی از panel_type
    elif callback_data.startswith("panel_type_"):
        # مستقیم به add_panel_scene ارجاع دهیم تا توسط کد اصلی آن پردازش شود
        try:
            return await add_panel_scene.panel_type(update, context)
        except Exception as e:
            logger.error(f"Error handling panel_type: {e}")
            await query.edit_message_text("❌ خطایی در پردازش نوع پنل رخ داد. لطفاً دوباره تلاش کنید.")
    
    # Handle pattern matches after exact matches
    # Handle panel selection
    elif callback_data.startswith("panel_") and len(callback_data.split("_")) >= 2 and callback_data.split("_")[1].isdigit():
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

async def handle_back_to_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle back to admin menu request in conversations"""
    return await handle_back_to_menu(
        update=update,
        context=context,
        menu_callback=admin_menu.show,
        menu_name="admin",
        target_state="admin",
        user_states_dict=user_states
    )

async def handle_back_to_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle back to main menu request in conversations"""
    return await handle_back_to_menu(
        update=update,
        context=context,
        menu_callback=main_menu.show,
        menu_name="main",
        target_state="main",
        user_states_dict=user_states
    )

async def conversation_timeout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle conversation timeout"""
    logger.info("Conversation timed out")
    context.user_data['in_conversation'] = False
    return ConversationHandler.END

async def conversation_stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle conversation stop"""
    logger.info("Conversation stopped")
    context.user_data['in_conversation'] = False
    return ConversationHandler.END

async def send_admin_notification(application):
    """Send notification to admin users when bot starts"""
    # You can get admin user IDs from a config file or database
    # Here we're using a hard-coded admin ID for simplicity
    admin_ids = []
    
    # Get admin IDs from middleware
    try:
        admins = AdminMiddleware().get_admin_list()
        admin_ids = admins
    except Exception as e:
        logger.error(f"Error getting admin IDs: {e}")
    
    # Fallback if no admins found
    if not admin_ids:
        logger.warning("No admin IDs found, notification won't be sent")
        return
    
    try:
        # Send notification to all admins
        bot_info = await application.bot.get_me()
        bot_username = bot_info.username
        message = (
            f"✅ Bot @{bot_username} started successfully!\n"
            f"Mode: {'Webhook' if os.getenv('WEBHOOK_URL') else 'Polling'}\n"
            f"Time: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        
        for admin_id in admin_ids:
            try:
                await application.bot.send_message(chat_id=admin_id, text=message)
                logger.info(f"Start notification sent to admin {admin_id}")
            except Exception as e:
                logger.error(f"Failed to send notification to admin {admin_id}: {e}")
    except Exception as e:
        logger.error(f"Error sending admin notifications: {e}")

def main():
    """Start the bot."""
    print("🤖 Starting SMPanel Bot initialization...")
    
    # Create the Application
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    
    # *** FIRST PRIORITY HANDLERS ***
    # Add special message handlers for back buttons - HIGHEST PRIORITY
    # استفاده از فیلترهای دقیق‌تر برای جلوگیری از چندین بار پردازش یک پیام
    back_to_main_filter = filters.Regex("^🔙 بازگشت به منوی اصلی$") & ~filters.UpdateType.EDITED_MESSAGE
    back_to_admin_filter = filters.Regex("^🔙 بازگشت به منوی مدیریت$") & ~filters.UpdateType.EDITED_MESSAGE
    
    # تعداد handler های اضافی را کاهش می‌دهیم
    application.add_handler(MessageHandler(back_to_main_filter, handle_back_to_main, block=True), group=0)
    application.add_handler(MessageHandler(back_to_admin_filter, handle_back_to_admin, block=True), group=0)
    
    # *** SECOND PRIORITY HANDLERS ***
    # Add conversation handlers
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
    application.add_handler(add_panel_conv_handler, group=1)
    
    # Add conversation handler for category management
    add_category_conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^🛒 اضافه کردن دسته بندی$"), add_category_scene.start_scene)],
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
    application.add_handler(add_category_conv_handler, group=1)
    
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
    application.add_handler(add_product_conv_handler, group=1)
    
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
    application.add_handler(delete_category_conv_handler, group=1)
    
    # Add conversation handler for delete product
    delete_product_conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^❌ حذف محصول$"), delete_product_scene.start_scene)],
        states={
            SHOW_PRODUCTS: [CallbackQueryHandler(delete_product_scene.handle_selection)],
            PRODUCT_CONFIRM_DELETE: [CallbackQueryHandler(delete_product_scene.handle_confirmation)],
        },
        fallbacks=[CommandHandler("cancel", delete_product_scene.cancel)],
        name="delete_product_conversation",
        conversation_timeout=300,  # 5 minute timeout
        persistent=False
    )
    logger.info("Registering delete_product_conv_handler")
    application.add_handler(delete_product_conv_handler, group=1)
    
    # Add conversation handler for edit product
    edit_product_conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^✏️ ویرایش محصول$"), edit_product_scene.start_scene)],
        states={
            EDIT_PRODUCT_SELECT_CATEGORY: [CallbackQueryHandler(edit_product_scene.select_category)],
            SELECT_PRODUCT: [CallbackQueryHandler(edit_product_scene.select_product)],
            EDIT_OPTIONS: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_product_scene.handle_edit_options)],
            EDIT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_product_scene.edit_name)],
            EDIT_CATEGORY: [CallbackQueryHandler(edit_product_scene.edit_category)],
            EDIT_DATA_LIMIT: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_product_scene.edit_data_limit)],
            EDIT_DURATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_product_scene.edit_duration)],
            EDIT_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_product_scene.edit_price)],
        },
        fallbacks=[CommandHandler("cancel", edit_product_scene.cancel)],
        name="edit_product_conversation",
        conversation_timeout=300,  # 5 minute timeout
        persistent=False
    )
    logger.info("Registering edit_product_conv_handler")
    application.add_handler(edit_product_conv_handler, group=1)
    
    # *** THIRD PRIORITY HANDLERS ***
    # Add callback query handler for inline buttons
    application.add_handler(CallbackQueryHandler(handle_callback_query), group=2)
    
    # *** LOWEST PRIORITY HANDLER ***
    # Add message handler for menu navigation - this must be last
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_menu_navigation), group=3)
    
    # Register error handler
    application.add_error_handler(error_handler)
    
    # Start the Bot
    print("✅ Bot initialized successfully!")
    
    # Get webhook info from environment
    WEBHOOK_URL = os.getenv('WEBHOOK_URL')
    WEBHOOK_PATH = os.getenv('WEBHOOK_PATH', '/webhook')
    SERVER_PORT = int(os.getenv('SERVER_PORT', '8443'))
    
    # Run as a synchronous function so the event loop works properly
    async def start_webhook_async():
        # Send admin notification
        await send_admin_notification(application)
        
        # Start the webhook
        await application.initialize()
        await application.start()
        await application.updater.start_webhook(
            listen="0.0.0.0",
            port=SERVER_PORT,
            url_path=f"{WEBHOOK_PATH}/{TELEGRAM_BOT_TOKEN}",
            webhook_url=f"{WEBHOOK_URL}{WEBHOOK_PATH}/{TELEGRAM_BOT_TOKEN}",
            drop_pending_updates=True,
            allowed_updates=Update.ALL_TYPES
        )
        
        # Keep the application running - اصلاح روش نگه داشتن اپلیکیشن
        while True:
            # اجازه دهیم اپلیکیشن به کار خود ادامه دهد
            await asyncio.sleep(3600)  # انتظار 1 ساعت - این فقط برای نگه داشتن برنامه است
    
    async def start_polling_async():
        # Send admin notification
        await send_admin_notification(application)
        
        # Start polling
        await application.initialize()
        await application.start()
        await application.updater.start_polling(allowed_updates=Update.ALL_TYPES)
        
        # Keep the application running - اصلاح روش نگه داشتن اپلیکیشن
        while True:
            # اجازه دهیم اپلیکیشن به کار خود ادامه دهد
            await asyncio.sleep(3600)  # انتظار 1 ساعت - این فقط برای نگه داشتن برنامه است
    
    if WEBHOOK_URL:
        # Start in webhook mode
        print(f"🚀 Starting bot with webhook at {WEBHOOK_URL}{WEBHOOK_PATH}/{TELEGRAM_BOT_TOKEN}")
        asyncio.run(start_webhook_async())
    else:
        # Fallback to polling mode
        print("🚀 Starting bot in polling mode...")
        asyncio.run(start_polling_async())

if __name__ == "__main__":
    main() 