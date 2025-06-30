import asyncio
import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import yt_dlp
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

load_dotenv()
token = os.getenv("discord_token")

# กำหนด Client ID/Secret ของ Spotify (ต้องตั้งใน env หรือใส่ตรงนี้)
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")

if not SPOTIFY_CLIENT_ID or not SPOTIFY_CLIENT_SECRET:
    raise Exception("กรุณาตั้ง SPOTIFY_CLIENT_ID และ SPOTIFY_CLIENT_SECRET ใน .env ด้วย")

sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=SPOTIFY_CLIENT_ID, client_secret=SPOTIFY_CLIENT_SECRET))

bot = commands.Bot(command_prefix='!!', intents=discord.Intents.all())

queues = {}

@bot.event
async def on_ready():
    print("Bot Start!")

@bot.event
async def on_member_join(member):
    channel = bot.get_channel(1388485745181982852)
    text = f"Welcome to Kekhuay Family, {member.mention}!"
    em = discord.Embed(title="Welcome to Kekhuay Family!", description=text, color=0xfab6e8)
    em.set_thumbnail(url=member.avatar.url if member.avatar else None)
    em.timestamp = discord.utils.utcnow()
    em.set_footer(text="Welcome message from Kekhuay Bot")

    if channel:
        await channel.send(text)
        await channel.send(embed=em)

    if member.dm_channel is None:
        await member.create_dm()
    await member.dm_channel.send(text)

@bot.event
async def on_member_remove(member):
    channel = bot.get_channel(1388487145064235079)
    text = f"Goodbye, {member.mention}!"
    em = discord.Embed(title="Bye!", description=text, color=0xadffad)
    em.timestamp = discord.utils.utcnow()
    em.set_footer(text="Farewell message from Kekhuay Bot")

    if channel:
        await channel.send(text)
        await channel.send(embed=em)

def get_queue(guild_id):
    if guild_id not in queues:
        queues[guild_id] = []
    return queues[guild_id]

async def play_next(ctx):
    queue = get_queue(ctx.guild.id)
    if queue:
        url, title = queue.pop(0)
        source = discord.FFmpegPCMAudio(url)

        def after_playing(error):
            if error:
                print(f'Error playing audio: {error}')
            fut = asyncio.run_coroutine_threadsafe(play_next(ctx), bot.loop)
            try:
                fut.result()
            except Exception as e:
                print(f'Error in after_playing: {e}')

        ctx.voice_client.play(source, after=after_playing)

        embed = discord.Embed(
            title="🎶 Now Playing",
            description=f"[{title}](https://www.youtube.com/results?search_query={title.replace(' ', '+')})",
            color=0xfab6e8
        )
        await ctx.send(embed=embed)

    else:
        if ctx.voice_client:
            await ctx.voice_client.disconnect()

@bot.command()
async def play(ctx, *, query: str):
    if ctx.author.voice is None:
        await ctx.send("❌ มึงต้องอยู่ในห้อง voice ก่อน")
        return

    voice_channel = ctx.author.voice.channel

    if ctx.voice_client is None:
        vc = await voice_channel.connect()
    else:
        if ctx.voice_client.channel != voice_channel:
            await ctx.voice_client.move_to(voice_channel)
        vc = ctx.voice_client

    search_queries = []

    if "open.spotify.com" in query:
        try:
            if "track" in query:
                # กรณีลิงก์ Spotify track
                track_id = query.split("/")[-1].split("?")[0]
                track = sp.track(track_id)
                search_queries.append(f"{track['name']} {track['artists'][0]['name']}")
            elif "playlist" in query:
                # กรณีลิงก์ Spotify playlist
                playlist_id = query.split("/")[-1].split("?")[0]
                results = sp.playlist_items(playlist_id)
                for item in results['items']:
                    track = item['track']
                    search_queries.append(f"{track['name']} {track['artists'][0]['name']}")
            else:
                await ctx.send("❌ ตอนนี้รองรับแค่ Spotify track กับ playlist link นะ")
                return
        except Exception as e:
            await ctx.send(f"❌ อ่าน Spotify ไม่ได้: {e}")
            return
    else:
        # ถ้าไม่ใช่ลิงก์ Spotify ก็ search ตามปกติ
        search_queries.append(query)

    ydl_opts = {
        'format': 'bestaudio/best',
        'quiet': True,
        'default_search': 'ytsearch',
        'noplaylist': True,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
    }

    try:
        queue = get_queue(ctx.guild.id)
        for q in search_queries:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(q, download=False)
                if 'entries' in info:
                    info = info['entries'][0]

                audio_url = info['url']
                title = info.get('title', 'Unknown Title')

            queue.append((audio_url, title))
            await ctx.send(f"✅ Added to Queue: [{title}](https://www.youtube.com/watch?v={info['id']})")

        if not vc.is_playing():
            await play_next(ctx)

    except Exception as e:
        await ctx.send(f"❌ เกิดข้อผิดพลาด: {e}")


@bot.command()
async def stop(ctx):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.send("🛑 หยุดเล่นเพลงแล้ว")

@bot.command()
async def queue(ctx):
    queue = get_queue(ctx.guild.id)
    if not queue:
        await ctx.send("📭 คิวว่างเปล่า ไม่มีเพลงเลย")
    else:
        embed = discord.Embed(title="🎶 คิวเพลงตอนนี้", color=0xfab6e8)
        desc = ""
        for i, (_, title) in enumerate(queue, 1):
            desc += f"{i}. {title}\n"
        embed.description = desc
        await ctx.send(embed=embed)

bot.run(token)
