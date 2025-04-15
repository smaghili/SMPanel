#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from src.bot.menus.base_menu import BaseMenu

class ShopMenu(BaseMenu):
    """Shop menu implementation"""
    
    def setup_menu(self):
        """Setup shop menu keyboard and message"""
        self._message = "🏪 بخش فروشگاه:\nلطفا یکی از گزینه های زیر را انتخاب کنید:"
        self._keyboard = [
            [self.create_button("❌ حذف محصول"), self.create_button("🛍️ اضافه کردن محصول")],
            [self.create_button("❌ حذف دسته بندی"), self.create_button("🛒 اضافه کردن دسته بندی")],
            [self.create_button("✏️ ویرایش محصول")],
            [self.create_button("➕ تنظیم قیمت حجم اضافه")],
            [self.create_button("❌ حذف کد هدیه"), self.create_button("🎁 ساخت کد هدیه")],
            [self.create_button("❌ حذف کد تخفیف"), self.create_button("🏷️ ساخت کد تخفیف")],
            [self.create_button("🔙 بازگشت به منوی مدیریت")]
        ]

    async def add_product(self, update, context):
        """Handle add product request"""
        # Import here to avoid circular import
        from src.bot.scenes.add_product_scene import AddProductScene
        add_product_scene = AddProductScene()
        return await add_product_scene.start_scene(update, context)

    async def delete_product(self, update, context):
        """Handle delete product request"""
        # Import here to avoid circular import
        from src.bot.scenes.delete_product_scene import DeleteProductScene
        delete_product_scene = DeleteProductScene()
        return await delete_product_scene.start_scene(update, context)

    async def add_category(self, update, context):
        """Handle add category request"""
        # Import here to avoid circular import
        from src.bot.scenes.add_category_scene import AddCategoryScene
        add_category_scene = AddCategoryScene()
        return await add_category_scene.start_scene(update, context)

    async def delete_category(self, update, context):
        """Handle delete category request"""
        # Import here to avoid circular import
        from src.bot.scenes.delete_category_scene import DeleteCategoryScene
        delete_category_scene = DeleteCategoryScene()
        return await delete_category_scene.start_scene(update, context)

    async def edit_product(self, update, context):
        """Handle edit product request"""
        # Import here to avoid circular import
        from src.bot.scenes.edit_product_scene import EditProductScene
        edit_product_scene = EditProductScene()
        return await edit_product_scene.start_scene(update, context)

    async def set_volume_price(self, update, context):
        """Handle set volume price request"""
        await update.message.reply_text("🚧 بخش تنظیم قیمت حجم اضافه در حال توسعه است...")

    async def create_gift_code(self, update, context):
        """Handle create gift code request"""
        await update.message.reply_text("🚧 بخش ساخت کد هدیه در حال توسعه است...")

    async def delete_gift_code(self, update, context):
        """Handle delete gift code request"""
        await update.message.reply_text("🚧 بخش حذف کد هدیه در حال توسعه است...")

    async def create_discount_code(self, update, context):
        """Handle create discount code request"""
        await update.message.reply_text("🚧 بخش ساخت کد تخفیف در حال توسعه است...")

    async def delete_discount_code(self, update, context):
        """Handle delete discount code request"""
        await update.message.reply_text("🚧 بخش حذف کد تخفیف در حال توسعه است...") 