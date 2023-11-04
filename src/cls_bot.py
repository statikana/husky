import datetime
import json
import time
from typing import (
    Any,
    Callable,
    Generator,
    Mapping,
    Optional,
    Set,
    Type,
    TypeVar,
    Union,
)
import typing
import discord
from discord.ext import commands
from discord.app_commands import CommandTree
from discord.ext.commands.cog import Cog
from discord.ext.commands.core import Command
from discord.message import Message

from .utils.errors import AmbiguousCommandName

from .utils.types import LoadedFile
from . import logging_setup
import logging
from glob import glob
import asyncpg
import aiohttp
import importlib

from .database.database import HuskyPool, HuskyWrapper, Users, TODO


class Husky(commands.Bot):
    def __init__(self):
        self.prefix = "hk "
        super().__init__(
            command_prefix=self.prefix,
            help_command=None,
            tree_cls=HuskyTree,
            intents=discord.Intents.all(),
        )

        self.session: aiohttp.ClientSession = aiohttp.ClientSession(
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0"
            }
        )

    async def get_context(
        self,
        origin: Union[discord.Message, discord.Interaction],
        *,
        cls: Optional[Type[commands.Context["Husky"]]] = None,
    ) -> "HuskyContext":
        ctx = await super().get_context(origin, cls=HuskyContext)
        if ctx.command is None and ctx.prefix is not None:
            # try to find the command
            try:
                message = ctx.message.content
                command_content = message[len(ctx.prefix) :]  # remove prefix
                command_content = command_content.strip()
                # we have no way of splitting between the command and the
                # arguments, so we guess for each possible layer of subcommands
                indicies = range(1, 3)
                for i in indicies:
                    command_name_parts = command_content.split(" ")[0:i]
                    command_name = " ".join(command_name_parts).strip()

                    found_commands = list(
                        filter(
                            lambda c: c.qualified_name.endswith(command_name)
                            or any(alias == command_name for alias in c.aliases),
                            self.walk_commands(),
                        )
                    )
                    if len(found_commands) == 0:
                        continue
                    elif len(found_commands) == 1:
                        command = found_commands[0]
                        ctx.command = command
                        ctx.invoked_with = command.name
                        ctx.invoked_parents = command.qualified_name.split(" ")[:-1]
                        return ctx
                        # now we need to convert arguments as the library would normally do

                        # ctx.invoke(
                        #     command, *command_name_parts[i:].extend(ctx.message.attachments)
                        # )
                    else:
                        raise AmbiguousCommandName(found_commands)
            except AmbiguousCommandName as e:
                raise e
            except Exception as e:
                return ctx
        return ctx

    async def setup_hook(self) -> None:
        logging_setup.begin()
        logging.info(f"{self.__class__.__name__} starting...")

        await self.reload_extensions()
        await self.connect_psql()

        logging.info(f"{self.__class__.__name__} ready")

    async def reload_extensions(self) -> tuple[list[LoadedFile], list[LoadedFile]]:
        format: Callable[[str], str] = (
            lambda path: path.replace("\\", ".").removesuffix(".py").strip(".")
        )

        loaded_ext = []
        loaded_util = []
        for ext_path in glob(".\\src\\ext\\*.py", recursive=True):
            path = format(ext_path)
            try:
                await self.load_extension(path)
            except commands.ExtensionAlreadyLoaded:
                await self.reload_extension(path)

            loaded_ext.append(LoadedFile(path, path[path.rfind(".") + 1 :]))

        for ext_path in glob(".\\src\\utils\\*.py", recursive=True):
            path = format(ext_path)
            try:
                module = importlib.import_module(path)
                importlib.reload(module)
            except ImportError:
                continue

            loaded_util.append(LoadedFile(path, path[path.rfind(".") + 1 :]))

        return loaded_ext, loaded_util

    async def connect_psql(self) -> None:
        env = open("env.json", "r")
        dir = json.load(env)["psql"]
        pool = await asyncpg.create_pool(
            dsn=f"postgresql://{dir['user']}:{dir['password']}@{dir['host']}:{dir['port']}/{dir['database']}"
        )
        # self.pool = HuskyPool.from_apg_pool(pool)
        self.pool = pool
        await self.instantiate_database_wrappers()

    async def instantiate_database_wrappers(self) -> None:
        self.db_users: Users = Users(self.pool)
        await self.db_users.make_table()
        self.db_todo: TODO = TODO(self.pool)
        await self.db_todo.make_table()

    # overrides for inherited methods
    def get_command(self, name: str) -> "HuskyCommand":
        return super().get_command(name)

    def get_cog(self, name: str) -> "HuskyCog":
        return super().get_cog(name)

    def walk_commands(
        self,
    ) -> Generator["HuskyCommand", None, None]:
        return super().walk_commands()

    def cogs(self) -> Mapping[str, "HuskyCog"]:
        return super().cogs

    def add_command(self, command: "HuskyCommand") -> None:
        return super().add_command(command)

    def remove_command(self, name: str) -> Optional["HuskyCommand"]:
        return super().remove_command(name)

    async def add_cog(self, cog: "HuskyCog") -> None:
        return await super().add_cog(cog)

    async def remove_cog(self, name: str) -> Optional["HuskyCog"]:
        return await super().remove_cog(name)


class HuskyTree(CommandTree):
    def __init__(self, client: discord.Client):
        super().__init__(client, fallback_to_global=True)


class HuskyContext(commands.Context):
    def __init__(self, **kwargs):
        self._guild: discord.Guild = kwargs.get("guild", kwargs["message"].guild)
        self._message: discord.Message = kwargs["message"]
        self._bot: Husky = kwargs["bot"]

        super().__init__(**kwargs)

    @property
    def guild(self) -> discord.Guild:
        return self._guild

    @property
    def message(self) -> "_HuskyMessage":
        return self._message

    @message.setter
    def message(self, value: discord.Message) -> None:
        self._message = value

    @property
    def bot(self) -> Husky:
        return self._bot

    @bot.setter
    def bot(self, value: Husky) -> None:
        self._bot = value

    def embed(
        self,
        title: Optional[str] = None,
        description: Optional[str] = None,
        color: discord.Color = discord.Color.dark_teal(),
        **kwargs,
    ):
        embed = discord.Embed(
            title=title, description=description, color=color, **kwargs
        )
        embed.timestamp = datetime.datetime.now()
        embed.set_author(
            name=self.author.display_name,
            url=f"https://discordapp.com/users/{self.author.id}",
            icon_url=self.author.display_avatar.url,
        )
        # formatted time Month Day, Year at Hour:Minute:Second
        fmt = time.strftime(
            "%B %d, %Y at %H:%M:%S", datetime.datetime.now().timetuple()
        )

        embed.set_footer(
            text=f"husky @ {fmt} ~ {self.prefix}help",
        )
        return embed


class HuskyCog(commands.Cog):
    def __init__(
        self,
        bot: Husky,
        hidden: bool = False,
        active: bool = True,
        emoji: str = "\N{WHITE QUESTION MARK ORNAMENT}",
    ):
        super().__init__()
        self.bot = bot
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
    ) -> Set["HuskyCommand"]:
        return {c for c in self.walk_commands()}

    def embed(
        self,
        title: Optional[str] = None,
        description: Optional[str] = None,
        color: discord.Color = discord.Color.dark_teal(),
        **kwargs,
    ):
        embed = discord.Embed(
            title=title, description=description, color=color, **kwargs
        )
        embed.timestamp = datetime.datetime.now()
        author_id = kwargs.get("author_id", None)
        if author_id is not None:
            author = self.bot.get_user(author_id)
            embed.set_author(
                name=author.display_name,
                url=f"https://discordapp.com/users/{author.id}",
                icon_url=author.display_avatar.url,
            )
        # formatted time Month Day, Year at Hour:Minute:Second
        fmt = time.strftime(
            "%B %d, %Y at %H:%M:%S", datetime.datetime.now().timetuple()
        )

        embed.set_footer(
            text=f"husky @ {fmt} ~ {self.prefix}help",
        )
        return embed


class _HuskyMessage(discord.Message):
    @property
    def guild(self) -> discord.Guild:
        return self.guild


class HuskyCommand(commands.HybridCommand[HuskyCog, Any, Any]):
    @property
    def cog(self) -> HuskyCog:
        return super().cog

    @property
    def parent(self) -> "HuskyCommandGroup":
        return super().parent


class HuskyCommandGroup(commands.GroupMixin[HuskyCog], HuskyCommand):
    @property
    def commands(self) -> Set[HuskyCommand]:
        return super().commands

    @property
    def add_command(self, command: HuskyCommand) -> None:
        return super().add_command(command)

    @property
    def remove_command(self, command: HuskyCommand) -> None:
        return super().remove_command(command)

    @property
    def walk_commands(self) -> Generator[HuskyCommand, None, None]:
        return super().walk_commands()

    @property
    def get_command(self, name: str) -> HuskyCommand:
        return super().get_command(name)

    def get_commands(self) -> list[HuskyCommand]:
        return super().get_commands()

    @property
    def recursively_remove_all_commands(self) -> None:
        return super().recursively_remove_all_commands()
