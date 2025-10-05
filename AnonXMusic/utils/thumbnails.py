import os
import re
import aiofiles
import aiohttp
import shutil
import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont
from unidecode import unidecode
#from youtubesearchpython.future import VideosSearch
from AnonXMusic import app
from config import YOUTUBE_IMG_URL

from youtubesearchpython import VideosSearch

CACHE_DIR = "cache"
os.makedirs(CACHE_DIR, exist_ok=True)

# Panel & layout constants
PANEL_W, PANEL_H = 763, 545
PANEL_X = (1280 - PANEL_W) // 2
PANEL_Y = 88
TRANSPARENCY = 170
INNER_OFFSET = 36

THUMB_W, THUMB_H = 542, 273
THUMB_X = PANEL_X + (PANEL_W - THUMB_W) // 2
THUMB_Y = PANEL_Y + INNER_OFFSET

TITLE_X = 377
META_X = 377
TITLE_Y = THUMB_Y + THUMB_H + 10
META_Y = TITLE_Y + 45

BAR_X, BAR_Y = 388, META_Y + 45
BAR_RED_LEN = 280
BAR_TOTAL_LEN = 480

ICONS_W, ICONS_H = 415, 45
ICONS_X = PANEL_X + (PANEL_W - ICONS_W) // 2
ICONS_Y = BAR_Y + 48

MAX_TITLE_WIDTH = 580

def trim_to_width(text, font, max_width):
    ellipsis = "…"
    if (font.getbbox(text)[2] - font.getbbox(text)[0]) <= max_width:
        return text
    for i in range(len(text) - 1, 0, -1):
        cropped = text[:i] + ellipsis
        if (font.getbbox(cropped)[2] - font.getbbox(cropped)[0]) <= max_width:
            return cropped
    return ellipsis

def circle(img):
    h, w = img.size
    a = Image.new("L", [h, w], 0)
    b = ImageDraw.Draw(a)
    b.pieslice([(0, 0), (h, w)], 0, 360, fill=255)
    c = np.array(img)
    d = np.array(a)
    e = np.dstack((c, d))
    return Image.fromarray(e)

def changeImageSize(maxWidth, maxHeight, image):
    widthRatio = maxWidth / image.size[0]
    heightRatio = maxHeight / image.size[1]
    newWidth = int(widthRatio * image.size[0])
    newHeight = int(heightRatio * image.size[1])
    return image.resize((newWidth, newHeight))

async def gen_thumb(videoid: str, user_id=None, input_image_path: str = None) -> str:
    cache_path = os.path.join(CACHE_DIR, f"{videoid}_{user_id or 'v4'}.png")
    if os.path.exists(cache_path):
        os.remove(cache_path)

    title = "Unsupported Title"
    duration_text = "Unknown Mins"
    views = "Unknown Views"
    is_live = False
    thumb_path = None

    # Handle input image first
    resolved_input_image = None
    if input_image_path and os.path.isfile(input_image_path):
        resolved_input_image = input_image_path
    elif os.path.isfile(videoid):
        resolved_input_image = videoid

    if resolved_input_image:
        thumb_path = os.path.join(CACHE_DIR, f"thumb_{os.path.basename(resolved_input_image)}")
        try:
            shutil.copyfile(resolved_input_image, thumb_path)
            title = re.sub(r"\W+", " ", os.path.splitext(os.path.basename(resolved_input_image))[0]).title()
            views = "From Image"
            duration_text = "Unknown Mins"
        except Exception:
            return YOUTUBE_IMG_URL
    else:
        # Fetch YouTube data
        try:
            results = VideosSearch(f"https://www.youtube.com/watch?v={videoid}", limit=1)
            results_data = await results.next()
            data = results_data.get("result", [{}])[0]
            title = re.sub(r"\W+", " ", data.get("title", "Unsupported Title")).title()
            thumbnail = data.get("thumbnails", [{}])[0].get("url", YOUTUBE_IMG_URL)
            duration = data.get("duration")
            views = data.get("viewCount", {}).get("short", "Unknown Views")
            is_live = not duration or str(duration).strip().lower() in {"", "live", "live now"}
            duration_text = "Live" if is_live else duration or "Unknown Mins"

            thumb_path = os.path.join(CACHE_DIR, f"thumb{videoid}.png")
            async with aiohttp.ClientSession() as session:
                async with session.get(thumbnail) as resp:
                    if resp.status == 200:
                        async with aiofiles.open(thumb_path, "wb") as f:
                            await f.write(await resp.read())
        except Exception:
            thumb_path = None

    try:
        base = Image.open(thumb_path).convert("RGBA") if thumb_path else Image.new("RGBA", (1280, 720), "gray")
        base = base.resize((1280, 720))
    except Exception:
        base = Image.new("RGBA", (1280, 720), "gray")

    bg = ImageEnhance.Brightness(base.filter(ImageFilter.BoxBlur(10))).enhance(0.6)

    # Panel overlay
    panel_area = bg.crop((PANEL_X, PANEL_Y, PANEL_X + PANEL_W, PANEL_Y + PANEL_H))
    overlay = Image.new("RGBA", (PANEL_W, PANEL_H), (255, 255, 255, TRANSPARENCY))
    frosted = Image.alpha_composite(panel_area, overlay)
    mask = Image.new("L", (PANEL_W, PANEL_H), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, PANEL_W, PANEL_H), 50, fill=255)
    bg.paste(frosted, (PANEL_X, PANEL_Y), mask)

    draw = ImageDraw.Draw(bg)
    try:
        title_font = ImageFont.truetype("AnonXMusic/assets/font2.ttf", 32)
        regular_font = ImageFont.truetype("AnonXMusic/assets/font.ttf", 18)
    except OSError:
        title_font = regular_font = ImageFont.load_default()

    # Small thumbnail inside panel
    thumb = base.resize((THUMB_W, THUMB_H))
    tmask = Image.new("L", thumb.size, 0)
    ImageDraw.Draw(tmask).rounded_rectangle((0, 0, THUMB_W, THUMB_H), 20, fill=255)
    bg.paste(thumb, (THUMB_X, THUMB_Y), tmask)

    draw.text((TITLE_X, TITLE_Y), trim_to_width(title, title_font, MAX_TITLE_WIDTH), fill="black", font=title_font)
    draw.text((META_X, META_Y), f"YouTube | {views}", fill="black", font=regular_font)

    # Progress bar
    draw.line([(BAR_X, BAR_Y), (BAR_X + BAR_RED_LEN, BAR_Y)], fill="red", width=6)
    draw.line([(BAR_X + BAR_RED_LEN, BAR_Y), (BAR_X + BAR_TOTAL_LEN, BAR_Y)], fill="gray", width=5)
    draw.ellipse([(BAR_X + BAR_RED_LEN - 7, BAR_Y - 7), (BAR_X + BAR_RED_LEN + 7, BAR_Y + 7)], fill="red")
    draw.text((BAR_X, BAR_Y + 15), "00:00", fill="black", font=regular_font)
    draw.text((BAR_X + BAR_TOTAL_LEN - (90 if is_live else 60), BAR_Y + 15),
              duration_text, fill="red" if is_live else "black", font=regular_font)

    # Play icons
    icons_path = "AnonXMusic/assets/play_icons.png"
    if os.path.isfile(icons_path):
        ic = Image.open(icons_path).resize((ICONS_W, ICONS_H)).convert("RGBA")
        r, g, b, a = ic.split()
        black_ic = Image.merge("RGBA", (r.point(lambda *_: 0), g.point(lambda *_: 0), b.point(lambda *_: 0), a))
        bg.paste(black_ic, (ICONS_X, ICONS_Y), black_ic)

    # Old-style user avatar circle
    if user_id:
        try:
            async for photo in app.get_chat_photos(user_id, 1):
                sp = await app.download_media(photo.file_id, file_name=f"{user_id}.jpg")
            user_img = Image.open(sp)
            avatar = changeImageSize(200, 200, circle(user_img))
            bg.paste(avatar, (1045, 225), mask=avatar)
        except Exception:
            pass

    # Cleanup
    if resolved_input_image and os.path.exists(thumb_path):
        os.remove(thumb_path)

    bg.save(cache_path)
    return cache_path