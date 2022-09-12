from dotenv import load_dotenv
from pymongo import MongoClient
import os
import discord

MONGO_URL = os.getenv("ATLAS_URI")
cluster = MongoClient(MONGO_URL)
db = cluster["Users"]
collection = db["UserData"]


def balance_of_player(member: discord.member):
    search = {"_id": member.id}
    if collection.count_documents(search) == 0:
        post = {"_id": member.id, "balance": 1000}
        collection.insert_one(post)
    user = collection.find(search)
    for result in user:
        balance = result["balance"]
        prev_balance = balance
    return prev_balance, balance
