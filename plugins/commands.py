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
from utils import (
    get_settings, get_size, is_subscribed, is_requested_one, is_requested_two, 
    save_group_settings, temp, check_loop_sub, check_loop_sub1, check_loop_sub2
)


logger = logging.getLogger(__name__)

from dotenv import load_dotenv

load_dotenv("./dynamic.env", override=True, encoding="utf-8")

BATCH_FILES = {}
DS_REACT = ["⚡"]

should_run_check_loop_sub = False
should_run_check_loop_sub1 = False

inclient = pymongo.MongoClient(DATABASE_URI)
indb = inclient[DATABASE_NAME]
incol = indb['auto_del']
infile = indb['file_reply_text']
restarti = indb['restart']

async def admin_check(message: Message) -> bool:
    if not message.from_user: return False
    if message.chat.type not in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]: return False
    if message.from_user.id in [777000, 1087968824]: return True
    client = message._client
    chat_id = message.chat.id
    user_id = message.from_user.id
    check_status = await client.get_chat_member(chat_id=chat_id, user_id=user_id)
    admin_strings = [enums.ChatMemberStatus.OWNER, enums.ChatMemberStatus.ADMINISTRATOR]
    if check_status.status not in admin_strings: return False
    else: return True      
    
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
    except:
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
            f_caption=CUSTOM_FILE_CAPTION.format(file_name= '' if title is None else title, file_size='' if size is None else size, file_caption='' if f_caption is None else f_caption, mention=query.from_user.mention)
        except Exception as e:
            logger.exception(e)
            f_caption = f_caption
    if f_caption is None:
        f_cation = f"{title}"
    inline_keyboard = [[
            InlineKeyboardButton('🎥 𝐌𝐚𝐢𝐧 𝐂𝐡𝐚𝐧𝐧𝐞𝐥 🎥', url=f'https://t.me/Clmainchannel')
            ],[     
            InlineKeyboardButton('👥 𝐉𝐨𝐢𝐧 𝐎𝐮𝐫 𝐆𝐫𝐨𝐮𝐩 👥', url='https://t.me/+Ik14BdOewjQzYjI1')
    ]]
    reply_markup = InlineKeyboardMarkup(inline_keyboard)
    ok = await client.send_cached_media(
        chat_id=query.from_user.id,
        file_id=file_id,
        caption=f_caption,
        protect_content=True if ident == 'checksubp' else False,
        reply_markup=reply_markup
    )
    asyncio.create_task(delete_after_2_minutes(ok))
   
@Client.on_message(filters.command("start") & filters.incoming)
async def start(client, message):   
    if message.chat.type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        buttons = [
                InlineKeyboardButton('👥 𝐉𝐨𝐢𝐧 𝐎𝐮𝐫 𝐆𝐫𝐨𝐮𝐩 👥', url=f'https://t.me/+Ik14BdOewjQzYjI1')
               ],[
                InlineKeyboardButton('🎥 𝐌𝐚𝐢𝐧 𝐂𝐡𝐚𝐧𝐧𝐞𝐥 🎥', url=f'https://t.me/Clmainchannel')
              ],[
                InlineKeyboardButton('👥 𝐒𝐮𝐩𝐩𝐨𝐫𝐭 𝐆𝐫𝐨𝐮𝐩 👥', url="https://t.me/+hl_Pkp8qUOsxMmY1"),
        ]       
        reply_markup = InlineKeyboardMarkup(buttons)
        await message.reply(script.START_TXT.format(message.from_user.mention if message.from_user else message.chat.title, temp.U_NAME, temp.B_NAME), reply_markup=reply_markup)
        await asyncio.sleep(2) # 😢 https://github.com/EvamariaTG/EvaMaria/blob/master/plugins/p_ttishow.py#L17 😬 wait a bit, before checking.
        if not await db.get_chat(message.chat.id):
            total=await client.get_chat_members_count(message.chat.id)
            await client.send_message(LOG_CHANNEL, script.LOG_TEXT_G.format(message.chat.title, message.chat.id, total, "Unknown"))       
            await db.add_chat(message.chat.id, message.chat.title)
        return 
    if not await db.is_user_exist(message.from_user.id):
        await db.add_user(message.from_user.id, message.from_user.first_name)
        await client.send_message(LOG_CHANNEL, script.LOG_TEXT_P.format(message.from_user.id, message.from_user.mention))
    # For Achu Vj
    if len(message.command) != 2 or message.command[1] in ["subscribe", "error", "okay", "help"]:
        buttons = [[
            InlineKeyboardButton('➕ ᴀᴅᴅ ᴍᴇ ᴛᴏ ʏᴏᴜʀ ɢʀᴏᴜᴘꜱ ➕', url=f'http://t.me/{temp.U_NAME}?startgroup=true')
            ],[
            InlineKeyboardButton('🔍 ꜱᴇᴀʀᴄʜ 🔎', switch_inline_query_current_chat=''),
            InlineKeyboardButton('📣 ᴜᴘᴅᴀᴛᴇꜱ 📣', url='https://t.me/Clmainchannel')
            ],[
            InlineKeyboardButton('ℹ️ ʜᴇʟᴘ ℹ️', callback_data='help'),
            InlineKeyboardButton('📍 ᴀʙᴏᴜᴛ 📍', callback_data='about')
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
        return
    if REQ_CHANNEL1 and not await is_requested_one(client, message):
        btn = [[
            InlineKeyboardButton(
                "➳ 𝐽𝑂𝐼𝑁 𝑈𝑃𝐷𝐴𝑇𝐸 𝐶𝐻𝑁𝑁𝑁𝐸𝐿 ✺", url=client.req_link1)
        ]]
        should_run_check_loop_sub1 = True
        should_run_check_loop_sub = False
        try:
            if REQ_CHANNEL2 and not await is_requested_two(client, message):
                btn.append(
                      [
                    InlineKeyboardButton(
                        "➳ 𝐽𝑂𝐼𝑁 𝑈𝑃𝐷𝐴𝑇𝐸 𝐶𝐻𝑁𝑁𝑁𝐸𝐿 ✺", url=client.req_link2)
                      ]
                )
                should_run_check_loop_sub = True                      
        except Exception as e:
            print(e)
        if message.command[1] != "subscribe":
            try:
                kk, file_id = message.command[1].split("_", 1)
                pre = 'checksubp' if kk == 'filep' else 'checksub' 
                btn.append([InlineKeyboardButton("🔄 𝐓𝐫𝐲 𝐀𝐠𝐚𝐢𝐧 🔄", callback_data=f"{pre}#{file_id}")])
            except (IndexError, ValueError):
                btn.append([InlineKeyboardButton("🔄 𝐓𝐫𝐲 𝐀𝐠𝐚𝐢𝐧 🔄", url=f"https://t.me/{temp.U_NAME}?start={message.command[1]}")])
        sh = await client.send_message(
            chat_id=message.from_user.id,
            text="**♦️ 𝗥𝗘𝗔𝗗 𝗧𝗛𝗜𝗦 𝗜𝗡𝗦𝗧𝗥𝗨𝗖𝗧𝗜𝗢𝗡 ♦️\n\nനിങ്ങൾ ചോദിക്കുന്ന സിനിമകൾ ലഭിക്കണം എന്നുണ്ടെങ്കിൽ നിങ്ങൾ ഞങ്ങളുടെ ചാനലിൽ ജോയിൻ ചെയ്തിരിക്കണം. ജോയിൻ ചെയ്യാൻ ✺ 𝐽𝑂𝐼𝑁 𝑈𝑃𝐷𝐴𝑇𝐸 𝐶𝐻𝑁𝑁𝑁𝐸𝐿 ✺ എന്ന ബട്ടണിൽ ക്ലിക്ക് ചെയ്യാവുന്നതാണ്.\n\nജോയിൻ ചെയ്ത ശേഷം 🔄 𝐓𝐫𝐲 𝐀𝐠𝐚𝐢𝐧 🔄 എന്ന ബട്ടണിൽ അമർത്തിയാൽ നിങ്ങൾക്ക് ഞാൻ ആ സിനിമ അയച്ചു തരുന്നതാണ്..\n\nCLICK ✺ 𝐽𝑂𝐼𝑁 𝑈𝑃𝐷𝐴𝑇𝐸 𝐶𝐻𝑁𝑁𝑁𝐸𝐿 ✺ AND THEN CLICK 🔄 𝐓𝐫𝐲 𝐀𝐠𝐚𝐢𝐧 🔄 BUTTON TO GET MOVIE FILE 🗃️**",
            reply_markup=InlineKeyboardMarkup(btn),
            parse_mode=enums.ParseMode.MARKDOWN
            )
        if should_run_check_loop_sub:
            check = await check_loop_sub(client, message)
        elif should_run_check_loop_sub1:
            check = await check_loop_sub1(client, message)
        if check:     
            await send_file(client, message, pre, file_id)
            await sh.delete()        
            return
        else:
            return False

    if REQ_CHANNEL2 and not await is_requested_two(client, message):
        btn = [[
            InlineKeyboardButton(
                "Update Channel 2", url=client.req_link2)
        ]]
        if message.command[1] != "subscribe":
            try:
                kk, file_id = message.command[1].split("_", 1)
                pre = 'checksubp' if kk == 'filep' else 'checksub' 
                btn.append([InlineKeyboardButton("Try Again", callback_data=f"{pre}#{file_id}")])
            except (IndexError, ValueError):
                btn.append([InlineKeyboardButton("Try Again", url=f"https://t.me/{temp.U_NAME}?start={message.command[1]}")])
        sh = await client.send_message(
            chat_id=message.from_user.id,
            text="**♦️ 𝗥𝗘𝗔𝗗 𝗧𝗛𝗜𝗦 𝗜𝗡𝗦𝗧𝗥𝗨𝗖𝗧𝗜𝗢𝗡 ♦️\n\nനിങ്ങൾ ചോദിക്കുന്ന സിനിമകൾ ലഭിക്കണം എന്നുണ്ടെങ്കിൽ നിങ്ങൾ ഞങ്ങളുടെ ചാനലിൽ ജോയിൻ ചെയ്തിരിക്കണം. ജോയിൻ ചെയ്യാൻ ✺ 𝐽𝑂𝐼𝑁 𝑈𝑃𝐷𝐴𝑇𝐸 𝐶𝐻𝑁𝑁𝑁𝐸𝐿 ✺ എന്ന ബട്ടണിൽ ക്ലിക്ക് ചെയ്യാവുന്നതാണ്.\n\nജോയിൻ ചെയ്ത ശേഷം 🔄 𝐓𝐫𝐲 𝐀𝐠𝐚𝐢𝐧 🔄 എന്ന ബട്ടണിൽ അമർത്തിയാൽ നിങ്ങൾക്ക് ഞാൻ ആ സിനിമ അയച്ചു തരുന്നതാണ്..\n\nജോയിൻ ചെയ്ത ശേഷം 🔄 𝐓𝐫𝐲 𝐀𝐠𝐚𝐢𝐧 🔄 എന്ന ബട്ടണിൽ അമർത്തിയാൽ നിങ്ങൾക്ക് ഞാൻ ആ സിനിമ അയച്ചു തരുന്നതാണ്..\n\nCLICK ✺ 𝐽𝑂𝐼𝑁 𝑈𝑃𝐷𝐴𝑇𝐸 𝐶𝐻𝑁𝑁𝑁𝐸𝐿 ✺ AND THEN CLICK 🔄 Try Again 🔄 BUTTON TO GET MOVIE FILE 🗃️**",
            reply_markup=InlineKeyboardMarkup(btn),
            parse_mode=enums.ParseMode.MARKDOWN
        )
        check = await check_loop_sub2(client, message)
        if check:
            await send_file(client, message, pre, file_id)
            await sh.delete()     
            return 
        else:
            return False
    if len(message.command) == 2 and message.command[1].startswith('getfile'):
        searches = message.command[1].split("-", 1)[1] 
        search = searches.replace('-',' ')
        message.text = search 
        await auto_filter(client, message) 
        return
         
    if len(message.command) == 2 and message.command[1] in ["subscribe", "error", "okay", "help"]:
        buttons = [
               InlineKeyboardButton('👥 𝐉𝐨𝐢𝐧 𝐎𝐮𝐫 𝐆𝐫𝐨𝐮𝐩 👥', url=f'https://t.me/+Ik14BdOewjQzYjI1')
               ],[
                InlineKeyboardButton('🎥 𝐌𝐚𝐢𝐧 𝐂𝐡𝐚𝐧𝐧𝐞𝐥 🎥', url=f'https://t.me/Clmainchannel')
              ],[
                InlineKeyboardButton('👥 𝐒𝐮𝐩𝐩𝐨𝐫𝐭 𝐆𝐫𝐨𝐮𝐩 👥', url="https://t.me/+hl_Pkp8qUOsxMmY1"),
        ]       
        reply_markup = InlineKeyboardMarkup(buttons)
        await message.reply_video(
            video="https://envs.sh/_O0.mp4",
            caption=script.START_TXT.format(message.from_user.mention, temp.U_NAME, temp.B_NAME),
            reply_markup=reply_markup,
            parse_mode=enums.ParseMode.HTML
        )
        return
    data = message.command[1]
    try:
        pre, file_id = data.split('_', 1)
    except:
        file_id = data
        pre = ""
    if data.split("-", 1)[0] == "BATCH":
        sts = await message.reply("Please wait")
        file_id = data.split("-", 1)[1]
        msgs = BATCH_FILES.get(file_id)
        if not msgs:
            file = await client.download_media(file_id)
            try: 
                with open(file) as file_data:
                    msgs=json.loads(file_data.read())
            except:
                await sts.edit("FAILED")
                return await client.send_message(LOG_CHANNEL, "UNABLE TO OPEN FILE.")
            os.remove(file)
            BATCH_FILES[file_id] = msgs
        for msg in msgs:
            title = msg.get("title")
            size=get_size(int(msg.get("size", 0)))
            f_caption=msg.get("caption", "")
            if BATCH_FILE_CAPTION:
                try:
                    f_caption=BATCH_FILE_CAPTION.format(file_name= '' if title is None else title, file_size='' if size is None else size, file_caption='' if f_caption is None else f_caption)
                except Exception as e:
                    logger.exception(e)
                    f_caption=f_caption
            if f_caption is None:
                f_caption = f"{title}"
            try:
                await client.send_cached_media(
                    chat_id=message.from_user.id,
                    file_id=msg.get("file_id"),
                    caption=f_caption,
                    protect_content=msg.get('protect', False),
                    )
            except FloodWait as e:
                await asyncio.sleep(e.x)
                logger.warning(f"Floodwait of {e.x} sec.")
                await client.send_cached_media(
                    chat_id=message.from_user.id,
                    file_id=msg.get("file_id"),
                    caption=f_caption,
                    protect_content=msg.get('protect', False),
                    )
            except Exception as e:
                logger.warning(e, exc_info=True)
                continue
            await asyncio.sleep(1) 
        await sts.delete()
        return
    elif data.split("-", 1)[0] == "DSTORE":
        sts = await message.reply("Please wait")
        b_string = data.split("-", 1)[1]
        decoded = (base64.urlsafe_b64decode(b_string + "=" * (-len(b_string) % 4))).decode("ascii")
        try:
            f_msg_id, l_msg_id, f_chat_id, protect = decoded.split("_", 3)
        except:
            f_msg_id, l_msg_id, f_chat_id = decoded.split("_", 2)
            protect = "/pbatch" if PROTECT_CONTENT else "batch"
        diff = int(l_msg_id) - int(f_msg_id)
        async for msg in client.iter_messages(int(f_chat_id), int(l_msg_id), int(f_msg_id)):
            if msg.media:
                media = getattr(msg, msg.media)
                if BATCH_FILE_CAPTION:
                    try:
                        f_caption=BATCH_FILE_CAPTION.format(file_name=getattr(media, 'file_name', ''), file_size=getattr(media, 'file_size', ''), file_caption=getattr(msg, 'caption', ''))
                    except Exception as e:
                        logger.exception(e)
                        f_caption = getattr(msg, 'caption', '')
                else:
                    media = getattr(msg, msg.media)
                    file_name = getattr(media, 'file_name', '')
                    f_caption = getattr(msg, 'caption', file_name)
                try:
                    await msg.copy(message.chat.id, caption=f_caption, protect_content=True if protect == "/pbatch" else False)
                except FloodWait as e:
                    await asyncio.sleep(e.x)
                    await msg.copy(message.chat.id, caption=f_caption, protect_content=True if protect == "/pbatch" else False)
                except Exception as e:
                    logger.exception(e)
                    continue
            elif msg.empty:
                continue
            else:
                try:
                    await msg.copy(message.chat.id, protect_content=True if protect == "/pbatch" else False)
                except FloodWait as e:
                    await asyncio.sleep(e.x)
                    await msg.copy(message.chat.id, protect_content=True if protect == "/pbatch" else False)
                except Exception as e:
                    logger.exception(e)
                    continue
            await asyncio.sleep(1) 
        return await sts.delete()
        

    files_ = await get_file_details(file_id)           
    if not files_:
        pre, file_id = ((base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))).decode("ascii")).split("_", 1)
        try:
            msg = await client.send_cached_media(
                chat_id=message.from_user.id,
                file_id=file_id,
                protect_content=True if pre == 'filep' else False,
                )
            filetype = msg.media
            file = getattr(msg, filetype)
            title = file.file_name
            size=get_size(file.file_size)
            f_caption = f"<code>{title}</code>"
            if CUSTOM_FILE_CAPTION:
                try:
                    f_caption=CUSTOM_FILE_CAPTION.format(file_name= '' if title is None else title, file_size='' if size is None else size, file_caption='' if f_caption is None else f_caption, mention=message.from_user.mention)    
                except:
                    return
            await msg.edit_caption(f_caption)
            return
        except:
            pass
        return await message.reply('No such file exist.')
    files = files_[0]
    title = files.file_name
    size=get_size(files.file_size)
    f_caption=files.caption
    if CUSTOM_FILE_CAPTION:
        try:
            f_caption=CUSTOM_FILE_CAPTION.format(file_name= '' if title is None else title, file_size='' if size is None else size, file_caption='' if f_caption is None else f_caption, mention=message.from_user.mention)
        except Exception as e:
            logger.exception(e)
            f_caption = f_caption

    if f_caption is None:
        f_caption = f"{title}"
        f_caption += "\n\n⚠️ This file will be deleted automatically in 2 minutes.\n📌 Please save/forward it before deletion."

    xd = await client.send_cached_media(
        chat_id=message.from_user.id,
        file_id=file_id,
        caption=f_caption,
        protect_content=True if pre == 'filep' else False,
        reply_markup=InlineKeyboardMarkup([
    [
        InlineKeyboardButton(
            '🎥 𝐌𝐚𝐢𝐧 𝐂𝐡𝐚𝐧𝐧𝐞𝐥 🎥',
            url='https://t.me/Clmainchannel'
        )
    ],
    [
        InlineKeyboardButton(
            '👥 𝐉𝐨𝐢𝐧 𝐎𝐮𝐫 𝐆𝐫𝐨𝐮𝐩 👥',
            url='https://t.me/+Ik14BdOewjQzYjI1'
        )
    ],
    [
        InlineKeyboardButton(
            'ℹ️ ᴠɪᴇᴡ ᴀᴜᴅɪᴏ & ꜱᴜʙꜱ ɪɴꜰᴏ ℹ️',
            callback_data=f'extract_data:{file_id}'
        )
    ]
]))
    asyncio.create_task(delete_after_2_minutes(xd))
       
@Client.on_message(filters.command('channel') & filters.user(ADMINS))
async def channel_info(bot, message):
           
    """Send basic information of channel"""
    if isinstance(CHANNELS, (int, str)):
        channels = [CHANNELS]
    elif isinstance(CHANNELS, list):
        channels = CHANNELS
    else:
        raise ValueError("Unexpected type of CHANNELS")

    text = '📑 **Indexed channels/groups**\n'
    for channel in channels:
        chat = await bot.get_chat(channel)
        if chat.username:
            text += '\n@' + chat.username
        else:
            text += '\n' + chat.title or chat.first_name

    text += f'\n\n**Total:** {len(CHANNELS)}'

    if len(text) < 4096:
        await message.reply(text)
    else:
        file = 'Indexed channels.txt'
        with open(file, 'w') as f:
            f.write(text)
        await message.reply_document(file)
        os.remove(file)


@Client.on_message(filters.command('logs') & filters.user(ADMINS))
async def log_file(bot, message):
    """Send log file"""
    try:
        await message.reply_document('TelegramBot.log')
    except Exception as e:
        await message.reply(str(e))

@Client.on_message(filters.command('delete') & filters.user(ADMINS))
async def delete(bot, message):
    """Delete file from database"""
    reply = message.reply_to_message
    if reply and reply.media:
        msg = await message.reply("Processing...⏳", quote=True)
    else:
        await message.reply('Reply to the file with /delete that you want to delete', quote=True)
        return

    for file_type in ("document", "video", "audio"):
        media = getattr(reply, file_type, None)
        if media is not None:
            break
    else:
        await msg.edit('This is not a supported file format')
        return
    
    file_id, file_ref = unpack_new_file_id(media.file_id)

    # Check if the file exists in Media collection
    result_media = await Media.collection.find_one({'_id': file_id})

    # Check if the file exists in Mediaa collection
    result_mediaa = await Mediaa.collection.find_one({'_id': file_id})   

    if result_media and result_mediaa:
        await Media.collection.delete_one({'_id': file_id})
        await Mediaa.collection.delete_one({'_id': file_id})
        
    if result_media:
        # Delete from Media collection
        await Media.collection.delete_one({'_id': file_id})
    elif result_mediaa:
        # Delete from Mediaa collection
        await Mediaa.collection.delete_one({'_id': file_id})
    else:
        # File not found in both collections
        await msg.edit('File not found in the database')
        return

    await msg.edit('File is successfully deleted from the database')


@Client.on_message(filters.command('deleteall') & filters.user(ADMINS))
async def delete_all_index(bot, message):
    await message.reply_text(
        'This will delete all indexed files.\nDo you want to continue??',
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        text="YES", callback_data="autofilter_delete"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="CANCEL", callback_data="close_data"
                    )
                ],
            ]
        ),
        quote=True,
    )


@Client.on_callback_query(filters.regex(r'^autofilter_delete'))
async def delete_all_index_confirm(bot, message):
    await Media.collection.drop()
    await Mediaa.collection.drop()
    await message.answer('Piracy Is Crime')
    await message.message.edit('Succesfully Deleted All The Indexed Files.')


@Client.on_message(filters.command('settings'))
async def settings(client, message):
    userid = message.from_user.id if message.from_user else None
    if not userid:
        return await message.reply(f"You are anonymous admin. Use /connect {message.chat.id} in PM")
    chat_type = message.chat.type

    if chat_type == enums.ChatType.PRIVATE:
        grpid = await active_connection(str(userid))
        if grpid is not None:
            grp_id = grpid
            try:
                chat = await client.get_chat(grpid)
                title = chat.title
            except:
                await message.reply_text("Make sure I'm present in your group!!", quote=True)
                return
        else:
            await message.reply_text("I'm not connected to any groups!", quote=True)
            return

    elif chat_type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        grp_id = message.chat.id
        title = message.chat.title

    else:
        return

    st = await client.get_chat_member(grp_id, userid)
    if (
            st.status != enums.ChatMemberStatus.ADMINISTRATOR
            and st.status != enums.ChatMemberStatus.OWNER
            and str(userid) not in ADMINS
    ):
        return

    settings = await get_settings(grp_id)

    if settings is not None:
        buttons = [
            [
                InlineKeyboardButton(
                    'Filter Button',
                    callback_data=f'setgs#button#{settings["button"]}#{grp_id}',
                ),
                InlineKeyboardButton(
                    'Single' if settings["button"] else 'Double',
                    callback_data=f'setgs#button#{settings["button"]}#{grp_id}',
                ),
            ],
            [
                InlineKeyboardButton(
                    'Bot PM',
                    callback_data=f'setgs#botpm#{settings["botpm"]}#{grp_id}',
                ),
                InlineKeyboardButton(
                    '✅ Yes' if settings["botpm"] else '❌ No',
                    callback_data=f'setgs#botpm#{settings["botpm"]}#{grp_id}',
                ),
            ],
            [
                InlineKeyboardButton(
                    'File Secure',
                    callback_data=f'setgs#file_secure#{settings["file_secure"]}#{grp_id}',
                ),
                InlineKeyboardButton(
                    '✅ Yes' if settings["file_secure"] else '❌ No',
                    callback_data=f'setgs#file_secure#{settings["file_secure"]}#{grp_id}',
                ),
            ],
            [
                InlineKeyboardButton(
                    'IMDB',
                    callback_data=f'setgs#imdb#{settings["imdb"]}#{grp_id}',
                ),
                InlineKeyboardButton(
                    '✅ Yes' if settings["imdb"] else '❌ No',
                    callback_data=f'setgs#imdb#{settings["imdb"]}#{grp_id}',
                ),
            ],
            [
                InlineKeyboardButton(
                    'Spell Check',
                    callback_data=f'setgs#spell_check#{settings["spell_check"]}#{grp_id}',
                ),
                InlineKeyboardButton(
                    '✅ Yes' if settings["spell_check"] else '❌ No',
                    callback_data=f'setgs#spell_check#{settings["spell_check"]}#{grp_id}',
                ),
            ],
            [
                InlineKeyboardButton(
                    'Welcome',
                    callback_data=f'setgs#welcome#{settings["welcome"]}#{grp_id}',
                ),
                InlineKeyboardButton(
                    '✅ Yes' if settings["welcome"] else '❌ No',
                    callback_data=f'setgs#welcome#{settings["welcome"]}#{grp_id}',
                ),
            ],
        ]

        reply_markup = InlineKeyboardMarkup(buttons)

        await message.reply_text(
            text=f"<b>Change Your Settings for {title} As Your Wish ⚙</b>",
            reply_markup=reply_markup,
            disable_web_page_preview=True,
            parse_mode=enums.ParseMode.HTML,
            reply_to_message_id=message.id
        )



@Client.on_message(filters.command('set_template'))
async def save_template(client, message):
    sts = await message.reply("Checking template")
    userid = message.from_user.id if message.from_user else None
    if not userid:
        return await message.reply(f"You are anonymous admin. Use /connect {message.chat.id} in PM")
    chat_type = message.chat.type

    if chat_type == enums.ChatType.PRIVATE:
        grpid = await active_connection(str(userid))
        if grpid is not None:
            grp_id = grpid
            try:
                chat = await client.get_chat(grpid)
                title = chat.title
            except:
                await message.reply_text("Make sure I'm present in your group!!", quote=True)
                return
        else:
            await message.reply_text("I'm not connected to any groups!", quote=True)
            return

    elif chat_type in [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]:
        grp_id = message.chat.id
        title = message.chat.title

    else:
        return

    st = await client.get_chat_member(grp_id, userid)
    if (
            st.status != enums.ChatMemberStatus.ADMINISTRATOR
            and st.status != enums.ChatMemberStatus.OWNER
            and str(userid) not in ADMINS
    ):
        return

    if len(message.command) < 2:
        return await sts.edit("No Input!!")
    template = message.text.split(" ", 1)[1]
    await save_group_settings(grp_id, 'template', template)
    await sts.edit(f"Successfully changed template for {title} to\n\n{template}")

@Client.on_message(filters.command('restart') & filters.user(ADMINS))
async def restart(b, m):
    if os.path.exists(".git"):
        os.system("git pull")

    oo = await m.reply_text("Restarting...")
    await oo.delete()
    try:
        os.remove("TelegramBot.txt")
    except:
        pass
    os.execl(sys.executable, sys.executable, "bot.py")

@Client.on_message(filters.command("pur") & filters.group)
async def purge(c: Client, m: Message):

    if m.chat.type != ChatType.SUPERGROUP:
        await m.reply_text(text="Cannot purge messages in a basic group")
        return

    is_admin = await admin_check(m)
    if not is_admin: return
  
    if m.reply_to_message:
        message_ids = list(range(m.reply_to_message.id, m.id))

        def divide_chunks(l: list, n: int = 100):
            for i in range(0, len(l), n):
                yield l[i : i + n]

        # Dielete messages in chunks of 100 messages
        m_list = list(divide_chunks(message_ids))

        try:
            for plist in m_list:
                await c.delete_messages(
                    chat_id=m.chat.id,
                    message_ids=plist,
                    revoke=True,
                )
            await m.delete()
        except MessageDeleteForbidden:
            await m.reply_text(
                text="Cannot delete all messages. The messages may be too old, I might not have delete rights, or this might not be a supergroup."
            )
            return        
        count_del_msg = len(message_ids)

        z = await m.reply_text(text=f"Deleted <i>{count_del_msg}</i> messages")
        await sleep(3)
        await z.delete()
        return
    await m.reply_text("Reply to a message to start purge !")
    return

@Client.on_message(filters.command('file_text') & filters.user(ADMINS))
async def set_file_text_command(client, message):
    await message.react("😍")
    text_data = infile.find_one({"_id": "file_text"})    
    if len(message.command) == 1:        
        if not text_data:
            await message.reply("You don't have any text")
            return
        text = text_data.get("text")
        if text == "off":
            await message.reply("You don't have any text")
            return
        else:
            await message.reply(f"current text is\n\n {text}")
            return 
    else:
        text = message.text.split(" ", 1)[1]
        if text == "off":
            if not text_data:                    
                await message.reply(f"Text have Deleted.")
            else:
                infile.update_one(
                    {"_id": "file_text"},
                    {"$set": {"text": "off"}},
                    upsert=True
                )
                await message.reply("Text have Deleted.")
        else:
            infile.update_one(
                    {"_id": "file_text"},
                    {"$set": {"text": text}},
                    upsert=True
            )
            await message.reply("Saved buddy 😁.")
            
@Client.on_message(filters.command('autodel') & filters.user(ADMINS))
async def set_deltime_command(client, message):
    del_data = incol.find_one({"_id": "delete_time"})
    if len(message.command) == 1:        
        if not del_data:
            await message.reply("𝗨𝘀𝗲 𝘁𝗶𝗺𝗲 𝗶𝗻 𝘁𝗵𝗲 𝗳𝗼𝗿𝗺𝗮𝘁 𝘀, 𝗺, 𝗼𝗿 𝗵:\n\n* <code>1s</code> 𝗳𝗼𝗿 𝟭 𝘀𝗲𝗰𝗼𝗻𝗱\n* <code>1m</code> 𝗳𝗼𝗿 𝟭 𝗺𝗶𝗻𝘂𝘁𝗲\n* <code>1h</code> 𝗳𝗼𝗿 𝟭 𝗵𝗼𝘂𝗿")
        else:      
            time_seconds = del_data.get("time_seconds")
            await message.reply(f"current mode is {time_seconds}")
    if len(message.command) == 2:
        time_str = message.command[1]
        args = message.text.split(" ", 1)
        numb = message.text.split(" ", 1)[1]        
        if "off" in numb:
            if not del_data:                
                await message.reply_text("Turned off!")
            else:
                incol.delete_one({"_id": "delete_time"})                                           
                await message.reply_text("Turned off!")
        elif "0" in args:
            if not del_data:               
                await message.reply_text("Turned off!")
            else:
                incol.delete_one({"_id": "delete_time"})
                await message.reply_text("Turned off!")
                    
        else:     
            time_seconds = convert_time_to_seconds(time_str)        
            if time_seconds > 0:
                # Save time in the group's data
                if not del_data:
                    incol.update_one(
                        {"_id": "delete_time"},
                        {"$set": {"time_seconds": time_seconds}},
                        upsert=True
                    )
                    await message.reply(f"Time set to {time_seconds} seconds.")
                else:
                    incol.update_one(
                        {"_id": "delete_time"},
                        {"$set": {"time_seconds": time_seconds}},
                        upsert=True
                    )
                    await message.reply(f"Time set to {time_seconds} seconds.")
        
            else:
                await message.reply("𝗨𝘀𝗲 𝘁𝗶𝗺𝗲 𝗶𝗻 𝘁𝗵𝗲 𝗳𝗼𝗿𝗺𝗮𝘁 𝘀, 𝗺, 𝗼𝗿 𝗵:\n\n* <code>1s</code> 𝗳𝗼𝗿 𝟭 𝘀𝗲𝗰𝗼𝗻𝗱\n* <code>1m</code> 𝗳𝗼𝗿 𝟭 𝗺𝗶𝗻𝘂𝘁𝗲\n* <code>1h</code> 𝗳𝗼𝗿 𝟭 𝗵𝗼𝘂𝗿")


@Client.on_message(filters.command("setchat1") & filters.user(ADMINS))
async def add_fsub_chats(bot: Client, update: Message):
    await update.react("🌭")
    chat = update.command[1] if len(update.command) > 1 else None
    if not chat:
        await update.reply_text("Invalid chat id.", quote=True)
        return
    else:
        chat = int(chat)
    await db.add_fsub_chat(chat)

    text = f"Added chat <code>{chat}</code> to the database."
    await update.reply_text(text=text, quote=True, parse_mode=enums.ParseMode.HTML)
    with open("./dynamic.env", "wt+") as f:
        f.write(f"REQ_CHANNEL1={chat}\n")
    restarti.update_one(
        {"_id": "frestart"},
        {"$set": {"restart": "on"}},
        upsert=True
    )
    os.execl(sys.executable, sys.executable, "bot.py")


@Client.on_message(filters.command("delchat1") & filters.user(ADMINS))
async def clear_fsub_chats(bot: Client, update: Message):
    await update.react("👍")
    await db.delete_fsub_chat(chat_id=(await db.get_fsub_chat())['chat_id'])
    await update.reply_text(text="Deleted fsub chat from the database.", quote=True)
    with open("./dynamic.env", "wt+") as f:
        f.write(f"REQ_CHANNEL1=False\n")

    logger.info("Restarting to update REQ_CHANNEL from database...")
    os.execl(sys.executable, sys.executable, "bot.py")
    
@Client.on_message(filters.command("viewchat1") & filters.user(ADMINS))
async def get_fsub_chat(bot: Client, update: Message):
    await update.react("👍")
    chat = await db.get_fsub_chat()
    if not chat:
        await update.reply_text("No fsub chat found in the database.", quote=True)
        return
    else:
        await update.reply_text(f"Fsub chat: <code>{chat['chat_id']}</code>", quote=True, parse_mode=enums.ParseMode.HTML)
        
@Client.on_message(filters.command("setchat2") & filters.user(ADMINS))
async def add_fsub_chats2(bot: Client, update: Message):
    await update.react("🍌")
    chat = update.command[1] if len(update.command) > 1 else None
    if not chat:
        await update.reply_text("Invalid chat id.", quote=True)
        return
    else:
        chat = int(chat)
    await db.add_fsub_chat2(chat)

    text = f"Added chat <code>{chat}</code> to the database."
    await update.reply_text(text=text, quote=True, parse_mode=enums.ParseMode.HTML)
    with open("./dynamic.env", "wt+") as f:
        f.write(f"REQ_CHANNEL2={chat}\n")
    restarti.update_one(
        {"_id": "frestart"},
        {"$set": {"restart": "on"}},
        upsert=True
    )
    os.execl(sys.executable, sys.executable, "bot.py")


@Client.on_message(filters.command("delchat2") & filters.user(ADMINS))
async def clear_fsub_chats2(bot: Client, update: Message):
    await update.react("👍")
    await db.delete_fsub_chat2(chat_id=(await db.get_fsub_chat2())['chat_id'])
    await update.reply_text(text="Deleted fsub chat from the database.", quote=True)
    with open("./dynamic.env", "wt+") as f:
        f.write(f"REQ_CHANNEL2=False\n")

    logger.info("Restarting to update REQ_CHANNEL from database...")
    os.execl(sys.executable, sys.executable, "bot.py")
    
@Client.on_message(filters.command("viewchat2") & filters.user(ADMINS))
async def get_fsub_chat2(bot: Client, update: Message):
    await update.react("👍")
    chat = await db.get_fsub_chat2()
    if not chat:
        await update.reply_text("No fsub chat found in the database.", quote=True)
        return
    else:
        await update.reply_text(f"Fsub chat: <code>{chat['chat_id']}</code>", quote=True, parse_mode=enums.ParseMode.HTML)

@Client.on_message(filters.command("deletefiles") & filters.user(ADMINS))
async def deletemultiplefiles(bot, message):
    chat_type = message.chat.type
    if chat_type != enums.ChatType.PRIVATE:
        return await message.reply_text(f"<b>Hᴇʏ {message.from_user.mention}, Tʜɪs ᴄᴏᴍᴍᴀɴᴅ ᴡᴏɴ'ᴛ ᴡᴏʀᴋ ɪɴ ɢʀᴏᴜᴘs. Iᴛ ᴏɴʟʏ ᴡᴏʀᴋs ᴏɴ ᴍʏ PM!</b>")
    else:
        pass
    try:
        keyword = message.text.split(" ", 1)[1]
    except:
        return await message.reply_text(f"<b>Hᴇʏ {message.from_user.mention}, Gɪᴠᴇ ᴍᴇ ᴀ ᴋᴇʏᴡᴏʀᴅ ᴀʟᴏɴɢ ᴡɪᴛʜ ᴛʜᴇ ᴄᴏᴍᴍᴀɴᴅ ᴛᴏ ᴅᴇʟᴇᴛᴇ ғɪʟᴇs.</b>")
    btn = [[
       InlineKeyboardButton("Yᴇs, Cᴏɴᴛɪɴᴜᴇ !", callback_data=f"killfilesdq#{keyword}")
       ],[
       InlineKeyboardButton("Nᴏ, Aʙᴏʀᴛ ᴏᴘᴇʀᴀᴛɪᴏɴ !", callback_data="close_data")
    ]]
    await message.reply_text(
        text="<b>Aʀᴇ ʏᴏᴜ sᴜʀᴇ? Dᴏ ʏᴏᴜ ᴡᴀɴᴛ ᴛᴏ ᴄᴏɴᴛɪɴᴜᴇ?\n\nNᴏᴛᴇ:- Tʜɪs ᴄᴏᴜʟᴅ ʙᴇ ᴀ ᴅᴇsᴛʀᴜᴄᴛɪᴠᴇ ᴀᴄᴛɪᴏɴ!</b>",
        reply_markup=InlineKeyboardMarkup(btn),
        parse_mode=enums.ParseMode.HTML
    )
    
@Client.on_message(filters.command("deletesmallfiles") & filters.user(ADMINS))
async def process_command(client, message):
    chat_id = message.chat.id
    processing_message = await message.reply_text("<b>Processing: Deleting files...</b>")
    
    total_files_deleted = 0
    batch_size = 250

    while True:
        deleted_files = await delete_files_below_threshold(db, threshold_size_mb=50, batch_size=batch_size)
        
        if deleted_files == 0:
            break

        total_files_deleted += deleted_files

        # Update the message to show progress
        progress_message = f'<b>Processing: Deleted {total_files_deleted} files in {total_files_deleted // batch_size} batches.</b>'
        await processing_message.edit_text(progress_message)
        await asyncio.sleep(3)

    print(f'Total files deleted: {total_files_deleted}')
    await processing_message.edit_text(f'<b>Deletion complete: Deleted {total_files_deleted} files.</b>')


@Client.on_message(filters.command('stats') & filters.incoming)
async def get_ststs(bot, message):
    rju = await message.reply('Fetching stats..')
    tot = await Media.count_documents()
    tota = await Mediaa.count_documents()
    total = tot + tota
    users = await db.total_users_count()
    chats = await db.total_chat_count()
    stats = await clientDB.command('dbStats')
    used_dbSize = (stats['dataSize']/(1024*1024))+(stats['indexSize']/(1024*1024))        
    free_dbSize = 512-used_dbSize
    stats2 = await clientDB2.command('dbStats')
    used_dbSize2 = (stats2['dataSize']/(1024*1024))+(stats2['indexSize']/(1024*1024))
    free_dbSize2 = 512-used_dbSize2
    stats3 = await clientDB3.command('dbStats')
    used_dbSize3 = (stats3['dataSize']/(1024*1024))+(stats2['indexSize']/(1024*1024))
    free_dbSize3 = 512-used_dbSize3
    await rju.edit(script.STATUS_TXT2.format(total, tot, round(used_dbSize2, 2), round(free_dbSize2, 2), tota, round(used_dbSize3, 2), round(free_dbSize3, 2), users, chats, round(used_dbSize, 2), round(free_dbSize, 2)))

@Client.on_message(filters.command('chats') & filters.user(ADMINS))
async def list_chats(bot, message):
        await message.reply_document('chats.txt', caption="List Of Chats")



@Client.on_message(filters.command('purge_one') & filters.private & filters.user(ADMINS))
async def purge_req_one(bot, message):
    r = await message.reply("`processing...`")
    await db.delete_all_one()
    await r.edit("**Req db Cleared**" )


@Client.on_message(filters.command('purge_two') & filters.private & filters.user(ADMINS))
async def purge_req_two(bot, message):
    r = await message.reply("`processing...`")
    await db.delete_all_two()
    await r.edit("**Req db Cleared**" )

@Client.on_message(filters.command("totalreq") & filters.user(ADMINS))
async def total_requests(bot, message): 
    rju = await message.reply('Fetching stats..')
    total_one = await db.get_all_one_count()
    total_two = await db.get_all_two_count()
    if REQ_CHANNEL1 != False: 
        req_channel1 = await bot.get_chat(REQ_CHANNEL1)
        req_channel1 = req_channel1.title
    else:
        req_channel1 = "REQ_CHANNEL1"
    if REQ_CHANNEL2 != False:
        req_channel2 = await bot.get_chat(REQ_CHANNEL2)
        req_channel2 = req_channel2.title
    else:
        req_channel2 = "REQ_CHANNEL2"
    await rju.edit(f"{req_channel1} : {total_one}\n{req_channel2} : {total_two}")


@Client.on_message(filters.command("delete_duplicate") & filters.user(ADMINS))
async def delete_duplicate_files(client, message):
    ok = await message.reply("prosessing...")
    deleted_count = 0
    batch_size = 0
    async def remove_duplicates(collection1, unique_files, ok, deleted_count, batch_size):                        
        async for duplicate_file in collection1.find():
            file_size = duplicate_file["file_size"]
            file_id = duplicate_file["file_id"]
            if file_size in unique_files and unique_files[file_size] != file_id:
                result_media1 = await collection1.find_one({'_id': file_id})                
                if result_media1:
                    await collection1.collection.delete_one({'_id': file_id})               
                    deleted_count += 1                
                    if deleted_count % 100 == 0:
                        batch_size += 1
                        await ok.edit(f'<b>Processing: Deleted {deleted_count} files in {batch_size} batches.</b>')
        return deleted_count, batch_size
    # Get all four collections
    media1_collection = Media
    media2_collection = Mediaa
    
    # Get all files from each collection
    all_files_media1 = await media1_collection.find({}, {"file_id": 1, "file_size": 1}).to_list(length=None)
    all_files_media2 = await media2_collection.find({}, {"file_id": 1, "file_size": 1}).to_list(length=None)
    
    # Combine files from all collections
    all_files = all_files_media1 + all_files_media2

    # Remove duplicate files while keeping one copy
    unique_files = {}
    for file_info in all_files:
        file_id = file_info["file_id"]
        file_size = file_info["file_size"]
        if file_size not in unique_files:
            unique_files[file_size] = file_id

    # Delete duplicate files from each collection
    deleted_count, batch_size = await remove_duplicates(media1_collection, unique_files, ok, deleted_count, batch_size)
    deleted_count = deleted_count
    batch_size = batch_size
    deleted_count, batch_size = await remove_duplicates(media2_collection, unique_files, ok, deleted_count, batch_size)
    deleted_count = deleted_count
    batch_size = batch_size
    
    # Send a final message indicating the total number of duplicates deleted
    await message.reply(f"Deleted {deleted_count} duplicate files. in {batch_size} batches")
