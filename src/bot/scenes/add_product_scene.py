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
from src.bot.menus.add_product_menu import AddProductMenu

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Define states
(
    PRODUCT_NAME, 
    SELECT_CATEGORY, 
    DATA_LIMIT, 
    DURATION, 
    PRICE, 
    CONFIRMATION
) = range(6)

class AddProductScene:
    """Scene for adding a new product"""
    
    def __init__(self):
        self.shop_service = ShopService()
        self.shop_menu = ShopMenu()
        self.admin_menu = AdminMenu()
        self.add_product_menu = AddProductMenu()
    
    def get_handler(self):
        """Get the conversation handler for this scene"""
        return ConversationHandler(
            entry_points=[],  # This will be set by the caller
            states={
                PRODUCT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.product_name)],
                SELECT_CATEGORY: [CallbackQueryHandler(self.select_category)],
                DATA_LIMIT: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.data_limit)],
                DURATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.duration)],
                PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.price)],
                CONFIRMATION: [CallbackQueryHandler(self.confirmation)],
            },
            fallbacks=[CommandHandler("cancel", self.cancel)],
        )
    
    async def start_scene(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start the scene"""
        # Initialize user data
        context.user_data['in_conversation'] = True
        logger.info(f"Starting add_product scene for user {update.effective_user.id}")
        
        # تنظیم کیبورد با دکمه بازگشت بدون ارسال پیام اضافی
        self.add_product_menu.setup_menu()
        keyboard_markup = self.add_product_menu.create_keyboard_markup()
        
        # ارسال پیام اصلی با کیبورد بازگشت
        await update.message.reply_text(
            "🛍 اضافه کردن محصول\n\n"
            "📌 ابتدا نام اشتراک خود را ارسال نمایید\n"
            "⚠️ نکات هنگام وارد کردن نام محصول:\n"
            "• در کنار نام اشتراک حتما قیمت اشتراک را هم وارد کنید.\n"
            "• در کنار نام اشتراک حتما زمان اشتراک را هم وارد کنید.\n\n"
            "به عنوان مثال: ۱ ماه ۲۰۰ گیگ ۱۵۰ هزار تومان",
            reply_markup=keyboard_markup
        )
        
        return PRODUCT_NAME
    
    async def product_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle product name entry"""
        try:
            product_name = update.message.text
            logger.info(f"Received product name: '{product_name}' from user {update.effective_user.id}")
            
            # Check if user is trying to go back
            if product_name == "🔙 بازگشت به بخش فروشگاه":
                context.user_data['in_conversation'] = False
                await update.message.reply_text("❌ عملیات لغو شد.")
                await self.shop_menu.show(update, context)
                return ConversationHandler.END
            
            # Save product name in user data
            context.user_data['product_name'] = product_name
            
            # Get all categories
            categories = self.shop_service.get_all_categories()
            
            if not categories or len(categories) == 0:
                await update.message.reply_text(
                    "❌ هیچ دسته بندی یافت نشد. ابتدا یک دسته بندی اضافه کنید."
                )
                context.user_data['in_conversation'] = False
                await self.shop_menu.show(update, context)
                return ConversationHandler.END
            
            # Create inline keyboard with categories
            keyboard = []
            for category in categories:
                # Safely get category ID and name with fallbacks
                category_id = category.get('id', 0)
                category_name = category.get('name', 'بدون نام')
                
                keyboard.append([
                    InlineKeyboardButton(category_name, callback_data=f"category_{category_id}")
                ])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                "📌 دسته بندی محصول را انتخاب کنید:",
                reply_markup=reply_markup
            )
            
            return SELECT_CATEGORY
            
        except Exception as e:
            logger.error(f"Error in product_name: {e}")
            await update.message.reply_text(
                "❌ خطایی در پردازش نام محصول رخ داد.\n"
                "لطفاً دوباره تلاش کنید یا با پشتیبانی تماس بگیرید."
            )
            # Log detailed error
            logger.error(traceback.format_exc())
            
            # Reset conversation
            context.user_data['in_conversation'] = False
            await self.shop_menu.show(update, context)
            return ConversationHandler.END
    
    async def select_category(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle category selection"""
        query = update.callback_query
        await query.answer()
        
        callback_data = query.data
        category_id = int(callback_data.split('_')[1])
        
        # Get category details
        categories = self.shop_service.get_all_categories()
        selected_category = next((c for c in categories if c['id'] == category_id), None)
        
        if not selected_category:
            await query.edit_message_text(
                "❌ دسته بندی انتخاب شده معتبر نیست.\n"
                "لطفاً دوباره تلاش کنید."
            )
            context.user_data['in_conversation'] = False
            return ConversationHandler.END
        
        # Save category in user data
        context.user_data['category_id'] = category_id
        context.user_data['category_name'] = selected_category['name']
        
        await query.edit_message_text(
            f"✅ دسته بندی انتخاب شده: {selected_category['name']}\n\n"
            f"حجم اشتراک را ارسال کنید\n"
            f"توجه واحد حجم گیگابایت است\n\n"
            f"اگر میخواهید حجم نامحدود باشد عدد 0 ارسال کنید"
        )
        
        return DATA_LIMIT
    
    async def data_limit(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle data limit entry"""
        try:
            data_limit_text = update.message.text.strip()
            
            # Check if user is trying to go back
            if data_limit_text == "🔙 بازگشت به بخش فروشگاه":
                context.user_data['in_conversation'] = False
                await self.shop_menu.show(update, context)
                return ConversationHandler.END
            
            # Try to convert to integer
            try:
                data_limit = int(data_limit_text)
                if data_limit < 0:
                    raise ValueError("مقدار حجم نمی‌تواند منفی باشد")
            except ValueError as e:
                await update.message.reply_text(
                    "❌ مقدار وارد شده معتبر نیست. لطفاً یک عدد صحیح وارد کنید."
                )
                return DATA_LIMIT
            
            # Save data limit in user data
            context.user_data['data_limit'] = data_limit
            
            await update.message.reply_text(
                f"✅ حجم اشتراک: {data_limit} گیگابایت\n\n"
                f"زمان اشتراک را وارد نمایید\n"
                f"توجه واحد زمان اشتراک روز است\n"
                f"اگر می خواهید زمان نامحدود باشد عدد 0 را ارسال کنید"
            )
            
            return DURATION
            
        except Exception as e:
            logger.error(f"Error in data_limit: {e}")
            await update.message.reply_text(
                "❌ خطایی در پردازش حجم اشتراک رخ داد.\n"
                "لطفاً دوباره تلاش کنید."
            )
            return DATA_LIMIT
    
    async def duration(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle duration entry"""
        try:
            duration_text = update.message.text.strip()
            
            # Check if user is trying to go back
            if duration_text == "🔙 بازگشت به بخش فروشگاه":
                context.user_data['in_conversation'] = False
                await self.shop_menu.show(update, context)
                return ConversationHandler.END
            
            # Try to convert to integer
            try:
                duration = int(duration_text)
                if duration < 0:
                    raise ValueError("مدت زمان نمی‌تواند منفی باشد")
            except ValueError:
                await update.message.reply_text(
                    "❌ مقدار وارد شده معتبر نیست. لطفاً یک عدد صحیح وارد کنید."
                )
                return DURATION
            
            # Save duration in user data
            context.user_data['duration'] = duration
            
            await update.message.reply_text(
                f"✅ مدت زمان اشتراک: {duration} روز\n\n"
                f"قیمت اشتراک را ارسال کنید.\n"
                f"توجه:\n"
                f"محصول براساس تومان است و قیمت را بدون هیچ کاراکتر اضافی ارسال نمایید."
            )
            
            return PRICE
            
        except Exception as e:
            logger.error(f"Error in duration: {e}")
            await update.message.reply_text(
                "❌ خطایی در پردازش مدت زمان اشتراک رخ داد.\n"
                "لطفاً دوباره تلاش کنید."
            )
            return DURATION
    
    async def price(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle price entry"""
        try:
            price_text = update.message.text.strip()
            
            # Check if user is trying to go back
            if price_text == "🔙 بازگشت به بخش فروشگاه":
                context.user_data['in_conversation'] = False
                await self.shop_menu.show(update, context)
                return ConversationHandler.END
            
            # Remove any non-numeric characters
            price_digits = ''.join(c for c in price_text if c.isdigit())
            
            if not price_digits:
                await update.message.reply_text(
                    "❌ قیمت وارد شده معتبر نیست. لطفاً فقط اعداد را وارد کنید."
                )
                return PRICE
            
            # Convert to float
            try:
                price = float(price_digits)
                if price < 0:
                    raise ValueError("قیمت نمی‌تواند منفی باشد")
            except ValueError:
                await update.message.reply_text(
                    "❌ قیمت وارد شده معتبر نیست. لطفاً یک عدد صحیح وارد کنید."
                )
                return PRICE
            
            # Save price in user data
            context.user_data['price'] = price
            
            # Try to add the product to the database
            try:
                product_id = self.shop_service.add_product(
                    context.user_data['product_name'],
                    context.user_data['data_limit'],
                    context.user_data['price'],
                    context.user_data['category_id'],
                    context.user_data['duration']
                )
                
                # Format product summary
                data_limit_str = f"{context.user_data['data_limit']} گیگابایت" if context.user_data['data_limit'] > 0 else "نامحدود"
                duration_str = f"{context.user_data['duration']} روز" if context.user_data['duration'] > 0 else "نامحدود"
                price_formatted = '{:,}'.format(int(context.user_data['price']))
                
                await update.message.reply_text(
                    f"✅ محصول با موفقیت ذخیره شد 🥳🎉\n\n"
                    f"📝 نام محصول: {context.user_data['product_name']}\n"
                    f"🏷️ دسته بندی: {context.user_data['category_name']}\n"
                    f"📊 حجم: {data_limit_str}\n"
                    f"⏱️ مدت زمان: {duration_str}\n"
                    f"💰 قیمت: {price_formatted} تومان"
                )
                
                # Clean up user data
                for key in ['product_name', 'category_id', 'category_name', 'data_limit', 'duration', 'price']:
                    if key in context.user_data:
                        del context.user_data[key]
                
                context.user_data['in_conversation'] = False
                
                # نمایش منوی فروشگاه بعد از ذخیره موفق
                await self.shop_menu.show(update, context)
                
                return ConversationHandler.END
                
            except Exception as e:
                logger.error(f"Error adding product: {e}")
                await update.message.reply_text(
                    f"❌ خطا در افزودن محصول: {str(e)}\n"
                    f"لطفاً دوباره تلاش کنید."
                )
                context.user_data['in_conversation'] = False
                await self.shop_menu.show(update, context)
                return ConversationHandler.END
            
        except Exception as e:
            logger.error(f"Error in price: {e}")
            await update.message.reply_text(
                "❌ خطایی در پردازش قیمت اشتراک رخ داد.\n"
                "لطفاً دوباره تلاش کنید."
            )
            return PRICE
    
    async def confirmation(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle final confirmation"""
        # This state is not used in current flow but kept for future expansion
        query = update.callback_query
        await query.answer()
        
        return ConversationHandler.END
    
    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Cancel the conversation"""
        # Clean up user data
        for key in ['product_name', 'category_id', 'category_name', 'data_limit', 'duration', 'price']:
            if key in context.user_data:
                del context.user_data[key]
        
        # Reset conversation flag
        context.user_data['in_conversation'] = False
        
        await update.message.reply_text("❌ عملیات لغو شد.")
        # Return to shop menu
        await self.shop_menu.show(update, context)
        return ConversationHandler.END 