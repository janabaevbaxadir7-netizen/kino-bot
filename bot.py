import logging
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters, ConversationHandler
)
from database import Database

# Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Config
BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID"))

# States
WAIT_CODE, WAIT_VIDEO_CODE, WAIT_VIDEO_FILE, WAIT_BROADCAST = range(4)

db = Database()


# ─────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────

def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID


def main_menu_keyboard(user_id: int) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton("🎬 Kino kodi kiriting", callback_data="enter_code")],
        [InlineKeyboardButton("📂 Kategoriyalar", callback_data="categories")],
        [InlineKeyboardButton("⭐ Top kinolar", callback_data="top_movies")],
        [InlineKeyboardButton("ℹ️ Bot haqida", callback_data="about")],
    ]
    if is_admin(user_id):
        buttons.append([InlineKeyboardButton("⚙️ Admin Panel", callback_data="admin_panel")])
    return InlineKeyboardMarkup(buttons)


def admin_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton("📤 Video yuklash", callback_data="upload_video")],
        [InlineKeyboardButton("🗑️ Video o'chirish", callback_data="delete_video")],
        [InlineKeyboardButton("📊 Statistika", callback_data="stats")],
        [InlineKeyboardButton("📢 Hammaga xabar", callback_data="broadcast")],
        [InlineKeyboardButton("👥 Foydalanuvchilar", callback_data="users_list")],
        [InlineKeyboardButton("🔒 Botni yopish/ochish", callback_data="toggle_bot")],
        [InlineKeyboardButton("🔙 Orqaga", callback_data="main_menu")],
    ]
    return InlineKeyboardMarkup(buttons)


def categories_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton("🎥 Kinolar", callback_data="cat_movie")],
        [InlineKeyboardButton("📺 Seriallar", callback_data="cat_serial")],
        [InlineKeyboardButton("🎭 Multfilmlar", callback_data="cat_cartoon")],
        [InlineKeyboardButton("🔙 Orqaga", callback_data="main_menu")],
    ]
    return InlineKeyboardMarkup(buttons)


# ─────────────────────────────────────────
# START
# ─────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.add_user(user.id, user.username or "", user.first_name or "")

    if not db.is_bot_active() and not is_admin(user.id):
        await update.message.reply_text("🔒 Bot hozircha yopiq. Tez orada ochiladi!")
        return

    text = (
        f"👋 Salom, <b>{user.first_name}</b>!\n\n"
        "🎬 <b>Kino Man UZ</b> botiga xush kelibsiz!\n\n"
        "📌 Instagram'dagi kodlarni yozing va kinoni oling!"
    )
    await update.message.reply_text(
        text,
        parse_mode="HTML",
        reply_markup=main_menu_keyboard(user.id)
    )


# ─────────────────────────────────────────
# CALLBACK QUERY HANDLER
# ─────────────────────────────────────────

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    # ── Main menu ──
    if data == "main_menu":
        await query.edit_message_text(
            "🏠 Asosiy menyu:",
            reply_markup=main_menu_keyboard(user_id)
        )

    # ── Enter code ──
    elif data == "enter_code":
        await query.edit_message_text(
            "🔑 Kino kodini yozing:\n\n"
            "📌 Masalan: <code>KM001</code>",
            parse_mode="HTML"
        )
        context.user_data["waiting_code"] = True

    # ── Categories ──
    elif data == "categories":
        await query.edit_message_text(
            "📂 Kategoriyani tanlang:",
            reply_markup=categories_keyboard()
        )

    elif data in ("cat_movie", "cat_serial", "cat_cartoon"):
        cat_map = {"cat_movie": "movie", "cat_serial": "serial", "cat_cartoon": "cartoon"}
        cat_name = {"cat_movie": "🎥 Kinolar", "cat_serial": "📺 Seriallar", "cat_cartoon": "🎭 Multfilmlar"}
        videos = db.get_by_category(cat_map[data])
        if not videos:
            await query.edit_message_text(
                f"{cat_name[data]}\n\n❌ Hozircha bu kategoriyada kino yo'q.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Orqaga", callback_data="categories")]])
            )
        else:
            text = f"{cat_name[data]}\n\n"
            for v in videos[:20]:
                text += f"🎬 <b>{v['title']}</b> — Kod: <code>{v['code']}</code>\n"
            await query.edit_message_text(
                text,
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Orqaga", callback_data="categories")]])
            )

    # ── Top movies ──
    elif data == "top_movies":
        videos = db.get_top_videos()
        if not videos:
            await query.edit_message_text(
                "⭐ Top kinolar\n\n❌ Hozircha ma'lumot yo'q.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Orqaga", callback_data="main_menu")]])
            )
        else:
            text = "⭐ <b>Top 10 kinolar:</b>\n\n"
            for i, v in enumerate(videos, 1):
                text += f"{i}. 🎬 <b>{v['title']}</b> — {v['views']} marta ko'rilgan\nKod: <code>{v['code']}</code>\n\n"
            await query.edit_message_text(
                text,
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Orqaga", callback_data="main_menu")]])
            )

    # ── About ──
    elif data == "about":
        await query.edit_message_text(
            "ℹ️ <b>Kino Man UZ Bot</b>\n\n"
            "🎬 Kinolar, seriallar va multfilmlarni bir joyda toping!\n"
            "📌 Instagram'dagi kodlar orqali kino oling\n"
            "🆓 Butunlay bepul!\n\n"
            "📲 Instagram: @kino_man_uz",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Orqaga", callback_data="main_menu")]])
        )

    # ─────────────── ADMIN ───────────────

    elif data == "admin_panel":
        if not is_admin(user_id):
            await query.answer("❌ Ruxsat yo'q!", show_alert=True)
            return
        stats = db.get_stats()
        await query.edit_message_text(
            f"⚙️ <b>ADMIN PANEL</b>\n\n"
            f"👥 Jami foydalanuvchilar: <b>{stats['total_users']}</b>\n"
            f"🎬 Jami videolar: <b>{stats['total_videos']}</b>\n"
            f"📊 Bugungi kirishlar: <b>{stats['today_visits']}</b>\n"
            f"🔒 Bot holati: <b>{'Ochiq ✅' if db.is_bot_active() else 'Yopiq 🔒'}</b>",
            parse_mode="HTML",
            reply_markup=admin_keyboard()
        )

    elif data == "upload_video":
        if not is_admin(user_id):
            return
        await query.edit_message_text(
            "📤 <b>Video yuklash</b>\n\n"
            "1️⃣ Avval kino <b>kodini</b> yozing:\n"
            "📌 Masalan: <code>KM001</code>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Bekor qilish", callback_data="admin_panel")]])
        )
        context.user_data["state"] = "wait_video_code"

    elif data == "delete_video":
        if not is_admin(user_id):
            return
        await query.edit_message_text(
            "🗑️ <b>Video o'chirish</b>\n\n"
            "O'chirmoqchi bo'lgan kino <b>kodini</b> yozing:\n"
            "📌 Masalan: <code>KM001</code>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Bekor qilish", callback_data="admin_panel")]])
        )
        context.user_data["state"] = "wait_delete_code"

    elif data == "stats":
        if not is_admin(user_id):
            return
        stats = db.get_stats()
        top = db.get_top_videos(5)
        text = (
            f"📊 <b>Statistika</b>\n\n"
            f"👥 Jami foydalanuvchilar: <b>{stats['total_users']}</b>\n"
            f"🎬 Jami videolar: <b>{stats['total_videos']}</b>\n"
            f"📊 Bugungi kirishlar: <b>{stats['today_visits']}</b>\n"
            f"📈 Jami ko'rishlar: <b>{stats['total_views']}</b>\n\n"
            f"⭐ <b>Top 5 kino:</b>\n"
        )
        for i, v in enumerate(top, 1):
            text += f"{i}. {v['title']} — {v['views']} marta\n"
        await query.edit_message_text(
            text,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Orqaga", callback_data="admin_panel")]])
        )

    elif data == "broadcast":
        if not is_admin(user_id):
            return
        await query.edit_message_text(
            "📢 <b>Hammaga xabar yuborish</b>\n\n"
            "Xabar matnini yozing:",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Bekor qilish", callback_data="admin_panel")]])
        )
        context.user_data["state"] = "wait_broadcast"

    elif data == "users_list":
        if not is_admin(user_id):
            return
        users = db.get_users(limit=20)
        text = "👥 <b>So'nggi 20 foydalanuvchi:</b>\n\n"
        for u in users:
            username = f"@{u['username']}" if u['username'] else "—"
            text += f"👤 {u['first_name']} | {username} | ID: <code>{u['user_id']}</code>\n"
        await query.edit_message_text(
            text,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Orqaga", callback_data="admin_panel")]])
        )

    elif data == "toggle_bot":
        if not is_admin(user_id):
            return
        new_state = db.toggle_bot()
        state_text = "Ochiq ✅" if new_state else "Yopiq 🔒"
        await query.answer(f"Bot holati: {state_text}", show_alert=True)
        await query.edit_message_text(
            f"🔒 Bot holati o'zgartirildi: <b>{state_text}</b>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Orqaga", callback_data="admin_panel")]])
        )


# ─────────────────────────────────────────
# MESSAGE HANDLER
# ─────────────────────────────────────────

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text or ""
    state = context.user_data.get("state", "")

    if not db.is_bot_active() and not is_admin(user_id):
        await update.message.reply_text("🔒 Bot hozircha yopiq!")
        return

    # ── Admin: wait video code ──
    if state == "wait_video_code" and is_admin(user_id):
        context.user_data["new_video_code"] = text.strip().upper()
        await update.message.reply_text(
            f"✅ Kod: <code>{context.user_data['new_video_code']}</code>\n\n"
            "2️⃣ Endi kino <b>nomini</b> yozing:",
            parse_mode="HTML"
        )
        context.user_data["state"] = "wait_video_title"
        return

    if state == "wait_video_title" and is_admin(user_id):
        context.user_data["new_video_title"] = text.strip()
        await update.message.reply_text(
            f"✅ Nom: <b>{text.strip()}</b>\n\n"
            "3️⃣ Kategoriyani tanlang:",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🎥 Kino", callback_data="set_cat_movie")],
                [InlineKeyboardButton("📺 Serial", callback_data="set_cat_serial")],
                [InlineKeyboardButton("🎭 Multfilm", callback_data="set_cat_cartoon")],
            ])
        )
        context.user_data["state"] = "wait_video_category"
        return

    if state == "wait_video_file" and is_admin(user_id):
        if update.message.video or update.message.document:
            file_id = (update.message.video or update.message.document).file_id
            code = context.user_data.get("new_video_code", "")
            title = context.user_data.get("new_video_title", "")
            category = context.user_data.get("new_video_category", "movie")
            db.add_video(code, title, file_id, category)
            context.user_data.clear()
            await update.message.reply_text(
                f"✅ <b>Video muvaffaqiyatli saqlandi!</b>\n\n"
                f"🎬 Nom: <b>{title}</b>\n"
                f"🔑 Kod: <code>{code}</code>\n"
                f"📂 Kategoriya: {category}",
                parse_mode="HTML",
                reply_markup=admin_keyboard()
            )
        else:
            await update.message.reply_text("❌ Iltimos, video fayl yuboring!")
        return

    # ── Admin: delete video ──
    if state == "wait_delete_code" and is_admin(user_id):
        code = text.strip().upper()
        video = db.get_video(code)
        if video:
            db.delete_video(code)
            await update.message.reply_text(
                f"✅ <b>{video['title']}</b> o'chirildi!",
                parse_mode="HTML",
                reply_markup=admin_keyboard()
            )
        else:
            await update.message.reply_text(
                f"❌ <code>{code}</code> kodi topilmadi!",
                parse_mode="HTML"
            )
        context.user_data.clear()
        return

    # ── Admin: broadcast ──
    if state == "wait_broadcast" and is_admin(user_id):
        users = db.get_all_user_ids()
        success = 0
        for uid in users:
            try:
                await context.bot.send_message(uid, text, parse_mode="HTML")
                success += 1
            except Exception:
                pass
        context.user_data.clear()
        await update.message.reply_text(
            f"✅ Xabar yuborildi: <b>{success}/{len(users)}</b> foydalanuvchiga",
            parse_mode="HTML",
            reply_markup=admin_keyboard()
        )
        return

    # ── User: kino kodi ──
    if context.user_data.get("waiting_code") or (len(text) >= 2 and not text.startswith("/")):
        code = text.strip().upper()
        video = db.get_video(code)
        if video:
            db.increment_views(code)
            db.add_visit(user_id)
            await update.message.reply_video(
                video["file_id"],
                caption=f"🎬 <b>{video['title']}</b>\n🔑 Kod: <code>{code}</code>",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🏠 Bosh sahifa", callback_data="main_menu")
                ]])
            )
        else:
            await update.message.reply_text(
                f"❌ <code>{code}</code> — bunday kod topilmadi!\n\n"
                "📌 Instagram'dan to'g'ri kodni oling.",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🏠 Bosh sahifa", callback_data="main_menu")
                ]])
            )
        context.user_data["waiting_code"] = False


# ─────────────────────────────────────────
# CATEGORY SET CALLBACKS
# ─────────────────────────────────────────

async def set_category_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    cat_map = {"set_cat_movie": "movie", "set_cat_serial": "serial", "set_cat_cartoon": "cartoon"}
    cat_name = {"set_cat_movie": "🎥 Kino", "set_cat_serial": "📺 Serial", "set_cat_cartoon": "🎭 Multfilm"}
    data = query.data
    context.user_data["new_video_category"] = cat_map[data]
    context.user_data["state"] = "wait_video_file"
    await query.edit_message_text(
        f"✅ Kategoriya: <b>{cat_name[data]}</b>\n\n"
        "4️⃣ Endi <b>video faylni</b> yuboring:",
        parse_mode="HTML"
    )


# ─────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────

def main():
    db.init_db()
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(set_category_handler, pattern="^set_cat_"))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, message_handler))

    logger.info("Bot ishga tushdi...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
