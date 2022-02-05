#!/usr/bin/env python3

import discord
from discord.ext import commands
from discord.commands import Option


class Base_Bot(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print("Bot {} is ready.".format(self.bot.user))
        print("Debug guilds", self.bot.debug_guilds)

    @commands.Cog.listener()
    async def on_command_error(self, ctx: discord.ApplicationContext, error):
        self.send_and_print_str(ctx, "THERE WAS AN ERROR: {}".format(error))

    async def send_and_print_str(
        self,
        ctx: discord.ApplicationContext,
        string: str,
        **kwargs,
    ) -> discord.Interaction:
        """For debugging. Just prints whatever string content there was before passing it off to ctx.respond."""
        print(string)
        return await ctx.respond(string, **kwargs)

    def to_be_deleted(self, msg: discord.Message) -> bool:
        """Just a helper function to decide if a message was sent by this bot."""
        # delete anything done by the bot
        return msg.author.id == self.bot.user.id

    @commands.slash_command(
        name="purge_thread",
        description="Deletes all messages from this bot in a thread.",
    )
    async def purge_thread(self, ctx: discord.ApplicationContext):
        # input args aren't used, but they're here for the future
        channel = self.bot.get_channel(ctx.channel_id)
        if (
            channel.type != discord.ChannelType.public_thread
            and channel.type != discord.ChannelType.private_thread
        ):
            await ctx.respond("Sorry, this can only be done in a private thread.")
            return

        await ctx.channel.purge(limit=1000, check=self.to_be_deleted)

    @commands.message_command(
        name="Delete Message", description="Deletes the selected message."
    )
    async def delete_message(
        self, ctx: discord.ApplicationContext, message: discord.Message
    ):
        if self.to_be_deleted(message):
            await ctx.delete()
            await message.delete()

        else:
            await ctx.respond("Sorry, this message can't be deleted.")
