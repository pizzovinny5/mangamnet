
import discord
from discord import app_commands
import requests

# 1. Configuration
BOT_TOKEN = "YOUR_DISCORD_BOT_TOKEN"
WEBHOOK_URL = "YOUR_DISCORD_WEBHOOK_URL"
MAX_WARNINGS = 8

# 2. Setup Bot Client
class WarningBot(discord.Client):
    def __init__(self):
        super().__init__(intents=discord.Intents.all())
        self.tree = app_commands.CommandTree(self)

    async def on_ready(self):
        # Sync slash commands with Discord globally
        await self.tree.sync()
        print(f"Logged in as {self.user} and slash commands synced!")

client = WarningBot()

# Simple dictionary to store warnings temporarily in memory: {user_id: count}
# Note: Restarts will reset this. For permanent storage, look into a database.
warning_database = {}

# 3. Create the /warn Slash Command
@client.tree.command(name="warn", description="Warn a user. Automatically bans them at 8 warnings.")
@app_commands.describe(user="The member you want to warn", reason="Reason for the warning")
@app_commands.checks.has_permissions(ban_members=True) # Restrict command to mods/admins
async def warn(interaction: discord.Interaction, user: discord.Member, reason: str = "No reason provided"):
    
    # Don't let the bot warn itself or the server owner
    if user.bot or user == interaction.guild.owner:
        await interaction.response.send_message("You cannot warn this user.", ephemeral=True)
        return

    # Update warning count
    user_id = user.id
    current_warnings = warning_database.get(user_id, 0) + 1
    warning_database[user_id] = current_warnings

    # Base message sent back to the moderator who typed the command
    await interaction.response.send_message(f"Successfully processed warning for {user.mention}.", ephemeral=True)

    # Check if they hit the maximum limit
    if current_warnings >= MAX_WARNINGS:
        # Send Final Ban Webhook Alert
        payload = {
            "embeds": [{
                "title": "🚨 User Banned (Max Warnings Reached)",
                "description": f"**User:** {user.mention} ({user.name})\n**Reason:** Accumulated {MAX_WARNINGS} warnings.\n**Last Infraction:** {reason}",
                "color": 16515072 # Crimson Red
            }]
        }
        requests.post(WEBHOOK_URL, json=payload)
        
        # Execute the Ban
        await user.ban(reason=f"Reached maximum limit of {MAX_WARNINGS} warnings. Last reason: {reason}")
        
    else:
        # Send Standard Warning Webhook Alert
        payload = {
            "embeds": [{
                "title": "⚠️ Warning Issued",
                "description": f"**User:** {user.mention} ({user.name})\n**Moderator:** {interaction.user.mention}\n**Reason:** {reason}",
                "fields": [
                    {"name": "Warning Progress", "value": f"`{current_warnings} / {MAX_WARNINGS}`", "inline": True}
                ],
                "color": 16763904 # Amber Yellow
            }]
        }
        requests.post(WEBHOOK_URL, json=payload)

# Error handling if a non-moderator tries to use the command
@warn.error
async def warn_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)

# Run the bot
client.run(BOT_TOKEN)
