from email import message
import email
from faulthandler import disable
from bs4 import BeautifulSoup
from datetime import datetime
from discord import app_commands
from discord.app_commands import Choice
from discord.ext import commands
from dotenv import load_dotenv
from pymongo import MongoClient
from typing import Optional
import discord
import os
import random
import requests

load_dotenv()
GAMES = os.getenv("GAMES")
list_of_guilds = os.getenv("GUILDS").split(",")
MY_GUILDS = [discord.Object(id=int(guild)) for guild in list_of_guilds]
MONGO_URL = os.getenv("ATLAS_URI")
cluster = MongoClient(MONGO_URL)
db = cluster["Users"]
collection = db["UserData"]


class Games(commands.Cog):
    """Games functions"""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(
        name="games", description="Provide the google sheet links to games"
    )
    async def games(self, interaction: discord.Interaction):
        
        """Provide the google sheet links to games"""
        view = GamesList()
        await interaction.response.send_message(
            f'Games Channel: <#629459633031086080>', view=view
        )
        
    @app_commands.command(name="add_game", description="add a game to games channel")
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
    async def add(
        self,
        interaction: discord.Interaction,
        add: str,
        download_link: str,
        steam_link: str,
    ):
        """Adds two numbers together."""

        # bs4 to parse through steam link for data
        url = steam_link
        response = requests.get(url)
        soup = BeautifulSoup(response.text, features="html.parser")

        title = soup.select_one('div[class="apphub_AppName"]').contents[0]
        description = soup.find("meta", property="og:description")["content"]
        image = soup.find("meta", property="og:image")["content"]
        price = soup.find("meta", itemprop="price")["content"]
        reviews = soup.find("meta", itemprop="reviewCount")["content"]
        app_id = steam_link.split("/")[4]

        embed = discord.Embed(title=f"{add} - {title}", color=0x336EFF, url=steam_link)
        embed.add_field(
            name="Direct Download Link",
            value=f"[Click Here]({download_link})",
            inline=False,
        )
        embed.add_field(
            name="Full Games List", value=f"[Click Here]({GAMES})", inline=False
        )
        embed.add_field(name="Steam Link", value=f"{steam_link}", inline=False)
        embed.add_field(name="Description", value=f"{description}", inline=False)
        embed.add_field(name="Price", value=f"{price}", inline=True)
        embed.add_field(name="Reviews", value=f"{reviews}", inline=True)
        embed.add_field(name="App Id", value=f"{app_id}", inline=True)
        embed.set_image(url=image)
        embed.timestamp = datetime.now()
        embed.set_footer(text=f"{interaction.user}", icon_url=interaction.user.avatar)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(
        name="gamble", description="Chance to win or lose money - Default $100"
    )
    @app_commands.describe(amount="Amount of money you want to gamble - Default $100")
    async def gamble(
        self, interaction: discord.Interaction, amount: Optional[int] = 100
    ):
        await interaction.response.defer()
        view = GamblingButton(interaction, amount)
        embed = gamble_helper(interaction, amount)
        await interaction.followup.send(embed=embed, view=view)

    @app_commands.command(
        name="blackjack", description="Starts a game of blackjack with the dealer"
    )
    @app_commands.describe(amount="Amount of money you want to gamble - Default $100")
    async def blackjack(
        self, interaction: discord.Interaction, amount: Optional[int] = 100
    ):
        await interaction.response.defer()
        prev_balance, balance = balance_of_player(interaction.user)
        if amount > balance:
            embed = discord.Embed(
                title="Not enough balance", description=f"${amount:,} bet"
            )
            embed.add_field(name="Needed Balance", value=f"${amount:,}", inline=True)
            embed.add_field(name="Balance", value=f"${balance:,}", inline=True)
            await interaction.followup.send(embed=embed)

        else:
            prev_balance += amount
            balance -= amount
            collection.update_one(
                {"_id": interaction.user.id}, {"$set": {"balance": balance}}
            )
            embed = discord.Embed(title="Blackjack")
            card1 = random_card()
            dealer_cards = [[card1[1], "⬛"], card1[0]]
            if(dealer_cards[0][0] == "🇦"):
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
            player_cards = [[card1[1], card2[1]], card1[0] + card2[0]]
            
            if(player_cards[0][0] == "🇦" or player_cards[0][1] == "🇦"):
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
            if(player_cards[0][0] == "🇦" or player_cards[0][1] == "🇦") and (player_cards[0][0] in ["🔟", "🇯", "🇶", "🇰"] or player_cards[0][1] in ["🔟", "🇯", "🇶", "🇰"]):
                prev_balance += amount
                balance += amount
                balance += amount * 1.5
                collection.update_one(
                    {"_id": interaction.user.id}, {"$set": {"balance": balance}}
                )
                embed.add_field(name="Result", value="Win", inline=False)
                embed.add_field(name="Prev Balance", value = f'${prev_balance:,}', inline=True)
                embed.add_field(name="New Balance", value = f'${balance:,}', inline=True)
                embed.add_field(name="Result", value = f'${balance-prev_balance:,}', inline=True)
                await interaction.followup.send(embed=embed)
            else:
                view = BlackjackButton(dealer_cards, player_cards, embed, interaction, amount)
                await interaction.followup.send(embed=embed, view=view)

    @app_commands.command(name="fight")
    async def fight(self, interaction: discord.Interaction, member: Optional[discord.Member] = None):
        if not member:
            member = self.bot.user
        view = FightButton(interaction, member)
        content = f'It is {interaction.user.mention} turn'
        await interaction.response.send_message(embed=fight_helper(interaction, member),content=content, view=view)
        
        
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
    def __init__(self, interaction: discord.Interaction, amount: Optional[int]):
        super().__init__(timeout=None)
        self.amount = amount
        self.interaction = interaction

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
        embed = gamble_helper(interaction, self.amount)
        await interaction.response.edit_message(embed=embed, view=self)

class BlackjackButton(discord.ui.View):
    def __init__(
        self,
        dealer_cards: list,
        player_cards: list,
        embed: discord.Embed,
        interaction: discord.Interaction,
        amount: Optional[int] = 100
    ):
        super().__init__(timeout=None)
        self.dealer_cards = dealer_cards
        self.player_cards = player_cards
        self.embed = embed
        self.interaction = interaction
        self.amount = amount

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
        await interaction.response.defer()
        new_card = random_card()
        self.player_cards[0].append(new_card[1])
        self.player_cards[1] += new_card[0]
        if("🇦" in self.player_cards[0] and self.player_cards[1] <=10 and self.player_cards[1] +10 <=21):
            self.embed.set_field_at(
            index=1,
            name=f"Player's Hand - {self.player_cards[1]}/{self.player_cards[1]+10}",
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
        if self.player_cards[1] > 21:
            button.disabled = True
            self.stay.disabled = True
            prev_balance += self.amount
            collection.update_one(
                {"_id": interaction.user.id}, {"$set": {"balance": balance}}
            )
            self.embed.add_field(name="Result", value="Lose", inline=False)
            self.embed.add_field(name="Prev Balance", value = f'${prev_balance:,}', inline=True)
            self.embed.add_field(name="New Balance", value = f'${balance:,}', inline=True)
            self.embed.add_field(name="Result", value = f'${balance-prev_balance:,}', inline=True)
            await interaction.followup.edit_message(
                message_id=interaction.message.id, embed=self.embed, view=self
            )
        else:
            await interaction.followup.edit_message(
                message_id=interaction.message.id, embed=self.embed, view=self
            )

    @discord.ui.button(label="Stay", style=discord.ButtonStyle.red)
    async def stay(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        await self.result(interaction, button)

    async def result(self, interaction: discord.Interaction, button: discord.ui.Button):
        prev_balance, balance = balance_of_player(interaction.user)
        prev_balance += self.amount
        balance += self.amount
        collection.update_one(
                {"_id": interaction.user.id}, {"$set": {"balance": balance}}
            )
        self.hit.disabled = True
        self.stay.disabled = True
        while self.dealer_cards[1] <= 16:
            new_card = random_card()
            self.dealer_cards[0].append(new_card[1])
            self.dealer_cards[1] += new_card[0]
            if("🇦" in self.dealer_cards[0] and self.dealer_cards[1] +10 >=17 and self.dealer_cards[1] + 10 <=21):
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
        if self.dealer_cards[1] > 21:
            self.embed.add_field(name="Result", value="Win", inline=False)
            balance += self.amount
            collection.update_one(
                {"_id": interaction.user.id}, {"$set": {"balance": balance}}
            )
        elif "🇦" in self.player_cards[0] and "🇦" not in self.dealer_cards[0]:
            if(self.player_cards[1] + 10 > self.dealer_cards[1] and self.player_cards[1]+10 <= 21):
                self.embed.add_field(name="Result", value="Win", inline=False)
                balance += self.amount
                collection.update_one(
                    {"_id": interaction.user.id}, {"$set": {"balance": balance}}
                )
            elif(self.player_cards[1] + 10 < self.dealer_cards[1] and self.player_cards[1]+10 <= 21):
                self.embed.add_field(name="Result", value="Lose", inline=False)
                balance -= self.amount
                collection.update_one(
                    {"_id": interaction.user.id}, {"$set": {"balance": balance}}
                )
            elif(self.player_cards[1] + 10 == self.dealer_cards[1] and self.player_cards[1]+10 <= 21):
                self.embed.add_field(name="Result", value="Tie", inline=False)
            elif(self.player_cards[1] > self.dealer_cards[1]):
                self.embed.add_field(name="Result", value="Win", inline=False)
                balance += self.amount
                collection.update_one(
                    {"_id": interaction.user.id}, {"$set": {"balance": balance}}
                )
            elif(self.player_cards[1] < self.dealer_cards[1]):
                self.embed.add_field(name="Result", value="Lose", inline=False)
                balance -= self.amount
                collection.update_one(
                    {"_id": interaction.user.id}, {"$set": {"balance": balance}}
                )
            elif(self.player_cards[1] == self.dealer_cards[1]):
                self.embed.add_field(name="Result", value="Tie", inline=False)
        elif "🇦" in self.dealer_cards[0] and "🇦" not in self.player_cards[0]:
            if(self.dealer_cards[1] + 10 > self.player_cards[1] and self.dealer_cards[1]+10 <= 21):
                self.embed.add_field(name="Result", value="Lose", inline=False)
                balance -= self.amount
                collection.update_one(
                    {"_id": interaction.user.id}, {"$set": {"balance": balance}}
                )
            elif(self.dealer_cards[1] + 10 < self.player_cards[1] and self.dealer_cards[1]+10 <= 21):
                self.embed.add_field(name="Result", value="Win", inline=False)
                balance += self.amount
                collection.update_one(
                    {"_id": interaction.user.id}, {"$set": {"balance": balance}}
                )
            elif(self.dealer_cards[1] + 10 == self.player_cards[1] and self.dealer_cards[1]+10 <= 21):
                self.embed.add_field(name="Result", value="Tie", inline=False)
            elif(self.dealer_cards[1] > self.player_cards[1]):
                self.embed.add_field(name="Result", value="Lose", inline=False)
                balance -= self.amount
                collection.update_one(
                    {"_id": interaction.user.id}, {"$set": {"balance": balance}}
                )
            elif(self.dealer_cards[1]  < self.player_cards[1]):
                self.embed.add_field(name="Result", value="Win", inline=False)
                balance += self.amount
                collection.update_one(
                    {"_id": interaction.user.id}, {"$set": {"balance": balance}}
                )
            elif(self.dealer_cards[1] == self.player_cards[1]):
                self.embed.add_field(name="Result", value="Tie", inline=False)
        elif "🇦" in self.player_cards[0] and "🇦" in self.dealer_cards[0]:
            if(self.player_cards[1] + 10 > self.dealer_cards[1] + 10 and self.player_cards[1]+10 <= 21 and self.dealer_cards[1] + 10 <=21):
                self.embed.add_field(name="Result", value="Win", inline=False)
                balance += self.amount
                collection.update_one(
                    {"_id": interaction.user.id}, {"$set": {"balance": balance}}
                )
            elif(self.dealer_cards[1] + 10 > self.player_cards[1]+10 and self.dealer_cards[1]+10 <= 21 and self.player_cards[1] + 10 <=21):
                self.embed.add_field(name="Result", value="Lose", inline=False)
                balance -= self.amount
                collection.update_one(
                    {"_id": interaction.user.id}, {"$set": {"balance": balance}}
                )
            elif(self.player_cards[1] + 10 == self.dealer_cards[1] + 10 and self.player_cards[1]+10 <= 21 and self.dealer_cards[1] + 10 <=21):
                self.embed.add_field(name="Result", value="Tie", inline=False)
            elif(self.player_cards[1] + 10 > self.dealer_cards[1] and self.player_cards[1]+10 <= 21 and self.dealer_cards[1] <=21):
                self.embed.add_field(name="Result", value="Win", inline=False)
                balance += self.amount
                collection.update_one(
                    {"_id": interaction.user.id}, {"$set": {"balance": balance}}
                )
            elif(self.player_cards[1] > self.dealer_cards[1] + 10 and self.player_cards[1] <= 21 and self.dealer_cards[1] + 10 <=21):
                self.embed.add_field(name="Result", value="Win", inline=False)
                balance += self.amount
                collection.update_one(
                    {"_id": interaction.user.id}, {"$set": {"balance": balance}}
                )
            elif(self.player_cards[1] + 10 < self.dealer_cards[1] and self.player_cards[1]+10 <= 21 and self.dealer_cards[1] <=21):
                self.embed.add_field(name="Result", value="Lose", inline=False)
                balance -= self.amount
                collection.update_one(
                    {"_id": interaction.user.id}, {"$set": {"balance": balance}}
                )
            elif(self.player_cards[1] < self.dealer_cards[1] + 10 and self.player_cards[1] <= 21 and self.dealer_cards[1] + 10 <=21):
                self.embed.add_field(name="Result", value="Lose", inline=False)
                balance -= self.amount
                collection.update_one(
                    {"_id": interaction.user.id}, {"$set": {"balance": balance}}
                )
            elif(self.player_cards[1] + 10 == self.dealer_cards[1] and self.player_cards[1]+10 <= 21 and self.dealer_cards[1] <=21):
                self.embed.add_field(name="Result", value="Tie", inline=False)
            elif(self.player_cards[1] == self.dealer_cards[1] + 10 and self.player_cards[1] <= 21 and self.dealer_cards[1] + 10 <=21):
                self.embed.add_field(name="Result", value="Tie", inline=False)
                
            elif(self.player_cards[1] < self.dealer_cards[1]):
                self.embed.add_field(name="Result", value="Lose", inline=False)
                balance -= self.amount
                collection.update_one(
                    {"_id": interaction.user.id}, {"$set": {"balance": balance}}
                )
            elif(self.player_cards[1] > self.dealer_cards[1] + 10):
                self.embed.add_field(name="Result", value="Win", inline=False)
                balance += self.amount
                collection.update_one(
                    {"_id": interaction.user.id}, {"$set": {"balance": balance}}
                )
        elif self.dealer_cards[1] == self.player_cards[1]:
            self.embed.add_field(name="Result", value="Tie", inline=False)
        elif self.dealer_cards[1] > self.player_cards[1]:
            self.embed.add_field(name="Result", value="Lose", inline=False)
            balance -= self.amount
            collection.update_one(
                {"_id": interaction.user.id}, {"$set": {"balance": balance}}
            )
        elif self.dealer_cards[1] < self.player_cards[1]:
            self.embed.add_field(name="Result", value="Win", inline=False)
            balance += self.amount
            collection.update_one(
                {"_id": interaction.user.id}, {"$set": {"balance": balance}}
            )
        self.embed.add_field(name="Prev Balance", value = f'${prev_balance:,}', inline=True)
        self.embed.add_field(name="New Balance", value = f'${balance:,}', inline=True)
        self.embed.add_field(name="Result", value = f'${balance-prev_balance:,}', inline=True)
        await interaction.followup.edit_message(
                message_id=interaction.message.id, embed=self.embed, view=self
            )

class FightButton(discord.ui.View):
    def __init__(self,interaction:discord.Interaction, member: discord.Member):
        super().__init__()
        self.interaction = interaction
        self.member = member
        self.embed = fight_helper(interaction, member)
        self.player = 1
        self.battle_log = ""
        
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if self.interaction.user.id != interaction.user.id and self.member.id != interaction.user.id:
            return False
        return True
    
    @discord.ui.button(label="Attack", style=discord.ButtonStyle.red)
    async def attack(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        player_damage = random.randint(10,20)
        enemy_damage = random.randint(10,20)
        if(interaction.user.id == self.interaction.user.id and self.player == 1):
            #self.embed.set_field_at(index=1, name=f'{self.embed.fields[1].name}', value=f'{int(self.embed.fields[1].value)-damage}')
            if(self.member.bot):
                player_health = int(self.embed.fields[0].value)- enemy_damage
                enemy_health = int(self.embed.fields[1].value) - player_damage
                self.player = 1
                if(enemy_health <= 0 and player_health > 0):
                    content=f'{self.interaction.user.mention} wins $100\n'
                    enemy_health = 0
                    prev_balance, balance = balance_of_player(self.interaction.user)
                    balance +=100
                    collection.update_one(
                    {"_id": self.interaction.user.id}, {"$set": {"balance": balance}}
                    )
                    self.attack = False
                elif(player_health <= 0 and enemy_health > 0):
                    content=f'{self.member.mention} wins\n'
                    player_health = 0
                    self.attack = False
                elif(player_health <= 0 and enemy_health <= 0):
                    content=f'it\'s a tie\n'
                    player_health = 0
                    enemy_damage = 0
                    self.attack = False
                else:
                    self.battle_log += f'{self.interaction.user.mention} did {player_damage} damage\n{self.member.mention} did {enemy_damage} damage\n'
                    content = f'It is now {self.interaction.user.mention}\'s turn\n'
                
                self.embed.set_field_at(index=0, name=f'{self.embed.fields[0].name}', value=f'{player_health}')
                self.embed.set_field_at(index=1, name=f'{self.embed.fields[1].name}', value=f'{enemy_health}')
                content += self.battle_log
                await interaction.followup.edit_message(message_id=interaction.message.id, content= content, embed=self.embed, view=self)
            else:
                self.player = 2
                content = f'It is now {self.member.mention}\'s turn\n'
                content += self.battle_log
                await interaction.followup.edit_message(message_id=interaction.message.id, content= content, embed=self.embed, view=self)
        elif(interaction.user.id == self.member.id and self.player == 2):
            player_health = int(self.embed.fields[0].value)- enemy_damage
            enemy_health = int(self.embed.fields[1].value) - player_damage
            self.player = 1
            if(enemy_health <= 0 and player_health > 0):
                content=f'{self.interaction.user.mention} wins $100\n'
                enemy_health = 0
                prev_balance, balance = balance_of_player(self.interaction.user)
                balance +=100
                collection.update_one(
                {"_id": self.interaction.user.id}, {"$set": {"balance": balance}}
                )
                self.attack = False
            elif(player_health <= 0 and enemy_health > 0):
                content=f'{self.member.mention} wins $100\n'
                player_health = 0
                prev_balance, balance = balance_of_player(self.member)
                balance += 100
                collection.update_one(
                {"_id": self.member.id}, {"$set": {"balance": balance}}
                )
                self.attack = False
            elif(player_health <= 0 and enemy_health <= 0):
                content=f'it\'s a tie\n'
                player_health = 0
                enemy_health = 0
                self.attack = False
            else:
                self.battle_log += f'{self.interaction.user.mention} did {player_damage} damage\n{self.member.mention} did {enemy_damage} damage\n'
                content = f'It is now {self.interaction.user.mention}\'s turn\n'
            
            self.embed.set_field_at(index=0, name=f'{self.embed.fields[0].name}', value=f'{player_health}')
            self.embed.set_field_at(index=1, name=f'{self.embed.fields[1].name}', value=f'{enemy_health}')
            content += self.battle_log
            await interaction.followup.edit_message(message_id=interaction.message.id, content= content, embed=self.embed, view=self)

    # @discord.ui.button(label="Defend", style=discord.ButtonStyle.red)
    # async def defend(self, interaction: discord.Interaction, button: discord.ui.Button):
    #     await interaction.response.defer()
    #     self.embed.set_field_at(index=1, name=f'{self.embed.fields[1].name}', value=f'{int(self.embed.fields[1].value)-5}')
    #     await interaction.followup.edit_message(message_id=interaction.message.id, embed=self.embed, view=self)
    
    @discord.ui.button(label="Fight Again", style=discord.ButtonStyle.blurple)
    async def fight_again(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        content = f'It is {self.interaction.user.mention} turn'
        await interaction.followup.edit_message(message_id= interaction.message.id,content=content, embed = fight_helper(interaction, self.member),view = self)
        
def gamble_helper(interaction: discord.Interaction, amount: Optional[int]):
    prev_balance, balance = balance_of_player(interaction)
    win = ""
    if amount > balance:
        embed = discord.Embed(
            title="Not enough balance", description=f"${amount:,} bet"
        )
        embed.add_field(name="Needed Balance", value=f"${amount:,}", inline=True)
        embed.add_field(name="Balance", value=f"${balance:,}", inline=True)
        return embed
    else:
        bot_number = int(random.randrange(1, 100))
        member_number = int(random.randrange(1, 100))
        if bot_number < member_number:
            balance += amount
            collection.update_one(
                {"_id": interaction.user.id}, {"$set": {"balance": balance}}
            )
            win = f"{interaction.user.mention} rolled a higher number"
        elif bot_number > member_number:
            balance -= amount
            collection.update_one(
                {"_id": interaction.user.id}, {"$set": {"balance": balance}}
            )
            win = f'Dealer rolled a higher number'
        elif bot_number == member_number:
            win = "No Winners"
        embed = discord.Embed(title="Gambling Details", description=f"${amount:,} bet")
        embed.add_field(name="Dealer rolled a ", value=bot_number, inline=False)
        embed.add_field(
            name=f"{interaction.user} rolled a", value=member_number, inline=False
        )
        embed.add_field(name="Result", value=f"{win}", inline=False)
        embed.add_field(
            name="Previous Balance", value=f"${prev_balance:,}", inline=True
        )
        embed.add_field(name="New Balance", value=f"${balance:,}", inline=True)
        new_balance = balance - prev_balance
        if new_balance >= 0:
            embed.add_field(
                name="Result", value=f"+${abs(balance-prev_balance):,}", inline=True
            )
        else:
            embed.add_field(
                name="Result", value=f"-${abs(balance-prev_balance):,}", inline=True
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
    
def fight_helper(interaction: discord.interactions, member: discord.Member):
    embed = discord.Embed(title=f"Battle Time")
    enemy_health = 100
    player_health = 100
    embed.add_field(name=f'{interaction.user.display_name} Health Bar', value=f'{player_health}', inline=True)
    embed.add_field(name=f'{member.display_name} Health Bar', value=f'{enemy_health}', inline=True)
    return embed
    
async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Games(bot), guilds=MY_GUILDS)
    print("Games is Loaded")
