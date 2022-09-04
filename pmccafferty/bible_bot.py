# -*- coding: utf-8 -*-
"""
Created on Wed Aug 24 04:35:00 2022

@author: Paul McCafferty
@version: 11.57
"""
import asyncio
import operator
import os
import sys
from typing import List

import pyrebase
import discord
from discord.channel import TextChannel
from discord.ext import commands
from discord.ext.commands.context import Context
from discord.role import Role
from dotenv import load_dotenv

import channel_interactor as ChannelInteractor
import util.string as StringHelper
import util.time as TimeHelper
import verse_interactor as VerseInteractor
from channel_interactor import ChannelType
from firebase_interactor import FirebaseInteractor, FIREBASE_CONFIG
from hangman_game import Hangman, HANGMAN_PREFILL_LEVEL_NONE
from quiz_game import Quiz
from util import logger

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
INVALID_GUILD_ERROR_CODE = 600
RUNNING_DEBUGGER = False

if not RUNNING_DEBUGGER:
    try:
        args = sys.argv[1:]
        GUILD = args[0]
        for i in range(1, len(args)):
            GUILD = "{0} {1}".format(GUILD, args[i])
        logger.d("Attempting bot login to guild={0}".format(GUILD))
    except Exception as error:
        GUILD = ""
        logger.e("Was unable to launch the bot. More information printed below.")
        logger.e(error)
        logger.d("Exiting with code {0}".format(INVALID_GUILD_ERROR_CODE))
        exit(INVALID_GUILD_ERROR_CODE)
else:
    GUILD = "Squeeze"

#############
# Constants #
#############
# Supported times: 5s, 10s, 15s, 30s, 1m, 2m, 5m, 10m, 15m, 30m, 1h, 2h, 6h
DISCORD_SUPPORTED_TIMES = ["5s", "10s", "15s", "30s", "1m", "2m", "5m", "10m", "15m", "30m", "1h", "2h", "6h"]


########
# init #
########
intents = discord.Intents().all()
bot = commands.Bot(command_prefix=commands.when_mentioned_or("$"), intents=intents)
firebase = pyrebase.initialize_app(FIREBASE_CONFIG)
database = firebase.database()
guild_string_ref = StringHelper.quick_hash(GUILD, 5, 15)
firebase_interactor = FirebaseInteractor(database, guild_string_ref)


#############
# Variables #
#############
swear_words = [line.split("\n")[0] for line in open("data/swear_words.txt", "r").readlines()]
operators = {"+": operator.add, "-": operator.sub, "*": operator.mul, "/": operator.truediv, "^": operator.pow}
excluded_quiz_words = [line.split("\n")[0] for line in open("data/excluded_quiz_words.txt", "r").readlines()]
quiz = Quiz(bot, GUILD, excluded_quiz_words, firebase_interactor)
hangman = Hangman(bot, GUILD)
server_napping = False
time_remaining = 0


##############
# Bot events #
##############
@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name="$h | $[command]"))
    logger.i('Successfully logged into {0} as {1}'.format(GUILD, bot.user))


@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if message.guild.name == GUILD:
        ChannelInteractor.update_message_log(GUILD, message)
        await ChannelInteractor.filter_message(message, swear_words)
        await bot.process_commands(message)
        if str(message.author) in quiz.players:
            await quiz.check_answer(message, message.content)
        elif "bro =" == message.content.lower():
            await ChannelInteractor.send_message(message, "Wassup homie")


################
# Bot commands #
################
@bot.command(
    name="h",
    help="Provides help on all the commands available by printing out the descriptions for each.",
    brief="Provides help on all the commands available."
)
async def print_help(context: Context):
    header_text = "Help Format Explanation: Words in straight brackets [] are required, words in parenthesis () are optional."
    h_help_text = "$h\nProvides help on all the commands available by printing out the descriptions for each."
    setup_help_text = "$setup (quiz/hangman) (channel-name)\nUse this command with the game you want to setup and which channel to link it to. Is provided with default values of \"bible-quiz-game\" and \"bible-hangman-game\"."
    dailyvotd_help_text = "$dailyvotd [time]\nPrints the Verse of the Day every day at a consistent time. Using again while active turns it off."
    votd_help_text = "$votd\nPrints the Verse of the Day that was fetched from online."
    lookup_help_text = "$lookup [book] [chapter:verse] (book_num)\nLooks up and prints out the verse that was searched."
    rlookup_help_text = "$rlookup\nLooks up and prints out a random verse."
    keywords_help_text = "$keywords [word]\nTakes in any amount of words and searches online for the top related verse to print out as a response."
    quiz_help_text = "$quiz [ref/word/sentence/rating/streak/games] (book)\nSends a random verse with either the reference, a single word, or a sentence missing for the user to solve."
    hangman_help_text = "$hangman [easy/medium/hard/status/quit] (none/low/medium/high)\nUsing hangman starts a game. Three modes, status and quit are the accepted arguments. Change prefill with secondary option."
    hguess_help_text = "$hguess [guess]\nUsed to submit a guess to an ongoing hangman puzzle for the message sender."
    math_help_text = "$math [number_a] [operator] [number_b]\nProvided two numbers and a method of operation, the bot will produce the result. Supported operators: +, -, *, /, ^"
    naptime_help_text = "$naptime (number) (seconds/minutes/hours)\nPuts all channels in slowmode for a specified period of time. Only the options which Discord allow are acceptable." \
                        "\nSupported times: 5s, 10s, 15s, 30s, 1m, 2m, 5m, 10m, 15m, 30m, 1h, 2h, 6h"
    napcheck_help_text = "$napcheck\nPrints out the time remaining for the nap."
    napend_help_text = "$napend\nEnds the current server nap."
    help_text = "```{0}\n\n{1}\n\n{2}\n\n{3}\n\n{4}\n\n{5}\n\n{6}\n\n{7}\n\n{8}\n\n{9}\n\n{10}\n\n{11}\n\n{12}\n\n{13}\n\n{14}```".format(
        header_text, h_help_text, setup_help_text, dailyvotd_help_text, votd_help_text,
        lookup_help_text, rlookup_help_text, keywords_help_text, quiz_help_text,
        hangman_help_text, hguess_help_text, math_help_text, naptime_help_text,
        napcheck_help_text, napend_help_text
    )
    await ChannelInteractor.send_message(context, help_text)


@bot.command(
    name="setup",
    help="Use this command with the game you want to setup and which channel to link it to. Is provided with default values of \"bible-quizzing\" and \"bible-hangman\".",
    brief="Set specific channels for the games."
)
async def setup_game_channels(context: Context, game: str = None, channel_name: str = None):
    if game is None or channel_name is None:
        await ChannelInteractor.send_message(context, "No game and/or channel name specified. Setting both channels back to default.")
        quiz.set_game_channel(ChannelInteractor.GAME_CHANNEL_QUIZ_DEFAULT_NAME)
        hangman.set_game_channel(ChannelInteractor.GAME_CHANNEL_HANGMAN_DEFAULT_NAME)

        existing_text_channels = []
        for guild in bot.guilds:
            if guild.name == GUILD:
                existing_text_channels = [str(channel.name) for channel in guild.text_channels]

        if quiz.game_channel_name not in existing_text_channels:
            logger.d("Channel {0} did not exist. Creating...".format(channel_name))
            await ChannelInteractor.create_channel(context, ChannelType.TEXT, ChannelInteractor.GAME_CHANNEL_QUIZ_DEFAULT_NAME)
        if hangman.game_channel_name not in existing_text_channels:
            logger.d("Channel {0} did not exist. Creating...".format(channel_name))
            await ChannelInteractor.create_channel(context, ChannelType.TEXT, ChannelInteractor.GAME_CHANNEL_HANGMAN_DEFAULT_NAME)
    else:
        if game != "hangman" and game != "quiz":
            await ChannelInteractor.send_message(context, "That game currently does not exist.")
        else:
            logger.d("Setting channel for {0} to {1}".format(game, channel_name))
            update_game_channel_name(game, channel_name)
            existing_text_channels = []
            for guild in bot.guilds:
                if guild.name == GUILD:
                    existing_text_channels = [str(channel.name) for channel in guild.text_channels]

            if channel_name not in existing_text_channels:
                logger.d("Channel {0} did not exist. Creating...".format(channel_name))
                await ChannelInteractor.create_channel(context, ChannelType.TEXT, channel_name)

            await ChannelInteractor.send_message(context, "Set {0} to be played in {1}".format(game, channel_name))


@bot.command(
    name="dailyvotd",
    help="Prints the Verse of the Day every day at a consistent time. Using again while active turns it off.",
    brief="Puts the bot on a timer for sending the daily VOTD."
)
async def send_daily_verse_of_the_day(context: Context, time: str = None):
    if time is None:
        await ChannelInteractor.send_message(context, "Please provide a time.")
    else:
        converted_time = StringHelper.convert_twenty_four_to_twelve(time)
        response = "Will now send the VOTD daily at {0}.".format(converted_time)
        await ChannelInteractor.send_message(context, response)
        await ChannelInteractor.send_message(context, "Oops, it seems this command is not finished yet!\nVerse will not be sent ;-;")


@bot.command(
    name="votd",
    help="Prints the Verse of the Day that was fetched from online.",
    brief="Prints the Verse of the Day."
)
async def send_verse_of_the_day(context: Context):
    votd = VerseInteractor.get_votd_from_url()
    await ChannelInteractor.send_message(context, StringHelper.remove_html_tags(votd))


@bot.command(
    name="lookup",
    help="Looks up and prints out the verse that was searched.",
    brief="Looks up verse and prints it."
)
async def lookup_verse(context: Context, book: str = None, chapter_verse: str = None, book_num: str = None):
    await VerseInteractor.lookup_verse(context, book, chapter_verse, book_num)


@bot.command(
    name="rlookup",
    help="Looks up and prints out a random verse.",
    brief="Prints random verse."
)
async def verse_lookup_random(context: Context):
    random_verse = VerseInteractor.get_random_verse()
    await ChannelInteractor.send_message(context, random_verse)


@bot.command(
    name="keywords",
    help="Takes in any amount of words and searches online for the top related verse to print out as a response.",
    brief="Search online for entered text."
)
async def search_keywords(context: Context, *, keyword: str = None):
    await VerseInteractor.search_keywords(context, keyword)


@bot.command(
    name="quiz",
    help="Sends a random verse with either the reference, a single word, or a sentence missing for the user to solve. User can select book.",
    brief="Quizzes the user on a random verse."
)
async def bible_quizzing(context: Context, option: str = None, *, book: str = None):
    await quiz.start_game(context, option, book)


@bot.command(
    name="hangman",
    help="Using hangman starts a game. Three modes, status and quit are the accepted arguments. Change prefill with secondary option.",
    brief="Plays hangman with the user."
)
async def play_hangman(context: Context, option: str = None, prefill_level: str = HANGMAN_PREFILL_LEVEL_NONE):
    await hangman.start_game(context, option, prefill_level)


@bot.command(
    name="hguess",
    help="Used to submit a guess to an ongoing hangman puzzle for the message sender.",
    brief="Submit a guess to ongoing hangman puzzle."
)
async def submit_hangman_guess(context: Context, guess: str = None):
    await hangman.submit_guess(context, guess)


@bot.command(
    name="math",
    help="Provided two numbers and a method of operation, the bot will produce the result.",
    brief="Give two number and an operator, get result."
)
async def do_math(context: Context, num_one: float = None, op: str = None, num_two: float = None):
    if num_one is None or op is None or num_two is None:
        await ChannelInteractor.send_message(context, "Cannot perform math operations without all the necessary parts.")
    else:
        answer = operators[op](num_one, num_two)
        await ChannelInteractor.send_message(context, "Answer: {0}".format(answer))


@bot.command(
    name="naptime",
    help="Puts all channels in slowmode for a specified period of time. Only the options which Discord allow are acceptable.",
    brief="Puts all channels in slowmode."
)
async def take_nap(context: Context, time_count: int = 1, time_unit: str = "hour"):
    # Technically although I only want to use those values in DISCORD_SUPPORTED_TIMES, they accept any seconds value from 1-21600
    can_use_command = can_user_use_command(context)
    if not can_use_command:
        logger.d("User {0} tried to use the $naptime command".format(context.author))
        await ChannelInteractor.send_message(context, "{0} you're not high enough on the role heirarchy to use that command.".format(context.author.mention))
        return

    global server_napping
    global time_remaining
    if server_napping:
        await ChannelInteractor.send_message(context, "Server is already taking a nap! ")
        return

    time_unit = time_unit[0]
    if "{0}{1}".format(str(time_count), time_unit) not in DISCORD_SUPPORTED_TIMES:
        await ChannelInteractor.send_message(context, "Time entered is unsupported by Discord.")
        return

    logger.d("Setting all channels to slowmode for {0}{1}. Initiated by {2}".format(time_count, time_unit, context.author))
    await ChannelInteractor.send_message(context, "Setting all channels to slowmode for {0}{1}".format(time_count, time_unit))
    server_napping = True

    discord_time_ms = TimeHelper.convert_discord_time_to_ms(time_count, time_unit)
    for guild in bot.guilds:
        if guild.name == GUILD:
            for text_channel in guild.text_channels:
                channel: TextChannel = text_channel
                await channel.edit(slowmode_delay=(discord_time_ms / 1000))

    time_remaining = discord_time_ms
    while time_remaining > 0 and server_napping:
        await asyncio.sleep(0.9)
        time_remaining -= 1000

    server_napping = False

    for guild in bot.guilds:
        if guild.name == GUILD:
            for text_channel in guild.text_channels:
                channel: TextChannel = text_channel
                await channel.edit(slowmode_delay=0)


@bot.command(
    name="napcheck",
    help="Prints out the time remaining for the nap.",
    brief="Returns how much nap time remains."
)
async def get_remaining_nap_time(context: Context):
    if not server_napping:
        await ChannelInteractor.send_message(context, "Server isn't taking a nap currently.")
    else:
        logger.d(time_remaining)
        str_time_remaining = TimeHelper.convert_ms_to_time(time_remaining)
        logger.d(str_time_remaining)
        await ChannelInteractor.send_message(context, "Remaining time of nap: {0}".format(str_time_remaining))


@bot.command(
    name="napend",
    help="Ends the current server nap.",
    brief="End current nap."
)
async def end_server_nap(context: Context):
    can_use_command = can_user_use_command(context)
    if not can_use_command:
        logger.d("User {0} tried to use the $napend command".format(context.author))
        await ChannelInteractor.send_message(context, "{0} you're not high enough on the role heirarchy to use that command.".format(context.author.mention))
        return

    global server_napping
    server_napping = False
    logger.d("Server nap was ended by {0}".format(context.author))


####################
# Helper functions #
####################

#########
# Async #
#########
async def can_user_use_command(context: Context) -> bool:
    can_use_command = False
    user = context.author
    if await bot.is_owner(user):
        can_use_command = True

    if not can_use_command:
        roles: List[Role] = user.roles
        for role in roles:
            role_name = role.name.lower()
            if role.permissions.administrator:
                can_use_command = True
                break
            elif role_name == "mod" or role_name == "admin":
                can_use_command = True
                break

    return can_use_command


#############
# Non-Async #
#############
def update_game_channel_name(game: str, channel_name: str):
    if game == quiz.game_name:
        quiz.set_game_channel(channel_name)
    elif game == hangman.game_name:
        hangman.set_game_channel(channel_name)
    else:
        logger.e("Invalid game option provided")


bot.run(TOKEN)
