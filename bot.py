"""
Helloow :3 
please make sure u have those libraries
pip install discord.py Pillow aiohttp
"""

import io
import logging
import os
import random
import aiohttp
import discord
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont, ImageOps

# Cnfg 

BOT_TOKEN = os.getenv("BOT_TOKEN", "PUT YOUR TOKEN HEEEERRE")
COMMAND_PREFIX = "."

SCALE = 3
CARD_WIDTH = 600
CARD_BG = (10, 10, 10)
TEXT_WHITE = (240, 240, 240)
TEXT_GRAY = (130, 130, 130)
STATS_GRAY = (120, 120, 120)
LINE_GRAY = (40, 40, 40)

# Maximum size (in pixels) 

MAX_IMAGE_PIXELS = 4096 * 4096


_HERE = os.path.dirname(os.path.abspath(__file__))

_BOLD_CANDIDATES = [
    os.path.join(_HERE, "font-bold.ttf"),
    # for Linux
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/google-noto/NotoSans-Bold.ttf",
    "/usr/share/fonts/google-droid-sans-fonts/DroidSans-Bold.ttf",
    # for macos
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    # and for Windows
    "C:\\Windows\\Fonts\\arialbd.ttf",
]
_REGULAR_CANDIDATES = [
    os.path.join(_HERE, "font-regular.ttf"),
    # 4Linux
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/google-droid-sans-fonts/DroidSans.ttf",
    "/usr/share/fonts/adwaita-sans-fonts/AdwaitaSans-Regular.ttf",
    # 4macOS
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    # 4Windows
    "C:\\Windows\\Fonts\\arial.ttf",
]


def _load_font(candidates, size):
    for path in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                continue
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


FONT_NAME = _load_font(_BOLD_CANDIDATES, 20 * SCALE)
FONT_HANDLE = _load_font(_REGULAR_CANDIDATES, 17 * SCALE)
FONT_BODY = _load_font(_REGULAR_CANDIDATES, 19 * SCALE)
FONT_STATS = _load_font(_REGULAR_CANDIDATES, 15 * SCALE)

log = logging.getLogger(__name__)


# Bot set up

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix=COMMAND_PREFIX, intents=intents)






async def fetch_image(session, url):
    try:
        async with session.get(url) as response:
            if response.status != 200:
                return None
            data = await response.read()
            img = Image.open(io.BytesIO(data))
            if img.width * img.height > MAX_IMAGE_PIXELS:
                img.thumbnail(
                    (4096, 4096), Image.Resampling.LANCZOS
                )
            return img.convert("RGBA")
    except Exception:
        return None


def crop_circle(im, size=(56, 56)): # crop it into circle
    im = ImageOps.fit(im, size, Image.Resampling.LANCZOS, centering=(0.5, 0.5))
    mask = Image.new("L", size, 0)
    ImageDraw.Draw(mask).ellipse((0, 0, size[0] - 1, size[1] - 1), fill=255)
    im.putalpha(mask)
    return im


def rounded_image(im, size, radius=16):
    """Resize/crop an image to fill `size` and round its corners."""
    im = ImageOps.fit(im, size, Image.Resampling.LANCZOS, centering=(0.5, 0.5))
    mask = Image.new("L", size, 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        [0, 0, size[0] - 1, size[1] - 1], radius=radius, fill=255
    )
    im.putalpha(mask)
    return im


def _font_line_height(font):
   
    if hasattr(font, "size") and font.size > 12:
        return font.size
    dummy = Image.new("RGB", (1, 1))
    d = ImageDraw.Draw(dummy)
    bbox = d.textbbox((0, 0), "Ayg|", font=font)
    return bbox[3] - bbox[1]


def wrap_text(draw, text, font, max_width):
    lines = []
    for raw_line in text.split("\n"):
        if raw_line == "":
            lines.append("")
            continue
        words = raw_line.split(" ")
        current = ""
        for word in words:
            trial = (current + " " + word).strip()
            if draw.textlength(trial, font=font) <= max_width:
                current = trial
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)
    return lines





def draw_reply_icon(draw, x, y, size=16, color=STATS_GRAY): # reply 
    draw.rounded_rectangle(
        [x, y, x + size, y + size * 0.75],
        radius=max(1, round(4 * SCALE)),
        outline=color,
        width=max(1, round(2 * SCALE)),
    )
    tail = [
        (x + size * 0.25, y + size * 0.75),
        (x + size * 0.15, y + size),
        (x + size * 0.5, y + size * 0.75),
    ]
    draw.polygon(tail, fill=color)


def draw_heart_icon(draw, x, y, size=16, color=STATS_GRAY): # hearth
    r = size / 4
    draw.ellipse([x, y, x + 2 * r, y + 2 * r], fill=color)
    draw.ellipse([x + 2 * r, y, x + 4 * r, y + 2 * r], fill=color)
    draw.polygon(
        [(x, y + r), (x + 4 * r, y + r), (x + 2 * r, y + size)],
        fill=color,
    )


def draw_views_icon(draw, x, y, size=16, color=STATS_GRAY): # views
    bar_w = size / 4
    gap = max(2, round(2 * SCALE))
    heights = [size * 0.4, size * 0.7, size]
    for i, h in enumerate(heights):
        bx = x + i * (bar_w + gap)
        draw.rectangle([bx, y + size - h, bx + bar_w, y + size], fill=color)


# Card generate



async def generate_card(
    author_name, handle, text, avatar_img, attach_img=None, server_icon_img=None
):
    S = SCALE
    pad = 22 * S
    avatar_size = 44 * S
    render_width = CARD_WIDTH * S

    content_left = pad + avatar_size + 14 * S

    dummy = Image.new("RGB", (10, 10))
    dummy_draw = ImageDraw.Draw(dummy)

    body_lh = _font_line_height(FONT_BODY) + 8 * S
    name_lh = _font_line_height(FONT_NAME)

    header_h = avatar_size
    y = pad + header_h + 14 * S

    # Body text wrapping
    body_lines = []
    if text:
        body_lines = wrap_text(dummy_draw, text, FONT_BODY, render_width - 2 * pad)
        body_h = body_lh * len(body_lines)
    else:
        body_h = 0

    # Attachment sizing
    attach_target = None
    attach_h = 0
    if attach_img is not None and attach_img.width > 0:
        target_w = render_width - 2 * pad
        target_h = min(
            int(attach_img.height * (target_w / attach_img.width)), 380 * S
        )
        if target_h < 1:
            target_h = 1
        attach_target = (target_w, target_h)
        attach_h = target_h + 14 * S

    stats_h = 34 * S
    height = y + body_h + attach_h + 14 * S + stats_h + pad

    # --- Create card canvas ---
    card = Image.new("RGBA", (render_width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(card)
    draw.rounded_rectangle(
        [0, 0, render_width - 1, height - 1], radius=22 * S, fill=CARD_BG
    )

    # Avatar
    if avatar_img:
        avatar = crop_circle(avatar_img, (avatar_size, avatar_size))
        card.paste(avatar, (pad, pad), avatar)

    # Name / handle
    draw.text(
        (content_left, pad - 2 * S), author_name, font=FONT_NAME, fill=TEXT_WHITE
    )
    draw.text(
        (content_left, pad - 2 * S + name_lh + 4 * S),
        f"@{handle}",
        font=FONT_HANDLE,
        fill=TEXT_GRAY,
    )

    # Server icon or clover badge, top-right
    if server_icon_img:
        icon_sz = 24 * S
        srv_icon = crop_circle(server_icon_img, (icon_sz, icon_sz))
        card.paste(srv_icon, (render_width - pad - icon_sz, pad), srv_icon)
   

    cy = y # body
    if body_lines:
        for line in body_lines:
            draw.text((pad, cy), line, font=FONT_BODY, fill=TEXT_WHITE)
            cy += body_lh
        cy += 6 * S

    # Attachment
    if attach_img is not None and attach_target is not None:
        fitted = rounded_image(attach_img, attach_target, radius=16 * S)
        card.paste(fitted, (pad, cy), fitted)
        cy += attach_target[1] + 14 * S

    # Divider
    draw.line(
        [pad, cy, render_width - pad, cy],
        fill=LINE_GRAY,
        width=max(1, S),
    )
    cy += 12 * S

    # Stats row
    replies = random.randint(120, 400)
    likes = random.randint(1500, 4000)
    views = random.randint(5000, 9999)

    icon_y = cy + 2 * S
    x = pad

    draw_reply_icon(draw, x, icon_y, size=15 * S)
    x += 22 * S
    replies_txt = f"{replies:,} Replies"
    draw.text((x, cy), replies_txt, font=FONT_STATS, fill=STATS_GRAY)
    x += int(draw.textlength(replies_txt, font=FONT_STATS)) + 26 * S

    draw_heart_icon(draw, x, icon_y, size=15 * S)
    x += 22 * S
    likes_txt = f"{likes:,} Likes"
    draw.text((x, cy), likes_txt, font=FONT_STATS, fill=STATS_GRAY)
    x += int(draw.textlength(likes_txt, font=FONT_STATS)) + 26 * S

    draw_views_icon(draw, x, icon_y, size=15 * S)
    x += 22 * S
    views_txt = f"{views:,} Views"
    draw.text((x, cy), views_txt, font=FONT_STATS, fill=STATS_GRAY)

    final_w = CARD_WIDTH
    final_h = round(height / S)
    final_card = card.resize((final_w, final_h), Image.Resampling.LANCZOS)

    buffer = io.BytesIO()
    final_card.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer


# Cmd


@bot.command(name="threadit")
async def threadit(ctx):
    if ctx.message.reference:
        try:
            target_msg = await ctx.channel.fetch_message(
                ctx.message.reference.message_id
            )
        except (discord.NotFound, discord.HTTPException):
            await ctx.send("Could not fetch the replied message.", delete_after=5)
            return
        text = target_msg.content
    else:
        target_msg = ctx.message
        prefix_len = len(ctx.prefix) + len(ctx.invoked_with)
        text = ctx.message.content[prefix_len:].strip()

    author = target_msg.author

    # Find the first image attachment, if any
    attach_url = None
    for attachment in target_msg.attachments:
        if attachment.content_type and attachment.content_type.startswith("image/"):
            attach_url = attachment.url
            break

    async with aiohttp.ClientSession() as session:
        avatar_img = await fetch_image(session, author.display_avatar.url)
        attach_img = (
            await fetch_image(session, attach_url) if attach_url else None
        )

        server_icon_img = None
        if ctx.guild and ctx.guild.icon:
            server_icon_img = await fetch_image(session, ctx.guild.icon.url)

        card_bytes = await generate_card(
            author_name=author.display_name,
            handle=author.name,
            text=text,
            avatar_img=avatar_img,
            attach_img=attach_img,
            server_icon_img=server_icon_img,
        )

    file = discord.File(card_bytes, filename="thread_card.png")

    embed = discord.Embed(
        description=f"**New Thread By :** {author.mention}",
        color=discord.Color.from_rgb(30, 30, 35),
    )
    embed.set_image(url="attachment://thread_card.png")

    if ctx.guild:
        guild_icon = ctx.guild.icon.url if ctx.guild.icon else None
        embed.set_footer(
            text=f"{ctx.guild.name} • feed", icon_url=guild_icon
        )

    await ctx.send(embed=embed, file=file)

    try:
        await ctx.message.delete()
    except (discord.Forbidden, discord.HTTPException):
        pass

# Error handler


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    log.exception("Unhandled command error in %s", ctx.command, exc_info=error)

if __name__ == "__main__":
    if not BOT_TOKEN:
        raise SystemExit("ERROR: No bot token found. Set the BOT_TOKEN environment variable.")
    bot.run(BOT_TOKEN)