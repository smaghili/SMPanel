#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from abc import ABC, abstractmethod
from telegram import Update
from telegram.ext import ContextTypes

class BaseCommand(ABC):
    """Base class for bot commands"""
    
    def __init__(self):
        pass
    
    @abstractmethod
    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle command"""
        pass 