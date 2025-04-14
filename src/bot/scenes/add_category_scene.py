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
from src.bot.menus.add_category_menu import AddCategoryMenu

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Define states directly instead of importing from index.py
ADD_CATEGORY_NAME, ADD_SELECT_PANELS, ADD_SELECT_INBOUNDS, ADD_CONFIRMATION = range(4)

class AddCategoryScene:
    """Scene for adding a new category"""
    
    def __init__(self):
        self.shop_service = ShopService()
        self.shop_menu = ShopMenu()
        self.admin_menu = AdminMenu()
        self.add_category_menu = AddCategoryMenu()
    
    def get_handler(self):
        """Get the conversation handler for this scene"""
        return ConversationHandler(
            entry_points=[],  # This will be set by the caller
            states={
                ADD_CATEGORY_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.category_name)],
                ADD_SELECT_PANELS: [CallbackQueryHandler(self.select_panels)],
                ADD_SELECT_INBOUNDS: [CallbackQueryHandler(self.select_inbounds)],
                ADD_CONFIRMATION: [CallbackQueryHandler(self.confirmation)],
            },
            fallbacks=[CommandHandler("cancel", self.cancel)],
        )
    
    async def start_scene(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start the scene"""
        # Initialize user data
        context.user_data['selected_panels'] = []
        context.user_data['selected_inbounds'] = []
        context.user_data['available_inbounds'] = {}
        
        # Set conversation flag to prevent other handlers from running
        context.user_data['in_conversation'] = True
        logger.info(f"Starting add_category scene for user {update.effective_user.id}")
        logger.info(f"Current conversation state: ADD_CATEGORY_NAME ({ADD_CATEGORY_NAME})")
        
        # تنظیم کیبورد با دکمه بازگشت بدون ارسال پیام اضافی
        self.add_category_menu.setup_menu()
        keyboard_markup = self.add_category_menu.create_keyboard_markup()
        
        # ارسال پیام اصلی با کیبورد بازگشت
        await update.message.reply_text(
            "🛒 اضافه کردن دسته بندی\n\n"
            "📌 نام دسته بندی را ارسال کنید",
            reply_markup=keyboard_markup
        )
        
        return ADD_CATEGORY_NAME
    
    async def category_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle category name entry"""
        try:
            category_name = update.message.text
            logger.info(f"Received category name: '{category_name}' from user {update.effective_user.id}")
            
            # Check if user is trying to go back
            if category_name == "🔙 بازگشت به بخش فروشگاه":
                context.user_data['in_conversation'] = False
                await update.message.reply_text("❌ عملیات لغو شد.")
                await self.shop_menu.show(update, context)
                return ConversationHandler.END
            
            # Show processing message to let user know we're working on it
            processing_message = await update.message.reply_text("⏳ در حال پردازش...")
            
            # Save category name in user data
            context.user_data['category_name'] = category_name
            
            # Get all panels
            logger.info("Fetching panels for selection...")
            panels = self.shop_service.get_all_panels()
            logger.info(f"Fetched panels: {panels}")
            
            if not panels or len(panels) == 0:
                logger.warning("No panels found!")
                await processing_message.edit_text("❌ هیچ پنلی یافت نشد. ابتدا یک پنل اضافه کنید.")
                context.user_data['in_conversation'] = False
                await self.shop_menu.show(update, context)
                return ConversationHandler.END
            
            # Create inline keyboard with panels
            keyboard = []
            for panel in panels:
                # Safely get panel ID and name with fallbacks
                panel_id = panel.get('id', 0)
                panel_name = panel.get('name', 'بدون نام')
                logger.info(f"Adding panel to keyboard: ID={panel_id}, Name={panel_name}")
                
                checkbox = "☑️" if panel_id in context.user_data['selected_panels'] else "⬜️"
                keyboard.append([
                    InlineKeyboardButton(f"{checkbox} {panel_name}", callback_data=f"panel_{panel_id}")
                ])
            
            # Add confirm button at the bottom
            keyboard.append([InlineKeyboardButton("✅ تایید پنل ها", callback_data="confirm_panels")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Remove processing message and send the actual selection keyboard
            await processing_message.delete()
            
            try:
                sent_message = await update.message.reply_text(
                    "📌 پنل های مورد نظر را انتخاب کنید:\n"
                    "می‌توانید چندین پنل را انتخاب کنید.",
                    reply_markup=reply_markup
                )
                logger.info(f"Panel selection keyboard sent successfully: {sent_message.message_id}")
                return ADD_SELECT_PANELS
            except Exception as e:
                logger.error(f"Error sending panel selection keyboard: {e}")
                await update.message.reply_text(f"❌ خطا در نمایش پنل‌ها: {str(e)}")
                context.user_data['in_conversation'] = False
                await self.shop_menu.show(update, context)
                return ConversationHandler.END
        
        except Exception as e:
            logger.error(f"Error in category_name: {e}")
            await update.message.reply_text(
                "❌ خطایی در پردازش نام دسته‌بندی رخ داد.\n"
                "لطفاً دوباره تلاش کنید یا با پشتیبانی تماس بگیرید."
            )
            # Log detailed error
            logger.error(traceback.format_exc())
            
            # Reset conversation
            context.user_data['in_conversation'] = False
            await self.shop_menu.show(update, context)
            return ConversationHandler.END
    
    async def select_panels(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle panel selection"""
        query = update.callback_query
        await query.answer()
        
        callback_data = query.data
        
        if callback_data == "confirm_panels":
            # User confirmed panel selection
            if not context.user_data['selected_panels']:
                # No panels selected
                await query.edit_message_text(
                    "❌ حداقل یک پنل باید انتخاب شود.\n"
                    "لطفاً دوباره تلاش کنید."
                )
                return ConversationHandler.END
            
            # Get available inbounds for selected panels
            panels = self.shop_service.get_all_panels()
            available_inbounds = {}
            selected_panel_names = []
            
            for panel in panels:
                if panel['id'] in context.user_data['selected_panels']:
                    selected_panel_names.append(panel['name'])
                    # Get inbounds for this panel
                    inbounds = self.shop_service.get_panel_inbounds(panel)
                    if inbounds:
                        available_inbounds[panel['id']] = inbounds
            
            if not available_inbounds:
                await query.edit_message_text(
                    "❌ هیچ اینباندی در پنل‌های انتخاب شده یافت نشد.\n"
                    "لطفاً پنل‌های دیگری انتخاب کنید یا اینباندها را در پنل بررسی کنید."
                )
                return ConversationHandler.END
            
            # Save available inbounds for later use
            context.user_data['available_inbounds'] = available_inbounds
            
            # Create keyboard for inbound selection
            keyboard = []
            
            # Group inbounds by panel
            for panel_id, inbounds in available_inbounds.items():
                panel_name = next((p['name'] for p in panels if p['id'] == panel_id), "پنل")
                
                # Add panel name as header
                keyboard.append([InlineKeyboardButton(f"📌 {panel_name}", callback_data=f"panel_header_{panel_id}")])
                
                # Add inbounds for this panel
                for inbound in inbounds:
                    port = inbound.get('port', 'نامشخص')
                    protocol = inbound.get('protocol', 'نامشخص')
                    remark = inbound.get('remark', 'بدون توضیحات')
                    
                    inbound_key = f"{panel_id}_{inbound.get('id', '0')}"
                    checkbox = "☑️" if inbound_key in context.user_data['selected_inbounds'] else "⬜️"
                    
                    keyboard.append([
                        InlineKeyboardButton(
                            f"{checkbox} پورت: {port} | {protocol} | {remark}", 
                            callback_data=f"inbound_{inbound_key}"
                        )
                    ])
            
            # Add confirm button
            keyboard.append([InlineKeyboardButton("✅ تایید اینباند ها", callback_data="confirm_inbounds")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                f"📌 انتخاب اینباندها برای دسته بندی «{context.user_data['category_name']}»\n\n"
                f"پنل های انتخاب شده: {', '.join(selected_panel_names)}\n\n"
                f"لطفاً اینباندهای مورد نظر را انتخاب کنید:",
                reply_markup=reply_markup
            )
            
            return ADD_SELECT_INBOUNDS
            
        else:
            # User selected/deselected a panel
            panel_id = int(callback_data.split('_')[1])
            
            # Toggle panel selection
            if panel_id in context.user_data['selected_panels']:
                context.user_data['selected_panels'].remove(panel_id)
            else:
                context.user_data['selected_panels'].append(panel_id)
            
            # Update keyboard
            panels = self.shop_service.get_all_panels()
            keyboard = []
            
            for panel in panels:
                checkbox = "☑️" if panel['id'] in context.user_data['selected_panels'] else "⬜️"
                keyboard.append([
                    InlineKeyboardButton(f"{checkbox} {panel['name']}", callback_data=f"panel_{panel['id']}")
                ])
            
            keyboard.append([InlineKeyboardButton("✅ تایید پنل ها", callback_data="confirm_panels")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                "📌 پنل های مورد نظر را انتخاب کنید:\n"
                "می‌توانید چندین پنل را انتخاب کنید.",
                reply_markup=reply_markup
            )
            
            return ADD_SELECT_PANELS
    
    async def select_inbounds(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle inbound selection"""
        query = update.callback_query
        await query.answer()
        
        callback_data = query.data
        
        if callback_data == "confirm_inbounds":
            # User confirmed inbound selection
            if not context.user_data['selected_inbounds']:
                await query.edit_message_text(
                    "❌ حداقل یک اینباند باید انتخاب شود.\n"
                    "لطفاً دوباره تلاش کنید."
                )
                return ConversationHandler.END
            
            # Process selected inbounds to extract port numbers
            inbound_ports = []
            for inbound_key in context.user_data['selected_inbounds']:
                panel_id, inbound_id = map(int, inbound_key.split('_'))
                
                # Find the inbound in available_inbounds
                for inbound in context.user_data['available_inbounds'].get(panel_id, []):
                    if inbound.get('id') == inbound_id:
                        port = inbound.get('port')
                        if port and port not in inbound_ports:
                            inbound_ports.append(port)
            
            # Try to add the category to database
            try:
                # Pass both the panel IDs and inbound ports
                category_id = self.shop_service.add_category(
                    context.user_data['category_name'],
                    "",  # Empty description for now
                    context.user_data['selected_panels'],
                    inbound_ports
                )
                
                # Get panel names for display
                panels = self.shop_service.get_all_panels()
                selected_panel_names = [
                    p['name'] for p in panels if p['id'] in context.user_data['selected_panels']
                ]
                
                # Format inbound information with more details
                inbound_details = []
                for inbound_key in context.user_data['selected_inbounds']:
                    panel_id, inbound_id = map(int, inbound_key.split('_'))
                    
                    # Find the inbound in available_inbounds
                    for inbound in context.user_data['available_inbounds'].get(panel_id, []):
                        if inbound.get('id') == inbound_id:
                            port = inbound.get('port', 'نامشخص')
                            protocol = inbound.get('protocol', 'نامشخص')
                            remark = inbound.get('remark', 'بدون توضیحات')
                            inbound_details.append(f"پورت {port} | {remark} | {protocol}")
                
                await query.edit_message_text(
                    f"✅ دسته بندی «{context.user_data['category_name']}» با موفقیت اضافه گردید.\n\n"
                    f"پنل‌های انتخاب شده: {', '.join(selected_panel_names)}\n"
                    f"اینباندهای انتخاب شده:\n" + "\n".join(inbound_details)
                )
                
                # Clean up user data
                if 'category_name' in context.user_data:
                    del context.user_data['category_name']
                if 'selected_panels' in context.user_data:
                    del context.user_data['selected_panels']
                if 'selected_inbounds' in context.user_data:
                    del context.user_data['selected_inbounds']
                if 'available_inbounds' in context.user_data:
                    del context.user_data['available_inbounds']
                
                context.user_data['in_conversation'] = False
                
                return ConversationHandler.END
                
            except Exception as e:
                logger.error(f"Error adding category: {e}")
                await query.edit_message_text(
                    f"❌ خطا در افزودن دسته بندی: {str(e)}\n"
                    f"لطفاً دوباره تلاش کنید."
                )
                return ConversationHandler.END
            
        elif callback_data.startswith("panel_header_"):
            # This is just a header, do nothing
            return ADD_SELECT_INBOUNDS
            
        elif callback_data.startswith("inbound_"):
            # User selected/deselected an inbound
            inbound_key = callback_data.split('_', 1)[1]
            
            # Toggle inbound selection
            if inbound_key in context.user_data['selected_inbounds']:
                context.user_data['selected_inbounds'].remove(inbound_key)
            else:
                context.user_data['selected_inbounds'].append(inbound_key)
            
            # Get panels for panel names
            panels = self.shop_service.get_all_panels()
            
            # Create updated keyboard
            keyboard = []
            
            # Add panel headers and inbounds
            for panel_id, inbounds in context.user_data['available_inbounds'].items():
                panel_name = next((p['name'] for p in panels if p['id'] == panel_id), "پنل")
                
                # Add panel name as header
                keyboard.append([InlineKeyboardButton(f"📌 {panel_name}", callback_data=f"panel_header_{panel_id}")])
                
                # Add inbounds for this panel
                for inbound in inbounds:
                    port = inbound.get('port', 'نامشخص')
                    protocol = inbound.get('protocol', 'نامشخص')
                    remark = inbound.get('remark', 'بدون توضیحات')
                    
                    ib_key = f"{panel_id}_{inbound.get('id', '0')}"
                    checkbox = "☑️" if ib_key in context.user_data['selected_inbounds'] else "⬜️"
                    
                    keyboard.append([
                        InlineKeyboardButton(
                            f"{checkbox} پورت: {port} | {protocol} | {remark}", 
                            callback_data=f"inbound_{ib_key}"
                        )
                    ])
            
            # Add confirm button
            keyboard.append([InlineKeyboardButton("✅ تایید اینباند ها", callback_data="confirm_inbounds")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Get selected panel names for display
            selected_panel_names = [
                p['name'] for p in panels if p['id'] in context.user_data['selected_panels']
            ]
            
            await query.edit_message_text(
                f"📌 انتخاب اینباندها برای دسته بندی «{context.user_data['category_name']}»\n\n"
                f"پنل های انتخاب شده: {', '.join(selected_panel_names)}\n\n"
                f"لطفاً اینباندهای مورد نظر را انتخاب کنید:",
                reply_markup=reply_markup
            )
            
            return ADD_SELECT_INBOUNDS
    
    async def confirmation(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle final confirmation"""
        # This state is not used in current flow but kept for future expansion
        query = update.callback_query
        await query.answer()
        
        return ConversationHandler.END
    
    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Cancel the conversation"""
        # Clean up user data
        if 'category_name' in context.user_data:
            del context.user_data['category_name']
        if 'selected_panels' in context.user_data:
            del context.user_data['selected_panels']
        if 'selected_inbounds' in context.user_data:
            del context.user_data['selected_inbounds']
        if 'available_inbounds' in context.user_data:
            del context.user_data['available_inbounds']
        
        # Reset conversation flag
        context.user_data['in_conversation'] = False
        
        await update.message.reply_text("❌ عملیات لغو شد.")
        # Return to shop menu
        await self.shop_menu.show(update, context)
        return ConversationHandler.END 