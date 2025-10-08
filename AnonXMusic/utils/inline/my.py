from pyrogram import filters
from pyrogram.types import CallbackQuery

from AnonXMusic.core.call import Anony
from AnonXMusic.misc import db
from AnonXMusic.utils import seconds_to_min
from AnonXMusic.utils.inline import close_markup


@app.on_callback_query(filters.regex(r"^ADMIN (Forward|Backward)\|(\-?\d+)$"))
async def seek_cb(client, cq: CallbackQuery):
    action, chat_id = cq.data.split("|", 1)
    chat_id = int(chat_id)

    playing = db.get(chat_id)
    if not playing:
        return await cq.answer("No track is playing right now!", show_alert=True)

    duration_seconds = int(playing[0]["seconds"])
    duration_played = int(playing[0]["played"])
    duration = playing[0]["dur"]
    file_path = playing[0]["file"]

    # Seek time
    skip = 20
    if action.split()[1] == "Backward":
        to_seek = max(duration_played - skip, 0)
        db[chat_id][0]["played"] = to_seek
    else:
        if duration_played + skip >= duration_seconds:
            return await cq.answer("Can't seek beyond track end!", show_alert=True)
        to_seek = duration_played + skip
        db[chat_id][0]["played"] = to_seek

    try:
        await Anony.seek_stream(
            chat_id,
            file_path,
            seconds_to_min(to_seek),
            duration,
            playing[0]["streamtype"],
        )
    except Exception as e:
        return await cq.message.reply_text(
            f"Seek failed: {e}", reply_markup=close_markup({})
        )

    await cq.answer()
    await cq.message.edit_text(
        f"⏩ Seeked to {seconds_to_min(to_seek)}",
        reply_markup=close_markup({}),
    )