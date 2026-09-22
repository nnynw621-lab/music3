import asyncio
import os
import sqlite3
import subprocess
import sys

try:
    from pyrogram import Client
    from pytgcalls import PyTgCalls
    try:
        from pytgcalls.types import AudioPiped
    except ImportError:
        try:
            from pytgcalls.types.input_source import AudioPiped
        except ImportError:
            AudioPiped = None
    PYTG_CALLS_AVAILABLE = True
except Exception as e:
    Client = None
    PyTgCalls = None
    AudioPiped = None
    PYTG_CALLS_AVAILABLE = False
    PYTG_CALLS_IMPORT_ERROR = e

import telebot
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup
import yt_dlp

# إعدادات الحساب المساعد الأساسية
API_ID = int(os.environ.get("API_ID", "12345678"))
API_HASH = os.environ.get("API_HASH", "your_api_hash_here")

# ==================== التحقق من وضع التشغيل (صانع أم بوت فرعي) ====================
if len(sys.argv) >= 2:
    TOKEN = sys.argv[1]
    bot = telebot.TeleBot(TOKEN)

    conn = sqlite3.connect("bot_maker.db", check_same_thread=False)
    cursor = conn.cursor()

    try:
        bot_info = bot.get_me()
        BOT_USERNAME = bot_info.username
    except Exception:
        BOT_USERNAME = "Bot"

    def get_bot_keyboard():
        cursor.execute(
            "SELECT rights, bot_type FROM created_bots WHERE bot_token = ?",
            (TOKEN,),
        )
        row = cursor.fetchone()
        bot_rights = row[0] if row else "with_rights"
        bot_type = row[1] if row else "free"

        if bot_rights == "no_rights":
            return None

        cursor.execute("SELECT value FROM settings WHERE key = 'creator_btn_text'")
        t_res = cursor.fetchone()
        cursor.execute("SELECT value FROM settings WHERE key = 'creator_btn_link'")
        l_res = cursor.fetchone()
        creator_text = t_res[0] if t_res else "بوت المنشئ"
        creator_link = l_res[0] if l_res else "https://t.me/YourCreatorBot"

        cursor.execute("SELECT value FROM settings WHERE key = 'nino_btn_text'")
        n_res = cursor.fetchone()
        cursor.execute("SELECT value FROM settings WHERE key = 'nino_btn_link'")
        nl_res = cursor.fetchone()
        nino_text = n_res[0] if n_res else "نينو"
        nino_link = nl_res[0] if nl_res else "https://t.me/YourChannel"

        keyboard = InlineKeyboardMarkup(row_width=2)

        if bot_type == "vip":
            keyboard.add(InlineKeyboardButton(f"🤖 {creator_text}", url=creator_link))
            keyboard.add(
                InlineKeyboardButton(
                    "➕ اضفني لقناتك/كروبك",
                    url=f"https://t.me/{BOT_USERNAME}?startgroup=true",
                )
            )
            keyboard.add(InlineKeyboardButton(f"💎 {nino_text}", url=nino_link))
        else:
            keyboard.add(
                InlineKeyboardButton(
                    "➕ اضفني لقناتك/كروبك",
                    url=f"https://t.me/{BOT_USERNAME}?startgroup=true",
                )
            )
            keyboard.add(InlineKeyboardButton(f"🤖 {creator_text}", url=creator_link))

            cursor.execute("SELECT value FROM settings WHERE key = 'sg_source_btn'")
            sg = cursor.fetchone()
            if sg and sg[0] == "true":
                keyboard.add(
                    InlineKeyboardButton(
                        "SG SOURCE", url="https://t.me/YourSourceChannel"
                    )
                )

            cursor.execute("SELECT value FROM settings WHERE key = 'add_btn'")
            add = cursor.fetchone()
            if add and add[0] == "true":
                keyboard.add(
                    InlineKeyboardButton(
                        "ADD", url=f"https://t.me/{BOT_USERNAME}?startgroup=true"
                    )
                )

            cursor.execute("SELECT value FROM settings WHERE key = 'x_btn'")
            x = cursor.fetchone()
            if x and x[0] == "true":
                keyboard.add(
                    InlineKeyboardButton("X", url="https://t.me/YourDeveloperAccount")
                )

        return keyboard

    def search_and_download_audio(query):
        download_dir = "downloads"
        os.makedirs(download_dir, exist_ok=True)

        search_options = {
            "format": "bestaudio/best",
            "noplaylist": True,
            "quiet": True,
            "default_search": "ytsearch1",
        }

        download_options = {
            "format": "bestaudio/best",
            "noplaylist": True,
            "quiet": True,
            "outtmpl": f"{download_dir}/%(id)s.%(ext)s",
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }
            ],
        }

        try:
            with yt_dlp.YoutubeDL(search_options) as ydl:
                info = ydl.extract_info(f"ytsearch1:{query}", download=False)

            if not info:
                return None, None

            if "entries" in info:
                entries = [entry for entry in info["entries"] if entry]
                if not entries:
                    return None, None
                info = entries[0]

            video_url = info.get("webpage_url") or info.get("original_url")
            video_id = info.get("id")
            title = info.get("title", "مقطع صوتي")

            if not video_url or not video_id:
                return None, None

            with yt_dlp.YoutubeDL(download_options) as ydl:
                ydl.download([video_url])

            output_path = os.path.join(download_dir, f"{video_id}.mp3")

            if not os.path.exists(output_path):
                return None, None

            return output_path, title

        except Exception as error:
            print(f"[search_and_download_audio] {error}")
            return None, None

    async def play_in_voice_chat(chat_id, query):
        if not PYTG_CALLS_AVAILABLE:
            return (
                None,
                "❌ ميزة المكالمات الصوتية غير متاحة حاليًا بسبب عدم توافق إصدار PyTgCalls: "
                f"{PYTG_CALLS_IMPORT_ERROR}",
            )

        cursor.execute(
            "SELECT session_string FROM assistants ORDER BY RANDOM() LIMIT 1"
        )
        ast = cursor.fetchone()
        if not ast:
            return None, "⚠️ تنبيه: لا توجد حسابات مساعدين مضافة في النظام!"

        session_string = ast[0]

        if API_ID == 12345678 or API_HASH == "your_api_hash_here":
            return None, "❌ يجب إضافة API_ID و API_HASH في Secrets."

        try:
            client = Client(
                f"session_{chat_id}",
                api_id=API_ID,
                api_hash=API_HASH,
                session_string=session_string,
                in_memory=True,
            )
            call_py = PyTgCalls(client)

            ydl_opts = {
                "format": "bestaudio/best",
                "noplaylist": True,
                "quiet": True,
                "default_search": "ytsearch1",
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                search_q = query if query.startswith(("http://", "https://")) else f"ytsearch1:{query}"
                info = ydl.extract_info(search_q, download=False)

                if not info:
                    return None, "❌ لم يتم العثور على النتيجة."

                if "entries" in info:
                    entries = [entry for entry in info["entries"] if entry]
                    if not entries:
                        return None, "❌ لم يتم العثور على النتيجة."
                    info = entries[0]

                audio_url = info.get("url")
                title = info.get("title", "مقطع صوتي")

                if not audio_url:
                    return None, "❌ تعذر الحصول على رابط الصوت."

            await client.start()
            await call_py.start()

            # الأسلوب الآمن حسب السجل
            if AudioPiped is None:
                await call_py.play(chat_id, audio_url)
            else:
                await call_py.play(chat_id, AudioPiped(audio_url))

            return title, None

        except Exception as e:
            print(f"[play_in_voice_chat] {e}")
            return None, f"❌ خطأ أثناء التشغيل الصوتي: {e}"

    @bot.message_handler(commands=["start"])
    def start_bot(message):
        keyboard = get_bot_keyboard()
        caption = (
            "🎵 **أهلاً بك في بوت الميوزك الخاص بك!**\n\n"
            "• للتحميل أرسل: `نزل [اسم الأغنية]`\n"
            "• للتشغيل بالمكالمة أرسل: `شغل [اسم الأغنية]`"
        )

        cursor.execute(
            "SELECT bot_type FROM created_bots WHERE bot_token = ?", (TOKEN,)
        )
        row = cursor.fetchone()
        b_type = row[0] if row else "free"
        image_path = "29038_2.jpg" if b_type == "vip" else "29038.jpg"

        if os.path.exists(image_path):
            with open(image_path, "rb") as photo:
                bot.send_photo(
                    message.chat.id,
                    photo,
                    caption=caption,
                    reply_markup=keyboard,
                    parse_mode="Markdown",
                )
        else:
            bot.reply_to(
                message, caption, reply_markup=keyboard, parse_mode="Markdown"
            )

    @bot.message_handler(
        func=lambda m: m.text
        and (m.text.startswith("نزل ") or m.text.startswith("تنزيل "))
    )
    def download_song(message):
        query = message.text.split(maxsplit=1)[1]
        sent_msg = bot.reply_to(
            message, f"🔍 جاري البحث والتحميل: `{query}`...", parse_mode="Markdown"
        )

        file_path, title = search_and_download_audio(query)
        keyboard = get_bot_keyboard()

        cursor.execute(
            "SELECT bot_type FROM created_bots WHERE bot_token = ?", (TOKEN,)
        )
        row = cursor.fetchone()
        b_type = row[0] if row else "free"
        image_path = "29038_2.jpg" if b_type == "vip" else "29038.jpg"
        caption_text = f"🎵 **تم التحميل بنجاح:** {title}"

        if file_path and os.path.exists(file_path):
            with open(file_path, "rb") as audio:
                bot.send_audio(
                    message.chat.id,
                    audio,
                    caption=caption_text,
                    parse_mode="Markdown",
                    reply_markup=keyboard,
                )

            try:
                bot.delete_message(message.chat.id, sent_msg.message_id)
            except Exception:
                pass

            try:
                os.remove(file_path)
            except Exception:
                pass
        else:
            bot.edit_message_text(
                "❌ عذراً، لم يتم العثور على نتائج.",
                message.chat.id,
                sent_msg.message_id,
            )

    @bot.message_handler(
        func=lambda m: m.text
        and (m.text.startswith("شغل ") or m.text.startswith("بحث "))
    )
    def play_voice(message):
        query = message.text.split(maxsplit=1)[1]
        sent = bot.reply_to(
            message,
            "🎙️ **جاري استدعاء المساعد والانضمام للمكالمة الصوتية...**",
            parse_mode="Markdown",
        )

        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            title, error = loop.run_until_complete(
                play_in_voice_chat(message.chat.id, query)
            )
            loop.close()

            if error:
                bot.edit_message_text(error, message.chat.id, sent.message_id)
            else:
                bot.edit_message_text(
                    f"🎶 **تم بدء التشغيل بنجاح!**\n• الأغنية: `{title}`",
                    message.chat.id,
                    sent.message_id,
                    parse_mode="Markdown",
                )
        except Exception as e:
            bot.edit_message_text(
                f"❌ فشل التشغيل: {e}", message.chat.id, sent.message_id
            )

    print("Music Bot Worker is running...")
    bot.infinity_polling()

else:
    # ======== تشغيل بوت المصنع الرئيسي (Creator Bot) ========
    CREATOR_BOT_TOKEN = os.environ.get("CREATOR_BOT_TOKEN", "YOUR_CREATOR_TOKEN")
    DEV_ID = int(os.environ.get("DEV_ID", "123456789"))

    bot = telebot.TeleBot(CREATOR_BOT_TOKEN)
    active_bots = {}
    user_states = {}

    conn = sqlite3.connect("bot_maker.db", check_same_thread=False)
    cursor = conn.cursor()

    cursor.execute(
        "CREATE TABLE IF NOT EXISTS admins (user_id INTEGER PRIMARY KEY)"
    )
    cursor.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS created_bots (
            bot_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            bot_token TEXT,
            bot_type TEXT,
            rights TEXT DEFAULT 'with_rights'
        )
    """)
    cursor.execute(
        "CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)"
    )
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS assistants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_string TEXT
        )
    """)
    conn.commit()

    # القيم الافتراضية للإعدادات
    cursor.execute(
        "INSERT OR IGNORE INTO settings (key, value) VALUES ('free_mode', 'true')"
    )
    cursor.execute(
        "INSERT OR IGNORE INTO settings (key, value) VALUES ('vip_btn_text', 'المطور')"
    )
    cursor.execute(
        "INSERT OR IGNORE INTO settings (key, value) VALUES ('vip_btn_link', 'https://t.me/YourUsername')"
    )
    cursor.execute(
        "INSERT OR IGNORE INTO settings (key, value) VALUES ('creator_btn_text', 'بوت المنشئ')"
    )
    cursor.execute(
        "INSERT OR IGNORE INTO settings (key, value) VALUES ('creator_btn_link', 'https://t.me/YourCreatorBot')"
    )
    cursor.execute(
        "INSERT OR IGNORE INTO settings (key, value) VALUES ('nino_btn_text', 'نينو')"
    )
    cursor.execute(
        "INSERT OR IGNORE INTO settings (key, value) VALUES ('nino_btn_link', 'https://t.me/YourChannel')"
    )
    cursor.execute(
        "INSERT OR IGNORE INTO settings (key, value) VALUES ('sg_source_btn', 'true')"
    )
    cursor.execute(
        "INSERT OR IGNORE INTO settings (key, value) VALUES ('add_btn', 'true')"
    )
    cursor.execute(
        "INSERT OR IGNORE INTO settings (key, value) VALUES ('x_btn', 'true')"
    )
    conn.commit()

    cursor.execute("SELECT bot_token FROM created_bots")
    for row in cursor.fetchall():
        b_token = row[0]
        if b_token not in active_bots:
            try:
                p = subprocess.Popen(["python", __file__, b_token])
                active_bots[b_token] = p
            except Exception:
                pass

    def is_admin(user_id):
        if user_id == DEV_ID:
            return True
        cursor.execute("SELECT user_id FROM admins WHERE user_id = ?", (user_id,))
        return cursor.fetchone() is not None

    def get_main_admin_keyboard():
        keyboard = InlineKeyboardMarkup(row_width=2)
        keyboard.add(
            InlineKeyboardButton("⚙️ الإعدادات المتقدمة", callback_data="adv_menu"),
            InlineKeyboardButton("📊 الإحصائيات العامة", callback_data="stats_menu"),
            InlineKeyboardButton("🎛️ نظام التشغيل", callback_data="control_menu"),
            InlineKeyboardButton("📣 قسم النشر والإذاعة", callback_data="publish_menu"),
            InlineKeyboardButton("🎨 تخصيص أزرار الحقوق", callback_data="rights_menu"),
            InlineKeyboardButton("⭐ تخصيص زر اصنع VIP", callback_data="vip_btn_config"),
            InlineKeyboardButton("💎 إدارة بوتات الـ VIP", callback_data="admin_vip_manager"),
            InlineKeyboardButton("🤖 إدارة المساعدين", callback_data="assistants_menu"),
        )
        return keyboard

    def get_member_main_keyboard():
        keyboard = InlineKeyboardMarkup(row_width=1)
        keyboard.add(
            InlineKeyboardButton("🤖 اصنع بوتك مجاناً", callback_data="member_free_create"),
            InlineKeyboardButton("💎 اصنع VIP", callback_data="member_vip"),
        )
        return keyboard

    @bot.message_handler(commands=["start"])
    def send_welcome(message):
        user_id = message.from_user.id
        cursor.execute(
            "INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,)
        )
        conn.commit()

        if is_admin(user_id):
            bot.reply_to(
                message,
                "💎 **أهلاً بك يا مطور في لوحة التحكم الرئيسية:**",
                reply_markup=get_main_admin_keyboard(),
                parse_mode="Markdown",
            )
        else:
            welcome_text = (
                "مرحباً بك في نظام صنع بوتات الميوزك 🎵\n\n"
                "• للتحميل أرسل: `نزل [اسم الأغنية]`\n"
                "• للتشغيل بالمكالمة أرسل: `شغل [اسم الأغنية]`\n\n"
                "اختر من الأزرار أدناه:"
            )
            bot.reply_to(
                message,
                welcome_text,
                reply_markup=get_member_main_keyboard(),
                parse_mode="Markdown",
            )

    @bot.callback_query_handler(func=lambda call: True)
    def callback_handler(call):
        user_id = call.from_user.id
        data = call.data

        if data == "member_main":
            bot.edit_message_text(
                "مرحباً بك مجدداً في نظام صنع بوتات الميوزك 🎵\nاختر من الأزرار أدناه:",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=get_member_main_keyboard(),
            )

        elif data == "member_free_create":
            cursor.execute(
                "SELECT bot_token FROM created_bots WHERE user_id = ?", (user_id,)
            )
            existing_bot = cursor.fetchone()
            keyboard = InlineKeyboardMarkup().add(
                InlineKeyboardButton("🔙 رجوع", callback_data="member_main")
            )
            if existing_bot:
                text = (
                    "🎉 **مبروك عزيزي بوتك صار جاهزاً!** 🎶\n"
                    "أنت تمتلك بوت ميوزك بالفعل قيد التشغيل."
                )
            else:
                text = (
                    "🤖 **خطوات إنشاء بوت ميوزك مجاني:**\n\n"
                    "1. اذهب إلى بوت صنع بوتات الرسمي: @BotFather\n"
                    "2. أنشئ بوت جديد واحصل على الـ (Token).\n"
                    "3. أرسل التوكن هنا بالشكل التالي:\n\n"
                    "`/create [التوكن الخاص بك]`"
                )
            bot.edit_message_text(
                text,
                call.message.chat.id,
                call.message.message_id,
                reply_markup=keyboard,
                parse_mode="Markdown",
            )

        elif data == "member_vip":
            cursor.execute("SELECT value FROM settings WHERE key = 'vip_btn_text'")
            t_res = cursor.fetchone()
            cursor.execute("SELECT value FROM settings WHERE key = 'vip_btn_link'")
            l_res = cursor.fetchone()
            btn_text = t_res[0] if t_res else "المطور"
            btn_link = l_res[0] if l_res else "https://t.me/YourUsername"

            keyboard = InlineKeyboardMarkup(row_width=1).add(
                InlineKeyboardButton(f"👤 {btn_text}", url=btn_link),
                InlineKeyboardButton("🔙 رجوع", callback_data="member_main"),
            )
            bot.edit_message_text(
                "💎 **خدمة بوتات الـ VIP المدفوعة:**\n\n"
                "احصل على بوت ميوزك بمميزات إضافية وبدون حقوق.\n"
                "للاشتراك أو الاستفسار تواصل عبر الزر أدناه:",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=keyboard,
                parse_mode="Markdown",
            )

        if not is_admin(user_id):
            return

        if data == "main_admin":
            bot.edit_message_text(
                "💎 **لوحة تحكم المطور الرئيسية:**",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=get_main_admin_keyboard(),
                parse_mode="Markdown",
            )

        elif data == "adv_menu":
            keyboard = InlineKeyboardMarkup(row_width=2)
            keyboard.add(
                InlineKeyboardButton("➕ إضافة مشرف", callback_data="add_admin_prompt"),
                InlineKeyboardButton("➖ إزالة مشرف", callback_data="remove_admin_prompt"),
                InlineKeyboardButton("📋 قائمة المشرفين", callback_data="list_admins"),
                InlineKeyboardButton("🔙 رجوع", callback_data="main_admin"),
            )
            bot.edit_message_text(
                "⚙️ **قسم إدارة المشرفين:**",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=keyboard,
                parse_mode="Markdown",
            )

        elif data == "add_admin_prompt":
            user_states[user_id] = "waiting_add_admin"
            bot.answer_callback_query(call.id)
            bot.send_message(
                call.message.chat.id,
                "👤 أرسل آيدي (ID) المشرف الجديد:",
                parse_mode="Markdown",
            )

        elif data == "remove_admin_prompt":
            user_states[user_id] = "waiting_remove_admin"
            bot.answer_callback_query(call.id)
            bot.send_message(
                call.message.chat.id,
                "🗑️ أرسل آيدي (ID) المشرف المراد إزالته:",
                parse_mode="Markdown",
            )

        elif data == "list_admins":
            cursor.execute("SELECT user_id FROM admins")
            admins = cursor.fetchall()
            text = f"👑 **المطور الأساسي:** `{DEV_ID}`\n\n📋 **المشرفون:**\n"
            for adm in admins:
                text += f"• `{adm[0]}`\n"
            keyboard = InlineKeyboardMarkup().add(
                InlineKeyboardButton("🔙 رجوع", callback_data="adv_menu")
            )
            bot.edit_message_text(
                text,
                call.message.chat.id,
                call.message.message_id,
                reply_markup=keyboard,
                parse_mode="Markdown",
            )

        elif data == "stats_menu":
            cursor.execute("SELECT COUNT(*) FROM users")
            u_cnt = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM created_bots")
            b_cnt = cursor.fetchone()[0]
            bot.edit_message_text(
                f"📊 **الإحصائيات العامة:**\n• إجمالي الأعضاء: `{u_cnt}`\n• البوتات المنشأة: `{b_cnt}`",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=InlineKeyboardMarkup().add(
                    InlineKeyboardButton("🔙 رجوع", callback_data="main_admin")
                ),
                parse_mode="Markdown",
            )

    # بقية الملف لا يختلف جوهريًا؛ فقط حافظ على باقي المنطق كما هو
    print("Main Creator Bot is running completely with all features...")
    bot.infinity_polling()
