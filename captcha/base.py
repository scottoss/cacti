"""
I can't believe you're reading this file, if you're not a Red gang member.
Feel free to explore the files of this project.

This is a full and complete rewrite of my oldest project, Captcher.
Where I wasn't satisfied with Captcher, I now can feel free to do things correctly in here.

This rewrite include a lot of copy-paste from https://github.com/retke/Laggrons-Dumb-Cogs.
Thanks for the code, it was very helpful and I'm learning always a little bit more. :)

It's so cool that I can write shit here without no one noticing on the bot!
IMABUTTEFLYJZIEOFJOIENAIUDBACZD
"""

# Builtin/pip related
import logging

# Discord/Red related
from redbot.core import commands, Config
from redbot.core.bot import Red
from redbot.core.utils.chat_formatting import humanize_list, warning
from redbot.core.i18n import Translator, cog_i18n

# Local
from .abc import CompositeMetaClass
from .commands.settings import Settings
from .commands.global_settings import OwnerCommands
from .event import Listeners
from .informations import __version__, __author__

log = logging.getLogger("red.predeactor.captcha")
_ = Translator("Captcha", __file__)


@cog_i18n(_)
class Base(
    Settings, OwnerCommands, Listeners, commands.Cog, name="Captcha", metaclass=CompositeMetaClass
):
    """A Captcha defensive system. Challenge the new users and protect yourself a bit more of raids."""

    def __init__(self, bot: Red) -> None:
        super().__init__()
        self.bot = bot
        self.data = Config.get_conf(None, identifier=495954056, cog_name="Captcha")
        # Must use cog_name this way, else the name could be "Base", which will be annoying later
        self.data.register_global(
            log_level=50  # According to the logging docs, we just remove the 0 to be easier.
        )
        self.data.register_guild(
            channel=None,  # The channel where the captcha is sent.
            logschannel=None,  # Where logs are sent.
            enabled=False,  # if challenges must be activated.
            autoroles=[],  # Roles to give.
            temprole=None,  # Temporary role to give
            type="PLAIN",  # Captcha type.
            timeout=5,  # Timeout before kicking.
        )
        self.user_challenge_class = {}
        # This dict will contain the user ID we're challenging, inside will be the associated
        # challenge class.

    def format_help_for_context(self, ctx: commands.Context) -> str:
        """
        This will put some text at the top of the main help. ([p]help Captcha)
        Thank to Sinbad.
        """
        pre_processed = super().format_help_for_context(ctx)
        return (
            _("{pre_processed}\n\nAuthor: {authors}\nVersion: {version}\n{additional}")
        ).format(
            pre_processed=pre_processed,
            authors=humanize_list(__author__),
            version=__version__,
            additional=warning(
                "This cog (Captcha) is in '{version}' version. You are kindly asked to unload "
                "this cog. You won't receive support for this cog. - Predeactor".format(
                    version=__version__
                )
            ),
        )

    async def initialize(self):
        log_level = await self.data.log_level()
        log.setLevel(log_level)
        log.info("Captcha logging level has been set to: {lev}".format(lev=log_level))
        log.debug(
            "Debug: This logging level is reserved for testing and monitoring purpose, set the "
            "level to 3 if you prefer to be alerted by less minor events or doesn't want to help "
            "debugging this cog."
        )
