from pyrogram import filters
from pyrogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup

from AnonXMusic import YouTube, app
from AnonXMusic.core.call import Anony
from AnonXMusic.misc import db
from AnonXMusic.utils import AdminRightsCheck, seconds_to_min
from config import BANNED_USERS


# -----------------------------
# 🔹 Close markup helper
# -----------------------------
def close_markup(_dict=None):
    text = "❌ Close"
    if _dict and "CLOSE_BUTTON" in _dict:
        text = _dict["CLOSE_BUTTON"]
    return InlineKeyboardMarkup([[InlineKeyboardButton(text=text, callback_data="close")]])


# -----------------------------
# 🔹 Admin check helper
# -----------------------------
async def is_admin(client, chat_id: int, user_id: int) -> bool:
    member = await client.get_chat_member(chat_id, user_id)
    return member.status in ["administrator", "creator"] or member.privileges is not None


# -----------------------------
# 🔹 Reusable seek function
# -----------------------------
async def do_seek(chat_id: int, skip: int, backward: bool = False):
    playing = db.get(chat_id)
    if not playing:
        return None, "❌ No track is playing right now!"

    duration_seconds = int(playing[0]["seconds"])
    duration_played = int(playing[0]["played"])
    duration = playing[0]["dur"]
    file_path = playing[0]["file"]

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

    # Adjust file path
    if "vid_" in file_path:
        n, file_path = await YouTube.video(playing[0]["vidid"], True)
        if n == 0:
            return None, "❌ Stream error!"
    check = playing[0].get("speed_path")
    if check:
        file_path = check
    if "index_" in file_path:
        file_path = playing[0]["vidid"]

    # Apply seek
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
# 🔹 Seek Command Handler
# -----------------------------
@app.on_message(
    filters.command(["seek", "cseek", "seekback", "cseekback"])
    & filters.group
    & ~BANNED_USERS
)
@AdminRightsCheck
async def seek_comm(cli, message: Message, _, chat_id):
    if len(message.command) == 1:
        return await message.reply_text("❌ Specify seconds to seek.")

    query = message.text.split(None, 1)[1].strip()
    if not query.isnumeric():
        return await message.reply_text("❌ Only numeric values allowed!")

    skip = int(query)
    backward = message.command[0] in ["seekback", "cseekback"]

    mystic = await message.reply_text("⏳ Seeking...")
    to_seek, error = await do_seek(chat_id, skip, backward=backward)
    if error:
        return await mystic.edit_text(error, reply_markup=close_markup())

    # Send live seek bar buttons
    await mystic.edit_text(
        f"⏩ Track seeked to: {seconds_to_min(to_seek)}",
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("<- 20s", callback_data=f"ADMIN Backward|{chat_id}"),
                    InlineKeyboardButton("20s + >", callback_data=f"ADMIN Forward|{chat_id}"),
                ],
                [InlineKeyboardButton("❌ Close", callback_data="close")],
            ]
        ),
    )


# -----------------------------
# 🔹 Callback Handler for Buttons
# -----------------------------
@app.on_callback_query(filters.regex(r"^ADMIN (Forward|Backward)\|(\d+)"))
async def seek_cb(client, cq: CallbackQuery):
    try:
        action, chat_id = cq.data.split("|")[:2]
        chat_id = int(chat_id)
    except:
        return await cq.answer("Invalid callback!", show_alert=True)

    # Admin check
    if not await is_admin(client, chat_id, cq.from_user.id):
        return await cq.answer("⚠️ Only admins can control playback!", show_alert=True)

    backward = "Backward" in action
    to_seek, error = await do_seek(chat_id, 20, backward=backward)

    if error:
        return await cq.answer(error, show_alert=True)

    await cq.answer("✅ Seek successful!", show_alert=False)
    await cq.message.edit_text(
        f"⏩ Track seeked to: {seconds_to_min(to_seek)}",
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("<- 20s", callback_data=f"ADMIN Backward|{chat_id}"),
                    InlineKeyboardButton("20s + >", callback_data=f"ADMIN Forward|{chat_id}"),
                ],
                [InlineKeyboardButton("❌ Close", callback_data="close")],
            ]
        ),
    )