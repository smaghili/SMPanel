#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

# تنظیم لاگینگ
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def create_checkbox_keyboard(items, is_selected_callback, item_callback_prefix, confirm_text="✅ تایید", confirm_callback="confirm"):
    """
    ساخت کیبورد با چک‌باکس‌ها و دکمه تایید
    
    Args:
        items: لیست آیتم‌های قابل انتخاب (باید id و name داشته باشند)
        is_selected_callback: تابعی که مشخص می‌کند آیا آیتم انتخاب شده است
        item_callback_prefix: پیشوند callback_data برای هر آیتم
        confirm_text: متن دکمه تایید
        confirm_callback: callback_data برای دکمه تایید
    
    Returns:
        InlineKeyboardMarkup: کیبورد ساخته شده
    """
    keyboard = []
    
    for item in items:
        item_id = item.get('id', 0)
        item_name = item.get('name', 'بدون نام')
        
        # تعیین علامت چک‌باکس بر اساس انتخاب یا عدم انتخاب
        checkbox = "☑️" if is_selected_callback(item_id) else "⬜️"
        
        # اضافه کردن دکمه به کیبورد
        keyboard.append([
            InlineKeyboardButton(f"{checkbox} {item_name}", callback_data=f"{item_callback_prefix}{item_id}")
        ])
    
    # اضافه کردن دکمه تایید
    keyboard.append([InlineKeyboardButton(confirm_text, callback_data=confirm_callback)])
    
    return InlineKeyboardMarkup(keyboard)

def create_grouped_inbound_keyboard(panel_inbounds_dict, panel_dict, selected_inbounds, confirm_text="✅ تایید اینباند ها", confirm_callback="confirm_inbounds"):
    """
    ساخت کیبورد اینباندها گروه‌بندی شده بر اساس پنل
    
    Args:
        panel_inbounds_dict: دیکشنری اینباندها با کلید panel_id
        panel_dict: دیکشنری پنل‌ها برای دریافت نام پنل
        selected_inbounds: لیست اینباندهای انتخاب شده
        confirm_text: متن دکمه تایید
        confirm_callback: callback_data برای دکمه تایید
    
    Returns:
        InlineKeyboardMarkup: کیبورد ساخته شده
    """
    keyboard = []
    
    for panel_id, inbounds in panel_inbounds_dict.items():
        # پیدا کردن نام پنل
        panel_name = "پنل"
        for panel in panel_dict:
            if panel.get('id') == panel_id:
                panel_name = panel.get('name', 'پنل')
                break
        
        # اضافه کردن هدر پنل
        keyboard.append([InlineKeyboardButton(f"📌 {panel_name}", callback_data=f"panel_header_{panel_id}")])
        
        # اضافه کردن اینباندها
        for inbound in inbounds:
            port = inbound.get('port', 'نامشخص')
            protocol = inbound.get('protocol', 'نامشخص')
            remark = inbound.get('remark', 'بدون توضیحات')
            
            inbound_key = f"{panel_id}_{inbound.get('id', '0')}"
            checkbox = "☑️" if inbound_key in selected_inbounds else "⬜️"
            
            keyboard.append([
                InlineKeyboardButton(
                    f"{checkbox} پورت: {port} | {protocol} | {remark}", 
                    callback_data=f"inbound_{inbound_key}"
                )
            ])
    
    # اضافه کردن دکمه تایید
    keyboard.append([InlineKeyboardButton(confirm_text, callback_data=confirm_callback)])
    
    return InlineKeyboardMarkup(keyboard) 