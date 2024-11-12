import os
import random
from datetime import datetime
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

from utils.stats import (balance_of_player, blackjack_stats, gamble_stats,
                         slots_stats, wordle_stats)

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

    @app_commands.command(name="wordle", description="Start a Wordle-like game")
    async def wordle(self, interaction: discord.Interaction):
        user_id = interaction.user.id

        # Check if the user is already in a game
        if user_id in self.games:
            print(dir(self.games[user_id].message))
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
        view = View()
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
        await interaction.response.defer()
        view = GamblingButton(interaction, amount, action)
        embed = gamble_helper(interaction, amount, action)
        await interaction.followup.send(embed=embed, view=view)

    @app_commands.command(
        name="blackjack", description="Starts a game of blackjack with the dealer"
    )
    @app_commands.describe(amount="Amount of money you want to gamble - Default $100")
    async def blackjack(
        self,
        interaction: discord.Interaction,
        amount: Optional[app_commands.Range[int, 1, None]] = 100,
    ):
        await interaction.response.defer()
        prev_balance, balance = balance_of_player(interaction.user)
        blackjacks_won, blackjacks_lost, blackjacks_played = blackjack_stats(
            interaction.user
        )
        # checks balance of player
        # if balance is lower than amount being being cancel bet
        if amount > balance:
            embed = discord.Embed(title="Not enough balance")
            embed.add_field(name="Needed Balance", value=f"${amount:,.2f}", inline=True)
            embed.add_field(name="Balance", value=f"${balance:,.2f}", inline=True)
            await interaction.followup.send(embed=embed)
            return
        # if balance is greater than amount being bet
        # send an embed with dealer card and player cards
        # three buttons to press - Hit, Stay, Double down
        # Hit - receive another card
        # Stay - keep hand as is
        # double down - if balance greater than amount * 2 then receive one card and dealer goes
        else:
            blackjacks_played += 1
            collection.update_one(
                {"_id": interaction.user.id},
                {"$set": {"blackjacks_played": blackjacks_played}},
            )
            balance -= amount
            collection.update_one(
                {"_id": interaction.user.id}, {"$set": {"balance": balance}}
            )
            embed = discord.Embed(title="Blackjack", description=f"${amount:,.2f} bet")
            card1 = random_card()
            # dealer starts with one card and the other is covered
            # if there is an ace in the dealers hand it will total to 1 or 11
            dealer_cards = [[card1[1], "⬛"], card1[0]]
            if dealer_cards[0][0] == "🇦":
                embed.add_field(
                    name=f"Dealer's Hand - {dealer_cards[1]}/{dealer_cards[1]+10}",
                    value=f"{dealer_cards[0][0]} {dealer_cards[0][1]}",
                    inline=False,
                )
            else:
                embed.add_field(
                    name=f"Dealer's Hand - {dealer_cards[1]}",
                    value=f"{dealer_cards[0][0]} {dealer_cards[0][1]}",
                    inline=False,
                )
            card1 = random_card()
            card2 = random_card()
            # player starts with two cards
            player_cards = [[card1[1], card2[1]], card1[0] + card2[0]]
            if player_cards[0][0] == "🇦" or player_cards[0][1] == "🇦":
                embed.add_field(
                    name=f"Player's Hand - {player_cards[1]}/{player_cards[1]+10}",
                    value=f"{player_cards[0][0]} {player_cards[0][1]}",
                    inline=False,
                )
            else:
                embed.add_field(
                    name=f"Player's Hand - {player_cards[1]}",
                    value=f"{player_cards[0][0]} {player_cards[0][1]}",
                    inline=False,
                )
            # This is a natural blackjack condition
            # Player has both an Ace and a ten value card in hand totaling to 21
            # Player receives 1.5x their bet back as winnings
            if (player_cards[0][0] == "🇦" or player_cards[0][1] == "🇦") and (
                player_cards[0][0] in ["🔟", "🇯", "🇶", "🇰"]
                or player_cards[0][1] in ["🔟", "🇯", "🇶", "🇰"]
            ):
                blackjacks_won += 1
                collection.update_one(
                    {"_id": interaction.user.id},
                    {"$set": {"blackjacks_won": blackjacks_won}},
                )
                balance += amount + (amount * 1.5)
                collection.update_one(
                    {"_id": interaction.user.id}, {"$set": {"balance": balance}}
                )
                embed.add_field(name="Result", value="Win", inline=False)
                embed.add_field(
                    name="Prev Balance", value=f"${prev_balance:,.2f}", inline=True
                )
                embed.add_field(
                    name="New Balance", value=f"${balance:,.2f}", inline=True
                )
                embed.add_field(
                    name="Result", value=f"${balance-prev_balance:,.2f}", inline=True
                )
                embed.set_footer(
                    text=f"{blackjacks_won} blackjacks won, {blackjacks_lost} blackjacks lost, {blackjacks_played - blackjacks_won - blackjacks_lost} blackjacks tied, {blackjacks_played} blackjacks played"
                )
                await interaction.followup.send(embed=embed)
            # If player has no winning conditions
            # The game will continue depending on what choice the player chooses to make
            else:
                view = BlackjackButton(
                    dealer_cards, player_cards, embed, interaction, amount
                )
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
        prev_balance, balance = balance_of_player(interaction.user)
        blackjacks_won, blackjacks_lost, blackjacks_played = blackjack_stats(
            interaction.user
        )
        prev_balance += self.amount
        await interaction.response.defer()
        # player will receive a card
        # if an ace is in hand will show both values of hand with ace equaling 1 and 11
        new_card = random_card()
        self.player_cards[0].append(new_card[1])
        self.player_cards[1] += new_card[0]
        if "🇦" in self.player_cards[0] and self.player_cards[1] <= 11:
            self.embed.set_field_at(
                index=1,
                name=f"Player's Hand - {self.player_cards[1]}/{self.player_cards[1] + 10}",
                value=f"{self.embed.fields[1].value} {self.player_cards[0][-1]}",
                inline=False,
            )
        else:
            self.embed.set_field_at(
                index=1,
                name=f"Player's Hand - {self.player_cards[1]}",
                value=f"{self.embed.fields[1].value} {self.player_cards[0][-1]}",
                inline=False,
            )
        # If the players hand is above 21
        # They will lose, all buttons will be disabled and game has ended
        # Player will lose their bet
        if self.player_cards[1] > 21:
            blackjacks_lost += 1
            collection.update_one(
                {"_id": interaction.user.id},
                {"$set": {"blackjacks_lost": blackjacks_lost}},
            )
            self.hit.disabled = True
            self.stay.disabled = True
            self.double_down.disabled = True
            self.embed.add_field(name="Result", value="Lose", inline=False)
            self.embed.add_field(
                name="Prev Balance", value=f"${prev_balance:,.2f}", inline=True
            )

            self.embed.add_field(
                name="New Balance", value=f"${balance:,.2f}", inline=True
            )
            new_balance = balance - prev_balance
            if new_balance >= 0:
                self.embed.add_field(
                    name="Result", value=f"+${abs(new_balance):,.2f}", inline=True
                )
            else:
                self.embed.add_field(
                    name="Result", value=f"-${abs(new_balance):,.2f}", inline=True
                )
            self.embed.set_footer(
                text=f"{blackjacks_won} blackjacks won, {blackjacks_lost} blackjacks lost, {blackjacks_played - blackjacks_won - blackjacks_lost} blackjacks tied, {blackjacks_played} blackjacks played"
            )
        await interaction.followup.edit_message(
            message_id=interaction.message.id, embed=self.embed, view=self
        )

    @discord.ui.button(label="Stay", style=discord.ButtonStyle.red)
    async def stay(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        await self.result(interaction, button)

    @discord.ui.button(label="Double Down", style=discord.ButtonStyle.blurple)
    async def double_down(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):

        prev_balance, balance = balance_of_player(interaction.user)
        prev_balance += self.amount
        balance += self.amount
        collection.update_one(
            {"_id": interaction.user.id}, {"$set": {"balance": balance}}
        )
        blackjacks_won, blackjacks_lost, blackjacks_played = blackjack_stats(
            interaction.user
        )
        await interaction.response.defer()
        # Player will receive one card and results be determined
        # Player will receive double their bet if they win
        # Player will lose double their bet if they lose
        new_card = random_card()
        self.player_cards[0].append(new_card[1])
        self.player_cards[1] += new_card[0]
        if "🇦" in self.player_cards[0] and self.player_cards[1] <= 11:
            self.embed.set_field_at(
                index=1,
                name=f"Player's Hand - {self.player_cards[1]}/{self.player_cards[1] + 10}",
                value=f"{self.embed.fields[1].value} {self.player_cards[0][-1]}",
                inline=False,
            )

        else:
            self.embed.set_field_at(
                index=1,
                name=f"Player's Hand - {self.player_cards[1]}",
                value=f"{self.embed.fields[1].value} {self.player_cards[0][-1]}",
                inline=False,
            )
        self.amount *= 2
        balance -= self.amount
        # If player hand goes over 21
        # They will lose double their bet
        if self.player_cards[1] > 21:
            blackjacks_lost += 1
            collection.update_one(
                {"_id": interaction.user.id},
                {"$set": {"blackjacks_lost": blackjacks_lost}},
            )
            self.hit.disabled = True
            self.stay.disabled = True
            self.double_down.disabled = True

            self.embed.add_field(name="Result", value="Lose", inline=False)
            self.embed.add_field(
                name="Prev Balance", value=f"${prev_balance:,.2f}", inline=True
            )
            self.embed.add_field(
                name="New Balance", value=f"${balance:,.2f}", inline=True
            )
            new_balance = balance - prev_balance
            if new_balance >= 0:
                self.embed.add_field(
                    name="Result", value=f"+${abs(new_balance):,.2f}", inline=True
                )

            else:
                self.embed.add_field(
                    name="Result", value=f"-${abs(new_balance):,.2f}", inline=True
                )
            self.embed.set_footer(
                text=f"{blackjacks_won} blackjacks won, {blackjacks_lost} blackjacks lost, {blackjacks_played - blackjacks_won - blackjacks_lost} blackjacks tied, {blackjacks_played} blackjacks played"
            )
            await interaction.followup.edit_message(
                message_id=interaction.message.id, embed=self.embed, view=self
            )
        else:
            collection.update_one(
                {"_id": interaction.user.id}, {"$set": {"balance": balance}}
            )
            await self.result(interaction, button)

    async def result(self, interaction: discord.Interaction, button: discord.ui.Button):
        prev_balance, balance = balance_of_player(interaction.user)
        prev_balance += self.amount
        balance += self.amount
        collection.update_one(
            {"_id": interaction.user.id}, {"$set": {"balance": balance}}
        )
        blackjacks_won, blackjacks_lost, blackjacks_played = blackjack_stats(
            interaction.user
        )
        self.hit.disabled = True
        self.stay.disabled = True
        self.double_down.disabled = True
        # Dealer has to be above 17 and if above 17 they will stop
        while self.dealer_cards[1] <= 16:
            new_card = random_card()
            self.dealer_cards[0].append(new_card[1])
            self.dealer_cards[1] += new_card[0]
            if (
                "🇦" in self.dealer_cards[0]
                and self.dealer_cards[1] + 10 >= 17
                and self.dealer_cards[1] + 10 <= 21
            ):
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
        # Conditions for Win, Lose, Tie
        # If dealers hand is greater than 21
        # Dealer loses
        if self.dealer_cards[1] > 21:
            self.embed.add_field(name="Result", value="Win", inline=False)
            balance += self.amount
            blackjacks_won += 1

        elif "🇦" in self.player_cards[0] and "🇦" not in self.dealer_cards[0]:
            if (
                self.player_cards[1] + 10 > self.dealer_cards[1]
                and self.player_cards[1] + 10 <= 21
            ) or (self.player_cards[1] > self.dealer_cards[1]):
                self.embed.add_field(name="Result", value="Win", inline=False)
                balance += self.amount
                blackjacks_won += 1

            elif (
                self.player_cards[1] + 10 < self.dealer_cards[1]
                and self.player_cards[1] + 10 <= 21
            ) or (
                self.player_cards[1] < self.dealer_cards[1]
                and self.player_cards[1] + 10 != self.dealer_cards[1]
            ):
                self.embed.add_field(name="Result", value="Lose", inline=False)
                balance -= self.amount
                blackjacks_lost += 1

            elif (
                self.player_cards[1] + 10 == self.dealer_cards[1]
                and self.player_cards[1] + 10 <= 21
            ) or (self.player_cards[1] == self.dealer_cards[1]):
                self.embed.add_field(name="Result", value="Tie", inline=False)

        elif "🇦" in self.dealer_cards[0] and "🇦" not in self.player_cards[0]:
            if (
                self.dealer_cards[1] + 10 > self.player_cards[1]
                and self.dealer_cards[1] + 10 <= 21
            ) or (self.dealer_cards[1] > self.player_cards[1]):
                self.embed.add_field(name="Result", value="Lose", inline=False)
                balance -= self.amount
                blackjacks_lost += 1

            elif (
                self.dealer_cards[1] + 10 < self.player_cards[1]
                and self.dealer_cards[1] + 10 <= 21
            ) or (
                self.dealer_cards[1] < self.player_cards[1]
                and self.dealer_cards[1] + 10 != self.player_cards[1]
            ):
                self.embed.add_field(name="Result", value="Win", inline=False)
                balance += self.amount
                blackjacks_won += 1

            elif (
                self.dealer_cards[1] + 10 == self.player_cards[1]
                and self.dealer_cards[1] + 10 <= 21
            ) or (self.dealer_cards[1] == self.player_cards[1]):
                self.embed.add_field(name="Result", value="Tie", inline=False)

        elif "🇦" in self.player_cards[0] and "🇦" in self.dealer_cards[0]:
            if (
                (
                    self.player_cards[1] + 10 > self.dealer_cards[1] + 10
                    and self.player_cards[1] + 10 <= 21
                    and self.dealer_cards[1] + 10 <= 21
                )
                or (
                    self.player_cards[1] + 10 > self.dealer_cards[1]
                    and self.player_cards[1] + 10 <= 21
                    and self.dealer_cards[1] + 10 > 21
                )
                or (
                    self.player_cards[1] > self.dealer_cards[1] + 10
                    and self.dealer_cards[1] + 10 <= 21
                    and self.player_cards[1] + 10 > 21
                )
            ):
                self.embed.add_field(name="Result", value="Win", inline=False)
                balance += self.amount
                blackjacks_won += 1

            elif (
                (
                    self.dealer_cards[1] + 10 > self.player_cards[1] + 10
                    and self.dealer_cards[1] + 10 <= 21
                    and self.player_cards[1] + 10 <= 21
                )
                or (
                    self.player_cards[1] + 10 < self.dealer_cards[1]
                    and self.player_cards[1] + 10 <= 21
                    and self.dealer_cards[1] + 10 > 21
                )
                or (
                    self.player_cards[1] < self.dealer_cards[1] + 10
                    and self.dealer_cards[1] + 10 <= 21
                    and self.player_cards[1] + 10 > 21
                )
            ):
                self.embed.add_field(name="Result", value="Lose", inline=False)
                balance -= self.amount
                blackjacks_lost += 1

            elif (
                (
                    self.player_cards[1] + 10 == self.dealer_cards[1] + 10
                    and self.player_cards[1] + 10 <= 21
                    and self.dealer_cards[1] + 10 <= 21
                )
                or (
                    self.player_cards[1] + 10 == self.dealer_cards[1]
                    and self.player_cards[1] + 10 <= 21
                    and self.dealer_cards[1] <= 21
                )
                or (
                    self.player_cards[1] == self.dealer_cards[1] + 10
                    and self.player_cards[1] <= 21
                    and self.dealer_cards[1] + 10 <= 21
                )
                or (self.player_cards[1] == self.dealer_cards[1])
            ):
                self.embed.add_field(name="Result", value="Tie", inline=False)

        elif self.dealer_cards[1] == self.player_cards[1]:
            self.embed.add_field(name="Result", value="Tie", inline=False)
        elif self.dealer_cards[1] > self.player_cards[1]:
            self.embed.add_field(name="Result", value="Lose", inline=False)
            balance -= self.amount
            blackjacks_lost += 1

        elif self.dealer_cards[1] < self.player_cards[1]:
            self.embed.add_field(name="Result", value="Win", inline=False)
            balance += self.amount
            blackjacks_won += 1

        collection.update_one(
            {"_id": interaction.user.id}, {"$set": {"balance": balance}}
        )
        self.embed.add_field(
            name="Prev Balance", value=f"${prev_balance:,.2f}", inline=True
        )
        self.embed.add_field(name="New Balance", value=f"${balance:,.2f}", inline=True)
        new_balance = balance - prev_balance
        if new_balance >= 0:
            self.embed.add_field(
                name="Result", value=f"+${abs(new_balance):,.2f}", inline=True
            )
        else:
            self.embed.add_field(
                name="Result", value=f"-${abs(new_balance):,.2f}", inline=True
            )

        collection.update_one(
            {"_id": interaction.user.id}, {"$set": {"blackjacks_won": blackjacks_won}}
        )
        collection.update_one(
            {"_id": interaction.user.id}, {"$set": {"blackjacks_lost": blackjacks_lost}}
        )
        self.embed.set_footer(
            text=f"{blackjacks_won} blackjacks won, {blackjacks_lost} blackjacks lost, {blackjacks_played - blackjacks_won - blackjacks_lost} blackjacks tied, {blackjacks_played} blackjacks played"
        )
        await interaction.followup.edit_message(
            message_id=interaction.message.id, embed=self.embed, view=self
        )


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
        await interaction.response.defer()
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
        await interaction.response.defer()
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
    gambles_won, gambles_lost, gambles_played = gamble_stats(interaction.user)
    gambles_played += 1
    if action:
        amount = balance
    win = ""
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
            gambles_won += 1
            collection.update_one(
                {"_id": interaction.user.id}, {"$set": {"balance": balance}}
            )
            win = f"{interaction.user.mention} rolled a higher number"
        elif bot_number > member_number:
            balance -= amount
            gambles_lost += 1
            collection.update_one(
                {"_id": interaction.user.id}, {"$set": {"balance": balance}}
            )
            win = "Dealer rolled a higher number"
        elif bot_number == member_number:
            win = "No Winners"
        embed = discord.Embed(
            title="Gambling Details", description=f"${amount:,.2f} bet"
        )
        embed.add_field(name="Dealer rolled a ", value=bot_number, inline=False)
        embed.add_field(
            name=f"{interaction.user} rolled a", value=member_number, inline=False
        )
        embed.add_field(name="Result", value=f"{win}", inline=False)
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

        collection.update_one(
            {"_id": interaction.user.id}, {"$set": {"gambles_won": gambles_won}}
        )
        collection.update_one(
            {"_id": interaction.user.id}, {"$set": {"gambles_lost": gambles_lost}}
        )
        collection.update_one(
            {"_id": interaction.user.id},
            {"$set": {"gambles_played": gambles_played}},
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
    prev_balance, balance = balance_of_player(interaction.user)
    slots_won, slots_lost, slots_played = slots_stats(interaction.user)
    slots_played += 1
    board_display = ""
    # Check if player has sufficient balance
    if amount > balance:
        embed = discord.Embed(title="Not enough balance")
        embed.add_field(name="Needed Balance", value=f"${amount:,.2f}", inline=True)
        embed.add_field(name="Balance", value=f"${balance:,.2f}", inline=True)
        return board_display, embed

    # Set up slot emojis and display board
    emojis = "🍎🍊🍐🍋🍉🍇🍓🍒"
    board = [random.choice(emojis) for _ in range(9)]
    for i in range(0, 9, 3):
        board_display += " ".join(board[i : i + 3]) + "\n"

    embed = discord.Embed(title="Slots", description=f"${amount} bet")

    # Define win conditions for different payouts
    winning_lines = [
        (0, 1, 2),
        (3, 4, 5),
        (6, 7, 8),  # Horizontal
        (0, 4, 8),
        (2, 4, 6),  # Diagonal
        (0, 3, 6),
        (1, 4, 7),
        (2, 5, 8),  # Vertical
    ]

    # Check for 3-in-line win
    won = False
    for line in winning_lines:
        if board[line[0]] == board[line[1]] == board[line[2]]:
            balance += amount * 3
            slots_won += 1
            embed.add_field(
                name="Result",
                value=f"3 in a line - ${amount*3:,.2f} won - New Balance ${balance:,.2f}",
                inline=False,
            )
            won = True
            break

    # Check for special fruit bonuses if no 3-in-line win
    if not won:
        cherry_count, pear_count, melon_count = (
            board.count("🍒"),
            board.count("🍐"),
            board.count("🍉"),
        )
        max_special_fruits = max(cherry_count, pear_count, melon_count)

        if max_special_fruits == 3:
            balance += amount * 1.5
            slots_won += 1
            embed.add_field(
                name="Result",
                value=f"3 special fruits - ${amount*1.5:,.2f} won - New Balance ${balance:,.2f}",
                inline=False,
            )
        elif max_special_fruits == 4:
            balance += amount * 2
            slots_won += 1
            embed.add_field(
                name="Result",
                value=f"4 special fruits - ${amount*2:,.2f} won - New Balance ${balance:,.2f}",
                inline=False,
            )
        elif max_special_fruits >= 5:
            balance += amount * 2.5
            slots_won += 1
            embed.add_field(
                name="Result",
                value=f"5 or more special fruits - ${amount*2.5:,.2f} won - New Balance ${balance:,.2f}",
                inline=False,
            )
        else:
            balance -= amount
            slots_lost += 1
            embed.add_field(
                name="Result",
                value=f"No matches - New Balance ${balance:,.2f}",
                inline=False,
            )

    # Update all user stats in a single database call
    collection.update_one(
        {"_id": interaction.user.id},
        {
            "$set": {
                "slots_won": slots_won,
                "slots_lost": slots_lost,
                "slots_played": slots_played,
                "balance": balance,
            }
        },
    )

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
