from pyrogram import filters
from pyrogram.types import Message, CallbackQuery

from AnonXMusic import YouTube, app
from AnonXMusic.core.call import Anony
from AnonXMusic.misc import db
from AnonXMusic.utils import AdminRightsCheck, seconds_to_min
from AnonXMusic.utils.inline import close_markup
from config import BANNED_USERS


# -----------------------------
# 🔹 Common Seek Function
# -----------------------------
async def do_seek(chat_id: int, skip: int, backward: bool = False):
    playing = db.get(chat_id)
    if not playing:
        return None, "❌ No track is playing right now!"

    duration_seconds = int(playing[0]["seconds"])
    duration_played = int(playing[0]["played"])
    duration = playing[0]["dur"]
    file_path = playing[0]["file"]

    # 🔹 New position calculation
    if backward:
        to_seek = max(duration_played - skip, 0)
        if to_seek <= 10:
            return None, f"⚠️ Can't seek before {seconds_to_min(to_seek)}"
        db[chat_id][0]["played"] = to_seek
    else:
        if duration_played + skip >= duration_seconds - 10:
            return None, f"⚠️ Can't seek beyond {duration}"
        to_seek = duration_played + skip
        db[chat_id][0]["played"] = to_seek

    # 🔹 Stream adjustments
    if "vid_" in file_path:
        n, file_path = await YouTube.video(playing[0]["vidid"], True)
        if n == 0:
            return None, "❌ Stream error!"
    check = (playing[0]).get("speed_path")
    if check:
        file_path = check
    if "index_" in file_path:
        file_path = playing[0]["vidid"]

    # 🔹 Apply seek
    try:
        await Anony.seek_stream(
            chat_id,
            file_path,
            seconds_to_min(to_seek),
            duration,
            playing[0]["streamtype"],
        )
    except Exception as e:
        return None, f"❌ Seek failed: {e}"

    return to_seek, None


# -----------------------------
# 🔹 Command Handler (/seek)
# -----------------------------
@app.on_message(
    filters.command(["seek", "cseek", "seekback", "cseekback"])
    & filters.group
    & ~BANNED_USERS
)
@AdminRightsCheck
async def seek_comm(cli, message: Message, _, chat_id):
    if len(message.command) == 1:
        return await message.reply_text(_["admin_20"])

    query = message.text.split(None, 1)[1].strip()
    if not query.isnumeric():
        return await message.reply_text(_["admin_21"])

    skip = int(query)
    backward = message.command[0] in ["seekback", "cseekback"]

    mystic = await message.reply_text(_["admin_24"])
    to_seek, error = await do_seek(chat_id, skip, backward=backward)
    if error:
        return await mystic.edit_text(error, reply_markup=close_markup(_))

    await mystic.edit_text(
        text=_["admin_25"].format(seconds_to_min(to_seek), message.from_user.mention),
        reply_markup=close_markup(_),
    )


# -----------------------------
# 🔹 Callback Handler (buttons)
# -----------------------------
async def is_admin(client, chat_id: int, user_id: int) -> bool:
    """Check if user is admin in chat"""
    member = await client.get_chat_member(chat_id, user_id)
    return member.privileges is not None or member.status in ("administrator", "creator")


@app.on_callback_query(filters.regex(r"^ADMIN (Forward|Backward)\|(\-?\d+)$"))
async def seek_cb(client, cq: CallbackQuery):
    action, chat_id = cq.data.split("|", 1)
    chat_id = int(chat_id)

    # 🔹 Admin check
    if not await is_admin(client, chat_id, cq.from_user.id):
        return await cq.answer("⚠️ Only admins can control playback!", show_alert=True)

    # 🔹 Perform seek
    backward = "Backward" in action
    to_seek, error = await do_seek(chat_id, 20, backward=backward)

    if error:
        return await cq.answer(error, show_alert=True)

    await cq.answer("✅ Seek successful!", show_alert=False)
    await cq.message.edit_text(
        f"⏩ Track seeked to: {seconds_to_min(to_seek)}",
        reply_markup=close_markup({}),
    )