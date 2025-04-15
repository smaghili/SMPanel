#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    CallbackContext
)
import logging
import traceback

from src.services.shop_service import ShopService
from src.bot.menus.shop_menu import ShopMenu
from src.bot.menus.admin_menu import AdminMenu
from src.bot.menus.add_category_menu import AddCategoryMenu
from src.bot.utils.keyboard_helpers import create_checkbox_keyboard, create_grouped_inbound_keyboard

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
        category_name = update.message.text
        
        # Check if user is trying to go back
        if category_name == "🔙 بازگشت به بخش مدیریت":
            # Reset conversation flag
            context.user_data['in_conversation'] = False
            # Go back to shop menu
            await self.shop_menu.show(update, context)
            return ConversationHandler.END
        
        # Check if name is too short
        if len(category_name) < 2:
            await update.message.reply_text(
                "❌ نام دسته بندی باید حداقل 2 کاراکتر باشد."
            )
            return ADD_CATEGORY_NAME
        
        # Store category name
        context.user_data['category_name'] = category_name
        
        # اطمینان از مقداردهی اولیه selected_panels
        context.user_data['selected_panels'] = []
        context.user_data['selected_inbounds'] = []
        
        try:
            # Get all panels
            panels = self.shop_service.get_all_panels()
            
            if not panels:
                await update.message.reply_text(
                    "❌ هیچ پنلی یافت نشد. ابتدا باید حداقل یک پنل اضافه کنید."
                )
                context.user_data['in_conversation'] = False
                await self.shop_menu.show(update, context)
                return ConversationHandler.END
            
            # Create keyboard with panels
            keyboard = []
            
            for panel in panels:
                # Use ⬜️ for unselected panels initially
                keyboard.append([
                    InlineKeyboardButton(f"⬜️ {panel['name']}", callback_data=f"panel_{panel['id']}")
                ])
            
            # Add confirmation button
            keyboard.append([InlineKeyboardButton("✅ تایید پنل ها", callback_data="confirm_panels")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                f"📌 انتخاب پنل‌ها برای دسته بندی «{category_name}»\n\n"
                f"پنل های مورد نظر را انتخاب کنید:\n"
                f"می‌توانید چندین پنل را انتخاب کنید.",
                reply_markup=reply_markup
            )
            
            return ADD_SELECT_PANELS
            
        except Exception as e:
            await update.message.reply_text(
                f"❌ خطا: {str(e)}\n"
                f"لطفاً دوباره تلاش کنید."
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
            if not context.user_data.get('selected_panels', []):
                # No panels selected
                await query.edit_message_text(
                    "❌ حداقل یک پنل باید انتخاب شود.\n"
                    "لطفاً دوباره تلاش کنید."
                )
                return ConversationHandler.END

            # اطمینان از اینکه selected_panels وجود دارد
            if 'selected_panels' not in context.user_data:
                context.user_data['selected_panels'] = []
                
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
                    else:
                        logger.warning(f"No inbounds found for panel {panel['id']} ({panel['name']})")
            
            if not available_inbounds:
                logger.warning(f"No available inbounds found for selected panels: {context.user_data['selected_panels']}")
                await query.edit_message_text(
                    "❌ هیچ اینباندی در پنل‌های انتخاب شده یافت نشد.\n"
                    "لطفاً پنل‌های دیگری انتخاب کنید یا اینباندها را در پنل بررسی کنید."
                )
                return ConversationHandler.END
            
            # Save available inbounds for later use
            context.user_data['available_inbounds'] = available_inbounds
            
            # ساخت کیبورد اینباندها با استفاده از تابع کمکی
            if 'selected_inbounds' not in context.user_data:
                context.user_data['selected_inbounds'] = []
                
            reply_markup = create_grouped_inbound_keyboard(
                panel_inbounds_dict=available_inbounds,
                panel_dict=panels,
                selected_inbounds=context.user_data.get('selected_inbounds', [])
            )
            
            await query.edit_message_text(
                f"📌 انتخاب اینباندها برای دسته بندی «{context.user_data['category_name']}»\n\n"
                f"پنل های انتخاب شده: {', '.join(selected_panel_names)}\n\n"
                f"لطفاً اینباندهای مورد نظر را انتخاب کنید:",
                reply_markup=reply_markup
            )
            
            return ADD_SELECT_INBOUNDS
            
        # اضافه کردن شرط برای 'panel_list' برای جلوگیری از خطا
        elif callback_data == "panel_list":
            # کاربر دکمه برگشت به لیست پنل ها را زده است - به منوی اصلی برگردیم
            await query.edit_message_text("عملیات انتخاب پنل لغو شد.")
            # برگشت به منوی فروشگاه
            await self.shop_menu.show(update, context)
            return ConversationHandler.END
            
        elif callback_data.startswith("panel_"):
            # User selected/deselected a panel
            try:
                panel_id = int(callback_data.split('_')[1])
                
                # اطمینان از اینکه selected_panels وجود دارد
                if 'selected_panels' not in context.user_data:
                    context.user_data['selected_panels'] = []
                
                # Toggle panel selection
                if panel_id in context.user_data['selected_panels']:
                    context.user_data['selected_panels'].remove(panel_id)
                    logger.info(f"Removed panel {panel_id} from selection, now have {context.user_data['selected_panels']}")
                else:
                    context.user_data['selected_panels'].append(panel_id)
                    logger.info(f"Added panel {panel_id} to selection, now have {context.user_data['selected_panels']}")
                
                # استفاده از تابع کمکی برای ساخت کیبورد
                panels = self.shop_service.get_all_panels()
                
                # تابع بررسی انتخاب پنل
                is_panel_selected = lambda panel_id: panel_id in context.user_data['selected_panels']
                
                reply_markup = create_checkbox_keyboard(
                    items=panels,
                    is_selected_callback=is_panel_selected,
                    item_callback_prefix="panel_",
                    confirm_text="✅ تایید پنل ها",
                    confirm_callback="confirm_panels"
                )
                
                await query.edit_message_text(
                    f"📌 انتخاب پنل‌ها برای دسته بندی «{context.user_data['category_name']}»\n\n"
                    f"پنل های مورد نظر را انتخاب کنید:\n"
                    f"می‌توانید چندین پنل را انتخاب کنید.",
                    reply_markup=reply_markup
                )
                
                return ADD_SELECT_PANELS
            except ValueError as e:
                logger.error(f"Error parsing panel_id from {callback_data}: {e}")
                await query.edit_message_text("خطا در پردازش انتخاب پنل. لطفاً دوباره تلاش کنید.")
                return ConversationHandler.END
        else:
            logger.warning(f"Unexpected callback_data: {callback_data} in select_panels")
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
                
                # Reset conversation flag
                context.user_data['in_conversation'] = False
                
                # برگشت به منوی فروشگاه با استفاده از chat_id
                chat_id = update.effective_chat.id
                await self.shop_menu.show_with_chat_id(chat_id, context)
                
                # تنظیم وضعیت کاربر به "shop"
                from src.bot.index import user_states
                user_states[update.effective_user.id] = "shop"
                
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
            
            # ساخت کیبورد با استفاده از تابع کمکی
            reply_markup = create_grouped_inbound_keyboard(
                panel_inbounds_dict=context.user_data['available_inbounds'],
                panel_dict=panels,
                selected_inbounds=context.user_data['selected_inbounds']
            )
            
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
        
        # نمایش پیام لغو
        await update.message.reply_text("❌ عملیات لغو شد.")
        
        # بازگشت به منوی فروشگاه با استفاده از chat_id
        chat_id = update.effective_chat.id
        
        # استفاده از تابع show_with_chat_id از BaseMenu با پارامترهای اضافی
        await self.shop_menu.show_with_chat_id(
            chat_id=chat_id, 
            context=context,
            user_id=update.effective_user.id,
            user_states_dict=user_states,
            target_state="shop"
        )
        
        return ConversationHandler.END 