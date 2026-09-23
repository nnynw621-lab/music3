import asyncio
import os
import sqlite3
import telebot
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup
from pyrogram import Client
from pytgcalls import PyTgCalls

# Support both PyTgCalls layouts used by compatible 2.x releases.
try:
    from pytgcalls.types.input_stream import AudioPiped
except ModuleNotFoundError:
    from pytgcalls.types import MediaStream as AudioPiped

import yt_dlp
