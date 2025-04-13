#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import mysql.connector
import logging

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def get_db_connection():
    """Get database connection"""
    try:
        db_config = {
            'host': os.getenv('DB_HOST'),
            'database': os.getenv('DB_NAME'),
            'user': os.getenv('DB_USER'),
            'password': os.getenv('DB_PASSWORD')
        }
        
        conn = mysql.connector.connect(**db_config)
        conn.autocommit = True
        return conn
    except mysql.connector.Error as e:
        logger.error(f"Database connection error: {e}")
        # Persian error message for Telegram, but error is logged in English
        raise Exception(f"خطا در اتصال به پایگاه داده: {e}") 