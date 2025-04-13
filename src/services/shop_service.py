#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import json
import mysql.connector
import logging
from src.utils.db import get_db_connection
from src.services.panel import PanelService

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class ShopService:
    """Service for shop module operations"""
    
    def __init__(self):
        self.panel_service = PanelService()
    
    def add_category(self, name, description, panel_ids, inbound_ports):
        """Add a new category to the database
        
        Args:
            name (str): Category name
            description (str): Category description
            panel_ids (list): List of panel IDs
            inbound_ports (list): List of inbound ports
            
        Returns:
            int: ID of the new category
        """
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Convert inbound_ports list to JSON string
            inbound_ports_json = json.dumps(inbound_ports)
            
            # Insert new category
            query = """
                INSERT INTO categories (name, description, inbound_ports)
                VALUES (%s, %s, %s)
            """
            values = (name, description, inbound_ports_json)
            
            cursor.execute(query, values)
            conn.commit()
            
            # Get the ID of the newly inserted category
            category_id = cursor.lastrowid
            
            # Add relationships to category_panel table
            if panel_ids:
                for panel_id in panel_ids:
                    query = """
                        INSERT INTO category_panel (category_id, panel_id)
                        VALUES (%s, %s)
                    """
                    cursor.execute(query, (category_id, panel_id))
                
                conn.commit()
            
            cursor.close()
            conn.close()
            
            return category_id
            
        except mysql.connector.Error as e:
            logger.error(f"Database error in add_category: {e}")
            raise
    
    def get_all_panels(self):
        """Get all active panels
        
        Returns:
            list: List of panel dictionaries
        """
        try:
            logger.info("Getting panels directly from database")
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            
            query = """
                SELECT id, name, url, username, password, status 
                FROM panels 
                WHERE status = 'active' OR status IS NULL
                ORDER BY id
            """
            cursor.execute(query)
            panels = cursor.fetchall()
            
            cursor.close()
            conn.close()
            
            logger.info(f"Found {len(panels)} panels in database")
            if len(panels) == 0:
                logger.warning("No panels found in database!")
            else:
                # Log first panel details for debugging
                logger.info(f"First panel details: {panels[0]}")
            
            # Ensure each panel has all required fields
            for i, panel in enumerate(panels):
                # Ensure 'id' exists and is an integer
                if 'id' not in panel:
                    logger.warning(f"Panel at index {i} missing 'id' field")
                    panel['id'] = i + 1
                
                # Ensure 'name' exists
                if 'name' not in panel or not panel['name']:
                    logger.warning(f"Panel at index {i} missing or empty 'name' field")
                    panel['name'] = f"Panel {panel.get('id', i+1)}"
            
            return panels
        except Exception as e:
            logger.error(f"Error in get_all_panels: {e}")
            import traceback
            logger.error(traceback.format_exc())
            # Return empty list but not None
            return []
    
    def get_panel_inbounds(self, panel):
        """Get all inbounds from a panel
        
        Args:
            panel (dict): Panel dictionary with id, url, username, password
            
        Returns:
            list: List of inbound dictionaries
        """
        try:
            # Build URL for API call
            url = panel['url']
            # Ensure URL has http:// or https:// prefix
            if not url.startswith(('http://', 'https://')):
                url = 'http://' + url
                
            # Append API path
            url = url.rstrip('/') + '/panel/api/inbounds/list'
            
            logger.info(f"Getting inbounds for panel {panel['id']} from URL: {url}")
            
            # Set up cookies with session info
            cookies = self._login_and_get_cookies(panel)
            if not cookies:
                logger.warning(f"Failed to login to panel {panel['name']}")
                return []
            
            # Make API request
            response = requests.get(url, cookies=cookies, timeout=10)
            
            # Check response status
            if response.status_code == 200:
                result = response.json()
                
                # Check if response has inbounds data
                if 'obj' in result:
                    inbounds = result['obj']
                    logger.info(f"Found {len(inbounds)} inbounds for panel {panel['id']}")
                    return inbounds
                else:
                    logger.warning(f"No 'obj' field in response for panel {panel['id']}")
                    return []
            else:
                logger.error(f"Error getting inbounds for panel {panel['id']}: status code {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"Error getting inbounds for panel {panel.get('id', 'unknown')}: {str(e)}")
            return []
    
    def _login_and_get_cookies(self, panel):
        """Log in to panel and get cookies
        
        Args:
            panel (dict): Panel dictionary with url, username, password
            
        Returns:
            dict: Cookies from successful login or None if login failed
        """
        try:
            # Build login URL
            url = panel['url']
            # Ensure URL has http:// or https:// prefix
            if not url.startswith(('http://', 'https://')):
                url = 'http://' + url
            
            # Get panel type, defaulting to 3x-ui if not specified
            panel_type = panel.get('panel_type', '3x-ui')
            
            # Append login path based on panel type
            if panel_type == '3x-ui':
                login_url = url.rstrip('/') + '/login'
            elif panel_type == 'marzban':
                # For marzban, the login endpoint will be handled differently
                # We'll implement this in the future
                logger.warning("Marzban panel type not fully implemented yet")
                login_url = url.rstrip('/') + '/api/admin/token'
            else:
                # Default to 3x-ui behavior
                login_url = url.rstrip('/') + '/login'
            
            # Prepare login payload
            payload = {
                'username': panel['username'],
                'password': panel['password']
            }
            
            logger.info(f"Logging in to panel {panel['id']} at URL: {login_url}")
            
            # Send login request
            session = requests.Session()
            response = session.post(login_url, data=payload, timeout=10)
            
            # Check if login was successful
            if response.status_code == 200:
                try:
                    result = response.json()
                    if 'success' in result and result['success'] is True:
                        logger.info(f"Login successful for panel {panel['id']}")
                        return session.cookies.get_dict()
                except Exception as e:
                    logger.error(f"Error parsing login response for panel {panel['id']}: {e}")
            
            logger.warning(f"Login failed for panel {panel['id']} with status code {response.status_code}")
            return None
            
        except Exception as e:
            logger.error(f"Login error for panel {panel.get('id', 'unknown')}: {str(e)}")
            return None
    
    def get_all_categories(self):
        """Get all categories
        
        Returns:
            list: List of category dictionaries
        """
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            
            query = "SELECT * FROM categories ORDER BY name"
            cursor.execute(query)
            
            categories = cursor.fetchall()
            
            # Parse JSON inbound_ports for each category
            for category in categories:
                if category.get('inbound_ports'):
                    try:
                        category['inbound_ports'] = json.loads(category['inbound_ports'])
                    except:
                        category['inbound_ports'] = []
                else:
                    category['inbound_ports'] = []
            
            cursor.close()
            conn.close()
            
            return categories
            
        except mysql.connector.Error as e:
            logger.error(f"Database error in get_all_categories: {e}")
            return []
    
    def get_category_panels(self, category_id):
        """Get all panels related to a category
        
        Args:
            category_id (int): Category ID
            
        Returns:
            list: List of panel dictionaries
        """
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            
            query = """
                SELECT p.* FROM panels p
                JOIN category_panel cp ON p.id = cp.panel_id
                WHERE cp.category_id = %s
            """
            cursor.execute(query, (category_id,))
            panels = cursor.fetchall()
            
            cursor.close()
            conn.close()
            
            return panels
            
        except mysql.connector.Error as e:
            logger.error(f"Database error in get_category_panels: {e}")
            return []
    
    def delete_category(self, category_id):
        """Delete a category
        
        Args:
            category_id (int): ID of the category to delete
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Note: Due to ON DELETE CASCADE, associated records in category_panel 
            # will be automatically deleted
            query = "DELETE FROM categories WHERE id = %s"
            cursor.execute(query, (category_id,))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            return True
            
        except mysql.connector.Error as e:
            logger.error(f"Database error in delete_category: {e}")
            return False
    
    def delete_multiple_categories(self, category_ids):
        """Delete multiple categories
        
        Args:
            category_ids (list): List of category IDs to delete
            
        Returns:
            dict: Dictionary with success status and count of deleted categories
        """
        if not category_ids:
            return {"success": False, "count": 0, "message": "هیچ دسته‌بندی برای حذف انتخاب نشده است"}
            
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Format placeholders for SQL query based on number of IDs
            placeholders = ','.join(['%s'] * len(category_ids))
            query = f"DELETE FROM categories WHERE id IN ({placeholders})"
            
            # Execute the query
            cursor.execute(query, tuple(category_ids))
            
            # Get count of affected rows
            deleted_count = cursor.rowcount
            
            conn.commit()
            cursor.close()
            conn.close()
            
            return {
                "success": True,
                "count": deleted_count,
                "message": f"{deleted_count} دسته‌بندی با موفقیت حذف شد"
            }
            
        except mysql.connector.Error as e:
            logger.error(f"Database error in delete_multiple_categories: {e}")
            return {"success": False, "count": 0, "message": f"خطا در حذف دسته‌بندی‌ها: {str(e)}"}
    
    def get_all_products(self):
        """Get all products with their categories
        
        Returns:
            list: List of product dictionaries with category information
        """
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            
            query = """
                SELECT p.*, IFNULL(c.name, 'بدون دسته‌بندی') as category_name
                FROM products p
                LEFT JOIN categories c ON p.category_id = c.id
                ORDER BY p.name
            """
            cursor.execute(query)
            
            products = cursor.fetchall()
            
            cursor.close()
            conn.close()
            
            return products
            
        except mysql.connector.Error as e:
            logger.error(f"Database error in get_all_products: {e}")
            return []
    
    def delete_product(self, product_id):
        """Delete a product
        
        Args:
            product_id (int): ID of the product to delete
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            query = "DELETE FROM products WHERE id = %s"
            cursor.execute(query, (product_id,))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            return True
            
        except mysql.connector.Error as e:
            logger.error(f"Database error in delete_product: {e}")
            return False
    
    def delete_multiple_products(self, product_ids):
        """Delete multiple products
        
        Args:
            product_ids (list): List of product IDs to delete
            
        Returns:
            dict: Dictionary with success status and count of deleted products
        """
        if not product_ids:
            return {"success": False, "count": 0, "message": "هیچ محصولی برای حذف انتخاب نشده است"}
            
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # قبل از حذف، بررسی می‌کنیم که آیا سفارش‌های مرتبط وجود دارند
            orders_count = 0
            query = "SELECT COUNT(*) FROM orders WHERE product_id IN ({})".format(
                ','.join(['%s'] * len(product_ids))
            )
            cursor.execute(query, tuple(product_ids))
            result = cursor.fetchone()
            if result and result[0] > 0:
                orders_count = result[0]
            
            # Format placeholders for SQL query based on number of IDs
            placeholders = ','.join(['%s'] * len(product_ids))
            query = f"DELETE FROM products WHERE id IN ({placeholders})"
            
            # Execute the query
            cursor.execute(query, tuple(product_ids))
            
            # Get count of affected rows
            deleted_count = cursor.rowcount
            
            conn.commit()
            cursor.close()
            conn.close()
            
            message = f"{deleted_count} محصول با موفقیت حذف شد"
            
            # اگر سفارش مرتبط وجود داشته باشد، به کاربر اطلاع می‌دهیم
            if orders_count > 0:
                message += f"\n⚠️ {orders_count} سفارش مرتبط با این محصولات در سیستم باقی می‌مانند و فقط ارتباط آنها با محصولات قطع شد."
            
            return {
                "success": True,
                "count": deleted_count,
                "message": message
            }
            
        except mysql.connector.Error as e:
            logger.error(f"Database error in delete_multiple_products: {e}")
            return {"success": False, "count": 0, "message": f"خطا در حذف محصولات: {str(e)}"}
    
    def add_product(self, name, data_limit, price, category_id, duration, users_limit=1):
        """Add a new product to the database
        
        Args:
            name (str): Product name
            data_limit (int): Data limit in GB (0 for unlimited)
            price (float): Product price
            category_id (int): Category ID
            duration (int): Duration in days (0 for unlimited)
            users_limit (int, optional): Number of users allowed. Defaults to 1.
            
        Returns:
            int: ID of the new product
        """
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Insert new product
            query = """
                INSERT INTO products (name, data_limit, price, category_id, duration, users_limit, status)
                VALUES (%s, %s, %s, %s, %s, %s, 'active')
            """
            values = (name, data_limit, price, category_id, duration, users_limit)
            
            cursor.execute(query, values)
            conn.commit()
            
            # Get the ID of the newly inserted product
            product_id = cursor.lastrowid
            
            cursor.close()
            conn.close()
            
            return product_id
            
        except mysql.connector.Error as e:
            logger.error(f"Database error in add_product: {e}")
            raise
    
    def get_uncategorized_products(self):
        """Get all products without a category
        
        Returns:
            list: List of product dictionaries without category
        """
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            
            query = """
                SELECT * FROM products 
                WHERE category_id IS NULL
                ORDER BY name
            """
            cursor.execute(query)
            
            products = cursor.fetchall()
            
            cursor.close()
            conn.close()
            
            return products
            
        except mysql.connector.Error as e:
            logger.error(f"Database error in get_uncategorized_products: {e}")
            return [] 