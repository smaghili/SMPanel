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
    SHOW_PRODUCTS,
    CONFIRM_DELETE
) = range(2)

class DeleteProductScene:
    """Scene for deleting products"""
    
    def __init__(self):
        self.shop_service = ShopService()
    
    def get_handler(self):
        """Get the conversation handler for this scene"""
        return ConversationHandler(
            entry_points=[],  # This will be set by the caller
            states={
                SHOW_PRODUCTS: [CallbackQueryHandler(self.handle_selection)],
                CONFIRM_DELETE: [CallbackQueryHandler(self.handle_confirmation)],
            },
            fallbacks=[CommandHandler("cancel", self.cancel)],
        )
    
    async def start_scene(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start the scene"""
        # Initialize user data
        context.user_data['in_conversation'] = True
        context.user_data['selected_products'] = []
        logger.info(f"Starting delete_product scene for user {update.effective_user.id}")
        
        # Get all products
        products = self.shop_service.get_all_products()
        
        if not products or len(products) == 0:
            await update.message.reply_text("❌ هیچ محصولی یافت نشد.")
            context.user_data['in_conversation'] = False
            return ConversationHandler.END
        
        # Create keyboard with products
        keyboard = self._create_products_keyboard(products, context.user_data['selected_products'])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "❌ حذف محصول\n\n"
            "📌 محصولات مورد نظر برای حذف را انتخاب کنید:\n"
            "می‌توانید چندین محصول را انتخاب کنید.",
            reply_markup=reply_markup
        )
        
        return SHOW_PRODUCTS
    
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
        
        if callback_data == "back":
            # Return to shop menu
            context.user_data['in_conversation'] = False
            from src.bot.menus.shop_menu import ShopMenu
            shop_menu = ShopMenu()
            await shop_menu.show(update, context)
            return ConversationHandler.END
            
        elif callback_data == "clear_selection":
            # Clear selected products
            context.user_data['selected_products'] = []
            
            # Update keyboard
            products = self.shop_service.get_all_products()
            keyboard = self._create_products_keyboard(products, context.user_data['selected_products'])
            
            await query.edit_message_text(
                "❌ حذف محصول\n\n"
                "📌 محصولات مورد نظر برای حذف را انتخاب کنید:\n"
                "می‌توانید چندین محصول را انتخاب کنید.",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
            return SHOW_PRODUCTS
            
        elif callback_data == "delete_selected":
            # Show confirmation message
            products = self.shop_service.get_all_products()
            
            # Get names of selected products
            selected_names = []
            for product_id in context.user_data['selected_products']:
                product = next((p for p in products if p['id'] == product_id), None)
                if product:
                    selected_names.append(product['name'])
            
            # Create confirmation keyboard
            keyboard = [
                [
                    InlineKeyboardButton("✅ بله، حذف شود", callback_data="confirm_delete"),
                    InlineKeyboardButton("❌ خیر، انصراف", callback_data="cancel_delete")
                ]
            ]
            
            # ساخت لیست محصولات با شماره‌گذاری
            products_list = "\n".join(f"{i+1}. {name}" for i, name in enumerate(selected_names))
            
            await query.edit_message_text(
                f"⚠️ آیا از حذف {len(selected_names)} محصول زیر اطمینان دارید؟\n\n"
                f"📋 محصولات انتخاب شده:\n{products_list}",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
            return CONFIRM_DELETE
            
        else:
            # Toggle product selection
            try:
                product_id = int(callback_data.split('_')[1])
                
                # Toggle selection
                if product_id in context.user_data['selected_products']:
                    context.user_data['selected_products'].remove(product_id)
                else:
                    context.user_data['selected_products'].append(product_id)
                
                # Update keyboard
                products = self.shop_service.get_all_products()
                keyboard = self._create_products_keyboard(products, context.user_data['selected_products'])
                
                await query.edit_message_text(
                    "❌ حذف محصول\n\n"
                    "📌 محصولات مورد نظر برای حذف را انتخاب کنید:\n"
                    "می‌توانید چندین محصول را انتخاب کنید.",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
                
                return SHOW_PRODUCTS
                
            except Exception as e:
                logger.error(f"Error handling product selection: {e}")
                logger.error(traceback.format_exc())
                
                await query.edit_message_text(
                    "❌ خطا در پردازش انتخاب محصول. لطفاً دوباره تلاش کنید."
                )
                
                context.user_data['in_conversation'] = False
                return ConversationHandler.END
    
    async def handle_confirmation(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle delete confirmation"""
        query = update.callback_query
        await query.answer()
        
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
            
            return SHOW_PRODUCTS
    
    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Cancel the conversation"""
        # Clean up user data
        context.user_data['in_conversation'] = False
        if 'selected_products' in context.user_data:
            del context.user_data['selected_products']
        
        await update.message.reply_text("❌ عملیات لغو شد.")
        
        # Return to shop menu
        from src.bot.menus.shop_menu import ShopMenu
        shop_menu = ShopMenu()
        await shop_menu.show(update, context)
        
        return ConversationHandler.END 