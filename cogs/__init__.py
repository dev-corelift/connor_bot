"""Cog registration."""

from __future__ import annotations

from discord.ext import commands

from .admin import AdminCog
from .content import ContentCog
from .core import CoreCog
from .knowledge import KnowledgeCog
from .thoughts import ThoughtsCog
from .voice import VoiceCog
from .music import MusicCog
from .moderation import ModerationCog


def register_cogs(bot: commands.Bot) -> None:
    bot.add_cog(CoreCog(bot))
    bot.add_cog(ContentCog(bot))
    bot.add_cog(ThoughtsCog(bot))
    bot.add_cog(KnowledgeCog(bot))
    bot.add_cog(VoiceCog(bot))
    bot.add_cog(MusicCog(bot))
    bot.add_cog(AdminCog(bot))
    bot.add_cog(ModerationCog(bot))
