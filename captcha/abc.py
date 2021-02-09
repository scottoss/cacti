from abc import ABC, abstractmethod
from typing import Optional, Union

import discord
from redbot.core import Config
from redbot.core.bot import Red
from redbot.core.commands import Cog


class MixinMeta(ABC):
    def __init__(self, *_args):
        self.bot: Red

        self.data: Config
        self.running: dict

        self.version: str
        self.patchnote: str
        self.patchnoteconfig: Config

    @abstractmethod
    async def send_or_update_log_message(
        self,
        guild: discord.Guild,
        message_content: str,
        message_to_update: Optional[discord.Message] = None,
        *,
        member: discord.Member = None,
        file: discord.File = None,
        embed: discord.Embed = None,
    ):
        raise NotImplementedError()

    @abstractmethod
    def create_challenge_for(self, member: discord.Member):
        raise NotImplementedError()

    @abstractmethod
    def delete_challenge_for(self, member: Union[discord.Member, int]) -> bool:
        raise NotImplementedError()

    @abstractmethod
    def is_running_captcha(self, user_or_id: Union[discord.Member, int]):
        raise NotImplementedError()

    @abstractmethod
    def _initialize(self, send_patchnote: bool = True):
        raise NotImplementedError()


class CompositeMetaClass(type(Cog), type(ABC)):
    """
    Allows the metaclass used for proper type detection to coexist with discord.py's metaclass.
    Credit to https://github.com/Cog-Creators/Red-DiscordBot (mod cog) for all mixin stuff.
    Credit to the top of the file "base.py".
    """

    pass
