#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters
)
import logging

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
    SHOW_MENU,
    SET_PRICE,
    SET_MIN_VOLUME,
    SET_MAX_VOLUME
) = range(5)

class ExtraVolumeSettingsScene:
    """Scene for configuring extra volume settings"""
    
    def __init__(self):
        self.shop_service = ShopService()
        self.shop_menu = ShopMenu()
    
    # متدهای کمکی جدید برای کاهش تکرار کد
    def _format_volume_display(self, volume):
        """نمایش مقدار حجم به صورت متنی مناسب"""
        return f"{volume} گیگابایت" if volume > 0 else "بدون محدودیت"
    
    def _get_settings_status_text(self, context):
        """تولید متن وضعیت تنظیمات حجم اضافه"""
        category_name = context.user_data['extra_volume_settings']['category_name']
        price_per_gb = context.user_data['extra_volume_settings']['price_per_gb']
        min_volume = context.user_data['extra_volume_settings']['min_volume']
        max_volume = context.user_data['extra_volume_settings']['max_volume']
        is_enabled = context.user_data['extra_volume_settings']['is_enabled']
        
        # Prepare status message
        enabled_status = "✅ فعال" if is_enabled else "❌ غیرفعال"
        min_volume_display = self._format_volume_display(min_volume)
        max_volume_display = self._format_volume_display(max_volume)
        
        return (
            f"➕ تنظیمات حجم اضافه برای: {category_name}\n\n"
            f"تنظیمات فعلی:\n"
            f"💰 قیمت هر گیگابایت: {price_per_gb:,} تومان\n"
            f"⬇️ حداقل حجم: {min_volume_display}\n"
            f"⬆️ حداکثر حجم: {max_volume_display}\n"
            f"🔄 وضعیت خرید: {enabled_status}"
        )
    
    def _get_settings_keyboard(self):
        """تولید کیبورد تنظیمات حجم اضافه"""
        return [
            ["💰 تنظیم قیمت هر گیگابایت"],
            ["⬇️ تنظیم حداقل حجم خرید", "⬆️ تنظیم حداکثر حجم خرید"],
            ["🔄 فعال یا غیرفعال کردن خرید حجم اضافه"],
            ["🔙 بازگشت به منوی مدیریت فروشگاه"]
        ]
    
    async def _update_setting(self, update, context, new_value, old_value, 
                            update_method, field_name, format_func=None, error_msg=None):
        """متد عمومی برای بروزرسانی تنظیمات با کاهش تکرار کد"""
        # Save in user data
        context.user_data['extra_volume_settings'][field_name] = new_value
        
        # Save to database
        category_id = context.user_data['extra_volume_settings']['category_id']
        success = update_method(category_id, new_value)
        
        if success:
            old_display = format_func(old_value) if format_func else old_value
            new_display = format_func(new_value) if format_func else new_value
            
            await update.message.reply_text(
                f"✅ {error_msg} با موفقیت از {old_display} به {new_display} تغییر یافت."
            )
        else:
            await update.message.reply_text(
                f"❌ خطا در بروزرسانی {error_msg}. لطفاً بعداً دوباره تلاش کنید."
            )
            # Revert the change in user data
            context.user_data['extra_volume_settings'][field_name] = old_value
        
        return await self.show_settings_menu(update, context)
        
    async def start_scene(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start the scene with category selection"""
        # Initialize user data
        context.user_data['in_conversation'] = True
        context.user_data['extra_volume_settings'] = {}
        logger.info(f"Starting extra_volume_settings scene for user {update.effective_user.id}")
        
        # Get all categories
        categories = self.shop_service.get_all_categories()
        
        if not categories or len(categories) == 0:
            await update.message.reply_text("❌ هیچ دسته‌بندی یافت نشد. ابتدا یک دسته‌بندی اضافه کنید.")
            context.user_data['in_conversation'] = False
            await self.shop_menu.show(update, context)
            return ConversationHandler.END
        
        # Create inline keyboard with categories
        keyboard = []
        for category in categories:
            # Safely get category ID and name with fallbacks
            category_id = category.get('id', 0)
            category_name = category.get('name', 'Unnamed')
            
            keyboard.append([
                InlineKeyboardButton(category_name, callback_data=f"evs_cat_{category_id}")
            ])
        
        # Add back button
        keyboard.append([
            InlineKeyboardButton("🔙 بازگشت", callback_data="cancel_evs")
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "➕ تنظیمات حجم اضافه\n\n"
            "📌 لطفاً یک دسته‌بندی انتخاب کنید:",
            reply_markup=reply_markup
        )
        
        return SELECT_CATEGORY
        
    async def select_category(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle category selection"""
        query = update.callback_query
        await query.answer()
        
        callback_data = query.data
        
        # Handle cancel
        if callback_data == "cancel_evs":
            context.user_data['in_conversation'] = False
            # متن پیام را ویرایش کن
            await query.edit_message_text("بازگشت به منوی فروشگاه...")
            
            # دریافت chat_id و user_id برای استفاده در show_with_chat_id
            chat_id = update.effective_chat.id
            user_id = update.effective_user.id
            
            # استفاده از show_with_chat_id به جای show
            await self.shop_menu.show_with_chat_id(
                chat_id=chat_id,
                context=context,
                user_id=user_id,
                user_states_dict=context.user_data.get('user_states', {}),
                target_state="shop_management"
            )
            return ConversationHandler.END
        
        # Extract category ID
        category_id = int(callback_data.split('_')[2])
        
        # Get category details
        categories = self.shop_service.get_all_categories()
        selected_category = next((c for c in categories if c['id'] == category_id), None)
        
        if not selected_category:
            await query.edit_message_text(
                "❌ دسته‌بندی انتخاب شده معتبر نیست.\n"
                "لطفاً دوباره تلاش کنید."
            )
            context.user_data['in_conversation'] = False
            return ConversationHandler.END
        
        # Save category in user data
        context.user_data['extra_volume_settings']['category_id'] = category_id
        context.user_data['extra_volume_settings']['category_name'] = selected_category['name']
        
        # Get current extra volume settings for this category
        settings = self.shop_service.get_extra_volume_settings(category_id)
        
        if settings:
            # Save current settings
            context.user_data['extra_volume_settings']['price_per_gb'] = settings['price_per_gb']
            context.user_data['extra_volume_settings']['min_volume'] = settings['min_volume']
            context.user_data['extra_volume_settings']['max_volume'] = settings['max_volume']
            context.user_data['extra_volume_settings']['is_enabled'] = settings['is_enabled']
        else:
            # Default settings
            context.user_data['extra_volume_settings']['price_per_gb'] = 10000  # Default: 10,000 tomans
            context.user_data['extra_volume_settings']['min_volume'] = 1
            context.user_data['extra_volume_settings']['max_volume'] = 100
            context.user_data['extra_volume_settings']['is_enabled'] = True
        
        return await self.show_settings_menu(update, context)
    
    async def show_settings_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show the settings menu with physical buttons"""
        if update.callback_query:
            query = update.callback_query
            message = query.message
        else:
            message = update.message
        
        # استفاده از متدهای کمکی برای کاهش تکرار کد
        keyboard = self._get_settings_keyboard()
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        status_text = self._get_settings_status_text(context)
        
        if update.callback_query:
            # فقط متن را ویرایش کن
            await message.edit_text(status_text)
            # یک پیام جدید با کیبورد ارسال کن
            chat_id = message.chat_id
            await context.bot.send_message(chat_id=chat_id, text="یک عملیات را انتخاب کنید", reply_markup=reply_markup)
        else:
            await message.reply_text(status_text, reply_markup=reply_markup)
        
        return SHOW_MENU
    
    async def handle_menu_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle menu selection"""
        message_text = update.message.text
        
        # کیبورد برگشت به منوی تنظیمات
        back_keyboard = [["🔙 بازگشت به منوی تنظیمات حجم اضافه"]]
        back_markup = ReplyKeyboardMarkup(back_keyboard, resize_keyboard=True)
        
        # Handle options
        if message_text == "🔙 بازگشت به منوی مدیریت فروشگاه":
            context.user_data['in_conversation'] = False
            await self.shop_menu.show(update, context)
            return ConversationHandler.END
        
        elif message_text == "💰 تنظیم قیمت هر گیگابایت":
            price_per_gb = context.user_data['extra_volume_settings']['price_per_gb']
            await update.message.reply_text(
                f"قیمت فعلی هر گیگابایت: {price_per_gb:,} تومان\n\n"
                f"لطفاً قیمت جدید هر گیگابایت را به تومان وارد کنید:",
                reply_markup=back_markup
            )
            return SET_PRICE
        
        # Handle set minimum volume
        elif message_text == "⬇️ تنظیم حداقل حجم خرید":
            min_volume = context.user_data['extra_volume_settings']['min_volume']
            min_volume_display = self._format_volume_display(min_volume)
            await update.message.reply_text(
                f"حداقل حجم فعلی: {min_volume_display}\n\n"
                f"لطفاً حداقل حجم جدید را به گیگابایت وارد کنید (برای بدون محدودیت عدد 0 را وارد کنید):",
                reply_markup=back_markup
            )
            return SET_MIN_VOLUME
        
        # Handle set maximum volume
        elif message_text == "⬆️ تنظیم حداکثر حجم خرید":
            max_volume = context.user_data['extra_volume_settings']['max_volume']
            max_volume_display = self._format_volume_display(max_volume)
            await update.message.reply_text(
                f"حداکثر حجم فعلی: {max_volume_display}\n\n"
                f"لطفاً حداکثر حجم جدید را به گیگابایت وارد کنید (برای بدون محدودیت عدد 0 را وارد کنید):",
                reply_markup=back_markup
            )
            return SET_MAX_VOLUME
        
        # Handle toggle extra volume status
        elif message_text == "🔄 فعال یا غیرفعال کردن خرید حجم اضافه":
            is_enabled = context.user_data['extra_volume_settings']['is_enabled']
            current_status = "فعال ✅" if is_enabled else "غیرفعال ❌"
            
            # Create inline keyboard for toggle
            keyboard = [
                [InlineKeyboardButton("فعال ✅", callback_data="evs_enable_true")],
                [InlineKeyboardButton("غیرفعال ❌", callback_data="evs_enable_false")],
                [InlineKeyboardButton("🔙 بازگشت", callback_data="evs_back_to_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                f"وضعیت فعلی خرید حجم اضافه: {current_status}\n\n"
                f"وضعیت جدید را انتخاب کنید:",
                reply_markup=reply_markup
            )
            
            return SHOW_MENU
        
        else:
            await update.message.reply_text("لطفاً یکی از گزینه‌های منو را انتخاب کنید.")
            return SHOW_MENU
    
    async def set_price(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle setting the price per GB"""
        # بررسی اگر کاربر می‌خواهد به منوی قبلی برگردد
        if update.message.text == "🔙 بازگشت به منوی تنظیمات حجم اضافه":
            return await self.show_settings_menu(update, context)
            
        try:
            # Remove commas if present
            price_text = update.message.text.replace(',', '')
            price_per_gb = int(price_text)
            
            if price_per_gb < 0:
                await update.message.reply_text("❌ قیمت باید عدد مثبت باشد. لطفاً دوباره تلاش کنید:")
                return SET_PRICE
            
            # استفاده از متد کمکی برای بروزرسانی تنظیمات
            old_price = context.user_data['extra_volume_settings']['price_per_gb']
            return await self._update_setting(
                update, context, 
                price_per_gb, old_price,
                self.shop_service.set_extra_volume_price, 
                'price_per_gb',
                lambda x: f"{x:,} تومان",
                "قیمت هر گیگابایت"
            )
            
        except ValueError:
            await update.message.reply_text(
                "❌ قیمت نامعتبر. لطفاً یک عدد معتبر وارد کنید:"
            )
            return SET_PRICE
    
    async def set_min_volume(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle setting the minimum volume"""
        # بررسی اگر کاربر می‌خواهد به منوی قبلی برگردد
        if update.message.text == "🔙 بازگشت به منوی تنظیمات حجم اضافه":
            return await self.show_settings_menu(update, context)
            
        try:
            min_volume = int(update.message.text)
            
            if min_volume < 0:
                await update.message.reply_text("❌ حداقل حجم باید عدد غیرمنفی باشد. لطفاً دوباره تلاش کنید:")
                return SET_MIN_VOLUME
            
            # استفاده از متد کمکی برای بروزرسانی تنظیمات
            old_min = context.user_data['extra_volume_settings']['min_volume']
            return await self._update_setting(
                update, context, 
                min_volume, old_min,
                self.shop_service.set_extra_volume_min, 
                'min_volume',
                self._format_volume_display,
                "حداقل حجم"
            )
            
        except ValueError:
            await update.message.reply_text(
                "❌ حجم نامعتبر. لطفاً یک عدد معتبر وارد کنید:"
            )
            return SET_MIN_VOLUME
    
    async def set_max_volume(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle setting the maximum volume"""
        # بررسی اگر کاربر می‌خواهد به منوی قبلی برگردد
        if update.message.text == "🔙 بازگشت به منوی تنظیمات حجم اضافه":
            return await self.show_settings_menu(update, context)
            
        try:
            max_volume = int(update.message.text)
            
            if max_volume < 0:
                await update.message.reply_text("❌ حداکثر حجم باید عدد غیرمنفی باشد. لطفاً دوباره تلاش کنید:")
                return SET_MAX_VOLUME
            
            # استفاده از متد کمکی برای بروزرسانی تنظیمات
            old_max = context.user_data['extra_volume_settings']['max_volume']
            return await self._update_setting(
                update, context, 
                max_volume, old_max,
                self.shop_service.set_extra_volume_max, 
                'max_volume',
                self._format_volume_display,
                "حداکثر حجم"
            )
            
        except ValueError:
            await update.message.reply_text(
                "❌ حجم نامعتبر. لطفاً یک عدد معتبر وارد کنید:"
            )
            return SET_MAX_VOLUME
    
    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Cancel the conversation"""
        # Clean up user data
        if 'extra_volume_settings' in context.user_data:
            del context.user_data['extra_volume_settings']
        
        # Reset conversation flag
        context.user_data['in_conversation'] = False
        
        # Get chat_id and user_id
        chat_id = update.effective_chat.id
        user_id = update.effective_user.id
        
        # Send cancellation message
        await update.effective_message.reply_text("⛔ عملیات لغو شد.")
        
        # Return to shop menu with better state management - استفاده از target_state="shop_management"
        # برای نمایش مستقیم منوی مدیریت فروشگاه بدون نمایش منوی مدیریت
        await self.shop_menu.show_with_chat_id(
            chat_id=chat_id,
            context=context,
            user_id=user_id,
            user_states_dict=context.user_data.get('user_states', {}),
            target_state="shop_management"
        )
        return ConversationHandler.END
    
    async def toggle_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle toggling the extra volume status"""
        query = update.callback_query
        await query.answer()
        
        callback_data = query.data
        
        # اگر کاربر روی دکمه بازگشت کلیک کرده باشد
        if callback_data == "evs_back_to_menu":
            # پیام را حذف کنیم
            try:
                await query.delete_message()
            except Exception as e:
                logger.error(f"Error deleting message: {e}")
                
            # منوی تنظیمات را نمایش دهیم - اما از یک پیام جدید استفاده کنیم
            chat_id = update.effective_chat.id
            
            # استفاده از متدهای کمکی برای کاهش تکرار کد
            keyboard = self._get_settings_keyboard()
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            status_text = self._get_settings_status_text(context)
            
            # ارسال پیام جدید
            await context.bot.send_message(
                chat_id=chat_id,
                text=status_text,
                reply_markup=reply_markup
            )
            
            return SHOW_MENU
            
        is_enabled = callback_data == "evs_enable_true"
        
        # Get category ID from user data
        category_id = context.user_data['extra_volume_settings']['category_id']
        
        # Save old status for comparison
        old_status = context.user_data['extra_volume_settings']['is_enabled']
        
        # Update user data
        context.user_data['extra_volume_settings']['is_enabled'] = is_enabled
        
        # Save to database
        success = self.shop_service.set_extra_volume_enabled(category_id, is_enabled)
        
        if success:
            old_status_text = "فعال ✅" if old_status else "غیرفعال ❌"
            new_status_text = "فعال ✅" if is_enabled else "غیرفعال ❌"
            
            await query.edit_message_text(
                f"✅ وضعیت خرید حجم اضافه با موفقیت از {old_status_text} به {new_status_text} تغییر یافت."
            )
        else:
            await query.edit_message_text(
                "❌ خطا در بروزرسانی وضعیت. لطفاً بعداً دوباره تلاش کنید."
            )
            # Revert the change in user data
            context.user_data['extra_volume_settings']['is_enabled'] = old_status
        
        # Show updated settings menu
        return await self.show_settings_menu(update, context)
    
    def get_handler(self):
        """Return the ConversationHandler for this scene"""
        return ConversationHandler(
            entry_points=[MessageHandler(filters.Regex("^➕ تنظیم قیمت حجم اضافه$"), self.start_scene)],
            states={
                SELECT_CATEGORY: [
                    CallbackQueryHandler(self.select_category, pattern=r'^evs_cat_|^cancel_evs')
                ],
                SHOW_MENU: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_menu_selection),
                    CallbackQueryHandler(self.toggle_status, pattern=r'^evs_enable_|^evs_back_to_menu')
                ],
                SET_PRICE: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.set_price)
                ],
                SET_MIN_VOLUME: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.set_min_volume)
                ],
                SET_MAX_VOLUME: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.set_max_volume)
                ]
            },
            fallbacks=[
                CommandHandler("cancel", self.cancel),
                MessageHandler(filters.Regex("^🔙 بازگشت به منوی مدیریت فروشگاه$"), self.cancel)
            ],
            name="extra_volume_settings_conversation",
            persistent=False
        ) 