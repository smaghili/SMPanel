#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import mysql.connector
from mysql.connector.cursor import MySQLCursorDict
import logging
import requests
from requests.exceptions import RequestException
import json

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class PanelService:
    """Service for panel management"""
    
    def __init__(self):
        self.db_config = {
            'host': os.getenv('DB_HOST'),
            'database': os.getenv('DB_NAME'),
            'user': os.getenv('DB_USER'),
            'password': os.getenv('DB_PASSWORD')
        }
    
    def get_connection(self):
        """Get database connection"""
        try:
            conn = mysql.connector.connect(**self.db_config)
            conn.autocommit = True
            return conn
        except mysql.connector.Error as e:
            logger.error(f"Database connection error: {e}")
            # Persian error message for Telegram, but error is logged in English
            raise Exception(f"خطا در اتصال به پایگاه داده: {e}")
    
    def add_panel(self, name, url, username, password, panel_type='3x-ui'):
        """Add a new panel"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor(dictionary=True)
            logger.info(f"Adding new panel: {name}, Type: {panel_type}")
            cursor.execute(
                """
                INSERT INTO panels (name, url, username, password, panel_type, status)
                VALUES (%s, %s, %s, %s, %s, 'active')
                """,
                (name, url, username, password, panel_type)
            )
            panel_id = cursor.lastrowid
            cursor.close()
            conn.close()
            logger.info(f"Panel added successfully with ID: {panel_id}")
            return panel_id
        except mysql.connector.Error as e:
            logger.error(f"Database error while adding panel: {e}")
            # Log the SQL state which helps identify permission issues
            if hasattr(e, 'errno'):
                logger.error(f"MySQL Error Code: {e.errno}")
            # Persian error message for Telegram, but error is logged in English
            raise Exception(f"خطا در ذخیره‌سازی پنل: {e}")
        except Exception as e:
            logger.error(f"Unexpected error adding panel: {e}")
            # Persian error message for Telegram, but error is logged in English
            raise Exception(f"خطای غیرمنتظره: {e}")
    
    def get_panel(self, panel_id):
        """Get panel by ID"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor(dictionary=True)
            logger.info(f"Getting panel with ID: {panel_id}")
            cursor.execute(
                """
                SELECT * FROM panels WHERE id = %s
                """,
                (panel_id,)
            )
            panel = cursor.fetchone()
            cursor.close()
            conn.close()
            if panel:
                logger.info(f"Panel found: {panel['name']}")
            else:
                logger.info(f"No panel found with ID: {panel_id}")
            return panel
        except Exception as e:
            logger.error(f"Error getting panel: {e}")
            return None
    
    def get_all_panels(self):
        """Get all panels"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor(dictionary=True)
            logger.info("Retrieving all panels")
            cursor.execute(
                """
                SELECT * FROM panels ORDER BY id
                """
            )
            panels = cursor.fetchall()
            cursor.close()
            conn.close()
            logger.info(f"Retrieved {len(panels)} panels")
            return panels
        except Exception as e:
            logger.error(f"Error getting all panels: {e}")
            return []
    
    def update_panel(self, panel_id, name=None, url=None, username=None, password=None, status=None):
        """Update panel details"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor(dictionary=True)
            logger.info(f"Updating panel with ID: {panel_id}")
            # Build the update query dynamically
            query_parts = []
            params = []
            
            if name is not None:
                query_parts.append("name = %s")
                params.append(name)
            
            if url is not None:
                query_parts.append("url = %s")
                params.append(url)
            
            if username is not None:
                query_parts.append("username = %s")
                params.append(username)
            
            if password is not None:
                query_parts.append("password = %s")
                params.append(password)
            
            if status is not None:
                query_parts.append("status = %s")
                params.append(status)
            
            if not query_parts:
                logger.warning(f"No fields to update for panel ID: {panel_id}")
                return False
            
            query = f"""
                UPDATE panels 
                SET {', '.join(query_parts)}
                WHERE id = %s
            """
            params.append(panel_id)
            
            cursor.execute(query, params)
            affected_rows = cursor.rowcount
            cursor.close()
            conn.close()
            if affected_rows > 0:
                logger.info(f"Panel updated successfully: {panel_id}")
            else:
                logger.warning(f"No panel found with ID: {panel_id}")
            return affected_rows > 0
        except Exception as e:
            logger.error(f"Error updating panel: {e}")
            return False
    
    def check_panel_status(self, panel_id):
        """
        Check if a panel is active by sending a login request to its URL
        
        Args:
            panel_id: The ID of the panel to check
            
        Returns:
            bool: True if the panel is active and responding, False otherwise
            str: A message describing the status or error
        """
        try:
            panel = self.get_panel(panel_id)
            if not panel:
                return False, "پنل یافت نشد"
            
            if not panel['url']:
                return False, "آدرس پنل وجود ندارد"
                
            # Ensure URL has http:// or https:// prefix
            url = panel['url']
            if not url.startswith(('http://', 'https://')):
                url = 'http://' + url
                
            # Append /login path if it doesn't have it
            if not url.endswith('/login'):
                url = url.rstrip('/') + '/login'
                
            logger.info(f"Checking status of panel ID {panel_id} at URL: {url}")
            
            # Prepare login payload
            payload = {
                'username': panel['username'],
                'password': panel['password']
            }
            
            # Send POST request to panel login URL
            response = requests.post(url, data=payload, timeout=10)
            
            # Handle response
            if response.status_code == 200:
                # Try to parse response as JSON
                try:
                    # Parse JSON response
                    result = response.json()
                    
                    # Check for success field in JSON response
                    if 'success' in result:
                        if result['success'] is True:
                            logger.info(f"Panel ID {panel_id} login successful with message: {result.get('msg', '')}")
                            self.update_panel(panel_id, status='active')
                            return True, "پنل فعال و در دسترس است"
                        else:
                            # Login failed but panel is responding
                            logger.warning(f"Panel ID {panel_id} login failed with message: {result.get('msg', '')}")
                            self.update_panel(panel_id, status='inactive')
                            return False, f"پنل در دسترس است اما ورود ناموفق بود: {result.get('msg', 'نام کاربری یا رمز عبور نادرست')}"
                    
                    # If there's no success field but has other common fields
                    elif any(key in result for key in ['status', 'result', 'data']):
                        logger.info(f"Panel ID {panel_id} is active and responding with valid JSON")
                        self.update_panel(panel_id, status='active')
                        return True, "پنل فعال و در دسترس است"
                        
                except (json.JSONDecodeError, ValueError):
                    # Some panels might return HTML or other formats
                    if 'login' in response.text.lower() or 'admin' in response.text.lower():
                        logger.info(f"Panel ID {panel_id} is active and responding with HTML")
                        self.update_panel(panel_id, status='active')
                        return True, "پنل فعال و در دسترس است"
            
            # If we got a response but couldn't verify it's valid
            if response.status_code != 200:
                logger.warning(f"Panel ID {panel_id} returned status code: {response.status_code}")
                self.update_panel(panel_id, status='inactive')
                return False, f"پنل پاسخ نامعتبر با کد {response.status_code} برگرداند"
            
            # If we got here, the panel responded but we couldn't verify it's valid
            logger.warning(f"Panel ID {panel_id} response couldn't be verified as valid: {response.text[:100]}")
            self.update_panel(panel_id, status='unknown')
            return False, "وضعیت پنل نامشخص است"
                
        except RequestException as e:
            logger.error(f"Error connecting to panel ID {panel_id}: {e}")
            self.update_panel(panel_id, status='inactive')
            return False, f"خطا در اتصال به پنل: {e}"
        except Exception as e:
            logger.error(f"Unexpected error checking panel ID {panel_id}: {e}")
            return False, f"خطای غیرمنتظره: {e}"
            
    def check_all_panels_status(self):
        """
        Check status of all panels
        
        Returns:
            dict: A dictionary with panel IDs as keys and tuples of (status, message) as values
        """
        panels = self.get_all_panels()
        results = {}
        
        for panel in panels:
            status, message = self.check_panel_status(panel['id'])
            results[panel['id']] = (status, message)
            
        return results
    
    def delete_panel(self, panel_id):
        """Delete a panel"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            logger.info(f"Deleting panel with ID: {panel_id}")
            cursor.execute(
                """
                DELETE FROM panels WHERE id = %s
                """,
                (panel_id,)
            )
            affected_rows = cursor.rowcount
            cursor.close()
            conn.close()
            if affected_rows > 0:
                logger.info(f"Panel deleted successfully: {panel_id}")
            else:
                logger.warning(f"No panel found with ID: {panel_id}")
            return affected_rows > 0
        except Exception as e:
            logger.error(f"Error deleting panel: {e}")
            return False 