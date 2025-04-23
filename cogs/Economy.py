import os
import random
from typing import Optional

import discord
import matplotlib.pyplot as plt
import io
import numpy as np
from discord import app_commands, Interaction, Member
from discord.ext import commands, tasks
from dotenv import load_dotenv
from pymongo import MongoClient
from datetime import datetime, timedelta
from utils.stats import (
    balance_of_player,
    update_user_heist_stats,
    update_user_duel_stats,
    update_user_steal_stats,
    update_user_mine_stats,
    update_user_fish_stats,
    mine_stats,
    fish_stats,
    get_user_inventory,
    bank_stats,
    update_user_bank_stats,
    update_balance,
    update_user_highlow_stats,
    update_user_roulette_stats,
    roulette_stats,
)
from utils.embeds import create_embed
from discord.ui import Button, View

import asyncio


load_dotenv()
MONGO_URL = os.getenv("ATLAS_URI")
cluster = MongoClient(MONGO_URL)
db = cluster["Users"]
collection = db["UserData"]


class Economy(commands.Cog):
    """Economy Features"""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.active_heist_users: set[int] = set()
        self.active_heist_creators = set()
        self.add_interest.start()

    @app_commands.command(name="give", description="Give users money")
    @app_commands.describe(
        member="The member you want to give money to",
        amount="The amount you want to give",
    )
    async def give(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        amount: app_commands.Range[int, 1, None],
    ):
        await interaction.response.defer(thinking=True)
        prev_balance, balance = balance_of_player(member)
        app = await interaction.client.application_info()
        if interaction.user.id == app.owner.id:
            balance += amount
            collection.update_one({"_id": member.id}, {"$set": {"balance": balance}})
            await interaction.followup.send(f"{member.mention} now has ${balance:,.2f}")
        else:
            prev_balance, user_balance = balance_of_player(interaction.user)
            if amount > user_balance:
                await interaction.followup.send(
                    f"{interaction.user.mention} is too broke to give away money - they only have {user_balance:,.2f}"
                )
            else:
                balance += amount
                collection.update_one(
                    {"_id": member.id},
                    {"$set": {"balance": balance}},
                )
                user_balance -= amount
                collection.update_one(
                    {"_id": interaction.user.id},
                    {"$set": {"balance": user_balance}},
                )
                await interaction.followup.send(
                    f"{member.mention} now has ${balance:,}"
                )

    @app_commands.command(name="mine", description="Mine ores for money")
    async def mine(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True)

        (
            result,
            payout,
            loss,
            total_payout,
            bonus,
            new_balance,
            new_level,
            xp,
            xp_needed,
            reward_message,
            pickaxe,
            pickaxe_bonus,
        ) = await run_mining_logic(interaction.user)
        if payout > 0:
            msg = (
                f"{interaction.user.mention} mined and found **{result}**, worth ${payout:,.2f}!\n"
                f"💰 **Base Reward:** ${payout:,.2f}\n"
                f"🎉 **Bonus from Level ({new_level}):** +${bonus:,.2f}\n"
                f"⛏️ **Pickaxe Used:** {pickaxe.title()} +${pickaxe_bonus:,.2f}\n"
                f"💸 **Total Payout:** ${total_payout:,.2f}\n"
                f"💰 New Balance: ${new_balance:,.2f}\n\n"
                f"**Current Level:** {new_level}\n**Current XP:** {xp}\n**XP Needed for Next Level:** {xp_needed}"
            )
        elif loss > 0:
            msg = (
                f"{interaction.user.mention} encountered **{result}** and lost **${loss:,.2f}**! 😵\n"
                f"💸 New Balance: ${new_balance:,.2f}\n\n"
                f"**Current Level:** {new_level}\n**Current XP:** {xp}\n**XP Needed for Next Level:** {xp_needed}"
            )
        else:
            msg = (
                f"{interaction.user.mention} mined and found **{result}**. No gain, no loss.\n\n"
                f"**Current Level:** {new_level}\n**Current XP:** {xp}\n**XP Needed for Next Level:** {xp_needed}"
            )
        msg += f"\n{reward_message}"

        view = MineAgainView(interaction.user)
        await interaction.followup.send(content=msg, view=view)

    @app_commands.command(name="fish", description="Catch fish for money")
    async def fish(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True)

        (
            result,
            payout,
            loss,
            total_payout,
            bonus,
            new_balance,
            new_level,
            xp,
            xp_needed,
            reward_message,
            fishing_rod,
            fishing_rod_bonus,
        ) = await run_fishing_logic(interaction.user)

        if payout > 0:
            msg = (
                f"{interaction.user.mention} fished and caught **{result}**, worth ${payout:,.2f}!\n"
                f"🎣 **Base Reward:** ${payout:,.2f}\n"
                f"⭐ **Bonus from Level ({new_level}):** ${bonus:,.2f}\n"
                f"🎣 **Fishing Rod Used:** {fishing_rod.title()} +${fishing_rod_bonus:,.2f}\n"
                f"💰 **Total Payout:** ${total_payout:,.2f}\n"
                f"💰 New Balance: ${new_balance:,.2f}\n\n"
                f"**Fishing Level:** {new_level}\n**XP:** {xp}\n**XP Needed for Next Level:** {xp_needed}"
            )
        elif loss > 0:
            msg = (
                f"{interaction.user.mention} pulled up **{result}** and lost **${loss:,.2f}**! 🥲\n"
                f"💸 New Balance: ${new_balance:,.2f}\n\n"
                f"**Fishing Level:** {new_level}\n**XP:** {xp}\n**XP Needed for Next Level:** {xp_needed}"
            )
        else:
            msg = (
                f"{interaction.user.mention} fished and found **{result}**. No gain, no loss.\n\n"
                f"**Fishing Level:** {new_level}\n**XP:** {xp}\n**XP Needed for Next Level:** {xp_needed}"
            )

        msg += f"\n{reward_message}"
        view = FishAgainView(interaction.user)
        await interaction.followup.send(content=msg, view=view)

    @app_commands.command(
        name="steal", description="Attempt to steal money from another user."
    )
    async def steal(self, interaction: Interaction, target: Member):
        await interaction.response.defer(thinking=True)

        if target == interaction.user:
            await interaction.followup.send("You can't steal from yourself, silly.")
            return

        # Get player documents
        thief_doc = collection.find_one({"_id": interaction.user.id}) or {
            "_id": interaction.user.id,
            "balance": 1000,
            "last_steal": None,
        }
        target_doc = collection.find_one({"_id": target.id}) or {
            "_id": target.id,
            "balance": 0,
        }

        thief_balance = thief_doc.get("balance", 0)
        target_balance = target_doc.get("balance", 0)
        last_steal = thief_doc.get("last_steal")
        last_stolen = target_doc.get("last_stolen")

        # Check cooldown (1800 seconds = 30 minutes)
        if last_steal:
            now = datetime.utcnow()
            elapsed = now - last_steal
            if elapsed.total_seconds() < 1800:
                remaining = 1800 - elapsed.total_seconds()
                minutes = int(remaining // 60)
                seconds = int(remaining % 60)
                await interaction.followup.send(
                    f"⏳ You're still cooling down. Try again in {minutes}m {seconds}s.",
                    ephemeral=True,
                )
                return

        if last_stolen:
            now = datetime.utcnow()
            elapsed = now - last_stolen
            if elapsed.total_seconds() < 28800:  # 8 hours = 28800 seconds
                remaining = 28800 - elapsed.total_seconds()
                hours = int(remaining // 3600)
                minutes = int((remaining % 3600) // 60)
                await interaction.followup.send(
                    f"{target.mention} is on high alert! You’ll have to wait {hours}h {minutes}m before trying to rob them again.",
                    ephemeral=True,
                )
                return

        # Check if target or thief is too broke
        if target_balance < 100:
            await interaction.followup.send(
                f"{target.mention} is too broke to steal from."
            )
            return

        if thief_balance < 100:
            await interaction.followup.send(
                "You're too broke to attempt a robbery. Get some money first using /mine"
            )
            return

        # Proceed with stealing
        wealth_factor = min(target_balance / 5000, 1.0)
        success_chance = 0.25 + 0.50 * wealth_factor
        now = datetime.utcnow()

        success_messages = [
            "💰 Success! You stole ${amount:,} ({percent:.1f}%) from {target}!",
            "🕶️ Like a shadow in the night, you nabbed ${amount:,} from {target}!",
            "👟 Quick hands! You got away with ${amount:,} from {target}!",
            "🧤 Smooth criminal! You lifted ${amount:,} from {target} without a trace.",
            "💸 Jackpot! {target} didn’t see it coming — ${amount:,} is yours!",
        ]

        fail_messages = [
            "🚓 Busted! You got caught trying to rob {target} and lost ${penalty:,} ({percent:.1f}%)!",
            "🧍‍♂️ {target} turned around just in time — you lost ${penalty:,} for your clumsiness.",
            "🪤 Trap sprung! {target} set you up and you lost ${penalty:,}!",
            "📸 Caught on camera! You dropped ${penalty:,} while fleeing from {target}.",
            "👮‍♂️ Security tackled you! You paid ${penalty:,} in fines to {target}.",
        ]

        if random.random() < success_chance:
            percent = random.uniform(0.05, 0.20)
            stolen_amount = int(target_balance * percent)

            target_balance -= stolen_amount
            thief_balance += stolen_amount

            msg = random.choice(success_messages).format(
                amount=stolen_amount, percent=percent * 100, target=target.mention
            )
            await interaction.followup.send(msg)

            update_user_steal_stats(
                interaction.user,
                success=True,
                amount=stolen_amount,
                balance=thief_balance,
                update_last_steal=True,
            )

            update_user_steal_stats(
                target,
                success=False,
                amount=stolen_amount,
                balance=target_balance,
                got_stolen=True,
                update_last_stolen=True,
            )
        else:
            percent = random.uniform(0.10, 0.30)
            penalty = int(thief_balance * percent)
            actual_penalty = min(penalty, thief_balance)

            thief_balance -= actual_penalty
            target_balance += actual_penalty

            msg = random.choice(fail_messages).format(
                penalty=actual_penalty, percent=percent * 100, target=target.mention
            )
            await interaction.followup.send(msg)

            # Calculate the amount the target gains from the failed steal
            gained_on_fail = actual_penalty

            # Update the thief's stats for the failed steal
            update_user_steal_stats(
                interaction.user,
                success=False,
                amount=actual_penalty,
                balance=thief_balance,
                update_last_steal=True,
                gained_on_fail=0,
            )

            # Update the target's stats (they gained from a failed steal)
            update_user_steal_stats(
                target,
                success=False,
                amount=0,
                balance=target_balance,
                got_stolen=True,
                gained_on_fail=gained_on_fail,
                update_last_stolen=True,
            )

    @app_commands.command(
        name="daily", description="Claim your daily reward and keep your streak going!"
    )
    async def daily(self, interaction: Interaction):
        await interaction.response.defer(thinking=True)

        user_id = interaction.user.id
        now = datetime.utcnow()

        # Retrieve user from database or initialize if new
        user = collection.find_one({"_id": user_id})
        if not user:
            user = {"_id": user_id, "balance": 0, "daily_streak": 0, "last_daily": None}
            collection.insert_one(user)

        last_daily = user.get("last_daily")
        streak = user.get("daily_streak", 0)

        if last_daily:
            last_time = datetime.fromisoformat(last_daily)
            delta = now - last_time

            if delta < timedelta(hours=24):
                hours_left = 24 - delta.total_seconds() // 3600
                await interaction.followup.send(
                    f"🕒 You already claimed your daily reward! Come back in {int(hours_left)} hour(s)."
                )
                return
            elif delta > timedelta(hours=48):
                streak = 0  # Reset streak if more than 48 hours passed
        else:
            streak = 0

        # Calculate the base reward
        base_reward = 1000

        # Calculate the bonus, doubling each streak day
        bonus = base_reward * (2**streak)  # Start at 1 for streak = 0
        bonus = min(bonus, 250000)  # Cap bonus at $10,000

        total_reward = base_reward + bonus

        # Update database with new balance, streak, and claim time
        new_balance = user.get("balance", 0) + total_reward
        collection.update_one(
            {"_id": user_id},
            {
                "$set": {
                    "balance": new_balance,
                    "daily_streak": streak + 1,  # Increment streak
                    "last_daily": now.isoformat(),
                }
            },
        )

        await interaction.followup.send(
            f"✅ You claimed your daily reward of **${total_reward:,}**!\n"
            f"🔥 Streak: {streak + 1} day(s) (+${bonus:,} bonus)"
        )

    @app_commands.command(name="heist", description="Join a heist to rob the bank!")
    @app_commands.describe(difficulty="Choose the difficulty: easy, medium, or hard.")
    @app_commands.choices(
        difficulty=[
            app_commands.Choice(name="easy", value="easy"),
            app_commands.Choice(name="medium", value="medium"),
            app_commands.Choice(name="hard", value="hard"),
        ]
    )
    async def heist(
        self, interaction: discord.Interaction, difficulty: app_commands.Choice[str]
    ):
        user_id = interaction.user.id

        # Prevent duplicate heists
        if user_id in self.active_heist_users:
            await interaction.response.send_message(
                "❌ You're already in a heist!", ephemeral=True
            )
            return

        if user_id in self.active_heist_creators:
            await interaction.response.send_message(
                "❌ You already started a heist. Wait for it to finish before starting another one!",
                ephemeral=True,
            )
            return

        self.active_heist_creators.add(user_id)
        difficulty_value = difficulty.value.lower()
        view = HeistButtonView(
            interaction, self.active_heist_users, difficulty=difficulty_value
        )

        await interaction.response.send_message(
            f"💣 A heist is being planned at **{difficulty_value.title()}** difficulty! Click below to join...",
            view=view,
        )
        followup_message = await interaction.original_response()

        # Countdown task to update the message
        async def countdown_task():
            key_moments = [60, 30, 10, 5, 4, 3, 2, 1]
            countdown_message = f"💣 A heist is being planned at **{difficulty_value.title()}** difficulty!"

            for remaining in range(60, 0, -1):
                if remaining in key_moments:
                    try:
                        content = f"{countdown_message}\n⏳ Starting in **{remaining}** seconds!"
                        await followup_message.edit(content=content)
                    except Exception as e:
                        print(f"[Countdown Edit Error] Failed at {remaining}s: {e}")
                await asyncio.sleep(1)

            # Disable all buttons
            for button in view.children:
                button.disabled = True

            # Final message after countdown ends
            try:
                await followup_message.edit(
                    content=f"{countdown_message}\n💥 The heist has started! Time's up, no more joining!",
                    view=view,
                )
            except Exception as e:
                print(f"[Final Edit Error] {e}")

            # Start the actual heist logic
            await view.on_finish()
            self.active_heist_creators.discard(interaction.user.id)

        # Start the countdown task
        asyncio.create_task(countdown_task())

        # Wait for the view to finish (either the timeout or when the button is clicked)
        await view.wait()

    # @app_commands.command(name="highlow", description="Play a game of High-Low!")
    # @app_commands.describe(amount="The amount of money you want to wager")
    # async def highlow(
    #     self, interaction: discord.Interaction, amount: app_commands.Range[int, 1, None]
    # ):
    #     user_id = interaction.user
    #     # Replace with your own balance checker
    #     prev_balance, balance = balance_of_player(user_id)

    #     if amount > balance:
    #         return await interaction.response.send_message(
    #             "You don't have enough money!", ephemeral=True
    #         )

    #     start_number = random.randint(1, 100)
    #     view = HighLowView(interaction.user, amount, start_number)

    #     await interaction.response.send_message(
    #         f"🎲 Starting number is **{start_number}** (range: 1–100).\n"
    #         f"Will the next number be higher or lower?\n"
    #         f"Wager: **${amount:,}**",
    #         view=view,
    #     )

    @app_commands.command(
        name="duel", description="Challenge another user to a duel for money!"
    )
    @app_commands.describe(
        challenged="The user you want to duel", amount="The wagered amount of money"
    )
    async def duel(
        self, interaction: discord.Interaction, challenged: discord.User, amount: int
    ):
        challenger = interaction.user

        if challenged.id == challenger.id:
            return await interaction.response.send_message(
                "You can't duel yourself!", ephemeral=True
            )

        if challenged.bot:
            return await interaction.response.send_message(
                "You can't duel a bot!", ephemeral=True
            )

        if amount <= 0:
            return await interaction.response.send_message(
                "Enter a valid amount to wager!", ephemeral=True
            )

        # Fetch user balances (replace with actual DB queries)
        challenger_data = collection.find_one({"_id": challenger.id}) or {"balance": 0}
        challenged_data = collection.find_one({"_id": challenged.id}) or {"balance": 0}

        if challenger_data["balance"] < amount:
            return await interaction.response.send_message(
                "You don't have enough money!", ephemeral=True
            )

        if challenged_data["balance"] < amount:
            return await interaction.response.send_message(
                f"{challenged.display_name} doesn't have enough money!", ephemeral=True
            )

        # Ask for duel acceptance
        view = DuelAcceptView(challenger, challenged)
        await interaction.response.send_message(
            f"{challenged.mention}, {challenger.mention} has challenged you to a duel for **${amount:,}**! Do you accept?",
            view=view,
        )
        await view.wait()

        decline_messages = [
            f"😱 {challenged.mention} declined the duel... what a coward!",
            f"🫣 {challenged.mention} backed out! Maybe next time they'll grow some courage.",
            f"🥱 {challenged.mention} declined the duel. Guess they knew they'd lose!",
            f"🏳️ {challenged.mention} has fled from battle! A true knight never runs!",
            f"🙈 {challenged.mention} said nope! Not ready for the smoke today!",
        ]

        if view.value is None:
            return await interaction.response.edit_message(
                content=random.choice(decline_messages), view=None
            )

        if view.value is False:
            return await interaction.response.edit_message(
                content=random.choice(decline_messages), view=None
            )

        # Helper function to create the health bar for players
        def get_bar(hp):
            bars = int(hp / 10)
            return "🟥" * bars + "⬛" * (10 - bars)

        def apply_special_abilities(player):
            abilities = []
            # Handle offensive effects (mutually exclusive)
            roll = random.random()
            if roll > 0.65:
                abilities.append("Fire Strike [1.5x Damage]")
            elif roll > 0.75:
                abilities.append("Critical Strike [Double Damage]")
            elif roll > 0.85:
                abilities.append("Weak Strike [1/2 Damage]")
            elif roll > 0.90:
                abilities.append("Stunned [0 Damage]")

            # Shield and Lifesteal are separate and can occur with any of the above
            if random.random() < 0.10:
                abilities.append("Shield [25% Damage Blocked]")
            if random.random() < 0.10:
                abilities.append("Lifesteal [Heal 25% of Damage Dealt]")
            if random.random() < 0.10:
                abilities.append("Deflect [Reflects 25% of damage back to attacker]")
            return abilities

        def calculate_damage(attacker, defender, abilities):
            damage = random.randint(16, 19)

            if "Critical Strike [Double Damage]" in abilities.get(attacker, []):
                damage *= 2
            if "Stunned [0 Damage]" in abilities.get(defender, []):
                damage = 0
            if "Weak Strike [1/2 Damage]" in abilities.get(attacker, []):
                damage = max(1, damage // 2)
            if "Shield [25% Damage Blocked]" in abilities.get(defender, []):
                damage = max(1, int(damage * 0.75))
            if "Fire Strike [1.5x Damage]" in abilities.get(attacker, []):
                damage = int(damage * 1.5)
            reflected = 0
            if "Deflect [Reflects 25% of damage back to attacker]" in abilities.get(
                defender, []
            ):
                reflected = int(damage * 0.25)
            return damage, reflected

        def generate_fight_message(
            challenger,
            challenged,
            dmg_to_challenger,
            dmg_to_challenged,
            special_abilities,
            heal_challenger=0,
            heal_challenged=0,
            challenger_hp=100,
            challenged_hp=100,
            reflect_to_challenger=0,
            reflect_to_challenged=0,
        ):
            # Create ability string
            challenger_abilities = ", ".join(special_abilities.get(challenger, []))
            challenged_abilities = ", ".join(special_abilities.get(challenged, []))

            lifesteal_msg = ""
            if heal_challenger > 0:
                lifesteal_msg += f"\n{challenger.display_name} heals for **{heal_challenger}** HP from Lifesteal!"
            if heal_challenged > 0:
                lifesteal_msg += f"\n{challenged.display_name} heals for **{heal_challenged}** HP from Lifesteal!"

            reflect_msg = ""
            if reflect_to_challenged > 0:
                reflect_msg += f"\n🪞 {challenged.display_name} reflects **{reflect_to_challenged}** damage back to {challenger.display_name}!"
            if reflect_to_challenger > 0:
                reflect_msg += f"\n🪞 {challenger.display_name} reflects **{reflect_to_challenger}** damage back to {challenged.display_name}!"

            ability_message = ""
            if challenger_abilities:
                ability_message += (
                    f"\n{challenger.display_name} has effects: {challenger_abilities}"
                )
            if challenged_abilities:
                ability_message += (
                    f"\n{challenged.display_name} has effects: {challenged_abilities}"
                )

            # Add current HP information
            hp_message = f"\n\n**{challenger.display_name}** HP: `{challenger_hp} HP`\n**{challenged.display_name}** HP: `{challenged_hp} HP`"

            return (
                f"**{challenger.display_name}** hits **{challenged.display_name}** for **{dmg_to_challenged}** damage!\n"
                f"**{challenged.display_name}** hits **{challenger.display_name}** for **{dmg_to_challenger}** damage!"
                + ability_message
                + lifesteal_msg
                + reflect_msg
                + hp_message  # Add current HP to the message
            )

        # Duel logic
        challenger_hp = 100
        challenged_hp = 100
        msg = await interaction.edit_original_response(
            content="⚔️ Duel begins!", view=None
        )

        special_abilities = {}
        round_number = 1
        fight_history = ""

        while challenger_hp > 0 and challenged_hp > 0:
            await asyncio.sleep(2)

            # Apply new abilities each round
            special_abilities[challenger] = apply_special_abilities(challenger)
            special_abilities[challenged] = apply_special_abilities(challenged)

            # Calculate damage
            dmg_to_challenger, reflect_to_challenged = calculate_damage(
                challenged, challenger, special_abilities
            )
            dmg_to_challenged, reflect_to_challenger = calculate_damage(
                challenger, challenged, special_abilities
            )

            challenger_hp = max(
                0, challenger_hp - dmg_to_challenger - reflect_to_challenger
            )
            challenged_hp = max(
                0, challenged_hp - dmg_to_challenged - reflect_to_challenged
            )

            # Healing from Lifesteal
            heal_challenger = 0
            heal_challenged = 0

            if (
                challenger_hp > 0
                and "Lifesteal [Heal 25% of Damage Dealt]"
                in special_abilities.get(challenger, [])
            ):
                heal_challenger = int(dmg_to_challenged * 0.25)
                challenger_hp = min(100, challenger_hp + heal_challenger)

            if (
                challenged_hp > 0
                and "Lifesteal [Heal 25% of Damage Dealt]"
                in special_abilities.get(challenged, [])
            ):
                heal_challenged = int(dmg_to_challenger * 0.25)
                challenged_hp = min(100, challenged_hp + heal_challenged)

            # Generate round message
            round_msg = f"**⚔️ Round {round_number}**\n" + generate_fight_message(
                challenger,
                challenged,
                dmg_to_challenger,
                dmg_to_challenged,
                special_abilities,
                heal_challenger,
                heal_challenged,
                challenger_hp,
                challenged_hp,
                reflect_to_challenged,
                reflect_to_challenger,
            )

            if len(fight_history) + len(round_msg) + 2 > 2000:
                await interaction.followup.send(fight_history)
                fight_history = ""

            fight_history += round_msg + "\n\n"

            embed = create_embed(
                title="🤺 Duel In Progress",
                description=f"After Round {round_number}",
                color=discord.Color.orange(),
                fields=[
                    (
                        f"{challenger.display_name}",
                        f"{get_bar(challenger_hp)}\n`{challenger_hp} HP`",
                        True,
                    ),
                    (
                        f"{challenged.display_name}",
                        f"{get_bar(challenged_hp)}\n`{challenged_hp} HP`",
                        True,
                    ),
                ],
            )
            await msg.edit(content=fight_history, embed=embed)

            if challenger_hp <= 0 and challenged_hp <= 0:
                fight_history = (
                    "**🤯 It's a double knockout! Restarting the fight...**\n\n"
                )
                challenger_hp = 100
                challenged_hp = 100
                round_number = 1
                special_abilities.clear()
                continue  # Restart the loop

            if challenger_hp <= 0 or challenged_hp <= 0:
                break

            round_number += 1

        # Wrap-up
        if fight_history:
            await msg.edit(content=fight_history, embed=embed)

        # Determine outcome
        if challenger_hp <= 0 and challenged_hp <= 0:
            winner = None
        elif challenger_hp > 0:
            winner, loser = challenger, challenged
        else:
            winner, loser = challenged, challenger

        tie_outcomes = [
            f"🤝 It's a draw! {challenger.display_name} and {challenged.display_name} collapsed at the same time. No money changes hands.",
            f"😬 Mutual destruction! {challenger.display_name} and {challenged.display_name} both hit 0 HP!",
            f"💤 After a long and exhausting fight, {challenger.display_name} and {challenged.display_name} fainted. It's a tie!",
        ]

        if winner:
            win_outcomes = [
                f"⚔️ {winner.display_name} outmaneuvered {loser.display_name} and snatched victory, winning **${amount}**!",
                f"💥 A critical hit! {winner.display_name} wins the duel and takes home **${amount}**!",
                f"😵 {loser.display_name} tripped on a banana peel. {winner.display_name} snuck away with **${amount}**!",
                f"🎯 Bullseye! {winner.display_name} lands the final blow and wins **${amount}**!",
                f"💸 {loser.display_name} lost **${amount}**, while {winner.display_name} walks away richer!",
                f"🪙 With swift moves and sharper aim, {winner.display_name} pockets **${amount}** from the fallen {loser.display_name}.",
            ]

            # Update duel stats for both players
            update_user_duel_stats(winner, "win", amount)
            update_user_duel_stats(loser, "lose", -amount)

            outcome_text = fight_history + random.choice(win_outcomes)
        else:
            update_user_duel_stats(challenger, "tie", 0)
            update_user_duel_stats(challenged, "tie", 0)
            outcome_text = fight_history + random.choice(tie_outcomes)

        await msg.edit(content=f"🎮 **Duel Complete!**\n\n{outcome_text}", embed=embed)

    @app_commands.command(name="deposit", description="Deposit money into the bank")
    async def deposit(
        self,
        interaction: discord.Interaction,
        amount: app_commands.Range[int, 1, None],
    ):
        await interaction.response.defer(thinking=True)

        # Get wallet and bank balance
        _, balance = balance_of_player(interaction.user)
        bank_balance = bank_stats(interaction.user)

        if amount > balance:
            await interaction.followup.send(
                f"{interaction.user.mention}, you dont have enough money to deposit."
            )
            return

        if amount + bank_balance > 1000000:
            await interaction.followup.send(
                f"{interaction.user.mention}, you can't have more than $1,000,000 in the bank."
            )
            return

        new_balance = update_user_bank_stats(interaction.user, amount)
        update_balance(interaction.user, balance - amount)
        await interaction.followup.send(
            f"Deposited ${amount:,} into the bank. Current Bank Balance: ${new_balance:,}"
        )

    @app_commands.command(name="withdraw", description="Withdraw money from the bank")
    async def withdraw(
        self,
        interaction: discord.Interaction,
        amount: app_commands.Range[int, 1, None],
    ):
        await interaction.response.defer(thinking=True)

        # Get wallet and bank balance
        _, balance = balance_of_player(interaction.user)
        bank_balance = bank_stats(interaction.user)

        if amount > bank_balance:
            await interaction.followup.send(
                f"{interaction.user.mention}, you dont have enough money in the bank to withdraw."
            )
            return

        new_balance = update_user_bank_stats(interaction.user, -amount)
        update_balance(interaction.user, balance + amount)

        await interaction.followup.send(
            f"Withdrew ${amount:,} from the bank. Current Bank Balance: ${new_balance:,}"
        )

    @app_commands.command(name="bank_balance", description="Check your bank balance")
    async def bank_balance(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True)

        bank_balance = bank_stats(interaction.user)
        await interaction.followup.send(
            f"{interaction.user.mention}, your current bank balance is ${bank_balance:,}."
        )

    @app_commands.command(name="roulette", description="Bet on Red, Black, or Green!")
    @app_commands.describe(amount="How much to bet")
    async def roulette(self, interaction: Interaction, amount: int):
        if amount <= 0:
            await interaction.response.send_message(
                "❌ Bet must be more than 0.", ephemeral=True
            )
            return

        user_id = interaction.user.id
        user_data = collection.find_one({"_id": user_id}) or {"balance": 1000}
        balance = user_data.get("balance", 0)

        if amount > balance:
            await interaction.response.send_message(
                "❌ You don't have enough balance!", ephemeral=True
            )
            return

        view = RouletteButtons(interaction.user, amount, balance)
        await interaction.response.send_message(
            f"🎯 Choose your color to bet **{amount:,}** coins!", view=view
        )

    @app_commands.command(
        name="rps", description="Play Rock Paper Scissors vs bot or another player"
    )
    @app_commands.describe(
        amount="Coins to bet", opponent="Challenge someone (optional)"
    )
    async def rps(
        self,
        interaction: discord.Interaction,
        amount: int,
        opponent: discord.Member = None,
    ):
        challenger = interaction.user
        is_pvp = opponent and opponent != challenger and not opponent.bot

        if amount <= 0:
            await interaction.response.send_message(
                "Bet must be greater than 0.", ephemeral=True
            )
            return

        if is_pvp:
            pc_bal, c_bal = balance_of_player(challenger)
            po_bal, o_bal = balance_of_player(opponent)
            if c_bal < amount or o_bal < amount:
                await interaction.response.send_message(
                    "One or both players don't have enough coins!", ephemeral=True
                )
                return

            await interaction.response.send_message(
                f"{challenger.mention} vs {opponent.mention} — wager: **{amount} coins**.\nChoose your move!",
                view=RPSView(challenger, opponent, amount, is_bot=False),
            )

        else:
            pc_bal, c_bal = balance_of_player(challenger)
            if c_bal < amount:
                await interaction.response.send_message(
                    "You don't have enough coins!", ephemeral=True
                )
                return

            await interaction.response.send_message(
                f"{challenger.mention} vs 🤖 Bot — wager: **{amount} coins**.\nChoose your move!",
                view=RPSView(challenger, None, amount, is_bot=True),
            )

    # Task to add 5% interest to everyone's bank account
    @tasks.loop(hours=6)  # this will run the task every 6 hours
    async def add_interest(self):
        print("[Bank Interest] Adding interest to all bank accounts...")
        users = collection.find({"bank": {"$exists": True, "$ne": 0}})
        for user in users:
            user_id = user["_id"]
            bank_balance = user["bank"]
            interest = round(bank_balance * 0.01)
            new_balance = round(bank_balance + interest)

            # Update the user's bank balance
            collection.update_one({"_id": user_id}, {"$set": {"bank": new_balance}})

    @add_interest.before_loop
    async def before_add_interest(self):
        await self.bot.wait_until_ready()
        print("[Bank Interest] Waiting before first interest application...")
        await asyncio.sleep(21600)  # 6 hours in seconds

    def cog_unload(self):
        """Stop the task when the cog is unloaded."""
        self.add_interest.cancel()

    @app_commands.command(
        name="leaderboard",
        description="Show the richest members or top miners/fishers of your server",
    )
    @app_commands.choices(
        type=[
            app_commands.Choice(name="Balance", value="balance"),
            app_commands.Choice(name="Mining", value="mining"),
            app_commands.Choice(name="Fishing", value="fishing"),
            app_commands.Choice(name="Bank", value="bank"),
        ]
    )
    @app_commands.describe(type="Choose leaderboard type")
    async def leaderboard(
        self, interaction: discord.Interaction, type: app_commands.Choice[str]
    ):
        await interaction.response.defer(thinking=True)

        members = interaction.guild.members
        member_ids = [m.id for m in members]
        id_to_name = {m.id: m.nick or m.name for m in members}

        docs = collection.find({"_id": {"$in": member_ids}})
        top_members = {}

        for doc in docs:
            uid = doc["_id"]
            if type.value == "balance":
                value = doc.get("balance", 0)
            elif type.value == "fishing":
                value = doc.get("fishing_level", 0)
                if value == 0:  # Skip members with no fishing level
                    continue
            elif type.value == "bank":
                value = doc.get("bank", 0)
                if value == 0:
                    continue
            else:
                value = doc.get("mining_level", 0)
                if value == 0:  # Skip members with no mining level
                    continue

            name = id_to_name.get(uid)
            if name:
                top_members[name] = value

        sorted_members = dict(
            sorted(top_members.items(), key=lambda item: item[1], reverse=True)
        )

        pages = []
        page_count = 1
        count = 0
        title = f"{interaction.guild.name} {'Wealth' if type.value == 'balance' else 'Top ' + type.value.capitalize()} Leaderboard"
        embed = discord.Embed(title=title)
        embed.set_footer(
            text=f"Page {page_count}", icon_url=interaction.user.display_avatar
        )

        for name, value in sorted_members.items():
            field_value = (
                f"${value:,.2f}"
                if type.value in ["balance", "bank"]
                else f"Level {value}/99"
            )
            embed.add_field(
                name=f"{count + 1}. {name}", value=field_value, inline=False
            )
            count += 1

            if count % 10 == 0:
                pages.append(embed)
                page_count += 1
                embed = discord.Embed(title=title)
                embed.set_footer(
                    text=f"Page {page_count}", icon_url=interaction.user.display_avatar
                )

        if count % 10 != 0:
            pages.append(embed)

        view = LeaderboardButton(interaction, pages)
        await interaction.followup.send(embed=pages[0], view=view)

    @app_commands.command(
        name="stealstatus",
        description="List all users with active steal protection cooldowns.",
    )
    async def stealstatus(self, interaction: Interaction):
        await interaction.response.defer(thinking=True)

        now = datetime.utcnow()
        cooldown_seconds = 28800  # 8 hours

        members = interaction.guild.members
        member_ids = [m.id for m in members]
        id_to_name = {m.id: m.nick or m.name for m in members}

        cursor = collection.find({"last_stolen": {"$ne": None}})
        users_on_cooldown = {}

        for doc in cursor:
            uid = doc["_id"]
            last_stolen = doc["last_stolen"]
            elapsed = now - last_stolen
            remaining = cooldown_seconds - elapsed.total_seconds()

            if remaining > 0:
                name = id_to_name.get(uid)
                users_on_cooldown[name] = remaining

        if not users_on_cooldown:
            await interaction.followup.send("🎉 No one is on cooldown. Steal away!")
            return

        sorted_users = dict(
            sorted(users_on_cooldown.items(), key=lambda item: item[1], reverse=False)
        )

        pages = []
        page_count = 1
        count = 0
        title = f"{interaction.guild.name} Steal Cooldown Status"
        embed = discord.Embed(title=title)
        embed.set_footer(
            text=f"Page {page_count}", icon_url=interaction.user.display_avatar
        )
        embed.description = "Users with active steal protection cooldowns:\n"
        for name, remaining in sorted_users.items():
            hours, remainder = divmod(remaining, 3600)
            minutes, seconds = divmod(remainder, 60)
            field_value = f"{int(hours)}h {int(minutes)}m {int(seconds)}s"
            embed.add_field(name=name, value=field_value, inline=False)
            count += 1

            if count % 10 == 0:
                pages.append(embed)
                page_count += 1
                embed = discord.Embed(title=title)
                embed.set_footer(
                    text=f"Page {page_count}", icon_url=interaction.user.display_avatar
                )
        if count % 10 != 0:
            pages.append(embed)
        view = LeaderboardButton(interaction, pages)
        await interaction.followup.send(embed=pages[0], view=view)


class StealCooldownView(discord.ui.View):
    def __init__(self, pages):
        super().__init__(timeout=None)
        self.pages = pages
        self.current_page = 0

    async def update_message(self, interaction):
        embed = self.pages[self.current_page]
        for i, child in enumerate(self.children):
            if isinstance(child, discord.ui.Button):
                if child.custom_id == "prev":
                    child.disabled = self.current_page == 0
                elif child.custom_id == "next":
                    child.disabled = self.current_page == len(self.pages) - 1
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="⏮️ Prev", style=discord.ButtonStyle.grey, custom_id="prev")
    async def previous(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if self.current_page > 0:
            self.current_page -= 1
            await self.update_message(interaction)

    @discord.ui.button(label="⏭️ Next", style=discord.ButtonStyle.grey, custom_id="next")
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page < len(self.pages) - 1:
            self.current_page += 1
            await self.update_message(interaction)


class LeaderboardButton(discord.ui.View):
    def __init__(self, interaction: discord.Interaction, pages: list):
        super().__init__(timeout=None)
        self.interaction = interaction
        self.pages = pages
        self.count = 0

        # Disable Previous Page by default (since we're on page 0)
        self.prev_page.disabled = True

        # Disable Next Page if there's only 1 page
        if len(pages) <= 1:
            self.next_page.disabled = True

    @discord.ui.button(label="Previous Page", style=discord.ButtonStyle.red)
    async def prev_page(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        self.count -= 1
        self.next_page.disabled = False

        if self.count <= 0:
            self.prev_page.disabled = True

        await interaction.response.edit_message(embed=self.pages[self.count], view=self)

    @discord.ui.button(label="Next Page", style=discord.ButtonStyle.red)
    async def next_page(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        self.count += 1
        self.prev_page.disabled = False

        if self.count >= len(self.pages) - 1:
            self.next_page.disabled = True

        await interaction.response.edit_message(embed=self.pages[self.count], view=self)


class HeistButtonView(discord.ui.View):
    def __init__(
        self,
        interaction: discord.Interaction,
        active_heist_users: set[int],
        difficulty: str = "medium",
    ):
        super().__init__()
        self.initiator = interaction
        self.participants = []
        self.difficulty = difficulty.lower()
        self.active_heist_users = active_heist_users

    def get_settings(self):
        if self.difficulty == "easy":
            return {
                "win_chance": 0.60,
                "min_amount": 1000,
                "max_amount": 2500,
                "backstab_chance": 0.1,
            }
        elif self.difficulty == "hard":
            return {
                "win_chance": 0.20,
                "min_amount": 10000,
                "max_amount": 20000,
                "backstab_chance": 0.025,
            }
        else:  # Default to medium
            return {
                "win_chance": 0.40,
                "min_amount": 7500,
                "max_amount": 10000,
                "backstab_chance": 0.05,
            }

    def check_balance(self, user: discord.User):
        """Checks if the user has enough balance to participate in the heist."""
        user_data = collection.find_one({"_id": user.id}) or {"balance": 0}
        balance = user_data.get("balance", 0)

        # Define the minimum required percentage based on difficulty
        difficulty_percent = {"easy": 0.025, "medium": 0.10, "hard": 0.20}

        percent = difficulty_percent.get(self.difficulty, 0.10)  # Default to medium
        min_required_balance = int(balance * percent)

        # To prevent requiring 0 balance if user has very low balance
        min_required_balance = max(
            min_required_balance, self.get_settings()["min_amount"]
        )

        return balance >= min_required_balance, balance, min_required_balance

    def get_scaled_amount(self, user: discord.User, amount: int):
        """Scales the reward/penalty based on the player's balance and difficulty."""
        user_data = collection.find_one({"_id": user.id}) or {"balance": 0}
        balance = user_data.get("balance", 0)

        # Define percentage multiplier based on difficulty
        difficulty_percent = {
            "easy": 0.025,
            "medium": 0.10,
            "hard": 0.20,
        }

        settings = self.get_settings()
        percent = difficulty_percent.get(self.difficulty, 0.10)  # Default to medium

        scaled_amount = int(balance * percent)
        scaled_amount = max(settings["min_amount"], scaled_amount)

        return scaled_amount

    @discord.ui.button(label="💰 Join Heist", style=discord.ButtonStyle.green)
    async def join_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        user = interaction.user

        # Check if the user is already in an active heist
        if user.id in self.active_heist_users:
            await interaction.response.send_message(
                "🚫 You are already in an active heist and cannot join another one.",
                ephemeral=True,
            )
            return

        if self.is_finished():
            await interaction.response.send_message(
                "The heist has already begun or expired!", ephemeral=True
            )
            return

        if user in self.participants:
            await interaction.response.send_message(
                "You're already in the heist!", ephemeral=True
            )
            return

        # Check user's balance before adding them to the heist
        can_join, balance, min_required_balance = self.check_balance(user)

        if not can_join:
            await interaction.response.send_message(
                f"🚫 You need at least **${min_required_balance:,}** to join the heist. You only have **${balance:,}**.",
                ephemeral=True,
            )
            return

        self.participants.append(user)
        self.active_heist_users.add(user.id)
        await interaction.response.send_message(f"{user.mention} has joined the heist!")

        # If there are enough participants, stop accepting more
        if len(self.participants) >= 10:
            self.stop()

    async def on_finish(self):

        # Clear all users after the heist finishes
        for user in self.participants:
            self.active_heist_users.discard(user.id)

        if not self.participants:
            await self.initiator.followup.send("⏰ The heist timed out! No one joined.")
            return

        # Check that all participants still have enough balance before proceeding with the heist
        for user in self.participants[:]:
            can_participate, balance, min_required_balance = self.check_balance(user)
            if not can_participate:
                await self.initiator.followup.send(
                    f"🚫 {user.mention} no longer has enough balance to participate and has been removed from the heist."
                )
                self.participants.remove(user)

        if not self.participants:
            await self.initiator.followup.send(
                "⏰ All participants were removed due to insufficient balance. The heist is canceled."
            )
            return

        settings = self.get_settings()
        base_win_chance = settings["win_chance"]
        bonus_per_person = 0.02  # 2% per participant
        extra_chance = min(
            bonus_per_person * len(self.participants), 0.25
        )  # Cap at 25%
        win_chance = min(base_win_chance + extra_chance, 0.95)  # Cap total at 95%

        messages = []
        min_amount = settings["min_amount"]
        max_amount = settings["max_amount"]
        is_backstab = random.random() < settings["backstab_chance"]

        if is_backstab and len(self.participants) > 1:
            backstabber = random.choice(self.participants)
            stolen_total = 0

            for user in self.participants:
                user_data = collection.find_one({"_id": user.id}) or {"balance": 0}
                balance = user_data.get("balance", 0)

                if user == backstabber:
                    # We'll calculate their stolen loot after the loop
                    continue

                stolen_amount = random.randint(min_amount, max_amount)
                stolen_total += stolen_amount
                balance = max(0, balance - stolen_amount)

                update_user_heist_stats(
                    user, loot_change=-stolen_amount, won=False, was_betrayed=True
                )
                messages.append(
                    f"🩸 {user.mention} was betrayed and lost **${stolen_amount:,}**!"
                )

            # Reward the backstabber
            backstabber_data = collection.find_one({"_id": backstabber.id}) or {
                "balance": 0
            }
            backstabber_balance = backstabber_data.get("balance", 0)
            backstabber_balance += stolen_total

            update_user_heist_stats(
                backstabber, loot_change=stolen_total, won=True, betrayed_others=True
            )
            messages.append(
                f"🗡️ {backstabber.mention} **betrayed the crew** and stole a total of **${stolen_total:,}**!"
            )

        else:
            for user in self.participants:
                result = random.choices(
                    ["win", "lose"],
                    weights=[win_chance, 1 - win_chance],
                )[0]
                amount = random.randint(min_amount, max_amount)

                # Scale the amount based on the user's balance
                scaled_amount = self.get_scaled_amount(user, amount)

                user_data = collection.find_one({"_id": user.id}) or {"balance": 0}
                balance = user_data.get("balance", 0)

                if result == "win":
                    balance += scaled_amount
                    win_messages = [
                        f"🤑 {user.mention} cracked the vault and grabbed **${scaled_amount:,}**!",
                        f"💼 {user.mention} disguised as a janitor and snuck away with **${scaled_amount:,}**!",
                        f"🏎️ {user.mention} drifted away in a getaway car with **${scaled_amount:,}**!",
                        f"🎭 {user.mention} pulled off an Oscar-worthy act and pocketed **${scaled_amount:,}**!",
                        f"🕵️ {user.mention} hacked the security system and stole **${scaled_amount:,}** unnoticed!",
                    ]
                    outcome = random.choice(win_messages)
                    update_user_heist_stats(user, loot_change=scaled_amount, won=True)
                else:
                    if self.difficulty == "easy":
                        reduced_loss = int(scaled_amount * 0.55)
                    elif self.difficulty == "medium":
                        reduced_loss = int(scaled_amount * 0.35)
                    else:
                        reduced_loss = int(scaled_amount * 0.25)
                    balance = max(0, balance - reduced_loss)
                    lose_messages = [
                        f"🚨 {user.mention} tripped the alarm and lost **${reduced_loss:,}**!",
                        f"🔒 {user.mention} got locked in the vault and dropped **${reduced_loss:,}** trying to escape!",
                        f"👮 {user.mention} ran into a guard and fumbled **${reduced_loss:,}**!",
                        f"🧨 {user.mention} triggered a booby trap and lost **${reduced_loss:,}** in the chaos!",
                        f"🐶 {user.mention} was chased by the security dog and had to drop **${reduced_loss:,}** to distract it!",
                    ]
                    outcome = random.choice(lose_messages)
                    update_user_heist_stats(user, loot_change=-reduced_loss, won=False)

                messages.append(outcome)

        await self.initiator.followup.send(
            "🎬 The heist has concluded! Here's what happened:\n\n"
            + "\n".join(messages)
        )


class DuelAcceptView(discord.ui.View):
    def __init__(self, challenger, opponent):
        super().__init__(timeout=30)
        self.value = None
        self.challenger = challenger
        self.opponent = opponent

    @discord.ui.button(label="Accept Duel", style=discord.ButtonStyle.success)
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.opponent.id:
            await interaction.response.send_message(
                "This isn't your duel!", ephemeral=True
            )
            return
        self.value = True
        self.stop()

    @discord.ui.button(label="Decline", style=discord.ButtonStyle.danger)
    async def decline(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        if interaction.user.id != self.opponent.id:
            await interaction.response.send_message(
                "This isn't your duel!", ephemeral=True
            )
            return
        self.value = False
        self.stop()


async def run_mining_logic(user: discord.User) -> tuple[str, int, int, int, int, int]:
    common_blocks = [
        "dirt",
        "sand",
        "cobblestone",
        "wood",
        "gravel",
        "andesite",
        "granite",
        "diorite",
    ]

    common_ores = [
        "coal",
        "redstone",
        "lapis lazuli",
        "copper",
        "tin",
        "flint",
        "charcoal",
        "clay",
    ]

    uncommon_ores = [
        "iron",
        "gold",
        "nether quartz",
        "platinum",
        "golden apple",
        "amethyst",
        "glowstone",
        "honeycomb",
        "quartz block",
    ]

    rare_ores = [
        "diamond",
        "emerald",
        "mythril",
        "sponge",
        "heart of the sea",
        "totem of undying",
        "prismarine shard",
        "enchanted golden apple",
    ]

    epic_ores = [
        "ancient debris",
        "netherite scrap",
        "nether star",
        "dragon egg",
        "elytra",
        "beacon",
        "enchanted book",
        "dragon head",
    ]

    prev_balance, balance = balance_of_player(user)
    stats = mine_stats(user)
    current_level = stats["mining_level"]
    current_xp = stats["mining_xp"]
    choice = random.randint(0, 101)
    mining_result = ""
    payout = 0
    loss = 0

    if choice < 5:
        mining_result = random.choice(
            [
                "a creeper ambush 💥",
                "a lava block under your feet 😱",
                "an empty cave...",
                "a trap chest full of TNT 🎁💣",
                "nothing but disappointment...",
            ]
        )
        loss = random.randint(50, 100)
        payout = 0
    elif choice < 20:
        payout = random.randint(50, 100)
        mining_result = random.choice(common_blocks)
    elif choice < 60:
        payout = random.randint(100, 150)
        mining_result = random.choice(common_ores)
    elif choice < 80:
        payout = random.randint(150, 250)
        mining_result = random.choice(uncommon_ores)
    elif choice < 95:
        payout = random.randint(250, 500)
        mining_result = random.choice(rare_ores)
    elif choice <= 100:
        payout = random.randint(500, 750)
        mining_result = random.choice(epic_ores)
    elif choice == 101:
        payout = random.randint(1500, 2000)
        mining_result = f"epic loot: {random.choice(epic_ores)}, {random.choice(rare_ores)}, {random.choice(uncommon_ores)}, {random.choice(common_ores)}, and {random.choice(common_blocks)}"

    inventory = get_user_inventory(user)  # returns dict[str, dict]
    pickaxe_types = ["wood", "stone", "iron", "gold", "diamond", "netherite"]
    PICKAXE_BONUSES = {
        "wood": 0.00,
        "stone": 0.10,
        "iron": 1,
        "gold": 2.5,
        "diamond": 5,
        "netherite": 10,
    }

    # Default to wood
    best_pickaxe = "wood"
    highest_bonus = 0.0

    # Loop through each item in the inventory
    for item in inventory:
        pickaxe_name = item["name"].lower()

        for ptype in pickaxe_types:
            # Compare pickaxe name with formatted pickaxe type
            if pickaxe_name == f"{ptype} pickaxe":
                bonus = PICKAXE_BONUSES.get(
                    ptype, 0
                )  # Get the bonus, default to 0 if not found
                if bonus > highest_bonus:
                    highest_bonus = bonus
                    best_pickaxe = ptype  # Assign the pickaxe type

    pickaxe = best_pickaxe
    pickaxe_bonus_percentage = highest_bonus

    xp_gain = random.randint(5, 10)
    bonus_percentage = 0.02
    level_bonus = int(payout * bonus_percentage * current_level)
    pickaxe_bonus = int(payout * pickaxe_bonus_percentage)
    total_payout = payout + level_bonus + pickaxe_bonus

    if payout > 0:
        balance_change = total_payout
    elif loss > 0:
        balance_change = -loss
    else:
        balance_change = 0

    (
        new_level,
        current_xp,
        xp_needed,
        reward_message,
    ) = update_user_mine_stats(user, xp_gain, balance_change)

    return (
        mining_result,
        payout,
        loss,
        total_payout,
        level_bonus,
        balance + balance_change,
        new_level,
        current_xp,
        xp_needed,
        reward_message,
        pickaxe,
        pickaxe_bonus,
    )


class MineAgainView(discord.ui.View):
    def __init__(self, user: discord.User):
        super().__init__(timeout=None)
        self.user = user

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user.id:
            await interaction.response.send_message(
                "This button is not for you!", ephemeral=True
            )
            return False
        return True

    @discord.ui.button(label="Mine Again", style=discord.ButtonStyle.green)
    async def mine_again(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        (
            result,
            payout,
            loss,
            total_payout,
            bonus,
            new_balance,
            new_level,
            xp,
            xp_needed,
            reward_message,
            pickaxe,
            pickaxe_bonus,
        ) = await run_mining_logic(self.user)

        if payout > 0:
            msg = (
                f"{interaction.user.mention} mined and found **{result}**, worth ${payout:,.2f}!\n"
                f"💰 **Base Reward:** ${payout:,.2f}\n"
                f"🎉 **Bonus from Level ({new_level}):** +${bonus:,.2f}\n"
                f"⛏️ **Pickaxe Used:** {pickaxe.title()} +${pickaxe_bonus:,.2f}\n"
                f"💸 **Total Payout:** ${total_payout:,.2f}\n"
                f"💰 New Balance: ${new_balance:,.2f}\n\n"
                f"**Current Level:** {new_level}\n**Current XP:** {xp}\n**XP Needed for Next Level:** {xp_needed}"
            )
        elif loss > 0:
            msg = (
                f"{interaction.user.mention} encountered **{result}** and lost **${loss:,.2f}**! 😵\n"
                f"💸 New Balance: ${new_balance:,.2f}\n\n"
                f"**Current Level:** {new_level}\n**Current XP:** {xp}\n**XP Needed for Next Level:** {xp_needed}"
            )
        else:
            msg = (
                f"{interaction.user.mention} mined and found **{result}**. No gain, no loss.\n\n"
                f"**Current Level:** {new_level}\n**Current XP:** {xp}\n**XP Needed for Next Level:** {xp_needed}"
            )
        msg += f"\n{reward_message}"
        await interaction.response.edit_message(content=msg, view=self)


async def run_fishing_logic(
    user: discord.User,
) -> tuple[str, int, int, int, int, int, int, int]:
    common_fish = [
        "cod",
        "salmon",
        "tropical fish",
        "pufferfish",
        "anchovy",
        "sardine",
        "shrimp",
        "tilapia",
    ]

    uncommon_fish = [
        "clownfish",
        "bass",
        "catfish",
        "eel",
        "octopus",
        "squid",
        "crab",
        "lobster",
    ]

    rare_fish = [
        "swordfish",
        "tuna",
        "blue marlin",
        "stingray",
        "manta ray",
        "shark tooth",
        "electric eel",
    ]

    epic_fish = [
        "giant squid",
        "megalodon tooth",
        "golden koi",
        "mythical sea serpent scale",
        "cursed pearl",
        "leviathan fin",
    ]

    trash = [
        "old boot",
        "tin can",
        "seaweed",
        "plastic bag",
        "broken rod",
        "muddy sock",
    ]

    prev_balance, balance = balance_of_player(user)
    stats = fish_stats(user)
    current_level = stats["fishing_level"]
    current_xp = stats["fishing_xp"]

    choice = random.randint(0, 101)
    fishing_result = ""
    payout = 0
    loss = 0

    if choice < 5:
        fishing_result = random.choice(trash)
        loss = random.randint(25, 75)
    elif choice < 25:
        payout = random.randint(25, 100)
        fishing_result = random.choice(common_fish)
    elif choice < 60:
        payout = random.randint(100, 200)
        fishing_result = random.choice(uncommon_fish)
    elif choice < 90:
        payout = random.randint(200, 400)
        fishing_result = random.choice(rare_fish)
    elif choice <= 100:
        payout = random.randint(400, 750)
        fishing_result = random.choice(epic_fish)
    elif choice == 101:
        payout = random.randint(1500, 2000)
        fishing_result = (
            f"legendary haul: {random.choice(epic_fish)}, {random.choice(rare_fish)}, "
            f"{random.choice(uncommon_fish)}, and {random.choice(common_fish)}"
        )

    inventory = get_user_inventory(user)  # returns dict[str, dict]
    fishing_rod_types = ["wood", "stone", "iron", "gold", "diamond", "netherite"]
    FISHING_ROD_BONUSES = {
        "wood": 0.00,
        "stone": 0.10,
        "iron": 1,
        "gold": 2.5,
        "diamond": 5,
        "netherite": 10,
    }

    # Default to wood
    best_rod = "wood"
    highest_bonus = 0.0

    # Loop through each item in the inventory
    for item in inventory:
        item_name = item["name"].lower()  # Assuming 'name' key exists in item

        for rod_type in fishing_rod_types:
            # Compare item name with formatted rod type
            if item_name == f"{rod_type} fishing rod":
                bonus = FISHING_ROD_BONUSES.get(
                    rod_type, 0
                )  # Get the bonus, default to 0 if not found
                if bonus > highest_bonus:
                    highest_bonus = bonus
                    best_rod = rod_type  # Assign the rod type

    fishing_rod = best_rod
    fishing_rod_bonus_percentage = highest_bonus

    xp_gain = random.randint(5, 10)
    bonus_percentage = 0.02
    level_bonus = int(payout * bonus_percentage * current_level)
    fishing_rod_bonus = int(payout * fishing_rod_bonus_percentage)
    total_payout = payout + level_bonus + fishing_rod_bonus

    balance_change = total_payout if payout > 0 else -loss if loss > 0 else 0

    new_level, current_xp, xp_needed, reward_message = update_user_fish_stats(
        user, xp_gain, balance_change
    )

    return (
        fishing_result,
        payout,
        loss,
        total_payout,
        level_bonus,
        balance + balance_change,
        new_level,
        current_xp,
        xp_needed,
        reward_message,
        fishing_rod,
        fishing_rod_bonus,
    )


class FishAgainView(discord.ui.View):
    def __init__(self, user: discord.User):
        super().__init__(timeout=None)
        self.user = user

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user.id:
            await interaction.response.send_message(
                "This button is not for you!", ephemeral=True
            )
            return False
        return True

    @discord.ui.button(label="Fish Again", style=discord.ButtonStyle.blurple)
    async def fish_again(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        (
            result,
            payout,
            loss,
            total_payout,
            bonus,
            new_balance,
            new_level,
            xp,
            xp_needed,
            reward_message,
            fishing_rod,
            fishing_rod_bonus,
        ) = await run_fishing_logic(self.user)

        if payout > 0:
            msg = (
                f"{interaction.user.mention} caught **{result}**, worth ${payout:,.2f}!\n"
                f"🎣 **Base Reward:** ${payout:,.2f}\n"
                f"⭐ **Bonus from Level ({new_level}):** ${bonus:,.2f}\n"
                f"🎣 **Fishing Rod Used:** {fishing_rod.title()} +${fishing_rod_bonus:,.2f}\n"
                f"💰 **Total Payout:** ${total_payout:,.2f}\n"
                f"💰 New Balance: ${new_balance:,.2f}\n\n"
                f"**Fishing Level:** {new_level}\n**XP:** {xp}\n**XP Needed for Next Level:** {xp_needed}"
            )
        elif loss > 0:
            msg = (
                f"{interaction.user.mention} pulled up **{result}** and lost **${loss:,.2f}**! 🥲\n"
                f"💸 New Balance: ${new_balance:,.2f}\n\n"
                f"**Fishing Level:** {new_level}\n**XP:** {xp}\n**XP Needed for Next Level:** {xp_needed}"
            )
        else:
            msg = (
                f"{interaction.user.mention} fished and found **{result}**. No gain, no loss.\n\n"
                f"**Fishing Level:** {new_level}\n**XP:** {xp}\n**XP Needed for Next Level:** {xp_needed}"
            )
        msg += f"\n{reward_message}"
        await interaction.response.edit_message(content=msg, view=self)


class HighLowView(View):
    def __init__(self, user: discord.User, wager: int, start_number: int):
        super().__init__(timeout=60)
        self.user = user
        self.wager = wager
        self.current_number = start_number
        self.multiplier = 1.0
        self.round = 1
        self.is_active = True
        self.cashout_enabled = False  # Disable Cash Out on the first round
        self.win = ""

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user.id:
            await interaction.response.send_message(
                "This isn't your game!", ephemeral=True
            )
            return False
        return True

    def get_win_chance(self, guess: str) -> float:
        if guess == "higher":
            return (100 - self.current_number) / 99
        else:
            return (self.current_number - 1) / 99

    def get_multiplier(self, win_chance: float) -> float:
        house_edge = 0.95  # 5% house edge
        return round((1 / win_chance) * house_edge, 2)

    def generate_next_number(self) -> int:
        return random.randint(1, 100)

    async def handle_guess(self, interaction: discord.Interaction, guess: str):
        if not self.is_active:
            return

        next_number = self.generate_next_number()
        correct = (guess == "higher" and next_number > self.current_number) or (
            guess == "lower" and next_number < self.current_number
        )

        win_chance = self.get_win_chance(guess)
        current_mult = self.get_multiplier(win_chance)
        self.cashout_enabled = True  # Enable Cash Out after the first guess
        self.children[2].disabled = False  # The 'Cash Out' button is at index 2

        if correct:
            self.multiplier *= current_mult
            self.current_number = next_number
            self.round += 1

            await interaction.response.edit_message(
                content=(  # Update message with new information
                    f"✅ You guessed **{guess}** and the next number was **{next_number}**.\n"
                    f"🎯 Current multiplier: **x{self.multiplier:.2f}**\n"
                    f"🎲 New number is **{self.current_number}** (1–100)\n"
                    f"Do you want to continue or cash out?"
                ),
                view=self,  # The updated view with enabled cashout button
            )
            self.win = "win"
        else:
            self.is_active = False
            self.stop()
            await interaction.response.edit_message(
                content=(
                    f"❌ The next number was **{next_number}**. You guessed **{guess}** and lost.\n"
                    f"You lost your **${self.wager:,}** bet."
                ),
                view=None,  # Disable all buttons after losing
            )
            self.win = "lose"

    @discord.ui.button(label="Higher", style=discord.ButtonStyle.success)
    async def higher(self, interaction: discord.Interaction, button: Button):
        await self.handle_guess(interaction, "higher")

    @discord.ui.button(label="Lower", style=discord.ButtonStyle.danger)
    async def lower(self, interaction: discord.Interaction, button: Button):
        await self.handle_guess(interaction, "lower")

    @discord.ui.button(
        label="Cash Out 💰", style=discord.ButtonStyle.primary, disabled=True
    )
    async def cashout(self, interaction: discord.Interaction, button: Button):
        if not self.cashout_enabled:
            return

        # Disable Cash Out button after use
        self.is_active = False
        self.stop()

        # Retrieve the player's previous balance and calculate the winnings
        prev_balance, balance = balance_of_player(self.user)
        winnings = int(self.wager * self.multiplier)

        # Update the player's balance with the winnings
        update_balance(self.user, balance + winnings)
        update_user_highlow_stats(self.user, self.win, winnings, self.multiplier)

        await interaction.response.edit_message(
            content=(
                f"💰 You cashed out with a multiplier of **x{self.multiplier:.2f}**!\n"
                f"You won **${winnings:,}** from your original bet of **${self.wager:,}**."
            ),
            view=None,
        )


class RouletteButtons(discord.ui.View):
    def __init__(self, user: discord.User, amount: int, balance: int):
        super().__init__(timeout=None)
        self.user = user
        self.amount = amount
        self.balance = balance

    async def handle_spin(self, interaction: Interaction, chosen_color: str):
        if interaction.user.id != self.user.id:
            await interaction.response.send_message(
                "❌ This isn't your game!", ephemeral=True
            )
            return

        # Initial response with "Spinning..." message
        embed = discord.Embed(
            title="🎰 Spinning...",
            description="The wheel is spinning!",
            color=discord.Color.gold(),
        )
        embed.set_footer(text="Hold tight!")
        await interaction.response.edit_message(embed=embed)
        prev_balance = self.balance
        # Simulate the spinning wheel effect with a delay
        colors = ["red", "black", "green"]
        # for _ in range(5):  # Spin animation loop
        #     print("test")
        #     spin_result = random.choice(colors)
        #     color_map = {
        #         "red": discord.Color.red(),
        #         "black": discord.Color.dark_gray(),
        #         "green": discord.Color.green(),
        #     }
        #     embed.description = f"🎰 Spinning... {spin_result.upper()}!"
        #     embed.color = color_map[spin_result]
        #     await interaction.edit_original_response(embed=embed)
        #     # await interaction.response.edit_message(embed=embed)
        #     await asyncio.sleep(1)  # Change the spin every 100ms

        # Final result
        roll = random.choices(
            population=["red", "black", "green"], weights=[18, 18, 2], k=1
        )[0]

        win = roll == chosen_color
        payout = 0

        if win:
            if chosen_color in ["red", "black"]:
                payout = self.amount * 2
            else:
                payout = self.amount * 14
            self.balance += payout - self.amount
            result = f"🎉 It landed on **{roll.upper()}**! You won **{payout-self.amount:,}** coins!"
            update_user_roulette_stats(self.user, "win", payout - self.amount)
        else:
            self.balance -= self.amount
            result = f"💀 It landed on **{roll.upper()}**. You lost **{self.amount:,}** coins."
            update_user_roulette_stats(self.user, "lose", self.amount)

        # Update database
        collection.update_one(
            {"_id": self.user.id}, {"$set": {"balance": self.balance}}, upsert=True
        )

        color_map = {
            "red": discord.Color.red(),
            "black": discord.Color.dark_gray(),
            "green": discord.Color.green(),
        }
        embed = discord.Embed(
            title="🎡 Roulette Result", description=result, color=color_map[roll]
        )

        embed.add_field(name="Prev Balance", value=f"${prev_balance:,}", inline=True)
        embed.add_field(name="New Balance", value=f"${self.balance:,}", inline=True)
        result_value = (
            f"+${abs(self.balance - prev_balance):,.2f}"
            if self.balance >= prev_balance
            else f"-${abs(self.balance - prev_balance):,.2f}"
        )
        roulette_won, roulette_lost, roulette_played, total_winnings, total_losses = (
            roulette_stats(self.user).values()
        )

        embed.add_field(name="Result", value=f"{result_value}", inline=True)
        embed.set_footer(
            text=f"{roulette_won} roulette won, {roulette_lost} roulette lost, {roulette_played} roulette played"
        )

        for child in self.children:
            child.disabled = True

        # Add "Play Again" button
        play_again_button = PlayAgainButton(self.user, self.amount, self.balance)
        self.add_item(play_again_button)

        # Final edit of the message with result and view
        await interaction.edit_original_response(embed=embed, view=self)
        # await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="🟥 Red", style=discord.ButtonStyle.danger)
    async def red_button(self, interaction: Interaction, button: discord.ui.Button):
        await self.handle_spin(interaction, "red")

    @discord.ui.button(label="⬛ Black", style=discord.ButtonStyle.secondary)
    async def black_button(self, interaction: Interaction, button: discord.ui.Button):
        await self.handle_spin(interaction, "black")

    @discord.ui.button(label="🟩 Green", style=discord.ButtonStyle.success)
    async def green_button(self, interaction: Interaction, button: discord.ui.Button):
        await self.handle_spin(interaction, "green")


class PlayAgainButton(discord.ui.Button):
    def __init__(self, user: discord.User, amount: int, balance: int):
        super().__init__(label="Play Again", style=discord.ButtonStyle.green)
        self.user = user
        self.amount = amount
        self.balance = balance

    async def callback(self, interaction: Interaction):
        if interaction.user.id != self.user.id:
            await interaction.response.send_message(
                "❌ This isn't your game!", ephemeral=True
            )
            return

        # Check if user has enough balance to play again
        _, current_balance = balance_of_player(interaction.user)
        if current_balance < self.amount:
            await interaction.response.send_message(
                f"❌ You don't have enough balance to play again.\nRequired: {self.amount:,}, Your Balance: {current_balance:,}",
                ephemeral=True,
            )
            return

        # Restart the game
        view = RouletteButtons(self.user, self.amount, current_balance)
        await interaction.response.edit_message(
            content=f"🎯 Choose your color to bet **{self.amount:,}** coins!", view=view
        )
        self.view.stop()


class RPSView(discord.ui.View):
    def __init__(self, challenger, opponent, amount, is_bot):
        super().__init__(timeout=None)
        self.challenger = challenger
        self.opponent = opponent
        self.amount = amount
        self.is_bot = is_bot
        self.choices = {}

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if self.is_bot:
            return interaction.user == self.challenger
        return interaction.user in [self.challenger, self.opponent]

    async def handle_choice(self, interaction, player, choice):
        self.choices[player.id] = choice
        await interaction.response.defer()

        # Send confirmation to the player who made the choice
        await interaction.followup.send(
            content=f"{player.mention} picked **{choice}**!", ephemeral=True
        )

        # If bot is playing against the challenger
        if self.is_bot:
            bot_choice = random.choice(["rock", "paper", "scissors"])
            result = determine_outcome(choice, bot_choice)
            desc = f"You chose **{choice}**, I chose **{bot_choice}**.\n"

            prev, current = balance_of_player(player)
            if result == "win":
                update_balance(player, current + self.amount)
                desc += f"You **won** 💸 {self.amount} coins!"
            elif result == "lose":
                update_balance(player, current - self.amount)
                desc += f"You **lost** 🥲 {self.amount} coins!"
            else:
                desc += "It's a **tie**! Bet refunded."

            await interaction.followup.send(desc)

        # If it's a PvP match, check if both players have made their choices
        elif len(self.choices) == 2:
            c1 = self.choices[self.challenger.id]
            c2 = self.choices[self.opponent.id]
            result = determine_pvp_outcome(c1, c2)

            embed = discord.Embed(title="🪨 Rock Paper Scissors: PvP Result")
            embed.add_field(name=self.challenger.display_name, value=c1, inline=True)
            embed.add_field(name=self.opponent.display_name, value=c2, inline=True)

            pc_bal, c_bal = balance_of_player(self.challenger)
            po_bal, o_bal = balance_of_player(self.opponent)

            if result == "tie":
                embed.description = "It's a **tie**! No coins exchanged."
            elif result == "p1":
                update_balance(self.challenger, c_bal + self.amount)
                update_balance(self.opponent, o_bal - self.amount)
                embed.description = (
                    f"{self.challenger.mention} wins 💰 {self.amount} coins!"
                )
            else:
                update_balance(self.challenger, c_bal - self.amount)
                update_balance(self.opponent, o_bal + self.amount)
                embed.description = (
                    f"{self.opponent.mention} wins 💰 {self.amount} coins!"
                )

            # Disable all buttons after both players have chosen
            for item in self.children:
                item.disabled = True

            # Edit the original message to update the view with disabled buttons
            try:
                await interaction.message.edit(view=self)
            except Exception:
                pass  # In case the message was deleted or otherwise unavailable

            await interaction.followup.send(embed=embed)

    @discord.ui.button(label="🪨 Rock", style=discord.ButtonStyle.primary)
    async def rock(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_choice(interaction, interaction.user, "rock")

    @discord.ui.button(label="📄 Paper", style=discord.ButtonStyle.success)
    async def paper(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_choice(interaction, interaction.user, "paper")

    @discord.ui.button(label="✂️ Scissors", style=discord.ButtonStyle.danger)
    async def scissors(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await self.handle_choice(interaction, interaction.user, "scissors")


def determine_outcome(player, bot) -> str:
    wins = {"rock": "scissors", "paper": "rock", "scissors": "paper"}
    if player == bot:
        return "tie"
    return "win" if wins[player] == bot else "lose"


def determine_pvp_outcome(c1, c2) -> str:
    if c1 == c2:
        return "tie"
    wins = {"rock": "scissors", "paper": "rock", "scissors": "paper"}
    return "p1" if wins[c1] == c2 else "p2"


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Economy(bot))
    print("Economy is Loaded")
