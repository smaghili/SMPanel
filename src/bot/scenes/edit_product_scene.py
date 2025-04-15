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
from src.bot.menus.admin_menu import AdminMenu
from src.bot.menus.edit_product_menu import EditProductMenu

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# پیام‌های ثابت برای استفاده مجدد
BACK_TO_SHOP_TEXT = "🔙 بازگشت به بخش فروشگاه"
INVALID_VALUE_ERROR = "❌ مقدار وارد شده معتبر نیست. لطفاً یک عدد صحیح وارد کنید."
UPDATE_ERROR_TEMPLATE = "❌ خطایی در ویرایش {0} محصول رخ داد. لطفاً دوباره تلاش کنید."
UPDATE_SUCCESS_TEMPLATE = "✅ {0} محصول با موفقیت از '{1}' به '{2}' تغییر یافت."
NO_CATEGORIES_ERROR = "❌ هیچ دسته بندی یافت نشد. ابتدا یک دسته بندی اضافه کنید."
INVALID_CATEGORY_ERROR = "❌ دسته بندی انتخاب شده معتبر نیست.\nلطفاً دوباره تلاش کنید."
NO_PRODUCTS_ERROR = "❌ هیچ محصولی در دسته بندی '{0}' یافت نشد."

# Define states
(
    SELECT_CATEGORY,
    SELECT_PRODUCT,
    EDIT_OPTIONS,
    EDIT_NAME,
    EDIT_CATEGORY,
    EDIT_DATA_LIMIT,
    EDIT_DURATION,
    EDIT_PRICE,
    CONFIRMATION
) = range(9)

class EditProductScene:
    """Scene for editing products"""
    
    def __init__(self):
        self.shop_service = ShopService()
        self.shop_menu = ShopMenu()
        self.admin_menu = AdminMenu()
        self.edit_product_menu = EditProductMenu()
        
    async def start_scene(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start the scene"""
        # Initialize user data
        context.user_data['in_conversation'] = True
        context.user_data['edit_product'] = {}
        logger.info(f"Starting edit_product scene for user {update.effective_user.id}")
        
        # Get all categories
        categories = self.shop_service.get_all_categories()
        
        if not categories or len(categories) == 0:
            # شناسایی نوع update (پیام یا callback query)
            if update.callback_query:
                await update.callback_query.edit_message_text(NO_CATEGORIES_ERROR)
            else:
                await update.message.reply_text(NO_CATEGORIES_ERROR)
                
            context.user_data['in_conversation'] = False
            
            # استفاده از روش مناسب برای نمایش منو بسته به نوع update
            if update.callback_query:
                chat_id = update.effective_chat.id
                user_id = update.effective_user.id
                await self.shop_menu.show_with_chat_id(
                    chat_id=chat_id,
                    context=context,
                    user_id=user_id,
                    user_states_dict=context.user_data.get('user_states', {}),
                    target_state='shop_management'
                )
            else:
                await self.shop_menu.show(update, context)
                
            return ConversationHandler.END
        
        # Create inline keyboard with categories
        keyboard = []
        for category in categories:
            # Safely get category ID and name with fallbacks
            category_id = category.get('id', 0)
            category_name = category.get('name', 'بدون نام')
            
            keyboard.append([
                InlineKeyboardButton(category_name, callback_data=f"edit_cat_{category_id}")
            ])
        
        # Add back button
        keyboard.append([
            InlineKeyboardButton("🔙 بازگشت", callback_data="cancel_edit")
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # شناسایی نوع update (پیام یا callback query) و استفاده از روش مناسب
        if update.callback_query:
            await update.callback_query.edit_message_text(
                "✏️ ویرایش محصول\n\n"
                "📌 ابتدا یک دسته بندی را انتخاب کنید:",
                reply_markup=reply_markup
            )
        else:
            await update.message.reply_text(
                "✏️ ویرایش محصول\n\n"
                "📌 ابتدا یک دسته بندی را انتخاب کنید:",
                reply_markup=reply_markup
            )
        
        return SELECT_CATEGORY
        
    async def select_category(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle category selection"""
        query = update.callback_query
        await query.answer()
        
        callback_data = query.data
        
        # Handle cancel
        if callback_data == "cancel_edit":
            context.user_data['in_conversation'] = False
            await query.edit_message_text("در حال بازگشت به منوی فروشگاه...")
            
            # استفاده از chat_id به جای update.message که در callback_query خالی است
            chat_id = update.effective_chat.id
            user_id = update.effective_user.id
            
            # استفاده از show_with_chat_id به جای show
            await self.shop_menu.show_with_chat_id(
                chat_id=chat_id, 
                context=context, 
                user_id=user_id,
                user_states_dict=context.user_data.get('user_states', {}),
                target_state='shop_management'
            )
            
            return ConversationHandler.END
        
        # Extract category ID
        category_id = int(callback_data.split('_')[2])
        
        # Get category details
        categories = self.shop_service.get_all_categories()
        selected_category = next((c for c in categories if c['id'] == category_id), None)
        
        if not selected_category:
            await query.edit_message_text(INVALID_CATEGORY_ERROR)
            context.user_data['in_conversation'] = False
            return ConversationHandler.END
        
        # Save category in user data
        context.user_data['edit_product']['category_id'] = category_id
        context.user_data['edit_product']['category_name'] = selected_category['name']
        
        # Get products in this category
        products = self.shop_service.get_all_products()
        category_products = [p for p in products if p.get('category_id') == category_id]
        
        if not category_products:
            await query.edit_message_text(NO_PRODUCTS_ERROR.format(selected_category['name']))
            context.user_data['in_conversation'] = False
            return ConversationHandler.END
        
        # Create keyboard with products
        keyboard = []
        for product in category_products:
            product_id = product.get('id', 0)
            product_name = product.get('name', 'بدون نام')
            
            keyboard.append([
                InlineKeyboardButton(product_name, callback_data=f"edit_prod_{product_id}")
            ])
        
        # Add back button
        keyboard.append([
            InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_categories")
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # حذف پیام قبلی و ایجاد پیام جدید
        await query.message.delete()
        
        # ارسال پیام جدید برای انتخاب محصول
        await query.message.reply_text(
            f"✏️ ویرایش محصول در دسته بندی: {selected_category['name']}\n\n"
            f"📌 محصول مورد نظر برای ویرایش را انتخاب کنید:",
            reply_markup=reply_markup
        )
        
        return SELECT_PRODUCT
        
    async def select_product(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle product selection"""
        query = update.callback_query
        await query.answer()
        
        callback_data = query.data
        
        # Handle back to categories
        if callback_data == "back_to_categories":
            return await self.start_scene(update, context)
        
        # Extract product ID
        product_id = int(callback_data.split('_')[2])
        
        # Get product details
        product = self.shop_service.get_product_by_id(product_id)
        
        if not product:
            await query.edit_message_text(
                "❌ محصول انتخاب شده معتبر نیست.\n"
                "لطفاً دوباره تلاش کنید."
            )
            context.user_data['in_conversation'] = False
            return ConversationHandler.END
        
        # Save product in user data
        context.user_data['edit_product']['product_id'] = product_id
        context.user_data['edit_product']['product_name'] = product['name']
        context.user_data['edit_product']['data_limit'] = product['data_limit']
        context.user_data['edit_product']['duration'] = product['duration']
        context.user_data['edit_product']['price'] = product['price']
        
        # Format product details for display
        data_limit_str = f"{product['data_limit']} گیگابایت" if product['data_limit'] > 0 else "نامحدود"
        duration_str = f"{product['duration']} روز" if product['duration'] > 0 else "نامحدود"
        price_formatted = '{:,}'.format(int(product['price']))
        
        # حذف کیبورد قبلی (inline keyboard)
        await query.edit_message_reply_markup(reply_markup=None)
        
        # حذف پیام قبلی
        await query.message.delete()
        
        # Setup edit options menu
        self.edit_product_menu.setup_edit_options_menu(product['name'])
        keyboard_markup = self.edit_product_menu.create_keyboard_markup()
        
        # ارسال پیام جدید با کیبورد فیزیکی و اطلاعات محصول
        await query.message.reply_text(
            f"🖊️ ویرایش محصول: {product['name']}\n\n"
            f"📝 مشخصات فعلی محصول:\n"
            f"🏷️ دسته بندی: {product['category_name']}\n"
            f"📊 حجم: {data_limit_str}\n"
            f"⏱️ مدت زمان: {duration_str}\n"
            f"💰 قیمت: {price_formatted} تومان\n\n"
            f"لطفاً بخش مورد نظر برای ویرایش را انتخاب کنید:",
            reply_markup=keyboard_markup
        )
        
        return EDIT_OPTIONS
        
    async def handle_edit_options(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle edit options selection"""
        if update.callback_query:
            query = update.callback_query
            await query.answer()
            
            # Handle keyboard buttons
            if query.data == "back_to_admin":
                context.user_data['in_conversation'] = False
                await query.message.reply_text("در حال بازگشت به پنل مدیریت...")
                await self.admin_menu.show(update, context)
                return ConversationHandler.END
                
            elif query.data == "back_to_shop":
                context.user_data['in_conversation'] = False
                await query.message.reply_text("در حال بازگشت به منوی فروشگاه...")
                await self.shop_menu.show(update, context)
                return ConversationHandler.END
                
            else:
                await query.message.reply_text("لطفاً از کیبورد ارائه شده استفاده کنید.")
                return EDIT_OPTIONS
        
        else:
            # Handle message (Reply Keyboard)
            message_text = update.message.text
            
            # Check if the user wants to go back to shop
            if message_text == BACK_TO_SHOP_TEXT:
                context.user_data['in_conversation'] = False
                await self.shop_menu.show(update, context)
                return ConversationHandler.END
                
            # Based on selected option, move to appropriate edit state
            if message_text == "نام محصول":
                await update.message.reply_text(
                    f"📝 لطفاً نام جدید برای محصول '{context.user_data['edit_product']['product_name']}' وارد کنید:"
                )
                return EDIT_NAME
                
            elif message_text == "دسته بندی":
                # Get all categories
                categories = self.shop_service.get_all_categories()
                
                if not categories:
                    await update.message.reply_text(NO_CATEGORIES_ERROR)
                    return EDIT_OPTIONS
                
                # Create keyboard with categories
                keyboard = []
                for category in categories:
                    category_id = category.get('id', 0)
                    category_name = category.get('name', 'بدون نام')
                    
                    # Mark current category
                    if category_id == context.user_data['edit_product'].get('category_id'):
                        category_name = f"✅ {category_name} (فعلی)"
                    
                    keyboard.append([
                        InlineKeyboardButton(category_name, callback_data=f"set_cat_{category_id}")
                    ])
                
                # Add back button
                keyboard.append([
                    InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_edit_options")
                ])
                
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(
                    "🏷️ دسته بندی جدید را انتخاب کنید:",
                    reply_markup=reply_markup
                )
                return EDIT_CATEGORY
                
            elif message_text == "حجم":
                current_data_limit = context.user_data['edit_product']['data_limit']
                limit_text = f"{current_data_limit} گیگابایت" if current_data_limit > 0 else "نامحدود"
                
                await update.message.reply_text(
                    f"📊 حجم فعلی: {limit_text}\n\n"
                    f"لطفاً حجم جدید را به گیگابایت وارد کنید (عدد 0 به معنای نامحدود است):"
                )
                return EDIT_DATA_LIMIT
                
            elif message_text == "مدت زمان":
                current_duration = context.user_data['edit_product']['duration']
                duration_text = f"{current_duration} روز" if current_duration > 0 else "نامحدود"
                
                await update.message.reply_text(
                    f"⏱️ مدت زمان فعلی: {duration_text}\n\n"
                    f"لطفاً مدت زمان جدید را به روز وارد کنید (عدد 0 به معنای نامحدود است):"
                )
                return EDIT_DURATION
                
            elif message_text == "قیمت":
                current_price = context.user_data['edit_product']['price']
                price_formatted = '{:,}'.format(int(current_price))
                
                await update.message.reply_text(
                    f"💰 قیمت فعلی: {price_formatted} تومان\n\n"
                    f"لطفاً قیمت جدید را به تومان وارد کنید:"
                )
                return EDIT_PRICE
                
            else:
                await update.message.reply_text("لطفاً یکی از گزینه‌های ارائه شده را انتخاب کنید.")
                return EDIT_OPTIONS
    
    # متد کمکی برای به‌روزرسانی محصول
    async def _update_product_and_show_result(self, update, context, field_name, old_value_str, new_value_str, return_state):
        """متد کمکی برای به‌روزرسانی محصول و نمایش نتیجه"""
        try:
            success = self.shop_service.update_product(
                context.user_data['edit_product']['product_id'],
                context.user_data['edit_product']['product_name'],
                context.user_data['edit_product']['data_limit'],
                context.user_data['edit_product']['price'],
                context.user_data['edit_product']['category_id'],
                context.user_data['edit_product']['duration']
            )
            
            if success:
                # Setup edit options menu
                self.edit_product_menu.setup_edit_options_menu(context.user_data['edit_product']['product_name'])
                keyboard_markup = self.edit_product_menu.create_keyboard_markup()
                
                await update.message.reply_text(
                    UPDATE_SUCCESS_TEMPLATE.format(field_name, old_value_str, new_value_str),
                    reply_markup=keyboard_markup
                )
                
                return EDIT_OPTIONS
            else:
                await update.message.reply_text(UPDATE_ERROR_TEMPLATE.format(field_name))
                return return_state
        
        except Exception as e:
            logger.error(f"Error updating product {field_name}: {e}")
            await update.message.reply_text(UPDATE_ERROR_TEMPLATE.format(field_name))
            return return_state

    async def edit_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle product name edit"""
        # Check if the user is trying to go back
        if update.message.text == BACK_TO_SHOP_TEXT:
            context.user_data['in_conversation'] = False
            await self.shop_menu.show(update, context)
            return ConversationHandler.END
        
        # Get the old and new names
        old_name = context.user_data['edit_product']['product_name']
        new_name = update.message.text.strip()
        
        # Validate the new name
        if not new_name:
            await update.message.reply_text("❌ نام وارد شده نامعتبر است.\nلطفاً یک نام معتبر وارد کنید.")
            return EDIT_NAME
        
        # Update the user data
        context.user_data['edit_product']['product_name'] = new_name
        
        # Update the product in database and show result
        return await self._update_product_and_show_result(
            update, context, "نام", old_name, new_name, EDIT_NAME
        )
            
    async def edit_category(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle category edit"""
        query = update.callback_query
        await query.answer()
        
        callback_data = query.data
        
        # Handle back to edit options
        if callback_data == "back_to_edit_options":
            # حذف کیبورد inline
            await query.edit_message_reply_markup(reply_markup=None)
            
            # نمایش پیام با کیبورد فیزیکی
            self.edit_product_menu.setup_edit_options_menu(context.user_data['edit_product']['product_name'])
            keyboard_markup = self.edit_product_menu.create_keyboard_markup()
            
            await query.message.reply_text(
                "لطفاً بخش مورد نظر برای ویرایش را انتخاب کنید:",
                reply_markup=keyboard_markup
            )
            return EDIT_OPTIONS
        
        # Extract category ID
        category_id = int(callback_data.split('_')[2])
        
        # Get category details
        categories = self.shop_service.get_all_categories()
        selected_category = next((c for c in categories if c['id'] == category_id), None)
        
        if not selected_category:
            await query.edit_message_text(INVALID_CATEGORY_ERROR)
            return EDIT_CATEGORY
        
        # Save old and new category info
        old_category_id = context.user_data['edit_product']['category_id']
        old_category = next((c for c in categories if c['id'] == old_category_id), {'name': 'نامشخص'})
        
        context.user_data['edit_product']['category_id'] = category_id
        context.user_data['edit_product']['category_name'] = selected_category['name']
        
        # Update product in database
        try:
            success = self.shop_service.update_product(
                context.user_data['edit_product']['product_id'],
                context.user_data['edit_product']['product_name'],
                context.user_data['edit_product']['data_limit'],
                context.user_data['edit_product']['price'],
                category_id,
                context.user_data['edit_product']['duration']
            )
            
            if success:
                # حذف کیبورد inline
                await query.edit_message_reply_markup(reply_markup=None)
                
                # حذف پیام دسته بندی جدید انتخاب کنید
                await query.message.delete()
                
                # تنظیم منوی ویرایش
                self.edit_product_menu.setup_edit_options_menu(context.user_data['edit_product']['product_name'])
                keyboard_markup = self.edit_product_menu.create_keyboard_markup()
                
                # نمایش فقط پیام موفقیت و برگشت به منوی ویرایش
                sent_message = await query.message.reply_text(
                    UPDATE_SUCCESS_TEMPLATE.format("دسته بندی", old_category['name'], selected_category['name']),
                    reply_markup=keyboard_markup
                )
                
                return EDIT_OPTIONS
            else:
                await query.edit_message_text(UPDATE_ERROR_TEMPLATE.format("دسته بندی"))
                return EDIT_CATEGORY
        
        except ValueError as e:
            await query.edit_message_text(f"❌ خطا: {str(e)}")
            return EDIT_CATEGORY
        except Exception as e:
            logger.error(f"Error updating product category: {e}")
            await query.edit_message_text(UPDATE_ERROR_TEMPLATE.format("دسته بندی"))
            return EDIT_CATEGORY
            
    async def edit_data_limit(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle data limit edit"""
        data_limit_text = update.message.text.strip()
        
        # Check if user is trying to go back
        if data_limit_text == BACK_TO_SHOP_TEXT:
            context.user_data['in_conversation'] = False
            await self.shop_menu.show(update, context)
            return ConversationHandler.END
        
        # Convert to integer
        try:
            new_data_limit = int(data_limit_text)
            if new_data_limit < 0:
                raise ValueError("Data limit must be non-negative")
        except ValueError:
            await update.message.reply_text(INVALID_VALUE_ERROR)
            return EDIT_DATA_LIMIT
        
        # Format old and new values for display
        old_data_limit = context.user_data['edit_product']['data_limit']
        old_data_limit_str = f"{old_data_limit} گیگابایت" if old_data_limit > 0 else "نامحدود"
        new_data_limit_str = f"{new_data_limit} گیگابایت" if new_data_limit > 0 else "نامحدود"
        
        # Update the user data
        context.user_data['edit_product']['data_limit'] = new_data_limit
        
        # Update the product in database and show result
        return await self._update_product_and_show_result(
            update, context, "حجم", old_data_limit_str, new_data_limit_str, EDIT_DATA_LIMIT
        )
            
    async def edit_duration(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle duration edit"""
        duration_text = update.message.text.strip()
        
        # Check if user is trying to go back
        if duration_text == BACK_TO_SHOP_TEXT:
            context.user_data['in_conversation'] = False
            await self.shop_menu.show(update, context)
            return ConversationHandler.END
        
        # Convert to integer
        try:
            new_duration = int(duration_text)
            if new_duration < 0:
                raise ValueError("Duration must be non-negative")
        except ValueError:
            await update.message.reply_text(INVALID_VALUE_ERROR)
            return EDIT_DURATION
        
        # Format old and new values for display
        old_duration = context.user_data['edit_product']['duration']
        old_duration_str = f"{old_duration} روز" if old_duration > 0 else "نامحدود"
        new_duration_str = f"{new_duration} روز" if new_duration > 0 else "نامحدود"
        
        # Update the user data
        context.user_data['edit_product']['duration'] = new_duration
        
        # Update the product in database and show result
        return await self._update_product_and_show_result(
            update, context, "مدت زمان", old_duration_str, new_duration_str, EDIT_DURATION
        )
            
    async def edit_price(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle price edit"""
        price_text = update.message.text.strip()
        
        # Check if user is trying to go back
        if price_text == BACK_TO_SHOP_TEXT:
            context.user_data['in_conversation'] = False
            await self.shop_menu.show(update, context)
            return ConversationHandler.END
        
        # Convert to integer
        try:
            # Remove commas if present
            price_text = price_text.replace(',', '')
            new_price = int(price_text)
            if new_price < 0:
                raise ValueError("Price must be non-negative")
        except ValueError:
            await update.message.reply_text(INVALID_VALUE_ERROR)
            return EDIT_PRICE
        
        # Format old and new values for display
        old_price = context.user_data['edit_product']['price']
        old_price_str = '{:,}'.format(int(old_price)) + " تومان"
        new_price_str = '{:,}'.format(new_price) + " تومان"
        
        # Update the user data
        context.user_data['edit_product']['price'] = new_price
        
        # Update the product in database and show result
        return await self._update_product_and_show_result(
            update, context, "قیمت", old_price_str, new_price_str, EDIT_PRICE
        )
            
    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Cancel the conversation"""
        # Clean up user data
        if 'edit_product' in context.user_data:
            del context.user_data['edit_product']
        
        # Reset conversation flag
        context.user_data['in_conversation'] = False
        
        # Return to shop menu
        await self.shop_menu.show(update, context)
        return ConversationHandler.END
            
    def get_handler(self):
        """Return the ConversationHandler for this scene"""
        return ConversationHandler(
            entry_points=[CommandHandler('edit_product', self.start_scene)],
            states={
                SELECT_CATEGORY: [
                    CallbackQueryHandler(self.select_category, pattern=r'^edit_cat_|^cancel_edit')
                ],
                SELECT_PRODUCT: [
                    CallbackQueryHandler(self.select_product, pattern=r'^edit_prod_|^back_to_categories')
                ],
                EDIT_OPTIONS: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_edit_options),
                    CallbackQueryHandler(self.handle_edit_options)
                ],
                EDIT_NAME: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.edit_name)
                ],
                EDIT_CATEGORY: [
                    CallbackQueryHandler(self.edit_category, pattern=r'^set_cat_|^back_to_edit_options')
                ],
                EDIT_DATA_LIMIT: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.edit_data_limit)
                ],
                EDIT_DURATION: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.edit_duration)
                ],
                EDIT_PRICE: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.edit_price)
                ]
            },
            fallbacks=[
                CommandHandler('cancel', self.cancel),
                MessageHandler(filters.Regex(f'^{BACK_TO_SHOP_TEXT}$'), self.cancel)
            ],
            name="edit_product_conversation",
            persistent=False
        )
