from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from AnonXMusic import YouTube, app
from AnonXMusic.core.call import Anony
from AnonXMusic.misc import db
from AnonXMusic.utils import seconds_to_min
from AnonXMusic.utils.inline import close_markup
from config import BANNED_USERS


# ---------------------------
# Inline buttons generator
# ---------------------------
def seek_buttons():
    buttons = [
        [
            InlineKeyboardButton("⏪ Back 20s", callback_data="cseek_20"),
            InlineKeyboardButton("⏩ Forward 20s", callback_data="seek_20"),
        ]
    ]
    return InlineKeyboardMarkup(buttons)


# ---------------------------
# Callback query handler
# ---------------------------
@app.on_callback_query(filters.regex(r"^(seek|cseek)_20$"))
async def seek_callback(_, query: CallbackQuery):
    action, value = query.data.split("_")
    skip_seconds = int(value)
    
    chat_id = query.message.chat.id
    playing = db.get(chat_id)
    if not playing:
        return await query.answer("No song is currently playing.", show_alert=True)
    
    duration_seconds = int(playing[0]["seconds"])
    if duration_seconds == 0:
        return await query.answer("This file cannot be seeked.", show_alert=True)

    file_path = playing[0]["file"]
    duration_played = int(playing[0]["played"])
    duration = playing[0]["dur"]

    # Determine seek direction
    if action == "cseek":  # backward
        if (duration_played - skip_seconds) <= 10:
            return await query.answer(
                f"Already at the beginning: {seconds_to_min(duration_played)}/{duration}",
                show_alert=True
            )
        to_seek = duration_played - skip_seconds + 1
    else:  # forward
        if (duration_seconds - (duration_played + skip_seconds)) <= 10:
            return await query.answer(
                f"Already near the end: {seconds_to_min(duration_played)}/{duration}",
                show_alert=True
            )
        to_seek = duration_played + skip_seconds + 1

    # Show "Processing..." to user
    await query.message.edit_text("⏳ Seeking, please wait...")

    # Handle YouTube or custom files
    if "vid_" in file_path:
        n, file_path = await YouTube.video(playing[0]["vidid"], True)
        if n == 0:
            return await query.message.edit_text("Cannot seek this file.", reply_markup=close_markup(_))

    check = (playing[0]).get("speed_path")
    if check:
        file_path = check
    if "index_" in file_path:
        file_path = playing[0]["vidid"]

    try:
        await Anony.seek_stream(
            chat_id,
            file_path,
            seconds_to_min(to_seek),
            duration,
            playing[0]["streamtype"],
        )
    except Exception as e:
        return await query.message.edit_text(f"Failed to seek: {e}", reply_markup=close_markup(_))

    # Update db
    if action == "cseek":
        db[chat_id][0]["played"] -= skip_seconds
    else:
        db[chat_id][0]["played"] += skip_seconds

    await query.message.edit_text(
        f"⏩ Seeked to {seconds_to_min(to_seek)} by {query.from_user.mention}",
        reply_markup=seek_buttons(),  # show buttons again
    )