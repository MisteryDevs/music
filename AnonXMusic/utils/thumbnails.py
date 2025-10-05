import os
import re
import aiofiles
import aiohttp
import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont
from unidecode import unidecode
from youtubesearchpython.__future__ import VideosSearch

from AnonXMusic import app
from config import YOUTUBE_IMG_URL

CACHE_DIR = "cache"
os.makedirs(CACHE_DIR, exist_ok=True)

def changeImageSize(maxWidth, maxHeight, image):
    widthRatio = maxWidth / image.size[0]
    heightRatio = maxHeight / image.size[1]
    ratio = min(widthRatio, heightRatio)
    newWidth = int(image.size[0] * ratio)
    newHeight = int(image.size[1] * ratio)
    return image.resize((newWidth, newHeight), Image.LANCZOS)

def circle(img):
    size = img.size
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse([(0, 0), size], fill=255)
    img = img.convert("RGBA")
    img.putalpha(mask)
    return img

def clear(text, max_length=60):
    words = text.split()
    title = ""
    for word in words:
        if len(title) + len(word) + 1 <= max_length:
            title += " " + word
    return title.strip()

async def gen_thumb(videoid: str, user_id: int):
    output_file = f"{CACHE_DIR}/{videoid}_{user_id}.png"
    if os.path.isfile(output_file):
        return output_file

    url = f"https://www.youtube.com/watch?v={videoid}"
    try:
        results = VideosSearch(url, limit=1)
        result = (await results.next())["result"][0]

        title = re.sub(r"\W+", " ", result.get("title", "Unsupported Title")).title()
        duration = result.get("duration", "Unknown")
        views = result.get("viewCount", {}).get("short", "Unknown Views")
        channel = result.get("channel", {}).get("name", "Unknown Channel")
        thumbnail_url = result.get("thumbnails", [{}])[0].get("url", YOUTUBE_IMG_URL).split("?")[0]

        # Download YouTube thumbnail
        async with aiohttp.ClientSession() as session:
            async with session.get(thumbnail_url) as resp:
                if resp.status != 200:
                    return YOUTUBE_IMG_URL
                thumb_path = f"{CACHE_DIR}/thumb_{videoid}.png"
                f = await aiofiles.open(thumb_path, "wb")
                await f.write(await resp.read())
                await f.close()

        # Download user profile pic
        try:
            async for photo in app.get_chat_photos(user_id, 1):
                user_photo_path = await app.download_media(photo.file_id, file_name=f"{CACHE_DIR}/{user_id}.png")
                break
            else:
                raise Exception
        except:
            async for photo in app.get_chat_photos(app.id, 1):
                user_photo_path = await app.download_media(photo.file_id, file_name=f"{CACHE_DIR}/bot.png")
                break

        # Open images
        youtube_img = Image.open(thumb_path)
        user_img = Image.open(user_photo_path)

        # Resize & blur background
        bg = changeImageSize(1280, 720, youtube_img).convert("RGBA")
        bg = bg.filter(ImageFilter.BoxBlur(10))
        bg = ImageEnhance.Brightness(bg).enhance(0.5)

        # Paste circular thumbnails
        bg.paste(circle(changeImageSize(200, 200, youtube_img)), (45, 225), mask=circle(changeImageSize(200, 200, youtube_img)))
        bg.paste(circle(changeImageSize(200, 200, user_img)), (1045, 225), mask=circle(changeImageSize(200, 200, user_img)))

        draw = ImageDraw.Draw(bg)
        font_path_bold = "AnonXMusic/assets/font2.ttf"
        font_path_regular = "AnonXMusic/assets/font.ttf"
        arial = ImageFont.truetype(font_path_bold, 30)
        font = ImageFont.truetype(font_path_regular, 30)

        # Draw texts
        draw.text((1110, 8), unidecode(app.name), fill="white", font=arial)
        draw.text((55, 560), f"{channel} | {views[:23]}", fill="white", font=arial)
        draw.text((57, 600), clear(title), fill="white", font=font)
        draw.line([(55, 660), (1220, 660)], fill="white", width=5)
        draw.ellipse([(918, 648), (942, 672)], fill="white")
        draw.text((36, 685), "00:00", fill="white", font=arial)
        draw.text((1185, 685), duration[:23], fill="white", font=arial)

        bg.save(output_file)

        # Cleanup
        try:
            os.remove(thumb_path)
        except:
            pass

        return output_file

    except Exception as e:
        print(f"Error generating thumbnail: {e}")
        return YOUTUBE_IMG_URL