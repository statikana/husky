import discord
from discord.ext import commands
from discord.interactions import Interaction
from ..database.database_types import Task

from ..utils.types import Indicies

# from discord.app_commands import

from ..cls_bot import HuskyContext, Husky, HuskyCog
from ..cls_ext import HuskyModal, HuskyView, HuskyPanel, HuskyPaginator
from ..utils.converters import convert_date, convert_time

import datetime
import time


class Secretary(HuskyCog):
    """Helps with mundane tasks"""

    def __init__(self, bot: Husky):
        super().__init__(bot, emoji="\N{BRIEFCASE}")
        self.bot = bot

    @commands.hybrid_group()
    async def todo(self, ctx: HuskyContext, *, task: str = ""):
        """Base command for the group."""
        if ctx.invoked_subcommand is None:
            if task == "":
                await ctx.invoke(self.list)
            else:
                await ctx.invoke(self.add, task=task)

    @todo.command(aliases=["a"])
    async def add(self, ctx: HuskyContext, *, task: str):
        """
        Adds a task to the todo list.

        Parameters
        ----------
        task: str
            The task to add to the todo list.
        """
        embed = ctx.embed(title="\N{Memo} Creating Task...", description=task)
        embed.add_field(name="Date", value="Not Set")
        embed.add_field(name="Time", value="Not Set")
        embed.add_field(name="Remind Type", value="Not Set [None]")

        view = AddTaskView(ctx, embed)
        message = await ctx.send(embed=embed, view=view)

        view.message = message

    @todo.command(aliases=["l"])
    async def list(self, ctx: HuskyContext, overdue_only: bool = False):
        """Lists all of your tasks"""
        tasks = await self.bot.db_todo.get_user_tasks(ctx.author.id)
        if overdue_only:
            tasks = [
                f
                for f in tasks
                if f.date is not None and f.date < datetime.datetime.now().date()
            ]

        if len(tasks) == 0:
            if overdue_only:
                embed = ctx.embed(
                    title="\N{White heavy check mark} You have no overdue tasks"
                )
            else:
                embed = ctx.embed(title="\N{White heavy check mark} You have no tasks")
            return await ctx.send(embed=embed)

        embed = ctx.embed(title="\N{Memo} Your Tasks")
        tasks = sorted(
            tasks,
            key=lambda t: datetime.datetime.combine(
                t.date or datetime.datetime.now().date(),
                t.time or datetime.time(0, 0, 0, 0),
            ),
        )
        view = TaskPaginator(ctx, tasks, 5)
        message = await ctx.send(embed=embed, view=view)
        view.message = message
        await view.update_view()


class AddTaskView(HuskyPanel):
    @discord.ui.button(
        label="Add Date", style=discord.ButtonStyle.primary, emoji="\N{CALENDAR}"
    )
    async def add_date(self, itx: discord.Interaction, button: discord.ui.Button):
        # open a modal using the interaction
        modal = AddTaskDateModal(self.ctx, self.embed)
        await itx.response.send_modal(modal)

    @discord.ui.button(
        label="Add Time",
        style=discord.ButtonStyle.primary,
        emoji="\N{CLOCK FACE ONE OCLOCK}",
    )
    async def add_time(self, itx: discord.Interaction, button: discord.ui.Button):
        modal = AddTaskTimeModal(self.ctx, self.embed)
        await itx.response.send_modal(modal)

    @discord.ui.button(
        label="Finish",
        style=discord.ButtonStyle.success,
        emoji="\N{WHITE HEAVY CHECK MARK}",
    )
    async def finish(self, itx: discord.Interaction, button: discord.ui.Button):
        embed_dict = self.embed.to_dict()
        cdate: datetime.date
        if embed_dict["fields"][0]["value"] == "Not Set":
            cdate = None
        else:
            cdate = datetime.datetime.strptime(
                embed_dict["fields"][0]["value"], "%B %d, %Y"
            ).date()

        ctime: datetime.time
        if embed_dict["fields"][1]["value"] == "Not Set":
            ctime = None
        else:
            ctime = datetime.datetime.strptime(
                embed_dict["fields"][1]["value"], "%I:%M %p"
            ).time()

        if ctime is not None and cdate is None:
            cdate = datetime.datetime.now().date()

            if datetime.datetime.combine(cdate, ctime) <= datetime.datetime.now():
                await itx.response.send_message(
                    "You can't set a task to be in the past!", ephemeral=True
                )
                return

        remind_type = embed_dict["fields"][2]["value"]

        await self.ctx.bot.db_todo.new_todo(
            itx.user.id, embed_dict["description"], cdate, ctime, remind_type
        )
        embed = self.ctx.embed(
            title="\N{WHITE HEAVY CHECK MARK} Task Created",
            description=embed_dict["description"],
        )

        datetime_desc = None
        if cdate is None and ctime is not None:
            datetime_desc = ctime.strftime("%I:%M %p")
        elif cdate is not None and ctime is None:
            datetime_desc = f"{cdate.strftime('%B %d')} [<t:{int(datetime.datetime.combine(cdate, datetime.time(0, 0, 0, 0)).timestamp())}:R>]"
        elif cdate is not None and ctime is not None:
            datetime_desc = f"{cdate.strftime('%B %d, %Y')} at {ctime.strftime('%I:%M %p')} [<t:{int(datetime.datetime.combine(cdate, ctime).timestamp())}:R>]"
        else:
            pass

        if datetime_desc is not None:
            embed.add_field(name="Date & Time", value=datetime_desc)

        await itx.response.edit_message(embed=embed, view=None)

    @discord.ui.select(
        placeholder="Remind type",
        options=[
            discord.SelectOption(label="Mention (this channel)"),
            discord.SelectOption(label="Direct Message"),
            discord.SelectOption(label="None"),
        ],
    )
    async def remind_type(self, itx: discord.Interaction, select: discord.ui.Select):
        embed_dict = self.embed.to_dict()
        embed_dict["fields"][2]["value"] = select.values[0]
        self.embed = discord.Embed.from_dict(embed_dict)
        await itx.response.edit_message(embed=self.embed)


class AddTaskDateModal(HuskyModal, title="Add task date"):
    def __init__(self, ctx: HuskyContext, embed: discord.Embed):
        super().__init__(ctx)
        self.ctx = ctx
        self.embed = embed

    date = discord.ui.TextInput(
        label="Date",
        placeholder="October 20 ... 20/10/2021 ... 20-10-2021 ... 20.10.2021 ... tomorrow ... next week",
    )

    async def on_submit(self, itx: discord.Interaction) -> None:
        cdate = await convert_date(self.ctx, self.date.value)
        embed_dict = self.embed.to_dict()
        t = embed_dict["fields"][1]["value"]
        if t != "Not Set":
            ctime = datetime.datetime.strptime(t, "%I:%M %p").time()
            cdatetime = datetime.datetime.combine(cdate, ctime)
            if cdatetime <= datetime.datetime.now():
                await itx.response.send_message(
                    "You can't set a task to be in the past!", ephemeral=True
                )
                return

        # t is either not set or past the current time
        if cdate < datetime.datetime.now().date():
            await itx.response.send_message(
                "You can't set a task to be in the past!", ephemeral=True
            )
            return

        embed_dict["fields"][0]["value"] = cdate.strftime("%B %d, %Y")
        self.embed = discord.Embed.from_dict(embed_dict)
        await itx.response.edit_message(embed=self.embed)


class AddTaskTimeModal(HuskyModal, title="Add task time"):
    def __init__(self, ctx: HuskyContext, embed: discord.Embed):
        super().__init__(ctx)
        self.ctx = ctx
        self.embed = embed

    time = discord.ui.TextInput(
        label="Time",
        placeholder="10:00 AM ... 10:00 PM ... 10:00 ... 10:00:00",
    )

    async def on_submit(self, itx: discord.Interaction) -> None:
        embed_dict = self.embed.to_dict()
        conv = await convert_time(self.ctx, self.time.value)
        embed_dict["fields"][1]["value"] = conv.strftime("%I:%M %p")
        self.embed = discord.Embed.from_dict(embed_dict)
        await itx.response.edit_message(embed=self.embed)


class TaskPaginator(HuskyPaginator):
    async def update_embed(
        self, indicies: Indicies, current_content: list[Task]
    ) -> discord.Embed:
        embed = self.ctx.embed(title="\N{Memo} Your Tasks")
        for i, task in enumerate(current_content):
            cdate = task.date
            ctime = task.time
            datetime_desc = None
            if cdate is None and ctime is not None:
                datetime_desc = ctime.strftime("%I:%M %p")
            elif cdate is not None and ctime is None:
                datetime_desc = f"{cdate.strftime('%B %d')} [<t:{int(datetime.datetime.combine(cdate, datetime.time(0, 0, 0, 0)).timestamp())}:R>]"
            elif cdate is not None and ctime is not None:
                datetime_desc = f"{cdate.strftime('%B %d, %Y')} at {ctime.strftime('%I:%M %p')} [<t:{int(datetime.datetime.combine(cdate, ctime).timestamp())}:R>]"
            else:
                datetime_desc = "No due date"

            created_desc = task.datetime_created.strftime("%B %d, %Y at %I:%M %p")

            embed.add_field(
                name=f"`{indicies.start+i+1}.` {task.task}",
                value=f"> **Due: {datetime_desc}**\n> *Set: {created_desc}*",
                inline=False,
            )

        return embed


async def setup(bot: Husky):
    await bot.add_cog(Secretary(bot))
