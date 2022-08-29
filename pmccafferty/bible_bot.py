# -*- coding: utf-8 -*-
"""
Created on Wed Aug 24 04:35:00 2022

@author: Paul McCafferty
@version: 7.41
"""
import operator
import os

import discord
from discord.ext import commands
from discord.ext.commands.context import Context
from dotenv import load_dotenv

import channel_interactor as ChannelInteractor
import util.string as StringHelper
import verse_interactor as VerseInteractor
from channel_interactor import ChannelType
from hangman_game import Hangman, HANGMAN_PREFILL_LEVEL_NONE
from quiz_game import Quiz
from util import logger

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_EBC = os.getenv("DISCORD_EBC_GUILD")
GUILD_SQUEEZE = os.getenv("DISCORD_SQUEEZE_GUILD")
# GUILD = GUILD_SQUEEZE
GUILD = GUILD_EBC

intents = discord.Intents().all()
bot = commands.Bot(command_prefix=commands.when_mentioned_or("$"), intents=intents)

#############
# Variables #
#############
swear_words = [line.split("\n")[0] for line in open("data/swear_words.txt", "r").readlines()]
operators = {"+": operator.add, "-": operator.sub, "*": operator.mul, "/": operator.truediv, "^": operator.pow}
excluded_quiz_words = [line.split("\n")[0] for line in open("data/excluded_quiz_words.txt", "r").readlines()]
quiz = Quiz(bot, GUILD, excluded_quiz_words)
hangman = Hangman(bot, GUILD)


##############
# Bot events #
##############
@bot.event
async def on_ready():
    logger.i('Successfully logged into {0} as {1}'.format(GUILD, bot.user))


@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if message.guild.name == GUILD:
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
    header_text = "Helpful Key: Words in straight brackets [] are required, words in parenthesis () are optional."
    h_help_text = "$h\nProvides help on all the commands available by printing out the descriptions for each."
    setup_help_text = "$setup (quiz/hangman) (channel-name)\nUse this command with the game you want to setup and which channel to link it to. Is provided with default values of \"bible-quizzing\" and \"bible-hangman\"."
    dailyvotd_help_text = "$dailyvotd [time]\nPrints the Verse of the Day every day at a consistent time. Using again while active turns it off."
    votd_help_text = "$votd\nPrints the Verse of the Day that was fetched from online."
    lookup_help_text = "$lookup [book] [chapter:verse] (book_num)\nLooks up and prints out the verse that was searched."
    rlookup_help_text = "$rlookup\nLooks up and prints out a random verse."
    keyword_help_text = "$keyword [word]\nTakes in a singular keyword and searches online for the top related verse to print out as a response."
    quiz_help_text = "$quiz [ref/word/sentence (book)\nSends a random verse with either the reference, a single word, or a sentence missing for the user to solve."
    hangman_help_text = "$hangman [easy/medium/hard/status/quit] (none/low/medium/high)\nUsing hangman starts a game. Three modes, status and quit are the accepted arguments. Change prefill with secondary option."
    hguess_help_text = "$hguess [guess]\nUsed to submit a guess to an ongoing hangman puzzle for the message sender."
    math_help_text = "$math [number_a] [operator] [number_b]\nProvided two numbers and a method of operation, the bot will produce the result. Supported operators: +, -, *, /, ^"
    help_text = "```{0}\n\n{1}\n\n{2}\n\n{3}\n\n{4}\n\n{5}\n\n{6}\n\n{7}\n\n{8}\n\n{9}\n\n{10}\n\n{11}```".format(
        header_text, h_help_text, setup_help_text, dailyvotd_help_text, votd_help_text,
        lookup_help_text, rlookup_help_text, keyword_help_text, quiz_help_text,
        hangman_help_text, hguess_help_text, math_help_text
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
    name="keyword",
    help="Takes in a singular keyword and searches online for the top related verse to print out as a response.",
    brief="Single keyword option to search online."
)
async def search_keyword(context: Context, keyword: str = None):
    await VerseInteractor.search_keyword(context, keyword)


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


####################
# Helper functions #
####################

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
