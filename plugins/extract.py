import asyncio
import os
import logging
import aiofiles
import tempfile
import uuid
import requests

from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from telegraph import Telegraph
from pymediainfo import MediaInfo

from database.ia_filterdb import get_file_details
from info import FILE_STORE_CHANNEL, LOG_CHANNEL

logger = logging.getLogger(__name__)


TELEGRAPH_ACCESS_TOKEN = os.environ.get("TELEGRAPH_ACCESS_TOKEN")

if TELEGRAPH_ACCESS_TOKEN:
    telegraph = Telegraph(access_token=TELEGRAPH_ACCESS_TOKEN)
else:
    telegraph = Telegraph()
    try:
        telegraph.create_account(short_name="Leobot")
    except Exception:
        logger.exception("Failed to create Telegraph account")


def format_track(lang, title):
    lang = (lang or "").strip()
    title = (title or "").strip()

    if lang and lang.lower() != "und":
        return lang

    if title:
        return title

    return "und"


@Client.on_callback_query(filters.regex(r"^extract_data"), group=2)
async def extract_data_handler(client: Client, query: CallbackQuery):

    try:
        await query.answer("Fetching Details...", show_alert=False)
    except Exception:
        pass

    try:
        _, file_id = query.data.split(":", 1)
    except Exception:
        await query.answer("Invalid file data.", show_alert=True)
        return

    current_markup = query.message.reply_markup
    wait_keyboard = []

    if current_markup and getattr(current_markup, "inline_keyboard", None):
        for row in current_markup.inline_keyboard:
            new_row = []

            for btn in row:
                if btn.callback_data == query.data:
                    new_row.append(
                        InlineKeyboardButton(
                            "ᴘʟᴇᴀꜱᴇ ᴡᴀɪᴛ... ⏳",
                            callback_data="wait_data"
                        )
                    )
                else:
                    new_row.append(btn)

            wait_keyboard.append(new_row)

    try:
        await query.edit_message_reply_markup(
            reply_markup=InlineKeyboardMarkup(wait_keyboard)
        )
    except Exception:
        pass

    temp_path = os.path.join(
        tempfile.gettempdir(),
        f"leobot_{query.from_user.id}_{query.message.id}_{uuid.uuid4().hex}.tmp"
    )

    storage_chat = None

    try:

        files_ = await get_file_details(file_id)

        if not files_:
            await query.message.reply_text(
                "❌ File not found in database."
            )
            return

        # Use FILE_STORE_CHANNEL if configured.
        if FILE_STORE_CHANNEL:
            storage_chat = FILE_STORE_CHANNEL[0]
        else:
            storage_chat = LOG_CHANNEL

        # Get the actual Telegram media message.
        log_msg = await client.send_cached_media(
            chat_id=storage_chat,
            file_id=file_id
        )

        # File name
        file_name = (
            log_msg.document.file_name
            if log_msg.document
            else "Media File"
        )

        safe_title = (
            file_name.replace(".", " ")
            .replace("_", " ")
            .replace("-", " ")
            .replace("[", "")
            .replace("]", "")
            .replace("(", "")
            .replace(")", "")
            .replace("mkv", "")
            .replace("mp4", "")
        )

        # Get file size
        media = None

        if log_msg.media:
            try:
                media = getattr(
                    log_msg,
                    log_msg.media.value
                )
            except Exception:
                media = None

        file_size = getattr(media, "file_size", 0) or 0

        chunk_limit = (
            5
            if file_size > 200 * 1024 * 1024
            else 4
        )

        # Download temporary file
        async with aiofiles.open(temp_path, "wb") as f:

            async for chunk in client.stream_media(
                log_msg,
                limit=chunk_limit
            ):
                await f.write(chunk)

        # Parse MediaInfo
        lib_path = (
            os.path.abspath("MediaInfo.dll")
            if os.path.exists("MediaInfo.dll")
            else None
        )

        media_info = await asyncio.wait_for(
            asyncio.to_thread(
                MediaInfo.parse,
                temp_path,
                library_file=lib_path
            ),
            timeout=30
        )

        audio_tracks = []
        subtitle_tracks = []
        video_info = []

        seen_audio = set()
        seen_subs = set()

        for track in media_info.tracks:

            ttype = (
                track.track_type or ""
            ).lower()

            # VIDEO
            if ttype == "video":

                codec = (
                    track.format
                    or track.codec_id
                    or "Unknown"
                )

                width = track.width or "?"
                height = track.height or "?"

                video_info.append(
                    f"Video: {codec} {width}x{height}"
                )

            # AUDIO
            elif ttype == "audio":

                lang = (
                    track.other_language[0]
                    if getattr(
                        track,
                        "other_language",
                        None
                    )
                    else track.language or "und"
                )

                key = (
                    lang,
                    track.title
                )

                if key not in seen_audio:

                    seen_audio.add(key)

                    audio_tracks.append({
                        "language": lang,
                        "title": track.title
                    })

            # SUBTITLE
            elif ttype in (
                "text",
                "subtitle"
            ):

                lang = (
                    track.other_language[0]
                    if getattr(
                        track,
                        "other_language",
                        None
                    )
                    else track.language or "und"
                )

                key = (
                    lang,
                    track.title
                )

                if key not in seen_subs:

                    seen_subs.add(key)

                    subtitle_tracks.append({
                        "language": lang,
                        "title": track.title
                    })

        # Build Telegraph page
        page_parts = []

        page_parts.append(
            "<h3><b>Available Tracks</b></h3><br>"
        )

        # Video
        if video_info:

            page_parts.append(
                "<b>Video Track:</b><br>"
            )

            for video in video_info:

                page_parts.append(
                    f"<blockquote>• {video}</blockquote>"
                )

            page_parts.append("<br>")

        # Audio
        if audio_tracks:

            page_parts.append(
                f"<b>Audio Tracks ({len(audio_tracks)}):</b><br>"
            )

            for audio in audio_tracks:

                page_parts.append(
                    "<blockquote>• "
                    f"{format_track(audio['language'], audio['title'])}"
                    "</blockquote>"
                )

            page_parts.append("<br>")

        else:

            page_parts.append(
                "<b>Audio Tracks:</b> None<br><br>"
            )

        # Subtitles
        if subtitle_tracks:

            page_parts.append(
                f"<b>Subtitle Tracks ({len(subtitle_tracks)}):</b><br>"
            )

            for subtitle in subtitle_tracks:

                page_parts.append(
                    "<blockquote>• "
                    f"{format_track(subtitle['language'], subtitle['title'])}"
                    "</blockquote>"
                )

            page_parts.append("<br>")

        else:

            page_parts.append(
                "<b>Subtitle Tracks:</b> None<br>"
            )

        page_content = "".join(page_parts)

        # Create Telegraph page
        try:

            response = await asyncio.to_thread(
                telegraph.create_page,
                title=safe_title[:200],
                html_content=page_content,
                author_name="Leobot"
            )

        except (
            requests.exceptions.ConnectionError,
            requests.exceptions.ReadTimeout
        ):

            await query.message.reply_text(
                "⚠️ Telegraph is busy. Try again later."
            )
            return

        telegraph_url = response["url"]

        # Replace button
        success_keyboard = []

        if current_markup and getattr(
            current_markup,
            "inline_keyboard",
            None
        ):

            for row in current_markup.inline_keyboard:

                new_row = []

                for btn in row:

                    if btn.callback_data == query.data:

                        new_row.append(
                            InlineKeyboardButton(
                                "📝 ᴠɪᴇᴡ ᴛʀᴀᴄᴋꜱ 📝",
                                url=telegraph_url
                            )
                        )

                    else:

                        new_row.append(btn)

                success_keyboard.append(new_row)

        await query.edit_message_reply_markup(
            reply_markup=InlineKeyboardMarkup(
                success_keyboard
            )
        )

        # Delete temporary storage message
        try:
            await log_msg.delete()
        except Exception:
            pass

    except Exception as e:

        logger.exception(e)

        try:
            await query.message.reply_text(
                f"❌ Error: {e}"
            )
        except Exception:
            pass

    finally:

        if os.path.exists(temp_path):

            try:
                os.remove(temp_path)
            except Exception:
                pass
