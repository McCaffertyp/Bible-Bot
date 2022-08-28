# -*- coding: utf-8 -*-
"""
Created on Wed Aug 24 04:35:00 2022

@author: Paul McCafferty
@version: 6.38
"""

# bot.py
import os
import csv
import random
import discord
import operator
import http.client
import html as html_helper
from enum import Enum
from util import logger
from discord.ext import commands
from dotenv import load_dotenv
from urllib.request import urlopen
from discord.ext.commands.context import Context

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_EBC = os.getenv("DISCORD_EBC_GUILD")
GUILD_SQUEEZE = os.getenv("DISCORD_SQUEEZE_GUILD")
# GUILD = GUILD_SQUEEZE
GUILD = GUILD_EBC

intents = discord.Intents().all()
bot = commands.Bot(command_prefix=commands.when_mentioned_or("$"), intents=intents)

#############
# Constants #
#############
RETURN_ERROR = "error"
BIBLE_DICT_NAME = "Name"
BIBLE_DICT_CHAPTERS = "Chapters"
BIBLE_DICT_TOTAL_VERSES = "Total Verses"
BIBLE_DICT_AVG_VERSES = "Average Verses"
GAME_CHANNEL_QUIZ = "quiz"
GAME_CHANNEL_HANGMAN = "hangman"
GAME_CHANNEL_QUIZ_DEFAULT_NAME = "bible-quizzing"
GAME_CHANNEL_HANGMAN_DEFAULT_NAME = "bible-hangman"
HANGMAN_DICT_SOLUTION = "solution"
HANGMAN_DICT_PROGRESS = "progress"
HANGMAN_DICT_MISTAKES_LEFT = "attempts"
HANGMAN_DICT_GUESSES = "guesses"
HANGMAN_PREFILL_LEVEL_NONE = "none"
HANGMAN_PREFILL_LEVEL_LOW = "low"
HANGMAN_PREFILL_LEVEL_MEDIUM = "medium"
HANGMAN_PREFILL_LEVEL_HIGH = "high"
VOTD_BASE_URL = "https://dailyverses.net/"
VERSE_LOOKUP_BASE_URL = "https://www.openbible.info/labs/cross-references/search?q="
KEYWORD_SEARCH_BASE_URL = "https://www.biblegateway.com/quicksearch/?quicksearch="
ENGLISH_ALPHABET = "abcdefghijklmnopqrstuvwxyz"

#############
# Variables #
#############
swear_words = [line.split("\n")[0] for line in open("swear_words.txt", "r").readlines()]
operators = {"+": operator.add, "-": operator.sub, "*": operator.mul, "/": operator.truediv, "^": operator.pow}
game_channels = {GAME_CHANNEL_QUIZ: GAME_CHANNEL_QUIZ_DEFAULT_NAME, GAME_CHANNEL_HANGMAN: GAME_CHANNEL_HANGMAN_DEFAULT_NAME}
quizzing = {}
playing_hangman = {}


##################
# Helper Classes #
##################
class ChannelType(Enum):
    TEXT = 1
    VOICE = 2


##############
# Bot events #
##############
@bot.event
async def on_ready():
    logger.i('Successfully logged into {0} as {1.user}'.format(GUILD, bot))


@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if message.guild.name == GUILD:
        await filter_message(message)
        await bot.process_commands(message)
        if str(message.author) in quizzing:
            await check_answer(message, message.content)
        elif "bro =" == message.content.lower():
            await send_message(message, "Wassup homie")


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
    await send_message(context, help_text)


@bot.command(
    name="setup",
    help="Use this command with the game you want to setup and which channel to link it to. Is provided with default values of \"bible-quizzing\" and \"bible-hangman\".",
    brief="Set specific channels for the games."
)
async def setup_game_channels(context: Context, game: str = None, channelName: str = None):
    if game is None or channelName is None:
        await send_message(context, "No game and/or channel name specified. Setting both channels back to default.")
        game_channels[GAME_CHANNEL_QUIZ] = GAME_CHANNEL_QUIZ_DEFAULT_NAME
        game_channels[GAME_CHANNEL_HANGMAN] = GAME_CHANNEL_HANGMAN_DEFAULT_NAME

        existing_text_channels = []
        for guild in bot.guilds:
            if guild.name == GUILD:
                existing_text_channels = [str(channel.name) for channel in guild.text_channels]

        if GAME_CHANNEL_QUIZ_DEFAULT_NAME not in existing_text_channels:
            logger.d("Channel {0} did not exist. Creating...".format(channelName))
            await create_channel(context, ChannelType.TEXT, GAME_CHANNEL_QUIZ_DEFAULT_NAME)
        if GAME_CHANNEL_HANGMAN_DEFAULT_NAME not in existing_text_channels:
            logger.d("Channel {0} did not exist. Creating...".format(channelName))
            await create_channel(context, ChannelType.TEXT, GAME_CHANNEL_HANGMAN_DEFAULT_NAME)
    else:
        if game != "hangman" and game != "quiz":
            await send_message(context, "That game currently does not exist.")
        else:
            logger.d("Setting channel for {0} to {1}".format(game, channelName))
            game_channels[game] = channelName
            existing_text_channels = []
            for guild in bot.guilds:
                if guild.name == GUILD:
                    existing_text_channels = [str(channel.name) for channel in guild.text_channels]

            if channelName not in existing_text_channels:
                logger.d("Channel {0} did not exist. Creating...".format(channelName))
                await create_channel(context, ChannelType.TEXT, channelName)

            await send_message(context, "Set {0} to be played in {1}".format(game, channelName))


@bot.command(
    name="dailyvotd",
    help="Prints the Verse of the Day every day at a consistent time. Using again while active turns it off.",
    brief="Puts the bot on a timer for sending the daily VOTD."
)
async def send_daily_verse_of_the_day(context: Context, time: str = None):
    if time is None:
        await send_message(context, "Please provide a time.")
    else:
        converted_time = convert_twenty_four_to_twelve(time)
        response = "Will now send the VOTD daily at {0}.".format(converted_time)
        await send_message(context, response)
        await send_message(context, "Oops, it seems this command is not finished yet!\nVerse will not be sent ;-;")


@bot.command(
    name="votd",
    help="Prints the Verse of the Day that was fetched from online.",
    brief="Prints the Verse of the Day."
)
async def send_verse_of_the_day(context: Context):
    votd = get_votd_from_url()
    await send_message(context, remove_html_tags(votd))


@bot.command(
    name="lookup",
    help="Looks up and prints out the verse that was searched.",
    brief="Looks up verse and prints it."
)
async def verse_lookup(context: Context, book: str = None, chapter_verse: str = None, book_num: str = None):
    if book is None:
        await send_message(context, "Unfortunately I cannot look that up. The Book was not provided.")
    elif chapter_verse is None:
        await send_message(context, "Unfortunately I cannot look that up. The Chapter:Verse was not provided.")
    elif ":" not in chapter_verse:
        await send_message(context, "Unfortunately I cannot look that up. The Chapter:Verse was not in the proper format.")
    else:
        if book_num is not None:
            if int(book_num) > 3 or int(book_num) < 1:
                await send_message(context, "Unfortunately I cannot look that up. The entered Book Number does not exist.")
        verse_text = get_verse_from_lookup_url(book.lower(), chapter_verse, book_num)
        if verse_text == "error":
            if book_num is not None:
                logger.w("Verse lookup \"{0} {1} {2}\" is not a valid reference".format(book_num, book, chapter_verse))
                await send_message(context, "Verse lookup \"{0} {1} {2}\" is not a valid reference.".format(book_num, book, chapter_verse))
            else:
                logger.w("Verse lookup \"{0} {1}\" is not a valid reference".format(book, chapter_verse))
                await send_message(context, "Verse lookup \"{0} {1}\" is not a valid reference.".format(book, chapter_verse))
            return
        else:
            await send_message(context, remove_html_tags(verse_text))


@bot.command(
    name="rlookup",
    help="Looks up and prints out a random verse.",
    brief="Prints random verse."
)
async def verse_lookup_random(context: Context):
    random_verse = get_random_verse()
    await send_message(context, random_verse)


@bot.command(
    name="keyword",
    help="Takes in a singular keyword and searches online for the top related verse to print out as a response.",
    brief="Single keyword option to search online."
)
async def search_keyword(context: Context, keyword: str = None):
    if keyword is None:
        await send_message(context, "Unfortunately nothing popped up for that keyword, since no keyword was entered.")
    else:
        verse_text = get_verse_from_keyword_url(keyword)
        if verse_text == "error":
            await send_message(context, "Keyword \"{0}\" has 0 good matches.".format(keyword))
        else:
            await send_message(context, remove_html_tags(verse_text))


@bot.command(
    name="quiz",
    help="Sends a random verse with either the reference, a single word, or a sentence missing for the user to solve. User can select book.",
    brief="Quizzes the user on a random verse."
)
async def bible_quizzing(context: Context, option: str = None, *, book: str = None):
    channel_exists = await check_channel_exists(context, GAME_CHANNEL_QUIZ, game_channels[GAME_CHANNEL_QUIZ])
    if not channel_exists:
        return

    correct_channel = await is_correct_channel(context, GAME_CHANNEL_QUIZ)
    if not correct_channel:
        return

    quizzer = str(context.author)
    username = quizzer.split("#")[0]
    if option is None:
        await send_message(context, "{0} provided no option. Choosing a random one.".format(username))
        options = ["ref", "word", "sentence"]
        option = options[random.randint(0, 2)]
        await send_message(context, "{0} your quizzing option is on: {1}".format(username, option))

    random_verse = get_random_verse(book)
    if random_verse == RETURN_ERROR:
        await send_message(context, "{0} that book does not exist.".format(username))
        return
    verse_text_start = random_verse.find("\"") + 1
    verse_text_end = random_verse.find("\"", verse_text_start)
    verse_text = random_verse[verse_text_start:verse_text_end]

    verse_reference_start_search = "\" - "
    verse_reference_start = random_verse.find(verse_reference_start_search) + len(verse_reference_start_search)
    verse_reference_end = random_verse.find(" ESV")
    verse_reference = random_verse[verse_reference_start:verse_reference_end]

    if option == "ref":
        quiz_verse = replace_characters(random_verse, verse_reference, "_")
        quizzing[quizzer] = verse_reference
    elif option == "word":
        verse_words = verse_text.split(" ")
        full_remove_word = verse_words[random.randint(0, (len(verse_words) - 1))]
        remove_word = remove_non_alphabet(full_remove_word)
        quiz_verse = replace_characters(random_verse, remove_word, "_")
        quizzing[quizzer] = remove_word
    elif option == "sentence":
        verse_words = verse_text.split(" ")
        remove_word_count = random.randint(2, (len(verse_words) - 1))
        remove_start_word_index = random.randint(0, (len(verse_words) - remove_word_count))
        remove_end_word_index = remove_start_word_index + remove_word_count - 1
        remove_start_word = verse_words[remove_start_word_index]
        remove_end_word = verse_words[remove_end_word_index]
        remove_sentence = random_verse[random_verse.find(remove_start_word):(random_verse.find(remove_end_word) + len(remove_end_word))]
        quiz_verse = replace_characters(random_verse, remove_sentence, "_")
        quizzing[quizzer] = remove_sentence
        # all_words = ""
        # for i in range(remove_start_index, (remove_start_index + remove_word_count)):
        #     remove_word = verse_words[i].replace(",", "")
        #     quiz_verse = replace_characters(quiz_verse, remove_word, "_")
        #     all_words = "{0},{1}".format(all_words, remove_word)
        # quizzing[quizzer] = all_words[1:(len(all_words) - 1)]
    else:
        await send_message(context, "{0}, that option is unsupported.".format(context.author.mention))
        return

    await send_message(context, "{0}, your quiz is:\n{1}".format(context.author.mention, quiz_verse))


@bot.command(
    name="hangman",
    help="Using hangman starts a game. Three modes, status and quit are the accepted arguments. Change prefill with secondary option.",
    brief="Plays hangman with the user."
)
async def play_hangman(context: Context, option: str = None, prefill_level: str = HANGMAN_PREFILL_LEVEL_NONE):
    if option is None:
        await send_message(context, "No hangman option was provided. Please use $h for options.")
    else:
        prefill_level = prefill_level.lower()
        if (prefill_level != HANGMAN_PREFILL_LEVEL_NONE and prefill_level != HANGMAN_PREFILL_LEVEL_LOW and
                prefill_level != HANGMAN_PREFILL_LEVEL_MEDIUM and prefill_level != HANGMAN_PREFILL_LEVEL_HIGH):
            await send_message(context, "Prefill level for the verse specified is unrecognized. Please use $h for options.")
            return

        channel_exists = await check_channel_exists(context, GAME_CHANNEL_HANGMAN, game_channels[GAME_CHANNEL_HANGMAN])
        if not channel_exists:
            return

        correct_channel = await is_correct_channel(context, GAME_CHANNEL_HANGMAN)
        if not correct_channel:
            return

        if option != "easy" and option != "medium" and option != "hard" and option != "status" and option != "quit":
            await send_message(context, "The entered option \"{0}\" is unsupported.".format(option))
            return

        player = str(context.author)
        player_mention = context.author.mention

        if option == "status":
            if player not in playing_hangman:
                await send_message(context, "{0} you have no ongoing games! Start one with: $hangman [difficulty]".format(player_mention))
                return
            else:
                current_progress = playing_hangman[player][HANGMAN_DICT_PROGRESS]
                remaining_mistakes = playing_hangman[player][HANGMAN_DICT_MISTAKES_LEFT]
                remaining_letters = get_remaining_letters(playing_hangman[player][HANGMAN_DICT_GUESSES])
                status_update = "{0} - Progress:\n{1}\n\nRemaining Mistakes: {2}\n\nRemaining Letters: {3}".format(
                    player_mention, current_progress, remaining_mistakes, remaining_letters
                )
                await send_message(context, handle_discord_formatting(status_update))
                return

        if option == "quit":
            if player not in playing_hangman:
                await send_message(context, "{0} you have no ongoing games! Start one with: $hangman [difficulty]".format(player_mention))
                return
            else:
                puzzle_solution = playing_hangman[player][HANGMAN_DICT_SOLUTION]
                status_update = "{0} Sorry you chose to quit :(\nHere's your finished verse:\n{1}".format(player_mention, puzzle_solution)
                playing_hangman.__delitem__(player)
                await send_message(context, handle_discord_formatting(status_update))
                return

        random_verse = get_random_verse()
        verse_text_start = random_verse.find("\"") + 1
        verse_text_end = random_verse.find("\"", verse_text_start)
        verse_text = random_verse[verse_text_start:verse_text_end]

        verse_reference_start_search = "\" - "
        verse_reference_start = random_verse.find(verse_reference_start_search) + len(verse_reference_start_search)
        verse_reference_end = random_verse.find(" ESV")
        verse_reference = random_verse[verse_reference_start:verse_reference_end]

        puzzle_answer = "\"{0}\" - {1}".format(verse_text, verse_reference)
        puzzle_progress = create_hangman_puzzle(puzzle_answer, prefill_level)

        playing_hangman[player] = dict()
        playing_hangman[player][HANGMAN_DICT_SOLUTION] = puzzle_answer
        playing_hangman[player][HANGMAN_DICT_PROGRESS] = puzzle_progress
        if option == "easy":
            playing_hangman[player][HANGMAN_DICT_MISTAKES_LEFT] = 10
        elif option == "medium":
            playing_hangman[player][HANGMAN_DICT_MISTAKES_LEFT] = 5
        elif option == "hard":
            playing_hangman[player][HANGMAN_DICT_MISTAKES_LEFT] = 3

        puzzle_preview = "{0} - Here's your puzzle!\n{1}\n\nYou have {2} allowed Mistakes.".format(
            player_mention, puzzle_progress, playing_hangman[player][HANGMAN_DICT_MISTAKES_LEFT]
        )
        await send_message(context, handle_discord_formatting(puzzle_preview))


@bot.command(
    name="hguess",
    help="Used to submit a guess to an ongoing hangman puzzle for the message sender.",
    brief="Submit a guess to ongoing hangman puzzle."
)
async def submit_hangman_guess(context: Context, guess: str = None):
    if guess is None:
        await send_message(context, "No guess was supplied!")
    elif guess.lower() not in ENGLISH_ALPHABET:
        await send_message(context, "That guess is invalid!")
    else:
        player = str(context.author)
        player_mention = context.author.mention
        if player not in playing_hangman:
            await send_message(context, "{0} you have no ongoing games! Start one with: $hangman [difficulty]".format(player_mention))
            return

        guess = guess.lower()
        try:
            previous_guesses = playing_hangman[player][HANGMAN_DICT_GUESSES]
            if guess in previous_guesses:
                await send_message(context, "{0} you have already guessed that letter! Try a different one.".format(player_mention))
                return
        except KeyError as error:
            previous_guesses = ""
            logger.w("Tried to access a non-existent key")

        puzzle_solution = playing_hangman[player][HANGMAN_DICT_SOLUTION]
        if guess in puzzle_solution.lower():
            puzzle_progress = playing_hangman[player][HANGMAN_DICT_PROGRESS]
            updated_progress = update_hangman_puzzle_progress(guess, puzzle_solution, puzzle_progress)
            playing_hangman[player][HANGMAN_DICT_PROGRESS] = updated_progress
        else:
            mistakes_remaining = int(playing_hangman[player][HANGMAN_DICT_MISTAKES_LEFT])
            updated_mistakes_remaining = mistakes_remaining - 1
            if updated_mistakes_remaining == 0:
                status_update = "Unfortunate, {0}. You ran out of mistakes. Here's the verse:\n{1}".format(player_mention, puzzle_solution)
                await send_message(context, handle_discord_formatting(status_update))
                playing_hangman.__delitem__(player)
                return
            playing_hangman[player][HANGMAN_DICT_MISTAKES_LEFT] = updated_mistakes_remaining

        playing_hangman[player][HANGMAN_DICT_GUESSES] = "{0}{1}".format(previous_guesses, guess)
        current_progress = playing_hangman[player][HANGMAN_DICT_PROGRESS]
        if puzzle_solution == current_progress:
            status_update = "Congrats, {0}! You finished the verse!\n{1}".format(player_mention, puzzle_solution)
            playing_hangman.__delitem__(player)
            await send_message(context, handle_discord_formatting(status_update))
        else:
            remaining_mistakes = playing_hangman[player][HANGMAN_DICT_MISTAKES_LEFT]
            remaining_letters = get_remaining_letters(playing_hangman[player][HANGMAN_DICT_GUESSES])
            status_update = "{0} - Progress:\n{1}\n\nRemaining Mistakes: {2}\n\nRemaining Letters: {3}".format(
                player_mention, current_progress, remaining_mistakes, remaining_letters
            )
            await send_message(context, handle_discord_formatting(status_update))


@bot.command(
    name="math",
    help="Provided two numbers and a method of operation, the bot will produce the result.",
    brief="Give two number and an operator, get result."
)
async def do_math(context: Context, num_one: float = None, op: str = None, num_two: float = None):
    if num_one is None or op is None or num_two is None:
        await send_message(context, "Cannot perform math operations without all the necessary parts.")
    else:
        answer = operators[op](num_one, num_two)
        await send_message(context, "Answer: {0}".format(answer))


####################
# Helper functions #
####################

#########
# Async #
#########
async def check_answer(message, answer: str):
    if "$quiz" in message.content:
        return
    quizzer = str(message.author)
    username = quizzer.split("#")[0]
    correct_answer: str = quizzing[quizzer]
    if answer.lower() != correct_answer.lower():
        await send_message(message, "Sorry, {0}, that is incorrect. Was looking for:\n{1}".format(username, correct_answer))
    else:
        await send_message(message, "Congratulations, {0}, that is correct!".format(username))
    quizzing.__delitem__(quizzer)


async def check_channel_exists(context: Context, game: str, channelName: str) -> bool:
    existing_text_channels = []
    for guild in bot.guilds:
        if guild.name == GUILD:
            existing_text_channels = [str(channel.name) for channel in guild.text_channels]

    if channelName not in existing_text_channels:
        logger.d("Channel {0} did not exist for {1}".format(channelName, game))
        await send_message(context, "Channel for {0} does not exist yet.\nPlease use $setup or $h for further help.".format(game))
        return False

    return True


async def create_channel(context: Context, channelType: ChannelType, channelName: str):
    guild = context.message.guild
    if channelType == ChannelType.TEXT:
        logger.d("Creating new text channel...")
        channelName = ensure_valid_channel_name(channelType, channelName)
        await guild.create_text_channel(channelName)
        logger.d("New text channel named {0} created successfully".format(channelName))
    elif channelType == ChannelType.VOICE:
        logger.d("Creating new voice channel...")
        channelName = ensure_valid_channel_name(channelType, channelName)
        await guild.create_voice_channel(channelName)
        logger.d("New voice channel named {0} created successfully".format(channelName))
    else:
        logger.e("Should not have reached this point. Something is broken")
        await send_message(context, "Unsure how this is even being printed. Something is broken. Info: channelType={0}, channelName={1}".format(channelType, channelName))


async def delete_message(message, word):
    await message.delete()
    logger.i("User {0} tried to use the banned word \"{1}\"".format(str(message.author).split("#")[0], word))
    response = "{0} no swearing while I'm around.".format(message.author.mention)
    await send_message(message, response)


async def filter_message(message):
    for word in swear_words:
        if word in message.content.lower():
            if is_banned_word(word, message.content.lower()):
                await delete_message(message, word)
                break


async def is_correct_channel(context: Context, game: str) -> bool:
    current_channel = context.channel.name
    if current_channel != game_channels[game]:
        await send_message(context, "{0} this is not the channel for {1}!".format(context.author.mention, game))
        return False
    return True


async def send_message(message, msg):
    await message.channel.send(msg, allowed_mentions=discord.AllowedMentions().all())


##############
# Non-Async #
#############
def convert_twenty_four_to_twelve(time: str) -> str:
    time_split = time.split(":")
    hour = int(time_split[0])
    minute = int(time_split[1])

    if minute > 59:
        minute = 59

    if hour < 12:
        return "{0}:{1} AM".format(hour, minute)
    elif 12 <= hour < 25:
        return "{0}:{1} PM".format(hour - 12, minute)
    else:
        return "{0}:{1} PM".format(23, minute)


def create_hangman_puzzle(verse: str, prefill_level: str) -> str:
    if prefill_level == HANGMAN_PREFILL_LEVEL_NONE:
        puzzle = ""
        for c in verse:
            if c.lower() in ENGLISH_ALPHABET:
                puzzle = "{0}_".format(puzzle)
            else:
                puzzle = "{0}{1}".format(puzzle, c)
        return puzzle
    else:
        words_in_verse = get_only_words(verse.split())
        sectioned_puzzle = section_hangman_puzzle(words_in_verse)
        if prefill_level == HANGMAN_PREFILL_LEVEL_LOW:
            # Remove 3 out of every 4
            removal_start_index = 1
        elif prefill_level == HANGMAN_PREFILL_LEVEL_MEDIUM:
            # Remove 1 out of every 2
            removal_start_index = 2
        elif prefill_level == HANGMAN_PREFILL_LEVEL_HIGH:
            # Remove 1 out of every 4
            removal_start_index = 3
        else:
            logger.e("Every prefill option for hangman was passed over. Should not be possible.")
            return "error"

        puzzle = verse
        find_start_index = 0
        for sub_section in sectioned_puzzle:
            for i in range(0, len(sub_section)):
                word = sub_section[i]
                word_len = len(word)
                if i >= removal_start_index:
                    replace_start_index = puzzle.find(word, find_start_index)
                    replace_end_index = replace_start_index + word_len
                    puzzle = "{0}{1}{2}".format(
                        puzzle[:replace_start_index], ("_" * word_len), puzzle[replace_end_index:]
                    )
                find_start_index += (word_len + 1)

        return puzzle


def ensure_valid_channel_name(channelType: ChannelType, channelName: str) -> str:
    if channelType == ChannelType.TEXT:
        channelName = channelName.lower().replace(" ", "-")
    elif channelType == ChannelType.VOICE:
        channelName = channelName
    return channelName


def get_only_words(verse_words: list) -> list:
    words = []
    for word in verse_words:
        stripped_word = remove_non_alphabet(word)
        if len(stripped_word) > 0:
            words.append(stripped_word)
    return words


def get_votd_from_url() -> str:
    lookup_url = "{0}{1}".format(VOTD_BASE_URL, "esv")
    webpage: http.client.HTTPResponse = urlopen(lookup_url)
    html_bytes: bytes = webpage.read()
    html: str = html_helper.unescape(html_bytes.decode("utf-8"))

    verse_text_start_search = "<span class=\"v1\">"
    verse_text_start_index = html.find(verse_text_start_search) + len(verse_text_start_search)
    verse_text_end_index = html.find("</span>", verse_text_start_index)

    verse_ref_start_search = "class=\"vc\">"
    verse_ref_start_index = html.find(verse_ref_start_search) + len(verse_ref_start_search)
    verse_ref_end_index = html.find("</a>", verse_ref_start_index)

    verse_text = html[verse_text_start_index:verse_text_end_index]
    reference = html[verse_ref_start_index:verse_ref_end_index]
    return "\"{0}\" - {1} ESV".format(verse_text, reference)


def get_verse_from_lookup_url(book: str, chapter_verse: str, book_num: str = None) -> str:
    book = book.capitalize()
    chapter_verse_split = chapter_verse.split(":")
    chapter = chapter_verse_split[0]
    verse = chapter_verse_split[1]
    logger.d("Looking up: book_num={0}, book={1}, chapter={2}, verse={3}".format(book_num, book, chapter, verse))
    if book_num is None:
        lookup_url = "{0}{1}+{2}%3A{3}".format(VERSE_LOOKUP_BASE_URL, book.replace(" ", "+"), chapter, verse)
    else:
        lookup_url = "{0}{1}+{2}+{3}%3A{4}".format(VERSE_LOOKUP_BASE_URL, book_num, book.replace(" ", "+"), chapter, verse)

    logger.d("Using url={0}".format(lookup_url))
    webpage: http.client.HTTPResponse = urlopen(lookup_url)
    html_bytes: bytes = webpage.read()
    html: str = html_helper.unescape(html_bytes.decode("utf-8"))

    verse_text_start_search = "<div class=\"crossref-verse\">"
    verse_text_sub_start_search = "<p>"
    verse_text_search_start_index = html.find(verse_text_start_search)
    if verse_text_search_start_index == -1:
        return RETURN_ERROR
    verse_text_start_index = html.find(verse_text_sub_start_search, verse_text_search_start_index) + len(verse_text_sub_start_search)
    verse_text_end_index = html.find("</p>", verse_text_start_index)

    verse_text = html[verse_text_start_index:verse_text_end_index]
    if book_num is None:
        reference = "{0} {1}".format(book, chapter_verse)
    else:
        reference = "{0} {1} {2}".format(book_num, book, chapter_verse)
    return "\"{0}\" - {1} ESV".format(verse_text, reference)


def get_verse_from_keyword_url(word) -> str:
    lookup_url = "{0}{1}&version=ESV".format(KEYWORD_SEARCH_BASE_URL, word)
    webpage: http.client.HTTPResponse = urlopen(lookup_url)
    html_bytes: bytes = webpage.read()
    html: str = html_helper.unescape(html_bytes.decode("utf-8"))

    verse_text_start_search = "<div class=\"bible-item-text\">"
    verse_text_start_index = html.find(verse_text_start_search)
    if verse_text_start_index == -1:
        verse_text_start_search = "div class=\"bible-item-text col-sm-9\">"
        verse_text_start_index = html.find(verse_text_start_search)
        if verse_text_start_index == -1:
            return RETURN_ERROR
    verse_text_end_index = html.find("<div class=\"bible-item-extras\">", verse_text_start_index)

    verse_ref_start_search = "<a class=\"bible-item-title\""
    verse_ref_sub_start_search = ">"
    verse_ref_search_start_index = html.find(verse_ref_start_search)
    verse_ref_start_index = html.find(verse_ref_sub_start_search, verse_ref_search_start_index) + len(
        verse_ref_sub_start_search)
    verse_ref_end_index = html.find("</a>", verse_ref_start_index)

    verse_text_adjusted_start_index = verse_text_start_index + len(verse_text_start_search)
    verse_text = html[verse_text_adjusted_start_index:verse_text_end_index]
    if "<h3>" in verse_text:
        verse_text_start_search = "</h3>"
        verse_text_start_index = verse_text.find(verse_text_start_search) + len(verse_text_start_search)
        verse_text_end_index = verse_text.find("<div class=\"bible-item-extras\">", verse_text_start_index)
        verse_text = verse_text[verse_text_start_index:verse_text_end_index]
    reference = html[verse_ref_start_index:verse_ref_end_index]

    while verse_text[0] == "\n":
        verse_text = verse_text[1:]

    return "\"{0}\" - {1} ESV".format(verse_text, reference)


def get_random_verse(book: str = None) -> str:
    with open("bible_data_esv.csv") as csv_file:
        csv_reader = csv.DictReader(csv_file)
        bible_dict = {}
        book_names = []
        skip_first_row = True
        for row in csv_reader:
            if not skip_first_row:
                skip_first_row = True
            else:
                book_name = row[BIBLE_DICT_NAME].lower()
                bible_dict[book_name] = row
                book_names.append(book_name)

        if book is None:
            book: str = book_names[random.randint(0, (len(book_names) - 1))]
            logger.d("Random book fetched = {0}".format(book))
        else:
            if book.lower() not in bible_dict:
                logger.e("Was unable to fetch provided book: {0}".format(book))
                return "error"
            logger.d("Using user supplied book = {0}".format(book))
        random_book_stats = bible_dict.get(book.lower())
        random_book_chapters = int(random_book_stats[BIBLE_DICT_CHAPTERS])
        logger.d("Random book chapter count = {0}".format(random_book_chapters))
        random_book_chapter = random.randint(1, random_book_chapters)
        logger.d("Random book chapter chosen = {0}".format(random_book_chapter))
        random_book_verses = int(random_book_stats[str(random_book_chapter)])
        logger.d("Random book verse count for selected chapter = {1}".format(random_book_chapter, random_book_verses))
        random_book_verse = random.randint(1, random_book_verses)
        logger.d("Random book verse selected = {0}".format(random_book_verse))
        random_chapter_verse = "{0}:{1}".format(random_book_chapter, random_book_verse)

        if " " in book:
            if "Song" in book:
                verse_text = get_verse_from_lookup_url(book, random_chapter_verse, None)
            else:
                random_book_split = book.split(" ")
                bna = random_book_split[1]
                bnu = random_book_split[0]
                verse_text = get_verse_from_lookup_url(bna, random_chapter_verse, bnu)
        else:
            verse_text = get_verse_from_lookup_url(book, random_chapter_verse, None)

        return remove_html_tags(verse_text)


def get_remaining_letters(guessed_letters: str) -> str:
    remaining_letters = ""
    for c in ENGLISH_ALPHABET:
        if c not in guessed_letters:
            remaining_letters = "{0}, {1}".format(remaining_letters, c)
    return remaining_letters[2:]


def handle_discord_formatting(text: str) -> str:
    discord_formatted = ""
    for c in text:
        if c == "_" or c == "*":
            discord_formatted = "{0}\\{1}".format(discord_formatted, c)
        else:
            discord_formatted = "{0}{1}".format(discord_formatted, c)

    return discord_formatted


def is_banned_word(swear_word: str, sentence: str) -> bool:
    start_index_of_swear_word = sentence.find(swear_word)
    end_index_of_swear_word = start_index_of_swear_word + len(swear_word)
    word = sentence[start_index_of_swear_word:end_index_of_swear_word]

    left = start_index_of_swear_word - 1
    right = end_index_of_swear_word

    while left > -1 and sentence[left] != " ":
        word = "{0}{1}".format(sentence[left], word)
        left -= 1

    while right < len(sentence) and sentence[right] != " ":
        word = "{0}{1}".format(word, sentence[right])
        right += 1

    return word in swear_words


def remove_html_tags(text: str) -> str:
    has_tag = "<" in text
    while has_tag:
        open_tag_index = text.find("<")
        end_tag_index = text.find(">") + 1
        text = text.replace(text[open_tag_index:end_tag_index], "")
        has_tag = "<" in text
    return text


def remove_non_alphabet(s: str) -> str:
    base_word = ""
    for c in s:
        if c.lower() in ENGLISH_ALPHABET:
            base_word = "{0}{1}".format(base_word, c)
    return base_word


def replace_characters(s: str, c: str, r: str) -> str:
    # Replaces characters "c" in string "s" with character "r"
    full_replace_string = ""
    for i in range(0, len(c), len(r)):
        full_replace_string = "{0}\\{1}".format(full_replace_string, r)
    return s.replace(c, full_replace_string)


def section_hangman_puzzle(words_in_verse: list) -> list:
    sections = []
    sub_section_size = 4
    for i in range(0, len(words_in_verse), sub_section_size):
        sub_section = words_in_verse[i:(i + sub_section_size)]
        sections.append(sub_section)
    return sections


def update_hangman_puzzle_progress(guess: str, solution: str, progress: str) -> str:
    solution_characters = [c for c in solution]
    progress_characters = [c for c in progress]
    updated_puzzle = ""

    for i in range(0, len(solution_characters)):
        if solution_characters[i].lower() == guess:
            updated_puzzle = "{0}{1}".format(updated_puzzle, solution_characters[i])
        else:
            updated_puzzle = "{0}{1}".format(updated_puzzle, progress_characters[i])

    return updated_puzzle


bot.run(TOKEN)
