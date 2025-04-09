#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os

class AdminMiddleware:
    """Middleware to check admin permissions"""
    
    def __init__(self):
        self.admin_id = int(os.getenv('ADMIN_TELEGRAM_ID'))
    
    def is_admin(self, user_id):
        """Check if user is admin"""
        return user_id == self.admin_id 