import discord
from discord.ext import commands
from ..cls_bot import Husky, HuskyContext
from ..cls_ext import HuskyCog


from ..data_types import Dimension


class Claims(HuskyCog):
    def __init__(self, bot: Husky):
        self.bot = bot
        super().__init__(bot, emoji="\N{World Map}")
    
    @commands.hybrid_group()
    async def claims(self):
        "Commands that deal with land claims in the SMP"

    @claims.command()
    async def create(self, claim_x: int, claim_y: int, dimension: Dimension = Dimension.OVERWORLD):
        "Attempts to create a claim in the given dimension. Claims have a default radius of 200."
        claims = await self.bot.dbw_claims


async def setup(bot: Husky) -> None:
    await bot.add_cog(Claims(bot))
