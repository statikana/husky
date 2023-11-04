import datetime
from functools import reduce
import time
from typing import Annotated, Any, Optional
import discord
from discord.ext import commands
from urllib.parse import quote_plus

from ..cls_bot import Husky, HuskyContext
from .types import Color
from .errors import InvalidMediaFormat, InvalidMediaSize
import re

from wand.image import Image as WandImage


class HuskyConverter(commands.Converter):
    def __init_subclass__(cls, anno: str) -> None:
        cls.__hk_annotation__ = anno
        return super().__init_subclass__()


class URLSafeConverter(HuskyConverter, anno="URL"):
    async def convert(self, ctx: "HuskyContext", argument: str):
        return quote_plus(argument)


class ColorConverter(HuskyConverter, anno="RGB[A]/Hex/Named Color"):
    def __init__(self, multiple: bool = False) -> None:
        self.multiple = multiple

    def convert_rgb(argument: str) -> Color | None:
        for c in [".", " ", ","]:
            match len(argument.split(c)):
                case 3:
                    r, g, b = argument.split(c)
                    return Color.from_rgb(r, g, b)
                case 4:
                    r, g, b, a = argument.split(c)
                    return Color.from_rgba(r, g, b, a)
                case _:
                    continue
        return None

    def convert_hex(argument: str) -> Color | None:
        argument = argument.strip("#")
        if all(c in "0123456789abcdef" for c in argument.lower()) and len(argument) in [
            6,
            8,
        ]:
            return Color.from_hex(argument)
        return None

    def convert_named(argument: str) -> Color | None:
        # if the argument matches the name of a function in discord.Color which returns a color, use that function to create the color
        attr = argument.lower()
        if hasattr(discord.Color, attr):
            if isinstance(color := getattr(discord.Color, attr)(), discord.Color):
                return Color(*color.to_rgb())
        return {
            "black": Color.from_rgb(0, 0, 0),
            "white": Color.from_rgb(255, 255, 255),
        }.get(attr, None)

    async def convert(self, ctx: HuskyContext, argument: str) -> list[Color] | Color:
        if self.multiple:
            parts = argument.split()
            colors = []
            for a in parts:
                if color := ColorConverter.convert_rgb(a):
                    colors.append(color)
                if color := ColorConverter.convert_hex(a):
                    colors.append(color)
                if color := ColorConverter.convert_named(a):
                    colors.append(color)
            if colors:
                return colors
        else:
            if color := ColorConverter.convert_rgb(argument):
                return color
            if color := ColorConverter.convert_hex(argument):
                return color
            if color := ColorConverter.convert_named(argument):
                return color
        raise TypeError(f"Could not convert {argument} to a color.")


async def convert_date(ctx: HuskyContext, argument: str) -> datetime.date:
    r: datetime.datetime | None = None
    argument = argument.strip().lower()
    date_formats = [
        "%d-%m-%Y",
        "%d/%m/%Y",
        "%d-%m-%y",
        "%d/%m/%y",
        "%d.%m.%Y",
        "%d.%m.%y",
        "%m-%d-%Y",
        "%m/%d/%Y",
        "%m-%d-%y",
        "%m/%d/%y",
        "%m.%d.%Y",
        "%m.%d.%y",
    ]
    for fmt in date_formats:
        try:
            date = datetime.datetime.strptime(argument, fmt)
            r = date
            break
        except ValueError:
            continue

    unit = {
        86400: ["d", "day", "days"],
        604800: ["w", "wk", "wks", "week", "weeks"],
        2592000: ["mo", "mos", "month", "months"],
        31536000: ["y", "yr", "yrs", "year", "years"],
    }
    # first, regex to see if it's actually in the right format
    regex = re.compile(
        # r"(?:\d+(?:\.\d+)?(?:s|sec|second|seconds|minute|minutes|h|hour|hours|d|day|days|w|week|weeks|m|mo|mon|month|months|y|year|years))",
        r"(?:\d+(?:\.\d+)?(?:d|day|days|w|week|weeks|m|mo|mon|month|months|y|year|years))",
        flags=re.IGNORECASE | re.MULTILINE,
    )  # god bless regex101.com
    matches = regex.findall(argument)
    if matches:
        total_seconds = 0
        for match in matches:
            for seconds, units in unit.items():
                for u in units:
                    if match.endswith(u):
                        total_seconds += seconds * float(match[: -len(u)])
                        break
        r = datetime.datetime.fromtimestamp(time.time() + total_seconds)

    # # maybe it's a time like 23:59:59
    # regex = re.compile(
    #     r"^(?:[0-23]{1,2}:[0-59]{2}(?::[0-59]{2})?)$",
    #     flags=re.IGNORECASE|re.MULTILINE
    # )
    # matches = regex.findall(argument)
    # if len(matches) == 1:
    #     return datetime.datetime.strptime(matches[0], "%H:%M:%S")
    # elif len(matches) > 1:
    #     raise ValueError("Too many times found in input")

    # Jan 23nd
    regex = re.compile(
        r"^(Jan|Janurary|Feb|Feburary|Mar|March|Apr|April|May|Jun|June|Jul|July|Aug|August|Sep|Sept|September|Oct|October|Nov|November|Dec|December) ?([0?[1-3][0-9])(?:st|th|rd)?$",
        flags=re.IGNORECASE | re.MULTILINE,
    )
    matches = regex.findall(argument)
    if matches:
        # group 1 is month
        # group 2 is day
        month = matches[0][0]
        day = matches[0][1]
        try:
            r = datetime.datetime.strptime(f"{month} {day}", "%B %d")
        except ValueError:
            r = datetime.datetime.strptime(f"{month} {day}", "%b %d")

    if argument == "tomorrow":
        r = datetime.datetime.now() + datetime.timedelta(days=1)
    elif argument == "today":
        r = datetime.datetime.now()
    elif argument in ["next week", "in a week", "in 1 week", "in one week"]:
        r = datetime.datetime.now() + datetime.timedelta(days=7)
    elif argument in ["in a month", "in 1 month", "in one month", "next month"]:
        r = datetime.datetime.now() + datetime.timedelta(days=30)
    elif argument in ["in a year", "in 1 year", "in one year", "next year"]:
        r = datetime.datetime.now() + datetime.timedelta(days=365)

    if r is not None:
        return r.date()
    raise ValueError("Could not convert input to a date")


async def convert_time(ctx: HuskyContext, argument: str) -> datetime.time:
    argument = argument.strip().lower()
    r = None
    # argument = reduce(lambda a, kv: a.replace(kv), ["am", "a.m.", "pm", "p.m.", "oclock", "o'clock"], argument).strip()
    time_formats = [
        "%I:%M%p",
        "%I:%M %p",
        "%I%p",
        "%I %p",
        "%I:%H",
        "%I %H",
        "%I",
        "%H:%M:%S",
        "%H:%M",
        "%H",
        # add seconds after each minute
        "%I:%M:%S%p",
        "%I:%M:%S %p",
        "%H:%M:%S",
    ]
    for fmt in time_formats:
        try:
            dt = datetime.datetime.strptime(argument, fmt)
            if dt.time() < datetime.datetime.now().time():
                if dt.time().hour < 12:
                    dt += datetime.timedelta(hours=12)
            return dt.time()
        except ValueError:
            continue

    unit = {
        60: ["s", "sec", "second", "seconds"],
        3600: ["m", "min", "minute", "minutes"],
        86400: ["h", "hr", "hour", "hours"],
    }

    # first, regex to see if it's actually in the right format
    regex = re.compile(
        r"(\d+)(?:s|sec|second|seconds|m|min|minute|minutes|h|hr|hour|hours)",
        flags=re.IGNORECASE | re.MULTILINE,
    )
    matches = regex.findall(argument)
    if matches:
        sec = 0
        for m in matches:
            b = m.group(0)
            u = m.group(1)
            sec += int(b) * unit[u]
        r = datetime.datetime.now() + datetime.timedelta(seconds=sec)
        return r.time()

    if argument in ["noon", "midday"]:
        return datetime.time(hour=12)
    elif argument in ["midnight"]:
        return datetime.time(hour=0)
    elif argument in ["now"]:
        return datetime.datetime.now().time()
    elif argument in ["next hour", "in an hour", "in 1 hour", "in one hour"]:
        r = datetime.datetime.now() + datetime.timedelta(hours=1)
    elif argument in ["next minute", "in a minute", "in 1 minute", "in one minute"]:
        r = datetime.datetime.now() + datetime.timedelta(minutes=1)
    elif argument in ["next second", "in a second", "in 1 second", "in one second"]:
        r = datetime.datetime.now() + datetime.timedelta(seconds=1)

    if r is not None:
        return r.time()
    raise ValueError("Could not convert input to a time")


VALID_IMAGE_FORMATS = ["png", "jpg", "jpeg"]
VALID_VIDEO_FORMATS = ["mp4"]
MAX_IMAGE_SIZE_BYTES = 8_388_608  # 8 MB
MAX_VIDEO_SIZE_BYTES = 16_777_216  # 16 MB


async def convert_image(attachment: discord.Attachment) -> WandImage:
    if attachment.size > MAX_IMAGE_SIZE_BYTES:
        raise InvalidMediaSize("Image is too large.")
    if (dot := attachment.filename.rfind(".")) != -1:
        if attachment.filename[dot + 1 :].lower() in VALID_IMAGE_FORMATS:
            data = await attachment.read()
            try:
                return WandImage(blob=data)
            except Exception as e:
                raise InvalidMediaFormat(
                    f"Could not convert image (most likely format mismatch): {e}"
                )
        raise InvalidMediaFormat(
            f"Image must be one of the following formats: {'/'.join(VALID_IMAGE_FORMATS)}"
        )
    raise InvalidMediaFormat("Image must have a file extension, such as .png or .jpg")


async def convert_video(attachment: discord.Attachment) -> bytes:
    if attachment.size > MAX_VIDEO_SIZE_BYTES:
        raise InvalidMediaSize("Video is too large.")
    if (dot := attachment.filename.rfind(".")) != -1:
        if attachment.filename[dot + 1 :].lower() in VALID_VIDEO_FORMATS:
            return await attachment.read()
        raise InvalidMediaFormat(
            f"Video must be one of the following formats: {'/'.join(VALID_VIDEO_FORMATS)}"
        )
    raise InvalidMediaFormat("Video must have a file extension, such as .mp4")


async def get_last_message_content(
    ctx: HuskyContext, default: Optional[Any] = None
) -> str | None:
    async for message in ctx.channel.history(limit=3):
        if message.id != ctx.message.id and message.author != ctx.bot.user:
            return message.content or "<No Content>"

    return default


# Reminder: params are set as the default value of the command's signature, the type hint would be the converter. Since the
# converter is wrapped into the parameter, the typehint can be used for any type the argument may be converted to.
URL_safe_param = commands.param(converter=URLSafeConverter(), displayed_name="query")
optional_URL_safe_param = commands.param(
    converter=URLSafeConverter(),
    displayed_name="query",
    default=get_last_message_content,
    displayed_default="Last Channel Message",
)

color_param = commands.param(
    converter=ColorConverter(multiple=False), displayed_name="RGB[A]/HEX/Named Color"
)
multiple_color_param = commands.param(
    converter=ColorConverter(multiple=True), displayed_name="RGB[A]/HEX/Named Colors"
)
optional_color_param = commands.param(
    converter=ColorConverter(),
    displayed_name="RGB[A]/HEX/Named Color",
    default=Color.from_hex("#00000000"),
    displayed_default="#00000000",
)
multiple_optional_color_param = commands.param(
    converter=ColorConverter(multiple=True),
    displayed_name="RGB[A]/HEX/Named Colors",
    default=[],
    displayed_default="No Colors",
)
