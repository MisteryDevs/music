import os
import re
import aiofiles
import aiohttp
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont
from youtubesearchpython.__future__ import VideosSearch
from config import YOUTUBE_IMG_URL
import shutil

CACHE_DIR = "cache"
os.makedirs(CACHE_DIR, exist_ok=True)

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

async def gen_thumb(videoid: str, input_image_path: str = None) -> str:
    # 1️⃣ Initialize variables safely
    cache_path = os.path.join(CACHE_DIR, f"{videoid}_v4.png")
    title = "Unsupported Title"
    thumbnail = YOUTUBE_IMG_URL
    duration = None
    views = "Unknown Views"
    is_live = False
    duration_text = "Unknown Mins"

    # Remove old thumbnail if exists
    if os.path.exists(cache_path):
        os.remove(cache_path)

    # Resolve input image preference
    resolved_input_image = None
    if input_image_path and os.path.isfile(input_image_path):
        resolved_input_image = input_image_path
    elif os.path.isfile(videoid):
        resolved_input_image = videoid

    # Use local image if available
    if resolved_input_image:
        thumb_path = os.path.join(CACHE_DIR, f"thumb_{os.path.basename(resolved_input_image)}")
        try:
            shutil.copyfile(resolved_input_image, thumb_path)
        except Exception:
            return YOUTUBE_IMG_URL

        # Set metadata from file
        title = re.sub(r"\W+", " ", os.path.splitext(os.path.basename(resolved_input_image))[0]).title()
        views = "From Image"
        duration_text = "Unknown Mins"
        is_live = False
    else:
        # Fetch from YouTube
        try:
            results = VideosSearch(f"https://www.youtube.com/watch?v={videoid}", limit=1)
            results_data = await results.next()
            result_items = results_data.get("result", [])
            if result_items:
                data = result_items[0]
                title = re.sub(r"\W+", " ", data.get("title", "Unsupported Title")).title()
                thumbnail = data.get("thumbnails", [{}])[0].get("url", YOUTUBE_IMG_URL)
                duration = data.get("duration")
                views = data.get("viewCount", {}).get("short", "Unknown Views")
        except Exception:
            pass  # keep defaults

        is_live = not duration or str(duration).strip().lower() in {"", "live", "live now"}
        duration_text = "Live" if is_live else duration or "Unknown Mins"

        # Download thumbnail
        thumb_path = os.path.join(CACHE_DIR, f"thumb{videoid}.png")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(thumbnail) as resp:
                    if resp.status == 200:
                        async with aiofiles.open(thumb_path, "wb") as f:
                            await f.write(await resp.read())
        except Exception:
            thumb_path = YOUTUBE_IMG_URL  # fallback

    # Open image
    try:
        base = Image.open(thumb_path).convert("RGBA")
    except Exception:
        return YOUTUBE_IMG_URL

    base = base.resize((1280, 720)).convert("RGBA")
    bg = ImageEnhance.Brightness(base.filter(ImageFilter.BoxBlur(10))).enhance(0.6)

    # Frosted panel
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

    # Thumb inside panel
    thumb = base.resize((THUMB_W, THUMB_H))
    tmask = Image.new("L", thumb.size, 0)
    ImageDraw.Draw(tmask).rounded_rectangle((0, 0, THUMB_W, THUMB_H), 20, fill=255)
    bg.paste(thumb, (THUMB_X, THUMB_Y), tmask)

    # Draw text
    draw.text((TITLE_X, TITLE_Y), trim_to_width(title, title_font, MAX_TITLE_WIDTH), fill="black", font=title_font)
    draw.text((META_X, META_Y), f"YouTube | {views}", fill="black", font=regular_font)

    # Progress bar
    draw.line([(BAR_X, BAR_Y), (BAR_X + BAR_RED_LEN, BAR_Y)], fill="red", width=6)
    draw.line([(BAR_X + BAR_RED_LEN, BAR_Y), (BAR_X + BAR_TOTAL_LEN, BAR_Y)], fill="gray", width=5)
    draw.ellipse([(BAR_X + BAR_RED_LEN - 7, BAR_Y - 7), (BAR_X + BAR_RED_LEN + 7, BAR_Y + 7)], fill="red")

    draw.text((BAR_X, BAR_Y + 15), "00:00", fill="black", font=regular_font)
    end_text = "Live" if is_live else duration_text
    draw.text((BAR_X + BAR_TOTAL_LEN - (90 if is_live else 60), BAR_Y + 15),
              end_text, fill="red" if is_live else "black", font=regular_font)

    # Play icons
    icons_path = "AnonXMusic/assets/play_icons.png"
    if os.path.isfile(icons_path):
        ic = Image.open(icons_path).resize((ICONS_W, ICONS_H)).convert("RGBA")
        r, g, b, a = ic.split()
        black_ic = Image.merge("RGBA", (r.point(lambda *_: 0), g.point(lambda *_: 0), b.point(lambda *_: 0), a))
        bg.paste(black_ic, (ICONS_X, ICONS_Y), black_ic)

    # Cleanup temporary thumb
    if resolved_input_image and os.path.exists(thumb_path):
        os.remove(thumb_path)

    # Save final thumbnail
    bg.save(cache_path)
    return cache_path