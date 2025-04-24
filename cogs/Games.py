import os
import random
from datetime import datetime, timedelta
from typing import Literal, Optional

import discord
import requests
from bs4 import BeautifulSoup
from discord import app_commands
from discord.app_commands import Choice
from discord.ext import commands
from discord.ui import Button, View
from dotenv import load_dotenv
from pymongo import MongoClient

from utils.stats import (
    balance_of_player,
    blackjack_stats,
    gamble_stats,
    slots_stats,
    update_user_blackjack_stats,
    update_user_gamble_stats,
    update_user_slots_stats,
    wordle_stats,
)

load_dotenv()
GAMES = os.getenv("GAMES")
MONGO_URL = os.getenv("ATLAS_URI")
cluster = MongoClient(MONGO_URL)
db = cluster["Users"]
collection = db["UserData"]


class Games(commands.Cog):
    """Games functions"""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.games = {}  # Dictionary to track the games for each user

    def cleanup_old_games(self):
        now = datetime.utcnow()
        expired_users = [
            user_id
            for user_id, game in self.games.items()
            if now - game.created_at > timedelta(minutes=10)
        ]
        for user_id in expired_users:
            del self.games[user_id]
            print(f"Removed stale Wordle game for user {user_id}")

    @app_commands.command(name="wordle", description="Start a Wordle-like game")
    async def wordle(self, interaction: discord.Interaction):
        self.cleanup_old_games()
        user_id = interaction.user.id

        # Check if the user is already in a game
        if user_id in self.games:
            original_message_link = (
                f"https://discord.com/channels/{self.games[user_id].message.guild.id}/"
                f"{self.games[user_id].message.channel.id}/{self.games[user_id].message.id}"
            )
            await interaction.response.send_message(
                f"You are already in an active Wordle game! [View your current game]({original_message_link})"
            )
            return

        # Start a new game for the user
        self.games[user_id] = WordleGame()
        button = Button(label="Make a Guess", style=discord.ButtonStyle.primary)
        view = View(timeout=None)
        view.add_item(button)

        # Send the welcome message with the button
        await interaction.response.send_message(
            "Welcome to Wordle! The game has started. Try to guess the 5-letter word.\n"
            "You have 6 attempts. After each guess, I will give you feedback:\n"
            "**Bold Letter** means the letter is correct and in the correct position.\n"
            "__Underlined__ means the letter is correct but in the wrong position.\n"
            "~~Letters~~ means the letter is incorrect.\n",
            view=view,
        )

        message = await interaction.original_response()
        self.games[user_id].message = message

        # Assign the button's callback function to open the modal
        async def on_button_click(interaction: discord.Interaction):
            if interaction.user.id != user_id:
                await interaction.response.send_message(
                    "Not your game. Type `/wordle` to start a new game.", ephemeral=True
                )
            if user_id not in self.games:
                await interaction.response.send_message(
                    "You don't have an active game. Type `/wordle` to start a new game."
                )
                return

            # Create and send the modal
            modal = GuessModal(
                user_id=user_id, game=self.games[user_id], games=self.games
            )
            await interaction.response.send_modal(modal)

        button.callback = on_button_click

    @app_commands.command(
        name="games", description="Provide the google sheet links to games"
    )
    async def games(self, interaction: discord.Interaction):
        """Provide the google sheet links to games"""
        view = GamesList()
        await interaction.response.send_message(
            "Games Channel: <#629459633031086080>", view=view
        )

    @app_commands.command(name="add_game", description="Add a game to games channel")
    @app_commands.describe(
        add="Adding or Updating a game",
        download_link="The google drive download link",
        steam_link="The steam link to the game",
    )
    @app_commands.choices(
        add=[
            Choice(name="Added", value="Added "),
            Choice(name="Updated", value="Updated"),
        ]
    )
    @app_commands.checks.has_permissions(moderate_members=True)
    async def add_game(
        self,
        interaction: discord.Interaction,
        add: str,
        download_link: str,
        steam_link: str,
        build: Optional[str] = None,
        notes: Optional[str] = "No Notes",
    ):
        """Easy embed for games download"""
        try:
            # bs4 to parse through steam link for data
            url = steam_link
            response = requests.get(url, timeout=100)
            soup = BeautifulSoup(response.text, features="html.parser")
            genres = ""
            for index, genre in enumerate(soup.find_all(class_="app_tag")):
                if index >= 5:
                    break
                if genre.contents[0].strip() == "+":
                    continue
                genres += f"`{genre.contents[0].strip()}` "

            title = soup.select_one('div[class="apphub_AppName"]').contents[0]
            description = soup.find("meta", property="og:description")["content"]
            image = soup.find("meta", property="og:image")["content"]
            if soup.select_one('div[class="discount_original_price"]'):
                original_price = soup.select_one(
                    'div[class="discount_original_price"]'
                ).contents[0]
                discounted_price = soup.select_one(
                    'div[class="discount_final_price"]'
                ).contents[0]
                price = f"~~{original_price}~~\n{discounted_price}"
            else:
                if soup.select_one('div[class="game_purchase_price price"]'):
                    price = soup.select_one(
                        'div[class="game_purchase_price price"]'
                    ).contents[0]
                else:
                    price = "N/A"
            reviews = soup.find("meta", itemprop="reviewCount")["content"]
            reviews_description = soup.find("span", itemprop="description").contents[0]
            app_id = soup.find("meta", property="og:url")["content"].split("/")[4]
            build_link = f"https://steamdb.info/app/{app_id}/patchnotes/"
            embed = discord.Embed(
                title=f"{add} - {title}",
                color=0x336EFF,
                url=steam_link,
                description=f"[Build {build}]({build_link})" if build else "",
            )
            embed.add_field(
                name="Direct Download Link",
                value=f"[Click Here]({download_link})",
                inline=False,
            )
            embed.add_field(
                name="Full Games List", value=f"[Click Here]({GAMES})", inline=False
            )
            embed.add_field(
                name="Steam Link", value=f"[Click Here]({steam_link})", inline=False
            )
            request_link = "https://forms.gle/d1K2NBLfJBqoSsv59"
            embed.add_field(
                name="Have a request?",
                value=f"[Click Here]({request_link})",
                inline=False,
            )
            embed.add_field(
                name="Description", value=f"```{description}```", inline=False
            )
            embed.add_field(name="Notes", value=f"```{notes}```", inline=False)
            embed.add_field(name="Price", value=f"{price}", inline=True)
            embed.add_field(
                name="Reviews", value=f"{reviews_description} ({reviews})", inline=True
            )
            embed.add_field(name="App Id", value=f"{app_id}", inline=True)
            embed.add_field(name="Genres", value=f"{genres}", inline=False)
            embed.set_image(url=image)
            embed.timestamp = datetime.now()
            embed.set_footer(
                text=f"{interaction.user}", icon_url=interaction.user.avatar
            )
        except Exception as e:
            print(e)
            return
        await interaction.response.send_message(embed=embed)

    @app_commands.command(
        name="gamble", description="Chance to win or lose money - Default $100"
    )
    @app_commands.describe(
        amount="Amount of money you want to gamble - Default $100",
        action="Choice for gambling all your money at once",
    )
    async def gamble(
        self,
        interaction: discord.Interaction,
        amount: Optional[app_commands.Range[int, 1, None]] = 100,
        action: Optional[Literal["All in"]] = None,
    ):
        await interaction.response.defer(thinking=True)
        view = GamblingButton(interaction, amount, action)
        embed = gamble_helper(interaction, amount, action)
        await interaction.followup.send(embed=embed, view=view)

    @discord.app_commands.command(
        name="blackjack", description="Starts a game of blackjack with the dealer"
    )
    @discord.app_commands.describe(
        amount="Amount of money you want to gamble - Default $100"
    )
    async def blackjack(
        self,
        interaction: discord.Interaction,
        amount: Optional[app_commands.Range[int, 1, None]] = 100,
    ):
        # 1) Defer & fetch balances
        await interaction.response.defer(thinking=True)
        prev_balance, balance = balance_of_player(interaction.user)

        # 2) Insufficient funds?
        if amount > balance:
            embed = discord.Embed(title="Not enough balance")
            embed.add_field(name="Needed Balance", value=f"${amount:,.2f}", inline=True)
            embed.add_field(name="Balance", value=f"${balance:,.2f}", inline=True)
            await interaction.followup.send(embed=embed)
            return

        # 3) Deduct the bet immediately
        balance -= amount
        collection.update_one(
            {"_id": interaction.user.id}, {"$set": {"balance": balance}}
        )

        # 4) Build initial deal embed
        embed = discord.Embed(title="Blackjack", description=f"${amount:,.2f} bet")

        # Dealer: one face‑up, one covered
        card1 = random_card()
        dealer_cards = [[card1[1], "⬛"], card1[0]]
        dealer_total = dealer_cards[1]
        if card1[1] == "🇦":
            dealer_label = f"{dealer_total}/{dealer_total+10}"
        else:
            dealer_label = str(dealer_total)
        embed.add_field(
            name=f"Dealer's Hand — {dealer_label}",
            value=f"{dealer_cards[0][0]} {dealer_cards[0][1]}",
            inline=False,
        )

        # Player: two cards
        card1, card2 = random_card(), random_card()
        player_cards = [[card1[1], card2[1]], card1[0] + card2[0]]
        p_total = player_cards[1]
        if "🇦" in player_cards[0]:
            player_label = f"{p_total}/{p_total+10}"
        else:
            player_label = str(p_total)
        embed.add_field(
            name=f"Player's Hand — {player_label}",
            value=f"{player_cards[0][0]} {player_cards[0][1]}",
            inline=False,
        )

        # 5) Natural Blackjack?
        is_natural = ("🇦" in player_cards[0]) and any(
            card in ["🔟", "🇯", "🇶", "🇰"] for card in player_cards[0]
        )
        if is_natural:
            # payout = 1.5 × stake
            payout = int(amount * 1.5)

            # record win (played + won + total_winnings)
            update_user_blackjack_stats(interaction.user, "win", payout)

            # credit stake + winnings back to balance
            balance += amount + payout
            collection.update_one(
                {"_id": interaction.user.id}, {"$set": {"balance": balance}}
            )

            # finish embed
            embed.add_field(
                name="Result", value="Natural Blackjack – You win!", inline=False
            )
            embed.add_field(
                name="Prev Balance", value=f"${prev_balance:,.2f}", inline=True
            )
            embed.add_field(name="New Balance", value=f"${balance:,.2f}", inline=True)
            embed.add_field(
                name="Change", value=f"+${(balance - prev_balance):,.2f}", inline=True
            )
            embed.set_footer(
                text=f"Blackjacks won/tied/lost/played: updated in stats helper"
            )

            await interaction.followup.send(embed=embed)
            return

        # 6) Otherwise, hand off to your view for Hit/Stay/Double‑Down
        view = BlackjackButton(dealer_cards, player_cards, embed, interaction, amount)
        await interaction.followup.send(embed=embed, view=view)

    @app_commands.command(
        name="fight", description="Fight against another player or a bot"
    )
    async def fight(
        self, interaction: discord.Interaction, member: Optional[discord.Member] = None
    ):
        if not member:
            member = self.bot.user
        view = FightButton(interaction, member)
        content = f"It is {interaction.user.mention} turn"
        await interaction.response.send_message(
            embed=fight_helper(interaction, member), content=content, view=view
        )

    @app_commands.command(name="slots", description="Spins a slot machine")
    async def slot(
        self,
        interaction: discord.Interaction,
        amount: Optional[app_commands.Range[int, 1, None]] = 100,
    ):
        view = SlotsButton(interaction, amount)
        content, embed = slots_helper(interaction, amount)
        await interaction.response.send_message(content=content, embed=embed, view=view)


class GamesList(discord.ui.View):
    def __init__(self):
        super().__init__()
        # we need to quote the query string to make a valid url. Discord will raise an error if it isn't valid.
        url = GAMES

        # Link buttons cannot be made with the decorator
        # Therefore we have to manually create one.
        # We add the quoted url to the button, and add the button to the view.
        self.add_item(discord.ui.Button(label="List Of Games", url=url))


class GamblingButton(discord.ui.View):
    def __init__(self, interaction: discord.Interaction, amount: Optional[int], action):
        super().__init__(timeout=None)
        self.amount = amount
        self.interaction = interaction
        self.action = action

    # this function must return a boolean, or to the very least a truthy/falsey value.
    async def interaction_check(self, interaction: discord.Interaction) -> bool:

        if self.interaction.user.id != interaction.user.id:
            await interaction.response.send_message(
                "Please start your own game with /gamble", ephemeral=True
            )
            return False
        return True

    @discord.ui.button(label="Play Again", style=discord.ButtonStyle.red)
    async def play_again(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        embed = gamble_helper(interaction, self.amount, self.action)
        await interaction.response.edit_message(embed=embed, view=self)


class BlackjackButton(discord.ui.View):
    def __init__(
        self,
        dealer_cards: list,
        player_cards: list,
        embed: discord.Embed,
        interaction: discord.Interaction,
        amount: app_commands.Range[int, 1, None] = 100,
    ):
        super().__init__(timeout=None)
        self.dealer_cards = dealer_cards
        self.player_cards = player_cards
        self.embed = embed
        self.interaction = interaction
        self.amount = amount
        prev_balance, balance = balance_of_player(interaction.user)
        balance += self.amount
        if self.amount * 2 > balance:
            self.double_down.disabled = True

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if self.interaction.user.id != interaction.user.id:
            await interaction.response.send_message(
                "Please start your own game with /blackjack", ephemeral=True
            )
            return False
        return True

    @discord.ui.button(label="Hit", style=discord.ButtonStyle.green)
    async def hit(self, interaction: discord.Interaction, button: discord.ui.Button):
        # 1) Load balances, then “refund” the original bet in‐memory
        prev_balance, balance = balance_of_player(interaction.user)
        # prev_balance += self.amount
        # balance += self.amount

        # 2) Deal one more card
        new_card = random_card()
        self.player_cards[0].append(new_card[1])
        self.player_cards[1] += new_card[0]

        # 3) Update the “Player’s Hand” field in the embed
        total = self.player_cards[1]
        if "🇦" in self.player_cards[0] and total <= 11:
            disp = f"{total}/{total + 10}"
        else:
            disp = str(total)

        self.embed.set_field_at(
            index=1,
            name=f"Player's Hand — {disp}",
            value=f"{self.embed.fields[1].value} {self.player_cards[0][-1]}",
            inline=False,
        )

        # 4) Check for bust
        if total > 21:
            prev_balance += self.amount
            # balance += self.amount
            # record the loss (2× the original bet is already in self.amount)
            update_user_blackjack_stats(interaction.user, "lose", self.amount)

            # persist the new balance
            collection.update_one(
                {"_id": interaction.user.id}, {"$set": {"balance": balance}}
            )

            # disable all action buttons
            self.hit.disabled = True
            self.stay.disabled = True
            self.double_down.disabled = True

            # build the “bust” fields
            self.embed.add_field(name="Result", value="Lose (bust)", inline=False)
            self.embed.add_field(
                name="Prev Balance", value=f"${prev_balance:,.2f}", inline=True
            )
            self.embed.add_field(
                name="New Balance", value=f"${balance:,.2f}", inline=True
            )

            diff = balance - prev_balance
            sign = "+" if diff >= 0 else "-"
            self.embed.add_field(
                name="Change", value=f"{sign}${abs(diff):,.2f}", inline=True
            )

            await interaction.response.edit_message(embed=self.embed, view=self)
            return

        # 5) If not busted yet, just re-render the updated embed with buttons still enabled
        await interaction.response.edit_message(embed=self.embed, view=self)

    @discord.ui.button(label="Stay", style=discord.ButtonStyle.red)
    async def stay(self, interaction: discord.Interaction, button: discord.ui.Button):
        # await interaction.response.defer(thinking=True, ephemeral=True)
        await self.result(interaction, button)

    @discord.ui.button(label="Double Down", style=discord.ButtonStyle.blurple)
    async def double_down(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        # 1) refund the original bet in‑memory
        prev_balance, balance = balance_of_player(interaction.user)
        prev_balance += self.amount
        balance += self.amount

        # 2) disable further buttons
        self.hit.disabled = True
        self.stay.disabled = True
        self.double_down.disabled = True

        # 3) deal exactly one more card
        new_card = random_card()
        self.player_cards[0].append(new_card[1])
        self.player_cards[1] += new_card[0]

        # 4) update the embed’s Player‐Hand field
        player_total = self.player_cards[1]
        if "🇦" in self.player_cards[0] and player_total <= 11:
            display_total = f"{player_total}/{player_total + 10}"
        else:
            display_total = str(player_total)

        self.embed.set_field_at(
            index=1,
            name=f"Player's Hand — {display_total}",
            value=f"{self.embed.fields[1].value} {self.player_cards[0][-1]}",
            inline=False,
        )

        # 5) double the stake and subtract that from balance
        self.amount *= 2
        balance -= self.amount

        # 6) if bust, update stats + balance immediately
        if player_total > 21:
            # record a loss of 2× the original bet
            update_user_blackjack_stats(interaction.user, "lose", self.amount)

            # persist the new balance
            collection.update_one(
                {"_id": interaction.user.id}, {"$set": {"balance": balance}}
            )

            # build your lose embed
            self.embed.add_field(name="Result", value="Lose (bust)", inline=False)
            self.embed.add_field(
                name="Prev Balance", value=f"${prev_balance:,.2f}", inline=True
            )
            self.embed.add_field(
                name="New Balance", value=f"${balance:,.2f}", inline=True
            )
            diff = balance - prev_balance
            sign = "+" if diff >= 0 else "-"
            self.embed.add_field(
                name="Change", value=f"{sign}${abs(diff):,.2f}", inline=True
            )

            await interaction.response.edit_message(embed=self.embed, view=self)
        else:
            # 7) otherwise run your full dealer‐and‐settlement logic
            #    (this will itself call update_user_blackjack_stats & set balance)
            await self.result(interaction, button)

    async def result(self, interaction: discord.Interaction, button: discord.ui.Button):
        prev_balance, balance = balance_of_player(interaction.user)
        prev_balance += self.amount
        balance += self.amount
        (
            blackjacks_won,
            blackjacks_lost,
            blackjacks_played,
            total_winnings,
            total_losses,
        ) = blackjack_stats(interaction.user)

        self.hit.disabled = True
        self.stay.disabled = True
        self.double_down.disabled = True

        # Dealer's Turn
        while self.dealer_cards[1] <= 16:
            new_card = random_card()
            self.dealer_cards[0].append(new_card[1])
            self.dealer_cards[1] += new_card[0]

            if "🇦" in self.dealer_cards[0] and 17 <= self.dealer_cards[1] + 10 <= 21:
                self.embed.set_field_at(
                    index=0,
                    name=f"Dealer's Hand - {self.dealer_cards[1]}/{self.dealer_cards[1]+10}",
                    value=f'{self.embed.fields[0].value.replace("⬛", "")} {self.dealer_cards[0][-1]}',
                    inline=False,
                )
                break
            self.embed.set_field_at(
                index=0,
                name=f"Dealer's Hand - {self.dealer_cards[1]}",
                value=f'{self.embed.fields[0].value.replace("⬛", "")} {self.dealer_cards[0][-1]}',
                inline=False,
            )

        def best_value(cards, total):
            return total + 10 if "🇦" in cards and total + 10 <= 21 else total

        dealer_value = best_value(self.dealer_cards[0], self.dealer_cards[1])
        player_value = best_value(self.player_cards[0], self.player_cards[1])

        # Determine outcome
        if dealer_value > 21 or player_value > dealer_value:
            outcome = "Win"
            balance += self.amount
            blackjacks_won += 1
        elif player_value < dealer_value:
            outcome = "Lose"
            balance -= self.amount
            blackjacks_lost += 1
        else:
            outcome = "Tie"

        update_user_blackjack_stats(interaction.user, outcome.lower(), self.amount)
        collection.update_one(
            {"_id": interaction.user.id}, {"$set": {"balance": balance}}
        )

        # Result embed
        self.embed.add_field(name="Result", value=outcome, inline=False)
        self.embed.add_field(
            name="Prev Balance", value=f"${prev_balance:,.2f}", inline=True
        )
        self.embed.add_field(name="New Balance", value=f"${balance:,.2f}", inline=True)

        diff = balance - prev_balance
        sign = "+" if diff >= 0 else "-"
        self.embed.add_field(
            name="Change", value=f"{sign}${abs(diff):,.2f}", inline=True
        )

        # Footer
        tied = blackjacks_played - blackjacks_won - blackjacks_lost
        self.embed.set_footer(
            text=f"{blackjacks_won} blackjacks won, {blackjacks_lost} lost, {tied} tied, {blackjacks_played} played"
        )

        await interaction.response.edit_message(embed=self.embed, view=self)


class FightButton(discord.ui.View):
    def __init__(self, interaction: discord.Interaction, member: discord.Member):
        super().__init__()
        self.interaction = interaction
        self.member = member
        self.embed = fight_helper(interaction, member)
        self.player = 1
        self.battle_log = ""

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if (
            self.interaction.user.id != interaction.user.id
            and self.member.id != interaction.user.id
        ):
            return False
        return True

    @discord.ui.button(label="Attack", style=discord.ButtonStyle.red)
    async def attack(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.fight_again.disabled = True
        await interaction.response.defer(thinking=True)
        player_damage = random.randint(10, 20)
        enemy_damage = random.randint(10, 20)
        if interaction.user.id == self.interaction.user.id and self.player == 1:
            # self.embed.set_field_at(index=1, name=f'{self.embed.fields[1].name}', value=f'{int(self.embed.fields[1].value)-damage}')
            if self.member.bot:
                player_health = int(self.embed.fields[0].value) - enemy_damage
                enemy_health = int(self.embed.fields[1].value) - player_damage
                self.player = 1
                if enemy_health <= 0 and player_health > 0:
                    content = f"{self.interaction.user.mention} wins $100\n"
                    enemy_health = 0
                    prev_balance, balance = balance_of_player(self.interaction.user)
                    balance += 100
                    collection.update_one(
                        {"_id": self.interaction.user.id},
                        {"$set": {"balance": balance}},
                    )
                    self.attack.disabled = True
                    self.fight_again.disabled = False
                elif player_health <= 0 and enemy_health > 0:
                    content = f"{self.member.mention} wins\n"
                    player_health = 0
                    self.attack.disabled = True
                    self.fight_again.disabled = False
                elif player_health <= 0 and enemy_health <= 0:
                    content = "it's a tie\n"
                    player_health = 0
                    enemy_damage = 0
                    self.attack.disabled = True
                    self.fight_again.disabled = False
                else:
                    self.battle_log += f"{self.interaction.user.mention} did {player_damage} damage\n{self.member.mention} did {enemy_damage} damage\n"
                    content = f"It is now {self.interaction.user.mention}'s turn\n"

                self.embed.set_field_at(
                    index=0,
                    name=f"{self.embed.fields[0].name}",
                    value=f"{player_health}",
                )
                self.embed.set_field_at(
                    index=1,
                    name=f"{self.embed.fields[1].name}",
                    value=f"{enemy_health}",
                )
                content += self.battle_log
                await interaction.followup.edit_message(
                    message_id=interaction.message.id,
                    content=content,
                    embed=self.embed,
                    view=self,
                )
            else:
                self.player = 2
                content = f"It is now {self.member.mention}'s turn\n"
                content += self.battle_log
                await interaction.followup.edit_message(
                    message_id=interaction.message.id,
                    content=content,
                    embed=self.embed,
                    view=self,
                )
        elif interaction.user.id == self.member.id and self.player == 2:
            player_health = int(self.embed.fields[0].value) - enemy_damage
            enemy_health = int(self.embed.fields[1].value) - player_damage
            self.player = 1
            if enemy_health <= 0 and player_health > 0:
                content = f"{self.interaction.user.mention} wins $100\n"
                enemy_health = 0
                prev_balance, balance = balance_of_player(self.interaction.user)
                balance += 100
                collection.update_one(
                    {"_id": self.interaction.user.id}, {"$set": {"balance": balance}}
                )
                self.attack.disabled = True
                self.fight_again.disabled = False
            elif player_health <= 0 and enemy_health > 0:
                content = f"{self.member.mention} wins $100\n"
                player_health = 0
                prev_balance, balance = balance_of_player(self.member)
                balance += 100
                collection.update_one(
                    {"_id": self.member.id}, {"$set": {"balance": balance}}
                )
                self.attack.disabled = True
                self.fight_again.disabled = False
            elif player_health <= 0 and enemy_health <= 0:
                content = "it's a tie\n"
                player_health = 0
                enemy_health = 0
                self.attack.disabled = True
                self.fight_again.disabled = False
            else:
                self.battle_log += f"{self.interaction.user.mention} did {player_damage} damage\n{self.member.mention} did {enemy_damage} damage\n"
                content = f"It is now {self.interaction.user.mention}'s turn\n"

            self.embed.set_field_at(
                index=0, name=f"{self.embed.fields[0].name}", value=f"{player_health}"
            )
            self.embed.set_field_at(
                index=1, name=f"{self.embed.fields[1].name}", value=f"{enemy_health}"
            )
            content += self.battle_log
            await interaction.followup.edit_message(
                message_id=interaction.message.id,
                content=content,
                embed=self.embed,
                view=self,
            )

    # @discord.ui.button(label="Defend", style=discord.ButtonStyle.red)
    # async def defend(self, interaction: discord.Interaction, button: discord.ui.Button):
    #     await interaction.response.defer()
    #     self.embed.set_field_at(index=1, name=f'{self.embed.fields[1].name}', value=f'{int(self.embed.fields[1].value)-5}')
    #     await interaction.followup.edit_message(message_id=interaction.message.id, embed=self.embed, view=self)

    @discord.ui.button(label="Fight Again", style=discord.ButtonStyle.blurple)
    async def fight_again(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await interaction.response.defer(thinking=True)
        content = f"It is {self.interaction.user.mention} turn"
        await interaction.followup.edit_message(
            message_id=interaction.message.id,
            content=content,
            embed=fight_helper(interaction, self.member),
            view=self,
        )


class SlotsButton(discord.ui.View):
    def __init__(
        self,
        interaction: discord.Interaction,
        amount: Optional[app_commands.Range[int, 1, None]],
    ):
        super().__init__(timeout=None)
        self.amount = amount
        self.interaction = interaction

    # this function must return a boolean, or to the very least a truthy/falsey value.
    async def interaction_check(self, interaction: discord.Interaction) -> bool:

        if self.interaction.user.id != interaction.user.id:
            await interaction.response.send_message(
                "Please start your own game with /slots", ephemeral=True
            )
            return False
        return True

    @discord.ui.button(label="Spin Again", style=discord.ButtonStyle.red)
    async def spin_again(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        content, embed = slots_helper(interaction, self.amount)
        await interaction.response.edit_message(content=content, embed=embed, view=self)


def gamble_helper(interaction: discord.Interaction, amount: Optional[int], action):
    prev_balance, balance = balance_of_player(interaction.user)
    gambles_won, gambles_lost, gambles_played, total_winnings, total_losses = (
        gamble_stats(interaction.user)
    )
    gambles_played += 1
    win_text = ""
    if action:
        amount = balance
    if amount > balance:
        embed = discord.Embed(title="Not enough balance")
        embed.add_field(name="Needed Balance", value=f"${amount:,.2f}", inline=True)
        embed.add_field(name="Balance", value=f"${balance:,.2f}", inline=True)
        return embed
    else:
        bot_number = int(random.randrange(1, 100))
        member_number = int(random.randrange(1, 100))
        if bot_number < member_number:
            balance += amount
            win_text = f"{interaction.user.mention} rolled higher"
            result = "win"
        elif bot_number > member_number:
            balance -= amount
            win_text = "Dealer rolled higher"
            result = "lose"
        else:
            win_text = "No Winners"
            result = "tie"
        # immediately update your stats in one call:
        update_user_gamble_stats(interaction.user, result, amount)

        # then save the new balance and build the embed
        collection.update_one(
            {"_id": interaction.user.id}, {"$set": {"balance": balance}}
        )

        embed = discord.Embed(
            title="Gambling Details", description=f"${amount:,.2f} bet"
        )
        embed.add_field(name="Dealer rolled a ", value=bot_number, inline=False)
        embed.add_field(
            name=f"{interaction.user} rolled a", value=member_number, inline=False
        )
        embed.add_field(name="Result", value=f"{win_text}", inline=False)
        embed.add_field(
            name="Previous Balance", value=f"${prev_balance:,.2f}", inline=True
        )
        embed.add_field(name="New Balance", value=f"${balance:,.2f}", inline=True)
        new_balance = balance - prev_balance
        if new_balance >= 0:
            embed.add_field(
                name="Result", value=f"+${abs(balance-prev_balance):,.2f}", inline=True
            )
        else:
            embed.add_field(
                name="Result", value=f"-${abs(balance-prev_balance):,.2f}", inline=True
            )
        embed.set_footer(
            text=f"{gambles_won} gambles won, {gambles_lost} gambles lost, {gambles_played - gambles_won - gambles_lost} gambles tied, {gambles_played} gambles played"
        )
        return embed


def random_card():
    dict_of_cards = {
        1: "🇦",
        2: "2️⃣",
        3: "3️⃣",
        4: "4️⃣",
        5: "5️⃣",
        6: "6️⃣",
        7: "7️⃣",
        8: "8️⃣",
        9: "9️⃣",
        10: ["🔟", "🇯", "🇶", "🇰"],
    }
    random_key = random.choice(list(dict_of_cards.keys()))
    if random_key == 10:
        random_card_choice = random.choice(dict_of_cards[random_key])
    else:
        random_card_choice = dict_of_cards[random_key]
    return [random_key, random_card_choice]


def fight_helper(interaction: discord.interactions, member: discord.Member):
    embed = discord.Embed(title="Battle Time")
    enemy_health = 100
    player_health = 100
    embed.add_field(
        name=f"{interaction.user.display_name} Health Bar",
        value=f"{player_health}",
        inline=True,
    )
    embed.add_field(
        name=f"{member.display_name} Health Bar", value=f"{enemy_health}", inline=True
    )
    return embed


def slots_helper(
    interaction: discord.Interaction, amount: Optional[app_commands.Range[int, 1, None]]
):
    # 1) Fetch previous balance
    prev_balance, balance = balance_of_player(interaction.user)

    # 2) Check stake validity
    if amount > balance:
        embed = discord.Embed(title="Not enough balance")
        embed.add_field(name="Needed", value=f"${amount:,.2f}", inline=True)
        embed.add_field(name="Current Balance", value=f"${balance:,.2f}", inline=True)
        return "", embed

    # 3) Spin the board
    emojis = "🍎🍊🍐🍋🍉🍇🍓🍒"
    board = [random.choice(emojis) for _ in range(9)]
    board_display = "\n".join(" ".join(board[i : i + 3]) for i in range(0, 9, 3))

    embed = discord.Embed(title="Slots", description=f"${amount} bet")

    # 4) Determine payout
    winning_lines = [
        (0, 1, 2),
        (3, 4, 5),
        (6, 7, 8),  # horizontals
        (0, 4, 8),
        (2, 4, 6),  # diagonals
        (0, 3, 6),
        (1, 4, 7),
        (2, 5, 8),  # verticals
    ]

    payout_amount = 0
    desc = ""
    # 4a) 3-in-line
    for a, b, c in winning_lines:
        if board[a] == board[b] == board[c]:
            payout_amount = amount * 2.75
            # embed.add_field(
            #     name="Result",
            #     value=f"3 in a line — You win ${payout_amount:,.2f}\nCurrent Balance: ${balance:,.2f}",
            #     inline=False,
            # )
            desc = "3 in a line"
            break

    # 4b) special fruits, if no line win
    if payout_amount == 0:
        counts = {
            "🍒": board.count("🍒"),
            "🍐": board.count("🍐"),
            "🍉": board.count("🍉"),
        }
        max_count = max(counts.values())

        if max_count == 3:
            payout_amount = amount * 1.5
            desc = "3 special fruits"
        elif max_count == 4:
            payout_amount = amount * 2
            desc = "4 special fruits"
        elif max_count >= 5:
            payout_amount = amount * 2.5
            desc = "5+ special fruits"
        else:
            payout_amount = -amount
            desc = "No matches"

    # 5) Apply payout to balance
    balance += payout_amount

    # 6) Update stats and balance in DB
    result_str = "win" if payout_amount > 0 else "lose"
    update_user_slots_stats(interaction.user, result_str, abs(payout_amount))
    collection.update_one({"_id": interaction.user.id}, {"$set": {"balance": balance}})
    slots_won, slots_lost, slots_played, total_winnings, total_losses = slots_stats(
        interaction.user
    )
    embed.add_field(name="Previous Balance", value=f"${prev_balance:,.2f}", inline=True)
    embed.add_field(name="Current Balance", value=f"${balance:,.2f}", inline=True)

    # Calculate the result of the slots game
    result_value = (
        f"{desc} +${abs(balance - prev_balance):,.2f}"
        if balance >= prev_balance
        else f"-${abs(balance - prev_balance):,.2f}"
    )

    embed.add_field(name="Result", value=f"{result_value}", inline=True)

    embed.set_footer(
        text=f"{slots_won} slots won, {slots_lost} slots lost, {slots_played} slots played"
    )

    return board_display, embed


class WordleGame:
    def __init__(self):
        # Word list for the game, can be extended with more words
        self.words = self.get_five_letter_words()
        self.target_word = random.choice(self.words)
        self.attempts = 0
        self.max_attempts = 6
        self.message = None
        print(self.target_word)

    def get_five_letter_words(self):
        response = requests.get("https://api.datamuse.com/words?sp=?????")
        words = [word["word"] for word in response.json()]
        return words

    def check_guess(self, guess):
        feedback = [""] * len(guess)  # Feedback array for each letter
        target_word_marked = [False] * len(
            self.target_word
        )  # Tracks matched letters in target word

        # Step 1: First pass for exact matches (Green)
        for i in range(len(guess)):
            if guess[i] == self.target_word[i]:
                feedback[i] = (
                    f"**{guess[i]}**"  # Green: Correct letter, correct position
                )
                target_word_marked[i] = True  # Mark this position as used

        # Step 2: Second pass for correct letters in wrong positions (Yellow)
        for i in range(len(guess)):
            if feedback[i]:  # Skip already marked letters
                continue
            if guess[i] in self.target_word:
                # Check if there's an unmatched instance of this letter in target_word
                for j in range(len(self.target_word)):
                    if guess[i] == self.target_word[j] and not target_word_marked[j]:
                        feedback[i] = (
                            f"__{guess[i]}__"  # Yellow: Correct letter, wrong position
                        )
                        target_word_marked[j] = True  # Mark this position as used
                        break
            # If no match, mark it as incorrect (gray)
            if not feedback[i]:
                feedback[i] = f"~~{guess[i]}~~"

        return " ".join(feedback)  # Return feedback as a string

    def is_game_over(self):
        return (
            self.attempts >= self.max_attempts or self.target_word == self.current_guess
        )


class GuessModal(discord.ui.Modal, title="Guess"):
    def __init__(self, user_id, game, games):
        super().__init__(custom_id="guess_modal")
        self.user_id = user_id
        self.game = game
        self.games = games

    feedback = discord.ui.TextInput(
        label="Enter your 5-letter guess",
        placeholder="e.g., apple",
        max_length=5,
        required=True,
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        guess = self.feedback.value.lower()

        # Validate guess
        if len(guess) != 5 or not guess.isalpha():
            await interaction.response.send_message(
                "Please enter a valid 5-letter word.", ephemeral=True
            )
            return

        feedback = self.game.check_guess(guess)
        self.game.attempts += 1
        self.game.current_guess = guess

        # Track previous attempts
        if not hasattr(self.game, "previous_attempts"):
            self.game.previous_attempts = []
        self.game.previous_attempts.append((guess, feedback))

        # Retrieve and update stats
        wordles_won, wordles_lost, wordles_played = wordle_stats(interaction.user)
        if (
            guess == self.game.target_word
            or self.game.attempts >= self.game.max_attempts
        ):
            game_over = guess == self.game.target_word
            wordles_won += int(game_over)
            wordles_lost += int(not game_over)
            wordles_played += 1

            collection.update_one(
                {"_id": interaction.user.id},
                {
                    "$set": {
                        "wordles_won": wordles_won,
                        "wordles_lost": wordles_lost,
                        "wordles_played": wordles_played,
                    }
                },
            )

            # Construct game-over message
            result_msg = (
                f"🎉 You guessed the word {self.game.target_word}!"
                if game_over
                else f"❌ Game Over! The word was {self.game.target_word}."
            )
            await self.end_game(
                interaction,
                result_msg,
                feedback,
                wordles_won,
                wordles_lost,
                wordles_played,
            )
        else:
            # Continue the game
            await self.update_game_feedback(interaction, feedback)

    async def update_game_feedback(self, interaction, feedback):
        embed = self.build_embed(
            feedback, f"Attempt {self.game.attempts}/{self.game.max_attempts}"
        )
        await self.game.message.edit(embed=embed)

    async def end_game(
        self,
        interaction,
        result_msg,
        feedback,
        wordles_won,
        wordles_lost,
        wordles_played,
    ):
        embed = self.build_embed(
            feedback, f"Attempt {self.game.attempts}/{self.game.max_attempts}"
        )
        embed.set_footer(
            text=f"{wordles_won} wordles won, {wordles_lost} wordles lost, {wordles_played} wordles played"
        )
        await self.game.message.edit(content=result_msg, embed=embed, view=None)
        del self.games[self.user_id]

    def build_embed(self, feedback, description):
        embed = discord.Embed(
            title="Wordle Attempt",
            description=description,
            color=discord.Color.blue(),
        )
        embed.add_field(name="Feedback", value=feedback, inline=False)
        embed.add_field(
            name="Previous Attempts",
            value="\n".join(
                f"{i + 1}. {attempt} - {attempt_feedback}"
                for i, (attempt, attempt_feedback) in enumerate(
                    self.game.previous_attempts
                )
            ),
            inline=False,
        )
        return embed


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Games(bot))
    print("Games is Loaded")
