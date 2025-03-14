import discord
from discord.ext import commands

class MusicControlView(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="Pause", style=discord.ButtonStyle.primary)
    async def pause_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.bot.pause(interaction)
        await interaction.response.send_message(f"Song paused: {self.bot.current_song['title']}", ephemeral=True, delete_after=3)
    
    @discord.ui.button(label="Resume", style=discord.ButtonStyle.success)
    async def resume_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.bot.resume(interaction)
        await interaction.response.send_message(f"Song resumed: {self.bot.current_song['title']}", ephemeral=True, delete_after=3)

    @discord.ui.button(label="Stop", style=discord.ButtonStyle.danger)
    async def stop_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.bot.skip(interaction)
        await interaction.response.send_message(f"Song stopped: {self.bot.current_song['title']}", ephemeral=True, delete_after=3)
