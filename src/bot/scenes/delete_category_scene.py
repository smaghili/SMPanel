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
from src.bot.menus.shop_menu import ShopMenu

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
        self.shop_menu = ShopMenu()
    
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
        
        # اگر کاربر دکمه بازگشت را انتخاب کرده است
        if callback_data == 'back':
            # ویرایش پیام برای نشان دادن بازگشت
            await query.edit_message_text("بازگشت به منوی مدیریت فروشگاه...")
            
            # دریافت chat_id و user_id برای استفاده در show_with_chat_id
            chat_id = update.effective_chat.id
            user_id = update.effective_user.id
            
            # پاک کردن داده‌های کاربر
            context.user_data['in_conversation'] = False
            if 'selected_categories' in context.user_data:
                del context.user_data['selected_categories']
            
            # استفاده از show_with_chat_id به جای show
            await self.shop_menu.show_with_chat_id(
                chat_id=chat_id,
                context=context,
                user_id=user_id,
                user_states_dict=context.user_data.get('user_states', {}),
                target_state="shop_management"
            )
            return ConversationHandler.END
        
        # اگر کاربر دکمه حذف موارد انتخاب شده را زده است
        elif callback_data == 'delete_selected':
            # بررسی کنیم که آیا دسته‌بندی‌ای انتخاب شده است
            selected_categories = context.user_data.get('selected_categories', [])
            
            if not selected_categories:
                await query.edit_message_text(
                    "⚠️ هیچ دسته‌بندی برای حذف انتخاب نشده است.\n"
                    "لطفاً حداقل یک دسته‌بندی را انتخاب کنید.",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("🔙 بازگشت", callback_data="back")
                    ]])
                )
                return SHOW_CATEGORIES
            
            # دریافت اطلاعات دسته‌بندی‌های انتخاب شده
            categories = self.shop_service.get_all_categories()
            selected_names = []
            
            for cat_id in selected_categories:
                category = next((c for c in categories if c['id'] == cat_id), None)
                if category:
                    selected_names.append(category['name'])
            
            # نمایش پیام تأیید حذف
            keyboard = [
                [
                    InlineKeyboardButton("✅ بله، حذف شود", callback_data="confirm_delete"),
                    InlineKeyboardButton("❌ خیر، انصراف", callback_data="cancel_delete")
                ]
            ]
            
            # ساخت متن پیام تایید با نام دسته‌بندی‌های انتخاب شده
            confirm_text = f"⚠️ آیا از حذف {len(selected_names)} دسته‌بندی زیر اطمینان دارید؟\n\n"
            confirm_text += "📋 دسته‌بندی‌های انتخاب شده:\n"
            for i, name in enumerate(selected_names):
                confirm_text += f"{i+1}. {name}\n"
            
            confirm_text += "\n⚠️ توجه: با حذف این دسته‌بندی‌ها، محصولات مرتبط با آنها بدون دسته‌بندی خواهند شد!"
            
            await query.edit_message_text(
                confirm_text,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
            return CONFIRM_DELETE
        
        # اگر کاربر روی یک دسته‌بندی کلیک کرده است
        elif callback_data.startswith('category_'):
            # ایجاد فهرست دسته‌بندی‌های انتخاب شده اگر وجود ندارد
            if 'selected_categories' not in context.user_data:
                context.user_data['selected_categories'] = []
            
            # استخراج شناسه دسته‌بندی از داده‌های بازخوردی
            category_id = int(callback_data.split('_')[1])
            selected_categories = context.user_data['selected_categories']
            
            # اضافه یا حذف دسته‌بندی از فهرست انتخاب‌ها
            if category_id in selected_categories:
                selected_categories.remove(category_id)
            else:
                selected_categories.append(category_id)
            
            # دریافت همه دسته‌بندی‌ها
            categories = self.shop_service.get_all_categories()
            
            # ایجاد صفحه کلید با وضعیت جدید
            keyboard = []
            for category in categories:
                category_id = category['id']
                category_name = category['name']
                
                # بررسی آیا دسته‌بندی انتخاب شده است
                is_selected = category_id in selected_categories
                check_mark = "✅" if is_selected else "⬜️"
                
                keyboard.append([
                    InlineKeyboardButton(f"{check_mark} {category_name}", callback_data=f"category_{category_id}")
                ])
            
            # اضافه کردن دکمه حذف و بازگشت
            keyboard.append([
                InlineKeyboardButton("❌ حذف موارد انتخاب شده", callback_data="delete_selected"),
                InlineKeyboardButton("🔙 بازگشت", callback_data="back")
            ])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                "❌ حذف دسته بندی\n\n"
                "📌 دسته بندی های مورد نظر برای حذف را انتخاب کنید:\n"
                "می‌توانید چندین دسته بندی را انتخاب کنید.",
                reply_markup=reply_markup
            )
            
            return SHOW_CATEGORIES
        
        # برای سایر داده‌های callback که پشتیبانی نشده‌اند
        else:
            logger.warning(f"Unsupported callback data: {callback_data}")
            await query.edit_message_text(
                "❌ عملیات نامعتبر. لطفاً دوباره تلاش کنید.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 بازگشت", callback_data="back")
                ]])
            )
            return SHOW_CATEGORIES
    
    async def handle_confirmation(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle delete confirmation"""
        query = update.callback_query
        await query.answer()
        
        # بررسی کن که آیا هنوز در گفتگو هستیم
        if not context.user_data.get('in_conversation', False):
            # کاربر از طریق دکمه‌های فیزیکی از گفتگو خارج شده است
            try:
                await query.edit_message_text("⚠️ عملیات لغو شده است.")
            except Exception:
                # ممکن است پیام قبلاً ویرایش شده باشد
                pass
            return ConversationHandler.END
        
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
        
        # Get chat_id and user_id
        chat_id = update.effective_chat.id
        user_id = update.effective_user.id
        
        await update.message.reply_text("❌ عملیات لغو شد.")
        
        # Return to shop menu with improved state management
        await self.shop_menu.show_with_chat_id(
            chat_id=chat_id,
            context=context,
            user_id=user_id,
            user_states_dict=context.user_data.get('user_states', {}),
            target_state="shop_management"
        )
        
        return ConversationHandler.END 