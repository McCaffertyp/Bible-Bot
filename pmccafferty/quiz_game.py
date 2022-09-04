import random

from discord.ext.commands import Bot
from discord.ext.commands.context import Context

import channel_interactor as ChannelInteractor
import util.string as StringHelper
import verse_interactor as VerseInteractor
from util import logger
from firebase_interactor import FirebaseInteractor


#############
# Constants #
#############
FIREBASE_BEST_STREAK_REF = "bestStreak"
FIREBASE_CURRENT_STREAK_REF = "currentStreak"
FIREBASE_GAMES_PLAYED_REF = "gamesPlayed"
FIREBASE_RATING_REF = "rating"
DEFAULT_POINTS = 100


class Quiz:
    def __init__(self, bot: Bot, guild_name: str, excluded_quiz_words: list, firebase_interactor: FirebaseInteractor):
        self.bot = bot
        self.guild_name = guild_name
        self.excluded_quiz_words = excluded_quiz_words
        self.firebase_interactor = firebase_interactor
        self.game_name = ChannelInteractor.GAME_CHANNEL_QUIZ
        self.game_channel_name = ChannelInteractor.GAME_CHANNEL_QUIZ_DEFAULT_NAME
        self.players = {}

    async def start_game(self, context: Context, option: str = None, book: str = None):
        channel_exists = await ChannelInteractor.check_channel_exists(self.bot, self.guild_name, context, self.game_name, self.game_channel_name)
        if not channel_exists:
            return

        correct_channel = await ChannelInteractor.is_correct_channel(context, self.game_name, self.game_channel_name)
        if not correct_channel:
            return

        player = str(context.author)
        username = StringHelper.make_valid_firebase_name(player.split("#")[0])
        if option is None:
            await ChannelInteractor.send_message(context, "{0} provided no option. Choosing a random one.".format(username))
            options = ["ref", "word", "sentence"]
            option = options[random.randint(0, 2)]
            await ChannelInteractor.send_message(context, "{0} your quizzing option is on: {1}".format(username, option))

        random_verse = VerseInteractor.get_random_verse(book)
        if random_verse == StringHelper.RETURN_ERROR:
            await ChannelInteractor.send_message(context, "{0} that book does not exist.".format(username))
            return
        verse_text_start = random_verse.find("\"") + 1
        verse_text_end = random_verse.find("\"", verse_text_start)
        verse_text = random_verse[verse_text_start:verse_text_end]

        verse_reference_start_search = "\" - "
        verse_reference_start = random_verse.find(verse_reference_start_search) + len(verse_reference_start_search)
        verse_reference_end = random_verse.find(" ESV")
        verse_reference = random_verse[verse_reference_start:verse_reference_end]

        if option == "ref":
            quiz_verse = self.option_ref(player, random_verse, verse_reference)
        elif option == "word":
            quiz_verse = self.option_word(player, random_verse, verse_text)
        elif option == "sentence":
            quiz_verse = self.option_sentence(player, random_verse, verse_text)
        elif option == "rating" or option == "streak" or option == "games":
            await self.option_stat(context, option, username)
            return
        else:
            await ChannelInteractor.send_message(context, "{0}, that option is unsupported.".format(context.author.mention))
            return

        self.check_and_create_player_data(username)
        await ChannelInteractor.send_message(context, "{0}, your quiz is:\n{1}".format(context.author.mention, quiz_verse))

    def option_ref(self, player: str, random_verse: str, verse_reference: str) -> str:
        self.players[player] = verse_reference
        return StringHelper.replace_characters(random_verse, verse_reference, "_")

    def option_word(self, player: str, random_verse: str, verse_text: str) -> str:
        verse_words = verse_text.split(" ")
        full_remove_word = verse_words[random.randint(0, (len(verse_words) - 1))]
        remove_word = StringHelper.remove_non_alphabet(full_remove_word)
        while remove_word.lower() in self.excluded_quiz_words:
            logger.d("Tried to remove \"{0}\" from verse. Fetching new word...".format(remove_word))
            full_remove_word = verse_words[random.randint(0, (len(verse_words) - 1))]
            remove_word = StringHelper.remove_non_alphabet(full_remove_word)
        self.players[player] = remove_word
        return StringHelper.replace_words(random_verse, remove_word, "_")

    def option_sentence(self, player: str, random_verse: str, verse_text: str) -> str:
        verse_words = verse_text.split(" ")
        remove_word_count = random.randint(2, (len(verse_words) - 1))
        remove_start_word_index = random.randint(0, (len(verse_words) - remove_word_count))
        remove_end_word_index = remove_start_word_index + remove_word_count - 1
        remove_start_word = verse_words[remove_start_word_index]
        remove_end_word = verse_words[remove_end_word_index]
        remove_sentence = random_verse[random_verse.find(remove_start_word):(random_verse.find(remove_end_word) + len(remove_end_word))]
        self.players[player] = remove_sentence
        # all_words = ""
        # for i in range(remove_start_index, (remove_start_index + remove_word_count)):
        #     remove_word = verse_words[i].replace(",", "")
        #     quiz_verse = replace_characters(quiz_verse, remove_word, "_")
        #     all_words = "{0},{1}".format(all_words, remove_word)
        # quizzing[player] = all_words[1:(len(all_words) - 1)]
        return StringHelper.replace_characters(random_verse, remove_sentence, "_")

    async def option_stat(self, context: Context, option: str, username: str):
        user_database_path = "{0}/{1}".format(self.game_name, username)
        rating_path = "{0}/{1}".format(user_database_path, FIREBASE_RATING_REF)
        best_streak_path = "{0}/{1}".format(user_database_path, FIREBASE_BEST_STREAK_REF)
        current_streak_path = "{0}/{1}".format(user_database_path, FIREBASE_CURRENT_STREAK_REF)
        games_played_path = "{0}/{1}".format(user_database_path, FIREBASE_GAMES_PLAYED_REF)
        if not self.firebase_interactor.check_node_exists(user_database_path):
            await ChannelInteractor.send_message(context, "{0} you aren't currently in the system.\nSetting up your profile...".format(context.author.mention))
            self.firebase_interactor.write_to_node(rating_path, DEFAULT_POINTS)
            self.firebase_interactor.write_to_node(best_streak_path, 0)
            self.firebase_interactor.write_to_node(current_streak_path, 0)
            self.firebase_interactor.write_to_node(games_played_path, 0)
            await ChannelInteractor.send_message(context, "{0} you are now in the database. Have fun playing!")
        else:
            if option == "rating":
                current_rating = self.firebase_interactor.read_from_node(rating_path)
                await ChannelInteractor.send_message(context, "{0} Current Rating: {1}".format(context.author.mention, current_rating))
            elif option == "streak":
                best_streak = self.firebase_interactor.read_from_node(best_streak_path)
                await ChannelInteractor.send_message(context, "{0} Best Streak: {1}".format(context.author.mention, best_streak))
            else:
                games_played = self.firebase_interactor.read_from_node(games_played_path)
                await ChannelInteractor.send_message(context, "{0} Games Played: {1}".format(context.author.mention, games_played))

    async def check_answer(self, message, answer: str):
        if "$quiz" in message.content:
            return
        player = str(message.author)
        username = StringHelper.make_valid_firebase_name(player.split("#")[0])
        user_rating_path = "{0}/{1}/{2}".format(self.game_name, username, FIREBASE_RATING_REF)
        user_best_streak_path = "{0}/{1}/{2}".format(self.game_name, username, FIREBASE_BEST_STREAK_REF)
        user_current_streak_path = "{0}/{1}/{2}".format(self.game_name, username, FIREBASE_CURRENT_STREAK_REF)
        user_games_played_path = "{0}/{1}/{2}".format(self.game_name, username, FIREBASE_GAMES_PLAYED_REF)
        current_rating = int(self.firebase_interactor.read_from_node(user_rating_path))
        best_streak = int(self.firebase_interactor.read_from_node(user_best_streak_path))
        current_streak = int(self.firebase_interactor.read_from_node(user_current_streak_path))
        games_played = int(self.firebase_interactor.read_from_node(user_games_played_path))
        correct_answer: str = self.players[player]
        if answer.lower() != correct_answer.lower():
            rating_decrement = random.randint(1, 5)
            updated_rating = current_rating - rating_decrement
            if updated_rating < 0:
                updated_rating = 0
            self.firebase_interactor.write_to_node(user_rating_path, updated_rating)
            self.firebase_interactor.write_to_node(user_current_streak_path, 0)
            if current_streak > best_streak:
                self.firebase_interactor.write_to_node(user_best_streak_path, current_streak)
            await ChannelInteractor.send_message(
                message,
                "Sorry, {0}, that is incorrect. Was looking for:\n{1}\n\nStreak reset from: {4}\nBest streak: {5}"
                .format(username, correct_answer, current_rating, updated_rating, current_streak, best_streak)
            )
        else:
            rating_increment = random.randint(5, 15)
            self.firebase_interactor.write_to_node(user_rating_path, current_rating + rating_increment)
            self.firebase_interactor.write_to_node(user_current_streak_path, current_streak + 1)
            await ChannelInteractor.send_message(
                message,
                "Congratulations, {0}, that is correct!\nCurrent streak: {1}"
                .format(username, current_streak + 1)
            )
        self.firebase_interactor.write_to_node(user_games_played_path, games_played + 1)
        self.players.__delitem__(player)

    def check_and_create_player_data(self, username: str):
        user_rating_path = "{0}/{1}/{2}".format(self.game_name, username, FIREBASE_RATING_REF)
        user_best_streak_path = "{0}/{1}/{2}".format(self.game_name, username, FIREBASE_BEST_STREAK_REF)
        user_current_streak_path = "{0}/{1}/{2}".format(self.game_name, username, FIREBASE_CURRENT_STREAK_REF)
        user_games_played_path = "{0}/{1}/{2}".format(self.game_name, username, FIREBASE_GAMES_PLAYED_REF)
        if not self.firebase_interactor.check_node_exists(user_rating_path):
            self.firebase_interactor.write_to_node(user_rating_path, DEFAULT_POINTS)
        if not self.firebase_interactor.check_node_exists(user_best_streak_path):
            self.firebase_interactor.write_to_node(user_best_streak_path, 0)
        if not self.firebase_interactor.check_node_exists(user_current_streak_path):
            self.firebase_interactor.write_to_node(user_current_streak_path, 0)
        if not self.firebase_interactor.check_node_exists(user_games_played_path):
            self.firebase_interactor.write_to_node(user_games_played_path, 0)

    ###########
    # Setters #
    ###########
    def set_game_channel(self, game_channel: str):
        self.game_channel_name = game_channel
