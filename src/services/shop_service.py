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
            # اطمینان از تبدیل صحیح پارامترها
            try:
                data_limit = int(data_limit) if data_limit is not None else 0
                price = float(price) if price is not None else 0
                
                # اگر category_id خالی است، به NULL تبدیل کنیم
                if category_id and category_id != '':
                    category_id = int(category_id)
                else:
                    category_id = None
                    
                duration = int(duration) if duration is not None else 0
                users_limit = int(users_limit) if users_limit is not None else 1
            except (ValueError, TypeError) as e:
                logger.error(f"Error converting parameters in add_product: {e}")
                raise ValueError(f"خطا در تبدیل پارامترها: {e}")
            
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Insert new product
            query = """
                INSERT INTO products (name, data_limit, price, category_id, duration, users_limit, status)
                VALUES (%s, %s, %s, %s, %s, %s, 'active')
            """
            values = (name, data_limit, price, category_id, duration, users_limit)
            
            logger.info(f"Adding product with values: {values}")
            
            cursor.execute(query, values)
            conn.commit()
            
            # Get the ID of the newly inserted product
            product_id = cursor.lastrowid
            
            cursor.close()
            conn.close()
            
            return product_id
            
        except mysql.connector.Error as e:
            logger.error(f"Database error in add_product: {e}")
            # بررسی نوع خطا برای ارائه پیام مناسب به کاربر
            if e.errno == 1452:  # Foreign key constraint fails
                raise ValueError("دسته‌بندی انتخاب شده وجود ندارد")
            elif e.errno == 1062:  # Duplicate entry
                raise ValueError("محصول با این نام قبلاً ثبت شده است")
            else:
                raise ValueError(f"خطا در ارتباط با پایگاه داده: {e}")
        except Exception as e:
            logger.error(f"Unexpected error in add_product: {e}")
            logger.error(f"Stack trace: {traceback.format_exc()}")
            raise ValueError(f"خطای غیرمنتظره: {e}")
    
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
            
    def get_product_by_id(self, product_id):
        """Get a product by its ID
        
        Args:
            product_id (int): Product ID
            
        Returns:
            dict: Product dictionary with category information or None if not found
        """
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            
            query = """
                SELECT p.*, IFNULL(c.name, 'بدون دسته‌بندی') as category_name
                FROM products p
                LEFT JOIN categories c ON p.category_id = c.id
                WHERE p.id = %s
            """
            cursor.execute(query, (product_id,))
            
            product = cursor.fetchone()
            
            cursor.close()
            conn.close()
            
            return product
            
        except mysql.connector.Error as e:
            logger.error(f"Database error in get_product_by_id: {e}")
            return None
            
    def update_product(self, product_id, name, data_limit, price, category_id, duration, users_limit=1):
        """Update a product in the database
        
        Args:
            product_id (int): ID of the product to update
            name (str): New product name
            data_limit (int): New data limit in GB (0 for unlimited)
            price (float): New product price
            category_id (int): New category ID
            duration (int): New duration in days (0 for unlimited)
            users_limit (int, optional): New number of users allowed. Defaults to 1.
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # اطمینان از تبدیل صحیح پارامترها
            try:
                data_limit = int(data_limit) if data_limit is not None else 0
                price = float(price) if price is not None else 0
                
                # اگر category_id خالی است، به NULL تبدیل کنیم
                if category_id and category_id != '':
                    category_id = int(category_id)
                else:
                    category_id = None
                    
                duration = int(duration) if duration is not None else 0
                users_limit = int(users_limit) if users_limit is not None else 1
            except (ValueError, TypeError) as e:
                logger.error(f"Error converting parameters in update_product: {e}")
                raise ValueError(f"خطا در تبدیل پارامترها: {e}")
            
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Update product
            query = """
                UPDATE products 
                SET name = %s, data_limit = %s, price = %s, category_id = %s, duration = %s, users_limit = %s
                WHERE id = %s
            """
            values = (name, data_limit, price, category_id, duration, users_limit, product_id)
            
            logger.info(f"Updating product {product_id} with values: {values}")
            
            cursor.execute(query, values)
            conn.commit()
            
            affected_rows = cursor.rowcount
            
            cursor.close()
            conn.close()
            
            return affected_rows > 0
            
        except mysql.connector.Error as e:
            logger.error(f"Database error in update_product: {e}")
            # بررسی نوع خطا برای ارائه پیام مناسب به کاربر
            if e.errno == 1452:  # Foreign key constraint fails
                raise ValueError("دسته‌بندی انتخاب شده وجود ندارد")
            else:
                raise ValueError(f"خطا در ارتباط با پایگاه داده: {e}")
        except Exception as e:
            logger.error(f"Unexpected error in update_product: {e}")
            import traceback
            logger.error(f"Stack trace: {traceback.format_exc()}")
            raise ValueError(f"خطای غیرمنتظره: {e}")
    
    # NEW METHODS FOR EXTRA VOLUME SETTINGS
    
    def get_extra_volume_settings(self, category_id):
        """Get extra volume settings for a category
        
        Args:
            category_id (int): Category ID
            
        Returns:
            dict: Extra volume settings or None if not found
        """
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            
            query = """
                SELECT id, category_id, price_per_gb, min_volume, max_volume, is_enabled
                FROM extra_volume_settings
                WHERE category_id = %s
            """
            cursor.execute(query, (category_id,))
            settings = cursor.fetchone()
            
            cursor.close()
            conn.close()
            
            return settings
            
        except mysql.connector.Error as e:
            logger.error(f"Database error in get_extra_volume_settings: {e}")
            return None
    
    def create_or_update_extra_volume_settings(self, category_id, price_per_gb, min_volume, max_volume, is_enabled=True):
        """Create or update extra volume settings for a category
        
        Args:
            category_id (int): Category ID
            price_per_gb (int): Price per gigabyte
            min_volume (int): Minimum volume that can be purchased
            max_volume (int): Maximum volume that can be purchased
            is_enabled (bool): Whether extra volume purchase is enabled
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Check if settings already exist for this category
            check_query = """
                SELECT id FROM extra_volume_settings WHERE category_id = %s
            """
            cursor.execute(check_query, (category_id,))
            existing = cursor.fetchone()
            
            if existing:
                # Update existing settings
                query = """
                    UPDATE extra_volume_settings
                    SET price_per_gb = %s, min_volume = %s, max_volume = %s, is_enabled = %s
                    WHERE category_id = %s
                """
                cursor.execute(query, (price_per_gb, min_volume, max_volume, is_enabled, category_id))
            else:
                # Create new settings
                query = """
                    INSERT INTO extra_volume_settings 
                    (category_id, price_per_gb, min_volume, max_volume, is_enabled)
                    VALUES (%s, %s, %s, %s, %s)
                """
                cursor.execute(query, (category_id, price_per_gb, min_volume, max_volume, is_enabled))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            return True
            
        except mysql.connector.Error as e:
            logger.error(f"Database error in create_or_update_extra_volume_settings: {e}")
            return False
    
    def set_extra_volume_price(self, category_id, price_per_gb):
        """Set the price per GB for extra volume
        
        Args:
            category_id (int): Category ID
            price_per_gb (int): Price per gigabyte
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            settings = self.get_extra_volume_settings(category_id)
            
            if settings:
                # Update existing settings
                return self.create_or_update_extra_volume_settings(
                    category_id,
                    price_per_gb,
                    settings['min_volume'],
                    settings['max_volume'],
                    settings['is_enabled']
                )
            else:
                # Create new settings with defaults
                return self.create_or_update_extra_volume_settings(
                    category_id, 
                    price_per_gb, 
                    1,  # Default min volume
                    100,  # Default max volume
                    True  # Enabled by default
                )
                
        except Exception as e:
            logger.error(f"Error in set_extra_volume_price: {e}")
            return False
    
    def set_extra_volume_min(self, category_id, min_volume):
        """Set the minimum volume that can be purchased
        
        Args:
            category_id (int): Category ID
            min_volume (int): Minimum volume
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            settings = self.get_extra_volume_settings(category_id)
            
            if settings:
                # Update existing settings
                return self.create_or_update_extra_volume_settings(
                    category_id,
                    settings['price_per_gb'],
                    min_volume,
                    settings['max_volume'],
                    settings['is_enabled']
                )
            else:
                # Create new settings with defaults
                return self.create_or_update_extra_volume_settings(
                    category_id, 
                    10000,  # Default price (10,000 tomans)
                    min_volume, 
                    100,  # Default max volume
                    True  # Enabled by default
                )
                
        except Exception as e:
            logger.error(f"Error in set_extra_volume_min: {e}")
            return False
    
    def set_extra_volume_max(self, category_id, max_volume):
        """Set the maximum volume that can be purchased
        
        Args:
            category_id (int): Category ID
            max_volume (int): Maximum volume
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            settings = self.get_extra_volume_settings(category_id)
            
            if settings:
                # Update existing settings
                return self.create_or_update_extra_volume_settings(
                    category_id,
                    settings['price_per_gb'],
                    settings['min_volume'],
                    max_volume,
                    settings['is_enabled']
                )
            else:
                # Create new settings with defaults
                return self.create_or_update_extra_volume_settings(
                    category_id, 
                    10000,  # Default price (10,000 tomans)
                    1,  # Default min volume
                    max_volume,
                    True  # Enabled by default
                )
            
        except Exception as e:
            logger.error(f"Error in set_extra_volume_max: {e}")
            return False
    
    def set_extra_volume_enabled(self, category_id, is_enabled):
        """Set whether extra volume purchase is enabled for a category
        
        Args:
            category_id (int): Category ID
            is_enabled (bool): Whether extra volume purchase is enabled
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            settings = self.get_extra_volume_settings(category_id)
            
            if settings:
                # Update existing settings
                return self.create_or_update_extra_volume_settings(
                    category_id,
                    settings['price_per_gb'],
                    settings['min_volume'],
                    settings['max_volume'],
                    is_enabled
                )
            else:
                # Create new settings with defaults
                return self.create_or_update_extra_volume_settings(
                    category_id, 
                    10000,  # Default price (10,000 tomans)
                    1,  # Default min volume
                    100,  # Default max volume
                    is_enabled
                )
            
        except Exception as e:
            logger.error(f"Error in set_extra_volume_enabled: {e}")
            return False
    
    def get_products_by_category(self, category_id):
        """Get products by category ID
        
        Args:
            category_id (int): Category ID
            
        Returns:
            list: List of products in the category
        """
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            
            query = """
                SELECT p.*
                FROM products p
                WHERE p.category_id = %s
                ORDER BY p.name
            """
            cursor.execute(query, (category_id,))
            
            products = cursor.fetchall()
            
            cursor.close()
            conn.close()
            
            return products
            
        except mysql.connector.Error as e:
            logger.error(f"Database error in get_products_by_category: {e}")
            return [] 