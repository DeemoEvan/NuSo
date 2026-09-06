import aiohttp
import discord
from discord.ext import commands
from discord import app_commands
import random
import asyncio
import os
import requests
import json
import yt_dlp
from datetime import datetime, timedelta
import threading
import edge_tts
#from nuro_tts import NeuroSmartGenerator
import pygame
import pygame._sdl2.audio as sdl2_audio
import pyaudio
import wave
import time
import numpy as np
from collections import deque

NEURO_MODEL_PATH = r"Neuro.pth"
NEURO_INDEX_PATH = r"Neuro.index"
INFER_CLI_PATH = r"mod\infer_cli.py"
THRESHOLD = 700       # 音量門檻
SILENCE_LIMIT = 1.5   # 自動收工時間
VB_CABLE_IN = "CABLE Input"
RECORD_OUT = "HitPaw"

YDL_OPTIONS = {'format': 'bestaudio/best', 'noplaylist': True, 'quiet': True, 'default_search': 'ytsearch'}
FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

# 搶銀行劇情
ROB_PLOTS = {
    "prep": [
      "🚗 {user} 負責接應，將改裝過的黑色麵包車停在巷口...",
      "🚁 {user} 將直升機飛到銀行上方，將窗戶切割進入...",
      "🔧 {user} 換上電力公司制服，藉由維修名義剪斷了銀行的備用供電線。",
      "💻 {user} 窩在公寓裡，透過暴力破解程序癱瘓了警局的調度系統 5 分鐘。",
      "🎭 {user} 提前在銀行門口布置了『修路中』看板，引導巡邏警車繞道。"
    ],
    "entry": [
      "💥 {user} 扔出一枚閃光彈，趁著混亂帶頭衝進大廳！",
      "📢 {user} 對著天花板開了一槍，大喊：『通通趴下！』",
      "🔕 {user} 使用吸盤與雷射刀，悄無聲息地在二樓落地窗切出一個圓洞。",
      "🆔 {user} 刷開了偽造的高階主管門禁卡，冷靜地走進 VIP 走廊。",
      "🧱 {user} 猛踩油門，開著重型卡車直接撞穿了銀行的側邊外牆！"
    ],
    "vault_drill": [
      "⚙️ {user} 架設起工業級電鑽，鑽頭與保險庫門磨出激烈火花...",
      "📟 {user} 接上破解黑盒，手指在螢幕上飛速敲擊指令...",
      "❄️ {user} 將液態氮灌入鎖芯，隨後用重錘猛力一擊，金屬瞬間粉碎。",
      "🔥 {user} 啟動了鋁熱劑切斷器，高溫融毀了厚達 30 公分的鋼板。",
      "👂 {user} 屏息凝神，用聽診器捕捉轉盤內部彈簧落下的極細微聲響。"
    ],
    "vault_open": [
      "🔓 隨著一聲清脆的響聲，{user} 成功推開了厚重的保險庫門！",
      "🌟 沉重的齒輪緩緩轉動，{user} 被門後堆積如山的金磚晃得睜不開眼。",
      "💨 氣壓平衡發出噴氣聲，{user} 拉開了這扇價值連城的最後防線。",
      "🚨 門開了，但內部的紅外線感應器開始閃爍，{user} 知道時間不多了！",
      "🛠️ 經過最後一次敲擊，保險庫手把終於鬆動，{user} 露出了一抹壞笑。"
    ],
    "loot": [
      "💰 {user} 瘋狂地將一疊疊美鈔塞進運動提袋中...",
      "💎 {user} 撬開了私人保險箱，發現了幾顆碩大的鑽石！",
      "👑 {user} 發現了收藏架上的純金古董皇冠，毫不猶豫地將它收入袋中。",
      "🧧 {user} 打開保險箱，發現裡面裝滿了不記名債券與秘密合約。",
      "🧱 {user} 快速搬運著沉重的金磚，每一塊都象徵著後半輩子的自由。"
    ],
    "police": [
      "🚨 警笛聲響徹街道，{user} 透過無線電大喊：『警察來了，準備撤離！』",
      "🚓 第一輛巡邏車甩尾停在門口，{user} 看見警員已經拔槍尋求掩護。",
      "🚁 遙遠的天空傳來直升機螺旋槳聲，{user} 知道特種部隊即將封鎖現場。",
      "👮 擴音器傳來最後通牒：『裡面的武裝分子聽著，你們已經被包圍了！』",
      "⚡ 銀行的靜默報警器被觸發，{user} 發現外面早已佈滿了藍紅閃爍的燈光。"
    ],
    "skirmish": [
      "🔫 {user} 拿起步槍對著防暴盾牌猛烈開火，壓制住了警方的包圍...",
      "🔥 {user} 扔出一枚煙霧彈，掩護隊友衝向出口！",
      "💥 {user} 啟動了預埋在街口汽車下的炸彈，巨大的爆炸聲讓警方陣腳大亂。",
      "🏹 {user} 爬上屋頂天台，用狙擊步槍點射那些試圖包抄的特警。",
      "🛡️ {user} 躲在圓柱後與警方展開激烈對射，子彈擊碎了銀行華麗的大理石柱。"
    ],
    "escape": [
      "🏎️ 最終猛踩油門，設法甩開了後方的巡邏車...",
      "🏁 最終穿過狹窄的後巷，前進至預定的安全屋...",
      "🌊 最終帶領隊友跳上運河旁的快艇，在海警的追逐中瘋狂加速...",
      "🚇 最終丟下受損的車輛，帶著大袋現金試圖混入了混亂的地鐵人群中...",
      "✈️ 最終抵達了私人機場，在警方趕到前設法飛往了沒有引渡條約的島嶼..."
    ]
}

# 讀取授權名單的工具函式
from .features.views import (
    BLACKJACK_AVATAR_URL,
    BlackjackView,
    DragonGateView,
    RedPacketView,
    FishingView,
    FishingHubView,
    FishConfirmView,
    FishActiveView,
    FishCancelConfirmView,
    SecretModal,
    SecretView,
    RobBankView,
    load_allowed_users,
    save_allowed_users
)

class TransferView(discord.ui.View):
    def __init__(self, bot, sender, receiver, amount, fee, total, bank_cog):
        super().__init__(timeout=30)
        self.bot = bot
        self.sender = sender
        self.receiver = receiver
        self.amount = amount
        self.fee = fee
        self.total = total
        self.bank_cog = bank_cog

    @discord.ui.button(label="確認轉帳", style=discord.ButtonStyle.green)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.sender.id:
            return await interaction.response.send_message("❌ 這不是你的轉帳交易！", ephemeral=True)

        # 再次檢查餘額
        s_data = self.bank_cog.add_stats(interaction.guild.id, self.sender.id)
        r_data = self.bank_cog.add_stats(interaction.guild.id, self.receiver.id)

        if s_data["coin"] < self.total:
            return await interaction.response.send_message("❌ 餘額不足，轉帳取消。", ephemeral=True)

        # 執行扣款與撥款
        s_data["coin"] -= self.total
        r_data["coin"] += self.amount
        self.bank_cog.save_data()

        # 製作成功介面 (對應圖片 3)
        embed = discord.Embed(title="💸 轉錢成功", color=0x2ecc71) # 綠色邊框
        embed.set_author(name=f"{self.sender.display_name} ➔ {self.receiver.display_name}", 
                         icon_url=self.sender.avatar.url if self.sender.avatar else None)

        embed.description = f"{self.sender.mention} 成功轉錢給 {self.receiver.mention}"

        embed.add_field(name="轉帳金額", value=f"`{self.amount:,}` 💰", inline=True)
        embed.add_field(name="手續費 (3%)", value=f"`{self.fee:,}` 💰", inline=True)
        embed.add_field(name="發送方支付", value=f"`{self.total:,}` 💰", inline=True)

        embed.add_field(name=f"{self.sender.display_name} 餘額", value=f"`{s_data['coin']:,}` 💰", inline=True)
        embed.add_field(name=f"{self.receiver.display_name} 餘額", value=f"`{r_data['coin']:,}` 💰", inline=True)

        embed.set_footer(text="轉錢操作已完成 (已扣除手續費並記錄)")
        embed.timestamp = datetime.now()

        # 加上錢包圖示 (如果有網址的話可以放 thumbnail)
        # embed.set_thumbnail(url="錢包圖片網址")

        await interaction.response.edit_message(content=None, embed=embed, view=None)

    @discord.ui.button(label="取消", style=discord.ButtonStyle.red)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="❌ 交易已取消。", embed=None, view=None)


class ABGuessModal(discord.ui.Modal, title="🎯 猜答案"):
    def __init__(self, game_view: "ABGameView"):
        super().__init__()
        self.game_view = game_view
        self.guess_input = discord.ui.TextInput(
            label=f"請輸入 {game_view.length} 位數字",
            placeholder="例如：2486",
            required=True,
            min_length=game_view.length,
            max_length=game_view.length,
        )
        self.add_item(self.guess_input)

    async def on_submit(self, interaction: discord.Interaction):
        if not self.game_view.can_submit_guess(interaction.user):
            return await interaction.response.send_message("❌ 這不是你的幾A幾B遊戲。", ephemeral=True)

        guess = str(self.guess_input.value or "").strip()
        error = self.game_view.validate_guess(guess)
        if error:
            return await interaction.response.send_message(error, ephemeral=True)

        self.game_view.apply_guess(guess)
        self.game_view.sync_buttons()
        await interaction.response.edit_message(embed=self.game_view.build_embed(), view=self.game_view)


class ABGameView(discord.ui.View):
    def __init__(self, cog_instance, owner: discord.abc.User, length: int, answer: str = None, challenge_mode: bool = False, target_user: discord.abc.User = None, guild_id: int = None):
        super().__init__(timeout=1800)
        self.cog = cog_instance
        self.owner = owner
        self.owner_id = owner.id
        self.creator = owner
        self.creator_id = owner.id
        self.challenge_mode = challenge_mode
        self.target_user = target_user
        self.target_user_id = target_user.id if target_user else None
        self.player = target_user if challenge_mode and target_user else (None if challenge_mode else owner)
        self.player_id = self.player.id if self.player else (None if challenge_mode else owner.id)
        self.guild_id = guild_id
        self.length = int(length)
        self.answer = answer if answer is not None else self.cog._generate_ab_answer(self.length)
        self.tries = 0
        self.history = []
        self.is_solved = False
        self.settlement_applied = False
        self.settlement_delta = 0
        self.settlement_text = None
        self.settlement_balance = None
        self.sync_buttons()

    def sync_buttons(self):
        if self.is_solved:
            if self.challenge_mode:
                self.action_btn.label = "✅ 已完成"
                self.action_btn.style = discord.ButtonStyle.secondary
                self.action_btn.disabled = True
            else:
                self.action_btn.label = "🔁 再來一局"
                self.action_btn.style = discord.ButtonStyle.success
                self.action_btn.disabled = False
        else:
            self.action_btn.label = "🎯 猜答案"
            self.action_btn.style = discord.ButtonStyle.primary
            self.action_btn.disabled = False

    def can_submit_guess(self, user: discord.abc.User):
        return (self.player_id is not None) and (user.id == self.player_id)

    def ensure_player(self, user: discord.abc.User):
        if self.challenge_mode:
            if user.id == self.creator_id:
                return False, "❌ 你是出題者，不能猜這題。"
            if self.target_user_id and user.id != self.target_user_id:
                return False, f"❌ 這題指定給 {self.target_user.mention} 挑戰。"
            if self.player_id is None:
                self.player_id = user.id
                self.player = user
                return True, None
            if user.id != self.player_id:
                return False, "❌ 這局已由其他玩家進行中。"
            return True, None

        if user.id != self.player_id:
            return False, "❌ 這不是你的幾A幾B遊戲。"
        return True, None

    def validate_guess(self, guess: str):
        return self.cog._validate_ab_input(guess, self.length)

    def apply_guess(self, guess: str):
        self.tries += 1
        a_count, b_count = self.cog._calc_ab(self.answer, guess)
        self.history.append((guess, a_count, b_count))
        if a_count == self.length:
            self.is_solved = True
            self._try_settle_reward()

    def _get_settlement_rule(self):
        rules = {
            3: {"limit": 8, "win": 15000000, "loss": -10000000},
            4: {"limit": 8, "win": 15000000, "loss": -10000000},
            5: {"limit": 10, "win": 30000000, "loss": -20000000},
            6: {"limit": 12, "win": 50000000, "loss": -30000000},
        }
        return rules.get(self.length)

    def _try_settle_reward(self):
        if self.challenge_mode or self.settlement_applied:
            return

        rule = self._get_settlement_rule()
        if not rule:
            self.settlement_applied = True
            self.settlement_text = "ℹ️ 此長度沒有獎懲規則。"
            return

        if self.guild_id is None or self.player_id is None:
            self.settlement_applied = True
            self.settlement_text = "⚠️ 無法結算（僅限伺服器內可結算）。"
            return

        delta = rule["win"] if self.tries <= rule["limit"] else rule["loss"]

        bank = self.cog.bank
        if not bank or not hasattr(bank, 'add_stats'):
            bank = self.cog._find_bank_cog()
            self.cog.bank = bank

        if not bank:
            self.settlement_applied = True
            self.settlement_delta = delta
            self.settlement_text = "⚠️ 銀行系統未就緒，暫時無法結算。"
            return

        try:
            user_data = bank.add_stats(self.guild_id, self.player_id, coin=delta)
            bank.save_data()
            self.settlement_balance = user_data.get("coin", 0)
            self.settlement_delta = delta
            self.settlement_applied = True
            if delta >= 0:
                self.settlement_text = f"🎁 獎勵 **{delta:,}**（{rule['limit']} 次內答對）"
            else:
                self.settlement_text = f"💸 懲罰 **{abs(delta):,}**（超過 {rule['limit']} 次）"
        except Exception as e:
            print(f"[AB結算] 結算失敗: {e}")
            self.settlement_applied = True
            self.settlement_delta = delta
            self.settlement_text = "⚠️ 結算時發生錯誤。"

    def reset_game(self):
        self.answer = self.cog._generate_ab_answer(self.length)
        self.tries = 0
        self.history = []
        self.is_solved = False
        self.sync_buttons()

    def build_embed(self):
        embed = discord.Embed(title="🐮 幾A幾B", color=0x5865F2)

        if self.is_solved:
            embed.description = (
                f"✅ 完成！答案是 **{self.answer}**\n"
                f"次數: **{self.tries}**"
            )
            if not self.challenge_mode and self.settlement_text:
                embed.description += f"\n{self.settlement_text}"
                if self.settlement_balance is not None:
                    embed.description += f"\n目前餘額: **{self.settlement_balance:,}**"
        else:
            if self.challenge_mode:
                challenger = self.player.mention if self.player else "（等待挑戰者）"
                if self.target_user:
                    challenger = f"{self.target_user.mention}（指定）"
                embed.description = (
                    f"出題者: {self.creator.mention}\n"
                    f"挑戰者: {challenger}\n"
                    f"規則: 長度 **{self.length}**、不重複數字、不可前導 0\n"
                    f"次數: **{self.tries}**"
                )
            else:
                embed.description = (
                    f"規則: 長度 **{self.length}**、不重複數字、不可前導 0\n"
                    f"次數: **{self.tries}**"
                )
                rule = self._get_settlement_rule()
                if rule:
                    embed.description += (
                        f"\n獎懲: {rule['limit']} 次內 +{rule['win']:,}，"
                        f"超過 {rule['limit']} 次 {rule['loss']:,}"
                    )

        if self.history:
            record_lines = [f"`{g}` → **{a}A{b}B**" for g, a, b in self.history[-12:]]
            record_text = "\n".join(record_lines)
        else:
            record_text = "（尚無紀錄）"

        embed.add_field(name="紀錄", value=record_text, inline=False)

        thumb_user = self.player if self.player else self.creator
        if thumb_user and thumb_user.display_avatar:
            embed.set_thumbnail(url=thumb_user.display_avatar.url)

        return embed

    @discord.ui.button(label="🎯 猜答案", style=discord.ButtonStyle.primary)
    async def action_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        allowed, msg = self.ensure_player(interaction.user)
        if not allowed:
            return await interaction.response.send_message(msg, ephemeral=True)

        if self.is_solved:
            if self.challenge_mode:
                return await interaction.response.send_message("✅ 這局已完成。", ephemeral=True)
            new_view = ABGameView(
                self.cog,
                interaction.user,
                self.length,
                guild_id=interaction.guild.id if interaction.guild else None,
            )
            return await interaction.response.send_message(embed=new_view.build_embed(), view=new_view)
        await interaction.response.send_modal(ABGuessModal(self))

# tts
""" class NeuroSmartGenerator:
    def __init__(self):
        self.pa = pyaudio.PyAudio()

    def get_device_index(self, name_fragment):
        for i in range(self.pa.get_device_count()):
            dev = self.pa.get_device_info_by_index(i)
            if name_fragment in dev['name'] and dev['maxInputChannels'] > 0:
                return i
        return None

    def record_smart_task(self, frames, start_signal, stop_signal):
        dev_idx = self.get_device_index(RECORD_OUT)
        if dev_idx is None: return

        stream = self.pa.open(format=pyaudio.paInt16, channels=1, rate=44100,
                              input=True, input_device_index=dev_idx, frames_per_buffer=1024)

        recording_started = False
        last_sound_time = time.time()

        print("監聽中... 等待 Neuro 開口...")

        while not stop_signal.is_set():
            data = stream.read(1024, exception_on_overflow=False)
            audio_data = np.frombuffer(data, dtype=np.int16)
            peak = np.max(np.abs(audio_data))

            if not recording_started:
                # 只有當音量夠大，才開始錄製
                if peak > THRESHOLD:
                    print("檢測到有效音頻...")
                    recording_started = True
                    last_sound_time = time.time()
            else:
                frames.append(data)
                if peak > THRESHOLD:
                    last_sound_time = time.time()

                # 自動收尾
                if time.time() - last_sound_time > SILENCE_LIMIT and start_signal.is_set():
                    # 💡 絕招：移除最後幾塊可能包含「靜音底噪」的數據
                    for _ in range(3):
                        if frames: frames.pop()
                    print("💤 收尾完成。")
                    break
        stream.stop_stream()
        stream.close()
 """
class MyCommands(commands.Cog):
    BANK_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bank.json")
    FISHER_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "active_fishers.json")
    CLAIM_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "claimed_red_packets.json")
    KEYWORDS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "keywords.txt")
    BJ_CONTROL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "blackjack_control.json")
    TRACKED_CHANNELS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tracked_log_channels.json")
    TRACKED_VOICE_CHANNELS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tracked_voice_channels.json")
    FISH_POOL = [
        # 災難級 (總機率: 10%)
        {"id": 1, "name": "核廢料", "price": -3000, "rarity": "災難", "emoji": "☢️", "chance": 8, "description": "被核污染的神秘物質，處理危險"},
        {"id": 2, "name": "詛咒的金錢", "price": -500, "rarity": "災難", "emoji": "🪦", "chance": 2, "description": "帶著詛咒的硬幣，會招致厄運"},
        
        # 垃圾級 (總機率: 30%)
        {"id": 3, "name": "垃圾鞋子", "price": 10, "rarity": "垃圾", "emoji": "👟", "chance": 12, "description": "海洋中最常見的廢棄物"},
        {"id": 4, "name": "漏水的桶子", "price": 15, "rarity": "垃圾", "emoji": "🪣", "chance": 10, "description": "生鏽且破裂的舊桶子"},
        {"id": 5, "name": "破舊的寶箱", "price": 20, "rarity": "垃圾", "emoji": "📦", "chance": 8, "description": "空的古老寶箱，內無一物"},
        
        # 普通級 (總機率: 30%)
        {"id": 6, "name": "小丑魚", "price": 150, "rarity": "普通", "emoji": "🐠", "chance": 12, "description": "橙白相間的可愛魚兒"},
        {"id": 7, "name": "鯽魚", "price": 120, "rarity": "普通", "emoji": "🐟", "chance": 10, "description": "淡水最常見的魚種"},
        {"id": 8, "name": "草魚", "price": 130, "rarity": "普通", "emoji": "🐟", "chance": 8, "description": "以青草為食的溫和魚兒"},
        
        # 稀有級 (總機率: 15%)
        {"id": 9, "name": "鮭魚", "price": 300, "rarity": "稀有", "emoji": "🐟", "chance": 7, "description": "海洋珍品，迴遊魚類的代表"},
        {"id": 10, "name": "金色鱘魚", "price": 500, "rarity": "稀有", "emoji": "🐟", "chance": 5, "description": "閃閃發光的古老魚種，十分稀見"},
        {"id": 11, "name": "帝王蟹", "price": 450, "rarity": "稀有", "emoji": "🦀", "chance": 3, "description": "深海中的國王，體型碩大"},
        
        # 史詩級 (總機率: 10%)
        {"id": 12, "name": "大白鯊", "price": 1500, "rarity": "史詩", "emoji": "🦈", "chance": 5, "description": "海洋之王，兇悍無比"},
        {"id": 13, "name": "龍魚", "price": 2000, "rarity": "史詩", "emoji": "🐲", "chance": 3, "description": "傳說中的龍族化身，驚人價值"},
        {"id": 14, "name": "巨型烏賊", "price": 1800, "rarity": "史詩", "emoji": "🦑", "chance": 2, "description": "深海怪物，神秘而恐怖"},
        
        # 傳說級 (總機率: 5%)
        {"id": 15, "name": "亞特蘭提斯金幣", "price": 5000, "rarity": "傳說", "emoji": "🔱", "chance": 3, "description": "遠古文明的寶藏，價值連城"},
        {"id": 16, "name": "人魚的眼淚", "price": 8000, "rarity": "傳說", "emoji": "🧜", "chance": 1, "description": "人魚之淚凝結而成，極其珍稀"},
        {"id": 17, "name": "黃金龍魚", "price": 10000, "rarity": "傳說", "emoji": "🏆", "chance": 1, "description": "傳說中最貴重的魚，一生難遇"},
    ]

    def __init__(self, bot, ai_logic_func=None):
        self.bot = bot
        self.ai_logic = ai_logic_func
        self._init_extra_vars()
        self.pa = pyaudio.PyAudio()
        self.is_processing = False
        self._console_listener_started = False

    def _ensure_console_listener(self):
        if self._console_listener_started:
            return
        self._console_listener_started = True
        print('--- NuSo Online ---')
        threading.Thread(target=self.console_listener, daemon=True).start()

    def _build_fishing_embed(self, type_: str, data: dict) -> discord.Embed:
            """
            type_: 'result' 結算, 'progress' 進行中, 'start' 出海確認, 'done' 已出海
            data: 需包含 user_name, user_id, rarity_counts, total_reward, finish_time, 等
            """
            if type_ == 'result':
                summary = "\n".join([f"• {r}: {count}次" for r, count in data.get("rarity_counts", {}).items()])
                embed = discord.Embed(title="🎣 釣魚成果報告", color=0x2ecc71)
                display_name = data.get("user_name") or f"<@{data.get('user_id')}>"
                embed.description = f"{display_name} 任務已完成！這是你在這段期間的收穫："
                embed.add_field(name="📊 捕獲統計", value=f"```\n{summary}\n```", inline=False)
                embed.add_field(name="💰 最終收益", value=f"**`${data.get('total_reward',0):,}`**", inline=True)
                
                # 添加技能經驗信息
                level_ups = int(data.get('level_ups', 0) or 0)
                current_level = int(data.get('current_level', 1) or 1)
                total_skill_exp = int(data.get('total_skill_exp', 0) or 0)
                prev_level = int(data.get('prev_level', current_level) or current_level)
                prev_exp = int(data.get('prev_exp', 0) or 0)
                current_exp = int(data.get('current_exp', 0) or 0)

                prev_progress = "MAX" if prev_level >= 20 else f"{max(0, min(prev_exp, 100))}/100"
                current_progress = "MAX" if current_level >= 20 else f"{max(0, min(current_exp, 100))}/100"

                if level_ups > 0:
                    skill_text = (
                        f"**升級了 {level_ups} 等！** 🎉\n"
                        f"本次獲得 `+{total_skill_exp}` 經驗\n"
                        f"`Lv.{prev_level}` ({prev_progress}) ➜ `Lv.{current_level}` ({current_progress})"
                    )
                else:
                    skill_text = (
                        f"本次獲得 `+{total_skill_exp}` 經驗\n"
                        f"目前 `Lv.{current_level}` ({current_progress})"
                    )
                embed.add_field(name="⭐ 釣魚技能", value=skill_text, inline=False)
                
                return embed
            elif type_ == 'progress':
                finish_display = data['finish_time'].strftime("%H:%M:%S")
                embed = discord.Embed(title="🎣 釣魚任務執行中", color=0x3498db)
                embed.description = f"目前正在作業中，預計 **{finish_display}** 回港。"
                return embed
            elif type_ == 'start':
                # 出海確認
                hh, remainder = divmod(data['duration'], 3600)
                mm, ss = divmod(remainder, 60)
                time_str = (f"{hh}小時" if hh > 0 else "") + (f"{mm}分" if mm > 0 else "") + f"{ss}秒"
                fish_skill_lv = data.get('fish_skill_lv', 1)
                discount = data.get('discount', '0%')
                embed = discord.Embed(title="🚢 漁船出海確認", color=0x2ecc71)
                embed.description = (
                    f"👤 **釣客：** {data['user_mention']}\n"
                    f"🚤 **漁船等級：** `Lv.{data['boat_lv']}`\n"
                    f"🎣 **魚竿等級：** `Lv.{data['rod_lv']}`\n"
                    f"⭐ **釣魚技能：** `Lv.{fish_skill_lv}`\n"
                    f"⏱️ **作業速度：** `{data['per_fish_time']:.1f}s` / 竿\n"
                    f"⏳ **總計耗時：** `約 {time_str}`\n"
                    f"🔔 **預計回港：** `{data['finish_time'].strftime('%H:%M:%S')}`\n"
                    f"💰 **消耗：** `${data['cost']:,}` (`-{discount}` 折扣)\n\n"
                    "請按下 **確認出海** 開始任務"
                )
                return embed
            elif type_ == 'done':
                hh, remainder = divmod(data['duration'], 3600)
                mm, ss = divmod(remainder, 60)
                time_str = (f"{hh}小時" if hh > 0 else "") + (f"{mm}分" if mm > 0 else "") + f"{ss}秒"
                embed = discord.Embed(title="🚢 漁船已出海", color=0x2ecc71)
                embed.description = (
                    f"👤 **釣客：** <@{data['user_id']}>\n"
                    f"🚤 **漁船等級：** `Lv.{data['boat_lv']}`\n"
                    f"⏱️ **作業速度：** `{data['per_fish_time']:.1f}s` / 竿\n"
                    f"⏳ **總計耗時：** `約 {time_str}`\n"
                    f"🔔 **回港時間：** `{data['finish_time'].strftime('%H:%M:%S')}`"
                )
                return embed
            return discord.Embed(title="釣魚通知", description="未知狀態", color=0x95a5a6)

    def _load_json(self, path):
        try:
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            print(f"[JSON] 讀取 {path} 失敗: {e}")
        return {}

    def _save_json(self, path, data):
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"[JSON] 儲存 {path} 失敗: {e}")

    def _sanitize_filename(self, text: str) -> str:
        invalid = '<>:"/\\|?*'
        safe = "".join("_" if ch in invalid else ch for ch in (text or "")).strip().rstrip('.')
        return safe or "unknown_channel"

    def _channel_log_output_path(self, channel_name: str) -> str:
        log_dir = os.path.join(os.getcwd(), "channel_log")
        os.makedirs(log_dir, exist_ok=True)
        return os.path.join(log_dir, f"{self._sanitize_filename(channel_name)}.txt")

    def _voice_channel_log_output_path(self, channel_name: str):
        log_dir = os.path.join(os.getcwd(), "channel_log")
        os.makedirs(log_dir, exist_ok=True)
        safe_channel = self._sanitize_filename(channel_name)
        return os.path.join(log_dir, f"voice_log_{safe_channel}.txt")

    def _append_voice_channel_log(self, item: dict):
        try:
            line = (
                f"[{item['time']}] {item['user']} ({item['user_id']}) | "
                f"{item['event']} | 頻道: {item['channel']}\n"
            )
            output_path = self._voice_channel_log_output_path(item.get("channel", "unknown_channel"))
            existing = ""
            if os.path.exists(output_path):
                with open(output_path, "r", encoding="utf-8") as f:
                    existing = f.read()
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(line)
                if existing:
                    f.write(existing)
        except Exception as e:
            print(f"⚠️ 寫入語音追蹤檔失敗: {e}")

    def _load_tracked_log_channels(self):
        data = self._load_json(self.TRACKED_CHANNELS_PATH)
        raw_list = data.get("channel_ids", []) if isinstance(data, dict) else []
        result = set()
        for item in raw_list:
            try:
                result.add(int(item))
            except Exception:
                pass
        return result

    def _load_tracked_voice_channels(self):
        data = self._load_json(self.TRACKED_VOICE_CHANNELS_PATH)
        raw_list = data.get("channel_ids", []) if isinstance(data, dict) else []
        result = set()
        for item in raw_list:
            try:
                result.add(int(item))
            except Exception:
                pass
        return result

    def _save_tracked_log_channels(self):
        data = {"channel_ids": sorted(self.tracked_log_channels)}
        self._save_json(self.TRACKED_CHANNELS_PATH, data)

    def _save_tracked_voice_channels(self):
        data = {"channel_ids": sorted(self.tracked_voice_channels)}
        self._save_json(self.TRACKED_VOICE_CHANNELS_PATH, data)

    async def _append_channel_message_log(self, message: discord.Message):
        try:
            ts = message.created_at.astimezone().strftime("%Y-%m-%d %H:%M:%S")
            content = (message.content or "").replace("\n", "\\n")
            if not content:
                if message.attachments:
                    attach_parts = [f"{att.filename}: {att.url}" for att in message.attachments]
                    content = f"[附件 {len(message.attachments)}] " + " | ".join(attach_parts)
                elif message.embeds:
                    content = f"[Embed {len(message.embeds)}]"
                else:
                    content = "[無文字內容]"

            line = f"[{ts}] {message.author.display_name} ({message.author.id}): {content}\n"
            output_path = self._channel_log_output_path(message.channel.name)
            existing = ""
            if os.path.exists(output_path):
                with open(output_path, "r", encoding="utf-8") as f:
                    existing = f.read()
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(line)
                if existing:
                    f.write(existing)
            print(f"[TrackLog][#{message.channel.name}] {line.rstrip()}")
        except Exception as e:
            print(f"⚠️ 追蹤頻道寫入失敗: {e}")

    def record_smart_task(self, frames, start_signal, stop_signal):
        """智慧錄音任務：只錄取從 HitPaw 傳出來有聲音的部分"""
        # 這裡會呼叫你類別內的 get_device_index
        dev_idx = self.get_device_index(RECORD_OUT)
        if dev_idx is None:
            print("❌ 找不到錄音設備 (HitPaw)，請檢查設備名稱！")
            return

        # 初始化串流
        stream = self.pa.open(format=pyaudio.paInt16, channels=1, rate=44100,
                              input=True, input_device_index=dev_idx, frames_per_buffer=1024)

        recording_started = False
        last_sound_time = time.time()

        print("🎙️ 智慧監聽中... 等待變聲器輸出...")

        while not stop_signal.is_set():
            try:
                data = stream.read(1024, exception_on_overflow=False)
                audio_data = np.frombuffer(data, dtype=np.int16)
                peak = np.max(np.abs(audio_data))

                if not recording_started:
                    # 只有當音量超過門檻 (THRESHOLD)，才開始把數據存進 frames
                    if peak > THRESHOLD:
                        print("🔥 檢測到變聲器音頻，開始錄製...")
                        recording_started = True
                        last_sound_time = time.time()
                else:
                    frames.append(data)
                    if peak > THRESHOLD:
                        last_sound_time = time.time()

                    # 自動收尾邏輯：如果靜音超過 SILENCE_LIMIT 秒，且播放已結束
                    if time.time() - last_sound_time > SILENCE_LIMIT and start_signal.is_set():
                        # 移除結尾可能的靜音數據
                        for _ in range(3):
                            if frames: frames.pop()
                        print("💤 錄音收尾完成。")
                        break
            except Exception as e:
                print(f"❌ 錄音過程出錯: {e}")
                break

        stream.stop_stream()
        stream.close()

    def get_device_index(self, name_fragment):
        print("--- 正在掃描音訊設備 ---")
        for i in range(self.pa.get_device_count()):
            dev = self.pa.get_device_info_by_index(i)
            print(f"Index {i}: {dev['name']}") # 👈 這行會印出你電腦所有設備名稱
            if name_fragment in dev['name'] and dev['maxInputChannels'] > 0:
                print(f"✅ 成功找到匹配設備: {dev['name']} (Index {i})")
                return i
        print(f"❌ 找不到包含 '{name_fragment}' 的錄音設備！")
        return None

    def load_keywords(self):
        if not os.path.exists(self.KEYWORDS_PATH):
            with open(self.KEYWORDS_PATH, "w", encoding="utf-8") as f:
                f.write("大紅包\n")
        try:
            with open(self.KEYWORDS_PATH, "r", encoding="utf-8") as f:
                return [line.strip() for line in f if line.strip()]
        except Exception as e:
            print(f"[紅包] 讀取 keywords.txt 失敗: {e}")
            return ["大紅包"]

    def load_claims(self):
        if not os.path.exists(self.CLAIM_PATH):
            self._save_json(self.CLAIM_PATH, {})
        return self._load_json(self.CLAIM_PATH)

    def save_claims(self, claims):
        self._save_json(self.CLAIM_PATH, claims)

    def get_all_fishers(self):
        raw = self._load_json(self.FISHER_PATH)
        # 轉回 datetime
        for uid, info in raw.items():
            if "end_time" in info and isinstance(info["end_time"], str):
                try:
                    info["end_time"] = datetime.fromisoformat(info["end_time"])
                except Exception:
                    pass
            if "start_time" in info and isinstance(info.get("start_time"), str):
                try:
                    info["start_time"] = datetime.fromisoformat(info["start_time"])
                except Exception:
                    pass
        return raw

    def update_fisher(self, user_id, data):
        all_fishers = self.get_all_fishers()
        # datetime 轉字串
        for k in ("start_time", "end_time"):
            if k in data and isinstance(data[k], datetime):
                data[k] = data[k].isoformat()
        all_fishers[str(user_id)] = data
        self.save_active_fishers(all_fishers)

    def save_active_fishers(self, all_fishers):
        # datetime 轉字串
        serialized = {}
        for uid, info in all_fishers.items():
            data = {}
            for k, v in info.items():
                if isinstance(v, datetime):
                    data[k] = v.isoformat()
                else:
                    data[k] = v
            serialized[str(uid)] = data
        self._save_json(self.FISHER_PATH, serialized)

    def remove_fisher(self, user_id):
        all_fishers = self.get_all_fishers()
        all_fishers.pop(str(user_id), None)
        self.save_active_fishers(all_fishers)







    def _find_bank_cog(self):

        # 1. 嘗試標準名稱
        bank = self.bot.get_cog("BankMod")
        if bank and hasattr(bank, 'add_stats'):
            return bank

        # 2. 遍歷所有已載入的 Cog，尋找擁有 add_stats 方法的模組
        for name, cog in self.bot.cogs.items():
            if hasattr(cog, 'add_stats') and name != "MyCommands":
                print(f"DEBUG: 透過特徵搜尋找到銀行模組: {name}")
                return cog
        return None

    def _init_extra_vars(self):
        self.last_word = ""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_dir = os.path.dirname(current_dir)
        self.idiom_file = os.path.join(project_dir, "idioms.txt")
        self.queues = {}
        self.stock_cache_file = os.path.join(current_dir, "stock_cache.json") # 快取檔案路徑
        # 優先從 bot.get_cog 獲取，若還沒載入則設為 None
        self.bank = self._find_bank_cog()
        self.active_robbers = set()
        self.BJ_CONTROL_PATH = os.path.join(current_dir, "blackjack_control.json")
        self.voice_event_log = deque(maxlen=20000)
        self.tracked_log_channels = self._load_tracked_log_channels()
        self.tracked_voice_channels = self._load_tracked_voice_channels()
        self.GUILD_IDS = [int(x) for x in getattr(self.bot, "guild_ids", [1446838276249096228])]
        self.GUILD_ID = self.GUILD_IDS[0] if self.GUILD_IDS else 1446838276249096228  # 終端預設操作伺服器
        print("[Path Debug] __file__:", os.path.abspath(__file__))
        print("[Path Debug] cwd:", os.getcwd())
        print("[Path Debug] idiom_file:", self.idiom_file)
        print("[Path Debug] stock_cache_file:", self.stock_cache_file)
        print("[Path Debug] BJ_CONTROL_PATH:", self.BJ_CONTROL_PATH)

    def _load_bj_control(self):
        """讀取 blackjack_control.json"""
        try:
            if os.path.exists(self.BJ_CONTROL_PATH):
                with open(self.BJ_CONTROL_PATH, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            print(f"⚠️ 讀取 blackjack_control.json 失敗: {e}")
        return {}

    def _save_bj_control(self, data):
        """寫入 blackjack_control.json"""
        try:
            with open(self.BJ_CONTROL_PATH, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"⚠️ 寫入 blackjack_control.json 失敗: {e}")

    def _get_bj_control_override(self, user_id):
        """若玩家在控制名單中，回傳 (result_type, result_text, color) 覆寫；否則回傳 None"""
        data = self._load_bj_control()
        uid_str = str(user_id)
        if uid_str not in data:
            return None
        ent = data[uid_str]
        mode = ent.get("mode", "").lower()
        if mode == "w":
            return ("win", "🎊 後台控制：強制勝利！", discord.Color.green())
        if mode == "l":
            return ("loss", "👻 後台控制：強制失敗。", discord.Color.red())
        return None

    def is_valid_idiom(self, word):
        if not os.path.exists(self.idiom_file):
            print(f"警告：找不到 {self.idiom_file}")
            return True
        try:
            with open(self.idiom_file, "r", encoding="utf-8") as f:
                idioms = {line.strip() for line in f.readlines()}
                return word in idioms
        except Exception as e:
            print(f"讀取成語庫出錯: {e}")
            return False

    def calculate_hand(self, hand):
        value = 0
        aces = 0
        for card in hand:
            # 提取卡牌的面值（牌格式為 "10♥️"、"J♠️" 等，花色佔最後 2 字元）
            rank = card[:-2] if card and len(card) >= 2 else (card[0] if card else '')

            if rank in ['J', 'Q', 'K']:
                value += 10
            elif rank == 'A':
                aces += 1
                value += 11
            else:
                try:
                    value += int(rank)
                except ValueError:
                    pass  # 如果無法轉換則跳過
        while value > 21 and aces:
            value -= 10
            aces -= 1
        return value

    def _generate_ab_answer(self, length: int) -> str:
        first = random.choice("123456789")
        remain_pool = [ch for ch in "0123456789" if ch != first]
        others = random.sample(remain_pool, length - 1)
        return first + "".join(others)

    def _validate_ab_input(self, number: str, length: int):
        value = (number or "").strip()
        if len(value) != int(length):
            return f"❌ 請輸入剛好 {length} 位數字。"
        if not value.isdigit():
            return "❌ 只能輸入數字。"
        if value[0] == "0":
            return "❌ 不可前導 0。"
        if len(set(value)) != len(value):
            return "❌ 每一位數字不能重複。"
        return None

    def _fixed_deposit_rate(self, term_days: int):
        if term_days <= 1:
            return 0.1
        if term_days <= 3:
            return 0.25
        if term_days <= 5:
            return 0.6
        return 1.2

    def _parse_fd_time(self, value: str):
        try:
            return datetime.fromisoformat(value)
        except Exception:
            return None

    def _calc_ab(self, answer: str, guess: str):
        a_count = sum(1 for i, ch in enumerate(guess) if answer[i] == ch)
        b_count = sum(1 for ch in guess if ch in answer) - a_count
        return a_count, b_count

    def load_stock_cache(self):
        if os.path.exists(self.stock_cache_file):
            try:
                with open(self.stock_cache_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except: return {}
        return {}

    def save_stock_cache(self, cache_data):
        with open(self.stock_cache_file, "w", encoding="utf-8") as f:
            json.dump(cache_data, f, indent=4, ensure_ascii=False)

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



    def cleanup_temp_file(self, file_path):
        """播放完後的清理工作"""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                print(f"🧹 已清理臨時檔案: {file_path}")
        except Exception as e:
            print(f"⚠️ 清理檔案失敗: {e}")

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        if member.bot:
            return

        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        events = []

        before_chan = before.channel.name if before.channel else "無"
        after_chan = after.channel.name if after.channel else "無"

        if before.channel != after.channel:
            if before.channel is None and after.channel is not None:
                events.append(f"加入語音：{after_chan}")
            elif before.channel is not None and after.channel is None:
                events.append(f"離開語音：{before_chan}")
            else:
                events.append(f"切換語音：{before_chan} -> {after_chan}")

        if before.self_mute != after.self_mute:
            events.append(f"麥克風：{'關閉' if after.self_mute else '開啟'}")

        if before.self_deaf != after.self_deaf:
            events.append(f"耳機：{'關閉(拒聽)' if after.self_deaf else '開啟'}")

        if before.mute != after.mute:
            events.append(f"伺服器靜音：{'開啟' if after.mute else '解除'}")

        if before.deaf != after.deaf:
            events.append(f"伺服器拒聽：{'開啟' if after.deaf else '解除'}")

        if before.self_stream != after.self_stream:
            events.append(f"直播：{'開始' if after.self_stream else '結束'}")

        if before.self_video != after.self_video:
            events.append(f"視訊：{'開啟' if after.self_video else '關閉'}")

        for e in events:
            item = {
                "time": ts,
                "user_id": member.id,
                "user": member.display_name,
                "channel": after.channel.name if after.channel else before_chan,
                "channel_id": (after.channel.id if after.channel else (before.channel.id if before.channel else None)),
                "event": e,
            }
            self.voice_event_log.append(item)
            if "加入語音" in e:
                print(f"[{item['time']}] 🔊 {item['user']} ({item['user_id']}) 加入語音頻道：{item['channel']}")
                cid = item.get("channel_id")
                if (not self.tracked_voice_channels) or (cid in self.tracked_voice_channels):
                    self._append_voice_channel_log(item)
            elif "離開語音" in e:
                print(f"[{item['time']}] 🚪 {item['user']} ({item['user_id']}) 離開語音頻道：{item['channel']}")
                cid = item.get("channel_id")
                if (not self.tracked_voice_channels) or (cid in self.tracked_voice_channels):
                    self._append_voice_channel_log(item)

    # --- 訊息處理中心 ---
    @commands.Cog.listener()
    async def on_message(self, message):
        # 排除機器人自己的訊息
        if message.author.bot:
            return

        if message.channel and message.channel.id in self.tracked_log_channels:
            await self._append_channel_message_log(message)

        content = message.content.lower()

        # --- 邏輯 A: 成語接龍 ---
        # 檢查是否存在 last_word 且內容長度為 4 (成語)
        if hasattr(self, 'last_word') and self.last_word and len(content) == 4:
            if message.reference and message.reference.message_id:
                try:
                    replied_msg = message.reference.cached_message or await message.channel.fetch_message(message.reference.message_id)
                    if replied_msg.author.id == self.bot.user.id and self.last_word in replied_msg.content:
                        if content[0] == self.last_word[-1]:
                            # 假設你有 is_valid_idiom 函式
                            if hasattr(self, 'is_valid_idiom') and self.is_valid_idiom(content):
                                self.last_word = content
                                await message.reply(f"✅ **判定成功！**\n下一個字：**{self.last_word[-1]}**")
                                return
                except:
                    pass

        # --- 邏輯 B: 關鍵字反應 ---
        if "nuso" in content:
            await message.add_reaction("✨")

        # --- 邏輯 C: Neuro 對話 (標記時觸發) ---

        if message.reference:
            return
        if self.bot.user.mentioned_in(message):
            if self.is_processing:
                return

            # 設定狀態為忙碌
            self.is_processing = True
            # 清理標記文字
            user_input = message.content.replace(f'<@!{self.bot.user.id}>', '').replace(f'<@{self.bot.user.id}>', '').strip()
            async with message.channel.typing():
                try:
                # 1. 思考 (文字生成)
                    response_text = await self.get_neuro_response(user_input)

                # 2. 回覆文字
                    await message.reply(response_text)

                # 3. 語音處理 (若使用者在語音頻道)
                    if message.author.voice:
                        # 接收產出的隨機檔名 (例如 neuro_2024...wav)
                        produced_wav_path = await self.generate_and_convert(response_text)

                        # 檢查是否有成功產出檔案，再傳給播放器
                        if produced_wav_path:
                            await self.play_neuro_file(message, produced_wav_path)
                        else:
                            print("⚠️ 錄音失敗，沒有產出語音檔案。")

                except Exception as e:
                    print(f"❌ Neuro 邏輯崩潰: {e}")
                finally:
                    # 不論成功或失敗，最後一定要把狀態改回「不忙」，否則機器人會永遠不理人
                    self.is_processing = False
    async def generate_and_convert(self, text):
        # 1. 取得目前路徑並印出
        current_dir = os.getcwd()
        print(f"📂 機器人目前資料夾 (CWD): {current_dir}")

        # 2. 使用時間戳記生成唯一檔名，防止 Permission denied
        # 使用 microsecond 確保即使連發也不會撞名
        ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        temp_tts = f"temp_{ts}.mp3"
        final_wav = f"neuro_{ts}.wav"

        # 完整路徑印出來給你看
        full_temp_path = os.path.join(current_dir, temp_tts)
        print(f"📝 正在寫入 TTS 暫存檔: {full_temp_path}")

        try:
            # TTS 轉換
            communicate = edge_tts.Communicate(text, "en-US-AriaNeural")
            await communicate.save(temp_tts)
            print(f"✅ TTS 生成成功")
        except Exception as e:
            print(f"❌ 無法寫入 TTS 檔案: {e}")
            return None

        # --- 錄音與播放邏輯 ---
        recorded_frames = []
        play_done_signal = threading.Event()
        force_stop_signal = threading.Event()

        record_thread = threading.Thread(
            target=self.record_smart_task,
            args=(recorded_frames, play_done_signal, force_stop_signal)
        )
        record_thread.start()

        # 播放到變聲器
        pygame.mixer.init()
        devices = sdl2_audio.get_audio_device_names(False)
        target_play = next((d for d in devices if VB_CABLE_IN in d), None)
        pygame.mixer.quit()
        pygame.mixer.init(devicename=target_play)

        pygame.mixer.music.load(temp_tts)
        pygame.mixer.music.play()
        print(f"🔈 正在播放暫存檔到變聲器...")

        while pygame.mixer.music.get_busy():
            await asyncio.sleep(0.1)

        play_done_signal.set()
        record_thread.join(timeout=10)
        force_stop_signal.set()

        # 3. 存成最後的 WAV
        if recorded_frames:
            with wave.open(final_wav, 'wb') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(self.pa.get_sample_size(pyaudio.paInt16))
                wf.setframerate(44100)
                wf.writeframes(b''.join(recorded_frames))

            print(f"語音成品已儲存: {os.path.abspath(final_wav)}")

            # 播放完畢，卸載音樂並嘗試刪除暫存檔
            pygame.mixer.music.unload()
            try:
                os.remove(temp_tts)
            except:
                pass

            return final_wav # 回傳這個路徑給播放器
        return None
    async def play_neuro_file(self, message, file_path):
        if not os.path.exists(file_path):
            print(f"❌ 找不到要播放的檔案: {file_path}")
            return
        try:
            # 取得語音頻道
            channel = message.author.voice.channel
            vc = discord.utils.get(self.bot.voice_clients, guild=message.guild)

            # 如果機器人不在頻道裡，就進去；如果不在，就跳過來
            if not vc:
                vc = await channel.connect()
            elif vc.channel != channel:
                await vc.move_to(channel)

            # 如果正在播別的（例如音樂），先停掉
            if vc.is_playing():
                vc.stop()

            # 開始播放
            print(f"🎵 Discord 正在播放: {file_path}")
            # 使用 after 參數在播放完後自動清理檔案，防止硬碟爆掉
            vc.play(discord.FFmpegPCMAudio(file_path), after=lambda e: self.cleanup_temp_file(file_path))

        except Exception as e:
            print(f"❌ Discord 播放失敗: {e}")
    @commands.Cog.listener()
    async def on_ready(self):
        self._ensure_console_listener()

    async def command_log(self, interaction: discord.Interaction, command: app_commands.Command):
        LOG_CHANNEL_ID = 1471923362581446676
        user = interaction.user
        cmd_name = command.name
        guild = interaction.guild.name if interaction.guild else "私訊"
        # 取得輸入參數
        options = interaction.data.get('options', [])
        args = {opt['name']: opt['value'] for opt in options} if options else "無參數"
        time_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        # 2. 同時保留 Terminal 顯示 (方便除錯)
        print(f"[{time_str}] {user.display_name} 使用了 /{cmd_name}")
        # 3. 發送到 Discord 頻道
        log_channel = self.bot.get_channel(LOG_CHANNEL_ID)
        if log_channel:
            embed = discord.Embed(
                title="📑 指令使用日誌",
                color=0x3498db,
                timestamp=datetime.now()
            )
            embed.add_field(name="使用者", value=f"{user.mention} ({user.id})", inline=False)
            embed.add_field(name="伺服器", value=guild, inline=False)
            embed.add_field(name="指令", value=f"`/{cmd_name}`", inline=False)
            embed.add_field(name="參數內容", value=f"```json\n{args}\n```", inline=False)
            await log_channel.send(embed=embed)


        # 啟動終端監聽線程
        await self.bot.change_presence(activity=discord.Game(name="Loss 3.5"))
        self._ensure_console_listener()

    async def _send_fishing_embed(self, ctx, type_, data, ephemeral=False):
        embed = self._build_fishing_embed(type_, data)
        try:
            if hasattr(ctx, "response") and not ctx.response.is_done():
                await ctx.response.send_message(embed=embed, ephemeral=ephemeral)
            elif hasattr(ctx, "followup"):
                await ctx.followup.send(embed=embed, ephemeral=ephemeral)
            else:
                await ctx.send(embed=embed, ephemeral=ephemeral)
        except Exception as e:
            print(f"⚠️ 發送釣魚 UI 失敗: {e}")
    async def process_bj_control(self, args):
        """處理終端指令 bj <display_name> <mode>（由 main.py 終端機轉發）"""
        try:
            parts = args.split(None, 1)
            if len(parts) < 2:
                print("❌ 格式：bj <顯示名稱> <w|l|p>")
                return
            display_name, mode = parts[0], parts[1].lower()
            if mode not in ("w", "l", "p"):
                print("❌ mode 須為 w(必贏)、l(必輸)、p(清除)")
                return

            found = None
            for guild in self.bot.guilds:
                for member in guild.members:
                    if member.display_name == display_name or member.name == display_name:
                        found = member
                        break
                if found:
                    break

            if not found:
                print(f"❌ 找不到成員：{display_name}")
                return

            data = self._load_bj_control()
            uid_str = str(found.id)
            if mode == "p":
                if uid_str in data:
                    del data[uid_str]
                    self._save_bj_control(data)
                    print(f"✅ 已清除 {found.display_name} ({uid_str}) 的 21 點控制紀錄")
                else:
                    print(f"ℹ️ {found.display_name} 無控制紀錄")
            else:
                data[uid_str] = {"mode": mode, "display_name": found.display_name}
                self._save_bj_control(data)
                m = "必贏" if mode == "w" else "必輸"
                print(f"✅ 已設定 {found.display_name} ({uid_str})：{m}")
        except Exception as e:
            print(f"⚠️ 21點控制指令錯誤: {e}")
    async def get_neuro_response(self, user_input):
        """呼叫 Llama 模型生成文字"""
        try:
            # 從 bot 物件中取得模型和 Tokenizer
            tokenizer = self.bot.tokenizer
            model = self.bot.neuro_model

            if model is None:
                return "My brain is not loaded yet..."

            # 你的簡化 Prompt
            prompt = f"<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n\n你現在是 Neuro-sama。短促、毒舌、傲嬌。<|eot_id|><|start_header_id|>user<|end_header_id|>\n\n{user_input}<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n\n"

            inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=256).to("cuda")

            # 使用 executor 避免卡住主執行緒
            loop = asyncio.get_event_loop()
            outputs = await loop.run_in_executor(None, lambda: model.generate(
                **inputs,
                max_new_tokens=40,
                do_sample=True,
                temperature=0.8,
                top_p=0.9,
                repetition_penalty=1.2,
                pad_token_id=tokenizer.eos_token_id,
                eos_token_id=tokenizer.eos_token_id
            ))

            full_response = tokenizer.decode(outputs[0], skip_special_tokens=True)
            # 取得 assistant 之後的文字
            return full_response.split("assistant")[-1].strip()
        except Exception as e:
            print(f"❌ AI 生成失敗: {e}")
            return "嘖，腦袋轉不動了..."

    @app_commands.command(name="claim", description="輸入密語領取新春紅包！")
    @app_commands.describe(code="請輸入紅包密語")
    async def claim(self, interaction: discord.Interaction, code: str):
        uid = str(interaction.user.id)
        code = code.strip()
        keywords = self.load_keywords()
        if code not in keywords:
            return await interaction.response.send_message("❌ 密語錯誤，請再檢查一下喔！", ephemeral=True)
        claims = self.load_claims()
        user_claims = claims.get(uid, [])
        if code in user_claims:
            return await interaction.response.send_message("⚠️ 這個紅包你已經領過囉！", ephemeral=True)
        # 發錢
        bank = self.bot.get_cog('BankMod')
        if not bank:
            return await interaction.response.send_message("❌ 系統錯誤，找不到銀行模組！", ephemeral=True)
        try:
            bank.add_stats(interaction.guild.id, interaction.user.id, coin=100000)
            bank.save_data()
        except Exception as e:
            print(f"[紅包] 發錢失敗: {e}")
            return await interaction.response.send_message("❌ 發放金幣時發生錯誤，請聯絡管理員。", ephemeral=True)
        # 更新紀錄
        user_claims.append(code)
        claims[uid] = user_claims
        self.save_claims(claims)
        # Embed UI
        embed = discord.Embed(title="🧧 新春大紅包領取成功！", color=0xFF0000)
        embed.description = "恭喜你獲得了 100,000 金幣！祝你大年初一開春大吉！"
        embed.set_footer(text=f"本次領取密語：{code}")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # 抽籤指令
    @app_commands.command(name="choose", description="幫你從多個選項中選一個")
    @app_commands.describe(選項="請輸入選項，空格分隔")
    async def choose(self, interaction: discord.Interaction, 選項: str):
        selection_list = 選項.split()
        picked = random.choice(selection_list) if selection_list else "沒給選項標題"
        await interaction.response.send_message(f"NuSo 幫你選了：**{picked}**")

    # Ping 指令
    @app_commands.command(name="ping", description="檢查延遲")
    async def ping(self, interaction: discord.Interaction):
        await interaction.response.send_message(f"機器人延遲為 {round(self.bot.latency * 1000)}ms")

    # 成語接龍指令
    @app_commands.command(name="idiom_start", description="開始一個成語接龍遊戲")
    @app_commands.describe(word="請輸入一個四字成語作為開頭")
    async def idiom_start(self, interaction: discord.Interaction, word: str):
        if len(word) != 4:
            await interaction.response.send_message("請輸入一個四字成語！", ephemeral=True)
            return
        self.last_word = word
        await interaction.response.send_message(f"🏁 成語接龍開始！\n當前成語：**{word}**\n請接下一個字：**{word[-1]}**")

    @app_commands.command(name="ab", description="幾A幾B（電腦出題）")
    @app_commands.describe(length="題目長度（3~6 位，預設 4）")
    async def ab(self, interaction: discord.Interaction, length: app_commands.Range[int, 3, 6] = 4):
        view = ABGameView(self, interaction.user, int(length), guild_id=interaction.guild.id if interaction.guild else None)
        await interaction.response.send_message(embed=view.build_embed(), view=view)

    @app_commands.command(name="ab_set", description="自訂幾A幾B題目給別人猜")
    @app_commands.describe(length="題目長度（3~6 位）", answer="你要出的答案（不可重複、不可前導0）", user="指定挑戰者")
    async def ab_set(self, interaction: discord.Interaction, length: app_commands.Range[int, 3, 6], answer: str, user: discord.Member):
        clean_answer = (answer or "").strip()
        error = self._validate_ab_input(clean_answer, int(length))
        if error:
            return await interaction.response.send_message(error, ephemeral=True)

        if user.id == interaction.user.id:
            return await interaction.response.send_message("❌ 不能指定自己當挑戰者。", ephemeral=True)

        view = ABGameView(
            self,
            interaction.user,
            int(length),
            answer=clean_answer,
            challenge_mode=True,
            target_user=user,
            guild_id=interaction.guild.id if interaction.guild else None,
        )
        await interaction.response.send_message(
            content=f"🧩 {interaction.user.mention} 出了一題幾A幾B，指定 {user.mention} 挑戰！",
            embed=view.build_embed(),
            view=view,
        )

    # 整合 Bank 系統的 21 點
    @app_commands.command(name="blackjack", description="跟我玩一場 21 點！")
    @app_commands.describe(bet="下注金額")
    async def blackjack_cmd(self, interaction: discord.Interaction, bet: int):
        await self.start_blackjack(interaction, bet)
    async def start_blackjack(self, interaction: discord.Interaction, bet: int):
        # 確保 bank 已正確載入
        if not self.bank or not hasattr(self.bank, 'add_stats'):
            self.bank = self._find_bank_cog()

        if not self.bank:
            print("ERROR: 21點無法獲取銀行模組 (BankMod)")
            return await (interaction.followup.send if interaction.response.is_done() else interaction.response.send_message)("❌ 銀行系統尚未就緒或未載入，請聯繫管理員！", ephemeral=True)

        try:
            user_data = self.bank.add_stats(interaction.guild.id, interaction.user.id, coin=0)
        except Exception as e:
            print(f"ERROR: 呼叫銀行模組失敗: {e}")
            return await (interaction.followup.send if interaction.response.is_done() else interaction.response.send_message)("❌ 銀行系統通訊錯誤！", ephemeral=True)

        if user_data['coin'] < bet:
            return await (interaction.followup.send if interaction.response.is_done() else interaction.response.send_message)("❌ 錢不夠！", ephemeral=True)

        self.bank.add_stats(interaction.guild.id, interaction.user.id, coin=-bet)
        self.bank.save_data()

        # 初始化牌組
        suits = ["♠️", "♥️", "♦️", "♣️"]
        ranks = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]
        deck = [f"{v}{s}" for s in suits for v in ranks]
        random.shuffle(deck)

        # 動態控制起手牌
        control = None
        try:
            bj_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "blackjack_control.json")
            if os.path.exists(bj_path):
                with open(bj_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                control = data.get(str(interaction.user.id))
        except Exception as e:
            print(f"[BJ控制] 開局讀取失敗: {e}")

        # 起手兩張牌必須完全隨機
        p_hand = [deck.pop(), deck.pop()]
        d_hand = [deck.pop(), deck.pop()]

        # 這裡的 calculate_hand 應該是你 Cog 裡原有的函式
        view = BlackjackView(interaction, p_hand, d_hand, deck, self.calculate_hand, self.bank, bet, self)
        
        # 檢查起手 blackjack (雙方前兩張)
        p_val = self.calculate_hand(p_hand)
        d_val_full = self.calculate_hand(d_hand)
        
        is_player_bj = (p_val == 21)
        is_dealer_bj = (d_val_full == 21)
        
        if is_player_bj or is_dealer_bj:
            # 直接結算
            payout = 0
            if is_player_bj and is_dealer_bj:
                msg, res_type, color = "🤝 雙方起手 BJ 平手！", 'draw', discord.Color.light_grey()
                payout = bet
                pnl_delta = 0
            elif is_player_bj:
                msg, res_type, color = "🎉 恭喜！起手 BlackJack (21點)！", 'win', discord.Color.gold()
                # 贏得 1.5倍 => 拿回本金(bet) + 贏(1.5*bet)
                payout = int(bet + (bet * 1.5))
                pnl_delta = int(bet * 1.5)
            else:
                msg, res_type, color = "👻 莊家起手 BlackJack！你輸了。", 'loss', discord.Color.red()
                payout = 0
                pnl_delta = -bet

            # 更新銀行與統計
            user_data = self.bank.add_stats(interaction.guild.id, interaction.user.id, coin=payout)
            user_data["blackjack_pnl"] = user_data.get("blackjack_pnl", 0) + pnl_delta
            user_data["blackjack_games"] = user_data.get("blackjack_games", 0) + 1
            if res_type == 'win':
                user_data["blackjack_wins"] = user_data.get("blackjack_wins", 0) + 1
            self.bank.save_data()

            # 顯示全手牌
            d_emojis = " ".join([view.get_card_emoji(c) for c in d_hand])
            p_emojis = " ".join([view.get_card_emoji(c) for c in p_hand])

            bj_pnl = user_data.get("blackjack_pnl", 0)
            pnl_str = f"{bj_pnl:+,}" if bj_pnl != 0 else "0"
            
            # 贏得/損失 醒目顯示
            if res_type == 'win':
                win_loss_line = f"✅ 贏得 {int(bet * 1.5):,} 💰"
            elif res_type == 'loss':
                win_loss_line = f"❌ 損失 {bet:,} 💰"
            else:
                win_loss_line = "🤝 平手 退回賭注"

            total_games = user_data.get("blackjack_games", 1)
            
            p_val_str = f"{p_val} 🔥" if p_val == 21 else f"{p_val}"
            d_val_str = f"{d_val_full} 🔥" if d_val_full == 21 else f"{d_val_full}"
            
            win_rate = (user_data.get("blackjack_wins", 0) / total_games * 100) if total_games > 0 else 0
            stats_line = f"➡️ 勝率 {win_rate:.1f}% 總場次 {total_games:,}"
            
            embed = discord.Embed(
                title="🎰 21點 遊戲結算 (Natural BJ)",
                description=(
                    f"### {msg}\n\n"
                    f"### {win_loss_line}\n\n"
                    f"{stats_line}\n\n"
                    f"**🎰 莊家手牌：**\n# {d_val_str} {d_emojis}\n\n"
                    f"**你的手牌：**\n# {p_val_str} {p_emojis}"
                ),
                color=color
            )
            embed.set_footer(text=f"下注: {bet:,} | 餘額: {user_data.get('coin', 0):,} | 總盈虧: {pnl_str}", icon_url=interaction.user.display_avatar.url)
            if BLACKJACK_AVATAR_URL:
                embed.set_thumbnail(url=BLACKJACK_AVATAR_URL)

            # 加上重玩按鈕 (清除 view 的 items 並加入 retry)
            view.clear_items()
            
            retry_btn = discord.ui.Button(label=f"再玩一局 (${bet:,})", style=discord.ButtonStyle.blurple, emoji="🔄")
            async def retry_callback(ri: discord.Interaction):
                if str(ri.user.id) != str(interaction.user.id): return
                await self.start_blackjack(ri, bet)
            retry_btn.callback = retry_callback
            view.add_item(retry_btn)

            double_bet = int(bet) * 2
            double_retry_btn = discord.ui.Button(label=f"雙倍下注 (${double_bet:,})", style=discord.ButtonStyle.danger, emoji="🔥")
            async def double_retry_callback(ri: discord.Interaction):
                if str(ri.user.id) != str(interaction.user.id): return
                await self.start_blackjack(ri, double_bet)
            double_retry_btn.callback = double_retry_callback
            view.add_item(double_retry_btn)
            
            # All In 按鈕
            user_balance = user_data.get('coin', 0)
            if user_balance > 0:
                all_in_btn = discord.ui.Button(label=f"All In (${user_balance:,})", style=discord.ButtonStyle.danger, emoji="🤑")
                async def all_in_callback(ri: discord.Interaction):
                    if str(ri.user.id) != str(interaction.user.id): return
                    # 重新獲取一次最新餘額
                    current_stats = self.bank.add_stats(ri.guild.id, ri.user.id, coin=0)
                    bal = current_stats['coin']
                    if bal <= 0:
                        return await ri.response.send_message("❌ 沒錢了還想梭哈？", ephemeral=True)
                    
                    # 確認視窗 View
                    confirm_view = discord.ui.View(timeout=60)
                    
                    yes_btn = discord.ui.Button(label="確定梭哈！", style=discord.ButtonStyle.danger, emoji="🔥")
                    async def yes_callback(cri: discord.Interaction):
                        final_stats = self.bank.add_stats(cri.guild.id, cri.user.id, coin=0)
                        final_bal = final_stats['coin']
                        if final_bal <= 0:
                            return await cri.response.send_message("❌ 沒錢了還想梭哈？", ephemeral=True)
                        await self.start_blackjack(cri, final_bal)

                    no_btn = discord.ui.Button(label="算了", style=discord.ButtonStyle.secondary, emoji="🌚")
                    async def no_callback(cri: discord.Interaction):
                        await cri.response.edit_message(content="已取消梭哈。", view=None)

                    yes_btn.callback = yes_callback
                    no_btn.callback = no_callback
                    confirm_view.add_item(yes_btn)
                    confirm_view.add_item(no_btn)

                    await ri.response.send_message(
                        f"⚠️ **高風險警示** ⚠️\n你確定要將目前所有財產 **${bal:,}** 全部投入下一局嗎？\n輸了就會變成 **$0** 喔！",
                        view=confirm_view,
                        ephemeral=True
                    )
                all_in_btn.callback = all_in_callback
                view.add_item(all_in_btn)

            if interaction.response.is_done():
                await interaction.followup.send(embed=embed, view=view)
            else:
                await interaction.response.send_message(embed=embed, view=view)
            return

        d_val = self.calculate_hand([d_hand[0]])
        d_val_str = f"{d_val} 🔥" if d_val == 21 else f"{d_val}"
        dealer_display = f"# {d_val_str} {view.get_card_emoji(d_hand[0])} {view.get_card_emoji(None, use_card_back=True)}"
        p_val = self.calculate_hand(p_hand)
        p_val_str = f"{p_val} 🔥" if p_val == 21 else f"{p_val}"
        p_emojis = " ".join([view.get_card_emoji(c) for c in p_hand])
        embed = discord.Embed(
            title="🕐 21點遊戲進行中",
            description=f"**莊家手牌：**\n{dealer_display}\n\n**你的手牌：**\n# {p_val_str} {p_emojis}",
            color=0x3498db
        )

        user_data = self.bank.add_stats(interaction.guild.id, interaction.user.id, coin=0)
        bj_pnl = user_data.get("blackjack_pnl", 0)
        pnl_str = f"{bj_pnl:+,}" if bj_pnl != 0 else "0"
        embed.set_footer(text=f"下注: {bet:,} | 餘額: {user_data.get('coin', 0):,} | 總盈虧: {pnl_str}", icon_url=interaction.user.display_avatar.url)
        if BLACKJACK_AVATAR_URL:
            embed.set_thumbnail(url=BLACKJACK_AVATAR_URL)

        if interaction.response.is_done():
            await interaction.followup.send(embed=embed, view=view)
        else:
            await interaction.response.send_message(embed=embed, view=view)

    # 股票查詢指令
    @app_commands.command(name="stock_search", description="查詢股票(目前僅限美股)")
    @app_commands.describe(股票代碼="請輸入美股代碼，例如 AAPL 或 NVDA")
    @app_commands.checks.cooldown(1, 3.0, key=lambda i: i.user.id)
    async def stock(self, interaction: discord.Interaction, 股票代碼: str):
        await interaction.response.defer()
        data, source = await self.get_stock_data(股票代碼.upper())

        if not data:
            await interaction.followup.send(f"❌ 找不到股票代碼 `{股票代碼}`")
            return

        color = 0x2ecc71 if data['change'] >= 0 else 0xe74c3c
        embed = discord.Embed(title=f"📈 {data['name']} ({data['ticker']})", color=color, timestamp=datetime.now())
        embed.add_field(name="當前價格", value=f"**{data['price']:.2f} {data['currency']}**", inline=True)
        embed.add_field(name="漲跌幅", value=f"{data['change']:+.2f} ({data['percent']:+.2f}%)", inline=True)
        embed.set_footer(text=f"來源: {source} | 更新時間: {data['update_time']}")
        await interaction.followup.send(embed=embed)
    async def get_stock_data(self, ticker):
        today = datetime.now().strftime("%Y-%m-%d")
        cache = self.load_stock_cache()

        # 檢查快取
        if today in cache and ticker in cache[today]:
            return cache[today][ticker], "JSON 快取"

        # 呼叫 API (Twelve Data)
        API_KEY = "7b125e135ebb41a89911571ba40e6f94" # 你的 Key
        url = f"https://api.twelvedata.com/quote?symbol={ticker}&apikey={API_KEY}"

        try:
            res = requests.get(url).json()
            # 台股自動修正邏輯
            if ("code" in res and res["code"] != 200) and ticker.isdigit():
                ticker_tpe = f"{ticker}:TWSE"
                res = requests.get(f"https://api.twelvedata.com/quote?symbol={ticker_tpe}&apikey={API_KEY}").json()
                ticker = ticker_tpe

            if "code" in res and res["code"] != 200:
                return None, None

            # 整理資料
            stock_info = {
                "name": res.get("name", ticker),
                "ticker": ticker,
                "price": float(res['close']),
                "change": float(res['change']),
                "percent": float(res['percent_change']),
                "currency": res.get("currency", "USD"),
                "update_time": datetime.now().strftime("%H:%M:%S")
            }

            # 更新快取
            if today not in cache: cache = {today: {}}
            cache[today][ticker] = stock_info
            self.save_stock_cache(cache)
            return stock_info, "Twelve Data API"
        except:
            return None, None

    # 購買股票
    @app_commands.command(name="stock_buy", description="購買股票並記錄成本")
    @app_commands.describe(股票代碼="股票代碼 (如: AAPL, NVDA)", 數量="購買的股數")
    @app_commands.guild_only()
    async def buy_stock(self, interaction: discord.Interaction, 股票代碼: str, 數量: int):
        if 數量 <= 0:
            await interaction.response.send_message("❌ 購買數量須大於 0", ephemeral=True)
            return

        await interaction.response.defer()
        bank = self.bot.get_cog('BankMod')
        data, source = await self.get_stock_data(股票代碼.upper())
        if not data:
            await interaction.followup.send(f"❌ 無法取得 `{股票代碼}` 的價格，交易取消。")
            return

        ticker = data['ticker']
        current_price = data['price']
        total_cost = int(current_price * 數量)
        gid, uid = str(interaction.guild.id), str(interaction.user.id)

        user_coin = bank.users.get(gid, {}).get(uid, {}).get("coin", 0)

        if user_coin < total_cost:
            await interaction.followup.send(f"❌ 金幣不足！需要 `{total_cost:,}`，你目前只有 `{user_coin:,}`。")
            return

        # 執行扣款
        bank.add_stats(gid, uid, coin=-total_cost)
        user_data = bank.users[gid][uid]

        # 初始化擴充欄位
        if "stocks" not in user_data: user_data["stocks"] = {}
        if "stock_costs" not in user_data: user_data["stock_costs"] = {}

        # 增加持股與累計成本
        user_data["stocks"][ticker] = user_data["stocks"].get(ticker, 0) + 數量
        user_data["stock_costs"][ticker] = user_data["stock_costs"].get(ticker, 0) + total_cost
        bank.save_data()

        embed = discord.Embed(title="✅ 買入成交", color=0x2ecc71, timestamp=datetime.now())
        embed.description = f"已購入 **{數量}** 股 **{data['name']}**"
        embed.add_field(name="成交單價", value=f"`{current_price}`", inline=True)
        embed.add_field(name="總計花費", value=f"`💰 {total_cost:,}`", inline=True)
        embed.set_footer(text=f"來源: {source}")
        await interaction.followup.send(embed=embed)

    # 查看投資組合
    @app_commands.command(name="stock_mine", description="查看投資組合")
    @app_commands.guild_only()
    async def portfolio(self, interaction: discord.Interaction):
        await interaction.response.defer()
        bank = self.bot.get_cog('BankMod')
        if not bank: return await interaction.followup.send("銀行系統異常。")

        gid, uid = str(interaction.guild.id), str(interaction.user.id)
        user_data = bank.users.get(gid, {}).get(uid, {})
        user_stocks = user_data.get("stocks", {})
        user_costs = user_data.get("stock_costs", {}) # 取得成本資料

        if not user_stocks:
            return await interaction.followup.send("💡 你目前手頭上沒有任何持股。")

        cache = self.load_stock_cache()
        today = datetime.now().strftime("%Y-%m-%d")
        daily_cache = cache.get(today, {})
        embed = discord.Embed(title=f"📊 {interaction.user.display_name} 的投資組合", color=0x3498db, timestamp=datetime.now())
        total_market_value = 0
        total_investment = 0
        for ticker, amount in user_stocks.items():
            stock_info = daily_cache.get(ticker)
            cost = user_costs.get(ticker, 0) # 該股票總投入成本
            total_investment += cost

            if stock_info:
                current_price = stock_info['price']
                market_value = current_price * amount
                total_market_value += market_value

                # 計算損益
                profit = market_value - cost
                profit_percent = (profit / cost * 100) if cost > 0 else 0

                # 決定符號與圖示
                indicator = "🔺" if profit >= 0 else "🔻"
                profit_text = f"{indicator} `{int(profit):+}` ({profit_percent:+.2f}%)"

                price_text = (
                    f"現價: `{current_price}` | 市值: `💰{int(market_value)}`\n"
                    f"淨收益: **{profit_text}**"
                )
            else:
                price_text = "*請先使用 /stock_search 更新報價以計算損益*"

            embed.add_field(name=f"📌 {ticker} ({amount} 股)", value=price_text, inline=False)

        # 總結算
        total_profit = total_market_value - total_investment
        total_profit_percent = (total_profit / total_investment * 100) if total_investment > 0 else 0
        profit_color = "🟢" if total_profit >= 0 else "🔴"

        summary_val = (
            f"💵 現金餘額: `{user_data.get('coin', 0):,}`\n"
            f"🏛️ 持股市值: `{int(total_market_value):,}`\n"
            f"📈 總盈虧: {profit_color} **`{int(total_profit):+}`** (`{total_profit_percent:+.2f}%`)"
        )
        embed.add_field(name="💰 資產總結", value=summary_val, inline=False)

        await interaction.followup.send(embed=embed)

    # 賣出股票指令
    @app_commands.command(name="stock_sell", description="賣出股票並結算收益")
    @app_commands.describe(股票代碼="請輸入股票代碼", 數量="請輸入賣出數量")
    @app_commands.guild_only()
    async def sell_stock(self, interaction: discord.Interaction, 股票代碼: str, 數量: int):
        if 數量 <= 0:
            await interaction.response.send_message("賣出數量必須大於 0！", ephemeral=True)
            return

        await interaction.response.defer()
        bank = self.bot.get_cog('BankMod')

        # 1. 取得最新股價
        data, source = await self.get_stock_data(股票代碼.upper())
        if not data:
            await interaction.followup.send(f"❌ 無法取得股票 `{股票代碼}` 的市價，交易取消。")
            return

        ticker = data['ticker']
        gid, uid = str(interaction.guild.id), str(interaction.user.id)

        # 2. 檢查持股
        user_data = bank.users.get(gid, {}).get(uid, {})
        user_stocks = user_data.get("stocks", {})

        # --- 核心修正：防禦性初始化 stock_costs ---
        if "stock_costs" not in user_data:
            user_data["stock_costs"] = {}

        current_hold = user_stocks.get(ticker, 0)
        if current_hold < 數量:
            await interaction.followup.send(f"❌ 持股不足！你手上的 `{ticker}` 只有 `{current_hold}` 股。")
            return

        # 3. 計算收益與成本扣除
        sell_price = data['price']
        total_revenue = int(sell_price * 數量)

        # 取得該股票的原始總成本
        original_total_cost = user_data["stock_costs"].get(ticker, 0)

        # 成本扣除額 = (賣出數量 / 總持股) * 總成本
        # 加上 max(1, ...) 避免除以 0 錯誤
        cost_to_remove = int((數量 / max(1, current_hold)) * original_total_cost)

        # 4. 更新資料
        user_data["stocks"][ticker] -= 數量
        user_data["stock_costs"][ticker] = max(0, original_total_cost - cost_to_remove)

        # 如果持股歸零，刪除紀錄
        if user_data["stocks"][ticker] <= 0:
            user_data["stocks"].pop(ticker, None)
            user_data["stock_costs"].pop(ticker, None)

        # 增加金幣並存檔
        bank.add_stats(gid, uid, coin=total_revenue)
        bank.save_data()

        # 5. 回傳結算 (美化面板)
        embed = discord.Embed(title="📉 賣出成交", color=0xe67e22, timestamp=datetime.now())
        embed.add_field(name="股票", value=f"{data['name']} ({ticker})", inline=True)
        embed.add_field(name="賣出數量", value=f"{數量} 股", inline=True)
        embed.add_field(name="成交單價", value=f"{sell_price} {data['currency']}", inline=True)
        embed.add_field(name="獲得金幣", value=f"💰 **{total_revenue:,}**", inline=False)

        # 計算這筆賣出的預估損益 (參考用)
        estimated_profit = total_revenue - cost_to_remove
        profit_indicator = "🟢" if estimated_profit >= 0 else "🔴"
        embed.add_field(name="本次賣出損益", value=f"{profit_indicator} `{estimated_profit:+}`", inline=True)

        embed.set_footer(text=f"餘額：{user_data['coin']:,} | 剩餘持股：{user_data['stocks'].get(ticker, 0):,}")

        await interaction.followup.send(embed=embed)

    # 只有特定 ID 才能解鎖內容
    @app_commands.command(name="secret", description="丟出一個只有特定人才能解鎖的訊息")
    @app_commands.guild_only()
    async def drop_secret(self, interaction: discord.Interaction):
        await interaction.response.send_modal(SecretModal())

    # 管理員專用：新增/移除授權觀看隱藏Msg
    @app_commands.command(name="manage_secret", description="【Admin】Manage the secret message access list")
    @app_commands.describe(action="add or remove", target="User")
    async def manage_secret(self, interaction: discord.Interaction, action: str, target: discord.Member):
        YOUR_ID = 1170599058717560875  # <--- 請改為你的 ID
        if interaction.user.id != YOUR_ID:
            await interaction.response.send_message("❌ You are not the Admin.", ephemeral=True)
            return

        current_list = load_allowed_users()
        target_id = str(target.id)

        if action.lower() == "add":
            if target_id not in current_list:
                current_list.append(target_id)
                save_allowed_users(current_list)
                await interaction.response.send_message(f"✅ 已將 {target.display_name} 加入授權名單。")
            else:
                await interaction.response.send_message(f"ℹ️ {target.display_name} 已經在名單中了。")

        elif action.lower() == "remove":
            if target_id in current_list:
                current_list.remove(target_id)
                save_allowed_users(current_list)
                await interaction.response.send_message(f"🈲 已將 {target.display_name} 從授權名單移除。")
            else:
                await interaction.response.send_message(f"ℹ️ 名單中找不到 {target.display_name}。")

    @app_commands.command(name="announce", description="【Admin】發送系統公告到指定文字頻道")
    @app_commands.guild_only()
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(channel="要發送公告的文字頻道", content="公告內容")
    async def announce(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
        content: str
    ):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("❌ 你沒有管理員權限。", ephemeral=True)

        if not content.strip():
            return await interaction.response.send_message("❌ 公告內容不能是空白。", ephemeral=True)

        embed = discord.Embed(description=f"# 📢 系統公告\n\n{content}", color=0xff0000)
        embed.set_author(name="NuSo 系統核心", icon_url=self.bot.user.avatar.url if self.bot.user and self.bot.user.avatar else None)
        embed.timestamp = datetime.now()

        try:
            await channel.send(embed=embed)
            await interaction.response.send_message(f"✅ 公告已發送至 {channel.mention}", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("❌ 我在該頻道沒有發送訊息權限。", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ 發送失敗：{e}", ephemeral=True)

    # 個人資料指令
    @app_commands.command(name="profile", description="查看你在本伺服器的個人資料與資產概況")
    @app_commands.guild_only()
    async def profile(self, interaction: discord.Interaction):
        await interaction.response.defer() # 因為要計算股票市值，建議先 defer

        gid, uid = str(interaction.guild.id), str(interaction.user.id)

        # 1. 取得銀行資料 (錢、等級、經驗值)
        bank = self.bot.get_cog('BankMod')
        if not bank:
            return await interaction.followup.send("❌ 銀行系統模組未啟動。")

        user_data = bank.add_stats(interaction.guild.id, interaction.user.id, coin=0)

        coin = user_data.get("coin", 0)
        exp = user_data.get("exp", 0)

        # 2. 取得股票資料與計算市值
        user_stocks = user_data.get("stocks", {})
        total_stock_value = 0
        cache = self.load_stock_cache()
        today = datetime.now().strftime("%Y-%m-%d")
        daily_cache = cache.get(today, {})

        stock_summary = ""
        if user_stocks:
            for ticker, info in user_stocks.items():
                qty = info.get("qty", 0)
                current_price = daily_cache.get(ticker)
                if current_price is not None:
                    value = qty * current_price
                    total_stock_value += value
                    stock_summary += f"`{ticker}` × {qty} = `${value:,.0f}`\n"
                else:
                    stock_summary += f"`{ticker}` × {qty} = (價格抓取失敗)\n"
        else:
            stock_summary = "目前沒有持股"

        # 3. 計算總資產
        net_worth = coin + total_stock_value

        # 4. 製作 Embed
        embed = discord.Embed(
            title=f"📊 {interaction.user.display_name} 的個人資料",
            color=0x9b59b6
        )
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        embed.add_field(name="💰 現金", value=f"`${coin:,}`", inline=True)
        embed.add_field(name="⭐ 經驗值", value=f"`{exp:,}`", inline=True)
        embed.add_field(name="📈 股票總市值", value=f"`${total_stock_value:,.0f}`", inline=True)
        embed.add_field(name="💎 總資產", value=f"**`${net_worth:,.0f}`**", inline=False)
        embed.add_field(name="📦 持股明細", value=stock_summary[:1024], inline=False)
        embed.set_footer(text=f"伺服器：{interaction.guild.name} | 查詢時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        await interaction.followup.send(embed=embed)
    @app_commands.command(name="spin", description="花費金幣進行幸運大轉盤 (下注 5000)")
    @app_commands.guild_only()
    async def spin(self, interaction: discord.Interaction):
        bank = self.bot.get_cog('BankMod')
        if not bank: return await interaction.response.send_message("❌ 銀行系統未啟動。")

        # 1. 檢查餘額 (固定每次下注 5000)
        bet = 5000
        user_data = bank.add_stats(interaction.guild.id, interaction.user.id, coin=0)
        if user_data["coin"] < bet:
            return await interaction.response.send_message(f"❌ 你的餘額不足！需要 `{bet:,}` 金幣。", ephemeral=True)

        # 2. 扣除賭金
        user_data["coin"] -= bet

        # 3. 轉盤邏輯
        items = ["🍎","🍋‍🟩","🍎", "🍋","🍋‍🟩","🍋", "🍇", "💎", "⭐"]
        result = [random.choice(items) for _ in range(3)]
        res_str = " | ".join(result)

        # 判定獎勵
        win_amount = 0
        if result[0] == result[1] == result[2]:
            if result[0] == "💎": win_amount = 100000 # 三個鑽石大獎
            elif result[0] == "⭐": win_amount = 5000
            else: win_amount = 50000
            msg = "🎊 **超級大獎！** 🎊"
        elif result[0] == result[1] or result[1] == result[2] or result[0] == result[2]:
            win_amount = 11000 # 兩兩相同小獎
            msg = "✨ **小獎！** ✨"
        else:
            msg = "💀 **可惜沒中獎，下次加油！**"

        # 4. 發放獎勵
        user_data["coin"] += win_amount
        bank.save_data()

        # 5. 製作結果 Embed
        embed = discord.Embed(title="🎡 NuSo 幸運轉盤", color=0xff8c00)
        embed.add_field(name="🎰 轉盤結果", value=f"```\n[ {res_str} ]\n```", inline=False)
        embed.add_field(name="結果", value=msg, inline=True)
        if win_amount > 0:
            embed.add_field(name="獲得獎金", value=f"💰 `{win_amount:,}`", inline=True)
        embed.set_footer(text=f"消耗: {bet:,} | 剩餘餘額: {user_data['coin']:,}")
        await interaction.response.send_message(embed=embed)

    # 天氣查詢指令
    @app_commands.command(name="weather", description="查詢城市天氣，可點選按鈕查看明天預報")
    @app_commands.describe(city="請輸入城市名稱 (例如: Taipei)")
    async def weather(self, interaction: discord.Interaction, city: str):
        api_key = "b171e1ded37b0ad51a1a33157b263ea9"
        # 必須使用 forecast API
        url = f"http://api.openweathermap.org/data/2.5/forecast?q={city}&appid={api_key}&units=metric&lang=zh_tw"

        await interaction.response.defer()

        cwa_map = {
            "Taipei": "63", "New Taipei": "65", "Taoyuan": "68", "Taichung": "66",
            "Tainan": "67", "Kaohsiung": "64", "Keelung": "10017", "Hsinchu": "10018",
            "Miaoli": "10005", "Changhua": "10007", "Nantou": "10008", "Yunlin": "10009",
            "Chiayi": "10010", "Pingtung": "10013", "Yilan": "10002", "Hualien": "10015",
            "Taitung": "10014", "Penghu": "10016", "Kinmen": "09020", "Lienchiang": "09007"
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    city_name = data['city']['name']

                    # 決定氣象局跳轉 URL
                    cwa_id = "index"
                    for key, val in cwa_map.items():
                        if key.lower() in city.lower():
                            cwa_id = f"County.html?CID={val}"
                            break
                    cwa_url = f"https://www.cwa.gov.tw/V8/C/W/County/{cwa_id}"

                    # 建立控制面板
                    view = WeatherView(data, city_name, cwa_url)

                    # 預設發送今日 (day_index=0) 的 Embed
                    embed = view.create_weather_embed(0)
                    await interaction.followup.send(embed=embed, view=view)
                else:
                    await interaction.followup.send(f"❌ 找不到城市：`{city}`，請確認英文拼字。", ephemeral=True)

    # 播放音樂
    @app_commands.command(name="play", description="播放 YouTube 音樂")
    @app_commands.describe(search="輸入歌名或網址")
    async def play(self, interaction: discord.Interaction, search: str):
        if not interaction.user.voice:
            return await interaction.response.send_message("❌ 你必須先進入語音頻道！", ephemeral=True)

        await interaction.response.defer()
        guild_id = interaction.guild.id

        # 1. 取得 YouTube 資訊
        with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
            try:
                info = ydl.extract_info(search, download=False)
                if 'entries' in info: info = info['entries'][0]
            except Exception as e:
                return await interaction.followup.send(f"❌ 搜尋失敗: {e}")

        # 2. 初始化清單並排隊
        if guild_id not in self.queues:
            self.queues[guild_id] = []

        vc = interaction.guild.voice_client
        if not vc:
            vc = await interaction.user.voice.channel.connect()

        if vc.is_playing() or vc.is_paused():
            # 正在播歌，排進下一首
            self.queues[guild_id].append(info)
            await interaction.followup.send(f"✅ 已加入待播放清單：**{info['title']}** (目前排第 {len(self.queues[guild_id])} 位)")
        else:
            # 沒在播歌，加入清單並啟動播放
            self.queues[guild_id].append(info)
            await self.play_next(interaction, guild_id)
            await interaction.followup.send("🎶 開始播放音樂！", ephemeral=True)
    async def play_next(self, interaction, guild_id):
        if guild_id in self.queues and len(self.queues[guild_id]) > 0:
            info = self.queues[guild_id].pop(0)
            vc = interaction.guild.voice_client
            if not vc: return

            source = await discord.FFmpegOpusAudio.from_probe(info['url'], **FFMPEG_OPTIONS)
            # after 參數會在歌曲結束時自動執行下一首
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

    # 搶銀行指令
    @app_commands.command(name="rob_bank", description="發起一場大型搶劫行動（主持人確認後開始）")
    @app_commands.guild_only()
    async def rob_bank_cmd(self, interaction: discord.Interaction):
        uid = interaction.user.id
        cost = 10000
        # 1. 檢查玩家是否已在行動中
        if uid in self.active_robbers:
            return await interaction.response.send_message("❌ 你已經在隊伍中或行動中，不能重複發起！", ephemeral=True)

        bank = self.bot.get_cog('BankMod')
        user_data = bank.add_stats(interaction.guild.id, interaction.user.id, coin=0)

        if user_data['coin'] < cost:
            return await interaction.response.send_message(f"❌ 錢不夠支付準備金 {cost:,}！", ephemeral=True)

        # 2. 將發起人加入鎖定名單
        self.active_robbers.add(uid)

        # 3. 傳入 self (Cog 實例) 給 View，以便 View 操作 active_robbers
        view = RobBankView(interaction, self, cost)
        embed = discord.Embed(
            title="🏦 銀行大劫案：計畫啟動",
            description=(
                f"**發起人：** {interaction.user.mention}\n"
                f"**準備金：** `${cost:,}`\n\n"
                f"👥 **已加入成員 (1 人)：**\n• {interaction.user.display_name}\n\n"
                f"📋 **主持人確認人數後按「確認開始」按鈕**"
            ),
            color=0x2b2d31
        )
        await interaction.response.send_message(embed=embed, view=view)
    async def start_robbery_logic(self, interaction, participants):
        bank = self.bot.get_cog('BankMod')
        if not bank: return

        gid = interaction.guild.id
        cost = 10000
        fail_fee = 50000
        count = len(participants)

        try:
            # 1. 扣錢
            for p in participants:
                bank.add_stats(gid, p.id, coin=-cost)
            bank.save_data()

            # 2. 開始劇情
            current_content = f"👥 **參與成員：** {', '.join([p.display_name for p in participants])}\n🎬 **行動代號：百萬劫案**"
            try:
                drama_msg = await interaction.channel.send(current_content)
            except discord.Forbidden:
                # 這裡如果發生權限錯誤，也要確保能進到 finally 解鎖，所以用 return 沒關係
                return await interaction.followup.send("⚠️ 機器人缺少在該頻道『傳送訊息』的權限！", ephemeral=True)

            # 3. 跑劇情
            stages = ['prep', 'entry', 'vault_drill', 'vault_open', 'loot', 'police', 'skirmish', 'escape']
            for stage in stages:
                await asyncio.sleep(2.0)
                lucky_guy = random.choice(participants).display_name
                plot_template = random.choice(ROB_PLOTS[stage])
                new_line = f"\n> {plot_template.format(user=lucky_guy)}"
                current_content += new_line
                try:
                    await drama_msg.edit(content=current_content)
                except:
                    break
                if stage in ['vault_drill', 'skirmish']:
                    await asyncio.sleep(1.5)

            # 4. 結算
            success_chance = min(5 + ((count - 1) * 10), 50)
            is_success = random.randint(1, 100) <= success_chance
            await asyncio.sleep(3)

            if is_success:
                total_loot = 1000000 + (count - 1) * 150000
                each_get = total_loot // count
                for p in participants:
                    bank.add_stats(gid, p.id, coin=each_get)

                res_embed = discord.Embed(
                    title="🏆 劫案傳奇：成功撤離！",
                    description=f"你們衝出了包圍網！\n💰 **分贓總額：** `$1,000,000`\n🧧 **每人入帳：** `${each_get:,}`",
                    color=0x2ecc71
                )
                res_embed.set_image(url="https://blog.hamibook.com.tw/wp-content/uploads/2020/01/%E7%B6%93%E7%90%86%E4%BA%BA%E7%89%B9%E5%88%8A%E7%AC%AC30%E6%9C%9Fb01.jpg")
            else:
                for p in participants:
                    bank.add_stats(gid, p.id, coin=-fail_fee)
                res_embed = discord.Embed(
                    title="🚔 灰頭土臉：全軍覆沒！",
                    description=f"醒來時，你們已經在押運車上...\n❌ **每人損失保釋金：** `${fail_fee:,}`",
                    color=0xe74c3c
                )
                res_embed.set_image(url="https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSM6XWVCnEiOfbARjZn-0lzDo3PkDqSu4gjFA&s")

            bank.save_data()
            p_mentions = ",".join([p.mention for p in participants])
            await interaction.channel.send(content=p_mentions, embed=res_embed)

        except Exception as e:
            # 這是捕捉 Try 區塊內所有可能的意外錯誤
            print(f"🚨 搶劫邏輯發生錯誤: {e}")
            await interaction.channel.send(f"🚨 行動中途發生意外（系統錯誤），計畫被迫中止！")

        finally:
            # 無論成功、失敗或報錯，最後一定會跑這裡解除玩家鎖定
            for p in participants:
                if p.id in self.active_robbers:
                    self.active_robbers.remove(p.id)
            print("🔓 搶案流程結束，已釋放所有參與者狀態。")

    # 存入金庫

    @app_commands.command(name="redpacket", description="發送紅包")
    @app_commands.describe(total="總金額", count="總共幾包(3-11包)")
    @app_commands.guild_only()
    async def redpacket(self, interaction: discord.Interaction, total: int, count: int):
        if count < 3 or count > 11:
            await interaction.response.send_message("紅包數量必須在 3 到 11 包之間！", ephemeral=True)
            return
            
        if total < count * 50:
            await interaction.response.send_message(f"金額太小啦！發 {count} 包至少需要 {count * 50} 💰！", ephemeral=True)
            return

        bank = getattr(self.bot, "get_cog", lambda x: None)('BankMod')
        if not bank:
            await interaction.response.send_message("銀行系統發生錯誤，無法存取！", ephemeral=True)
            return

        gid = str(interaction.guild.id)
        uid = str(interaction.user.id)
        
        if gid not in bank.users or uid not in bank.users[gid]:
            await interaction.response.send_message("你的銀行帳戶未建立！請先賺點錢吧。", ephemeral=True)
            return
            
        balance = bank.users[gid][uid].get('coin', 0)
            
        if balance < total:
            await interaction.response.send_message(f"你的現金（{balance} 💰）不夠發 {total} 的紅包哦！", ephemeral=True)
            return
            
        # 扣除紅包總金額
        bank.users[gid][uid]['coin'] -= total
        bank.save_data()

        # 生成紅包列
        packets = [0] * count
        
        # 獨拿 51% (資本家)
        big_amt = int(total * 0.51)
        
        # 只拿 1.5%~2% (窮光蛋)
        small_pct = random.uniform(0.015, 0.02)
        small_amt = max(1, int(total * small_pct))
        
        # 剩下的至少 5%
        min_rest_amt = int(total * 0.05)
        
        indices = list(range(count))
        random.shuffle(indices)
        
        packets[indices[0]] = big_amt
        packets[indices[1]] = small_amt
        
        rest_indices = indices[2:]
        for idx in rest_indices:
            packets[idx] = min_rest_amt
            
        remaining_total = total - sum(packets)
        
        if remaining_total > 0 and rest_indices:
            # 將剩餘的金額隨機切割
            cuts = [random.random() for _ in rest_indices]
            total_cuts = sum(cuts)
            bonus = [int(remaining_total * (c / total_cuts)) for c in cuts]
            
            for i, idx in enumerate(rest_indices):
                packets[idx] += bonus[i]
                
            # 將因強制整數導致的殘餘差異全部加進最後一份
            diff = total - sum(packets)
            packets[rest_indices[-1]] += diff
            
        random.shuffle(packets)

        # 這裡會使用稍早引入的 RedPacketView
        view = RedPacketView(self.bot, interaction.user, packets, total)
        embed = discord.Embed(
            title=f"🧧 {interaction.user.display_name} 發了一個大紅包！",
            description=f"總金額: `{total}` 💰\n剩餘金額: `{total}` 💰\n數量: `{count}` 包\n\n手刀點擊下方紅包領取！",
            color=0xff0000
        )
        
        await interaction.response.send_message(embed=embed, view=view)
        try:
            view.message = await interaction.original_response()
        except:
            pass

    @app_commands.command(name="deposit", description="定存系統：開單、查詢、到期領回")
    @app_commands.choices(action=[
        app_commands.Choice(name="📝 開定存", value="open"),
        app_commands.Choice(name="📋 查定存", value="status"),
        app_commands.Choice(name="💸 領到期", value="claim")
    ])
    @app_commands.describe(action="操作類型", amount="定存本金（開定存時必填）", days="定存天數（1~7，開定存時必填）")
    @app_commands.guild_only()
    async def deposit(
        self,
        interaction: discord.Interaction,
        action: app_commands.Choice[str],
        amount: int = 0,
        days: app_commands.Range[int, 1, 7] = 7,
    ):

        bank_cog = self.bot.get_cog('BankMod')
        if not bank_cog:
            return await interaction.response.send_message("❌ 系統錯誤：找不到金庫模組！", ephemeral=True)

        user_data = bank_cog.add_stats(interaction.guild.id, interaction.user.id)
        if "fixed_deposits" not in user_data or not isinstance(user_data.get("fixed_deposits"), list):
            user_data["fixed_deposits"] = []

        if action.value == "open":
            if amount <= 0:
                return await interaction.response.send_message("❌ 定存本金必須大於 0！", ephemeral=True)

            current_cash = user_data.get("coin", 0)
            if current_cash < amount:
                return await interaction.response.send_message(
                    f"❌ 你手上的現金不足！(目前持有: `${current_cash:,}`)",
                    ephemeral=True
                )

            rate = self._fixed_deposit_rate(int(days))
            now = datetime.now()
            mature_at = now + timedelta(days=int(days))

            user_data["coin"] -= amount
            user_data["fixed_deposits"].append({
                "principal": int(amount),
                "term_days": int(days),
                "rate": rate,
                "opened_at": now.isoformat(),
                "mature_at": mature_at.isoformat(),
            })
            bank_cog.save_data()

            expected_interest = int(amount * rate)
            expected_total = int(amount + expected_interest)
            embed = discord.Embed(title="🏦 定存開單成功", color=0x2ecc71)
            embed.add_field(name="💰 本金", value=f"`${amount:,}`", inline=True)
            embed.add_field(name="📆 期數", value=f"`{int(days)}` 天", inline=True)
            embed.add_field(name="📈 利率", value=f"`{rate*100:.2f}%`", inline=True)
            embed.add_field(name="⏰ 到期時間", value=f"<t:{int(mature_at.timestamp())}:F>", inline=False)
            embed.add_field(name="🧾 預估利息", value=f"`${expected_interest:,}`", inline=True)
            embed.add_field(name="💎 到期可領", value=f"`${expected_total:,}`", inline=True)
            embed.add_field(name="👜 目前現金", value=f"`${user_data['coin']:,}`", inline=False)
            return await interaction.response.send_message(embed=embed)

        if action.value == "claim":
            now = datetime.now()
            matured = []
            pending = []
            for item in user_data.get("fixed_deposits", []):
                mature_at = self._parse_fd_time(item.get("mature_at", ""))
                if mature_at and mature_at <= now:
                    matured.append(item)
                else:
                    pending.append(item)

            if not matured:
                return await interaction.response.send_message("❌ 目前沒有已到期的定存。", ephemeral=True)

            payout_total = 0
            interest_total = 0
            principal_total = 0
            for item in matured:
                principal = int(item.get("principal", 0))
                rate = float(item.get("rate", 0.0))
                interest = int(principal * rate)
                payout = principal + interest
                principal_total += principal
                interest_total += interest
                payout_total += payout

            user_data["coin"] += payout_total
            user_data["fixed_deposits"] = pending
            bank_cog.save_data()

            embed = discord.Embed(title="💸 定存領回成功", color=0x3498db)
            embed.add_field(name="📦 到期筆數", value=f"`{len(matured)}`", inline=True)
            embed.add_field(name="💰 本金合計", value=f"`${principal_total:,}`", inline=True)
            embed.add_field(name="🧾 利息合計", value=f"`${interest_total:,}`", inline=True)
            embed.add_field(name="🎉 本次入帳", value=f"`${payout_total:,}`", inline=False)
            embed.add_field(name="👜 目前現金", value=f"`${user_data['coin']:,}`", inline=False)
            return await interaction.response.send_message(embed=embed)

        deposits = user_data.get("fixed_deposits", [])
        if not deposits:
            return await interaction.response.send_message("📭 目前沒有任何定存單。", ephemeral=True)

        now = datetime.now()
        sorted_items = sorted(
            deposits,
            key=lambda x: self._parse_fd_time(x.get("mature_at", "")) or datetime.max
        )
        lines = []
        total_principal = 0
        total_expected = 0
        for idx, item in enumerate(sorted_items[:10], 1):
            principal = int(item.get("principal", 0))
            rate = float(item.get("rate", 0.0))
            mature_at = self._parse_fd_time(item.get("mature_at", ""))
            expected = principal + int(principal * rate)
            total_principal += principal
            total_expected += expected
            if mature_at:
                if mature_at <= now:
                    state = "已到期"
                else:
                    state = f"<t:{int(mature_at.timestamp())}:R>"
            else:
                state = "時間資料異常"
            lines.append(f"`#{idx}` 本金 `${principal:,}` → 到期 `${expected:,}` | {state}")

        desc = "\n".join(lines)
        if len(sorted_items) > 10:
            desc += f"\n... 其餘 `{len(sorted_items)-10}` 筆未顯示"

        embed = discord.Embed(title="📋 定存清單", description=desc, color=0xf1c40f)
        embed.add_field(name="📦 筆數", value=f"`{len(sorted_items)}`", inline=True)
        embed.add_field(name="💰 本金總計", value=f"`${total_principal:,}`", inline=True)
        embed.add_field(name="💎 預估到期總額", value=f"`${total_expected:,}`", inline=True)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # 從銀行提領
    @app_commands.command(name="withdraw", description="從金庫提領現金到身上")
    @app_commands.guild_only()
    async def withdraw(self, interaction: discord.Interaction, amount: int):
        if amount <= 0:
            return await interaction.response.send_message("❌ 提領金額必須大於 0！", ephemeral=True)

        # --- 跨模組抓取 BankMod ---
        bank_cog = self.bot.get_cog('BankMod')
        if not bank_cog:
            return await interaction.response.send_message("❌ 系統錯誤：找不到金庫模組！", ephemeral=True)

        user_data = bank_cog.add_stats(interaction.guild.id, interaction.user.id)

        # 檢查存款
        current_bank = user_data.get("bank_balance", 0)
        if current_bank < amount:
            return await interaction.response.send_message(f"❌ 金庫存款不足！(目前存款: `${current_bank:,}`)", ephemeral=True)

        # 執行轉帳
        user_data["bank_balance"] -= amount
        user_data["coin"] += amount

        # 呼叫 bank_cog 的存檔
        bank_cog.save_data()

        embed = discord.Embed(title="💵 現金提領成功", color=0x3498db)
        embed.add_field(name="💰 提領金額", value=f"`${amount:,}`")
        embed.add_field(name="🏧 剩餘存款", value=f"`${user_data['bank_balance']:,}`")
        embed.add_field(name="👜 目前持有現金", value=f"`${user_data['coin']:,}`")
        await interaction.response.send_message(embed=embed)

    # 轉帳
    @app_commands.command(name="transfer", description="轉帳現金給其他玩家 (手續費 3%)")
    @app_commands.describe(user="收錢的對象", amount="要轉的金額")
    @app_commands.guild_only()
    async def transfer(self, interaction: discord.Interaction, user: discord.Member, amount: int):
        if amount <= 0:
            return await interaction.response.send_message("❌ 金額必須大於 0", ephemeral=True)
        if user.id == interaction.user.id:
            return await interaction.response.send_message("❌ 不能轉錢給自己", ephemeral=True)
        if user.bot:
            return await interaction.response.send_message("❌ 不能轉錢給機器人", ephemeral=True)

        bank = self.bot.get_cog('BankMod')
        user_data = bank.add_stats(interaction.guild.id, interaction.user.id)

        # 計算費用
        fee = int(amount * 0.03)
        total_cost = amount + fee

        if user_data["coin"] < total_cost:
            return await interaction.response.send_message(f"❌ 餘額不足！你需要 `${total_cost:,}` (含手續費)，但目前只有 `${user_data['coin']:,}`", ephemeral=True)

        # 製作確認介面 (對應圖片 2)
        embed = discord.Embed(title="💸 確認轉錢", color=0xf39c12) # 橘色邊框
        embed.description = f"您確定要轉錢給 {user.mention} 嗎？\n\n**轉錢詳情**"

        embed.add_field(name="轉帳金額", value=f"`{amount:,}` 💰", inline=False)
        embed.add_field(name="手續費 (3%)", value=f"`{fee:,}` 💰", inline=False)
        embed.add_field(name="您需支付", value=f"`{total_cost:,}` 💰", inline=False)
        embed.add_field(name="對方收到", value=f"`{amount:,}` 💰", inline=False)
        embed.add_field(name="您的當前餘額", value=f"`{user_data['coin']:,}` 💰", inline=False)
        embed.add_field(name="轉帳後餘額", value=f"`{user_data['coin'] - total_cost:,}` 💰", inline=False)

        embed.set_footer(text="請仔細確認轉錢資訊後再操作。")

        view = TransferView(self.bot, interaction.user, user, amount, fee, total_cost, bank)
        await interaction.response.send_message(embed=embed, view=view)

    # 釣魚
    @app_commands.command(name="fish", description="開啟釣魚管理面板（出海、收成都在這裡！）")
    @app_commands.guild_only()
    async def fish(self, interaction: discord.Interaction):
        """主流程分流，具體行為分派到獨立方法"""
        uid = interaction.user.id
        now = datetime.now()
        all_fishers = self.get_all_fishers()
        uid_str = str(uid)
        # 狀態分流
        if uid_str in all_fishers:
            status = all_fishers[uid_str]
            end_time = status.get("end_time")
            if isinstance(end_time, str):
                try:
                    end_time = datetime.fromisoformat(end_time)
                except Exception:
                    pass
            if end_time and now >= end_time:
                await self.finish_fishing(interaction, uid_str)
                bank = self.bot.get_cog('BankMod')
                user_data = bank.add_stats(interaction.guild.id, interaction.user.id) if bank else {}
                boat_lv = user_data.get("boat_level", 1)
                rod_lv = user_data.get("rod_level", 1)
                last_times = status.get("times", 1)
                hub_view = FishingHubView(self, interaction.user.id, interaction.guild.id, boat_lv, rod_lv, default_times=last_times)
                embed = hub_view._generate_embed()
                await interaction.followup.send(content="**✅ 上次漁獲已收成！要再次派遣船隻出海嗎？**", embed=embed, view=hub_view)
                return
            if end_time and now < end_time:
                remaining = end_time - now
                rm, rs = divmod(int(remaining.total_seconds()), 60)
                rh, rm = divmod(rm, 60)
                if rh > 0:
                    remain_str = f"{rh}時{rm}分{rs}秒"
                elif rm > 0:
                    remain_str = f"{rm}分{rs}秒"
                else:
                    remain_str = f"{rs}秒"
                active_view = FishActiveView(self, uid)
                embed = discord.Embed(title="🎣 釣魚任務執行中", color=0x3498db)
                embed.description = (
                    f"👤 **釣客：** <@{uid}>\n"
                    f"🚤 **漁船等級：** `Lv.{status.get('boat_level', '?')}`\n"
                    f"🎣 **魚竿等級：** `Lv.{status.get('rod_level', '?')}`\n"
                    f"🔔 **預計回港：** `{end_time.strftime('%H:%M:%S')}`\n"
                    f"⏳ **剩餘時間：** `{remain_str}`\n"
                    f"🎯 **釣魚次數：** `{status.get('times', '?')}` 次"
                )
                await interaction.response.send_message(embed=embed, view=active_view)
                return
        bank = self.bot.get_cog('BankMod')
        user_data = bank.add_stats(interaction.guild.id, interaction.user.id) if bank else {}
        boat_lv = user_data.get("boat_level", 1)
        rod_lv = user_data.get("rod_level", 1)
        hub_view = FishingHubView(self, interaction.user.id, interaction.guild.id, boat_lv, rod_lv)
        embed = hub_view._generate_embed()
        await interaction.response.send_message(embed=embed, view=hub_view)
    async def finish_fishing(self, ctx, user_id_str):
        """結算釣魚，顯示 UI、給錢、清除紀錄（可供 /fish 與 on_ready 共用）"""
        all_fishers = self.get_all_fishers()
        data = all_fishers.get(user_id_str)
        if not data:
            return
        
        # 初始化變數
        level_ups = 0
        current_level = 1
        total_skill_exp = 0
        prev_level = 1
        prev_exp = 0
        current_exp = 0
        
        # 發錢並計算技能經驗
        bank = self.bot.get_cog('BankMod')
        if bank:
            try:
                user_data = bank.add_stats(data.get("guild_id"), int(user_id_str), coin=data.get("total_reward", 0))
                
                # 技能經驗改為平滑成長：避免高次數一次滿等
                times = max(1, int(data.get("times", 1)))
                rarity_counts = data.get('rarity_counts', {})

                # 基礎經驗：每 100 竿約 1 EXP（5000 竿約 50 EXP）
                base_exp = max(1, times // 100)

                # 稀有加成改為「每 N 隻 +1」，避免依次數線性爆衝
                rarity_bonus = 0
                rarity_bonus += rarity_counts.get('傳說', 0) // 80
                rarity_bonus += rarity_counts.get('史詩', 0) // 100
                rarity_bonus += rarity_counts.get('稀有', 0) // 120

                # 單次上限，防止異常資料導致暴衝
                total_skill_exp = min(120, base_exp + rarity_bonus)
                
                # 升級邏輯
                current_level = user_data.get("fish_skill_level", 1)
                current_exp = user_data.get("fish_skill_exp", 0)
                prev_level = current_level
                prev_exp = current_exp
                
                user_data["fish_skill_exp"] = current_exp + total_skill_exp
                
                # 每級需要 100 經驗，最多升到 20 級
                level_ups = 0
                while user_data["fish_skill_exp"] >= 100 and current_level < 20:
                    user_data["fish_skill_exp"] -= 100
                    current_level += 1
                    level_ups += 1
                
                user_data["fish_skill_level"] = current_level

                # 滿等後不再累加經驗，避免數值無限膨脹
                if current_level >= 20:
                    user_data["fish_skill_exp"] = 100
                current_exp = user_data.get("fish_skill_exp", 0)
                
                print(f"✅ 用戶 {user_id_str} - 技能經驗 +{total_skill_exp} (等級 {current_level}, 剩餘 EXP {user_data['fish_skill_exp']})")
                bank.save_data()
            except Exception as e:
                print(f"⚠️ 結算時寫入銀行失敗: {e}")
        
        # 刪除紀錄
        self.remove_fisher(user_id_str)
        
        # 發送 UI
        await self._send_fishing_embed(ctx, 'result', {
            'user_name': data.get('user_name'),
            'user_id': user_id_str,
            'rarity_counts': data.get('rarity_counts', {}),
            'total_reward': data.get('total_reward', 0),
            'level_ups': level_ups,
            'current_level': current_level,
            'total_skill_exp': total_skill_exp,
            'prev_level': prev_level,
            'prev_exp': prev_exp,
            'current_exp': current_exp
        })
    async def do_fish_settlement(self, interaction_or_ctx, user_id_str):
        """結算釣魚（統一路徑，確保技能升級資訊一致）"""
        await self.finish_fishing(interaction_or_ctx, user_id_str)

    async def _handle_fish_start(self, interaction, times):
        """新開始區：出海確認與扣款檢查"""
        bank = self.bot.get_cog('BankMod')
        user_data = bank.add_stats(interaction.guild.id, interaction.user.id)
        boat_lv = user_data.get("boat_level", 1)
        rod_lv = user_data.get("rod_level", 1)
        fish_skill_lv = user_data.get("fish_skill_level", 1)
        skill_discount = 1.0 - max(0, fish_skill_lv - 1) * 0.02
        base_cost = times * 50
        cost = int(base_cost * skill_discount)
        discount_pct = int((1 - skill_discount) * 100)
        if user_data.get("coin", 0) < cost:
            msg = f"❌ 現金不足！需要 `${cost:,}`。"
            if not interaction.response.is_done():
                await interaction.response.send_message(msg, ephemeral=True)
            else:
                await interaction.followup.send(msg, ephemeral=True)
            return
        per_fish_time = max(0.5, 10.0 - (boat_lv - 1) * 0.5)
        duration = int(times * per_fish_time)
        finish_time = datetime.now() + timedelta(seconds=duration)
        data = {
            'user_mention': interaction.user.mention,
            'boat_lv': boat_lv,
            'rod_lv': rod_lv,
            'fish_skill_lv': fish_skill_lv,
            'per_fish_time': per_fish_time,
            'duration': duration,
            'finish_time': finish_time,
            'cost': cost,
            'discount': f"{discount_pct}%"
        }
        view = FishConfirmView(interaction, self, times, cost, boat_lv, rod_lv, per_fish_time, duration, finish_time)
        embed = self._build_fishing_embed('start', data)
        if not interaction.response.is_done():
            await interaction.response.send_message(embed=embed, view=view)
        else:
            await interaction.followup.send(embed=embed, view=view)

    async def execute_fish_start(self, interaction: discord.Interaction, fish_view):
        """確認出海後執行：扣款、計算收益、儲存、啟動計時器"""
        uid = fish_view.uid
        times = fish_view.times
        cost = fish_view.cost
        boat_lv = fish_view.boat_lv
        rod_lv = fish_view.rod_lv
        duration = fish_view.duration
        finish_time = fish_view.finish_time

        bank = self.bot.get_cog('BankMod')
        user_data = bank.add_stats(interaction.guild.id, uid, coin=0)
        if user_data.get("coin", 0) < cost:
            return await interaction.response.send_message("❌ 餘額不足，請重新下指令。", ephemeral=True)

        user_data["coin"] -= cost
        bank.save_data()

        fish_skill_lv = user_data.get("fish_skill_level", 1)
        fish_skill_bonus = max(0, (fish_skill_lv - 1) * 0.5)
        bonus = rod_lv - 1
        adj_weights = []
        for f in self.FISH_POOL:
            w = f["chance"]
            r = f["rarity"]
            if r == "傳說": w += bonus * 1 + fish_skill_bonus
            elif r == "史詩": w += bonus * 1 + fish_skill_bonus
            elif r == "稀有": w += int(bonus * 0.5) + fish_skill_bonus * 0.5
            elif r == "垃圾": w = max(5, w - int(bonus * 1.3))
            elif r == "災難": w = max(1, w - int(bonus * 0.5))
            else: w = max(10, w - int(bonus * 0.8))
            adj_weights.append(w)

        total_reward = 0
        rarity_counts = {}
        for _ in range(times):
            fish_obj = random.choices(self.FISH_POOL, weights=adj_weights, k=1)[0]
            price = fish_obj["price"]
            if price > 0:
                price = int(price * (1 + (rod_lv - 1) * 0.1))
            total_reward += price
            r = fish_obj["rarity"]
            rarity_counts[r] = rarity_counts.get(r, 0) + 1

        # 記錄掛機資訊（包含 start_time, 裝備等）
        fisher_data = {
            "start_time": datetime.now(),
            "end_time": finish_time,
            "total_reward": total_reward,
            "times": times,
            "rarity_counts": rarity_counts,
            "guild_id": interaction.guild.id,
            "channel_id": interaction.channel.id,
            "boat_level": boat_lv,
            "rod_level": rod_lv,
            "user_name": interaction.user.display_name,
            "fish_skill_level": fish_skill_lv,
            "cost": cost
        }
        self.update_fisher(uid, fisher_data)

        hh, remainder = divmod(duration, 3600)
        mm, ss = divmod(remainder, 60)
        time_str = (f"{hh}小時" if hh > 0 else "") + (f"{mm}分" if mm > 0 else "") + f"{ss}秒"

        active_view = FishActiveView(self, uid)
        discount_pct = getattr(fish_view, "discount_pct", int(max(0, fish_skill_lv - 1) * 2))
        embed = discord.Embed(title="🚢 漁船已出海", color=0x2ecc71)
        embed.description = (
            f"👤 **釣客：** <@{uid}>\n"
            f"🚤 **漁船等級：** `Lv.{boat_lv}`\n"
            f"🎣 **魚竿等級：** `Lv.{rod_lv}`\n"
            f"⭐ **釣魚技能：** `Lv.{fish_skill_lv}`\n"
            f"💸 **技能折扣：** `-{discount_pct}%`（本次消耗 `${cost:,}`）\n"
            f"⏱️ **作業速度：** `{fish_view.per_fish_time:.1f}s` / 竿\n"
            f"⏳ **總計耗時：** `約 {time_str}`\n"
            f"🔔 **回港時間：** `{finish_time.strftime('%H:%M:%S')}`\n\n"
            "💡 可隨時利用/fish指令查看進度或中途返航"
        )
        await interaction.response.edit_message(embed=embed, view=active_view)

    @app_commands.command(name="fish_shop", description="查看與升級你的釣魚設備")
    @app_commands.guild_only()
    async def fish_shop(self, interaction: discord.Interaction):
        if not self.bank or not hasattr(self.bank, 'add_stats'):
            self.bank = self._find_bank_cog()
        if not self.bank:
            return await interaction.response.send_message("❌ 銀行模組未就緒，請稍後重試。", ephemeral=True)
        
        bank = self.bank
        user_data = bank.add_stats(interaction.guild.id, interaction.user.id)

        boat_lv = user_data.get("boat_level", 1)
        rod_lv = user_data.get("rod_level", 1)

        current_boat_speed = max(0.5, 10.0 - (boat_lv - 1) * 0.5)
        next_boat_speed = max(0.5, 10.0 - (boat_lv) * 0.5)
        current_rod_bonus = (rod_lv - 1) * 10
        next_rod_bonus = rod_lv * 10

        boat_upgrade_cost = boat_lv * 1000000
        rod_upgrade_cost = rod_lv * 1000000

        embed = discord.Embed(
            title="🛠️ 漁具整備中心 (Max Lv.20)",
            description=f"歡迎回來，{interaction.user.mention}！目前最高等級已開放至 20 等。",
            color=0x3498db
        )

        boat_text = f"**等級：** `Lv.{boat_lv}/20`\n**目前速度：** `{current_boat_speed:.1f}s` / 竿\n"
        if boat_lv < 20:
            boat_text += f"**下一級：** `{next_boat_speed:.1f}s` (費用: `${boat_upgrade_cost:,}`)"
        else:
            boat_text += "**狀態：** 已達到頂級 ✨"
        embed.add_field(name="🚤 工業級漁船", value=boat_text, inline=False)

        rod_text = f"**等級：** `Lv.{rod_lv}/20`\n**價值加成：** `+{current_rod_bonus}%` 收益\n"
        if rod_lv < 20:
            rod_text += f"**下一級：** `+{next_rod_bonus}%` (費用: `${rod_upgrade_cost:,}`)"
        else:
            rod_text += "**狀態：** 已達到頂級 ✨"
        embed.add_field(name="🎣 鈦合金魚竿", value=rod_text, inline=False)

        embed.set_footer(text="使用 /upgrade <項目> 進行升級")
        embed.set_author(name="NuSo 系統核心", icon_url=self.bot.user.avatar.url if self.bot.user.avatar else None)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="upgrade", description="升級設備：漁船或魚竿")
    @app_commands.choices(item=[
        app_commands.Choice(name="🚤 漁船 (速度)", value="boat"),
        app_commands.Choice(name="🎣 魚竿 (品質)", value="rod")
    ])
    @app_commands.guild_only()
    async def upgrade(self, interaction: discord.Interaction, item: str):
        if not self.bank or not hasattr(self.bank, 'add_stats'):
            self.bank = self._find_bank_cog()
        if not self.bank:
            return await interaction.response.send_message("❌ 銀行模組未就緒，請稍後重試。", ephemeral=True)
        
        bank = self.bank
        user_data = bank.add_stats(interaction.guild.id, interaction.user.id)

        is_boat = (item == "boat")
        current_lv = user_data.get("boat_level", 1) if is_boat else user_data.get("rod_level", 1)
        item_name = "🚤 漁船" if is_boat else "🎣 魚竿"

        if current_lv >= 20:
            return await interaction.response.send_message(f"❌ 你的 {item_name} 已達最高等級 (Lv.20)！", ephemeral=True)

        cost = current_lv * 1000000
        if user_data.get("coin", 0) < cost:
            return await interaction.response.send_message(f"❌ 錢不夠！升級需要 `${cost:,}`", ephemeral=True)

        user_data["coin"] -= cost
        if is_boat:
            user_data["boat_level"] = current_lv + 1
        else:
            user_data["rod_level"] = current_lv + 1
        bank.save_data()

        embed = discord.Embed(
            title="🔨 設備升級成功 / Equipment Upgraded",
            description=f"你已成功將 **{item_name}** 提升至 **Lv.{current_lv + 1}**",
            color=0xff0000 # 紅色邊框
        )
        embed.add_field(name="消耗金額", value=f"`${cost:,}`", inline=True)
        embed.add_field(name="目前餘額", value=f"`${user_data['coin']:,}`", inline=True)

        if is_boat:
            eff = f"作業速度提升至：`{max(0.5, 10.0 - (current_lv) * 0.5):.1f}s` / 竿"
        else:
            eff = f"漁獲價值加成提升至：`+{current_lv * 10}%`"
        embed.add_field(name="✨ 強化效果", value=eff, inline=False)

        embed.set_author(name="NuSo 系統核心", icon_url=self.bot.user.avatar.url if self.bot.user.avatar else None)
        embed.set_footer(text="From system")
        embed.timestamp = datetime.now()
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="fish_skill", description="查看你的釣魚技能等級和經驗進度")
    @app_commands.guild_only()
    async def fish_skill(self, interaction: discord.Interaction):
        if not self.bank or not hasattr(self.bank, 'add_stats'):
            self.bank = self._find_bank_cog()
        if not self.bank:
            return await interaction.response.send_message("❌ 銀行模組未就緒，請稍後重試。", ephemeral=True)
        
        bank = self.bank
        user_data = bank.add_stats(interaction.guild.id, interaction.user.id)
        
        try:
            skill_lv = int(user_data.get('fish_skill_level', 1))
        except (TypeError, ValueError):
            skill_lv = 1
        try:
            skill_exp = int(user_data.get('fish_skill_exp', 0))
        except (TypeError, ValueError):
            skill_exp = 0
        skill_lv = max(1, min(skill_lv, 20))
        skill_exp = max(0, skill_exp)
        
        # 計算進度條（固定長度，避免超過 Discord embed 欄位限制）
        exp_needed = 100
        progress_bar_length = 15
        if skill_lv >= 20:
            progress_bar = "█" * progress_bar_length
            progress_text = f"[{progress_bar}] MAX"
            exp_left = 0
        else:
            safe_exp = max(0, min(skill_exp, exp_needed))
            filled = int((safe_exp / exp_needed) * progress_bar_length)
            progress_bar = "█" * filled + "░" * (progress_bar_length - filled)
            progress_text = f"[{progress_bar}] {safe_exp}/100"
            exp_left = exp_needed - safe_exp
        
        # 技能效果
        rarity_bonus = (skill_lv - 1) * 0.5
        cost_discount = (skill_lv - 1) * 2
        
        embed = discord.Embed(
            title="⭐ 釣魚技能檔案",
            color=0x00aaff
        )
        embed.description = f"<@{interaction.user.id}> 的技能信息"
        
        # 技能等級和進度
        embed.add_field(
            name="📈 等級",
            value=f"`Lv. {skill_lv}/20` • {progress_text}",
            inline=False
        )
        
        # 技能效果（合併在一個字段中以避免超過長度）
        effects_text = (
            f"💰 成本降低：`{cost_discount}%`\n"
            f"✨ 稀有度加成：`+{rarity_bonus:.1f}`"
        )
        embed.add_field(
            name="🎣 效果",
            value=effects_text,
            inline=False
        )
        
        # 升級提示簡化版
        if skill_lv < 20:
            embed.add_field(
                name="🎯 升級進度",
                value=f"還需 `{exp_left}` 經驗升級",
                inline=False
            )
        
        embed.set_footer(text="✨ 使用 /fish 進行釣魚來獲得經驗" if skill_lv < 20 else "✨ 已達到最高等級！")
        embed.timestamp = datetime.now()
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="dragongate", description="玩一局刺激的射龍門！")
    @app_commands.describe(bet="你要下注的金額")
    async def dragongate(self, interaction: discord.Interaction, bet: int):
        if not self.bank or not hasattr(self.bank, 'add_stats'):
            self.bank = self._find_bank_cog()
        if bet < 100:
            return await interaction.response.send_message("❌ 最低下注金額為 $100！", ephemeral=True)

        #獲取資料 (傳入 coin=0)
        user_data = self.bank.add_stats(interaction.guild.id, interaction.user.id, coin=0)

        # 2. 檢查餘額
        if user_data['coin'] < bet:
            return await interaction.response.send_message(f"❌ 錢不夠！你目前只有 ${user_data['coin']:,}。", ephemeral=True)

        #  開始時先扣錢
        self.bank.add_stats(interaction.guild.id, interaction.user.id, coin=-bet)
        self.bank.save_data()
        user_data = self.bank.add_stats(interaction.guild.id, interaction.user.id, coin=0)

        # 準備遊戲
        suits = ["♠️", "♥️", "♦️", "♣️"]
        deck = [(s, v) for s in suits for v in range(1, 14)]
        random.shuffle(deck)

        view = DragonGateView(interaction, user_data, bet, deck, self, self.bank)

        embed = discord.Embed(title="🐉 射龍門 (Shoot the Dragon Gate)", color=0xf1c40f)
        embed.add_field(name="⚖️ 目前門柱", value=f"{view.card_to_str(view.gate[0])}  ↔️  {view.card_to_str(view.gate[1])}", inline=False)
        embed.add_field(name="💰 下注金額", value=f"`${bet:,}` (已扣除)", inline=True)
        embed.set_footer(text="提示：撞柱賠兩倍！")

        await interaction.response.send_message(embed=embed, view=view)

    # --- 終端監聽與控制功能 ---
    def console_listener(self):
        """在獨立線程中監聽終端輸入"""
        print("\n" + "═"*30)
        print(" NuSo 核心終端已啟動")
        print(" 輸入 'help' 展開權限指令清單")
        print("═"*30 + "\n")

        while True:
            try:
                line = input("").strip().split()
                if not line: continue
                cmd = line[0].lower()
                args = line[1:]

                # 1. 幫助清單
                if cmd == "help":
                    print("\n" + "═"*25 + " 終端指令表 " + "═"*25)
                    print("【一、伺服器核心 (Server)】")
                    print(f"  {'guilds / setguild [GID]':<25} | 列出/切換終端預設伺服器")
                    print(f"  {'rename [名稱]':<23} | 變更伺服器名稱")
                    print(f"  {'security [0-4]':<25} | 調整驗證門檻 (0-4)")
                    print(f"  {'audit':<25} | 顯示最新 20 筆審核日誌")
                    print("\n【二、成員與身分組 (Members)】")
                    print(f"  {'kick [ID]':<25} | 驅逐成員")
                    print(f"  {'ban [ID] [天數]':<23} | 封鎖並刪除訊息 (0-7天)")
                    print(f"  {'add-admin [MID] [RID]':<25} | 🔴 賦予管理員身分組")
                    print(f"  {'rm-admin [MID] [RID]':<25} | 🔴 移除身分組權限")
                    print(f"  {'roles':<25} | 列出所有身份組與ID")
                    print(f"  {'botperms [CID]':<25} | 查看機器人目前權限(可指定頻道)")
                    print(f"  {'mute [ID] [分鐘]':<23} | 強制禁言 (Timeout)")
                    print(f"  {'nick [ID] [新名字]':<22} | 修改他人暱稱")
                    print("\n【三、頻道與內容 (Channels)】")
                    print(f"  {'channels':<25} | 列出所有分類/文字/語音頻道與ID")
                    print(f"  {'tracklog [CID] [on/off]':<25} | 開關該頻道新訊息自動記錄")
                    print(f"  {'tracklog-list':<25} | 查看目前自動記錄頻道")
                    print(f"  {'history [CID] [量]':<25} | 查看最新聊天紀錄並輸出TXT (預設20, 上限5000)")
                    print(f"  {'rm-chan [ID]':<25} | 刪除頻道/類別")
                    print(f"  {'purge [ID] [量]':<24} | 批量刪除訊息")
                    print(f"  {'chanvis [CID] [m/r] [ID] [on/off]':<25} | 調整頻道可見權限(成員/身分組)")
                    print("\n【四、語音與視訊 (Voice)】")
                    print(f"  {'vcstatus':<25} | 查看目前語音頻道使用狀態")
                    print(f"  {'vctrack [CID] [on/off]':<25} | 開關語音頻道自動加入追蹤")
                    print(f"  {'vctrack-list':<25} | 查看目前語音追蹤頻道")
                    print(f"  {'vclog [量] [CID]':<25} | 匯出語音事件紀錄TXT (預設30)")
                    print(f"  {'vcjoinlog [量] [CID]':<25} | 匯出加入語音紀錄TXT (預設30)")
                    print(f"  {'vckick [ID]':<25} | 強制斷開語音 (Disconnect)")
                    print(f"  {'vcmove [ID] [CID]':<25} | 強行拖拽至頻道 CID")
                    print(f"  {'vcmute [ID] [1/0]':<25} | 伺服器靜音 (1=開, 0=關)")
                    print(f"  {'vcdeaf [ID] [1/0]':<25} | 伺服器拒聽 (1=開, 0=關)")
                    print("\n【五、遊戲後台控制 (Game Control)】")
                    print(f"  {'bj [名稱] [w/l/p]':<23} | 21點控制 (w必贏/l必輸/p清除)")
                    print("\n【系 統】")
                    print(f"  {'ann:ID:msg':<25} | 發送系統公告 (舊格式)")
                    print(f"  {'r / cls / exit':<25} | 重載 / 清理 / 關閉")
                    print("═"*70 + "\n")

                # 2. 核心邏輯處理
                elif cmd == "rename":
                    asyncio.run_coroutine_threadsafe(self.bot.get_guild(self.GUILD_ID).edit(name=" ".join(args)), self.bot.loop)
                    print(f"✅ 伺服器已更名為: {' '.join(args)}")

                elif cmd == "audit":
                    # 🔍 顯示最新 20 筆審核日誌
                    guild = self.bot.get_guild(self.GUILD_ID)
                    print(f"\n--- 📡 伺服器最新審核日誌 ({guild.name}) ---")
                    # 使用 async for 迭代審核日誌
                    async def fetch_audit():
                        async for entry in guild.audit_logs(limit=20):
                            time = entry.created_at.strftime("%H:%M:%S")
                            print(f"[{time}] {entry.user.name} -> {entry.action.name} (對象: {entry.target})")
                    asyncio.run_coroutine_threadsafe(fetch_audit(), self.bot.loop)

                elif cmd == "security":
                    # 調整驗證等級 (0-4)
                    level = getattr(discord.VerificationLevel, ['none', 'low', 'medium', 'high', 'highest'][int(args[0])])
                    asyncio.run_coroutine_threadsafe(self.bot.get_guild(self.GUILD_ID).edit(verification_level=level), self.bot.loop)
                    print(f"✅ 驗證等級已調至: {level}")

                elif cmd == "guilds":
                    ids = [int(x) for x in getattr(self, "GUILD_IDS", [self.GUILD_ID])]
                    if not ids:
                        print("(目前沒有設定 GUILD_IDS)")
                        continue

                    print("\n--- 🌐 已設定伺服器清單 ---")
                    print(f"目前預設: {self.GUILD_ID}")
                    for gid in ids:
                        guild = self.bot.get_guild(gid)
                        gname = guild.name if guild else "(機器人未加入或尚未快取)"
                        mark = "*" if gid == self.GUILD_ID else " "
                        print(f"{mark} {gid} | {gname}")

                elif cmd == "setguild":
                    if not args:
                        print("❌ 用法: setguild [GID]")
                        continue
                    try:
                        gid = int(args[0])
                    except ValueError:
                        print("❌ GID 必須是數字。")
                        continue

                    ids = [int(x) for x in getattr(self, "GUILD_IDS", [self.GUILD_ID])]
                    if gid not in ids:
                        print("❌ 該 GID 不在 GUILD_IDS 設定清單中。")
                        continue

                    guild = self.bot.get_guild(gid)
                    if not guild:
                        print("❌ 機器人尚未加入該伺服器，或尚未取得快取。")
                        continue

                    self.GUILD_ID = gid
                    print(f"✅ 已切換終端預設伺服器為: {guild.name} ({gid})")

                elif cmd == "add-admin":
                    guild = self.bot.get_guild(self.GUILD_ID)
                    member = guild.get_member(int(args[0])) # 第一個參數是成員 ID
                    role = guild.get_role(int(args[1]))     # 第二個參數是身分組 ID

                    if member and role:
                        asyncio.run_coroutine_threadsafe(member.add_roles(role), self.bot.loop)
                        print(f"✅ [身分組支配]：已將 {role.name} 賦予給 {member.display_name}")
                    else:
                        print("❌ 錯誤：找不到成員或身分組，請檢查 ID 是否正確。")

                elif cmd == "rm-admin":
                    guild = self.bot.get_guild(self.GUILD_ID)
                    member = guild.get_member(int(args[0]))
                    role = guild.get_role(int(args[1]))
                    if member and role:
                        asyncio.run_coroutine_threadsafe(member.remove_roles(role), self.bot.loop)
                        print(f"✅ [身分組支配]：已從 {member.display_name} 身上剝奪 {role.name}")
                    else:
                        print("❌ 錯誤：操作失敗，請確認 ID。")

                elif cmd == "roles":
                    guild = self.bot.get_guild(self.GUILD_ID)
                    if not guild:
                        print("❌ 找不到目標伺服器。")
                        continue
                    print(f"\n--- 🧷 身份組清單 ({guild.name}) ---")
                    roles = sorted(guild.roles, key=lambda r: r.position, reverse=True)
                    for r in roles:
                        print(f"- {r.name} | ID:{r.id} | 位置:{r.position} | 人數:{len(r.members)}")

                elif cmd == "botperms":
                    guild = self.bot.get_guild(self.GUILD_ID)
                    if not guild:
                        print("❌ 找不到目標伺服器。")
                        continue

                    me = guild.me or guild.get_member(self.bot.user.id)
                    if not me:
                        print("❌ 找不到機器人在伺服器中的成員資料。")
                        continue

                    target_channel = None
                    if args:
                        try:
                            cid = int(args[0])
                            target_channel = self.bot.get_channel(cid)
                            if target_channel is None:
                                print("❌ 找不到該頻道ID。")
                                continue
                        except ValueError:
                            print("❌ 頻道ID 必須是數字。")
                            continue

                    perms_obj = target_channel.permissions_for(me) if target_channel else me.guild_permissions
                    enabled = [name for name, allowed in perms_obj if allowed]

                    scope = f"頻道 #{target_channel.name}" if target_channel else "伺服器層級"
                    print(f"\n--- 🤖 機器人權限 ({scope}) ---")
                    print(f"機器人：{me.display_name} ({me.id})")
                    print(f"啟用權限數：{len(enabled)}")
                    print("啟用權限：")
                    for p in enabled:
                        print(f"- {p}")

                elif cmd == "chanvis":
                    # chanvis [CID] [m/r] [ID] [on/off]
                    if len(args) < 4:
                        print("❌ 用法: chanvis [CID] [m/r] [ID] [on/off]")
                        print("   例: chanvis 123456789012345678 m 111111111111111111 on")
                        continue

                    try:
                        channel_id = int(args[0])
                    except ValueError:
                        print("❌ 頻道ID 必須是數字。")
                        continue

                    target_type = args[1].lower().strip()
                    if target_type not in ("m", "r"):
                        print("❌ 第二參數必須是 m(成員) 或 r(身分組)。")
                        continue

                    try:
                        target_id = int(args[2])
                    except ValueError:
                        print("❌ 目標ID 必須是數字。")
                        continue

                    action = args[3].lower().strip()
                    if action not in ("on", "off"):
                        print("❌ 第四參數必須是 on 或 off。")
                        continue

                    guild = self.bot.get_guild(self.GUILD_ID)
                    if not guild:
                        print("❌ 找不到目標伺服器。")
                        continue

                    channel = self.bot.get_channel(channel_id)
                    if not channel or not isinstance(channel, discord.TextChannel):
                        print("❌ 找不到文字頻道，請確認 CID。")
                        continue

                    me = guild.me or guild.get_member(self.bot.user.id)
                    if not me:
                        print("❌ 找不到機器人伺服器身分。")
                        continue

                    if not channel.permissions_for(me).manage_channels:
                        print("❌ 機器人沒有該頻道的 manage_channels 權限。")
                        continue

                    if target_type == "m":
                        target = guild.get_member(target_id)
                        if not target:
                            print("❌ 找不到該成員。")
                            continue
                    else:
                        target = guild.get_role(target_id)
                        if not target:
                            print("❌ 找不到該身分組。")
                            continue

                    visible = (action == "on")

                    async def do_chanvis():
                        await channel.set_permissions(
                            target,
                            view_channel=visible,
                            read_message_history=visible,
                        )

                    fut = asyncio.run_coroutine_threadsafe(do_chanvis(), self.bot.loop)
                    try:
                        fut.result(timeout=10)
                        state_text = "可見" if visible else "不可見"
                        print(f"✅ 已將 #{channel.name} 對 {target.name} 設為：{state_text}")
                    except Exception as e:
                        print(f"❌ chanvis 執行失敗: {e}")

                elif cmd == "kick":
                    guild = self.bot.get_guild(self.GUILD_ID)
                    m = guild.get_member(int(args[0]))
                    asyncio.run_coroutine_threadsafe(m.kick(reason="支配者指令"), self.bot.loop)
                    print(f"✅ 已驅逐: {m.display_name}")

                elif cmd == "ban":
                    # ban [ID] [天數]
                    guild = self.bot.get_guild(self.GUILD_ID)
                    m = guild.get_member(int(args[0]))
                    days = int(args[1]) if len(args) > 1 else 0
                    asyncio.run_coroutine_threadsafe(m.ban(delete_message_days=days, reason="支配者裁決"), self.bot.loop)
                    print(f"🔨 已封鎖 {m.display_name} (清理 {days} 天訊息)")

                elif cmd == "mute":
                    guild = self.bot.get_guild(self.GUILD_ID)
                    m = guild.get_member(int(args[0]))
                    time_min = int(args[1])
                    asyncio.run_coroutine_threadsafe(m.timeout(timedelta(minutes=time_min)), self.bot.loop)
                    print(f"✅ 已禁言 {m.display_name} {time_min} 分鐘")

                elif cmd == "nick":
                    # nick [ID] [新名字]
                    guild = self.bot.get_guild(self.GUILD_ID)
                    m = guild.get_member(int(args[0]))
                    new_name = " ".join(args[1:])
                    asyncio.run_coroutine_threadsafe(m.edit(nick=new_name), self.bot.loop)
                    print(f"📝 已將 {m.name} 改名為: {new_name}")

                elif cmd == "rm-chan":
                    # rm-chan [ID]
                    chan = self.bot.get_channel(int(args[0]))
                    if chan:
                        asyncio.run_coroutine_threadsafe(chan.delete(), self.bot.loop)
                        print(f"🗑️ 已刪除頻道: {chan.name}")

                elif cmd == "channels":
                    guild = self.bot.get_guild(self.GUILD_ID)
                    if not guild:
                        print("❌ 找不到目標伺服器。")
                        continue

                    print(f"\n--- 📚 頻道清單 ({guild.name}) ---")

                    categories = list(guild.categories)
                    if categories:
                        print("\n[分類頻道]")
                        for c in categories:
                            print(f"- {c.name} (ID: {c.id})")

                    text_channels = list(guild.text_channels)
                    if text_channels:
                        print("\n[文字頻道]")
                        for c in text_channels:
                            print(f"- #{c.name} (ID: {c.id})")

                    voice_channels = list(guild.voice_channels)
                    if voice_channels:
                        print("\n[語音頻道]")
                        for c in voice_channels:
                            print(f"- 🔊 {c.name} (ID: {c.id})")

                    if not (categories or text_channels or voice_channels):
                        print("(目前沒有可列出的頻道)")

                elif cmd == "tracklog":
                    if not args:
                        print("❌ 用法: tracklog [頻道ID] [on/off，可省略，預設on]")
                        continue

                    try:
                        channel_id = int(args[0])
                    except ValueError:
                        print("❌ 頻道ID 必須是數字。")
                        continue

                    action = (args[1].lower() if len(args) > 1 else "on")
                    if action not in ("on", "off"):
                        print("❌ 第二參數只能是 on 或 off")
                        continue

                    chan = self.bot.get_channel(channel_id)
                    if action == "on":
                        self.tracked_log_channels.add(channel_id)
                        self._save_tracked_log_channels()
                        name = chan.name if chan else f"channel_{channel_id}"
                        print(f"✅ 已啟用頻道追蹤: {name} ({channel_id})")
                    else:
                        if channel_id in self.tracked_log_channels:
                            self.tracked_log_channels.remove(channel_id)
                            self._save_tracked_log_channels()
                        name = chan.name if chan else f"channel_{channel_id}"
                        print(f"✅ 已停用頻道追蹤: {name} ({channel_id})")

                elif cmd == "tracklog-list":
                    if not self.tracked_log_channels:
                        print("(目前沒有啟用任何頻道追蹤)")
                        continue

                    print("\n--- 🧾 目前追蹤頻道 ---")
                    for cid in sorted(self.tracked_log_channels):
                        chan = self.bot.get_channel(cid)
                        name = chan.name if chan else f"channel_{cid}"
                        path = self._channel_log_output_path(name)
                        print(f"- {name} ({cid}) -> {path}")

                elif cmd == "history":
                    if not args:
                        print("❌ 用法: history [頻道ID] [筆數，可省略]")
                        continue

                    try:
                        channel_id = int(args[0])
                    except ValueError:
                        print("❌ 頻道ID 必須是數字。")
                        continue

                    try:
                        limit = int(args[1]) if len(args) > 1 else 20
                    except ValueError:
                        print("❌ 筆數必須是數字。")
                        continue

                    limit = max(1, min(limit, 5000))
                    chan = self.bot.get_channel(channel_id)
                    if not chan or not hasattr(chan, "history"):
                        print("❌ 找不到可讀取訊息的頻道，請確認頻道ID。")
                        continue

                    async def fetch_history():
                        try:
                            count = 0
                            export_lines = []
                            async for msg in chan.history(limit=limit, oldest_first=False):
                                ts = msg.created_at.astimezone().strftime("%Y-%m-%d %H:%M:%S")
                                content = (msg.content or "").replace("\n", "\\n")
                                if not content:
                                    if msg.attachments:
                                        attach_parts = [f"{att.filename}: {att.url}" for att in msg.attachments]
                                        content = f"[附件 {len(msg.attachments)}] " + " | ".join(attach_parts)
                                    elif msg.embeds:
                                        content = f"[Embed {len(msg.embeds)}]"
                                    else:
                                        content = "[無文字內容]"
                                export_lines.append(f"[{ts}] {msg.author.display_name} ({msg.author.id}): {content}")
                                count += 1

                            if count == 0:
                                print("(此頻道目前沒有可讀取訊息，未輸出檔案)")
                                return

                            invalid = '<>:"/\\|?*'
                            safe_name = "".join("_" if ch in invalid else ch for ch in chan.name).strip().rstrip('.')
                            if not safe_name:
                                safe_name = f"channel_{chan.id}"
                            log_dir = os.path.join(os.getcwd(), "channel_log")
                            os.makedirs(log_dir, exist_ok=True)
                            output_path = os.path.join(log_dir, f"{safe_name}.txt")

                            with open(output_path, "w", encoding="utf-8") as f:
                                f.write("\n".join(export_lines))

                            print(f"✅ 已輸出聊天紀錄檔案: {output_path} | 紀錄行數: {count}")
                        except Exception as e:
                            print(f"❌ 讀取聊天紀錄失敗: {e}")

                    asyncio.run_coroutine_threadsafe(fetch_history(), self.bot.loop)

                elif cmd == "purge":
                    # purge [頻道ID] [量]
                    chan = self.bot.get_channel(int(args[0]))
                    limit = int(args[1])
                    asyncio.run_coroutine_threadsafe(chan.purge(limit=limit), self.bot.loop)
                    print(f"🧹 已在 {chan.name} 刪除 {limit} 條訊息")

                elif cmd == "vcmove":
                    # vcmove [成員ID] [目標頻道ID]
                    guild = self.bot.get_guild(self.GUILD_ID)
                    m = guild.get_member(int(args[0]))
                    chan = self.bot.get_channel(int(args[1]))
                    asyncio.run_coroutine_threadsafe(m.move_to(chan), self.bot.loop)
                    print(f"🏃 已強行拖移 {m.display_name} 至 {chan.name}")

                elif cmd == "vcstatus":
                    guild = self.bot.get_guild(self.GUILD_ID)
                    if not guild:
                        print("❌ 找不到目標伺服器。")
                        continue

                    print(f"\n--- 🔊 語音使用狀態 ({guild.name}) ---")
                    has_member = False
                    for vc in guild.voice_channels:
                        if not vc.members:
                            continue
                        has_member = True
                        print(f"\n[{vc.name}] ({len(vc.members)} 人)")
                        for m in vc.members:
                            vs = m.voice
                            if not vs:
                                continue
                            mic = "關" if vs.self_mute else "開"
                            ear = "關(拒聽)" if vs.self_deaf else "開"
                            srv_mute = "是" if vs.mute else "否"
                            srv_deaf = "是" if vs.deaf else "否"
                            stream = "是" if vs.self_stream else "否"
                            video = "是" if vs.self_video else "否"
                            print(
                                f"- {m.display_name} ({m.id}) | 麥:{mic} 耳:{ear} "
                                f"伺服器靜音:{srv_mute} 伺服器拒聽:{srv_deaf} 直播:{stream} 視訊:{video}"
                            )

                    if not has_member:
                        print("(目前沒有成員在語音頻道)")

                elif cmd == "vctrack":
                    if not args:
                        print("❌ 用法: vctrack [語音頻道ID] [on/off，可省略，預設on]")
                        continue

                    try:
                        channel_id = int(args[0])
                    except ValueError:
                        print("❌ 頻道ID 必須是數字。")
                        continue

                    action = (args[1].lower() if len(args) > 1 else "on")
                    if action not in ("on", "off"):
                        print("❌ 第二參數只能是 on 或 off")
                        continue

                    chan = self.bot.get_channel(channel_id)
                    if not isinstance(chan, discord.VoiceChannel):
                        print("❌ 該 ID 不是語音頻道或不存在。")
                        continue

                    if action == "on":
                        self.tracked_voice_channels.add(channel_id)
                        self._save_tracked_voice_channels()
                        print(f"✅ 已啟用語音追蹤: {chan.name} ({channel_id})")
                    else:
                        if channel_id in self.tracked_voice_channels:
                            self.tracked_voice_channels.remove(channel_id)
                            self._save_tracked_voice_channels()
                        print(f"✅ 已停用語音追蹤: {chan.name} ({channel_id})")

                elif cmd == "vctrack-list":
                    if not self.tracked_voice_channels:
                        print("(目前語音追蹤清單為空：將追蹤所有語音頻道的加入事件)")
                        continue

                    print("\n--- 🔎 目前語音追蹤頻道 ---")
                    for cid in sorted(self.tracked_voice_channels):
                        chan = self.bot.get_channel(cid)
                        if isinstance(chan, discord.VoiceChannel):
                            name = chan.name
                        else:
                            name = f"voice_channel_{cid}"
                        path = self._channel_log_output_path(f"voice_join_log_{name}")
                        print(f"- {name} ({cid}) -> {path}")

                elif cmd == "vclog":
                    try:
                        limit = int(args[0]) if len(args) > 0 else 30
                    except ValueError:
                        print("❌ 用法: vclog [筆數] [頻道ID，可省略]")
                        continue

                    limit = max(1, min(limit, 5000))
                    channel_filter = None
                    if len(args) > 1:
                        try:
                            cid = int(args[1])
                            c = self.bot.get_channel(cid)
                            channel_filter = c.name if c else None
                            if channel_filter is None:
                                print("❌ 找不到該頻道ID，將顯示全部紀錄。")
                        except ValueError:
                            print("❌ 頻道ID 必須是數字。")
                            continue

                    logs = list(self.voice_event_log)
                    if channel_filter:
                        logs = [x for x in logs if x.get("channel") == channel_filter]

                    if not logs:
                        print("(目前沒有語音事件紀錄)")
                        continue

                    export_logs = logs[-limit:]
                    invalid = '<>:"/\\|?*'
                    base_name = f"voice_log_{channel_filter}" if channel_filter else "voice_log_all"
                    safe_name = "".join("_" if ch in invalid else ch for ch in base_name).strip().rstrip('.')
                    if not safe_name:
                        safe_name = "voice_log"

                    log_dir = os.path.join(os.getcwd(), "channel_log")
                    os.makedirs(log_dir, exist_ok=True)
                    output_path = os.path.join(log_dir, f"{safe_name}.txt")

                    export_lines = [
                        f"[{item['time']}] {item['user']} ({item['user_id']}) | {item['event']} | 頻道: {item['channel']}"
                        for item in export_logs
                    ]
                    with open(output_path, "w", encoding="utf-8") as f:
                        f.write("\n".join(export_lines))

                    print(f"✅ 已輸出語音事件檔案: {output_path} | 紀錄行數: {len(export_logs)}")

                elif cmd == "vcjoinlog":
                    try:
                        limit = int(args[0]) if len(args) > 0 else 30
                    except ValueError:
                        print("❌ 用法: vcjoinlog [筆數] [頻道ID，可省略]")
                        continue

                    limit = max(1, min(limit, 5000))
                    channel_filter = None
                    if len(args) > 1:
                        try:
                            cid = int(args[1])
                            c = self.bot.get_channel(cid)
                            channel_filter = c.name if c else None
                            if channel_filter is None:
                                print("❌ 找不到該頻道ID，將顯示全部加入紀錄。")
                        except ValueError:
                            print("❌ 頻道ID 必須是數字。")
                            continue

                    logs = [x for x in self.voice_event_log if "加入語音" in x.get("event", "")]
                    if channel_filter:
                        logs = [
                            x for x in logs
                            if x.get("channel_id") == cid or x.get("channel") == channel_filter
                        ]

                    if not logs:
                        print("(目前沒有加入語音紀錄)")
                        continue

                    export_logs = logs[-limit:]
                    invalid = '<>:"/\\|?*'
                    base_name = f"voice_join_log_{channel_filter}" if channel_filter else "voice_join_log_all"
                    safe_name = "".join("_" if ch in invalid else ch for ch in base_name).strip().rstrip('.')
                    if not safe_name:
                        safe_name = "voice_join_log"

                    log_dir = os.path.join(os.getcwd(), "channel_log")
                    os.makedirs(log_dir, exist_ok=True)
                    output_path = os.path.join(log_dir, f"{safe_name}.txt")

                    export_lines = [
                        f"[{item['time']}] {item['user']} ({item['user_id']}) | {item['event']} | 頻道: {item['channel']}"
                        for item in export_logs
                    ]
                    with open(output_path, "w", encoding="utf-8") as f:
                        f.write("\n".join(export_lines))

                    print(f"✅ 已輸出加入語音紀錄檔案: {output_path} | 紀錄行數: {len(export_logs)}")

                elif cmd == "vcdeaf":
                    # vcdeaf [成員ID] [1=開, 0=關]
                    guild = self.bot.get_guild(self.GUILD_ID)
                    m = guild.get_member(int(args[0]))
                    status = True if args[1] == "1" else False
                    asyncio.run_coroutine_threadsafe(m.edit(deafen=status), self.bot.loop)
                    print(f"🔇 伺服器拒聽狀態: {status}")

                elif cmd == "vckick":
                    guild = self.bot.get_guild(self.GUILD_ID)
                    m = guild.get_member(int(args[0]))
                    if m and m.voice:
                        asyncio.run_coroutine_threadsafe(m.move_to(None), self.bot.loop)
                        print(f"✅ 已斷開語音連線: {m.display_name}")

                elif cmd == "vcmute":
                    guild = self.bot.get_guild(self.GUILD_ID)
                    m = guild.get_member(int(args[0]))
                    status = True if args[1] == "1" else False
                    asyncio.run_coroutine_threadsafe(m.edit(mute=status), self.bot.loop)
                    print(f"✅ 伺服器靜音狀態已設為: {status}")

                elif cmd == "bj":
                    # bj <display_name> <w|l|p>
                    asyncio.run_coroutine_threadsafe(self.process_bj_control(" ".join(args)), self.bot.loop)

                elif cmd == "r":
                    asyncio.run_coroutine_threadsafe(self.reload_all_extensions(), self.bot.loop)

                elif cmd == "cls":
                    os.system('cls' if os.name == 'nt' else 'clear')

                elif cmd == "exit":
                    os._exit(0)

                elif cmd == "tts":
                    # 格式: tts [要說的話]
                    if not args:
                        print("❌ 請輸入文字。用法: tts 內容")
                        continue

                    speech_text = " ".join(args)

                    async def run_tts():
                        guild = self.bot.get_guild(self.GUILD_ID)
                        if not guild:
                            print("❌ 找不到伺服器。")
                            return

                        # 🔊 自動邏輯：找一個目前有人的語音頻道
                        target_chan = next((c for c in guild.voice_channels if len(c.members) > 0), None)

                        if not target_chan:
                            print("❌ 目前語音頻道沒人，機器人不知道要去哪裡說話。")
                            return

                        # 轉換語音
                        tts_file = "console_tts.mp3"
                        communicate = edge_tts.Communicate(
                        speech_text,
                            "zh-TW-HsiaoChenNeural",
                            rate="+25%",
                            pitch="+10Hz"
                        )
                        await communicate.save(tts_file)

                        # 連接並播放
                        vc = guild.voice_client
                        if not vc:
                            vc = await target_chan.connect()
                        elif vc.channel.id != target_chan.id:
                            await vc.move_to(target_chan)

                        if vc.is_playing():
                            vc.stop()

                        vc.play(discord.FFmpegPCMAudio(executable="ffmpeg", source=tts_file))
                        print(f"🎙️ [後台發言] 已在 {target_chan.name} 播放: {speech_text}")

                    # 丟回主執行緒執行
                    asyncio.run_coroutine_threadsafe(run_tts(), self.bot.loop)

                elif cmd == "play":
                    print(f"DEBUG: 收到 play 指令，路徑: {args}") # 確認有沒有進來
                    if not args:
                        print("❌ 請提供檔案路徑！")
                        continue
                    file_path = args[0]
                    if not os.path.exists(file_path):
                        print(f"❌ 找不到檔案: {file_path}")
                        continue

                    guild = self.bot.get_guild(self.GUILD_ID)
                    print(f"DEBUG: 抓取的伺服器名稱: {guild.name if guild else 'None'}")

                    async def auto_play():
                        try:
                            # 尋找有人的頻道
                            target_chan = next((c for c in guild.voice_channels if len(c.members) > 0), None)
                            if not target_chan:
                                print("❌ 錯誤：伺服器裡目前沒有人在語音頻道！請你自己先進去一個頻道。")
                                return
                            print(f"DEBUG: 準備連接頻道: {target_chan.name}")
                            vc = guild.voice_client or await target_chan.connect()
                            if vc.is_playing(): vc.stop()
                            print(f"DEBUG: 開始執行 FFmpeg...")
                            source = discord.FFmpegPCMAudio(executable="ffmpeg", source=file_path)
                            vc.play(source)
                            print(f"🎵 成功！正在 [{target_chan.name}] 播放: {file_path}")
                        except Exception as e:
                            print(f"❌ 播放內部出錯: {e}")

                    asyncio.run_coroutine_threadsafe(auto_play(), self.bot.loop)

                elif ":" in "".join(line):
                    raw_cmd = "".join(line)
                    parts = raw_cmd.split(":", 2)
                    if len(parts) == 3:
                        asyncio.run_coroutine_threadsafe(
                            self.send_controlled_message(parts[0], parts[1], parts[2]), self.bot.loop
                        )

                # --- 終端機專用播放指令 ---
            except Exception as e:
                print(f"❌ 執行錯誤: {e}")

    # --- 整合發送與重載函式 ---
    async def send_controlled_message(self, mode, target_id, content):
        try:
            target = self.bot.get_channel(int(target_id))
            if mode == "ann":
                embed = discord.Embed(description=f"# 📢 系統公告\n\n{content}", color=0xff0000)
                embed.set_author(name="NuSo 系統核心", icon_url=self.bot.user.avatar.url if self.bot.user.avatar else None)
                embed.timestamp = datetime.now()
                await target.send(embed=embed)
            else:
                await target.send(content)
            print(f"✅ 訊息已發送至 {target_id}")
        except Exception as e:
            print(f"❌ 發送失敗: {e}")

    async def reload_all_extensions(self):
        for ext in ['mod.bank', 'mod.Mod']:
            try:
                await self.bot.reload_extension(ext)
            except:
                pass

        guild_ids = [int(x) for x in getattr(self.bot, "guild_ids", [self.GUILD_ID])]
        if not guild_ids:
            synced = await self.bot.tree.sync()
            fish_synced = any(getattr(cmd, "name", None) == "fish" for cmd in synced)
            print(f"✅ 所有模組已重載並全域同步完成 | synced={len(synced)} | /fish={'OK' if fish_synced else 'MISSING'}")
            return

        total_synced = 0
        fish_ok_any = False
        for gid in guild_ids:
            synced = await self.bot.tree.sync(guild=discord.Object(id=gid))
            total_synced += len(synced)
            fish_synced = any(getattr(cmd, "name", None) == "fish" for cmd in synced)
            fish_ok_any = fish_ok_any or fish_synced
            print(f"✅ 已同步伺服器 {gid} | synced={len(synced)} | /fish={'OK' if fish_synced else 'MISSING'}")

        print(f"✅ 所有模組已重載並完成多伺服器同步 | guilds={len(guild_ids)} | total_synced={total_synced} | /fish={'OK' if fish_ok_any else 'MISSING'}")

async def setup(bot):
    # 這裡檢查 bot 是否有 ai_func 屬性，如果沒有則傳入 None
    ai_func = getattr(bot, "ai_func", None)
    cog = MyCommands(bot, ai_func)
    await bot.add_cog(cog)

    try:
        cog_app_cmds = cog.get_app_commands()
        fish_in_cog = any(cmd.name == "fish" for cmd in cog_app_cmds)
        fish_in_tree = bot.tree.get_command("fish") is not None
        print(
            f"[AppCmd] MyCommands 載入完成 | cog_cmds={len(cog_app_cmds)} | "
            f"/fish(cog)={'OK' if fish_in_cog else 'MISSING'} | "
            f"/fish(tree)={'OK' if fish_in_tree else 'MISSING'}"
        )
    except Exception as e:
        print(f"[AppCmd] 檢查 /fish 指令載入狀態失敗: {e}")
