#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes

from src.services.panel import PanelService

class PanelManagementMenu:
    """Panel management menu with inline buttons"""
    
    def __init__(self):
        self.panel_service = PanelService()
    
    async def show(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show panel management menu with all panels from database"""
        # Get all panels from database
        panels = self.panel_service.get_all_panels()
        
        if not panels:
            # No panels found
            await update.message.reply_text(
                "❌ هیچ پنلی یافت نشد!\n"
                "لطفا ابتدا با استفاده از گزینه 'اضافه کردن پنل' یک پنل جدید اضافه کنید."
            )
            return
        
        # Create inline keyboard
        keyboard = []
        
        # Add each panel as a button
        for panel in panels:
            # Determine status icon
            status_icon = "✅" if panel['status'] == 'active' else "❌"
            
            # Create button for each panel
            keyboard.append([
                InlineKeyboardButton(
                    f"{status_icon} {panel['name']}",
                    callback_data=f"panel_{panel['id']}"
                )
            ])
        
        # Add back button
        keyboard.append([
            InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_admin")
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Send message with panel list
        await update.message.reply_text(
            "📋 لیست پنل‌های موجود:\n"
            "برای مدیریت هر پنل، روی آن کلیک کنید.",
            reply_markup=reply_markup
        )
    
    async def show_panel_list(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show panel list through callback query"""
        # Get all panels from database
        panels = self.panel_service.get_all_panels()
        
        if not panels:
            # No panels found
            await update.callback_query.edit_message_text(
                "❌ هیچ پنلی یافت نشد!\n"
                "لطفا ابتدا با استفاده از گزینه 'اضافه کردن پنل' یک پنل جدید اضافه کنید."
            )
            return
        
        # Create inline keyboard
        keyboard = []
        
        # Add each panel as a button
        for panel in panels:
            # Determine status icon
            status_icon = "✅" if panel['status'] == 'active' else "❌"
            
            # Create button for each panel
            keyboard.append([
                InlineKeyboardButton(
                    f"{status_icon} {panel['name']}",
                    callback_data=f"panel_{panel['id']}"
                )
            ])
        
        # Add back button
        keyboard.append([
            InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_admin")
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Update message with panel list
        await update.callback_query.edit_message_text(
            "📋 لیست پنل‌های موجود:\n"
            "برای مدیریت هر پنل، روی آن کلیک کنید.",
            reply_markup=reply_markup
        )
    
    async def show_panel_options(self, update: Update, context: ContextTypes.DEFAULT_TYPE, panel_id):
        """Show options for a specific panel"""
        # Get panel data
        panel = self.panel_service.get_panel(panel_id)
        
        if not panel:
            # Panel not found
            await update.callback_query.answer("❌ پنل مورد نظر یافت نشد!")
            return
        
        # Determine current status
        status = panel['status']
        status_text = "فعال" if status == 'active' else "غیرفعال"
        toggle_action = "غیرفعال کردن" if status == 'active' else "فعال کردن"
        toggle_icon = "❌" if status == 'active' else "✅"
        
        # Create keyboard for panel options
        keyboard = [
            [
                InlineKeyboardButton(
                    f"{toggle_icon} {toggle_action} پنل",
                    callback_data=f"toggle_panel_{panel_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    "🗑️ حذف پنل",
                    callback_data=f"confirm_delete_{panel_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    "🔙 بازگشت به لیست پنل‌ها",
                    callback_data="panel_list"
                )
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Status icon
        status_icon = "✅" if status == 'active' else "❌"
        
        # Show panel info
        await update.callback_query.edit_message_text(
            f"🖥 اطلاعات پنل: {panel['name']}\n\n"
            f"🔗 آدرس: {panel['url']}\n"
            f"👤 نام کاربری: {panel['username']}\n"
            f"🔐 رمز عبور: {panel['password']}\n"
            f"📊 وضعیت: {status_icon} {status_text}\n\n"
            f"لطفا عملیات مورد نظر را انتخاب کنید:",
            reply_markup=reply_markup
        )
    
    async def confirm_delete_panel(self, update: Update, context: ContextTypes.DEFAULT_TYPE, panel_id):
        """Ask for confirmation before deleting a panel"""
        # Get panel data
        panel = self.panel_service.get_panel(panel_id)
        
        if not panel:
            # Panel not found
            await update.callback_query.answer("❌ پنل مورد نظر یافت نشد!")
            return
        
        # Create confirmation keyboard
        keyboard = [
            [
                InlineKeyboardButton(
                    "✅ بله، حذف شود",
                    callback_data=f"delete_panel_{panel_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    "❌ خیر، لغو عملیات",
                    callback_data=f"panel_{panel_id}"
                )
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Show confirmation message
        await update.callback_query.edit_message_text(
            f"⚠️ آیا از حذف پنل «{panel['name']}» اطمینان دارید؟\n\n"
            f"این عملیات غیرقابل بازگشت است!",
            reply_markup=reply_markup
        )
    
    async def toggle_panel_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE, panel_id):
        """Toggle panel active status"""
        # Get panel data
        panel = self.panel_service.get_panel(panel_id)
        
        if not panel:
            # Panel not found
            await update.callback_query.answer("❌ پنل مورد نظر یافت نشد!")
            return
        
        # Toggle status
        current_status = panel['status']
        new_status = 'inactive' if current_status == 'active' else 'active'
        
        # Update panel status
        success = self.panel_service.update_panel(panel_id, status=new_status)
        
        if success:
            status_text = "فعال" if new_status == 'active' else "غیرفعال"
            await update.callback_query.answer(f"✅ وضعیت پنل به {status_text} تغییر یافت.")
            
            # Show panel options again with updated status
            await self.show_panel_options(update, context, panel_id)
        else:
            await update.callback_query.answer("❌ خطا در تغییر وضعیت پنل!")
    
    async def delete_panel(self, update: Update, context: ContextTypes.DEFAULT_TYPE, panel_id):
        """Delete a panel"""
        # Get panel data for name
        panel = self.panel_service.get_panel(panel_id)
        
        if not panel:
            # Panel not found
            await update.callback_query.answer("❌ پنل مورد نظر یافت نشد!")
            return
        
        panel_name = panel['name']
        
        # Delete the panel
        success = self.panel_service.delete_panel(panel_id)
        
        if success:
            await update.callback_query.answer(f"✅ پنل {panel_name} با موفقیت حذف شد.")
            
            # Return to panel list
            await self.show_panel_list(update, context)
        else:
            await update.callback_query.answer("❌ خطا در حذف پنل!")
            await update.callback_query.edit_message_text(
                f"❌ خطا در حذف پنل {panel_name}.\n\n"
                f"لطفاً دوباره تلاش کنید یا با پشتیبانی تماس بگیرید."
            ) 