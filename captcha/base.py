import logging
from datetime import datetime
from typing import Optional, Union

import discapty
import discord
from redbot.core import Config, commands
from redbot.core.bot import Red
from redbot.core.utils.chat_formatting import bold, humanize_list

from .abc import CompositeMetaClass
from .api import API
from .commands import OwnerCommands, Settings
from .events import Listeners
from .errors import AlreadyHaveCaptchaError, MissingRequiredValueError, DeletedValueError
from .informations import (
    __author__,
    __patchnote__,
    __patchnote_version__,
    __version__,
)

DEFAULT_GLOBAL = {"log_level": 50}
DEFAULT_GUILD = {
    "channel": None,  # The channel where the captcha is sent.
    "logschannel": None,  # Where logs are sent.
    "enabled": False,  # if challenges must be activated.
    "autoroles": [],  # Roles to give.
    "temprole": None,  # Temporary role to give.
    "type": "plain",  # Captcha type.
    "timeout": 5,  # Time in minutes before kicking.
}
log = logging.getLogger("red.predeactor.captcha")


class Captcha(
    Settings,
    OwnerCommands,
    Listeners,
    commands.Cog,
    name="Captcha",
    metaclass=CompositeMetaClass,
):
    """A Captcha defensive system. to challenge the new users and protect yourself a bit more of
    raids."""

    def __init__(self, bot: Red) -> None:
        super().__init__()

        self.bot: Red = bot

        self.data: Config = Config.get_conf(None, identifier=495954056, cog_name="Captcha")
        self.data.register_global(**DEFAULT_GLOBAL)
        self.data.register_guild(**DEFAULT_GUILD)

        self.running = {}
        self.api = API(self.bot, self.data)

        self.version = __version__
        self.patchnote = __patchnote__
        self.patchnoteconfig = None

    async def send_or_update_log_message(
        self,
        guild: discord.Guild,
        message_content: str,
        message_to_update: Optional[discord.Message] = None,
        *,
        member: discord.Member = None,
        file: discord.File = None,
        embed: discord.Embed = None,
    ) -> discord.Message:
        """
        Send a message or update one in the log channel.
        """
        time = datetime.now().strftime("%H:%M - %w/%d/%Y")
        content = ""
        if message_to_update:
            content += message_to_update.content + "\n"
        content += f"{bold(str(time))}{f' {member.mention}' if member else ''}: {message_content}"

        log_channel_id: Union[int, None] = await self.data.guild(guild).logschannel()
        if not log_channel_id:
            raise MissingRequiredValueError("Missing logging channel ID.")

        log_channel: discord.TextChannel = self.bot.get_channel(log_channel_id)
        if log_channel and message_to_update:
            await message_to_update.edit(
                content=content,
                file=file,
                embed=embed,
                allowed_mentions=discord.AllowedMentions(users=False),
            )
            return message_to_update
        if log_channel:
            return await log_channel.send(
                content,
                file=file,
                embed=embed,
                allowed_mentions=discord.AllowedMentions(users=False),
            )
        raise DeletedValueError("Logging channel may have been deleted.")

    async def create_challenge_for(self, member: discord.Member) -> discapty.Captcha:
        """
        Create a Challenge class for an user and append it to the running challenges.
        """
        if member.id in self.running:
            raise AlreadyHaveCaptchaError("The user already have a captcha object running.")
        captcha_type = await self.config.guild(member.guild).type()
        captcha = discapty.Captcha(captcha_type)
        self.running[member.id] = captcha
        return captcha

    def delete_challenge_for(self, member: Union[discord.Member, int]) -> bool:
        if isinstance(member, discord.Member):
            member = member.id
        if member in self.running:
            del self.running[member.id]
            return True
        return False

    def is_running_captcha(self, user_or_id: Union[discord.Member, int]) -> bool:
        if isinstance(user_or_id, discord.Member):
            user_or_id = int(user_or_id.id)
        return user_or_id in self.running

    def format_help_for_context(self, ctx: commands.Context) -> str:
        """
        This will put some text at the top of the main help. ([p]help Captcha)
        Thank to Sinbad.
        """
        pre_processed = super().format_help_for_context(ctx)
        return "{pre_processed}\n\nAuthor: {authors}\nVersion: {version}".format(
            pre_processed=pre_processed,
            authors=humanize_list(__author__),
            version=self.version,
        )

    async def _initialize(self, send_patchnote: bool = True) -> None:
        """
        An initializer for the cog.
        It just set the logging level and send the patchnote if asked.
        """
        log_level = await self.data.log_level()
        log.setLevel(log_level)
        log.info("Captcha logging level has been set to: {lev}".format(lev=log_level))
        log.debug(
            "This logging level is reserved for testing and monitoring purpose, set the "
            "level to 2 if you prefer to be alerted by less minor events or doesn't want to help "
            "debugging this cog."
        )
        if send_patchnote:
            await self._send_patchnote()

    async def _send_patchnote(self) -> None:
        await self.bot.wait_until_red_ready()
        self.patchnoteconfig = notice = Config.get_conf(
            None,
            identifier=4145125452,
            cog_name="PredeactorNews",
        )
        notice.register_user(version="0")
        async with notice.get_users_lock():
            old_patchnote_version: str = await notice.user(self.bot.user).version()
            if old_patchnote_version != __patchnote_version__:
                log.info("New version of patchnote detected! Delivering... (¬‿¬ )")
                await self.bot.send_to_owners(self.patchnote)
                await notice.user(self.bot.user).version.set(__patchnote_version__)


def setup(bot: Red):
    cog = Captcha(bot)
    bot.add_cog(cog)
    # noinspection PyProtectedMember
    bot.loop.create_task(cog._initialize())
