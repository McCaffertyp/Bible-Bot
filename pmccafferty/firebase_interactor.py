from pyrebase.pyrebase import Database

from util import logger

#############
# Constants #
#############
FIREBASE_CONFIG = {
    "apiKey": "AIzaSyBqzcUFslYLweMJjivRWNvuQm9JhDIsEfQ",
    "authDomain": "discord-bot-bible-bot.firebaseapp.com",
    "databaseURL": "https://discord-bot-bible-bot-default-rtdb.firebaseio.com",
    "projectId": "discord-bot-bible-bot",
    "storageBucket": "discord-bot-bible-bot.appspot.com",
    "messagingSenderId": "1050362656538",
    "appId": "1:1050362656538:web:fd25c7d4b47b7b9f3d1ea3",
    "measurementId": "G-QGWZYNXFEY"
}
FIREBASE_TOP_LEVEL_NODE = "servers"


class FirebaseInteractor:
    def __init__(self, database: Database, guild_string_ref: str):
        self.guild_string_ref: str = guild_string_ref
        self.database: Database = database

    def get_db_node(self) -> Database:
        return self.database.child(FIREBASE_TOP_LEVEL_NODE).child(self.guild_string_ref)

    def write_to_node(self, path: str, value):
        path_names = path.split("/")
        current_node: Database = self.get_db_node()
        for name in path_names:
            current_node = current_node.child(name)
        logger.d("Writing to database path={0}".format(current_node.path))
        current_node.set(value)

    def read_from_node(self, path: str):
        path_names = path.split("/")
        current_node: Database = self.get_db_node()
        for name in path_names:
            current_node = current_node.child(name)
        logger.d("Reading from database path={0}".format(current_node.path))
        return current_node.get().val()

    def check_node_exists(self, path: str) -> bool:
        path_names = path.split("/")
        current_node: Database = self.get_db_node()
        for name in path_names:
            current_node = current_node.child(name)

        logger.d("Checking database path={0} exists".format(current_node.path))
        if current_node.get().val():
            return True
        else:
            return False
