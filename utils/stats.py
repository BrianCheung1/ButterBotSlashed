from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv
from pymongo import MongoClient
from typing import Optional
import discord
import os
import random

load_dotenv()
MONGO_URL = os.getenv("ATLAS_URI")
cluster = MongoClient(MONGO_URL)
db = cluster["Users"]
collection = db["UserData"]


def balance_of_player(member: discord.Member):
    search = {"_id": member.id}
    if collection.count_documents(search) == 0:
        post = {"_id": member.id, "balance": 1000}
        collection.insert_one(post)
    user = collection.find(search)
    for result in user:
        balance = result["balance"]
        prev_balance = balance
    return prev_balance, balance


def gamble_stats(member: discord.Member):
    search = {"_id": member.id}
    if collection.count_documents(search) == 0:
        post = {
            "_id": member.id,
            "balance": 1000,
        }
    user = collection.find(search)
    for result in user:
        if "gambles_won" and "gambles_lost" and "gambles_played" not in result:
            collection.update_one(
                {"_id": member.id},
                {"$set": {"gambles_won": 0, "gambles_lost": 0, "gambles_played": 0}},
            )
    user = collection.find(search)
    for result in user:
        gambles_won = result["gambles_won"]
        gambles_lost = result["gambles_lost"]
        gambles_played = result["gambles_played"]
    return gambles_won, gambles_lost, gambles_played


def blackjack_stats(member: discord.Member):
    search = {"_id": member.id}
    if collection.count_documents(search) == 0:
        post = {
            "_id": member.id,
            "balance": 1000,
        }
    user = collection.find(search)
    for result in user:
        if "blackjacks_won" and "blackjacks_lost" and "blackjacks_played" not in result:
            collection.update_one(
                {"_id": member.id},
                {
                    "$set": {
                        "blackjacks_won": 0,
                        "blackjacks_lost": 0,
                        "blackjacks_played": 0,
                    }
                },
            )
    user = collection.find(search)
    for result in user:
        blackjacks_won = result["blackjacks_won"]
        blackjacks_lost = result["blackjacks_lost"]
        blackjacks_played = result["blackjacks_played"]
    return blackjacks_won, blackjacks_lost, blackjacks_played


def slots_stats(member: discord.Member):
    search = {"_id": member.id}
    if collection.count_documents(search) == 0:
        post = {
            "_id": member.id,
            "balance": 1000,
        }
    user = collection.find(search)
    for result in user:
        if "slots_won" and "slots_lost" and "slots_played" not in result:
            collection.update_one(
                {"_id": member.id},
                {
                    "$set": {
                        "slots_won": 0,
                        "slots_lost": 0,
                        "slots_played": 0,
                    }
                },
            )
    user = collection.find(search)
    for result in user:
        slots_won = result["slots_won"]
        slots_lost = result["slots_lost"]
        slots_played = result["slots_played"]

    return slots_won, slots_lost, slots_played
