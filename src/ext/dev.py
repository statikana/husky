from typing import Optional
from discord.ext import commands

from ..cls_bot import HuskyContext, Husky, HuskyCog


class Dev(HuskyCog):
    def __init__(self, bot: Husky):
        super().__init__(bot, emoji="\N{GEAR}", hidden=True)
        self.bot = bot

    @commands.command(name="sync")
    @commands.is_owner()
    async def sync_(self, ctx: HuskyContext):
        surface = await self.bot.tree.sync()
        await ctx.send(f"Synced {len(surface)} surface commands.")

    @commands.command(name="reload", aliases=["r"])
    @commands.is_owner()
    async def reload_(self, ctx: HuskyContext, *, ext_name: Optional[str]):
        if ext_name is not None:
            ext = "src.ext." + ext_name
            try:
                self.bot.reload_extension(ext)
            except commands.ExtensionNotLoaded:
                self.bot.load_extension(ext)
            except commands.ExtensionNotFound:
                await ctx.send(f"Extension `{ext}` not found.")

            await ctx.send(f"Reloaded extension `{ext}`.")
        else:
            await self.bot.reload_extensions()  # load twice
            ext, util = await self.bot.reload_extensions()
            embed = ctx.embed(title="Reloaded extensions")
            desc = "\n".join(
                f"**`{e.filename.ljust(15, '.')}`**`[{e.path}]`" for e in ext
            )
            desc += "\n"
            desc += "\n".join(
                f"*`{u.filename.ljust(15, '.')}`*`[{u.path}]`" for u in util
            )
            embed.description = desc
            await ctx.send(embed=embed)

    @commands.command(name="up")
    @commands.is_owner()
    async def up_(self, ctx: HuskyContext):
        # do the last command by this user
        async for msg in ctx.channel.history(limit=100):
            if msg.author == ctx.author:
                await self.bot.process_commands(msg)
                return

    @commands.command()
    @commands.is_owner()
    async def sqlf(self, ctx: HuskyContext, query: str):
        async with self.bot.pool.acquire() as conn:
            await ctx.send(f"```{await conn.fetch(query)}```")

    @commands.command()
    @commands.is_owner()
    async def sqle(self, ctx: HuskyContext, query: str):
        async with self.bot.pool.acquire() as conn:
            await ctx.send(f"```{await conn.execute(query)}```")


async def setup(bot: Husky):
    await bot.add_cog(Dev(bot))
