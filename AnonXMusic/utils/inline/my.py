from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from AnonXMusic import YouTube, app
from AnonXMusic.core.call import Anony
from AnonXMusic.misc import db
from AnonXMusic.utils import seconds_to_min
from AnonXMusic.utils.inline import close_markup

# ---------------------------
# Inline buttons generator
# ---------------------------
def seek_buttons():
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("⏪ Back 20s", callback_data="cseek_20"),
                InlineKeyboardButton("⏩ Forward 20s", callback_data="seek_20"),
            ],
            [
                InlineKeyboardButton("❌ Close", callback_data="close_seek")
            ]
        ]
    )

# ---------------------------
# Callback for seek buttons
# ---------------------------
@app.on_callback_query(filters.regex(r"^(seek|cseek)_20$"))
async def seek_callback(_, query: CallbackQuery):
    chat_id = query.message.chat.id
    user = query.from_user.mention
    action, value = query.data.split("_")
    skip = int(value)

    playing = db.get(chat_id)
    if not playing:
        return await query.answer("No song is currently playing.", show_alert=True)

    duration_seconds = int(playing[0]["seconds"])
    if duration_seconds == 0:
        return await query.answer("This file cannot be seeked.", show_alert=True)

    file_path = playing[0]["file"]
    played = int(playing[0]["played"])
    duration = playing[0]["dur"]

    # Calculate new position
    if action == "cseek":  # backward
        if (played - skip) <= 0:
            return await query.answer(f"Already at the beginning ({seconds_to_min(played)}/{duration})", show_alert=True)
        to_seek = played - skip
    else:  # forward
        if (played + skip) >= duration_seconds:
            return await query.answer(f"Already near the end ({seconds_to_min(played)}/{duration})", show_alert=True)
        to_seek = played + skip

    # Show temporary processing message
    await query.message.edit_text("⏳ Seeking, please wait...")

    # Handle YouTube videos
    if "vid_" in file_path:
        n, file_path = await YouTube.video(playing[0]["vidid"], True)
        if n == 0:
            return await query.message.edit_text("Cannot seek this file.", reply_markup=close_markup(_))

    check = playing[0].get("speed_path")
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
            playing[0]["streamtype"]
        )
    except Exception as e:
        return await query.message.edit_text(f"Failed to seek: {e}", reply_markup=close_markup(_))

    # Update DB
    if action == "cseek":
        db[chat_id][0]["played"] -= skip
    else:
        db[chat_id][0]["played"] += skip

    await query.message.edit_text(
        f"⏩ Seeked to {seconds_to_min(to_seek)} by {user}",
        reply_markup=seek_buttons()
    )


# ---------------------------
# Close button handler
# ---------------------------
@app.on_callback_query(filters.regex(r"^close_seek$"))
async def close_seek(_, query: CallbackQuery):
    try:
        await query.message.edit_reply_markup(None)
        await query.answer("Closed!", show_alert=True)
    except:
        await query.answer("Cannot close.", show_alert=True)