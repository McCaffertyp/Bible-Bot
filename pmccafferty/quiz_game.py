import random

from discord.ext.commands import Bot
from discord.ext.commands.context import Context

import channel_interactor as ChannelInteractor
import util.string as StringHelper
import verse_helper as VerseHelper
from util import logger


class Quiz:
    def __init__(self, bot: Bot, guild_name: str, excluded_quiz_words: list):
        self.bot = bot
        self.guild_name = guild_name
        self.excluded_quiz_words = excluded_quiz_words
        self.game_name = "quiz"
        self.game_channel_name = "bible-quizzing"
        self.players = {}

    async def start_game(self, context: Context, option: str = None, book: str = None):
        channel_exists = await ChannelInteractor.check_channel_exists(self.bot, self.guild_name, context, self.game_name, self.game_channel_name)
        if not channel_exists:
            return

        correct_channel = await ChannelInteractor.is_correct_channel(context, self.game_name, self.game_channel_name)
        if not correct_channel:
            return

        player = str(context.author)
        username = player.split("#")[0]
        if option is None:
            await ChannelInteractor.send_message(context,
                                                 "{0} provided no option. Choosing a random one.".format(username))
            options = ["ref", "word", "sentence"]
            option = options[random.randint(0, 2)]
            await ChannelInteractor.send_message(context,
                                                 "{0} your quizzing option is on: {1}".format(username, option))

        random_verse = VerseHelper.get_random_verse(book)
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
            quiz_verse = StringHelper.replace_characters(random_verse, verse_reference, "_")
            self.players[player] = verse_reference
        elif option == "word":
            verse_words = verse_text.split(" ")
            full_remove_word = verse_words[random.randint(0, (len(verse_words) - 1))]
            remove_word = StringHelper.remove_non_alphabet(full_remove_word)
            while remove_word.lower() in self.excluded_quiz_words:
                logger.d("Tried to remove \"{0}\" from verse. Fetching new word...".format(remove_word))
                full_remove_word = verse_words[random.randint(0, (len(verse_words) - 1))]
                remove_word = StringHelper.remove_non_alphabet(full_remove_word)
            quiz_verse = StringHelper.replace_characters(random_verse, remove_word, "_")
            self.players[player] = remove_word
        elif option == "sentence":
            verse_words = verse_text.split(" ")
            remove_word_count = random.randint(2, (len(verse_words) - 1))
            remove_start_word_index = random.randint(0, (len(verse_words) - remove_word_count))
            remove_end_word_index = remove_start_word_index + remove_word_count - 1
            remove_start_word = verse_words[remove_start_word_index]
            remove_end_word = verse_words[remove_end_word_index]
            remove_sentence = random_verse[random_verse.find(remove_start_word):(
                        random_verse.find(remove_end_word) + len(remove_end_word))]
            quiz_verse = StringHelper.replace_characters(random_verse, remove_sentence, "_")
            self.players[player] = remove_sentence
            # all_words = ""
            # for i in range(remove_start_index, (remove_start_index + remove_word_count)):
            #     remove_word = verse_words[i].replace(",", "")
            #     quiz_verse = replace_characters(quiz_verse, remove_word, "_")
            #     all_words = "{0},{1}".format(all_words, remove_word)
            # quizzing[player] = all_words[1:(len(all_words) - 1)]
        else:
            await ChannelInteractor.send_message(context, "{0}, that option is unsupported.".format(context.author.mention))
            return

        await ChannelInteractor.send_message(context, "{0}, your quiz is:\n{1}".format(context.author.mention, quiz_verse))

    async def check_answer(self, message, answer: str):
        if "$quiz" in message.content:
            return
        player = str(message.author)
        username = player.split("#")[0]
        correct_answer: str = self.players[player]
        if answer.lower() != correct_answer.lower():
            await ChannelInteractor.send_message(message, "Sorry, {0}, that is incorrect. Was looking for:\n{1}".format(username, correct_answer))
        else:
            await ChannelInteractor.send_message(message, "Congratulations, {0}, that is correct!".format(username))
        self.players.__delitem__(player)

    ###########
    # Setters #
    ###########
    def set_game_channel(self, game_channel: str):
        self.game_channel_name = game_channel
