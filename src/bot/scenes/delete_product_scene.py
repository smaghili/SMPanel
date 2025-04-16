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
    SELECT_CATEGORY,
    SELECT_PRODUCT,
    CONFIRM_DELETE
) = range(3)

# Define alias for compatibility with index.py
PRODUCT_CONFIRM_DELETE = CONFIRM_DELETE

class DeleteProductScene:
    """Scene for deleting products"""
    
    def __init__(self):
        self.shop_service = ShopService()
        self.shop_menu = ShopMenu()
    
    def get_handler(self):
        """Get the conversation handler for this scene"""
        return ConversationHandler(
            entry_points=[],  # This will be set by the caller
            states={
                SELECT_CATEGORY: [CallbackQueryHandler(self.handle_selection)],
                SELECT_PRODUCT: [CallbackQueryHandler(self.handle_selection)],
                PRODUCT_CONFIRM_DELETE: [CallbackQueryHandler(self.handle_confirmation)],
            },
            fallbacks=[CommandHandler("cancel", self.cancel)],
            name="delete_product_conversation"
        )
    
    async def start_scene(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start the scene"""
        # Initialize user data
        context.user_data['in_conversation'] = True
        context.user_data['selected_products'] = []
        logger.info(f"Starting delete_product scene for user {update.effective_user.id}")
        logger.info(f"Setting in_conversation to True")
        
        # Get all categories for displaying
        categories = self.shop_service.get_all_categories()
        
        if not categories or len(categories) == 0:
            await update.message.reply_text("❌ هیچ دسته‌بندی یافت نشد. ابتدا یک دسته‌بندی اضافه کنید.")
            context.user_data['in_conversation'] = False
            return ConversationHandler.END
        
        # Create keyboard with categories
        keyboard = []
        for category in categories:
            keyboard.append([
                InlineKeyboardButton(category['name'], callback_data=f"cat_{category['id']}")
            ])
        
        keyboard.append([
            InlineKeyboardButton("🔙 بازگشت", callback_data="back")
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "❌ حذف محصول\n\n"
            "📌 لطفاً ابتدا دسته‌بندی محصولات را انتخاب کنید:",
            reply_markup=reply_markup
        )
        
        return SELECT_CATEGORY
    
    def _create_products_keyboard(self, products, selected_products):
        """Create keyboard with products"""
        keyboard = []
        
        # Add products
        for product in products:
            product_id = product.get('id', 0)
            product_name = product.get('name', 'بدون نام')
            
            # فقط نام محصول نمایش داده شود
            checkbox = "☑️" if product_id in selected_products else "⬜️"
            keyboard.append([
                InlineKeyboardButton(
                    f"{checkbox} {product_name}", 
                    callback_data=f"product_{product_id}"
                )
            ])
        
        # Add control buttons
        control_buttons = []
        
        if selected_products:
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
        """Handle product selection"""
        query = update.callback_query
        await query.answer()
        
        callback_data = query.data
        
        # اگر کاربر دکمه بازگشت را زده است
        if callback_data == 'back':
            # ویرایش پیام برای نشان دادن بازگشت
            await query.edit_message_text("بازگشت به منوی مدیریت فروشگاه...")
            
            # دریافت chat_id و user_id برای استفاده در show_with_chat_id
            chat_id = update.effective_chat.id
            user_id = update.effective_user.id
            
            # پاک کردن داده‌های کاربر
            context.user_data['in_conversation'] = False
            if 'selected_products' in context.user_data:
                del context.user_data['selected_products']
            
            # استفاده از show_with_chat_id به جای show
            await self.shop_menu.show_with_chat_id(
                chat_id=chat_id,
                context=context,
                user_id=user_id,
                user_states_dict=context.user_data.get('user_states', {}),
                target_state="shop_management"
            )
            return ConversationHandler.END
        
        # گرفتن دسته‌بندی‌ها
        categories = self.shop_service.get_all_categories()
        
        # اگر دکمه انتخاب دسته‌بندی زده شده
        if callback_data.startswith('cat_'):
            category_id = int(callback_data.split('_')[1])
            
            # ذخیره دسته‌بندی انتخاب شده
            context.user_data['selected_category'] = category_id
            
            # گرفتن محصولات دسته‌بندی
            products = self.shop_service.get_products_by_category(category_id)
            
            if not products:
                await query.edit_message_text(
                    "❌ هیچ محصولی در این دسته‌بندی یافت نشد.",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_categories")
                    ]])
                )
                return SELECT_PRODUCT
            
            # ایجاد کیبورد محصولات
            keyboard = []
            # ایجاد فهرست انتخاب‌ها اگر وجود ندارد
            if 'selected_products' not in context.user_data:
                context.user_data['selected_products'] = []
                
            for product in products:
                product_id = product['id']
                product_name = product['name']
                
                # نشان دادن وضعیت انتخاب
                is_selected = product_id in context.user_data['selected_products']
                prefix = "✅" if is_selected else "⬜️"
                
                keyboard.append([
                    InlineKeyboardButton(f"{prefix} {product_name}", callback_data=f"prod_{product_id}")
                ])
            
            # دکمه‌های عملیات
            action_row = []
            
            # فقط زمانی دکمه حذف موارد انتخاب شده را نشان بده که حداقل یک محصول انتخاب شده باشد
            if context.user_data.get('selected_products', []):
                action_row.append(
                    InlineKeyboardButton("❌ حذف موارد انتخاب شده", callback_data="delete_selected")
                )
            
            action_row.append(
                InlineKeyboardButton("🔙 بازگشت به دسته‌بندی‌ها", callback_data="back_to_categories")
            )
            
            keyboard.append(action_row)
            
            selected_category_name = next((c['name'] for c in categories if c['id'] == category_id), "نامشخص")
            
            await query.edit_message_text(
                f"❌ حذف محصول از دسته‌بندی: {selected_category_name}\n\n"
                f"📌 محصولات مورد نظر برای حذف را انتخاب کنید:\n"
                f"می‌توانید چندین محصول را انتخاب کنید.",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
            return SELECT_PRODUCT
        
        # اگر دکمه بازگشت به دسته‌بندی‌ها زده شده
        elif callback_data == 'back_to_categories':
            # نمایش دسته‌بندی‌ها
            keyboard = []
            for category in categories:
                keyboard.append([
                    InlineKeyboardButton(category['name'], callback_data=f"cat_{category['id']}")
                ])
            
            keyboard.append([
                InlineKeyboardButton("🔙 بازگشت", callback_data="back")
            ])
            
            await query.edit_message_text(
                "❌ حذف محصول\n\n"
                "📌 لطفاً ابتدا دسته‌بندی محصولات را انتخاب کنید:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
            return SELECT_CATEGORY
        
        # اگر دکمه حذف موارد انتخاب شده زده شده
        elif callback_data == 'delete_selected':
            selected_products = context.user_data.get('selected_products', [])
            
            if not selected_products:
                await query.edit_message_text(
                    "⚠️ هیچ محصولی برای حذف انتخاب نشده است.\n"
                    "لطفاً حداقل یک محصول را انتخاب کنید.",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_categories")
                    ]])
                )
                return SELECT_PRODUCT
            
            # دریافت اطلاعات محصولات انتخاب شده
            category_id = context.user_data.get('selected_category')
            products = self.shop_service.get_products_by_category(category_id)
            
            selected_product_names = []
            for product_id in selected_products:
                product = next((p for p in products if p['id'] == product_id), None)
                if product:
                    selected_product_names.append(product['name'])
            
            # نمایش پیام تأیید
            keyboard = [
                [
                    InlineKeyboardButton("✅ بله، حذف شود", callback_data="confirm_delete"),
                    InlineKeyboardButton("❌ خیر، انصراف", callback_data="back_to_categories")
                ]
            ]
            
            await query.edit_message_text(
                f"⚠️ آیا از حذف {len(selected_products)} محصول زیر اطمینان دارید؟\n\n"
                f"📋 موارد انتخاب شده:\n"
                f"{', '.join(selected_product_names)}\n\n"
                f"⚠️ توجه: این عمل غیرقابل بازگشت است!",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
            return PRODUCT_CONFIRM_DELETE
        
        # اگر دکمه تأیید حذف زده شده
        elif callback_data == 'confirm_delete':
            selected_products = context.user_data.get('selected_products', [])
            
            if not selected_products:
                await query.edit_message_text("❌ خطا در پردازش درخواست. لطفاً دوباره تلاش کنید.")
                return ConversationHandler.END
            
            # حذف محصولات
            result = self.shop_service.delete_multiple_products(selected_products)
            
            if result['success']:
                await query.edit_message_text(
                    f"✅ {result['message']}",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("🔙 بازگشت به منوی مدیریت", callback_data="back")
                    ]])
                )
            else:
                await query.edit_message_text(
                    f"❌ {result['message']}",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("🔙 بازگشت به منوی مدیریت", callback_data="back")
                    ]])
                )
            
            # پاک کردن انتخاب‌ها
            if 'selected_products' in context.user_data:
                del context.user_data['selected_products']
            
            return SELECT_CATEGORY
        
        # اگر یک محصول انتخاب شده
        elif callback_data.startswith('prod_'):
            product_id = int(callback_data.split('_')[1])
            
            # ایجاد فهرست انتخاب‌ها اگر وجود ندارد
            if 'selected_products' not in context.user_data:
                context.user_data['selected_products'] = []
            
            # تغییر وضعیت انتخاب محصول
            if product_id in context.user_data['selected_products']:
                context.user_data['selected_products'].remove(product_id)
            else:
                context.user_data['selected_products'].append(product_id)
            
            # نمایش دوباره محصولات با وضعیت جدید
            category_id = context.user_data.get('selected_category')
            products = self.shop_service.get_products_by_category(category_id)
            
            keyboard = []
            for product in products:
                product_id = product['id']
                product_name = product['name']
                
                # نشان دادن وضعیت انتخاب
                is_selected = product_id in context.user_data['selected_products']
                prefix = "✅" if is_selected else "⬜️"
                
                keyboard.append([
                    InlineKeyboardButton(f"{prefix} {product_name}", callback_data=f"prod_{product_id}")
                ])
            
            # دکمه‌های عملیات
            action_row = []
            
            # فقط زمانی دکمه حذف موارد انتخاب شده را نشان بده که حداقل یک محصول انتخاب شده باشد
            if context.user_data.get('selected_products', []):
                action_row.append(
                    InlineKeyboardButton("❌ حذف موارد انتخاب شده", callback_data="delete_selected")
                )
            
            action_row.append(
                InlineKeyboardButton("🔙 بازگشت به دسته‌بندی‌ها", callback_data="back_to_categories")
            )
            
            keyboard.append(action_row)
            
            selected_category_name = next((c['name'] for c in categories if c['id'] == category_id), "نامشخص")
            
            await query.edit_message_text(
                f"❌ حذف محصول از دسته‌بندی: {selected_category_name}\n\n"
                f"📌 محصولات مورد نظر برای حذف را انتخاب کنید:\n"
                f"می‌توانید چندین محصول را انتخاب کنید.",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
            return SELECT_PRODUCT
    
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
            # Delete selected products
            result = self.shop_service.delete_multiple_products(context.user_data['selected_products'])
            
            if result['success']:
                await query.edit_message_text(f"✅ {result['message']}")
            else:
                await query.edit_message_text(f"❌ {result['message']}")
            
            # Clean up
            context.user_data['in_conversation'] = False
            if 'selected_products' in context.user_data:
                del context.user_data['selected_products']
            
            return ConversationHandler.END
            
        else:  # cancel_delete
            # Return to product selection
            products = self.shop_service.get_all_products()
            keyboard = self._create_products_keyboard(products, context.user_data['selected_products'])
            
            await query.edit_message_text(
                "❌ حذف محصول\n\n"
                "📌 محصولات مورد نظر برای حذف را انتخاب کنید:\n"
                "می‌توانید چندین محصول را انتخاب کنید.",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
            return SELECT_PRODUCT
    
    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Cancel the conversation"""
        # Clean up user data
        context.user_data['in_conversation'] = False
        if 'selected_products' in context.user_data:
            del context.user_data['selected_products']
        
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