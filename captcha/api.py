import asyncio
import logging
from typing import Union

import discapty
import discord
from redbot.core import Config
from redbot.core.bot import Red
from redbot.core.utils import chat_formatting as form
from redbot.core.utils.predicates import MessagePredicate, ReactionPredicate

from .errors import MissingRequiredValueError, AskedForReload

log = logging.getLogger("red.predeactor.captcha")


class Challenge:
    """Representation of a challenge an user is doing."""

    def __init__(self, bot: Red, member: discord.Member, data: dict):
        self.bot: Red = bot

        self.member: discord.Member = member
        self.guild: discord.Guild = member.guild
        self.config: dict = data  # Will contain the config of the guild.

        if not self.config["channel"]:
            raise MissingRequiredValueError("Missing channel for verification.")
        self.channel: Union[discord.TextChannel, discord.DMChannel] = bot.get_channel(
            self.config["channel"]
        )

        self.type = self.config["type"]

        self.messages = dict()
        # bot_challenge: Message send for the challenge, contain captcha.
        # logs: The message that has been sent in the logging channel

        self.running = False
        self.tasks = []

        self.captcha = discapty.Captcha(self.type)

    async def try_challenging(self) -> bool:
        """Do challenging in one function!

        This does not try to get errors.
        This does not gives role.
        """
        if self.running is True:
            raise OverflowError("A Challenge is already running.")

        if self.messages.get("bot_challenge"):
            await self.reload()
        else:
            await self.send_basics()

        self.running = True

        try:
            received = await self.wait_for_action()
            if hasattr(received, "content"):
                error_message = ""
                try:
                    state = await self.verify(received.content)
                except discapty.SameCodeError:
                    error_message += form.error(form.bold("Code invalid. Do not copy and paste."))
                    state = False
                else:
                    error_message += form.warning("Code invalid.")
                await self.channel.send(error_message, delete_after=3)
            else:
                raise AskedForReload("User want to reload Captcha.")
        finally:
            self.running = False
        return state

    async def send_basics(self) -> None:
        """Send the first messages."""
        if self.messages.get("bot_challenge"):
            raise OverflowError("Use 'Challenge.reload' to create another code.")

        embed_and_file = await self.captcha.generate_embed(
            guild_name=self.guild.name,
            author={"name": f"Captcha for {self.member.name}", "url": self.member.avatar_url},
            title=f"{self.guild.name} Verification System",
            description=(
                "Please return me the code on the following image. The code is made of 8"
                "characters."
            ),
        )

        try:
            bot_message: discord.Message = await self.channel.send(
                embed=embed_and_file["embed"],
                file=embed_and_file["image"],
                delete_after=900,  # Delete after 15 minutes.
            )
        except discord.Forbidden:
            raise PermissionError("Cannot send message in verification channel.")
        self.messages["bot_challenge"] = bot_message
        try:
            await bot_message.add_reaction("🔁")
        except discord.Forbidden:
            raise PermissionError("Cannot react in verification channel.")

    async def wait_for_action(self) -> Union[discord.Reaction, discord.Message, None]:
        """Wait for an action from the user.

        It will return an object of discord.Message or discord.Reaction depending what the user
        did.
        """
        self.cancel_tasks()  # Just in case...
        self.tasks = self._give_me_tasks()
        done, pending = await asyncio.wait(
            self.tasks,
            timeout=self.config["timeout"] * 60,
            return_when=asyncio.FIRST_COMPLETED,
        )
        self.cancel_tasks()
        if len(done) == 0:
            raise TimeoutError("User didn't answer.")
        try:  # An error is raised if we return the result and when the task got cancelled.
            return done.pop().result()
        except asyncio.CancelledError:
            return None

    async def reload(self) -> None:
        if not self.messages.get("bot_challenge", None):
            raise AttributeError(
                "There is not message to reload. Use 'Challenge.send_basics' first."
            )

        old_message: discord.Message = self.messages["bot_challenge"]
        try:
            await old_message.delete()
        except (discord.Forbidden, discord.HTTPException):
            log.warning(
                "Bot was unable to delete previous message in {guild}, ignoring.".format(
                    guild=self.guild.name
                )
            )

        self.captcha.code = discapty.discapty.random_code()
        embed_and_file = await self.captcha.generate_embed(
            guild_name=self.guild.name,
            title="{guild} Verification System".format(guild=self.guild.name),
            description=(
                "Please return me the code on the followiing image. The code is made of 8"
                "characters."
            ),
        )

        try:
            bot_message: discord.Message = await self.channel.send(
                embed=embed_and_file["embed"],
                file=embed_and_file["image"],
                delete_after=900,  # Delete after 15 minutes.
            )
        except discord.Forbidden:
            raise PermissionError("Cannot send message in verification channel.")
        self.messages["bot_challenge"] = bot_message
        try:
            await bot_message.add_reaction("🔁")
        except discord.Forbidden:
            raise PermissionError("Cannot react in verification channel.")

    async def verify(self, code_input: str) -> bool:
        """Verify a code."""
        return await self.captcha.verify_code(code_input)

    def cancel_tasks(self) -> None:
        """Cancel the ongoing tasks."""
        for task in self.tasks:
            task: asyncio.Task
            if not task.done():
                task.cancel()

    def _give_me_tasks(self) -> list:
        return [
            asyncio.create_task(
                self.bot.wait_for(
                    "reaction_add",
                    check=ReactionPredicate.with_emojis(
                        "🔁", message=self.messages["bot_challenge"], user=self.member
                    ),
                )
            ),
            asyncio.create_task(
                self.bot.wait_for(
                    "message",
                    check=MessagePredicate.same_context(
                        channel=self.channel,
                        user=self.member,
                    ),
                )
            ),
        ]


# class ListenersAPI:
#     @commands.Cog.listener()
#     async def on_predeactor_captcha_pass(self, captcha_class: Challenge):
#         pass
#
#     @commands.Cog.listener()
#     async def on_predeactor_captcha_fail(self, captcha_class: Challenge):
#         pass
#
#     @commands.Cog.listener()
#     async def on_predeactor_captcha_ask_reload(self, captcha_class: Challenge):
#         pass


class API:
    def __init__(self, bot: Red, config: Config):
        self.bot = bot
        self.config = config
        self.challenge = {}

    async def generate_image_for_guild(self, guild: discord.Guild, *, code: str = None):
        captcha_type = await self.config.guild(guild).type()
        captcha = discapty.Captcha(captcha_type)
        return captcha.generate_captcha(code)

    async def generate_captcha_object_for_member(self, member: discord.Member):
        """
        Create a Captcha object for a member, append it to the API's queue and return it.
        """
        captcha_type = await self.config.guild(member.guild).type()
        captcha = discapty.Captcha(captcha_type)
        self.challenge[member.id] = captcha
        return captcha

    async def delete_member_in_queue(self, member: discord.Member):
        """
        Delete the user in the API's queue.
        """
        if member.id in self.challenge:
            del self.challenge[member.id]

    async def get_users_in_challenge(self):
        """
        Return a list of users ID that are actually having a challenge.
        """
        return [int(u) for u in self.challenge.keys()]
