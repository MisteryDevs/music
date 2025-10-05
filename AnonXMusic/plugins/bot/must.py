import random
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery
from pyrogram.errors import ChatAdminRequired, UserNotParticipant, ChatWriteForbidden
from AnonXMusic import app

# --- Configure required channels ---
REQUIRED_CHANNELS = [
    {"id": "vip_robotz", "display_name": "Vip_Robotz"},
    {"id": -1002021738886, "display_name": "Ur_Rishu_143"},
]

# Updated list of random captions
CAPTIONS = [
    "๏ ᴘʟᴇᴀsᴇ ᴊᴏɪɴ {channel_name} ᴛᴏ ᴄᴏɴᴛɪɴᴜᴇ ᴜsɪɴɢ ᴛʜᴇ ʙᴏᴛ!",
    "๏ ɪᴛ sᴇᴇᴍs ʏᴏᴜ ʜᴀᴠᴇɴ'ᴛ ᴊᴏɪɴᴇᴅ {channel_name} ʏᴇᴛ. ᴘʟᴇᴀsᴇ ᴊᴏɪɴ ᴛᴏ ᴘʀᴏᴄᴇᴇᴅ.",
    "๏ ᴊᴏɪɴ {channel_name} ᴛᴏ ᴜɴʟᴏᴄᴋ ғᴜʟʟ ᴀᴄᴄᴇss ᴛᴏ ᴍʏ ғᴇᴀᴛᴜʀᴇs!",
    "๏ ᴛᴏ ᴜsᴇ ᴍᴇ, ʏᴏᴜ ᴍᴜsᴛ ᴊᴏɪɴ {channel_name}.",
    "๏ {channel_name} ᴍᴜsᴛ ʙᴇ ᴊᴏɪɴᴇᴅ ʙᴇғᴏʀᴇ ʏᴏᴜ ᴄᴀɴ ᴄᴏɴᴛɪɴᴜᴇ!",
]

async def send_join_message(msg: Message, link: str, channel_name: str, all_done: bool=False):
    if all_done:
        await msg.reply_text("✅ ʏᴏᴜ ʜᴀᴠᴇ ᴊᴏɪɴᴇᴅ ᴀʟʟ ᴄʜᴀɴɴᴇʟs! ɴᴏᴡ ʏᴏᴜ ᴄᴀɴ ᴜsᴇ ᴛʜᴇ ʙᴏᴛ.")
        await msg.stop_propagation()
        return

    caption = random.choice(CAPTIONS).format(channel_name=channel_name)
    try:
        await msg.reply_text(
            text=caption,
            reply_markup=InlineKeyboardMarkup(
                [
                    [InlineKeyboardButton("• ᴊᴏɪɴ •", url=link)],
                    [InlineKeyboardButton("🔄 ʀᴇғʀᴇsʜ", callback_data="refresh_forcejoin")]
                ]
            ),
        )
        await msg.stop_propagation()
    except ChatWriteForbidden:
        pass


@app.on_message(filters.incoming & filters.private, group=-1)
async def must_join_channels(app: Client, msg: Message):
    if not REQUIRED_CHANNELS:
        return

    try:
        not_joined = []
        for chan in REQUIRED_CHANNELS:
            chat_id = chan["id"]
            display_name = chan.get("display_name") or str(chat_id)

            try:
                await app.get_chat_member(chat_id, msg.from_user.id)
                continue  # user already member
            except UserNotParticipant:
                # Need to join this channel
                invite_link = None
                try:
                    invite_link = await app.export_chat_invite_link(chat_id)
                except ChatAdminRequired:
                    if isinstance(chat_id, str) and not str(chat_id).startswith("-"):
                        invite_link = f"https://t.me/{chat_id}"
                if not invite_link:
                    continue

                not_joined.append((invite_link, display_name))

        if not not_joined:
            # all channels joined
            await send_join_message(msg, "", "", all_done=True)
        else:
            # send join requirement for the first missing channel
            link, name = not_joined[0]
            await send_join_message(msg, link, name)

    except ChatAdminRequired:
        print("⚠️ Please make the bot admin in required channels to generate invite links.")


# --- Callback Handler for Refresh ---
@app.on_callback_query(filters.regex("refresh_forcejoin"))
async def refresh_join(client: Client, query: CallbackQuery):
    msg = query.message
    user = query.from_user
    not_joined = []

    for chan in REQUIRED_CHANNELS:
        chat_id = chan["id"]
        display_name = chan.get("display_name") or str(chat_id)
        try:
            await client.get_chat_member(chat_id, user.id)
            continue
        except UserNotParticipant:
            if isinstance(chat_id, str) and not str(chat_id).startswith("-"):
                invite_link = f"https://t.me/{chat_id}"
            else:
                try:
                    invite_link = await client.export_chat_invite_link(chat_id)
                except:
                    invite_link = None
            if invite_link:
                not_joined.append((invite_link, display_name))

    if not not_joined:
        await msg.edit_text("✅ ʏᴏᴜ ʜᴀᴠᴇ ᴊᴏɪɴᴇᴅ ᴀʟʟ ᴄʜᴀɴɴᴇʟs! ɴᴏᴡ ʏᴏᴜ ᴄᴀɴ ᴜsᴇ ᴛʜᴇ ʙᴏᴛ.")
    else:
        link, name = not_joined[0]
        caption = random.choice(CAPTIONS).format(channel_name=name)
        await msg.edit_text(
            text=caption,
            reply_markup=InlineKeyboardMarkup(
                [
                    [InlineKeyboardButton("• ᴊᴏɪɴ •", url=link)],
                    [InlineKeyboardButton("🔄 ʀᴇғʀᴇsʜ", callback_data="refresh_forcejoin")]
                ]
            ),
        )