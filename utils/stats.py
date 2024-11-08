import os

import discord
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()
MONGO_URL = os.getenv("ATLAS_URI")
cluster = MongoClient(MONGO_URL)
db = cluster["Users"]
collection = db["UserData"]


# Default values for new user documents
DEFAULT_USER_DATA = {
    "_id": None,  # This will be set to the user's ID when updating
    "balance": 1000,
    "gambles_won": 0,
    "gambles_lost": 0,
    "gambles_played": 0,
    "blackjacks_won": 0,
    "blackjacks_lost": 0,
    "blackjacks_played": 0,
    "slots_won": 0,
    "slots_lost": 0,
    "slots_played": 0,
    "wordles_won": 0,
    "wordles_lost": 0,
    "wordles_played": 0,
}


def get_user_data(member: discord.Member):
    """Retrieve or initialize a user's data from the database."""
    search = {"_id": member.id}
    # Set missing keys using $set to fill in any missing fields with DEFAULT_USER_DATA values
    user_data = collection.find_one(search)
    if user_data:
        # Find missing fields and set them to default values
        missing_fields = {
            key: value
            for key, value in DEFAULT_USER_DATA.items()
            if key not in user_data
        }
        if missing_fields:
            collection.update_one(search, {"$set": missing_fields})
    else:
        # Insert new document with all default values
        user_data = DEFAULT_USER_DATA.copy()
        user_data["_id"] = member.id
        collection.insert_one(user_data)
    return collection.find_one(search)


def balance_of_player(member: discord.Member):
    """Retrieve the user's balance, initializing it if they don't have an account."""
    user_data = get_user_data(member)
    return user_data["balance"], user_data["balance"]


def gamble_stats(member: discord.Member):
    """Retrieve gamble stats for the user, initializing fields if they don't exist."""
    user_data = get_user_data(member)
    return (
        user_data["gambles_won"],
        user_data["gambles_lost"],
        user_data["gambles_played"],
    )


def blackjack_stats(member: discord.Member):
    """Retrieve blackjack stats for the user, initializing fields if they don't exist."""
    user_data = get_user_data(member)
    return (
        user_data["blackjacks_won"],
        user_data["blackjacks_lost"],
        user_data["blackjacks_played"],
    )


def slots_stats(member: discord.Member):
    """Retrieve slots stats for the user, initializing fields if they don't exist."""
    user_data = get_user_data(member)
    return user_data["slots_won"], user_data["slots_lost"], user_data["slots_played"]


def wordle_stats(member: discord.Member):
    """Retreive wordle stats for the user, initializing fields if they don't exist."""
    user_data = get_user_data(member)
    return (
        user_data["wordles_won"],
        user_data["wordles_lost"],
        user_data["wordles_played"],
    )
