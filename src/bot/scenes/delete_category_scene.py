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
import traceback

from src.services.shop_service import ShopService

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Define states
(
    SHOW_CATEGORIES,
    CONFIRM_DELETE
) = range(2)

class DeleteCategoryScene:
    """Scene for deleting categories"""
    
    def __init__(self):
        self.shop_service = ShopService()
    
    def get_handler(self):
        """Get the conversation handler for this scene"""
        return ConversationHandler(
            entry_points=[],  # This will be set by the caller
            states={
                SHOW_CATEGORIES: [CallbackQueryHandler(self.handle_selection)],
                CONFIRM_DELETE: [CallbackQueryHandler(self.handle_confirmation)],
            },
            fallbacks=[CommandHandler("cancel", self.cancel)],
        )
    
    async def start_scene(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start the scene"""
        # Initialize user data
        context.user_data['in_conversation'] = True
        context.user_data['selected_categories'] = []
        logger.info(f"Starting delete_category scene for user {update.effective_user.id}")
        
        # Get all categories
        categories = self.shop_service.get_all_categories()
        
        if not categories or len(categories) == 0:
            await update.message.reply_text("❌ هیچ دسته بندی یافت نشد.")
            context.user_data['in_conversation'] = False
            return ConversationHandler.END
        
        # Create keyboard with categories
        keyboard = self._create_categories_keyboard(categories, context.user_data['selected_categories'])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "❌ حذف دسته بندی\n\n"
            "📌 دسته بندی های مورد نظر برای حذف را انتخاب کنید:\n"
            "می‌توانید چندین دسته بندی را انتخاب کنید.",
            reply_markup=reply_markup
        )
        
        return SHOW_CATEGORIES
    
    def _create_categories_keyboard(self, categories, selected_categories):
        """Create keyboard with categories"""
        keyboard = []
        
        # Add categories
        for category in categories:
            category_id = category.get('id', 0)
            category_name = category.get('name', 'بدون نام')
            
            checkbox = "☑️" if category_id in selected_categories else "⬜️"
            keyboard.append([
                InlineKeyboardButton(f"{checkbox} {category_name}", callback_data=f"category_{category_id}")
            ])
        
        # Add control buttons
        control_buttons = []
        
        if selected_categories:
            control_buttons = [
                InlineKeyboardButton("❌ حذف موارد انتخاب شده", callback_data="delete_selected"),
                InlineKeyboardButton("🔄 پاک کردن انتخاب‌ها", callback_data="clear_selection")
            ]
        else:
            control_buttons = [
                InlineKeyboardButton("🔙 بازگشت", callback_data="back")
            ]
        
        keyboard.append(control_buttons)
        
        return keyboard
    
    async def handle_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle category selection"""
        query = update.callback_query
        await query.answer()
        
        callback_data = query.data
        
        if callback_data == "back":
            # Return to shop menu
            context.user_data['in_conversation'] = False
            from src.bot.menus.shop_menu import ShopMenu
            shop_menu = ShopMenu()
            await shop_menu.show(update, context)
            return ConversationHandler.END
            
        elif callback_data == "clear_selection":
            # Clear selected categories
            context.user_data['selected_categories'] = []
            
            # Update keyboard
            categories = self.shop_service.get_all_categories()
            keyboard = self._create_categories_keyboard(categories, context.user_data['selected_categories'])
            
            await query.edit_message_text(
                "❌ حذف دسته بندی\n\n"
                "📌 دسته بندی های مورد نظر برای حذف را انتخاب کنید:\n"
                "می‌توانید چندین دسته بندی را انتخاب کنید.",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
            return SHOW_CATEGORIES
            
        elif callback_data == "delete_selected":
            # Show confirmation message
            categories = self.shop_service.get_all_categories()
            
            # Get names of selected categories
            selected_names = []
            for category_id in context.user_data['selected_categories']:
                category = next((c for c in categories if c['id'] == category_id), None)
                if category:
                    selected_names.append(category['name'])
            
            # Create confirmation keyboard
            keyboard = [
                [
                    InlineKeyboardButton("✅ بله، حذف شود", callback_data="confirm_delete"),
                    InlineKeyboardButton("❌ خیر، انصراف", callback_data="cancel_delete")
                ]
            ]
            
            await query.edit_message_text(
                f"⚠️ آیا از حذف {len(selected_names)} دسته بندی زیر اطمینان دارید؟\n\n"
                f"📋 موارد انتخاب شده:\n"
                f"{', '.join(selected_names)}\n\n"
                f"⚠️ توجه: با حذف این دسته‌بندی‌ها، محصولات مرتبط با آنها بدون دسته‌بندی (دسته‌بندی نشده) خواهند شد!",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
            return CONFIRM_DELETE
            
        else:
            # Toggle category selection
            try:
                category_id = int(callback_data.split('_')[1])
                
                # Toggle selection
                if category_id in context.user_data['selected_categories']:
                    context.user_data['selected_categories'].remove(category_id)
                else:
                    context.user_data['selected_categories'].append(category_id)
                
                # Update keyboard
                categories = self.shop_service.get_all_categories()
                keyboard = self._create_categories_keyboard(categories, context.user_data['selected_categories'])
                
                await query.edit_message_text(
                    "❌ حذف دسته بندی\n\n"
                    "📌 دسته بندی های مورد نظر برای حذف را انتخاب کنید:\n"
                    "می‌توانید چندین دسته بندی را انتخاب کنید.",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
                
                return SHOW_CATEGORIES
                
            except Exception as e:
                logger.error(f"Error handling category selection: {e}")
                logger.error(traceback.format_exc())
                
                await query.edit_message_text(
                    "❌ خطا در پردازش انتخاب دسته بندی. لطفاً دوباره تلاش کنید."
                )
                
                context.user_data['in_conversation'] = False
                return ConversationHandler.END
    
    async def handle_confirmation(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle delete confirmation"""
        query = update.callback_query
        await query.answer()
        
        callback_data = query.data
        
        if callback_data == "confirm_delete":
            # Delete selected categories
            result = self.shop_service.delete_multiple_categories(context.user_data['selected_categories'])
            
            if result['success']:
                await query.edit_message_text(f"✅ {result['message']}")
            else:
                await query.edit_message_text(f"❌ {result['message']}")
            
            # Clean up
            context.user_data['in_conversation'] = False
            if 'selected_categories' in context.user_data:
                del context.user_data['selected_categories']
            
            return ConversationHandler.END
            
        else:  # cancel_delete
            # Return to category selection
            categories = self.shop_service.get_all_categories()
            keyboard = self._create_categories_keyboard(categories, context.user_data['selected_categories'])
            
            await query.edit_message_text(
                "❌ حذف دسته بندی\n\n"
                "📌 دسته بندی های مورد نظر برای حذف را انتخاب کنید:\n"
                "می‌توانید چندین دسته بندی را انتخاب کنید.",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
            return SHOW_CATEGORIES
    
    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Cancel the conversation"""
        # Clean up user data
        context.user_data['in_conversation'] = False
        if 'selected_categories' in context.user_data:
            del context.user_data['selected_categories']
        
        await update.message.reply_text("❌ عملیات لغو شد.")
        
        # Return to shop menu
        from src.bot.menus.shop_menu import ShopMenu
        shop_menu = ShopMenu()
        await shop_menu.show(update, context)
        
        return ConversationHandler.END 