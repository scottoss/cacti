# Builtin or Pip
import asyncio
from contextlib import suppress
from enum import Enum
import logging
from random import SystemRandom
from string import ascii_uppercase, digits
from typing import Union


# Discord/Red related
import discord
from redbot.core import Config
from redbot.core.bot import Red
from redbot.core.i18n import cog_i18n, Translator
from redbot.core.utils.predicates import MessagePredicate, ReactionPredicate
from redbot.core.utils.chat_formatting import box, warning, bold, humanize_list

# Local
from .abc import ChallengeMixinMeta
from .captchagenerator import WheezyCaptcha, ImageCaptcha, available_options
from .errors import NonInitializedError, AlreadyRunningError, RoleNotFoundError, NonEnabledError
from .informations import __version__ as captcha_version

log = logging.getLogger("red.predeactor.captcha")
ESCAPE_CHAR = "\u200B"
_ = Translator("Captcha", __file__)


# noinspection PyUnresolvedReferences
class CaptchaTask(ChallengeMixinMeta):
    async def wait_user_action(self) -> tuple:
        """
        Wait for the user to do something with the captcha, either reacting or answering the
        captcha.

        Return
        ------
        tuple:
            A tuple containing which kind of event has been completed and his result.
            The kind of even can be either ``reaction`` or ``message``.

        Raises
        ------
        TimeoutError:
            If no task has been completed in the time.
        """
        log.debug(f"{self.member.name} - {self.guild.id} ({self.guild.name}) - Preparing tasks.")
        self.tasks = [
            asyncio.create_task(
                self.useless_storage["bot"].wait_for(
                    "reaction_add",
                    check=ReactionPredicate.with_emojis(
                        "🔁", message=self.messages["bot_challenge"], user=self.member
                    ),
                )
            ),
            asyncio.create_task(
                self.useless_storage["bot"].wait_for(
                    "message",
                    check=MessagePredicate.same_context(
                        channel=self.channel
                        if not self.channel == "dm"
                        else self.member.dm_channel,
                        user=self.member,
                    ),
                )
            ),
        ]

        done = None
        try:
            log.debug(
                f"{self.member.name} - {self.guild.id} ({self.guild.name}) - Task ongoing. "
                f"Timeout: {self.useless_storage['timeout'] * 60}"
            )
            done, pending = await asyncio.wait(
                self.tasks,
                timeout=self.useless_storage["timeout"] * 60,
                return_when=asyncio.FIRST_COMPLETED,
            )
        except asyncio.CancelledError:
            # In case the tasks got cancelled in the meantime.
            log.debug(
                f"{self.member.name} {self.guild.id} ({self.guild.name}) - A task have been "
                "cancelled or all tasks have been cancelled."
            )
            if not done:
                log.debug("'done', 'pending' = (), ()")
                done, pending = (), ()
        else:
            # Cancels the tasks, we had an answer.
            log.debug(
                f"{self.member.name} {self.guild.id} ({self.guild.name}) - Cleaning up tasks."
            )
            await self.cancel_tasks()
        if len(done) == 0:
            # No tasks has been realized by the user.
            log.debug(
                f"{self.member.name} {self.guild.id} ({self.guild.name}) - No task have been "
                "realized, raising InterruptedError."
            )
            raise InterruptedError()
        result = done.pop().result()

        # Now that we know a task has been made, we determine it.
        task_type = "message" if hasattr(result, "content") else "reaction"
        # We add the user's message in the messages for deletion later.
        if task_type == "message":
            self.messages["answer"] = result
        return task_type, result

    async def cancel_tasks(self) -> None:
        """
        Cancels the ongoing tasks if running.
        """
        for task in self.tasks:
            task.cancel()
            log.debug
        log.debug("Tasks cancelled.")

    def running(self):
        """
        Return if there's tasks running.
        """
        if self.tasks:
            return True
        return False


@cog_i18n(_)
class Challenge(CaptchaTask):
    """Represent an on-going challenge."""

    def __init__(self, member: discord.Member):
        super().__init__()
        self.initialized = False

        self.member = member
        self.guild = member.guild
        self.data = Config.get_conf(None, identifier=495954056, cog_name="Captcha").guild_from_id(
            self.guild.id
        )
        self.tasks = []

        self.channel = None

        self.messages = {}
        # Container for all messages:
        # bot_challenge: Bot challenge, include captcha
        # answer: Member answer
        # bot_answer: Bot answer to captcha
        self.useless_storage = {}
        # bot: Red
        # timeout: Timeout to use for waiting
        # guild_settings: Server config
        # captcha_class: Captcha class

    async def initialize(self, bot: Red):
        """Initialize the challenge. Must be done first in any case.
        This will also give a temporary role if the guild set one.

        Parameters
        ----------
        bot: Red
            THe instance of Red, required for fetching channels.

        Raises
        ------
        AttributeError
            In case a channel wasn't found.
        """
        log.debug(f"{self.member.name} {self.guild.id} ({self.guild.name}) - Obtaining config.")
        settings = await self.data.all()
        self.useless_storage["guild_config"] = settings

        if not settings["enabled"]:
            log.debug(
                f"{self.member.name} {self.guild.id} ({self.guild.name}) - Captcha non enabled."
            )
            raise NonEnabledError(_("This guild didn't enabled Captcha."))

        channel_id = settings["channel"]
        if channel_id != "dm":
            channel = bot.get_channel(channel_id)
            if not channel:
                log.debug(
                    f"{self.member.name} {self.guild.id} ({self.guild.name}) - Channel not found "
                    ", raising AttributeError."
                )
                raise AttributeError(
                    _("Channel does not existing, is not set or cannot be found.")
                )
            self.channel = channel
        else:
            self.channel = self.member
        if logschannel_id := settings["logschannel"]:
            logschannel = bot.get_channel(logschannel_id)
            if not logschannel:
                log.debug(
                    f"{self.member.name} {self.guild.id} ({self.guild.name}) - Logs channel not "
                    "found, ignoring."
                )
                pass
        if role_id := settings["temprole"]:
            log.debug(
                f"{self.member.name} {self.guild.id} ({self.guild.name}) - Obtaining temporary "
                "role."
            )
            role = await self.guild.get_role(role_id)
            if not role:
                log.debug(
                    f"{self.member.name} {self.guild.id} ({self.guild.name}) - Temporary role not"
                    "found, raising RoleNotFoundError."
                )
                raise RoleNotFoundError(_("The temporary role that has been sent was not found."))
            try:
                await self.member.add_roles(
                    role, reason=_("Temporary role given by Captcha module")
                )
                log.debug(
                    f"{self.member.name} {self.guild.id} ({self.guild.name}) - Temporary role "
                    "gived."
                )
            except discord.Forbidden:
                log.debug(
                    f"{self.member.name} {self.guild.id} ({self.guild.name}) - Impossible to "
                    "give temporary role, raisong PermissionError."
                )
                raise PermissionError(_("Cannot assign temporary role."))

        self.useless_storage["type"] = settings["type"]
        self.useless_storage["bot"] = bot
        self.useless_storage["timeout"] = settings["timeout"]
        self.initialized = True

    async def start_challenge(self) -> None:
        """
        Start the challenge for the user and send a message. Must be looped with the function
        "looper".
        """
        if not self.initialized:
            # No idea why those happens
            # noinspection PyUnboundLocalVariable
            raise NonInitializedError(_("Captcha class is not initialized."))
        if self.running():
            # noinspection PyUnboundLocalVariable
            raise AlreadyRunningError(_("A Captcha challenge is already running."))

        captcha_class = getattr(CaptchaType, self.useless_storage["type"])  # Obtain class, yay
        self.useless_storage["captcha_class"] = captcha_class.value
        code = "".join(SystemRandom().choice(ascii_uppercase + digits) for _ in range(8))

        captcha_stuff = await captcha_class.value.generate(code, self.guild)

        bot_message: discord.Message = await self.channel.send(
            embed=captcha_stuff[0], file=captcha_stuff[1]
        )
        self.messages["bot_challenge"] = bot_message
        await bot_message.add_reaction("🔁")

    async def looper(self) -> bool:
        is_right = None
        while is_right is not True:
            try:
                inputing = await self.wait_user_action()
            except asyncio.TimeoutError:
                break
            is_right = await self.take_action(inputing)
            if is_right is False:
                await self.channel.send(_("Input incorrect, try again."), delete_after=10)
                try:
                    await self.messages["answer"].delete()
                except discord.Forbidden:
                    pass
        if is_right:
            self.messages["bot_answer"] = await self.channel.send(
                _("You have completed the challenge."), delete_after=10
            )
            return True
        self.messages["bot_answer"] = await self.channel.send(_("How sad."), delete_after=10)
        return False

    async def take_action(self, result: tuple):
        """
        Take action accordingly to the result.
        """
        if result[0] == "reaction":
            await self.reload_captcha()
            return None
        message = result[1]
        captcha_class = self.useless_storage["captcha_class"]
        resulting = await captcha_class.verify_input(message.content.upper())
        if isinstance(resulting, str):
            await message.channel.send(resulting, delete_after=10)
            return None
        return resulting

    async def reload_captcha(self) -> None:
        """
        Reload the captcha and do again all the shit...
        """
        if not self.initialized:
            raise NonInitializedError()

        await self.messages["bot_challenge"].delete()

        captcha_class = self.useless_storage["captcha_class"]
        code = "".join(SystemRandom().choice(ascii_uppercase + digits) for _ in range(8))
        captcha_stuff = await captcha_class.generate(code, self.guild)
        bot_message: discord.Message = await self.channel.send(
            embed=captcha_stuff[0], file=captcha_stuff[1]
        )
        self.messages["bot_challenge"] = bot_message
        await bot_message.add_reaction("🔁")

    async def handle_role(self) -> str:
        """Function to give and/or remove role from member.
        This will automatically grab roles from server's config.

        Returns
        -------
        str
            A text explaining what has been done, to send in logs.

        Raises
        ------
        discord.Forbidden
            Missing permissions to do role handling.
        """
        list_to_add = self.useless_storage["guild_config"]["autoroles"]
        to_remove = self.useless_storage["guild_config"]["temprole"]
        actions = []
        with suppress(discord.Forbidden):
            if list_to_add:
                for role in list_to_add:
                    to_add = self.member.guild.get_role(role)
                    await self.member.add_roles(to_add, reason=_("Autorole by Captcha."))
                if len(list_to_add) > 1:
                    actions.append(_("added automatically role"))
                else:
                    actions.append(_("added automatically roles"))
            if to_remove:
                to_remove = self.member.guild.get_role(to_remove)
                if to_remove in self.member.roles:
                    await self.member.remove_roles(
                        to_remove, reason=_("Removing temporary role by Captcha.")
                    )
                    actions.append(_("removed temporary role"))
        return humanize_list(actions).capitalize() if actions else _("No action taken.")

    async def cleanup(self):
        """
        Cleaning up the useless and not used anymore.
        """
        await self.cancel_tasks()
        with suppress(discord.Forbidden):
            for message in self.messages.items():
                await message[1].delete()
        self.running()


class WheezyCaptchaGen:
    def __init__(self):
        self.code = None
        self.image = None

    async def generate(self, code: str, guild: discord.Guild) -> tuple:
        """
        Create the captcha and his embed.

        Parameters
        ----------
        code: str
            The code that we will use in the Captcha.

        guild: discord.Guild
            The guild we are sending the Captcha in.

        Returns
        -------
        tuple
            A tuple containing the embed and the image to send as the message attachment.
        """
        self.code = code
        captcha_class = WheezyCaptcha(width=350, height=100)
        self.image = captcha_class.generate(code)
        embed = discord.Embed(
            title=_("{guild_name} Verification System").format(guild_name=guild.name),
            description=_(
                "Please send me back the code you're seeing in this image.\nClick on 🔁 to get "
                "another image.\nNote: This captcha does not include space and is made of 8 "
                "characters. In case you're missing one, reload the captcha."
            ),
        )
        embed.set_image(url="attachment://" + "captcha.png")
        embed.set_footer(
            text=_("You are challenging version: {vers}").format(vers=captcha_version),
            icon_url="https://cdn.discordapp.com/emojis/594238096934043658.png",
        )
        return embed, discord.File(self.image, filename="captcha.png")

    async def verify_input(self, user_input: str):
        if user_input != self.code:
            return False
        return True


class PlainCaptchaGen:
    def __init__(self):
        self.code = None
        self.code_with_escaping = None

    async def generate(self, code: str, guild: discord.Guild) -> tuple:
        """
        Create the captcha and his embed.

        Parameters
        ----------
        code: str
            The code that we will use in the Captcha.

        guild: discord.Guild
            The guild we are sending the Captcha in.

        Returns
        -------
        tuple
            A tuple containing embed and None, to facilitate my life with other Captcha types.
        """
        self.code = code
        self.code_with_escaping = ESCAPE_CHAR.join(self.code)
        embed = discord.Embed(
            title=_("{guild_name} Verification System").format(guild_name=guild.name),
            description=_(
                "Please return me the following code:\n{code}\nDo not copy and paste the code."
            ).format(code=box(self.code_with_escaping)),
        )
        embed.set_footer(
            text=_("You are challenging version: {vers}").format(vers=captcha_version),
            icon_url="https://cdn.discordapp.com/emojis/594238096934043658.png",
        )
        return embed, None

    async def verify_input(self, user_input: str) -> Union[bool, str]:
        """
        A verificator that check a given input.

        Parameters
        ----------
        user_input: str
            The user answer to the captcha, this is what we compare to the code.

        Returns
        -------

        """
        if user_input == self.code_with_escaping:
            return warning(
                bold("I asked you to NOT copy and paste the code. Retry without copying.")
            )
        escaped_user_text = user_input.replace(ESCAPE_CHAR, "")
        if escaped_user_text != self.code:
            return False
        return True


class ImageCaptchaGen:
    def __init__(self):
        self.code = None
        self.image = None

    async def generate(self, code: str, guild: discord.Guild) -> tuple:
        """
        Create the captcha and his embed.

        Parameters
        ----------
        code: str
            The code that we will use in the Captcha.

        guild: discord.Guild
            The guild we are sending the Captcha in.

        Returns
        -------
        tuple
            A tuple containing the embed and the image to send as the message attachment.
        """
        self.code = code
        captcha_class = ImageCaptcha(width=350, height=100)
        self.image = captcha_class.generate(self.code)
        embed = discord.Embed(
            title=_("{guild_name} Verification System").format(guild_name=guild.name),
            description=_(
                "Please send me back the code you're seeing in this image. Click on 🔁 to get "
                "another image."
            ),
        )
        embed.set_image(url="attachment://" + "captcha.png")
        embed.set_footer(
            text=_("You are challenging version: {vers}").format(vers=captcha_version),
            icon_url="https://cdn.discordapp.com/emojis/594238096934043658.png",
        )
        return embed, discord.File(self.image, filename="captcha.png")

    async def verify_input(self, user_input: str) -> bool:
        if user_input != self.code:
            return False
        return True


class CaptchaType(Enum):
    PLAIN = PlainCaptchaGen()
    IMAGE = ImageCaptchaGen()
    if "WheezyCaptcha" in available_options:
        WHEEZY = WheezyCaptchaGen()
