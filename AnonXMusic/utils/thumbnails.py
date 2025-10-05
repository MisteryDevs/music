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


def changeImageSize(maxWidth, maxHeight, image):
    widthRatio = maxWidth / image.size[0]
    heightRatio = maxHeight / image.size[1]
    newWidth = int(widthRatio * image.size[0])
    newHeight = int(heightRatio * image.size[1])
    newImage = image.resize((newWidth, newHeight))
    return newImage


def clear(text):
    list = text.split(" ")
    title = ""
    for i in list:
        if len(title) + len(i) < 60:
            title += " " + i
    return title.strip()


async def get_thumb(videoid, user_id):
    if os.path.isfile(f"cache/{videoid}_{user_id}.png"):
        return f"cache/{videoid}_{user_id}.png"

    url = f"https://www.youtube.com/watch?v={videoid}"
    try:
        results = VideosSearch(url, limit=1)
        for result in (await results.next())["result"]:
            try:
                title = result["title"]
                title = re.sub("\W+", " ", title).title()
            except:
                title = "Unsupported Title"
            try:
                duration = result["duration"]
            except:
                duration = "Unknown Mins"
            thumbnail = result["thumbnails"][0]["url"].split("?")[0]
            try:
                views = result["viewCount"]["short"]
            except:
                views = "Unknown Views"
            try:
                channel = result["channel"]["name"]
            except:
                channel = "Unknown Channel"

        # Download thumbnail
        async with aiohttp.ClientSession() as session:
            async with session.get(thumbnail) as resp:
                if resp.status == 200:
                    f = await aiofiles.open(f"cache/thumb{videoid}.png", mode="wb")
                    await f.write(await resp.read())
                    await f.close()

        youtube = Image.open(f"cache/thumb{videoid}.png")
        image1 = changeImageSize(1280, 720, youtube)
        image2 = image1.convert("RGBA")
        background = image2.filter(filter=ImageFilter.BoxBlur(10))
        enhancer = ImageEnhance.Brightness(background)
        background = enhancer.enhance(0.5)

        # Rounded square thumbnail (left side)
        thumb = changeImageSize(350, 350, youtube)
        mask = Image.new("L", thumb.size, 0)
        draw_mask = ImageDraw.Draw(mask)
        draw_mask.rounded_rectangle([0, 0, thumb.size[0], thumb.size[1]], 50, fill=255)
        thumb.putalpha(mask)
        background.paste(thumb, (100, 180), mask=thumb)

        draw = ImageDraw.Draw(background)
        font = ImageFont.truetype("AnonXMusic/assets/font.ttf", 32)
        arial = ImageFont.truetype("AnonXMusic/assets/font2.ttf", 28)

        # Horizontal white thick line (with left-right margins)
        margin_x = 80
        line_y = 400
        draw.line(
            [(margin_x, line_y), (1280 - margin_x, line_y)],
            fill="white",
            width=18
        )

        # Play icon (right side)
        play_x, play_y = 950, 280
        play_size = 120
        draw.polygon(
            [(play_x, play_y), (play_x, play_y + play_size), (play_x + play_size, play_y + play_size // 2)],
            fill="white"
        )

        # Play/Stop button under thumbnail
        btn_x, btn_y = 180, 560
        btn_w, btn_h = 120, 55
        draw.rounded_rectangle([btn_x, btn_y, btn_x + btn_w, btn_y + btn_h], 15, outline="white", width=4)
        draw.text((btn_x + 30, btn_y + 10), "▶️", fill="white", font=arial)

        # Text info (right side)
        draw.text((600, 180), f"{channel} | {views[:20]}", (255, 255, 255), font=arial)
        draw.text((600, 240), clear(title), (255, 255, 255), font=font)
        draw.text((600, 310), f"Duration: {duration}", (255, 255, 255), font=arial)

        try:
            os.remove(f"cache/thumb{videoid}.png")
        except:
            pass

        background.save(f"cache/{videoid}_{user_id}.png")
        return f"cache/{videoid}_{user_id}.png"
    except Exception:
        return YOUTUBE_IMG_URL