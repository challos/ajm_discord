# ajm_discord
A collection of several cogs for Discord bots with a few common methods/commands. Specifically for use with the [Pycord](https://github.com/Pycord-Development/pycord) API.

Install the current version with [PyPI](https://pypi.org/project/clubhouse-api/):

```bash
pip install ajm_discord
```

# Cogs

## BaseCog
Intentionally sparse cog, just contains an easy way to log and send messages.

## ListenerCog
Cog for listeners. Only the on_ready one does anything at the moment, really. TODO

## DeleteCog
Cog for deleting bot messages in bulk on the user side, and for users to be able to delete bot messages without permissions.

## TextCog
Cog for retrieving text. Specifically from Discord threads. Can retrieve text from .txt files, Discord messages, Discord embeds, Microsoft Word documents, and google doc links. Can also convert images/image links to markdown for ease of use.