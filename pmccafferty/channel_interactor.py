from enum import Enum

import discord
from discord.ext.commands import Bot
from discord.ext.commands.context import Context

import util.string as StringHelper
from util import logger

#############
# Constants #
#############
GAME_CHANNEL_QUIZ = "quiz"
GAME_CHANNEL_HANGMAN = "hangman"
GAME_CHANNEL_QUIZ_DEFAULT_NAME = "bible-quizzing"
GAME_CHANNEL_HANGMAN_DEFAULT_NAME = "bible-hangman"


##################
# Helper Classes #
##################
class ChannelType(Enum):
    TEXT = 1
    VOICE = 2


####################
# Helper Functions #
####################

#########
# Async #
#########
async def check_channel_exists(bot: Bot, guild_name: str, context: Context, game: str, channel_name: str) -> bool:
    existing_text_channels = []
    for guild in bot.guilds:
        if guild.name == guild_name:
            existing_text_channels = [str(channel.name) for channel in guild.text_channels]

    if channel_name not in existing_text_channels:
        logger.d("Channel {0} did not exist for {1}".format(channel_name, game))
        await send_message(context, "Channel for {0} does not exist yet.\nPlease use $setup or $h for further help.".format(game))
        return False

    return True


async def create_channel(context: Context, channelType: ChannelType, channel_name: str):
    guild = context.message.guild
    if channelType == ChannelType.TEXT:
        logger.d("Creating new text channel...")
        channel_name = ensure_valid_channel_name(channelType, channel_name)
        await guild.create_text_channel(channel_name)
        logger.d("New text channel named {0} created successfully".format(channel_name))
    elif channelType == ChannelType.VOICE:
        logger.d("Creating new voice channel...")
        channel_name = ensure_valid_channel_name(channelType, channel_name)
        await guild.create_voice_channel(channel_name)
        logger.d("New voice channel named {0} created successfully".format(channel_name))
    else:
        logger.e("Should not have reached this point. Something is broken")
        await send_message(context, "Unsure how this is even being printed. Something is broken. Info: channelType={0}, channel_name={1}".format(channelType, channel_name))


async def delete_message(message, word):
    await message.delete()
    logger.i("User {0} tried to use the banned word \"{1}\"".format(str(message.author).split("#")[0], word))
    response = "{0} no swearing while I'm around.".format(message.author.mention)
    await send_message(message, response)


async def filter_message(message, swear_words: list):
    for word in swear_words:
        if word in message.content.lower():
            if StringHelper.is_banned_word(swear_words, word, message.content.lower()):
                await delete_message(message, word)
                break


async def is_correct_channel(context: Context, game, channel_name: str) -> bool:
    current_channel = context.channel.name
    if current_channel != channel_name:
        await send_message(context, "{0} this is not the channel for {1}!".format(context.author.mention, game))
        return False
    return True


async def send_message(message, msg):
    await message.channel.send(msg, allowed_mentions=discord.AllowedMentions().all())


##############
# Non-Async #
#############
def ensure_valid_channel_name(channelType: ChannelType, channel_name: str) -> str:
    if channelType == ChannelType.TEXT:
        channel_name = channel_name.lower().replace(" ", "-")
    elif channelType == ChannelType.VOICE:
        channel_name = channel_name
    return channel_name
