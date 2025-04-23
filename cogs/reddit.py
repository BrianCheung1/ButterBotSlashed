import os

import aiosqlite
import asyncpraw
import discord
from discord import app_commands
from discord.ext import commands, tasks
from dotenv import load_dotenv

load_dotenv()
REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")


class Reddit(commands.Cog):
    """Basic Features"""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.reddit = asyncpraw.Reddit(
            client_id=REDDIT_CLIENT_ID,
            client_secret=REDDIT_CLIENT_SECRET,
            user_agent="discord:reddit-notifier:v1.0 (by u/your_username)",
        )
        self.tracked_users = {}
        self.latest_posts = {}
        self.latest_comments = {}
        self.db_folder = "database/reddit"

        # Ensure the 'database' folder exists
        if not os.path.exists(self.db_folder):
            os.makedirs(self.db_folder)

        # Specify the full path for the database
        self.db_path = os.path.join(self.db_folder, "reddit_alerts.db")

        # Call create_table once at initialization
        self.bot.loop.create_task(self.create_table())
        # Load users when the bot starts
        self.bot.loop.create_task(
            self.load_users()
        )  # Load users immediately on initialization
        self.check_reddit.start()  # Start the background task for Reddit

    def cog_unload(self):
        """Stop the task when the cog is unloaded."""
        self.check_reddit.cancel()

    async def create_table(self):
        """Create the necessary database table if it doesn't exist."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """CREATE TABLE IF NOT EXISTS reddit_users (
                    username TEXT PRIMARY KEY,
                    channel_id INTEGER,
                    subreddit TEXT,
                    last_post_time INTEGER,
                    post_title TEXT,
                    last_comment_time INTEGER,
                    comment TEXT,
                    track_type TEXT DEFAULT 'both'
                )"""
            )
            await db.commit()

    def get_db_name(self, guild_id: int) -> str:
        """Generate a unique database name based on the guild ID."""
        return f"reddit_{guild_id}.db"

    async def username_autocomplete(
        self, interaction: discord.Interaction, current: str
    ):
        """Autocomplete function for tracking Reddit users."""
        print(f"Autocomplete triggered with input: {current}")
        return [
            app_commands.Choice(name=user, value=user)
            for user in self.tracked_users.keys()
            if current.lower() in user.lower()
        ]

    async def save_user(
        self,
        username: str,
        channel_id: int,
        subreddit: str = None,
        last_post_time: int = 0,
        post_title: str = None,
        last_comment_time: int = 0,
        comment: str = None,
        track_type: str = "posts",
    ):
        """Save a tracked user to the database."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT OR REPLACE INTO reddit_users
                (username, channel_id, subreddit, last_post_time, post_title, last_comment_time, comment, track_type)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    username,
                    channel_id,
                    subreddit,
                    last_post_time,
                    post_title,
                    last_comment_time,
                    comment,
                    track_type,
                ),
            )
            await db.commit()

    async def load_users(self):
        """Load tracked Reddit users with subreddit filters, timestamps, and post titles."""
        self.tracked_users = {}  # Initialize an empty dictionary

        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT username, channel_id, subreddit, last_post_time, post_title, last_comment_time, comment, track_type FROM reddit_users"
            ) as cursor:
                async for row in cursor:
                    (
                        username,
                        channel_id,
                        subreddit,
                        last_post_time,
                        post_title,
                        last_comment_time,
                        comment,
                        track_type,
                    ) = row

                    # ✅ Correctly store each user in the dictionary
                    self.tracked_users[username] = {
                        "channel_id": channel_id,
                        "subreddit": subreddit,
                        "last_post_time": last_post_time or 0,
                        "post_title": post_title or "",
                        "last_comment_time": last_comment_time or 0,
                        "comment": comment or "",
                        "track_type": track_type or "both",
                    }

        if not self.tracked_users:
            print("⚠️ No Reddit users are currently being tracked.")
        else:
            print(f"✅ Loaded {len(self.tracked_users)} users from the database.")

    async def remove_user(self, username: str):
        """Remove a Reddit user from the database."""
        self.db = await aiosqlite.connect(self.db_path)
        await self.db.execute(
            "DELETE FROM reddit_users WHERE username = ?", (username,)
        )
        await self.db.commit()

    @app_commands.command(
        name="track_reddit",
        description="Track a Reddit user for new posts and/or comments.",
    )
    @app_commands.choices(
        track_type=[
            app_commands.Choice(name="Posts Only", value="posts"),
            app_commands.Choice(name="Comments Only", value="comments"),
            app_commands.Choice(name="Both", value="both"),
        ]
    )
    async def track_reddit(
        self,
        interaction: discord.Interaction,
        username: str,
        track_type: app_commands.Choice[str],
    ):
        """Track a Reddit user for new posts, comments, or both."""
        if username not in self.tracked_users:
            self.tracked_users[username] = {
                "channel_id": interaction.channel.id,
                "track_type": track_type.value,  # Store tracking type
                "last_post_time": 0,
                "last_comment_time": 0,
            }

            await self.save_user(
                username, interaction.channel.id, track_type=track_type.value
            )  # Save user to the database
            await interaction.response.send_message(
                f"✅ Now tracking [u/{username}](<https://www.reddit.com/user/{username}>) for **{track_type.name.lower()}**."
            )
        else:
            await interaction.response.send_message(
                f"⚠️ Already tracking u/{username} for **{self.tracked_users[username]['track_type']}**."
            )

    @app_commands.command(
        name="stop_reddit", description="Stop tracking a Reddit user."
    )
    @app_commands.autocomplete(username=username_autocomplete)
    async def stop_reddit(self, interaction: discord.Interaction, username: str):
        """Stop tracking a Reddit user."""
        if username in self.tracked_users:
            del self.tracked_users[username]
            await self.remove_user(username)  # Remove user from the database
            await interaction.response.send_message(
                f"✅ Stopped tracking posts from u/{username}."
            )
        else:
            await interaction.response.send_message(
                f"⚠️ u/{username} is not being tracked."
            )

    @app_commands.command(
        name="list_reddit",
        description="List all tracked Reddit users with their track type.",
    )
    async def list_reddit(self, interaction: discord.Interaction):
        """List all tracked Reddit users with links to their profiles and their track type."""
        if self.tracked_users:
            users = "\n".join(
                f"[u/{username}](<https://www.reddit.com/user/{username}>) - **{data.get('track_type', 'unknown')}**"
                for username, data in self.tracked_users.items()
            )
            await interaction.response.send_message(
                f"📌 **Currently tracking the following Reddit users:**\n{users}"
            )
        else:
            await interaction.response.send_message(
                "⚠️ No Reddit users are currently being tracked."
            )

    @app_commands.command(
        name="update_track_type",
        description="Update the track type for a tracked Reddit user.",
    )
    @app_commands.autocomplete(username=username_autocomplete)
    @app_commands.choices(
        track_type=[
            app_commands.Choice(name="Posts Only", value="posts"),
            app_commands.Choice(name="Comments Only", value="comments"),
            app_commands.Choice(name="Both", value="both"),
        ]
    )
    async def update_track_type(
        self,
        interaction: discord.Interaction,
        username: str,
        track_type: app_commands.Choice[str],
    ):
        """Update a tracked user's track type."""
        if username not in self.tracked_users:
            await interaction.response.send_message(
                f"⚠️ u/{username} is not being tracked.", ephemeral=True
            )
            return

        # Update the tracking type in memory
        self.tracked_users[username]["track_type"] = track_type.value

        # Update the database
        await self.save_user(
            username=username,
            channel_id=self.tracked_users[username]["channel_id"],
            subreddit=self.tracked_users[username].get("subreddit"),
            last_post_time=self.tracked_users[username].get("last_post_time", 0),
            post_title=self.tracked_users[username].get("post_title", ""),
            last_comment_time=self.tracked_users[username].get("last_comment_time", 0),
            comment=self.tracked_users[username].get("comment", ""),
            track_type=track_type.value,
        )

        await interaction.response.send_message(
            f"✅ Updated u/{username} to track **{track_type.name.lower()}**.",
            ephemeral=True,
        )

    @app_commands.command()
    @app_commands.autocomplete(username=username_autocomplete)
    async def test_reddit(self, interaction: discord.Interaction, username: str):
        """Manually check Reddit for a user's posts, respecting last post time."""
        try:
            print(f"🔍 Manually checking Reddit for {username}...")
            user_data = self.tracked_users.get(username)
            if not user_data:
                await interaction.response.send_message(
                    f"⚠️ u/{username} is not being tracked."
                )
                return

            last_post_time = user_data.get("last_post_time", 0)
            last_post_title = user_data.get("post_title", "")
            last_track_type = user_data.get("track_type", "both")
            redditor = await self.reddit.redditor(username)
            latest_submission = None

            async for submission in redditor.submissions.new(limit=5):
                post_time = int(submission.created_utc)
                post_title = submission.title
                if post_time <= last_post_time:
                    continue

                if not latest_submission or post_time > int(
                    latest_submission.created_utc
                ):
                    latest_submission = submission

            if latest_submission:
                # Found a new post
                new_post_time = int(latest_submission.created_utc)
                new_post_title = latest_submission.title
                new_post_url = latest_submission.url  # Direct URL to the post

                self.tracked_users[username]["last_post_time"] = new_post_time
                self.tracked_users[username]["post_title"] = new_post_title

                await self.save_user(
                    username,
                    user_data["channel_id"],
                    user_data["subreddit"],
                    new_post_time,
                    new_post_title,
                    last_track_type,
                )

                print(f"✅ Found new post: {new_post_title}")
                await interaction.response.send_message(
                    f"🆕 New post by u/{username}: **{new_post_title}**\n{new_post_url}"
                )
            else:
                # No new post, fetch the last post URL
                last_post_url = None
                async for submission in redditor.submissions.new(limit=1):
                    last_post_url = submission.url

                print(f"📝 Latest post by u/{username}: {last_post_title}")
                await interaction.response.send_message(
                    f"📝 Latest post by u/{username}: **{last_post_title}**\n{last_post_url}"
                )

        except Exception as e:
            print(f"❌ Error checking Reddit for {username}: {e}")
            await interaction.response.send_message(
                f"❌ Error fetching posts for u/{username}: {e}"
            )

    @tasks.loop(minutes=3)
    async def check_reddit(self):
        """Background task to check for new Reddit posts and comments based on track_type."""
        for username, user_data in list(self.tracked_users.items()):
            if isinstance(user_data, int):
                user_data = {
                    "channel_id": user_data,
                    "subreddit": None,
                    "track_type": "both",  # Default to 'both' if missing
                    "last_post_time": 0,
                    "post_title": "",
                    "last_comment_time": 0,
                    "comment": "",
                    "track_type": "both",  # Default to 'both' if missing
                }

            channel_id = user_data.get("channel_id")
            subreddit_filter = user_data.get("subreddit")
            track_type = user_data.get("track_type", "both")  # Ensure it exists
            last_post_time = user_data.get("last_post_time", 0)
            last_post_title = user_data.get("post_title", "")
            last_comment_time = user_data.get("last_comment_time", 0)
            last_comment = user_data.get("comment", "")  # Ensure it exists

            try:
                redditor = await self.reddit.redditor(username)
                latest_seen_post_time = last_post_time
                latest_seen_post_title = last_post_title
                latest_seen_comment_time = last_comment_time
                latest_seen_comment = last_comment

                channel = self.bot.get_channel(channel_id)
                user_mention = "<@1047615361886982235>"

                # Check for new posts if track_type is 'both' or 'posts'
                if track_type in ["both", "posts"]:
                    async for submission in redditor.submissions.new(limit=3):
                        if submission.stickied:  # Skip pinned posts
                            continue
                        post_time = int(submission.created_utc)
                        post_title = submission.title

                        if post_time > last_post_time:
                            latest_seen_post_time = max(
                                latest_seen_post_time, post_time
                            )
                            latest_seen_post_title = post_title
                            if channel:
                                post_url = (
                                    f"https://www.reddit.com{submission.permalink}"
                                )
                                await channel.send(
                                    f"🆕 {user_mention}\n**u/{username}** posted in r/{submission.subreddit}:\n"
                                    f"**{post_title}**\n🔗 {post_url}"
                                )

                # Check for new comments if track_type is 'both' or 'comments'
                if track_type in ["both", "comments"]:
                    async for comment in redditor.comments.new(limit=3):
                        comment_time = int(comment.created_utc)
                        comment_body = comment.body[:300]  # Truncate long comments

                        if comment_time > last_comment_time:
                            latest_seen_comment_time = max(
                                latest_seen_comment_time, comment_time
                            )
                            latest_seen_comment = comment_body
                            if channel:
                                comment_url = (
                                    f"https://www.reddit.com{comment.permalink}"
                                )
                                await channel.send(
                                    f"💬 {user_mention}\n**u/{username}** commented in r/{comment.subreddit}:\n"
                                    f"> {comment_body}\n🔗 <{comment_url}>"
                                )

                # Update stored data
                if (
                    latest_seen_post_time > last_post_time
                    or latest_seen_comment_time > last_comment_time
                ):
                    user_data["last_post_time"] = latest_seen_post_time
                    user_data["post_title"] = latest_seen_post_title
                    user_data["last_comment_time"] = latest_seen_comment_time
                    user_data["comment"] = latest_seen_comment
                    self.tracked_users[username] = user_data

                    await self.save_user(
                        username,
                        channel_id,
                        subreddit_filter,
                        latest_seen_post_time,
                        latest_seen_post_title,
                        latest_seen_comment_time,
                        latest_seen_comment,
                        track_type,
                    )

            except Exception as e:
                print(f"❌ Error checking Reddit for u/{username}: {e}")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Reddit(bot))
    print("Reddit is Loaded")
