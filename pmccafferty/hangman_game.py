from discord.member import Member
from discord.ext.commands import Bot
from discord.ext.commands.context import Context

import util.string as StringHelper
import channel_interactor as ChannelInteractor
import verse_interactor as VerseInteractor
from util import logger

#############
# Constants #
#############
LOG_TAG = "hangman_game"
HANGMAN_DICT_SOLUTION = "solution"
HANGMAN_DICT_PROGRESS = "progress"
HANGMAN_DICT_MISTAKES_LEFT = "mistakes"
HANGMAN_DICT_GUESSABLES = "guessables"
HANGMAN_DICT_GUESSES = "guesses"
HANGMAN_PREFILL_LEVEL_NONE = "none"
HANGMAN_PREFILL_LEVEL_LOW = "low"
HANGMAN_PREFILL_LEVEL_MEDIUM = "medium"
HANGMAN_PREFILL_LEVEL_HIGH = "high"


class Hangman:
    def __init__(self, bot: Bot, guild_name: str):
        self.bot = bot
        self.guild_name = guild_name
        self.game_name = ChannelInteractor.GAME_CHANNEL_HANGMAN
        self.game_channel_name = ChannelInteractor.GAME_CHANNEL_HANGMAN_DEFAULT_NAME
        self.players = {}

    async def start_game(self, context: Context, option: str = None, prefill_level: str = HANGMAN_PREFILL_LEVEL_NONE):
        if option is None:
            await ChannelInteractor.send_message(context, "No hangman option was provided. Please use $h for options.")
        else:
            prefill_level = prefill_level.lower()
            if (prefill_level != HANGMAN_PREFILL_LEVEL_NONE and prefill_level != HANGMAN_PREFILL_LEVEL_LOW and
                    prefill_level != HANGMAN_PREFILL_LEVEL_MEDIUM and prefill_level != HANGMAN_PREFILL_LEVEL_HIGH):
                await ChannelInteractor.send_message(context, "Prefill level for the verse specified is unrecognized. Please use $h for options.")
                return

            channel_exists = await ChannelInteractor.check_channel_exists(self.bot, self.guild_name, context, self.game_name, self.game_channel_name)
            if not channel_exists:
                return

            correct_channel = await ChannelInteractor.is_correct_channel(context, self.game_name, self.game_channel_name)
            if not correct_channel:
                return

            if option != "easy" and option != "medium" and option != "hard" and option != "status" and option != "quit":
                await ChannelInteractor.send_message(context, "The entered option \"{0}\" is unsupported.".format(option))
                return

            user: Member = context.author
            player = str(user)
            player_mention = user.mention

            if option == "status":
                if player not in self.players:
                    await ChannelInteractor.send_message(context, "{0} you have no ongoing games! Start one with: $hangman [difficulty] (prefill)".format(player_mention))
                    return
                else:
                    current_progress = self.players[player][HANGMAN_DICT_PROGRESS]
                    remaining_mistakes = self.players[player][HANGMAN_DICT_MISTAKES_LEFT]
                    remaining_letters = StringHelper.get_remaining_letters(self.players[player][HANGMAN_DICT_GUESSES])
                    status_update = "{0}\n\nRemaining Mistakes: {1}\n\nRemaining Letters: {2}".format(current_progress, remaining_mistakes, remaining_letters)
                    await ChannelInteractor.send_embedded_message(
                        context,
                        title="{0}'s Hangman - Status".format(user.display_name),
                        description=StringHelper.handle_discord_formatting(status_update)
                    )
                    return

            if option == "quit":
                if player not in self.players:
                    await ChannelInteractor.send_message(context, "{0} you have no ongoing games! Start one with: $hangman [difficulty] (prefill)".format(player_mention))
                    return
                else:
                    puzzle_solution = self.players[player][HANGMAN_DICT_SOLUTION]
                    status_update = "Sorry you chose to quit :(\nHere's your finished verse:\n{1}".format(player_mention, puzzle_solution)
                    self.players.__delitem__(player)
                    await ChannelInteractor.send_embedded_message(
                        context,
                        title="{0}'s Hangman - Quitting".format(user.display_name),
                        description=StringHelper.handle_discord_formatting(status_update)
                    )
                    return

            random_verse = VerseInteractor.get_random_verse()
            verse_text_start = random_verse.find("\"") + 1
            verse_text_end = random_verse.find("\"", verse_text_start)
            verse_text = random_verse[verse_text_start:verse_text_end]

            verse_reference_start_search = "\" - "
            verse_reference_start = random_verse.find(verse_reference_start_search) + len(verse_reference_start_search)
            verse_reference_end = random_verse.find(" ESV")
            verse_reference = random_verse[verse_reference_start:verse_reference_end]

            puzzle_solution = "\"{0}\" - {1}".format(verse_text, verse_reference)
            puzzle_progress = create_hangman_puzzle(puzzle_solution, prefill_level)

            self.players[player] = dict()
            self.players[player][HANGMAN_DICT_SOLUTION] = puzzle_solution
            self.players[player][HANGMAN_DICT_PROGRESS] = puzzle_progress
            self.players[player][HANGMAN_DICT_GUESSABLES] = populate_guessables(puzzle_solution, puzzle_progress)
            self.players[player][HANGMAN_DICT_GUESSES] = []
            if option == "easy":
                self.players[player][HANGMAN_DICT_MISTAKES_LEFT] = 10
            elif option == "medium":
                self.players[player][HANGMAN_DICT_MISTAKES_LEFT] = 5
            elif option == "hard":
                self.players[player][HANGMAN_DICT_MISTAKES_LEFT] = 3

            puzzle_preview = "Here's your puzzle!\n{0}\n\nYou have {1} allowed Mistakes.".format(
                puzzle_progress, self.players[player][HANGMAN_DICT_MISTAKES_LEFT]
            )
            await ChannelInteractor.send_embedded_message(
                context,
                title="{0}'s Hangman - Start".format(user.display_name),
                description=StringHelper.handle_discord_formatting(puzzle_preview)
            )

    async def submit_guess(self, context: Context, guess: str = None):
        if guess is None:
            await ChannelInteractor.send_message(context, "No guess was supplied!")
        elif len(guess) == 1 and guess.lower() not in StringHelper.ENGLISH_ALPHABET:
            await ChannelInteractor.send_message(context, "That guess is invalid!")
        else:
            player = str(context.author)
            player_mention = context.author.mention
            if player not in self.players:
                await ChannelInteractor.send_message(context, "{0} you have no ongoing games! Start one with: $hangman [difficulty] (prefill)".format(player_mention))
                return

            guess = guess.lower()
            previous_guesses = self.players[player][HANGMAN_DICT_GUESSES]
            if guess in previous_guesses:
                await ChannelInteractor.send_message(context, "{0} you have already guessed that! Try something else.".format(player_mention))
                return

            puzzle_solution = self.players[player][HANGMAN_DICT_SOLUTION]
            guessables: list = self.players[player][HANGMAN_DICT_GUESSABLES]
            if guess in guessables:
                if len(guess) == 1:
                    updated_progress = self.update_hangman_puzzle_progress_letter_guess(guess, player)
                    self.players[player][HANGMAN_DICT_PROGRESS] = updated_progress
                    self.players[player][HANGMAN_DICT_GUESSABLES].remove(guess)
                else:
                    updated_progress = self.update_hangman_puzzle_progress_word_guess(guess, player)
                    if updated_progress == "false":
                        await self.update_mistakes(context, player, player_mention, puzzle_solution)
                    else:
                        self.players[player][HANGMAN_DICT_PROGRESS] = updated_progress
                        self.players[player][HANGMAN_DICT_GUESSABLES].remove(guess)
                        self.update_guessables(player, puzzle_solution, updated_progress)
            else:
                await self.update_mistakes(context, player, player_mention, puzzle_solution)

            self.players[player][HANGMAN_DICT_GUESSES].append(guess)
            current_progress = self.players[player][HANGMAN_DICT_PROGRESS]
            if puzzle_solution == current_progress:
                await self.on_solved(context, player, puzzle_solution)
            else:
                await self.on_progress(context, player, current_progress)

    def update_hangman_puzzle_progress_letter_guess(self, guess: str, player: str) -> str:
        solution_characters = [c for c in self.players[player][HANGMAN_DICT_SOLUTION]]
        progress_characters = [c for c in self.players[player][HANGMAN_DICT_PROGRESS]]
        updated_puzzle = ""

        for i in range(0, len(solution_characters)):
            if solution_characters[i].lower() == guess:
                updated_puzzle = "{0}{1}".format(updated_puzzle, solution_characters[i])
            else:
                updated_puzzle = "{0}{1}".format(updated_puzzle, progress_characters[i])

        return updated_puzzle

    def update_hangman_puzzle_progress_word_guess(self, guess: str, player: str) -> str:
        guess_len = len(guess)
        solution: str = self.players[player][HANGMAN_DICT_SOLUTION]
        guess_start_index = solution.lower().find(guess)
        updated_puzzle: str = self.players[player][HANGMAN_DICT_PROGRESS]
        full_word_accuracy = False

        while guess_start_index != -1:
            guess_end_index = guess_start_index + guess_len
            if solution[guess_end_index] not in StringHelper.ENGLISH_ALPHABET:
                updated_puzzle = "{0}{1}{2}".format(
                    updated_puzzle[:guess_start_index], solution[guess_start_index:guess_end_index], updated_puzzle[guess_end_index:]
                )
                full_word_accuracy = True
            guess_start_index = solution.lower().find(guess, (guess_end_index + 1))

        if full_word_accuracy:
            return updated_puzzle
        else:
            return "false"

    def update_guessables(self, player, puzzle_solution: str, puzzle_progress: str):
        guessables = self.players[player][HANGMAN_DICT_GUESSABLES]
        guessable_letters = get_guessable_letters(puzzle_solution, puzzle_progress)
        for i in range(0, len(guessables)):
            if len(guessables[i]) == 1 and len(guessables[i + 1]) == 1:
                guessables = guessables[0:i]
                break
        self.players[player][HANGMAN_DICT_GUESSABLES] = guessables + guessable_letters

    async def update_mistakes(self, context: Context, player: str, player_mention: str, puzzle_solution: str):
        mistakes_remaining = int(self.players[player][HANGMAN_DICT_MISTAKES_LEFT])
        updated_mistakes_remaining = mistakes_remaining - 1
        if updated_mistakes_remaining == 0:
            status_update = "Unfortunate, {0}. You ran out of mistakes. Here's the verse:\n{1}".format(player_mention, puzzle_solution)
            await ChannelInteractor.send_message(context, StringHelper.handle_discord_formatting(status_update))
            self.players.__delitem__(player)
            return
        self.players[player][HANGMAN_DICT_MISTAKES_LEFT] = updated_mistakes_remaining

    async def on_progress(self, context: Context, player: str, current_progress: str):
        remaining_mistakes = self.players[player][HANGMAN_DICT_MISTAKES_LEFT]
        remaining_letters = StringHelper.get_remaining_letters(self.players[player][HANGMAN_DICT_GUESSES])
        status_update = "{0}\n\nRemaining Mistakes: {1}\n\nRemaining Letters: {2}".format(
            current_progress, remaining_mistakes, remaining_letters
        )
        await ChannelInteractor.send_embedded_message(
            context,
            title="{0}'s Hangman - Progress".format(context.author.display_name),
            description=StringHelper.handle_discord_formatting(status_update)
        )

    async def on_solved(self, context: Context, player: str, puzzle_solution: str):
        status_update = "You finished the verse!\n{0}".format(puzzle_solution)
        self.players.__delitem__(player)
        await ChannelInteractor.send_embedded_message(
            context,
            title="{0}'s Hangman - Finished".format(context.author.display_name),
            description=StringHelper.handle_discord_formatting(status_update)
        )

    ###########
    # Setters #
    ###########
    def set_game_channel(self, game_channel: str):
        self.game_channel_name = game_channel


def create_hangman_puzzle(verse: str, prefill_level: str) -> str:
    if prefill_level == HANGMAN_PREFILL_LEVEL_NONE:
        puzzle = ""
        for c in verse:
            if c.lower() in StringHelper.ENGLISH_ALPHABET:
                puzzle = "{0}_".format(puzzle)
            else:
                puzzle = "{0}{1}".format(puzzle, c)
        return puzzle
    else:
        words_in_verse = StringHelper.get_only_words(verse.split())
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
            logger.e(LOG_TAG, "Every prefill option for hangman was passed over. Should not be possible.")
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


def section_hangman_puzzle(words_in_verse: list) -> list:
    sections = []
    sub_section_size = 4
    for i in range(0, len(words_in_verse), sub_section_size):
        sub_section = words_in_verse[i:(i + sub_section_size)]
        sections.append(sub_section)
    return sections


def populate_guessables(puzzle_solution: str, puzzle_progress: str) -> list:
    guessables = StringHelper.get_only_words(puzzle_solution.split())
    guessable_letters = get_guessable_letters(puzzle_solution, puzzle_progress)
    return guessables + guessable_letters


def get_guessable_letters(puzzle_solution: str, puzzle_progress: str) -> list:
    guessable_letters = []
    for i in range(0, len(puzzle_solution)):
        psc = puzzle_solution[i].lower()
        ppc = puzzle_progress[i].lower()
        if psc in StringHelper.ENGLISH_ALPHABET and psc not in guessable_letters and ppc == "_":
            guessable_letters.append(psc)
    return guessable_letters
