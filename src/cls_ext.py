import logging
from typing import Any, Generator, Set
from discord.ext import commands


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
        logging.info(
            f"loaded {self.__class__.__name__} [{len(self.all_cog_commands())} commands]"
        )

    async def cog_unload(self) -> None:
        logging.info(
            f"unloaded {self.__class__.__name__} [{len(self.all_cog_commands())} commands]"
        )

    def all_cog_commands(
        self,
    ) -> Set[commands.HybridCommand["HuskyCog", Any, Any]]:
        return {c for c in self.walk_commands()}
