#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from telegram import Update
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    filters
)

from src.services.panel import PanelService

# Conversation states
(PANEL_NAME, PANEL_URL, PANEL_USERNAME, PANEL_PASSWORD) = range(4)

class AddPanelScene:
    """Scene for adding a new panel"""
    
    def __init__(self):
        self.panel_service = PanelService()
    
    def get_handler(self):
        """Get the conversation handler for this scene"""
        return ConversationHandler(
            entry_points=[],  # This will be set by the caller
            states={
                PANEL_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.panel_name)],
                PANEL_URL: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.panel_url)],
                PANEL_USERNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.panel_username)],
                PANEL_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.panel_password)],
            },
            fallbacks=[CommandHandler("cancel", self.cancel)],
        )
    
    async def start_scene(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start the scene"""
        await update.callback_query.message.edit_text(
            "برای اضافه کردن پنل به ربات ابتدا یک نام برای پنل خود ارسال کنید\n\n"
            "⚠️ توجه: نام پنل نامی است که در هنگام انجام عملیات جستجو نشان داده می شود."
        )
        return PANEL_NAME
    
    async def panel_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle panel name entry"""
        panel_name = update.message.text
        context.user_data['panel_name'] = panel_name
        
        await update.message.reply_text(
            "🔗 نام پنل ذخیره شد. حالا آدرس پنل خود را ارسال کنید.\n"
            "⚠️ توجه:\n"
            "🔸 آدرس پنل باید بدون dashboard ارسال شود.\n"
            "🔹 در صورتی که پورت پنل 443 است، پورت را نباید وارد کنید. (گاهی حتما با پورت باید وارد کنید)\n"
            "🔸 آخر آدرس نباید / داشته باشد.\n"
            "🔹 در صورت وارد کردن آیپی، حتما http یا https باید داشته باشد."
        )
        
        return PANEL_URL
    
    async def panel_url(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle panel URL entry"""
        panel_url = update.message.text
        context.user_data['panel_url'] = panel_url
        
        await update.message.reply_text(
            "👤 آدرس پنل ذخیره شد. حالا نام کاربری را ارسال کنید."
        )
        
        return PANEL_USERNAME
    
    async def panel_username(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle panel username entry"""
        panel_username = update.message.text
        context.user_data['panel_username'] = panel_username
        
        await update.message.reply_text(
            "🔑 نام کاربری ذخیره شد. حالا رمز عبور پنل خود را وارد نمایید."
        )
        
        return PANEL_PASSWORD
    
    async def panel_password(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle panel password entry"""
        panel_password = update.message.text
        context.user_data['panel_password'] = panel_password
        
        # Show typing status to indicate processing
        await update.message.chat.send_action(action="typing")
        
        # First check if panel is accessible and login works
        await update.message.reply_text("🔄 در حال بررسی اتصال به پنل...")
        
        try:
            # Create a temporary panel object without saving to database
            panel_data = {
                'id': -1,  # Temporary ID
                'name': context.user_data['panel_name'],
                'url': context.user_data['panel_url'],
                'username': context.user_data['panel_username'],
                'password': context.user_data['panel_password']
            }
            
            # Send request to panel to check if login works
            url = panel_data['url']
            # Ensure URL has http:// or https:// prefix
            if not url.startswith(('http://', 'https://')):
                url = 'http://' + url
                
            # Append /login path if it doesn't have it
            if not url.endswith('/login'):
                url = url.rstrip('/') + '/login'
            
            # Prepare login payload
            payload = {
                'username': panel_data['username'],
                'password': panel_data['password']
            }
            
            # Send POST request to panel login URL
            import requests
            from requests.exceptions import RequestException
            import json
            
            response = requests.post(url, data=payload, timeout=10)
            
            # Check if response is successful and contains valid JSON
            if response.status_code == 200:
                try:
                    # Try to parse JSON response
                    result = response.json()
                    
                    # Check if login was successful
                    if 'success' in result:
                        if result['success'] is True:
                            # Login successful, save panel to database
                            panel_id = self.panel_service.add_panel(
                                context.user_data['panel_name'],
                                context.user_data['panel_url'],
                                context.user_data['panel_username'],
                                context.user_data['panel_password']
                            )
                            
                            await update.message.reply_text(
                                f"🎉 تبریک! پنل شما با موفقیت اضافه گردید و فعال است.\n"
                                f"✅ پنل فعال و در دسترس است\n\n"
                                f"می‌توانید با دستور /start به منوی اصلی برگردید."
                            )
                            return ConversationHandler.END
                        else:
                            # Login failed, show error
                            error_msg = result.get('msg', 'نام کاربری یا رمز عبور نادرست')
                            await update.message.reply_text(
                                f"❌ اتصال به پنل برقرار شد اما ورود ناموفق بود.\n"
                                f"⚠️ {error_msg}\n\n"
                                f"دلایل احتمالی:\n"
                                f"• نام کاربری یا رمز عبور اشتباه است\n"
                                f"• پنل نیاز به تنظیمات بیشتری دارد\n\n"
                                f"لطفاً اطلاعات ورودی پنل را بررسی کنید و دوباره تلاش کنید."
                            )
                            return ConversationHandler.END
                    
                    # If there's no specific success field but response contains other common fields
                    elif any(key in result for key in ['status', 'result', 'data']):
                        # Looks like a valid API response, try to save panel
                        panel_id = self.panel_service.add_panel(
                            context.user_data['panel_name'],
                            context.user_data['panel_url'],
                            context.user_data['panel_username'],
                            context.user_data['panel_password']
                        )
                        
                        await update.message.reply_text(
                            f"🎉 تبریک! پنل شما با موفقیت اضافه گردید.\n"
                            f"✅ پنل فعال و در دسترس است\n\n"
                            f"می‌توانید با دستور /start به منوی اصلی برگردید."
                        )
                        return ConversationHandler.END
                        
                except (json.JSONDecodeError, ValueError):
                    # Response is not valid JSON, check if it contains login page
                    if 'login' in response.text.lower() or 'admin' in response.text.lower():
                        # Looks like a valid panel but not JSON API
                        panel_id = self.panel_service.add_panel(
                            context.user_data['panel_name'],
                            context.user_data['panel_url'],
                            context.user_data['panel_username'],
                            context.user_data['panel_password']
                        )
                        
                        await update.message.reply_text(
                            f"🎉 تبریک! پنل شما با موفقیت اضافه گردید.\n"
                            f"✅ پاسخ پنل HTML است، احتمالاً صفحه ورود\n\n"
                            f"می‌توانید با دستور /start به منوی اصلی برگردید."
                        )
                        return ConversationHandler.END
                    else:
                        # Unknown response
                        await update.message.reply_text(
                            f"❌ پنل پاسخ داد اما فرمت پاسخ قابل شناسایی نیست.\n"
                            f"⚠️ ممکن است آدرس لاگین اشتباه باشد.\n\n"
                            f"لطفاً آدرس پنل را بررسی کنید و دوباره تلاش کنید."
                        )
                        return ConversationHandler.END
            
            # Handle non-200 responses
            else:
                await update.message.reply_text(
                    f"❌ اتصال به پنل با خطا مواجه شد (کد {response.status_code}).\n"
                    f"دلایل احتمالی:\n"
                    f"• آدرس پنل اشتباه است\n"
                    f"• پنل در دسترس نیست\n"
                    f"• مسیر لاگین متفاوت است\n\n"
                    f"لطفاً آدرس را بررسی کنید و دوباره تلاش کنید."
                )
                return ConversationHandler.END
                
        except RequestException as e:
            # Connection error
            await update.message.reply_text(
                f"❌ خطا در اتصال به پنل: {str(e)}\n\n"
                f"دلایل احتمالی:\n"
                f"• آدرس پنل اشتباه است\n"
                f"• پنل در دسترس نیست\n"
                f"• فایروال یا محدودیت دسترسی\n\n"
                f"لطفاً آدرس را بررسی کنید و دوباره تلاش کنید."
            )
            return ConversationHandler.END
            
        except Exception as e:
            # Other errors
            error_message = str(e)
            print(f"Error: {error_message}")
            
            await update.message.reply_text(
                f"❌ خطای غیرمنتظره: {error_message}\n\n"
                f"لطفاً دوباره تلاش کنید یا با پشتیبانی تماس بگیرید."
            )
            return ConversationHandler.END
    
    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Cancel the conversation"""
        await update.message.reply_text("❌ عملیات لغو شد.")
        return ConversationHandler.END 