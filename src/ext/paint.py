from typing import Literal, Optional
import discord
from discord.app_commands import describe
from discord.ext import commands
import numpy as np
from wand.image import Image as WandImage
from wand.drawing import Drawing as WandDrawing
from wand.color import Color as WandColor
from io import BytesIO

from ..cls_bot import HuskyContext, Husky, HuskyCog

from ..utils.converters import color_param, ColorConverter
from ..utils.types import Color
from ..utils.formatting import sendoff


class Paint(HuskyCog):
    """Commands for creating images from colors."""

    def __init__(self, bot: Husky):
        super().__init__(bot, emoji="\N{ARTIST PALETTE}")
        self.bot = bot

    @commands.hybrid_group()
    async def paint(
        self,
        ctx: HuskyContext,
        colors: commands.Greedy[ColorConverter] = None,
        direction: Literal["horizontal", "h", "vertical", "v"] = "horizontal",
    ):
        """Base command for the group. If no subcommand is provided, this will default to `paint color`"""
        if ctx.invoked_subcommand is None:
            await ctx.invoke(self.color, colors=colors, direction=direction)

    @paint.command(aliases=["c"])
    async def color(
        self,
        ctx: HuskyContext,
        colors: commands.Greedy[ColorConverter],
        direction: Literal["horizontal", "h", "vertical", "v"] = "horizontal",
    ):
        """
        Creates a solid color image, with the specified color.

        Parameters
        ----------
        colors: list[Color]
            A list of colors to use, separated by spaces. See `hk guide colors` for more info.
        """
        pixels_per_color = 256 // len(colors)
        wimage = WandImage(width=256, height=256)
        d = WandDrawing()

        direction = (
            {"h": "horizontal", "v": "vertical"}.get(direction, direction).lower()
        )

        if direction == "horizontal":
            for i, color in enumerate(colors):
                d.fill_color = WandColor(color.to_hex())
                d.rectangle(
                    left=i * pixels_per_color,
                    top=0,
                    right=(i + 1) * pixels_per_color,
                    bottom=256,
                )

            if 256 % pixels_per_color != 0:
                d.fill_color = WandColor(colors[-1].to_hex())
                d.rectangle(
                    left=256 - 256 % pixels_per_color, top=0, right=256, bottom=256
                )

        elif direction == "vertical":
            for i, color in enumerate(colors):
                d.fill_color = WandColor(color.to_hex())
                d.rectangle(
                    left=0,
                    top=i * pixels_per_color,
                    right=256,
                    bottom=(i + 1) * pixels_per_color,
                )

            if 256 % pixels_per_color != 0:
                d.fill_color = WandColor(colors[-1].to_hex())
                d.rectangle(
                    left=0, top=256 - 256 % pixels_per_color, right=256, bottom=256
                )

        d.draw(wimage)

        await sendoff(ctx, wimage, str(colors))

    @paint.command(aliases=["grad", "g"])
    async def gradient(
        self,
        ctx: HuskyContext,
        colors: commands.Greedy[ColorConverter],
        direction: Literal["horizontal", "h", "vertical", "v"] = "horizontal",
    ):
        """
        Creates a gradient image, with the specified colors.

        Parameters
        ----------
        mode: Literal["horizontal", "h", "vertical", "v"]
            The direction of the gradient. "horizontal" or "h" for horizontal, "vertical" or "v" for vertical.

        colors: list[Color]
            A list of colors to use, separated by spaces. See `hk guide colors` for more info.
        """
        if len(colors) < 2:
            raise commands.BadArgument("A gradient needs at least 2 colors.")

        GRANULARITY = 1  # how many columns each color should have. 1 meaning every column of color is slightly different.
        wimage = WandImage(width=256, height=256)
        d = WandDrawing()

        spacing = 256 // (len(colors) - 1)
        if direction in ("horizontal", "h"):
            for slot in range(0, 256, spacing):
                if slot + spacing > 256:
                    break
                left = slot
                right = slot + spacing

                space_index = slot // spacing

                left_color = colors[space_index]
                right_color = colors[space_index + 1]

                for i in range(left, right, GRANULARITY):
                    # interpolate the color between the left and right colors, evenly spread across the space between them (hence numpy.interp)
                    # numpy my beloved
                    color = Color.from_rgb(
                        np.interp(i, [left, right], [left_color.red, right_color.red]),
                        np.interp(
                            i, [left, right], [left_color.green, right_color.green]
                        ),
                        np.interp(
                            i, [left, right], [left_color.blue, right_color.blue]
                        ),
                    )
                    d.fill_color = WandColor(color.to_hex())
                    d.rectangle(left=i, top=0, right=i + GRANULARITY, bottom=256)

        elif direction in ("vertical", "v"):
            for slot in range(0, 256, spacing):
                if slot + spacing > 256:
                    break
                top = slot
                bottom = slot + spacing

                space_index = slot // spacing

                top_color = colors[space_index]
                bottom_color = colors[space_index + 1]

                for i in range(top, bottom, GRANULARITY):
                    color = Color.from_rgb(
                        np.interp(i, [top, bottom], [top_color.red, bottom_color.red]),
                        np.interp(
                            i, [top, bottom], [top_color.green, bottom_color.green]
                        ),
                        np.interp(
                            i, [top, bottom], [top_color.blue, bottom_color.blue]
                        ),
                    )
                    d.fill_color = WandColor(color.to_hex())
                    d.rectangle(left=0, top=i, right=256, bottom=i + GRANULARITY)
        else:
            raise commands.BadArgument("Invalid mode.")

        if 256 % GRANULARITY != 0:
            d.fill_color = WandColor(colors[-1].to_hex())
            if direction in ("horizontal", "h"):
                d.rectangle(left=256 - 256 % GRANULARITY, top=0, right=256, bottom=256)
            elif direction in ("vertical", "v"):
                d.rectangle(left=0, top=256 - 256 % GRANULARITY, right=256, bottom=256)

        d.draw(wimage)

        await sendoff(ctx, wimage, str(colors))


async def setup(bot: Husky):
    await bot.add_cog(Paint(bot))
