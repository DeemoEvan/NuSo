import discord
import yt_dlp
from discord import app_commands

YDL_OPTIONS = {'format': 'bestaudio/best', 'noplaylist': True, 'quiet': True, 'default_search': 'ytsearch'}
FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}


class ProMusicView(discord.ui.View):
    def __init__(self, voice_client, filename):
        super().__init__(timeout=None)
        self.vc = voice_client
        self.filename = filename

    @discord.ui.button(label="上一首", style=discord.ButtonStyle.secondary, row=0)
    async def prev_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("目前僅播放單一本地檔案。", ephemeral=True)

    @discord.ui.button(label="暫停/恢復", style=discord.ButtonStyle.primary, row=0)
    async def play_pause(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.vc.is_playing():
            self.vc.pause()
            await interaction.response.send_message("⏸️ 已暫停播放", ephemeral=True)
        elif self.vc.is_paused():
            self.vc.resume()
            await interaction.response.send_message("▶️ 已恢復播放", ephemeral=True)
        else:
            await interaction.response.send_message("❌ 目前沒在播放", ephemeral=True)

    @discord.ui.button(label="下一首", style=discord.ButtonStyle.success, row=0)
    async def next_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("後面沒有歌囉！", ephemeral=True)

    @discord.ui.button(label="循環：關閉", style=discord.ButtonStyle.secondary, row=0)
    async def loop_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("單曲循環功能開發中。", ephemeral=True)

    @discord.ui.button(label="查看列表", style=discord.ButtonStyle.secondary, row=1)
    async def list_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(f"📋 目前播放清單：\n1. {self.filename}", ephemeral=True)


class YTMusicView(discord.ui.View):
    def __init__(self, voice_client, info, queue, cog):
        super().__init__(timeout=None)
        self.vc = voice_client
        self.info = info
        self.queue = queue
        self.cog = cog

    @discord.ui.button(label="暫停/恢復", style=discord.ButtonStyle.primary, row=0)
    async def play_pause(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.vc.is_playing():
            self.vc.pause()
            await interaction.response.send_message("⏸️ 已暫停", ephemeral=True)
        elif self.vc.is_paused():
            self.vc.resume()
            await interaction.response.send_message("▶️ 已恢復", ephemeral=True)

    @discord.ui.button(label="下一首", style=discord.ButtonStyle.success, row=0)
    async def next_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.vc:
            self.vc.stop()
            await interaction.response.send_message("⏭️ 跳過當前歌曲", ephemeral=True)

    @discord.ui.button(label="查看列表", style=discord.ButtonStyle.secondary, row=1)
    async def list_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.queue:
            return await interaction.response.send_message("📋 目前待播放清單是空的。", ephemeral=True)

        queue_text = "\n".join([f"{i+1}. {song['title']}" for i, song in enumerate(self.queue[:10])])
        await interaction.response.send_message(f"📋 **待播放清單 (前10首)：**\n{queue_text}", ephemeral=True)


class MusicCommandsMixin:
    def create_music_embed(self, info, interaction, queue_len):
        embed = discord.Embed(title="🎵 正在播放", color=0x2ecc71)
        next_song_text = "無" if queue_len == 0 else f"清單中還有 {queue_len} 首歌"
        embed.description = (
            f"**[{info['title']}]({info['webpage_url']})**\n\n"
            f"**作者** **時長**\n"
            f"{info.get('uploader', '未知')}      {info.get('duration_string', '未知')}\n\n"
            f"**進度**\n"
            f"0:00 ▬▬▬▬▬▬▬▬▬▬▬🔘 {info.get('duration_string', '未知')}\n\n"
            f"**循環**：關閉\n"
            f"**下一首**：{next_song_text}"
        )
        if info.get('thumbnail'):
            embed.set_thumbnail(url=info['thumbnail'])
        embed.set_footer(text=f"由 {interaction.user.display_name} 點播", icon_url=interaction.user.display_avatar.url)
        return embed

    @app_commands.command(name="play", description="播放 YouTube 音樂")
    @app_commands.describe(search="輸入歌名或網址")
    async def play(self, interaction: discord.Interaction, search: str):
        if not interaction.user.voice:
            return await interaction.response.send_message("❌ 你必須先進入語音頻道！", ephemeral=True)

        await interaction.response.defer()
        guild_id = interaction.guild.id

        with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
            try:
                info = ydl.extract_info(search, download=False)
                if 'entries' in info:
                    info = info['entries'][0]
            except Exception as e:
                return await interaction.followup.send(f"❌ 搜尋失敗: {e}")

        if guild_id not in self.queues:
            self.queues[guild_id] = []

        vc = interaction.guild.voice_client
        if not vc:
            vc = await interaction.user.voice.channel.connect()

        if vc.is_playing() or vc.is_paused():
            self.queues[guild_id].append(info)
            await interaction.followup.send(f"✅ 已加入待播放清單：**{info['title']}** (目前排第 {len(self.queues[guild_id])} 位)")
        else:
            self.queues[guild_id].append(info)
            await self.play_next(interaction, guild_id)
            await interaction.followup.send("🎶 開始播放音樂！", ephemeral=True)

    async def play_next(self, interaction, guild_id):
        if guild_id in self.queues and len(self.queues[guild_id]) > 0:
            info = self.queues[guild_id].pop(0)
            vc = interaction.guild.voice_client
            if not vc:
                return

            source = await discord.FFmpegOpusAudio.from_probe(info['url'], **FFMPEG_OPTIONS)
            vc.play(source, after=lambda e: self.bot.loop.create_task(self.play_next(interaction, guild_id)))

            embed = self.create_music_embed(info, interaction, len(self.queues[guild_id]))
            view = YTMusicView(vc, info, self.queues[guild_id], self)
            await interaction.channel.send(embed=embed, view=view)

    @app_commands.command(name="leave", description="叫機器人離開語音頻道")
    async def leave(self, interaction: discord.Interaction):
        if interaction.guild.voice_client:
            await interaction.guild.voice_client.disconnect()
            await interaction.response.send_message("👋 下次見！")
        else:
            await interaction.response.send_message("❌ 我不在語音頻道裡喔。", ephemeral=True)
