import discord
from discord.ext import commands
from ..cls_bot import Husky, HuskyContext
from ..cls_ext import HuskyCog


class Claims(HuskyCog):
    def __init__(self, bot: Husky):
        super().__init__(bot, emoji="\N{World Map}")


async def setup(bot: Husky) -> None:
    await bot.add_cog(Claims(bot))
