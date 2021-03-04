from typing import Literal

import aiohttp
import discord
from redbot.core import commands
from redbot.core.utils.chat_formatting import humanize_list

BASE_URL = "https://cacti-api.herokuapp.com"


class Miku(commands.Cog):
    """
    The first Miku images API.
    """

    __author__ = ["Predeactor"]
    __version__ = "v1.0.1"

    def __init__(self, bot):
        self.bot = bot

    def format_help_for_context(self, ctx: commands.Context) -> str:
        """Thanks Sinbad!"""
        pre_processed = super().format_help_for_context(ctx)
        return "{pre_processed}\n\nAuthor: {authors}\nCog Version: {version}".format(
            pre_processed=pre_processed,
            authors=humanize_list(self.__author__),
            version=self.__version__,
        )

    async def red_delete_data_for_user(
        self,
        *,
        requester: Literal["discord_deleted_user", "owner", "user", "user_strict"],
        user_id: int,
    ):
        """
        Nothing to delete...
        """
        pass

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    async def cacti(self, ctx: commands.Context):
        async with aiohttp.ClientSession() as session:
            async with session.get(BASE_URL) as response:
                if response.status == 503:
                    await ctx.send("The API is actually in maintenance, please retry later.")
                    return
                try:
                    status = response.status
                    url = await response.json()
                except aiohttp.ContentTypeError:
                    await ctx.send(
                        "API unavailable. Status code: {code}\nIt may be due of a "
                        "maintenance.".format(code=status)
                    )
                    return
        embed = discord.Embed(
            title="Here's a pic of Hatsune Miku!", color=await self.bot.get_embed_colour(ctx)
        )
        try:
            embed.set_image(url=url["url"])
        except KeyError:
            await ctx.send(
                "I received an incorrect format from the API\nStatus code: {code}".format(
                    code=status
                )
            )
        embed.set_footer(text="From https://cacti-api.herokuapp.com/")
        await ctx.send(embed=embed)
