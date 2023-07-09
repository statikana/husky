"""
Contains all of the classes for the bot which
contain and make up the bot's structure, types,
and events.
"""


from typing import Optional, Type, Union
import discord
from discord.ext import commands
from discord.app_commands import CommandTree
import logging_setup
import logging
from glob import glob
import asyncpg

from database import HuskyPool


class Husky(commands.Bot):
    def __init__(self):
        self.prefix = "hk "
        super().__init__(
            command_prefix=self.prefix,
            help_command=None,
            tree_cls=HuskyTree,
            intents=discord.Intents.all(),
        )

    async def get_context(
        self,
        origin: Union[discord.Message, discord.Interaction],
        *,
        cls: Optional[Type[commands.Context["Husky"]]] = None,
    ) -> Union[commands.Context, "HuskyContext"]:
        return await super().get_context(origin, cls=HuskyContext)

    async def setup_hook(self) -> None:
        logging_setup.begin()
        logging.INFO(f"{self.__class__.__name__} starting...")

        await self.load_extensions()

        logging.INFO(f"{self.__class__.__name__} ready")

    async def load_extensions(self, glob_fmt: str = "./ext/**/*.py") -> None:
        for ext_path in glob(glob_fmt):
            await self.load_extension(ext_path)

    async def add_cog(self, cog: commands.Cog) -> None:
        await super().add_cog(cog)
        logging.INFO(f"loaded {cog.__class__.__name__}")

    async def connect_psql(self) -> None:
        pool = asyncpg.create_pool(
            dsn=f"postgresql://postgres:{input('PSQL Password')}@localhost:5432/husky"
        )
        self.pool = HuskyPool.from_apg_pool(pool)

class HuskyTree(CommandTree):
    def __init__(self, client: discord.Client):
        super().__init__(client, fallback_to_global=True)


class HuskyContext(commands.Context):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._guild: discord.Guild = kwargs["guild"]
        self._message: discord.Message = kwargs["message"]
        self._bot: Husky = kwargs["bot"]

    @property
    def guild(self) -> discord.Guild:
        return self._guild

    @property
    def message(self) -> "_HuskyMessage":
        return self._message

    @property
    def bot(self) -> Husky:
        return self._bot


class _HuskyMessage(discord.Message):
    @property
    def guild(self) -> discord.Guild:
        return self.guild
