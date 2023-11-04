import datetime
import discord
from discord.ext import commands
from discord.ext import tasks

from .cls_bot import HuskyContext, Husky, HuskyCog


class Watch(HuskyCog):
    @tasks.loop(seconds=5)
    async def check_tasks_loop(self):
        # find tasks that are overdue
        tasks = await self.bot.db_todo.get_overdue_tasks(threshold_sec=5)
        for t in tasks:
            user = self.bot.get_user(t.user_id)
            if user is None:
                await self.bot.db_todo.delete_user_tasks(t)

            if t.remind_type == 1:
                embed = self.embed(
                    title="\N{Alarm Clock} Task Reminder - Overdue!",
                    description=t.task,
                    color=discord.Color.red(),
                )

                datetime_desc = None
                if t.date is None and t.time is not None:
                    datetime_desc = t.time.strftime("%I:%M %p")
                elif t.date is not None and t.time is None:
                    datetime_desc = f"{t.date.strftime('%B %d')} [<t:{int(datetime.datetime.combine(t.date, datetime.time(0, 0, 0, 0)).timestamp())}:R>]"
                elif t.date is not None and t.time is not None:
                    datetime_desc = f"{t.date.strftime('%B %d, %Y')} at {t.time.strftime('%I:%M %p')} [<t:{int(datetime.datetime.combine(t.date, t.time).timestamp())}:R>]"
                else:
                    pass

                if datetime_desc is not None:
                    embed.add_field(name="Date & Time", value=datetime_desc)
                try:
                    await user.send(embed=embed)
                except discord.Forbidden:
                    pass
