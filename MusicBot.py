import schedule
import time
import discord
from discord.ext import commands
import os
import asyncio
import yt_dlp
from pytube import Playlist
from dotenv import load_dotenv
import urllib.parse, urllib.request, re
from MusicControlView import MusicControlView  

class MusicBot:
    def __init__(self):
        load_dotenv()
        self.TOKEN = os.getenv('DISCORD_TOKEN')
        self.clear_time = "23:59"
        self.CHANNEL_NAME = 'bot'
        self.intents = discord.Intents.default()
        self.intents.message_content = True
        self.client = commands.Bot(command_prefix="!", intents=self.intents)
        self.client.remove_command('help')
        self.last_command_time = 0
        self.queues = {}
        self.voice_clients = {}
        self.current_song = None
        self.unavailable = '24/7 is currently unavailable'
        self.base_url = 'https://www.youtube.com/'
        self.results_url = self.base_url + 'results?'
        self.watch_url = self.base_url + 'watch?v='
        self.yt_dl_options = {"format": "bestaudio/best"}
        self.ytdl = yt_dlp.YoutubeDL(self.yt_dl_options)
        self.FFMPEG_PATH = os.getenv('FFMPEG')
        self.ffmpeg_options = {
            'executable': self.FFMPEG_PATH, 
            'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
            'options': '-vn -filter:a "volume=0.5"'
        }
        self.setup_events()
        self.setup_commands()

    async def play_playlist(self, ctx, link):
        loop = asyncio.get_event_loop()
        playlist_urls = await self.get_playlists(link)
        #data_list = [await loop.run_in_executor(None, lambda url=url: ytdl.extract_info(url,download=False)) for url in playlist_urls]
        for url in playlist_urls:
            await self.play_song(ctx, url)
            
    def run(self):
        self.client.run(self.TOKEN)

    def setup_events(self):
        @self.client.event
        async def on_message(message):
            if message.content.startswith(self.client.command_prefix):
                await self.client.process_commands(message)
                self.last_command_time = time.time()

        @self.client.event
        async def on_ready():
            print(f'{self.client.user} is online')
            await self.client.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name=self.unavailable))
            self.client.loop.create_task(self.background_task())

        @self.client.event
        async def on_voice_state_update(member, before, after):
            bot_voice_channel = member.guild.me.voice.channel if member.guild.me.voice else None
            if bot_voice_channel and len(bot_voice_channel.members) == 1 and member != self.client.user:
                if member.guild.id in self.voice_clients:
                    if time.time() - self.last_command_time >= 180:
                        voice_client = self.voice_clients[member.guild.id]
                        await bot_voice_channel.send("idle for too long. Disconnecting!")
                        await voice_client.disconnect()
                        del self.voice_clients[member.guild.id]

    def setup_commands(self):
        @self.client.command(name="join")
        async def join(ctx):
            if not (ctx.author.voice and ctx.author.voice.channel):
                await ctx.send("You must be in a voice channel to use this command.")
                return

            voice_client = ctx.guild.voice_client
            if voice_client:
                if voice_client.channel != ctx.author.voice.channel:
                    await voice_client.move_to(ctx.author.voice.channel)
                    await ctx.send(f"Moved to {ctx.author.voice.channel.name}")
                else:
                    await ctx.send("I'm already connected to this voice channel.")
            else:
                self.voice_clients[ctx.guild.id] = await ctx.author.voice.channel.connect()
                await ctx.send(f"Connected to {ctx.author.voice.channel.name}")

        @self.client.command(name='blank')
        @commands.has_permissions(manage_messages=True)
        async def clear(ctx):
            if ctx.channel.name == self.CHANNEL_NAME:
                schedule.clear('clean')
                current_time = time.strftime("%H:%M", time.localtime())
                if current_time >= self.clear_time:
                    await self.delete(ctx.channel)
                else:
                    schedule.every().day.at(self.clear_time).do(lambda: asyncio.create_task(self.delete(ctx.channel))).tag('clean')
                    await ctx.send(f"All messages will be cleared at {self.clear_time}.")

        @self.client.command(name="clean")
        @commands.has_permissions(manage_messages=True)
        async def clean(ctx):
            if ctx.channel.name == self.CHANNEL_NAME:
                await ctx.send("Forced deletion is activated.")
                await self.delete(ctx.channel)

        @self.client.command(name="playlist")
        async def playlist(ctx, *, link):
            if ctx.voice_client is None:
                await ctx.invoke(self.client.get_command('join'))
            try:
                await self.play_playlist(ctx, link=link)
            except Exception as e:
                print(e)

        @self.client.command(name="play", aliases=["p", "queue"])
        async def play(ctx, *, link):
            if ctx.voice_client is None:
                await ctx.invoke(self.client.get_command('join'))
            try:
                if self.base_url in link or "https://music.youtube.com/" in link or "https://youtu.be/" in link:
                    await self.play_song(ctx, link)
                else:
                    query_string = urllib.parse.urlencode({
                        'search_query': link
                    })
                    info = urllib.request.urlopen(self.results_url + query_string).read().decode()
                    results = re.findall(r'/watch\?v=(.{11})', info)
                    search_results = re.findall(r'\"title\":\{\"runs\":\[\{\"text\":\"(.+?)\"', info)
                    global message
                    message = "**Select a result (1-10):**\n"
                    for i, title in enumerate(search_results[0:10]):
                        message += f"{i}. {title}\n"
                    await ctx.send(message, delete_after=30)
                    def check(m):
                        return m.author == ctx.author and m.channel == ctx.channel and m.content.isdigit()
                    try:
                        global response
                        response = await self.client.wait_for('message', check=check, timeout=30)
                        index = int(response.content)*2-1
                        url = self.watch_url+results[index]
                        await self.play_song(ctx, url)
                        await response.delete()
                    except asyncio.TimeoutError:
                        await ctx.send("Timed out. Please try again.")
                        return
            except Exception as e:
                print(e)

        @self.client.command(name="skipall")
        async def skipall(ctx):
            await ctx.invoke(self.client.get_command('clear'))
            await ctx.invoke(self.client.get_command('skip'))

        @self.client.command(name="skip", aliases=["stop"])
        async def skip(ctx):
            try:
                self.voice_clients[ctx.guild.id].stop()
                await asyncio.sleep(2)
                await self.play_next(ctx)
            except Exception as e:
                await self.client.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name=self.unavailable))

        @self.client.command(name="clear")
        async def clear_queue(ctx):
            if ctx.guild.id in self.queues:
                self.queues[ctx.guild.id].clear()
                await ctx.send("Queue cleared!")
            else:
                await ctx.send("There is no queue to clear")

        @self.client.command(name="pause")
        async def pause(ctx):
            try:
                self.voice_clients[ctx.guild.id].pause()
                await self.client.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name=self.unavailable))
            except Exception as e:
                print(e)

        @self.client.command(name="resume", aliases=["continue"])
        async def resume(ctx):
            try:
                self.voice_clients[ctx.guild.id].resume()
                await self.client.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name=self.current_song['title']))
            except Exception as e:
                print(e)

        @self.client.command(name="list")
        async def queue(ctx):
            if not self.queues or len(self.queues) == 0:
                await ctx.send("Queue is empty!")
            else:
                current_page = 1
                SONGS_PER_PAGE = 40
                TOTAL_PAGES = (len(self.queues[ctx.guild.id]) + SONGS_PER_PAGE - 1) // SONGS_PER_PAGE

                while True:
                    start = (current_page - 1) * SONGS_PER_PAGE
                    end = start + SONGS_PER_PAGE
                    songs = self.queues[ctx.guild.id][start:end]
                    msg = f"** Current Queue (Page {current_page}/{TOTAL_PAGES}) **\n"
                    for i, song in enumerate(songs, start=1):
                        msg += f"{start+i}. {song['title']} \n"

                    view = discord.ui.View()
                    if current_page > 1:
                        view.add_item(discord.ui.Button(label="Previous", style=discord.ButtonStyle.blurple, id=f"queue_previous_{current_page-1}"))
                    if current_page < TOTAL_PAGES:
                        view.add_item(discord.ui.Button(label="Next", style=discord.ButtonStyle.blurple, id=f"queue_next_{current_page+1}"))
                    message = await ctx.send(msg, view=view)

                    def check(interaction):
                        return interaction.user == ctx.author and interaction.data["id"].startswith("queue_")
                    try:
                        interaction = await self.client.wait_for("interaction", check=check, timeout=60)
                    except asyncio.TimeoutError:
                        await message.edit(view=None)
                        return

                    if interaction.data["id"].startswith("queue_previous_"):
                        current_page = int(interaction.data["id"].split("_")[-1])
                        interaction.response.edit_message(content=msg, view=view)
                    else:
                        current_page = int(interaction.data["id"].split("_")[-1])
                        await interaction.response.edit_message(content=msg, view=view)

        @self.client.command(name="move")
        @commands.has_permissions(move_members=True)
        async def move(ctx, channel: discord.VoiceChannel, *members: discord.Member):
            await asyncio.gather(*(self.move_member(ctx, member, channel) for member in members))

        async def move_member(self, ctx, member: discord.Member, channel: discord.VoiceChannel):
            if member.voice:
                if member.voice.channel == channel:
                    await ctx.send(f"{member.mention} is already in {channel.name}.")
                else:
                    await member.move_to(channel)
                    await ctx.send(f"Moved {member.mention} to {channel.name}.")
            else:
                await ctx.send(f"{member.mention} is not in a voice channel.")

        @self.client.command(name="help")
        async def help(ctx):
            msg = "Welcome to the Python Help Center!\n\n"
            msg += "Here are some available commands:\n - `!join`: Join the bot.\n- `!play <song_name/url>`: Play a song.\n- `!skip/!stop`: Skip the current song.\n- `!list`: List the current queue.\n- `!clear`: Clear the queue.\n- `!pause`: Pause the current song.\n- `!resume`: Resume the current song.\n- `!quit`: Leave from the voice channel.\n\n"
            await ctx.send(msg)

        @self.client.command(name="quit", aliases=["disconnect", "q", "leave", "l"])
        async def disconnect(ctx):
            await ctx.voice_client.disconnect()
            await self.client.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name=self.unavailable))
            await ctx.invoke(self.client.get_command('blank'))

    async def delete(self, channel):
        total = 0
        while True:
            deleted = await channel.purge(limit=100)
            total += len(deleted)
            if len(deleted) < 100:
                break
            await asyncio.sleep(2)
        await channel.send('All messages cleared in this channel!', delete_after=5)

    async def background_task(self):
        while True:
            schedule.run_pending()
            current_time = time.strftime("%H:%M", time.localtime())
            if current_time == self.clear_time:
                for job in schedule.jobs:
                    if 'clean' in job.tags:
                        await job.run()
            await asyncio.sleep(60)

    async def get_playlists(self, url):
        playlist = Playlist(url)
        return [video.watch_url for video in playlist.videos]

    async def play_next(self, ctx):
        voice_client = self.voice_clients[ctx.guild.id]
        if ctx.guild.id not in self.queues or len(self.queues[ctx.guild.id]) == 0:
            await self.client.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name=self.unavailable))
            voice_client.stop()
            return

        next_song = self.queues[ctx.guild.id][0]
        await self.play_handling(ctx, next_song)
        self.queues[ctx.guild.id] = self.queues[ctx.guild.id][1:]

    async def play_handling(self, ctx, song):
        self.current_song = song
        player = discord.FFmpegOpusAudio(song['url'], **self.ffmpeg_options)
        self.voice_clients[ctx.guild.id].play(player, after=lambda e: asyncio.run_coroutine_threadsafe(self.play_next(ctx), self.client.loop))
        await self.client.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name=song['title']))

        # Create and send the view with buttons
        view = MusicControlView(self)
        await ctx.send(f"Now playing: {song['title']}", view=view)

    async def play_song(self, ctx, link):
        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: self.ytdl.extract_info(link, download=False))
        global song
        song = {
            'url': data['url'],
            'title': data['title']
        }
        if ctx.voice_client.is_playing():
            if ctx.guild.id in self.queues:
                self.queues[ctx.guild.id].append(song)
            else:
                self.queues.setdefault(ctx.guild.id, []).append(song)
            await ctx.send(f"Added {song['title']} to the queue.", delete_after=10)
        else:
            await self.play_handling(ctx, song)
    
    async def pause(self, interaction):
        self.voice_clients[interaction.guild_id].pause()

    async def resume(self, interaction):
        self.voice_clients[interaction.guild_id].resume()
    
    async def skip(self, interaction):
        self.voice_clients[interaction.guild_id].stop()
        await self.play_next(interaction)