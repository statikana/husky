import discord
from typing import Any
from wand.image import Image as WandImage

from io import BytesIO
from ..cls_bot import HuskyContext

from fuzzywuzzy import fuzz


def fmt_data(d: list[tuple[str, str]]) -> str:
    return "\n".join(f"**{k}:** `{v}`" for k, v in d)


async def sendoff(ctx: HuskyContext, image: WandImage, title: str = None):
    image.format = "png"
    image_buffer = BytesIO()
    image.save(file=image_buffer)
    image_buffer.seek(0)
    file = discord.File(image_buffer, filename="image.png")
    embed = ctx.embed(title=title)
    embed.set_image(url="attachment://image.png")
    await ctx.send(embed=embed, file=file)


def fuzzy(source: str, match: str) -> float:
    return float(fuzz.ratio(source, match)) / 100
