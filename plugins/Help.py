from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton


HELP_TEXT = """
<b>❗️How to Search Movies Here❓

▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬

1. Just Send Movie Name and Movie Released Year Correctly.

<blockquote>
Check Google for Correct Movie Spelling and Movie Released Year
</blockquote>

<b>Examples:</b>

<code>Oppam 2016</code>
<code>Baahubali 2015 1080p</code>

<blockquote>
For Getting only 1080p Quality Files
</blockquote>

▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬

<code>Baahubali 2015 Malayalam</code>
<code>Baahubali 2015 Tamil</code>

<blockquote>
For Dubbed Movie Files
</blockquote>

▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬

❗️On Android, Better Use VLC Media Player For Watch Movie's.

▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬

Cᴏɴᴛᴀᴄᴛ Bᴏᴛ Dᴇᴠᴇʟᴏᴘᴇʀ
(Oʀ) Rᴇᴘᴏʀᴛ Bᴜɢꜱ..!!

👉 @clsupportgroup
</b>
"""


# =========================================================
# Start Menu Help Button
# =========================================================

@Client.on_callback_query(filters.regex("^open_help$"))
async def open_help(client, query):

    buttons = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "📖 How To Use",
                    callback_data="help_howto"
                )
            ],
            [
                InlineKeyboardButton(
                    "👨‍💻 Developer",
                    url="https://t.me/clsupportgroup"
                )
            ],
            [
                InlineKeyboardButton(
                    "🔙 Close",
                    callback_data="help_close"
                )
            ]
        ]
    )

    await query.message.edit_text(
        "<b>👋 Welcome to Help Menu!</b>\n\n"
        "Choose an option below 👇",
        reply_markup=buttons
    )

    await query.answer()


# =========================================================
# /help command
# =========================================================

@Client.on_message(filters.command("help"))
async def generate_link(client, message):

    buttons = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "📖 How To Use",
                    callback_data="help_howto"
                )
            ],
            [
                InlineKeyboardButton(
                    "👨‍💻 Developer",
                    url="https://t.me/clsupportgroup"
                )
            ],
            [
                InlineKeyboardButton(
                    "🔙 Close",
                    callback_data="help_close"
                )
            ]
        ]
    )

    await message.reply(
        "<b>👋 Welcome to Help Menu!</b>\n\n"
        "Choose an option below 👇",
        reply_markup=buttons
    )


# =========================================================
# How To Use Button
# =========================================================

@Client.on_callback_query(filters.regex("^help_howto$"))
async def help_howto(client, query):

    buttons = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "🔙 Back",
                    callback_data="help_back"
                )
            ]
        ]
    )

    # 🟢 FIX START
    try:
        await query.message.edit_text(
            HELP_TEXT,
            reply_markup=buttons
        )
    except Exception as e:
        if "MESSAGE_NOT_MODIFIED" not in str(e):
            raise
    # 🟢 FIX END

    await query.answer()


# =========================================================
# Back Button
# =========================================================

@Client.on_callback_query(filters.regex("^help_back$"))
async def help_back(client, query):

    buttons = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "📖 How To Use",
                    callback_data="help_howto"
                )
            ],
            [
                InlineKeyboardButton(
                    "👨‍💻 Developer",
                    url="https://t.me/clsupportgroup"
                )
            ],
            [
                InlineKeyboardButton(
                    "🔙 Close",
                    callback_data="help_close"
                )
            ]
        ]
    )

    await query.message.edit_text(
        "<b>👋 Welcome to Help Menu!</b>\n\n"
        "Choose an option below 👇",
        reply_markup=buttons
    )

    await query.answer()


# =========================================================
# Close Button
# =========================================================

@Client.on_callback_query(filters.regex("^help_close$"))
async def help_close(client, query):

    await query.message.delete()
    await query.answer()
