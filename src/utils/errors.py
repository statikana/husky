from discord.ext import commands


class HuskyError(Exception):
    """Base class for exceptions in this module."""

    pass


class InternalError(HuskyError):
    """Exception raised for errors in the internal logic of the bot.
    Never an issue with user-input, but rather a bug in the code."""


class InvalidMediaFormat(HuskyError):
    """The format of your attachment was invalid. Make sure the
    extension of the file is one of the accepted values."""


class InvalidMediaSize(HuskyError):
    """The size of your attachment was too big."""


class AmbiguousCommandName(HuskyError):
    def __init__(self, found_commands: list[commands.Command]):
        self.found_commands = found_commands

    """The command you called does not exist, so I tried to find a
    command that was similar to the one you called. However, I found
    multiple commands that were similar, so I don't know which one
    you wanted to use. Please try again with a more specific command.
    """
