from typing import Optional
import discord
from discord.ext import commands
from lxml import etree
from time import perf_counter

from ..utils.errors import InternalError

from ..utils.types import Indicies

from ..cls_bot import Husky, HuskyContext, HuskyCog
from ..cls_ext import HuskyPaginator
from ..utils.converters import URL_safe_param, optional_URL_safe_param
from urllib.parse import unquote_plus


class Web(HuskyCog):
    """Commands for accessing data across the great interwebs."""

    def __init__(self, bot: Husky):
        super().__init__(bot, emoji="\N{GLOBE WITH MERIDIANS}")
        self.bot = bot

    @commands.hybrid_group()
    async def web(
        self, ctx: HuskyContext, *, query: Optional[str] = optional_URL_safe_param
    ):
        """Base command for the group. If no subcommand is provided, this will default to `web search`"""
        if ctx.invoked_subcommand is None:
            await ctx.invoke(self.search, query=query)

    @web.command()
    async def search(self, ctx: HuskyContext, query: str = optional_URL_safe_param):
        """
        Searches DDG for your query and returns a paginator with the results.

        Parameters
        ----------
        query: str, optional
            The query to search for. If not provided, the query will be taken from the previous message.
        """

        # while the javascript version is much nicer to work with, it's, well. javascript.
        # so we're going to use the html version instead, because emulating a browser is slow,
        # expensive, very not fun, and not scalabale.
        start = perf_counter()

        if query in (None, ""):
            raise commands.BadArgument(
                "No query provided or no previous message to take it from."
            )

        base = "https://lite.duckduckgo.com/lite"
        response = await self.bot.session.post(
            base,
            data={
                "q": query,
            },
        )

        root = etree.fromstring(await response.text(), etree.HTMLParser())

        results: list[tuple[str, str, str]] = []
        minor: list[str, str, str] = [None, None, None]

        n = 0  # xpaths is 1-indexed
        xpath_base = "/html/body/form/div/table[3]/tr[{}]"

        def format_text(text: str) -> str:
            try:
                text = text.strip("\n\t\r. ")
                replacements = {
                    "\xa0": " ",
                    "\u2013": "-",
                    "\u2014": "-",
                    "\u2018": "'",
                    "\u2019": "'",
                    "\u201c": '"',
                    "\u201d": '"',
                }
                text = text.translate(str.maketrans(replacements))
                return text
            except AttributeError:
                return "<no text provided>"

        while True:
            xpath_base_fmt = xpath_base.format(n + 1)
            try:
                if n % 4 == 0:
                    xpath = xpath_base_fmt + "/td[2]/a"
                    minor[0] = format_text(root.xpath(xpath)[0].text)
                elif n % 4 == 1:
                    xpath = xpath_base_fmt + "/td[2]"
                    temp = ""
                    for child in root.xpath(xpath)[0].itertext():
                        temp += child
                    minor[1] = format_text(temp)
                elif n % 4 == 2:
                    xpath = xpath_base_fmt + "/td[2]/span[1]"
                    minor[2] = format_text(root.xpath(xpath)[0].text)
                else:  # n % 4 == 3, blank spacer
                    xpath = xpath_base_fmt + "/td[2]"
                    results.append(tuple(minor))
                    minor = [None, None, None]

            except IndexError:
                break

            n += 1

        response.close()
        paginator = WebSearchPaginator(
            ctx,
            results,
            5,
            extras={
                "query": unquote_plus(query),
                "fetch_time": round(perf_counter() - start, 2),
            },
        )

        message = await ctx.send(view=paginator)
        await paginator.start(message)

    @web.command(aliases=["img"])
    async def image(self, ctx: HuskyContext, *, query: str = optional_URL_safe_param):
        """
        Searches DDG for your query and returns a paginator of images.

        Parameters
        ----------
        query: str, optional
            The query to search for. If not provided, the query will be taken from the previous message.
        """

        start = perf_counter()

        if query in (None, ""):
            raise commands.BadArgument(
                "No query provided or no previous message to take it from."
            )

        base = "https://unsplash.com/s/photos"
        response = await self.bot.session.get(
            f"{base}/{query.replace('+', '-')}",
        )

        root = etree.fromstring(await response.text(), etree.HTMLParser())

        response.close()

        results: list[tuple[str, str]] = []
        for c in root.xpath("//img[@itemprop='thumbnailUrl']"):
            try:
                results.append((c.attrib["src"], c.attrib["alt"]))
            except KeyError:
                break

        response.close()

        paginator = WebImagePaginator(
            ctx,
            results,
            1,
            extras={
                "query": unquote_plus(query),
                "fetch_time": round(perf_counter() - start, 2),
            },
        )

        message = await ctx.send(view=paginator)
        await paginator.start(message)


class WebSearchPaginator(HuskyPaginator):
    async def update_embed(
        self, indicies: Indicies, current_content: list
    ) -> discord.Embed:
        embed = self.ctx.embed(
            title=f"Search Results for `{self.extras['query']}` via DuckDuckGo - Page `{self.page + 1}/{self.n_pages}`",
            description=f"{len(self.items)} results in `~{self.extras['fetch_time']}` seconds",
        )
        for i, result in enumerate(current_content):
            embed.add_field(
                name=f"`{indicies.start+i+1}.` {result[0]}",
                value=f"> *{discord.utils.escape_markdown(result[1])}...*\rhttps://{result[2]}",
                inline=False,
            )

        return embed


class WebImagePaginator(HuskyPaginator):
    async def update_embed(
        self, indicies: Indicies, current_content: list
    ) -> discord.Embed:
        embed = self.ctx.embed(
            title=f"Image Results for `{self.extras['query']}` via UnSplash - Page `{self.page + 1}/{self.n_pages}`",
            description=f"{len(self.items)} results in `~{self.extras['fetch_time']}` seconds",
        )
        current_content = current_content[0]
        embed.set_image(url=current_content[0])
        embed.add_field(
            name=f"`{indicies.start+1}.` {current_content[1]}",
            value=f"https://{current_content[0]}",
        )

        return embed


async def setup(bot: Husky):
    await bot.add_cog(Web(bot))
