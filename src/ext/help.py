import copy
import inspect
from typing import Callable, Optional, Iterable
import discord
from discord.ext import commands
from discord.app_commands import Choice

from ..utils.formatting import fmt_data, fuzzy

from ..cls_ext import HuskyView

from ..cls_bot import HuskyCommand, HuskyCommandGroup, HuskyContext, Husky, HuskyCog


class Help(HuskyCog):
    def __init__(self, bot: Husky):
        super().__init__(bot, emoji="\N{BOOKS}", hidden=True)
        self.bot = bot

    @commands.hybrid_command(aliases=["h", "command", "whatis"])
    async def help(
        self,
        ctx: HuskyContext,
        *,
        command: Optional[str] = None,
        group: Optional[str] = None,
        cog: Optional[str] = None,
    ):
        if command is not None:
            found_command = self.bot.get_command(command)
            if found_command is None or found_command.hidden:
                raise commands.CommandNotFound(f"Command `{command}` not found.")

            if isinstance(found_command, commands.Group):
                group = command
                command = None

            else:
                embed = await Help.command_help_embed(ctx, found_command)
                view = await Help.command_help_view(ctx, found_command)
                message = await ctx.send(embed=embed, view=view)
                view.message = message

        if group is not None and command is None:
            found_group = self.bot.get_command(group)
            if (
                found_group is None
                or found_group.hidden
                or not isinstance(found_group, commands.Group)
            ):
                raise commands.CommandNotFound(f"Group `{group}` not found.")

            embed = await Help.group_help_embed(ctx, found_group)
            view = await Help.group_help_view(ctx, found_group)
            message = await ctx.send(embed=embed, view=view)
            view.message = message

        elif cog is not None:
            found_cog = self.bot.get_cog(cog)
            if found_cog is None or found_cog.hidden:
                raise commands.CommandNotFound(f"Cog `{cog}` not found.")

            embed = await Help.cog_help_embed(ctx, found_cog)
            view = await Help.cog_help_view(ctx, found_cog)
            message = await ctx.send(embed=embed, view=view)
            view.message = message

    @help.autocomplete(name="command")
    async def help_command_autocomplete(
        self, ctx: HuskyContext, argument: str
    ) -> list[Choice]:
        return self.autocomp(
            ctx,
            argument,
            self.bot.walk_commands(),
            cmd_filter=lambda c: not isinstance(c, commands.Group)
            and not c.cog.hidden
            and c.cog.active,
        )

    @help.autocomplete(name="group")
    async def help_group_autocomplete(
        self, ctx: HuskyContext, argument: str
    ) -> list[Choice]:
        self.autocomp(
            ctx,
            argument,
            self.bot.walk_commands(),
            cmd_filter=lambda c: isinstance(c, commands.Group)
            and not c.cog.hidden
            and c.cog.active,
        )

    @help.autocomplete(name="cog")
    async def help_cog_autocomplete(
        self, ctx: HuskyContext, argument: str
    ) -> list[Choice]:
        return self.autocomp(
            ctx,
            argument,
            self.bot.cogs().values(),
            cmd_filter=lambda c: not c.hidden and c.active,
        )

    def autocomp(
        self,
        ctx: HuskyContext,
        argument: str,
        items: Iterable[HuskyCommand | HuskyCog],
        cmd_filter: Callable[[HuskyCommand | HuskyCog], bool] = lambda c: not c.hidden,
    ):
        cached: dict[str, float] = {}
        l = []
        for v in items:
            if cmd_filter(v):
                cached[v.qualified_name] = fuzzy(v.qualified_name, argument)
                l.append(Choice(name=v.qualified_name, value=v.qualified_name))
        final = sorted(l, key=lambda c: cached[c.value], reverse=True)[:25]
        return final

    @staticmethod
    async def command_help_embed(
        ctx: HuskyContext, command: HuskyCommand
    ) -> discord.Embed:
        embed = ctx.embed(
            title=f"Help: `{command.qualified_name}`",
            description=f"> *{Help.get_command_description(command)}*",
        )
        embed.add_field(
            name="Usage",
            value=f"`{ctx.prefix}{await Help.get_command_signature(ctx, command)}`",
        )
        for name, param in command.params.items():
            points = [
                ("Input Type", Help.get_annotation_name(param)),
                ("Required", param.required),
            ]
            if not param.required:
                points.append(
                    (
                        "Default [In This Context]",
                        await param.get_default(ctx) or param.displayed_default,
                    )
                )
            desc = fmt_data(points)
            embed.add_field(
                name=f"`{await Help.get_param_display(ctx, param)}`",
                value=desc + f"\n> *{param.description or '<No Description>'}*",
                inline=False,
            )

        return embed

    @staticmethod
    async def command_help_view(ctx: HuskyContext, command: HuskyCommand):
        view = HuskyView()
        command_select_group = CommandSelect(
            ctx,
            [
                c
                for c in command.parent.commands
                if not c.hidden and not isinstance(c, commands.HybridGroup)
            ],
            placeholder="Select Command From Group",
        )
        view.add_item(command_select_group)

        command_select_cog = CommandSelect(
            ctx,
            [c for c in command.cog.walk_commands() if not c.hidden],
            placeholder="Select Command From Cog",
        )
        view.add_item(command_select_cog)

        cog_select = CogSelect(
            ctx, [c for c in ctx.bot.cogs().values() if not c.hidden]
        )
        view.add_item(cog_select)

        return view

    @staticmethod
    async def group_help_embed(ctx: HuskyContext, group: HuskyCommand) -> discord.Embed:
        embed = ctx.embed(
            title=f"Help: `{group.qualified_name}`",
            description=f"> *{Help.get_command_description(group)}*\n\r**Command Count:** `{len(group.commands)}`",
        )
        for command in group.commands:
            embed.add_field(
                name=f"`{await Help.get_command_signature(ctx, command)}`",
                value=f"> *{Help.get_command_description(command)}*",
                inline=False,
            )
        return embed

    @staticmethod
    async def group_help_view(ctx: HuskyContext, group: HuskyCommandGroup):
        view = HuskyView()
        command_select = CommandSelect(
            ctx,
            [c for c in group.commands if not c.hidden],
            placeholder="Select Command From Group",
        )
        view.add_item(command_select)

        cog_select = CogSelect(
            ctx,
            [
                c
                for c in ctx.bot.cogs().values()
                if not c.hidden and not isinstance(c, commands.GroupMixin)
            ],
        )
        view.add_item(cog_select)
        return view

    @staticmethod
    async def cog_help_embed(ctx: HuskyContext, cog: HuskyCog) -> discord.Embed:
        embed = ctx.embed(
            title=f"Help: `{cog.qualified_name}`",
            description=f"> *{Help.get_cog_description(cog)}*",
        )
        embed.add_field(name="Command Count", value=len(cog.all_cog_commands()))
        return embed

    @staticmethod
    async def cog_help_view(ctx: HuskyContext, cog: HuskyCog):
        view = HuskyView()
        command_select = CommandSelect(
            ctx,
            [c for c in cog.walk_commands() if not c.hidden],
            placeholder="Select Command From Cog",
        )
        view.add_item(command_select)

        cog_select = CogSelect(
            ctx,
            [
                c
                for c in ctx.bot.cogs().values()
                if not c.hidden and not isinstance(c, commands.GroupMixin)
            ],
        )
        view.add_item(cog_select)
        return view

    @staticmethod
    def get_command_description(command: HuskyCommand) -> str:
        return (
            command.description
            or command.short_doc
            or command.brief
            or "<No Description>"
        )

    @staticmethod
    async def get_command_signature(
        ctx: HuskyContext, command: HuskyCommand, *, hot: bool = False
    ) -> str:
        base = command.qualified_name
        for name, param in command.params.items():
            base += f" {await Help.get_param_display(ctx, param, hot=hot)}"

        return base

    @staticmethod
    async def get_param_display(
        ctx: HuskyContext, param: commands.Parameter, *, hot: bool = False
    ) -> str:
        # if it's hot, use the default and potentially call a default getter
        # if it's cold, use the default if it's not a function, otherwise use the displayed default
        if hot:
            default = await param.get_default(ctx) or f"~{param.displayed_default}~"
        else:
            default = (
                d
                if not callable(d := param.default)
                else f"~{param.displayed_default}~"
            )
        return (
            f"<{param.name}: {Help.get_annotation_name(param)}>"
            if param.required
            else f"[{param.name}: {Help.get_annotation_name(param)}={default}]"
        )

    @staticmethod
    def get_annotation_name(param: commands.Parameter) -> str:
        param_cls = param.annotation.__class__
        if hasattr(param_cls, "__hk_annotation__"):
            return param_cls.__hk_annotation__
        if param_cls == commands.Greedy:
            return f"Multiple[{Help.get_converter_name(param.annotation.converter)}]"
        return param.annotation.__name__

    @staticmethod
    def get_converter_name(converter: type[commands.Converter]) -> str:
        if hasattr(converter, "__hk_annotation__"):
            return converter.__hk_annotation__
        return str(converter.__name__)

    @staticmethod
    def get_cog_description(cog: HuskyCog) -> str:
        return cog.description or "<No Description>"


class CommandSelect(discord.ui.Select):
    def __init__(
        self, ctx: HuskyContext, commands: list[HuskyCommand], *, placeholder: str
    ):
        super().__init__(
            placeholder=placeholder,
            min_values=1,
            max_values=1,
            options=[
                discord.SelectOption(
                    label=c.qualified_name,
                    value=c.qualified_name,
                )
                for c in commands
            ],
        )
        self.ctx = ctx

    async def callback(self, interaction: discord.Interaction):
        command = self.ctx.bot.get_command(self.values[0])
        embed = await Help.command_help_embed(self.ctx, command)
        view = await Help.command_help_view(self.ctx, command)
        await interaction.response.edit_message(embed=embed, view=view)


class CogSelect(discord.ui.Select):
    def __init__(self, ctx: HuskyContext, cogs: list[HuskyCog]):
        super().__init__(
            placeholder="Select Cog",
            min_values=1,
            max_values=1,
            options=[
                discord.SelectOption(
                    label=c.qualified_name, value=c.qualified_name, emoji=c.emoji
                )
                for c in cogs
            ],
        )
        self.ctx = ctx

    async def callback(self, interaction: discord.Interaction):
        cog = self.ctx.bot.get_cog(self.values[0])
        embed = await Help.cog_help_embed(self.ctx, cog)
        view = await Help.cog_help_view(self.ctx, cog)
        await interaction.response.edit_message(embed=embed, view=view)


async def setup(bot: Husky):
    await bot.add_cog(Help(bot))
