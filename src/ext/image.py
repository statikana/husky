import logging
from typing import Literal, Optional
import typing
import discord
from discord.ext import commands
from discord.app_commands import Range

from wand.image import Image as WandImage
from wand.drawing import Drawing as WandDrawing
from wand.color import Color as WandColor

from ..cls_bot import HuskyContext, Husky, HuskyCog
from ..utils.converters import convert_image, optional_color_param, Color
from ..utils.formatting import sendoff


class Image(HuskyCog):
    """Commands for manipulating images."""

    def __init__(self, bot: Husky):
        super().__init__(bot, emoji="\N{FRAME WITH PICTURE}")
        self.bot = bot

    @commands.hybrid_group(aliases=["i", "img"])
    async def image(self, ctx: HuskyContext):
        """Base class for other img commands."""
        pass

    @image.command(aliases=["r", "rot"])
    async def rotate(
        self,
        ctx: HuskyContext,
        image: discord.Attachment,
        degrees: float,
        background: Color = optional_color_param,
    ):
        """
        Rotates an image by the specified degrees.

        Parameters
        ----------
        image: discord.Attachment
            The image to rotate.

        degrees: float
            The number of degrees to rotate the image by.

        background: Color, optional
            The color to use for the background.
        """
        wimage = await convert_image(image)
        wimage.rotate(
            degrees,
            background=WandColor(background.to_hex()),
        )
        await sendoff(ctx, wimage, f"Rotated {degrees} degrees")

    @image.command(aliases=["flop", "flip"])
    async def mirror(
        self,
        ctx: HuskyContext,
        image: discord.Attachment,
        direction: Literal["horizontal", "h", "vertical", "v"] = "horizontal",
    ):
        """
        Mirrors an image horizontally or vertically.

        Parameters
        ----------
        image: discord.Attachment
            The image to mirror.

        direction: Literal["horizontal", "h", "vertical", "v"]
            The direction to mirror the image in. `h` for horizontal, `v` for vertical.
        """
        wimage = await convert_image(image)
        direction = (
            {"h": "horizontal", "v": "vertical"}.get(direction, direction).lower()
        )
        if direction == "horizontal":
            wimage.flop()
        elif direction == "vertical":
            wimage.flip()

        await sendoff(ctx, wimage, f"Mirrored {direction}")

    @image.command(aliases=["resize"])
    async def rescale(
        self,
        ctx: HuskyContext,
        image: discord.Attachment,
        width: Optional[int],
        height: Optional[int],
        maintain_aspect_ratio: bool = True,
    ):
        """
        Rescales an image to the specified width and height.

        Parameters
        ----------
        image: discord.Attachment
            The image to rescale.

        width: Optional[int]
            The width to rescale the image to.

        height: Optional[int]
            The height to rescale the image to.

        maintain_aspect_ratio: bool
            Whether or not to maintain the aspect ratio of the image if only one of `width` or `height` is provided.
        """
        MAX_RESCALE_PIXELS = 4_194_304  # 2048x2048

        wimage = await convert_image(image)
        original_width, original_height = wimage.width, wimage.height

        if width is None and height is None:
            raise commands.BadArgument(
                "You must provide at least one of `width` or `height`"
            )

        if width is None and height is not None:
            if maintain_aspect_ratio:
                width = int(
                    wimage.width * (height / wimage.height)
                )  # get the scale ratio of old -> new and multiply it by the old value
            else:
                width = original_width

        if height is None and width is not None:
            if maintain_aspect_ratio:
                height = int(wimage.height * (width / wimage.width))
            else:
                height = original_height

        if width * height > MAX_RESCALE_PIXELS:
            raise commands.BadArgument(
                f"Image is too large to rescale. Maximum is {MAX_RESCALE_PIXELS} pixels."
            )

        wimage.resize(width, height)
        await sendoff(
            ctx,
            wimage,
            f"Rescaled from `{original_width}x{original_height}` to `{width}x{height}`",
        )

    @image.command(aliases=["cut"])
    async def crop(
        self,
        ctx: HuskyContext,
        image: discord.Attachment,
        start_x: int,
        start_y: int,
        width: Optional[int],
        height: Optional[int],
        end_x: Optional[int],
        end_y: Optional[int],
    ):
        """
        Crops an image to the specified dimensions, given a starting point and width/height.

        Parameters
        ----------
        image: discord.Attachment
            The image to crop.

        start_x: int
            The starting x coordinate of the crop, starting from the left.

        start_y: int
            The starting y coordinate of the crop, starting from the top.

        width: Optional[int]
            The width of the new image. Either this OR `end_x` must be provided.

        height: Optional[int]
            The height of the new image. Either this OR `end_y` must be provided.

        end_x: Optional[int]
            The ending x coordinate of the crop, starting from the left. Either this OR `width` must be provided.

        end_y: Optional[int]
            The ending y coordinate of the crop, starting from the top. Either this OR `height` must be provided.
        """
        original_width, original_height = wimage.width, wimage.height
        wimage = await convert_image(image)
        if width and end_x:
            raise commands.BadArgument("You cannot provide both `width` and `end_x`.")
        if width is None and end_x is None:
            raise commands.BadArgument("You must provide either `width` or `end_x`.")
        if height and end_y:
            raise commands.BadArgument("You cannot provide both `height` and `end_y`.")
        if height is None and end_y is None:
            raise commands.BadArgument("You must provide either `height` or `end_y`.")

        # no need to calculate the other bits, because wand will do it for us
        wimage.crop(start_x, start_y, end_x, end_y, width, height)

        await sendoff(
            ctx,
            wimage,
            f"Cropped from `{original_width}x{original_height}` to `{wimage.width}x{wimage.height}` at `({start_x}, {start_y})`",
        )

    @image.command(aliases=["b"])
    async def border(
        self,
        ctx: HuskyContext,
        image: discord.Attachment,
        color: Color = optional_color_param,
        width: int = 16,
        height: int = 16,
    ):
        """
        Adds a border to an image.

        Parameters
        ----------
        image: discord.Attachment
            The image to add a border to.

        color: Color, optional
            The color to use for the border.

        width: int
            The width of the border.
        """
        wimage = await convert_image(image)
        wimage.border(WandColor(color.to_hex()), width=width, height=height)
        await sendoff(ctx, wimage, f"Added a `{width}x{height} px` `{color}` border")

    @image.command()
    async def blur(
        self,
        ctx: HuskyContext,
        image: discord.Attachment,
        sigma: Range[float, 0, 50],
    ):
        """
        Blurs an image.

        Parameters
        ----------
        image: discord.Attachment
            The image to blur.

        sigma: float
            The sigma value to use for the blur. The higher it is, the more blurred the image will be.
        """
        wimage = await convert_image(image)
        wimage.blur(sigma=sigma)
        await sendoff(ctx, wimage, "Blurred image")

    @image.command(aliases=["shrp"])
    async def sharpen(
        self,
        ctx: HuskyContext,
        # image: discord.Attachment,
        radius: commands.Range[float, 0, 50],
        sigma: commands.Range[float, 0, 50],
    ):
        """
        Sharpens an image.

        Parameters
        ----------
        image: discord.Attachment
            The image to sharpen.

        radius: float
            The radius to use for the sharpen.

        sigma: float
            The sigma value to use for the sharpen.
        """

        wimage = await convert_image(image)
        wimage.sharpen(radius=radius, sigma=sigma)
        await sendoff(ctx, wimage, "Sharpened image")


async def setup(bot: Husky):
    await bot.add_cog(Image(bot))
