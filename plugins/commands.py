import base64
import json
import logging
import os
import random
import re
import sys
import asyncio
from asyncio import sleep

import pymongo
from pyrogram import Client, enums, filters
from pyrogram.enums import ChatType
from pyrogram.errors import ChatAdminRequired, FloodWait, MessageDeleteForbidden
from pyrogram.errors.exceptions.bad_request_400 import MessageTooLong, PeerIdInvalid
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

from Script import script
from database.connections_mdb import active_connection
from database.ia_filterdb import Media, Mediaa, get_file_details, unpack_new_file_id, delete_files_below_threshold, db as clientDB, db1 as clientDB2, db2 as clientDB3
from database.users_chats_db import db
from info import (
    ADMINS, CHANNELS, LOG_CHANNEL, REQ_CHANNEL1, REQ_CHANNEL2, SUPPORT_CHAT,
    MELCOW_NEW_USERS, PICS, START_IMG, START_VID, DATABASE_URI, DATABASE_NAME,
    PROTECT_CONTENT, BATCH_FILE_CAPTION, CUSTOM_FILE_CAPTION
)
from plugins.pm_filter import auto_filter
from database.filters_mdb import add_filter
from utils import (
    get_settings, get_size, is_subscribed, is_requested_one, is_requested_two,
    save_group_settings, temp, check_loop_sub, check_loop_sub1, check_loop_sub2
)


logger = logging.getLogger(__name__)

from dotenv import load_dotenv

load_dotenv("./dynamic.env", override=True, encoding="utf-8")

BATCH_FILES = {}
ADD_FILTER_STATE = {}
BATCH_CREATE_STATE = {}
DS_REACT = ["⚡"]

should_run_check_loop_sub = False
should_run_check_loop_sub1 = False

inclient = pymongo.MongoClient(DATABASE_URI)
indb = inclient[DATABASE_NAME]
incol = indb['auto_del']
infile = indb['file_reply_text']
restarti = indb['restart']


async def admin_check(message: Message) -> bool:
    if not message.from_user:
        return False

    if message.chat.type not in [
        enums.ChatType.GROUP,
        enums.ChatType.SUPERGROUP
    ]:
        return False

    if message.from_user.id in [777000, 1087968824]:
        return True

    client = message._client
    chat_id = message.chat.id
    user_id = message.from_user.id

    check_status = await client.get_chat_member(
        chat_id=chat_id,
        user_id=user_id
    )

    admin_strings = [
        enums.ChatMemberStatus.OWNER,
        enums.ChatMemberStatus.ADMINISTRATOR
    ]

    if check_status.status not in admin_strings:
        return False
    else:
        return True


def convert_time_to_seconds(time_str):
    if time_str.endswith("s"):
        return int(time_str[:-1])
    elif time_str.endswith("m"):
        return int(time_str[:-1]) * 60
    elif time_str.endswith("h"):
        return int(time_str[:-1]) * 3600
    else:
        return 0


async def delete_after_2_minutes(msg):
    await asyncio.sleep(120)

    try:
        await msg.delete()
    except Exception:
        pass


async def delete_after_10_minutes(msg):
    await asyncio.sleep(600)

    try:
        await msg.delete()
    except Exception:
        pass


async def send_file(client, query, ident, file_id):
    files_ = await get_file_details(file_id)

    if not files_:
        return

    files = files_[0]

    title = files.file_name
    size = get_size(files.file_size)
    f_caption = files.file_name

    if CUSTOM_FILE_CAPTION:
        try:
            f_caption = CUSTOM_FILE_CAPTION.format(
                file_name='' if title is None else title,
                file_size='' if size is None else size,
                file_caption='' if f_caption is None else f_caption,
                mention=query.from_user.mention
            )
        except Exception as e:
            logger.exception(e)
            f_caption = f_caption

    if f_caption is None:
        f_caption = f"{title}"

    inline_keyboard = [[
        InlineKeyboardButton(
            '📌 ᴊᴏɪɴ ᴜᴘᴅᴀᴛᴇ ᴄʜᴀɴɴᴇʟ 📌',
            url='https://t.me/Clmainchannel'
        )
    ], [
        InlineKeyboardButton(
            '👥 ᴊᴏɪɴ ᴏᴜʀ ɢʀᴏᴜᴘ 👥',
            url='https://t.me/+Ik14BdOewjQzYjI1'
        )
    ]]

    reply_markup = InlineKeyboardMarkup(inline_keyboard)

    ok = await client.send_cached_media(
        chat_id=query.from_user.id,
        file_id=file_id,
        caption=f_caption,
        protect_content=True if ident == 'checksubp' else False,
        reply_markup=reply_markup
    )

    asyncio.create_task(delete_after_10_minutes(ok))


@Client.on_message(
    filters.command("batch") &
    filters.private &
    filters.user(ADMINS)
)
async def batch_command(client, message):

    BATCH_CREATE_STATE[message.from_user.id] = []

    await message.reply_text(
        "📦 <b>Batch Mode Started!</b>\n\n"
        "📤 Send your files one by one.\n"
        "✅ After sending all files, send /finish",
        parse_mode=enums.ParseMode.HTML
    )


@Client.on_message(
    (
        filters.document
        | filters.video
        | filters.audio
        | filters.animation
        | filters.photo
        | filters.sticker
        | filters.voice
        | filters.video_note
    )
    & filters.private
    & filters.user(ADMINS)
)
async def batch_file_handler(client, message):

    user_id = message.from_user.id

    if user_id not in BATCH_CREATE_STATE:
        return

    if message.text and message.text.startswith("/"):
        return

    BATCH_CREATE_STATE[user_id].append({
        "chat_id": message.chat.id,
        "message_id": message.id
    })

    count = len(BATCH_CREATE_STATE[user_id])

    await message.reply_text(
        f"✅ Item {count} added to batch."
    )


@Client.on_message(
    filters.command("finish") &
    filters.private &
    filters.user(ADMINS)
)
async def finish_batch(client, message):

    user_id = message.from_user.id
    files = BATCH_CREATE_STATE.get(user_id, [])

    if not files:
        await message.reply_text(
            "❌ Batch-ൽ files ഒന്നും ഇല്ല."
        )
        return

    await message.reply_text(
        "⏳ Batch link create ചെയ്യുന്നു..."
    )

    batch_data = json.dumps(
        files,
        ensure_ascii=False
    )

    file_name = f"batch_{user_id}.json"

    with open(
        file_name,
        "w",
        encoding="utf-8"
    ) as f:
        f.write(batch_data)

    sent = await client.send_document(
        chat_id=user_id,
        document=file_name,
        caption="📦 Batch data"
    )

    batch_file_id = sent.document.file_id

    batch_link = (
        f"https://t.me/{temp.U_NAME}"
        f"?start=BATCH-{batch_file_id}"
    )

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "🔗 OPEN BATCH",
                url=batch_link
            )
        ]
    ])

    await message.reply_text(
        f"✅ <b>Batch Created Successfully!</b>\n\n"
        f"📁 Files: {len(files)}\n"
        f"🔗 താഴെയുള്ള button അമർത്തി batch തുറക്കാം.",
        reply_markup=keyboard,
        parse_mode=enums.ParseMode.HTML
    )

    BATCH_CREATE_STATE.pop(
        user_id,
        None
    )

    try:
        os.remove(file_name)
    except:
        pass


@Client.on_message(
    filters.command("start") &
    filters.incoming
)
async def start(client, message):

    # Report to Admin
    if (
        len(message.command) == 2
        and message.command[1] == "report"
    ):
        await message.reply_text(
            text="""<blockquote>
❌ Wrong Format / തെറ്റായ ഫോർമാറ്റ്!

Please send your request in this format:
Movie Name + Year

Example:
Kuruthi 2019

💡 സിനിമയുടെ പേരിനൊപ്പം വർഷം കൂടി ടൈപ്പ് ചെയ്ത് ഇവിടെ അയക്കുക
</blockquote>""",
            parse_mode=enums.ParseMode.HTML
        )
        return

    if message.chat.type in [
        enums.ChatType.GROUP,
        enums.ChatType.SUPERGROUP
    ]:
        buttons = [
            [
                InlineKeyboardButton(
                    '👥 ᴊᴏɪɴ ᴏᴜʀ ɢʀᴏᴜᴘ 👥',
                    url='https://t.me/+Ik14BdOewjQzYjI1'
                )
            ],
            [
                InlineKeyboardButton(
                    '📌 ᴊᴏɪɴ ᴜᴘᴅᴀᴛᴇ ᴄʜᴀɴɴᴇʟ 📌',
                    url='https://t.me/Clmainchannel'
                )
            ],
            [
                InlineKeyboardButton(
                    '👥 ꜱᴜᴘᴘᴏʀᴛ ɢʀᴏᴜᴘ 👥',
                    url="https://t.me/clsupportgroup"
                ),
            ]
        ]

        reply_markup = InlineKeyboardMarkup(buttons)

        await message.reply(
            script.START_TXT.format(
                message.from_user.mention
                if message.from_user
                else message.chat.title,
                temp.U_NAME,
                temp.B_NAME
            ),
            reply_markup=reply_markup
        )

        await asyncio.sleep(2)

        if not await db.get_chat(message.chat.id):
            total = await client.get_chat_members_count(
                message.chat.id
            )

            await client.send_message(
                LOG_CHANNEL,
                script.LOG_TEXT_G.format(
                    message.chat.title,
                    message.chat.id,
                    total,
                    "Unknown"
                )
            )

            await db.add_chat(
                message.chat.id,
                message.chat.title
            )

        return

    if not await db.is_user_exist(
        message.from_user.id
    ):
        await db.add_user(
            message.from_user.id,
            message.from_user.first_name
        )

        await client.send_message(
            LOG_CHANNEL,
            script.LOG_TEXT_P.format(
                message.from_user.id,
                message.from_user.mention
            )
        )

    # For Achu Vj
    if (
        len(message.command) != 2
        or message.command[1] in [
            "subscribe",
            "error",
            "okay",
            "help"
        ]
    ):
        buttons = [[
            InlineKeyboardButton(
                '➕ ᴀᴅᴅ ᴍᴇ ᴛᴏ ʏᴏᴜʀ ɢʀᴏᴜᴘꜱ ➕',
                url=f'http://t.me/{temp.U_NAME}?startgroup=true'
            )
        ], [
            InlineKeyboardButton(
                '🔍 ꜱᴇᴀʀᴄʜ 🔎',
                switch_inline_query_current_chat=''
            ),
            InlineKeyboardButton(
                '📣 ᴜᴘᴅᴀᴛᴇꜱ 📣',
                url='https://t.me/Clmainchannel'
            )
        ], [
            InlineKeyboardButton(
                'ℹ️ ʜᴇʟᴘ ℹ️',
                callback_data='help'
            ),
            InlineKeyboardButton(
                '📍 ᴀʙᴏᴜᴛ 📍',
                callback_data='about'
            )
        ]]

        reply_markup = InlineKeyboardMarkup(buttons)

        caption_text = script.START_TXT.format(
            message.from_user.mention,
            temp.U_NAME,
            temp.B_NAME
        )

        try:
            await message.reply_video(
                video=START_VID,
                caption=caption_text,
                reply_markup=reply_markup,
                parse_mode=enums.ParseMode.HTML
            )

        except Exception as video_error:
            logger.error(
                f"Achu മോനെ Video work ആയില്ല, കാരണം: {video_error}"
            )

            try:
                await message.reply_photo(
                    photo=START_IMG,
                    caption=caption_text,
                    reply_markup=reply_markup,
                    parse_mode=enums.ParseMode.HTML
                )

            except Exception as photo_error:
                logger.error(
                    f"Photo-യും മൂഞ്ചി, കാരണം: {photo_error}"
                )

                await message.reply_text(
                    text=caption_text,
                    reply_markup=reply_markup,
                    parse_mode=enums.ParseMode.HTML
                )

    check = False
    if REQ_CHANNEL1 and not await is_requested_one(client, message):
        btn = [[
            InlineKeyboardButton(
                "📌 ᴊᴏɪɴ ᴛᴏ ʀᴇQᴜᴇꜱᴛ ᴄʜᴀɴɴᴇʟ 📌",
                url=client.req_link1
            )
        ]]

        should_run_check_loop_sub1 = True
        should_run_check_loop_sub = False

        try:
            if REQ_CHANNEL2 and not await is_requested_two(client, message):
                btn.append([
                    InlineKeyboardButton(
                        "📌 ᴊᴏɪɴ ᴛᴏ ʀᴇQᴜᴇꜱᴛ ᴄʜᴀɴɴᴇʟ 📌",
                        url=client.req_link2
                    )
                ])

                should_run_check_loop_sub = True

        except Exception as e:
            print(e)

        if message.command[1] != "subscribe":
            try:
                kk, file_id = message.command[1].split("_", 1)

                pre = (
                    'checksubp'
                    if kk == 'filep'
                    else 'checksub'
                )

                btn.append([
                    InlineKeyboardButton(
                        "🔄 ᴛʀʏ ᴀɢᴀɪɴ 🔄",
                        callback_data=f"{pre}#{file_id}"
                    )
                ])

            except (IndexError, ValueError):
                btn.append([
                    InlineKeyboardButton(
                        "🔄 ᴛʀʏ ᴀɢᴀɪɴ 🔄",
                        url=f"https://t.me/{temp.U_NAME}?start={message.command[1]}"
                    )
                ])

        sh = await client.send_message(
            chat_id=message.from_user.id,
            text="""**♦️ ʀᴇᴀᴅ ᴛʜɪꜱ ɪɴꜱᴛʀᴜᴄᴛɪᴏɴ ♦️

നിങ്ങൾ ചോദിക്കുന്ന സിനിമകൾ ലഭിക്കണം എന്നുണ്ടെങ്കിൽ നിങ്ങൾ ഞങ്ങളുടെ ചാനലിൽ ജോയിൻ ചെയ്തിരിക്കണം. ജോയിൻ ചെയ്യാൻ 📌 ᴊᴏɪɴ ᴛᴏ ʀᴇQᴜᴇꜱᴛ ᴄʜᴀɴɴᴇʟ 📌 എന്ന ബട്ടണിൽ ക്ലിക്ക് ചെയ്യാവുന്നതാണ്.

ജോയിൻ ചെയ്ത ശേഷം 🔄 ᴛʀʏ ᴀɢᴀɪɴ 🔄 എന്ന ബട്ടണിൽ അമർത്തിയാൽ നിങ്ങൾക്ക് ഞാൻ ആ സിനിമ അയച്ചു തരുന്നതാണ്.

CLICK ✺ 𝐽𝑂𝐼𝑁 𝑈𝑃𝐷𝐴𝑇𝐸 𝐶𝐻𝑁𝑁𝑁𝐸𝐿 ✺ AND THEN CLICK 🔄 ᴛʀʏ ᴀɢᴀɪɴ 🔄 BUTTON TO GET MOVIE FILE 🗃️**""",
            reply_markup=InlineKeyboardMarkup(btn),
            parse_mode=enums.ParseMode.MARKDOWN
        )

        if should_run_check_loop_sub:
            check = await check_loop_sub(
                client,
                message
            )

        elif should_run_check_loop_sub1:
            check = await check_loop_sub1(
                client,
                message
            )

        if check:
            await send_file(
                client,
                message,
                pre,
                file_id
            )

            await sh.delete()
            return

        else:
            return False

    if REQ_CHANNEL2 and not await is_requested_two(
        client,
        message
    ):
        btn = [[
            InlineKeyboardButton(
                "Update Channel 2",
                url=client.req_link2
            )
        ]]

        if message.command[1] != "subscribe":
            try:
                kk, file_id = message.command[1].split("_", 1)

                pre = (
                    'checksubp'
                    if kk == 'filep'
                    else 'checksub'
                )

                btn.append([
                    InlineKeyboardButton(
                        "🔄 ᴛʀʏ ᴀɢᴀɪɴ 🔄",
                        callback_data=f"{pre}#{file_id}"
                    )
                ])

            except (IndexError, ValueError):
                btn.append([
                    InlineKeyboardButton(
                        "🔄 ᴛʀʏ ᴀɢᴀɪɴ 🔄",
                        url=f"https://t.me/{temp.U_NAME}?start={message.command[1]}"
                    )
                ])

        sh = await client.send_message(
            chat_id=message.from_user.id,
            text="""**♦️ ʀᴇᴀᴅ ᴛʜɪꜱ ɪɴꜱᴛʀᴜᴄᴛɪᴏɴ ♦️

നിങ്ങൾ ചോദിക്കുന്ന സിനിമകൾ ലഭിക്കണം എന്നുണ്ടെങ്കിൽ നിങ്ങൾ ഞങ്ങളുടെ ചാനലിൽ ജോയിൻ ചെയ്തിരിക്കണം. ജോയിൻ ചെയ്യാൻ 📌 ᴊᴏɪɴ ᴛᴏ ʀᴇQᴜᴇꜱᴛ ᴄʜᴀɴɴᴇʟ 📌 എന്ന ബട്ടണിൽ ക്ലിക്ക് ചെയ്യാവുന്നതാണ്.

ജോയിൻ ചെയ്ത ശേഷം 🔄ᴛʀʏ ᴀɢᴀɪɴ 🔄 എന്ന ബട്ടണിൽ അമർത്തിയാൽ നിങ്ങൾക്ക് ഞാൻ ആ സിനിമ അയച്ചു തരുന്നതാണ്.

ജോയിൻ ചെയ്ത ശേഷം 🔄 ᴛʀʏ ᴀɢᴀɪɴ 🔄 എന്ന ബട്ടണിൽ അമർത്തിയാൽ നിങ്ങൾക്ക് ഞാൻ ആ സിനിമ അയച്ചു തരുന്നതാണ്.

CLICK 📌 ᴊᴏɪɴ ᴛᴏ ʀᴇQᴜᴇꜱᴛ ᴄʜᴀɴɴᴇʟ 📌 AND THEN CLICK🔄ᴛʀʏ ᴀɢᴀɪɴ🔄 BUTTON TO GET MOVIE FILE 🗃️**""",
            reply_markup=InlineKeyboardMarkup(btn),
            parse_mode=enums.ParseMode.MARKDOWN
        )

        check = await check_loop_sub2(
            client,
            message
        )

        if check:
            await send_file(
                client,
                message,
                pre,
                file_id
            )

            await sh.delete()
            return

        else:
            return False

    if (
        len(message.command) == 2
        and message.command[1].startswith('getfile')
    ):
        searches = message.command[1].split("-", 1)[1]
        search = searches.replace('-', ' ')

        message.text = search

        await auto_filter(
            client,
            message
        )

        return

    if (
        len(message.command) == 2
        and message.command[1] in [
            "subscribe",
            "error",
            "okay",
            "help"
        ]
    ):
        buttons = [
            [
                InlineKeyboardButton(
                    '👥 ᴊᴏɪɴ ᴏᴜʀ ɢʀᴏᴜᴘ 👥',
                    url='https://t.me/+Ik14BdOewjQzYjI1'
                )
            ],
            [
                InlineKeyboardButton(
                    '📌 ᴊᴏɪɴ ᴜᴘᴅᴀᴛᴇ ᴄʜᴀɴɴᴇʟ 📌',
                    url='https://t.me/Clmainchannel'
                )
            ],
            [
                InlineKeyboardButton(
                    '👥 ꜱᴜᴘᴘᴏʀᴛ ɢʀᴏᴜᴘ 👥',
                    url="https://t.me/clsupportgroup"
                )
            ]
        ]

        reply_markup = InlineKeyboardMarkup(buttons)

        await message.reply_video(
            video="https://envs.sh/_O0.mp4",
            caption=script.START_TXT.format(
                message.from_user.mention,
                temp.U_NAME,
                temp.B_NAME
            ),
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )

        return

    if len(message.command) < 2:
    return

    data = message.command[1]

    try:
        pre, file_id = data.split("_", 1)

    except ValueError:
        file_id = data
        pre = ""

    if data.split("-", 1)[0] == "BATCH":
        sts = await message.reply(
            "Please wait..."
        )

        batch_file_id = data.split("-", 1)[1]

        msgs = BATCH_FILES.get(
            batch_file_id
        )

        if not msgs:
            file = None

            try:
                file = await client.download_media(
                    batch_file_id
                )

                with open(
                    file,
                    encoding="utf-8"
                ) as file_data:
                    msgs = json.loads(
                        file_data.read()
                    )

                BATCH_FILES[
                    batch_file_id
                ] = msgs

            except Exception as e:
                logger.exception(e)

                await sts.edit(
                    "❌ Unable to open batch."
                )

                return

            finally:
                if file:
                    try:
                        os.remove(file)

                    except OSError:
                        pass

        for item in msgs:
            try:
                copied = await client.copy_message(
                    chat_id=message.from_user.id,
                    from_chat_id=item["chat_id"],
                    message_id=item["message_id"],
                )

                asyncio.create_task(
                    delete_after_10_minutes(
                        copied
                    )
                )

                await asyncio.sleep(1)

            except FloodWait as e:
                await asyncio.sleep(
                    e.value
                )

            except Exception as e:
                logger.exception(e)
                continue

        await sts.delete()
        return

    elif data.split("-", 1)[0] == "DSTORE":
        sts = await message.reply(
            "Please wait"
        )

        b_string = data.split("-", 1)[1]

        try:
            decoded = (
                base64.urlsafe_b64decode(
                    b_string
                    + "=" * (-len(b_string) % 4)
                )
                .decode("ascii")
            )

            try:
                f_msg_id, l_msg_id, f_chat_id, protect = decoded.split(
                    "_",
                    3
                )

            except ValueError:
                f_msg_id, l_msg_id, f_chat_id = decoded.split(
                    "_",
                    2
                )

                protect = (
                    "/pbatch"
                    if PROTECT_CONTENT
                    else "batch"
                )

            async for msg in client.iter_messages(
                int(f_chat_id),
                int(l_msg_id),
                int(f_msg_id)
            ):
                if msg.media:
                    media = getattr(
                        msg,
                        msg.media
                    )

                    if BATCH_FILE_CAPTION:
                        try:
                            f_caption = BATCH_FILE_CAPTION.format(
                                file_name=getattr(
                                    media,
                                    "file_name",
                                    ""
                                ),
                                file_size=getattr(
                                    media,
                                    "file_size",
                                    ""
                                ),
                                file_caption=getattr(
                                    msg,
                                    "caption",
                                    ""
                                ),
                            )

                        except Exception as e:
                            logger.exception(e)

                            f_caption = getattr(
                                msg,
                                "caption",
                                ""
                            )

                    else:
                        file_name = getattr(
                            media,
                            "file_name",
                            ""
                        )

                        f_caption = (
                            getattr(
                                msg,
                                "caption",
                                None
                            )
                            or file_name
                        )

                    try:
                        await msg.copy(
                            message.chat.id,
                            caption=f_caption,
                            protect_content=(
                                True
                                if protect == "/pbatch"
                                else False
                            ),
                        )

                    except FloodWait as e:
                        await asyncio.sleep(
                            e.value
                        )

                        await msg.copy(
                            message.chat.id,
                            caption=f_caption,
                            protect_content=(
                                True
                                if protect == "/pbatch"
                                else False
                            ),
                        )

                    except Exception as e:
                        logger.exception(e)
                        continue

                elif msg.empty:
                    continue

                else:
                    try:
                        await msg.copy(
                            message.chat.id,
                            protect_content=(
                                True
                                if protect == "/pbatch"
                                else False
                            ),
                        )

                    except FloodWait as e:
                        await asyncio.sleep(
                            e.value
                        )

                        await msg.copy(
                            message.chat.id,
                            protect_content=(
                                True
                                if protect == "/pbatch"
                                else False
                            ),
                        )

                    except Exception as e:
                        logger.exception(e)
                        continue

                await asyncio.sleep(1)

            await sts.delete()

        except Exception as e:
            logger.exception(e)

            await sts.edit(
                "❌ Unable to process batch."
            )

        return

    files_ = await get_file_details(
        file_id
    )

    if not files_:
        pre, file_id = (
            (
                base64.urlsafe_b64decode(
                    data
                    + "=" * (-len(data) % 4)
                )
            )
            .decode("ascii")
            .split("_", 1)
        )

        try:
            msg = await client.send_cached_media(
                chat_id=message.from_user.id,
                file_id=file_id,
                protect_content=(
                    True
                    if pre == 'filep'
                    else False
                ),
            )

            filetype = msg.media

            file = getattr(
                msg,
                filetype
            )

            title = file.file_name
            size = get_size(
                file.file_size
            )

            f_caption = (
                f"<code>{title}</code>"
            )

            if CUSTOM_FILE_CAPTION:
                try:
                    f_caption = CUSTOM_FILE_CAPTION.format(
                        file_name='' if title is None else title,
                        file_size='' if size is None else size,
                        file_caption='' if f_caption is None else f_caption,
                        mention=message.from_user.mention
                    )

                except Exception:
                    return

            await msg.edit_caption(
                f_caption
            )

            return

        except Exception:
            pass

        return await message.reply(
            'No such file exist.'
        )

    files = files_[0]

    title = files.file_name

    size = get_size(
        files.file_size
    )

    f_caption = files.caption

    if CUSTOM_FILE_CAPTION:
        try:
            f_caption = CUSTOM_FILE_CAPTION.format(
                file_name='' if title is None else title,
                file_size='' if size is None else size,
                file_caption='' if f_caption is None else f_caption,
                mention=message.from_user.mention
            )

        except Exception as e:
            logger.exception(e)

            f_caption = f_caption

    if f_caption is None:
        f_caption = f"{title}"

        f_caption += (
            "\n\n⚠️ This file will be deleted automatically in 2 minutes."
            "\n📌 Please save/forward it before deletion."
        )

    xd = await client.send_cached_media(
        chat_id=message.from_user.id,
        file_id=file_id,
        caption=f_caption,
        protect_content=(
            True
            if pre == 'filep'
            else False
        ),
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    '👥 ᴊᴏɪɴ ᴏᴜʀ ɢʀᴏᴜᴘ 👥',
                    url='https://t.me/+Ik14BdOewjQzYjI1'
                )
            ],
            [
                InlineKeyboardButton(
                    '📌 ᴊᴏɪɴ ᴜᴘᴅᴀᴛᴇ ᴄʜᴀɴɴᴇʟ 📌',
                    url='https://t.me/Clmainchannel'
                )
            ],
            [
                InlineKeyboardButton(
                    'ℹ️ ᴠɪᴇᴡ ᴀᴜᴅɪᴏ & ꜱᴜʙꜱ ɪɴꜰᴏ ℹ️',
                    callback_data=f'extract_data:{file_id}'
                )
            ]
        ])
    )

    asyncio.create_task(
        delete_after_2_minutes(xd)
    )


@Client.on_message(
    filters.command('channel')
    & filters.user(ADMINS)
)
async def channel_info(
    bot,
    message
):

    """Send basic information of channel"""

    if isinstance(CHANNELS, (int, str)):
        channels = [CHANNELS]

    elif isinstance(CHANNELS, list):
        channels = CHANNELS

    else:
        raise ValueError(
            "Unexpected type of CHANNELS"
        )

    text = '📑 **Indexed channels/groups**\n'
    if not channels:
        await message.reply_text(
            "No channels configured."
        )
        return

    for channel in channels:
        try:
            chat = await bot.get_chat(
                channel
            )

            text += (
                f"\n• `{chat.id}` — "
                f"{chat.title}"
            )

        except Exception as e:
            logger.exception(e)

            text += (
                f"\n• `{channel}` — "
                f"Unable to fetch"
            )

    await message.reply_text(
        text
    )


@Client.on_message(
    filters.command(
        [
            "stats",
            "status"
        ]
    )
    & filters.user(ADMINS)
)
async def get_stats(
    bot,
    message
):

    total = await Media.count_documents({})

    await message.reply_text(
        f"📊 **Database Statistics**\n\n"
        f"📁 Total Files: `{total}`"
    )


@Client.on_message(
    filters.command("delete")
    & filters.user(ADMINS)
)
async def delete_files(
    bot,
    message
):

    if len(message.command) < 2:
        await message.reply_text(
            "Use `/delete <file_id>`"
        )
        return

    file_id = message.command[1]

    result = await Media.delete_one(
        {
            "file_id": file_id
        }
    )

    if result.deleted_count:
        await message.reply_text(
            "✅ File deleted successfully."
        )

    else:
        await message.reply_text(
            "❌ File not found."
        )


@Client.on_message(
    filters.command("deletefiles")
    & filters.user(ADMINS)
)
async def deletefiles(
    bot,
    message
):

    if len(message.command) < 2:
        await message.reply_text(
            "Use `/deletefiles <number>`"
        )
        return

    try:
        number = int(
            message.command[1]
        )

    except ValueError:
        await message.reply_text(
            "❌ Invalid number."
        )
        return

    result = await delete_files_below_threshold(
        number
    )

    await message.reply_text(
        f"✅ Deleted `{result}` files."
    )


@Client.on_message(
    filters.command("filter")
    & filters.group
)
async def filter_command(
    client,
    message
):

    if not await admin_check(message):
        await message.reply_text(
            "❌ Only group admins can use this command."
        )
        return

    if len(message.command) < 2:
        await message.reply_text(
            "❌ Usage:\n"
            "`/filter keyword`\n\n"
            "Example:\n"
            "`/filter leo`",
            parse_mode=enums.ParseMode.MARKDOWN
        )
        return

    keyword = " ".join(
        message.command[1:]
    ).lower()

    ADD_FILTER_STATE[
        message.from_user.id
    ] = {
        "chat_id": message.chat.id,
        "keyword": keyword,
        "message_id": message.id
    }

    await message.reply_text(
        "📸 Now send the poster/photo.\n\n"
        "After sending the photo, send the custom caption text."
    )


@Client.on_message(
    filters.photo
    & filters.group
)
async def filter_photo_handler(
    client,
    message
):

    if not await admin_check(message):
        return

    user_id = message.from_user.id

    if user_id not in ADD_FILTER_STATE:
        return

    data = ADD_FILTER_STATE[user_id]

    data["photo_file_id"] = (
        message.photo.file_id
    )

    await message.reply_text(
        "✅ Poster saved.\n\n"
        "Now send the custom text/caption."
    )


@Client.on_message(
    filters.text
    & filters.group
)
async def filter_caption_handler(
    client,
    message
):

    if message.text.startswith("/"):
        return

    if not await admin_check(message):
        return

    user_id = message.from_user.id

    if user_id not in ADD_FILTER_STATE:
        return

    data = ADD_FILTER_STATE[user_id]

    if "photo_file_id" not in data:
        return

    keyword = data["keyword"]
    photo_file_id = data["photo_file_id"]
    caption = message.text

    try:
        await add_filter(
            message.chat.id,
            keyword,
            caption,
            photo_file_id
        )

    except TypeError:
        try:
            await add_filter(
                message.chat.id,
                keyword,
                caption
            )

        except Exception as e:
            logger.exception(e)

            await message.reply_text(
                f"❌ Filter save failed:\n`{e}`"
            )

            ADD_FILTER_STATE.pop(
                user_id,
                None
            )

            return

    display_caption = (
        caption
        or f"🔎 Search Results For: {keyword}"
    )

    try:
        import html

        display_caption = (
            f"<blockquote>"
            f"<b>{html.escape(display_caption)}</b>"
            f"</blockquote>"
        )

    except Exception:
        display_caption = (
            f"<blockquote>"
            f"<b>{display_caption}</b>"
            f"</blockquote>"
        )

    await message.reply_text(
        "✅ Filter added successfully!"
    )

    ADD_FILTER_STATE.pop(
        user_id,
        None
    )


@Client.on_message(
    filters.command("filters")
    & filters.group
)
async def filters_command(
    client,
    message
):

    if not await admin_check(message):
        await message.reply_text(
            "❌ Only group admins can use this command."
        )
        return

    chat_id = message.chat.id

    try:
        from database.filters_mdb import get_filters

        filters_list = await get_filters(
            chat_id
        )

    except Exception as e:
        logger.exception(e)

        await message.reply_text(
            "❌ Unable to fetch filters."
        )
        return

    if not filters_list:
        await message.reply_text(
            "📭 No filters found."
        )
        return

    text = "📋 **Available Filters:**\n\n"

    for item in filters_list:
        try:
            keyword = (
                item.get("keyword")
                or item.get("name")
                or ""
            )

            text += (
                f"• `{keyword}`\n"
            )

        except Exception:
            continue

    await message.reply_text(
        text
    )


@Client.on_message(
    filters.command("deletefilter")
    & filters.group
)
async def delete_filter_command(
    client,
    message
):

    if not await admin_check(message):
        await message.reply_text(
            "❌ Only group admins can use this command."
        )
        return

    if len(message.command) < 2:
        await message.reply_text(
            "❌ Usage: `/deletefilter keyword`"
        )
        return

    keyword = " ".join(
        message.command[1:]
    ).lower()

    try:
        from database.filters_mdb import delete_filter

        result = await delete_filter(
            message.chat.id,
            keyword
        )

        await message.reply_text(
            "✅ Filter deleted."
            if result
            else "❌ Filter not found."
        )

    except Exception as e:
        logger.exception(e)

        await message.reply_text(
            f"❌ Error:\n`{e}`"
        )


@Client.on_message(
    filters.command("alldeletefilters")
    & filters.group
)
async def delete_all_filters(
    client,
    message
):

    if not await admin_check(message):
        await message.reply_text(
            "❌ Only group admins can use this command."
        )
        return

    try:
        from database.filters_mdb import delete_all_filters as remove_all

        await remove_all(
            message.chat.id
        )

        await message.reply_text(
            "✅ All filters deleted."
        )

    except Exception as e:
        logger.exception(e)

        await message.reply_text(
            f"❌ Error:\n`{e}`"
       )

@Client.on_message(
    filters.command("autodel")
    & filters.user(ADMINS)
)
async def auto_delete(
    client,
    message
):

    args = message.command[1:]

    if not args:
        await message.reply_text(
            "❌ Usage:\n"
            "`/autodel 10m`\n"
            "`/autodel 1h`\n"
            "`/autodel 0`"
        )
        return

    numb = args[0]

    if "0" in numb:
        await db.set_auto_delete(
            message.chat.id,
            0
        )

        await message.reply_text(
            "✅ Auto delete disabled."
        )
        return

    seconds = convert_time_to_seconds(
        numb
    )

    if seconds <= 0:
        await message.reply_text(
            "❌ Invalid time.\n\n"
            "Examples:\n"
            "`10s`\n"
            "`10m`\n"
            "`1h`"
        )
        return

    await db.set_auto_delete(
        message.chat.id,
        seconds
    )

    await message.reply_text(
        f"✅ Auto delete set to `{numb}`."
    )


@Client.on_message(
    filters.command("settings")
    & filters.group
)
async def settings(
    client,
    message
):

    if not await admin_check(message):
        await message.reply_text(
            "❌ Only group admins can use this command."
        )
        return

    try:
        settings = await get_settings(
            message.chat.id
        )

    except Exception as e:
        logger.exception(e)

        await message.reply_text(
            "❌ Unable to load settings."
        )
        return

    text = (
        "⚙️ **Group Settings**\n\n"
        f"Auto Delete: `{settings.get('auto_delete', 0)}`\n"
        f"Auto Filter: `{settings.get('auto_filter', True)}`\n"
        f"Protect Content: `{settings.get('protect_content', False)}`"
    )

    await message.reply_text(
        text
    )


@Client.on_message(
    filters.command("setcaption")
    & filters.user(ADMINS)
)
async def set_caption(
    client,
    message
):

    if len(message.command) < 2:
        await message.reply_text(
            "❌ Please provide a caption."
        )
        return

    caption = message.text.split(
        None,
        1
    )[1]

    await db.set_caption(
        caption
    )

    await message.reply_text(
        "✅ Caption updated."
    )


@Client.on_message(
    filters.command("delcaption")
    & filters.user(ADMINS)
)
async def delete_caption(
    client,
    message
):

    await db.set_caption(
        None
    )

    await message.reply_text(
        "✅ Caption removed."
    )


@Client.on_message(
    filters.command("id")
)
async def get_id(
    client,
    message
):

    if message.reply_to_message:
        msg = message.reply_to_message

        if msg.forward_from_chat:
            await message.reply_text(
                f"Chat ID: `{msg.forward_from_chat.id}`"
            )
            return

        await message.reply_text(
            f"Message ID: `{msg.id}`\n"
            f"Chat ID: `{msg.chat.id}`"
        )
        return

    await message.reply_text(
        f"Your ID: `{message.from_user.id}`\n"
        f"Chat ID: `{message.chat.id}`"
    )


@Client.on_message(
    filters.command("info")
)
async def info(
    client,
    message
):

    if not message.reply_to_message:
        await message.reply_text(
            "❌ Reply to a message."
        )
        return

    msg = message.reply_to_message

    text = (
        "ℹ️ **Message Information**\n\n"
        f"Message ID: `{msg.id}`\n"
        f"Chat ID: `{msg.chat.id}`"
    )

    if msg.from_user:
        text += (
            f"\nUser ID: `{msg.from_user.id}`"
            f"\nName: `{msg.from_user.first_name}`"
        )

    await message.reply_text(
        text
    )


@Client.on_message(
    filters.command("broadcast")
    & filters.user(ADMINS)
)
async def broadcast(
    client,
    message
):

    if not message.reply_to_message:
        await message.reply_text(
            "❌ Reply to the message you want to broadcast."
        )
        return

    users = []

    try:
        users = await db.get_all_users()

    except Exception as e:
        logger.exception(e)

    if not users:
        await message.reply_text(
            "❌ No users found."
        )
        return

    sent = 0
    failed = 0

    status = await message.reply_text(
        "📢 Broadcast started..."
    )

    for user in users:
        try:
            user_id = (
                user["id"]
                if isinstance(user, dict)
                else user
            )

            await message.reply_to_message.copy(
                chat_id=user_id
            )

            sent += 1

        except FloodWait as e:
            await asyncio.sleep(
                e.value
            )

        except Exception:
            failed += 1

        await asyncio.sleep(
            0.05
        )

    await status.edit_text(
        f"✅ Broadcast completed.\n\n"
        f"📤 Sent: `{sent}`\n"
        f"❌ Failed: `{failed}`"
    )


@Client.on_message(
    filters.command("restart")
    & filters.user(ADMINS)
)
async def restart(
    client,
    message
):

    await message.reply_text(
        "♻️ Restarting..."
    )

    try:
        restarti.delete_many({})

    except Exception:
        pass

    os.execl(
        sys.executable,
        sys.executable,
        *sys.argv
    )


@Client.on_message(
    filters.command("ping")
)
async def ping(
    client,
    message
):

    start = asyncio.get_event_loop().time()

    msg = await message.reply_text(
        "🏓 Pinging..."
    )

    end = asyncio.get_event_loop().time()

    ms = round(
        (end - start) * 1000,
        2
    )

    await msg.edit_text(
        f"🏓 **Pong!** `{ms} ms`"
    )


@Client.on_message(
    filters.command("help")
)
async def help_command(
    client,
    message
):

    buttons = [
        [
            InlineKeyboardButton(
                "📖 Help",
                callback_data="help"
            )
        ],
        [
            InlineKeyboardButton(
                "ℹ️ About",
                callback_data="about"
            )
        ]
    ]

    await message.reply_text(
        script.HELP_TXT,
        reply_markup=InlineKeyboardMarkup(
            buttons
        )
    )


@Client.on_message(
    filters.command("about")
)
async def about_command(
    client,
    message
):

    await message.reply_text(
        script.ABOUT_TXT,
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "🔙 Back",
                    callback_data="start"
                )
            ]
        ])
    )


@Client.on_message(
    filters.command("log")
    & filters.user(ADMINS)
)
async def log_command(
    client,
    message
):

    if not LOG_CHANNEL:
        await message.reply_text(
            "❌ LOG_CHANNEL is not configured."
        )
        return

    await message.reply_text(
        f"📝 Log channel:\n`{LOG_CHANNEL}`"
    )


@Client.on_message(
    filters.command("clear")
    & filters.user(ADMINS)
)
async def clear_command(
    client,
    message
):

    try:
        await message.delete()

    except Exception:
        pass

    for _ in range(10):
        try:
            msg = await client.get_messages(
                message.chat.id,
                message.id - _ - 1
            )

            if msg:
                await msg.delete()

        except Exception:
            pass


@Client.on_message(
    filters.command("protect")
    & filters.user(ADMINS)
)
async def protect_command(
    client,
    message
):

    if len(message.command) < 2:
        await message.reply_text(
            "Usage: `/protect on` or `/protect off`"
        )
        return

    value = (
        message.command[1].lower()
    )

    if value == "on":
        await db.set_protect_content(
            message.chat.id,
            True
        )

        await message.reply_text(
            "🔒 Protect Content enabled."
        )

    elif value == "off":
        await db.set_protect_content(
            message.chat.id,
            False
        )

        await message.reply_text(
            "🔓 Protect Content disabled."
        )

    else:
        await message.reply_text(
            "❌ Use `on` or `off`."
        )


@Client.on_message(
    filters.command("request")
)
async def request_command(
    client,
    message
):

    if len(message.command) < 2:
        await message.reply_text(
            "❌ Send your movie request after `/request`."
        )
        return

    request = message.text.split(
        None,
        1
    )[1]

    await client.send_message(
        LOG_CHANNEL,
        f"🎬 **New Movie Request**\n\n"
        f"👤 User: {message.from_user.mention}\n"
        f"🆔 ID: `{message.from_user.id}`\n"
        f"🎞 Request: `{request}`"
    )

    await message.reply_text(
        "✅ Your request has been sent."
    )


@Client.on_message(
    filters.command("users")
    & filters.user(ADMINS)
)
async def users_command(
    client,
    message
):

    try:
        count = await db.total_users()

    except Exception:
        count = 0

    await message.reply_text(
        f"👥 **Total Users:** `{count}`"
    )


@Client.on_message(
    filters.command("groups")
    & filters.user(ADMINS)
)
async def groups_command(
    client,
    message
):

    try:
        count = await db.total_groups()

    except Exception:
        count = 0

    await message.reply_text(
        f"👥 **Total Groups:** `{count}`"
    )
@Client.on_message(
    filters.command("delusers")
    & filters.user(ADMINS)
)
async def delete_users(
    client,
    message
):

    await message.reply_text(
        "⚠️ This command is disabled for safety."
    )


@Client.on_message(
    filters.command("delgroups")
    & filters.user(ADMINS)
)
async def delete_groups(
    client,
    message
):

    await message.reply_text(
        "⚠️ This command is disabled for safety."
    )


@Client.on_message(
    filters.command("setgroup")
    & filters.user(ADMINS)
)
async def setgroup(
    client,
    message
):

    if len(message.command) < 2:
        await message.reply_text(
            "❌ Usage: `/setgroup <chat_id>`"
        )
        return

    try:
        chat_id = int(
            message.command[1]
        )

        await save_group_settings(
            chat_id,
            {
                "auto_filter": True
            }
        )

        await message.reply_text(
            f"✅ Group `{chat_id}` saved."
        )

    except Exception as e:
        logger.exception(e)

        await message.reply_text(
            f"❌ Error:\n`{e}`"
        )


@Client.on_message(
    filters.command("delgroup")
    & filters.user(ADMINS)
)
async def delgroup(
    client,
    message
):

    if len(message.command) < 2:
        await message.reply_text(
            "❌ Usage: `/delgroup <chat_id>`"
        )
        return

    try:
        chat_id = int(
            message.command[1]
        )

        await db.delete_chat(
            chat_id
        )

        await message.reply_text(
            "✅ Group removed."
        )

    except Exception as e:
        logger.exception(e)

        await message.reply_text(
            f"❌ Error:\n`{e}`"
        )


@Client.on_message(
    filters.command("leave")
    & filters.user(ADMINS)
)
async def leave_chat(
    client,
    message
):

    if len(message.command) < 2:
        await message.reply_text(
            "❌ Usage: `/leave <chat_id>`"
        )
        return

    try:
        chat_id = int(
            message.command[1]
        )

        await client.leave_chat(
            chat_id
        )

        await message.reply_text(
            "✅ Left the chat."
        )

    except Exception as e:
        logger.exception(e)

        await message.reply_text(
            f"❌ Error:\n`{e}`"
        )


@Client.on_message(
    filters.command("ban")
    & filters.group
)
async def ban_user(
    client,
    message
):

    if not await admin_check(message):
        return

    if not message.reply_to_message:
        await message.reply_text(
            "❌ Reply to a user."
        )
        return

    try:
        await client.ban_chat_member(
            message.chat.id,
            message.reply_to_message.from_user.id
        )

        await message.reply_text(
            "🚫 User banned."
        )

    except ChatAdminRequired:
        await message.reply_text(
            "❌ I need admin permission."
        )

    except Exception as e:
        logger.exception(e)

        await message.reply_text(
            f"❌ Error:\n`{e}`"
        )


@Client.on_message(
    filters.command("unban")
    & filters.group
)
async def unban_user(
    client,
    message
):

    if not await admin_check(message):
        return

    if not message.reply_to_message:
        await message.reply_text(
            "❌ Reply to a user."
        )
        return

    try:
        await client.unban_chat_member(
            message.chat.id,
            message.reply_to_message.from_user.id
        )

        await message.reply_text(
            "✅ User unbanned."
        )

    except Exception as e:
        logger.exception(e)

        await message.reply_text(
            f"❌ Error:\n`{e}`"
        )


@Client.on_message(
    filters.command("mute")
    & filters.group
)
async def mute_user(
    client,
    message
):

    if not await admin_check(message):
        return

    if not message.reply_to_message:
        await message.reply_text(
            "❌ Reply to a user."
        )
        return

    try:
        await client.restrict_chat_member(
            message.chat.id,
            message.reply_to_message.from_user.id,
            permissions=enums.ChatPermissions()
        )

        await message.reply_text(
            "🔇 User muted."
        )

    except Exception as e:
        logger.exception(e)

        await message.reply_text(
            f"❌ Error:\n`{e}`"
        )


@Client.on_message(
    filters.command("unmute")
    & filters.group
)
async def unmute_user(
    client,
    message
):

    if not await admin_check(message):
        return

    if not message.reply_to_message:
        await message.reply_text(
            "❌ Reply to a user."
        )
        return

    try:
        await client.restrict_chat_member(
            message.chat.id,
            message.reply_to_message.from_user.id,
            permissions=enums.ChatPermissions(
                can_send_messages=True,
                can_send_media_messages=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True
            )
        )

        await message.reply_text(
            "🔊 User unmuted."
        )

    except Exception as e:
        logger.exception(e)

        await message.reply_text(
            f"❌ Error:\n`{e}`"
        )


@Client.on_message(
    filters.command("del")
    & filters.group
)
async def delete_message(
    client,
    message
):

    if not await admin_check(message):
        return

    if not message.reply_to_message:
        await message.reply_text(
            "❌ Reply to the message."
        )
        return

    try:
        await message.reply_to_message.delete()
        await message.delete()

    except MessageDeleteForbidden:
        await message.reply_text(
            "❌ I don't have permission to delete messages."
        )

    except Exception as e:
        logger.exception(e)


@Client.on_message(
    filters.command("pin")
    & filters.group
)
async def pin_message(
    client,
    message
):

    if not await admin_check(message):
        return

    if not message.reply_to_message:
        await message.reply_text(
            "❌ Reply to the message."
        )
        return

    try:
        await message.reply_to_message.pin(
            disable_notification=True
        )

        await message.reply_text(
            "📌 Message pinned."
        )

    except Exception as e:
        logger.exception(e)

        await message.reply_text(
            f"❌ Error:\n`{e}`"
        )


@Client.on_message(
    filters.command("unpin")
    & filters.group
)
async def unpin_message(
    client,
    message
):

    if not await admin_check(message):
        return

    try:
        await client.unpin_all_chat_messages(
            message.chat.id
        )

        await message.reply_text(
            "📌 All messages unpinned."
        )

    except Exception as e:
        logger.exception(e)

        await message.reply_text(
            f"❌ Error:\n`{e}`"
        )


@Client.on_message(
    filters.new_chat_members
)
async def new_member(
    client,
    message
):

    for member in message.new_chat_members:

        if member.is_bot:
            continue

        try:
            await db.add_user(
                member.id,
                member.first_name
            )

        except Exception:
            pass


@Client.on_message(
    filters.left_chat_member
)
async def left_member(
    client,
    message
):

    member = message.left_chat_member

    if not member:
        return

    if member.is_bot:
        return

    try:
        await db.delete_user(
            member.id
        )

    except Exception:
        pass


@Client.on_message(
    filters.group
    & filters.incoming
    & ~filters.command(
        [
            "start",
            "help",
            "about",
            "filter",
            "filters",
            "deletefilter",
            "alldeletefilters"
        ]
    )
)
async def group_auto_filter(
    client,
    message
):

    if not message.text:
        return

    if message.text.startswith("/"):
        return

    try:
        settings = await get_settings(
            message.chat.id
        )

    except Exception:
        settings = {}

    if settings.get(
        "auto_filter",
        True
    ) is False:
        return

    try:
        await auto_filter(
            client,
            message
        )

    except Exception as e:
        logger.exception(e)


@Client.on_callback_query()
async def callback_handler(
    client,
    query
):

    data = query.data

    if data == "help":
        await query.message.edit_text(
            script.HELP_TXT,
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "🔙 Back",
                        callback_data="start"
                    )
                ]
            ])
        )

        await query.answer()
        return

    if data == "about":
        await query.message.edit_text(
            script.ABOUT_TXT,
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "🔙 Back",
                        callback_data="start"
                    )
                ]
            ])
        )

        await query.answer()
        return

    if data == "start":
        await query.message.edit_text(
            script.START_TXT.format(
                query.from_user.mention,
                temp.U_NAME,
                temp.B_NAME
            ),
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(
                        "ℹ️ Help",
                        callback_data="help"
                    ),
                    InlineKeyboardButton(
                        "📍 About",
                        callback_data="about"
                    )
                ]
            ])
        )

        await query.answer()
        return

    if data.startswith("checksub"):
        try:
            pre, file_id = data.split(
                "#",
                1
            )

        except ValueError:
            await query.answer(
                "Invalid request.",
                show_alert=True
            )
            return

        try:
            check = await is_subscribed(
                client,
                query.message
            )

        except Exception:
            check = False

        if check:
            try:
                await send_file(
                    client,
                    query.message,
                    pre,
                    file_id
                )

                await query.message.delete()

            except Exception as e:
                logger.exception(e)

            await query.answer()

        else:
            await query.answer(
                "❌ Please join the required channel first.",
                show_alert=True
            )

        return

    if data.startswith("extract_data:"):
        file_id = data.split(
            ":",
            1
        )[1]

        files_ = await get_file_details(
            file_id
        )

        if not files_:
            await query.answer(
                "File not found.",
                show_alert=True
            )
            return

        file = files_[0]

        title = file.file_name or "Unknown"
        size = get_size(
            file.file_size
        )

        caption = (
            f"📁 <b>File Information</b>\n\n"
            f"📌 Name: <code>{title}</code>\n"
            f"📦 Size: <code>{size}</code>"
        )

        await query.message.reply_text(
            caption,
            parse_mode=enums.ParseMode.HTML
        )

        await query.answer()
        return

    await query.answer()
