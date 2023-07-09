import logging
from typing import Any, Generator, Set
import discord
from discord.ext import commands
from discord import app_commands


class HuskyCog(commands.Cog):
    def __init__(
        self,
        hidden: bool = False,
        active: bool = True,
        emoji: str = "\N{WHITE QUESTION MARK ORNAMENT}",
    ):
        super().__init__()
        self.hidden = hidden
        self.active = active
        self.emoji = emoji

    async def cog_load(self) -> None:
        logging.DEBUG(
            f"loaded cog {self.__class__.__name__} [{len(all_commands)} commands]"
        )

    async def cog_unload(self) -> None:
        logging.DEBUG(
            f"unloaded cog {self.__class__.__name__} [{len(all_commands)} commands]"
        )

    def all_cog_commands(
        self,
    ) -> Generator[commands.HybridCommand["HuskyCog", Any, Any], None, None]:
        return self.walk_commands()
