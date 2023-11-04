from dataclasses import dataclass
import logging
from typing import Any, Callable, Generic, Set, TypeVar
import discord
from discord.ext import commands

from .cls_bot import HuskyContext

from .utils.types import Indicies

from .utils.errors import InternalError


T = TypeVar("T")


@dataclass
class HuskyViewOptions:
    timeout: int = 360
    """The timeout for the view, in seconds. Default: 360."""
    delete_after_timeout: bool = False
    """Whether or not to delete the message after the timeout. Requires the `message` attribute to be set on the respective `HuskyView`. Default: False"""
    func_allow_inter: Callable[[discord.Interaction], bool] = lambda view: True
    """A function that returns whether or not the interaction should be allowed. Default: lambda view: True"""

    @classmethod
    def default(cls) -> "HuskyViewOptions":
        return cls()


class HuskyView(discord.ui.View):
    def __init__(self, *, options: HuskyViewOptions = HuskyViewOptions.default()):
        super().__init__(timeout=options.timeout)

        self.opts = options
        self.message: discord.Message | None = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return self.opts.func_allow_inter(interaction)

    async def on_timeout(self) -> None:
        if self.opts.delete_after_timeout and self.message is not None:
            await self.message.delete()


class HuskyPaginator(HuskyView, Generic[T]):
    def __init__(
        self,
        ctx: HuskyContext,
        items: list[T],
        items_per_page: int,
        *,
        extras: dict[str, Any] = {},
        options: HuskyViewOptions = HuskyViewOptions.default(),
    ):
        super().__init__(options=options)

        self.ctx = ctx
        self.page = 0
        """Current index of the paginator. Should never be more than `self.n_pages-1` or less than 0."""
        self.items = items
        """The items being paginated."""
        self.items_per_page = items_per_page
        """The amount of items per page."""
        self.extras = extras
        """Extra data to be passed to the inheriting class."""

        self.n_pages = len(self.items) // self.items_per_page
        """The amount of pages in the paginator. Calculated automatically."""
        if len(self.items) % self.items_per_page != 0:
            self.n_pages += 1  # add one if there's any remaining

    @discord.ui.button(
        emoji="\N{BLACK LEFT-POINTING DOUBLE TRIANGLE WITH VERTICAL BAR}",
        style=discord.ButtonStyle.blurple,
        row=0,
    )
    async def full_back(self, inter: discord.Interaction, button: discord.Button):
        self.page = 0
        await self.update_view(inter, button)

    @discord.ui.button(
        emoji="\N{BLACK LEFT-POINTING TRIANGLE}",
        style=discord.ButtonStyle.blurple,
        row=0,
    )
    async def back(self, inter: discord.Interaction, button: discord.Button):
        self.page = max(0, self.page - 1)
        await self.update_view(inter, button)

    @discord.ui.button(
        emoji="\N{CROSS MARK}",
        style=discord.ButtonStyle.danger,
        row=0,
        custom_id="stop",
    )
    async def stop(self, inter: discord.Interaction, button: discord.Button):
        await self.update_view(inter, button)

    @discord.ui.button(
        emoji="\N{BLACK RIGHT-POINTING TRIANGLE}",
        style=discord.ButtonStyle.blurple,
        row=0,
    )
    async def next(self, inter: discord.Interaction, button: discord.Button):
        self.page = min(self.n_pages - 1, self.page + 1)
        await self.update_view(inter, button)

    @discord.ui.button(
        emoji="\N{BLACK RIGHT-POINTING DOUBLE TRIANGLE WITH VERTICAL BAR}",
        style=discord.ButtonStyle.blurple,
        row=0,
    )
    async def full_next(self, inter: discord.Interaction, button: discord.Button):
        self.page = self.n_pages - 1
        await self.update_view(inter, button)

    async def start(self, message: discord.Message) -> None:
        self.message = message
        await self.update_view()

    async def update_view(
        self,
        inter: discord.Interaction | None = None,
        button: discord.Button | None = None,
    ) -> None:
        if self.message is None:
            raise InternalError("HuskyPaginator.message is None")

        if button is not None:
            if button.custom_id == "stop":
                for child in self.children:
                    if isinstance(child, (discord.ui.Button, discord.ui.Select)):
                        child.disabled = True
                if inter is not None:
                    await inter.response.defer()
                super().stop()
                await self.message.edit(view=self)
                return

            for child in self.children:
                if isinstance(child, discord.ui.Button):
                    if child.custom_id == button.custom_id:
                        child.style = discord.ButtonStyle.green
                    elif child.custom_id != "stop":
                        child.style = discord.ButtonStyle.blurple

        if self.page == 0:
            self.full_back.disabled = True
            self.back.disabled = True
        else:
            self.full_back.disabled = False
            self.back.disabled = False

        if self.page == self.n_pages - 1:
            self.full_next.disabled = True
            self.next.disabled = True
        else:
            self.full_next.disabled = False
            self.next.disabled = False

        current_content = self.items[
            self.page * self.items_per_page : (self.page + 1) * self.items_per_page
        ]
        indicies = Indicies(
            start=self.page * self.items_per_page,
            end=min((self.page + 1) * self.items_per_page, len(self.items)),
        )
        embed = await self.update_embed(indicies, current_content)
        content = await self.update_content(indicies, current_content)

        await self.message.edit(content=content, embed=embed, view=self)
        if inter is not None:
            await inter.response.defer()

    async def update_embed(
        self, indicies: Indicies, current_content: list[T]
    ) -> discord.Embed:
        """Returns an embed with the current page's content. Must be overridden by an inheriting class. Called automatically by `HuskyPaginator.update_view`."""
        raise NotImplementedError

    async def update_content(self, indicies: Indicies, current_content: list[T]) -> str:
        """Returns the text to be displayed in the message. May be overridden by an inheriting class. Called automatically by `HuskyPaginator.update_view`. Defualts to an empty string."""
        return ""


class HuskyPanel(HuskyView):
    def __init__(
        self,
        ctx: HuskyContext,
        embed: discord.Embed,
        *,
        options: HuskyViewOptions = HuskyViewOptions.default(),
    ):
        self.ctx = ctx
        self.embed = embed
        super().__init__(options=options)

    @discord.ui.button(
        emoji="\N{CROSS MARK}",
        label="Cancel",
        style=discord.ButtonStyle.danger,
        row=0,
        custom_id="stop",
    )
    async def stop(self, itx: discord.Interaction, button: discord.Button):
        for child in self.children:
            if isinstance(child, (discord.ui.Button, discord.ui.Select)):
                child.disabled = True
        await itx.response.edit_message(view=self)
        super().stop()


class HuskyModal(discord.ui.Modal):
    def __init__(self, ctx: HuskyContext):
        self.ctx = ctx
        super().__init__(timeout=360)

    async def interaction_check(self, itx: discord.Interaction) -> bool:
        return itx.user == self.ctx.author
