import os
from datetime import datetime

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
    "gambles_total_winnings": 0,
    "gambles_total_losses": 0,
    "blackjacks_won": 0,
    "blackjacks_lost": 0,
    "blackjacks_played": 0,
    "blackjacks_total_winnings": 0,
    "blackjacks_total_losses": 0,
    "slots_won": 0,
    "slots_lost": 0,
    "slots_played": 0,
    "slots_total_winnings": 0,
    "slots_total_losses": 0,
    "wordles_won": 0,
    "wordles_lost": 0,
    "wordles_played": 0,
    "daily_streak": 0,
    "last_daily": 0,
    "last_heist": 0,
    "last_steal": 0,
    # 🎯 Heist stats
    "heists_joined": 0,
    "heists_won": 0,
    "heists_lost": 0,
    "total_loot_gained": 0,
    "total_loot_lost": 0,
    "backstabs": 0,
    "times_betrayed": 0,
    # Duel Stats:
    "duels_won": 0,
    "duels_lost": 0,
    "duels_tied": 0,
    # Steal Stats
    "steals_attempted": 0,  # Total number of steal attempts by the user
    "steals_successful": 0,  # Total number of successful steals by the user
    "steals_failed": 0,  # Total number of failed steal attempts by the user
    "total_amount_stolen": 0,  # Amount successfully stolen by the user
    "amount_lost_to_failed_steals": 0,  # Amount the user lost from failed steal attempts
    "amount_stolen_by_others": 0,  # Amount stolen from the user by others
    "times_stolen_from": 0,  # How many times the user has been stolen from
    "amount_gained_from_failed_steals": 0,  # Amount the user gained from failed steal attempts (from others' failed steals)
    # Mining Stats
    "mining_level": 1,
    "mining_xp": 0,
    "next_level_xp": 50,
    # Fishing Stats
    "fishing_level": 1,
    "fishing_xp": 0,
    "fishing_next_level_xp": 50,
    # Inventory System
    "inventory": [],  # Array to hold the inventory items
    # Bank
    "bank": 0,  # Bank balance
    # highlow game
    "highlow_won": 0,
    "highlow_lost": 0,
    "highlow_played": 0,
    "highlow_total_winnings": 0,
    "highlow_total_losses": 0,
    "highlow_biggest_multiplier": 0,
    # roulette game
    "roulette_won": 0,
    "roulette_lost": 0,
    "roulette_played": 0,
    "roulette_total_winnings": 0,
    "roulette_total_losses": 0,
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
        user_data["gambles_total_winnings"],
        user_data["gambles_total_losses"],
    )


def blackjack_stats(member: discord.Member):
    """Retrieve blackjack stats for the user, initializing fields if they don't exist."""
    user_data = get_user_data(member)
    return (
        user_data["blackjacks_won"],
        user_data["blackjacks_lost"],
        user_data["blackjacks_played"],
        user_data["blackjacks_total_winnings"],
        user_data["blackjacks_total_losses"],
    )


def slots_stats(member: discord.Member):
    """Retrieve slots stats for the user, initializing fields if they don't exist."""
    user_data = get_user_data(member)
    return (
        user_data["slots_won"],
        user_data["slots_lost"],
        user_data["slots_played"],
        user_data["slots_total_winnings"],
        user_data["slots_total_losses"],
    )


def wordle_stats(member: discord.Member):
    """Retreive wordle stats for the user, initializing fields if they don't exist."""
    user_data = get_user_data(member)
    return (
        user_data["wordles_won"],
        user_data["wordles_lost"],
        user_data["wordles_played"],
    )


def heist_stats(member: discord.Member):
    """Retrieve heist stats for the user, initializing fields if they don't exist."""
    user_data = get_user_data(member)

    return {
        "heists_joined": user_data.get("heists_joined", 0),
        "heists_won": user_data.get("heists_won", 0),
        "heists_lost": user_data.get("heists_lost", 0),
        "total_loot_gained": user_data.get("total_loot_gained", 0),
        "total_loot_lost": user_data.get("total_loot_lost", 0),
        "backstabs": user_data.get("backstabs", 0),
        "times_betrayed": user_data.get("times_betrayed", 0),
    }


def mine_stats(member: discord.Member):
    """Retrieve mining stats for the user, initializing fields if they don't exist."""
    user_data = get_user_data(member)

    return {
        "mining_level": user_data.get("mining_level", 1),
        "mining_xp": user_data.get("mining_xp", 0),
        "next_level_xp": user_data.get("next_level_xp", 50),
    }


def fish_stats(member: discord.Member):
    """Retrieve fishing stats for the user, initializing fields if they don't exist."""
    user_data = get_user_data(member)

    return {
        "fishing_level": user_data.get("fishing_level", 1),
        "fishing_xp": user_data.get("fishing_xp", 0),
        "fishing_next_level_xp": user_data.get("fishing_next_level_xp", 50),
    }


def highlow_stats(member: discord.Member):
    """Retrieve highlow stats for the user, initializing fields if they don't exist."""
    user_data = get_user_data(member)

    return {
        "highlow_won": user_data.get("highlow_won", 0),
        "highlow_lost": user_data.get("highlow_lost", 0),
        "highlow_played": user_data.get("highlow_played", 0),
        "highlow_total_winnings": user_data.get("highlow_total_winnings", 0),
        "highlow_total_losses": user_data.get("highlow_total_losses", 0),
        "highlow_biggest_multiplier": user_data.get("highlow_biggest_multiplier", 0),
    }


def roulette_stats(member: discord.Member):
    """Retrieve roulette stats for the user, initializing fields if they don't exist."""
    user_data = get_user_data(member)

    return {
        "roulette_won": user_data.get("roulette_won", 0),
        "roulette_lost": user_data.get("roulette_lost", 0),
        "roulette_played": user_data.get("roulette_played", 0),
        "roulette_total_winnings": user_data.get("roulette_total_winnings", 0),
        "roulette_total_losses": user_data.get("roulette_total_losses", 0),
    }


def all_stats(member: discord.Member):
    user_data = get_user_data(member)

    return {
        "gamble": {
            "won": user_data.get("gambles_won", 0),
            "lost": user_data.get("gambles_lost", 0),
            "played": user_data.get("gambles_played", 0),
            "total_winnings": user_data.get("gambles_total_winnings", 0),
            "total_losses": user_data.get("gambles_total_losses", 0),
        },
        "blackjack": {
            "won": user_data.get("blackjacks_won", 0),
            "lost": user_data.get("blackjacks_lost", 0),
            "played": user_data.get("blackjacks_played", 0),
            "total_winnings": user_data.get("blackjacks_total_winnings", 0),
            "total_losses": user_data.get("blackjacks_total_losses", 0),
        },
        "slots": {
            "won": user_data.get("slots_won", 0),
            "lost": user_data.get("slots_lost", 0),
            "played": user_data.get("slots_played", 0),
            "total_winnings": user_data.get("slots_total_winnings", 0),
            "total_losses": user_data.get("slots_total_losses", 0),
        },
        "wordle": {
            "won": user_data.get("wordles_won", 0),
            "lost": user_data.get("wordles_lost", 0),
            "played": user_data.get("wordles_played", 0),
        },
        "duel": {
            "won": user_data.get("duels_won", 0),
            "lost": user_data.get("duels_lost", 0),
            "tied": user_data.get("duels_tied", 0),
        },
        "heist": {
            "joined": user_data.get("heists_joined", 0),
            "won": user_data.get("heists_won", 0),
            "lost": user_data.get("heists_lost", 0),
            "loot_gained": user_data.get("total_loot_gained", 0),
            "loot_lost": user_data.get("total_loot_lost", 0),
            "backstabs": user_data.get("backstabs", 0),
            "betrayed": user_data.get("times_betrayed", 0),
        },
        "steal": {
            "attempted": user_data.get("steals_attempted", 0),
            "successful": user_data.get("steals_successful", 0),
            "failed": user_data.get("steals_failed", 0),
            "amount_stolen": user_data.get("total_amount_stolen", 0),
            "amount_lost_to_failed_steals": user_data.get(
                "amount_lost_to_failed_steals", 0
            ),
            "amount_stolen_by_others": user_data.get("amount_stolen_by_others", 0),
            "times_stolen_from": user_data.get("times_stolen_from", 0),
            "amount_gained_from_failed_steals": user_data.get(
                "amount_gained_from_failed_steals", 0
            ),
        },
        "mining": {
            "mining_level": user_data.get("mining_level", 1),
            "mining_xp": user_data.get("mining_xp", 0),
            "next_level_xp": user_data.get("next_level_xp", 50),
        },
        "fishing": {
            "fishing_level": user_data.get("fishing_level", 1),
            "fishing_xp": user_data.get("fishing_xp", 0),
            "fishing_next_level_xp": user_data.get("fishing_next_level_xp", 50),
        },
        "highlow": {
            "won": user_data.get("highlow_won", 0),
            "lost": user_data.get("highlow_lost", 0),
            "played": user_data.get("highlow_played", 0),
            "total_winnings": user_data.get("highlow_total_winnings", 0),
            "total_losses": user_data.get("highlow_total_losses", 0),
            "biggest_multiplier": user_data.get("highlow_biggest_multiplier", 0),
        },
        "roulette": {
            "won": user_data.get("roulette_won", 0),
            "lost": user_data.get("roulette_lost", 0),
            "played": user_data.get("roulette_played", 0),
            "total_winnings": user_data.get("roulette_total_winnings", 0),
            "total_losses": user_data.get("roulette_total_losses", 0),
        },
    }


def bank_stats(member: discord.Member):
    """Retrieve bank stats for the user, initializing fields if they don't exist."""
    user_data = get_user_data(member)

    return user_data.get("bank", 0)


def update_user_heist_stats(
    user: discord.User,
    loot_change: int = 0,
    won: bool = False,
    betrayed_others: bool = False,
    was_betrayed: bool = False,
):
    user_data = get_user_data(user)
    new_balance = max(0, user_data.get("balance", 0) + loot_change)

    update_fields = {
        "$set": {"balance": new_balance},
        "$inc": {
            "heists_joined": 1,
            "total_loot_gained": max(loot_change, 0),
            "total_loot_lost": abs(min(loot_change, 0)),
            "heists_won": 1 if won else 0,
            "heists_lost": 0 if won else 1,
            "backstabs": 1 if betrayed_others else 0,
            "times_betrayed": 1 if was_betrayed else 0,
        },
    }

    collection.update_one({"_id": user.id}, update_fields, upsert=True)


def update_user_duel_stats(
    user: discord.User, result: str, balance_change: int = 0  # 'win', 'lose', or 'tie'
):
    user_data = get_user_data(user)
    update_fields = {"$inc": {}}

    if result == "win":
        update_fields["$inc"]["duels_won"] = 1
    elif result == "lose":
        update_fields["$inc"]["duels_lost"] = 1
    elif result == "tie":
        update_fields["$inc"]["duels_tied"] = 1

    if balance_change != 0:
        update_fields["$inc"]["balance"] = balance_change

    update_fields["$inc"]["duels_played"] = 1

    collection.update_one({"_id": user.id}, update_fields)


def update_user_steal_stats(
    user: discord.User,
    success: bool,
    amount: int,
    balance: int,
    update_last_steal: bool = False,
    got_stolen: bool = False,
    gained_on_fail: int = 0,
    update_last_stolen: bool = False,  # NEW PARAM
):
    now = datetime.utcnow()

    update_fields = {
        "$inc": {
            "steals_attempted": 1 if not got_stolen else 0,
            "steals_successful": 1 if success and not got_stolen else 0,
            "steals_failed": 1 if not success and not got_stolen else 0,
            "total_amount_stolen": amount if success and not got_stolen else 0,
            "amount_lost_to_failed_steals": (
                amount if not success and not got_stolen else 0
            ),
            "amount_stolen_by_others": amount if got_stolen else 0,
            "times_stolen_from": 1 if got_stolen else 0,
            "amount_gained_from_failed_steals": gained_on_fail if got_stolen else 0,
        },
        "$set": {
            "balance": balance,
        },
    }

    if update_last_steal and not got_stolen:
        update_fields["$set"]["last_steal"] = now

    if update_last_stolen:
        update_fields["$set"]["last_stolen"] = now

    collection.update_one({"_id": user.id}, update_fields, upsert=True)


def update_user_mine_stats(user: discord.User, xp_gain: int, balance_change: int):
    user_data = get_user_data(user)

    current_xp = user_data.get("mining_xp", 0) + xp_gain
    base_xp = 50
    exponent = 1.5

    # Determine new level and total XP needed up to that level
    new_level = 1
    total_xp_required = 0
    xp_for_next = int(base_xp * (new_level**exponent))

    while current_xp >= total_xp_required + xp_for_next:
        total_xp_required += xp_for_next
        new_level += 1
        xp_for_next = int(base_xp * (new_level**exponent))

    # Cap the level at 99
    new_level = min(new_level, 99)

    # XP needed for next level
    next_level_xp = int(base_xp * ((new_level) ** exponent))
    xp_progress = current_xp - total_xp_required
    xp_needed = next_level_xp - xp_progress

    # Check for rewards if the user leveled up
    reward_message = reward_player_for_level_up(user, new_level, type="mining")

    # Update user stats in the database
    collection.update_one(
        {"_id": user.id},
        {
            "$set": {
                "mining_xp": current_xp,
                "mining_level": new_level,
                "next_level_xp": current_xp + xp_needed,
            },
            "$inc": {
                "balance": balance_change,
            },
        },
    )

    return new_level, current_xp, xp_needed, reward_message


def update_user_fish_stats(user: discord.User, xp_gain: int, balance_change: int):
    user_data = get_user_data(user)

    current_xp = user_data.get("fishing_xp", 0) + xp_gain
    base_xp = 50
    exponent = 1.5

    # Determine new level and total XP needed up to that level
    new_level = 1
    total_xp_required = 0
    xp_for_next = int(base_xp * (new_level**exponent))

    while current_xp >= total_xp_required + xp_for_next:
        total_xp_required += xp_for_next
        new_level += 1
        xp_for_next = int(base_xp * (new_level**exponent))

    # Cap the level at 99
    new_level = min(new_level, 99)

    # XP needed for next level
    next_level_xp = int(base_xp * ((new_level) ** exponent))
    xp_progress = current_xp - total_xp_required
    xp_needed = next_level_xp - xp_progress

    # Check for rewards if the user leveled up
    reward_message = reward_player_for_level_up(user, new_level, type="fishing")

    # Update user stats in the database
    collection.update_one(
        {"_id": user.id},
        {
            "$set": {
                "fishing_xp": current_xp,
                "fishing_level": new_level,
                "fishing_next_level_xp": current_xp + xp_needed,
            },
            "$inc": {
                "balance": balance_change,
            },
        },
    )

    return new_level, current_xp, xp_needed, reward_message


def update_user_highlow_stats(
    user: discord.User,
    result: str,
    amount: int = 0,
    multiplier: float = 0.0,
):
    user_data = get_user_data(user)
    update_fields = {"$inc": {}}

    if result == "win":
        # Ensure $set exists before using it
        if "$set" not in update_fields:
            update_fields["$set"] = {}
        update_fields["$inc"]["highlow_won"] = 1
        update_fields["$inc"]["highlow_total_winnings"] = amount
        update_fields["$set"]["highlow_biggest_multiplier"] = max(
            user_data.get("highlow_biggest_multiplier", 0), multiplier
        )
    elif result == "lose":
        update_fields["$inc"]["highlow_lost"] = 1
        update_fields["$inc"]["highlow_total_losses"] = amount

    update_fields["$inc"]["highlow_played"] = 1

    collection.update_one({"_id": user.id}, update_fields)


def add_item_to_inventory(
    user, item_name, quantity=1, rarity="common", level_required=1, type="tool"
):
    # Fetch user data from the database
    user_data = get_user_data(user)
    message = ""

    # Check if the item already exists in the inventory
    item_exists = False
    for item in user_data["inventory"]:
        if item["name"] == item_name:
            # If it's a tool, do not increase quantity
            if type != "tool":
                item["quantity"] += quantity
                message = (
                    f"Your {item_name} quantity has been updated to {item['quantity']}!"
                )
            item_exists = True
            break

    # If the item doesn't exist, add it to the inventory
    if not item_exists:
        user_data["inventory"].append(
            {
                "name": item_name,
                "quantity": quantity,
                "rarity": rarity,
                "level_required": level_required,
                "type": type,
            }
        )
        message = f"You have added a new item to your inventory: {item_name}!"

    # Save the updated inventory back to the database
    collection.update_one(
        {"_id": user.id}, {"$set": {"inventory": user_data["inventory"]}}
    )

    # Return the message
    return message


def remove_item_from_inventory(user, item_name, quantity=1):
    # Fetch user data from the database
    user_data = get_user_data(user)

    # Find the item in the inventory
    for item in user_data["inventory"]:
        if item["name"] == item_name:
            if item["quantity"] >= quantity:
                item["quantity"] -= quantity
                if item["quantity"] == 0:
                    user_data["inventory"].remove(item)
                break
            else:
                return "Not enough quantity to remove"

    # Save the updated inventory back to the database
    collection.update_one(
        {"_id": user.id}, {"$set": {"inventory": user_data["inventory"]}}
    )


def get_user_inventory(user: discord.Member) -> set[str]:
    user_data = get_user_data(user)

    if not user_data or "inventory" not in user_data:
        return set()

    # Create a list of dictionaries with the desired attributes for each item
    inventory = [
        {
            "name": item["name"],
            "quantity": item.get(
                "quantity", 0
            ),  # Default to 0 if 'quantity' is not found
            "rarity": item.get(
                "rarity", "Unknown"
            ),  # Default to 'Unknown' if 'rarity' is not found
            "level": item.get("level", 0),  # Default to 0 if 'level' is not found
            "required": item.get(
                "required", "None"
            ),  # Default to 'None' if 'required' is not found
            "tool_type": item.get(
                "tool_type", "None"
            ),  # Default to 'None' if 'tool_type' is not found
        }
        for item in user_data["inventory"]
    ]

    return inventory


def reward_player_for_level_up(user: discord.User, level, type="mining"):
    message = ""  # Final return message
    milestone_messages = []

    # Define milestone rewards
    milestone_rewards = {
        20: "Stone",
        40: "Iron",
        60: "Gold",
        80: "Diamond",
        99: "netherite",
    }

    for milestone_level, name in milestone_rewards.items():
        if level >= milestone_level:
            # Build the item name
            tool_name = f"{name} Pickaxe" if type == "mining" else f"{name} Fishing Rod"

            # Check if the user already has this tool

            inventory = get_user_inventory(user)
            if tool_name not in inventory:
                rarity_map = {
                    "Stone": "uncommon",
                    "Iron": "rare",
                    "Gold": "epic",
                    "Diamond": "legendary",
                    "netherite": "netherite",
                }
                reward_msg = add_item_to_inventory(
                    user, tool_name, 1, rarity_map[name], milestone_level, "tool"
                )
                milestone_messages.append(reward_msg)

    if milestone_messages:
        message = "\n".join(milestone_messages)

    return message


def update_user_bank_stats(user: discord.User, amount: int) -> tuple[int, bool]:
    # Fetch user data from the database
    user_data = get_user_data(user)

    # Get current balance
    current_balance = user_data.get("bank", 0)

    new_balance = current_balance + amount

    # Save new balance to the database
    collection.update_one({"_id": user.id}, {"$set": {"bank": new_balance}})

    return new_balance


def update_balance(user: discord.User, amount: int) -> tuple[int, bool]:
    # Fetch user data from the database
    user_data = get_user_data(user)

    # Save new balance to the database
    collection.update_one({"_id": user.id}, {"$set": {"balance": amount}})


def update_user_slots_stats(
    user: discord.User,
    result: str,
    amount: int = 0,
):
    user_data = get_user_data(user)
    update_fields = {"$inc": {}}

    if result == "win":
        update_fields["$inc"]["slots_won"] = 1
        update_fields["$inc"]["slots_total_winnings"] = amount
    elif result == "lose":
        update_fields["$inc"]["slots_lost"] = 1
        update_fields["$inc"]["slots_total_losses"] = amount

    update_fields["$inc"]["slots_played"] = 1

    collection.update_one({"_id": user.id}, update_fields)


def update_user_gamble_stats(
    user: discord.User,
    result: str,
    amount: int = 0,
):
    user_data = get_user_data(user)
    update_fields = {"$inc": {}}

    if result == "win":
        update_fields["$inc"]["gambles_won"] = 1
        update_fields["$inc"]["gambles_total_winnings"] = amount
    elif result == "lose":
        update_fields["$inc"]["gambles_lost"] = 1
        update_fields["$inc"]["gambles_total_losses"] = amount

    update_fields["$inc"]["gambles_played"] = 1

    collection.update_one({"_id": user.id}, update_fields)


def update_user_blackjack_stats(
    user: discord.User,
    result: str,
    amount: int = 0,
):
    user_data = get_user_data(user)
    update_fields = {"$inc": {}}

    if result == "win":
        update_fields["$inc"]["blackjacks_won"] = 1
        update_fields["$inc"]["blackjacks_total_winnings"] = amount
    elif result == "lose":
        update_fields["$inc"]["blackjacks_lost"] = 1
        update_fields["$inc"]["blackjacks_total_losses"] = amount

    update_fields["$inc"]["blackjacks_played"] = 1

    collection.update_one({"_id": user.id}, update_fields)


def update_user_roulette_stats(
    user: discord.User,
    result: str,
    amount: int = 0,
):
    user_data = get_user_data(user)
    update_fields = {"$inc": {}}

    if result == "win":
        update_fields["$inc"]["roulette_won"] = 1
        update_fields["$inc"]["roulette_total_winnings"] = amount
    elif result == "lose":
        update_fields["$inc"]["roulette_lost"] = 1
        update_fields["$inc"]["roulette_total_losses"] = amount

    update_fields["$inc"]["roulette_played"] = 1

    collection.update_one({"_id": user.id}, update_fields)
