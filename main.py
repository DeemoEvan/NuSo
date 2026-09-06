import torch
import discord
from discord.ext import commands
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from peft import PeftModel
import os
import asyncio
import sys
from datetime import datetime

# Windows 終端機顏色支援
if sys.platform == "win32":
    os.system('color')

# --- [基礎設定] ---
GUILD_IDS = [
    1446838276249096228,
    861274546077171752,
]

class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix="!",
            intents=discord.Intents.all()
        )
        self.extensions_list = ['mod.Mod', 'mod.bank']
        self.guild_ids = GUILD_IDS

        # --- [⚙️ Neuro-sama 核心人設與參數設定] ---
        # 在這裡修改英文提示詞，可以控制她不要每句都嗆人
        self.neuro_config = {
            "system_prompt": (
                "You are Neuro-sama, a snarky, witty AI VTuber. Mix teasing with care. Don't attack every sentence. Be chaotic and concise."
            ),
            "max_input_length": 256,  # 限制讀取長度，保護顯存不炸掉
            "max_new_tokens": 64,     # 限制回覆長度，確保秒回
            "temperature": 0.7,       # 溫度稍微調低，讓說話比較穩定不亂噴
            "top_p": 0.9,
            "repetition_penalty": 1.1 # 降低重複懲罰，讓語氣更自然
        }

        # --- [✨ 核心 AI 載入區] ---
        print("\033[94m正在初始化 Neuro-sama (Llama-3.1-8B) 靈魂模式...\033[0m")

        base_model_name = "unsloth/meta-llama-3.1-8b-instruct-bnb-4bit"
        adapter_path = r"neuro_model_smart"

        # 極限 4bit 配置
        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_use_double_quant=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.float16
        )

        """ try:
            print("Loading model and Tokenizer...")
            self.tokenizer = AutoTokenizer.from_pretrained(base_model_name)

            base_model = AutoModelForCausalLM.from_pretrained(
                base_model_name,
                quantization_config=bnb_config,
                device_map="auto",
                trust_remote_code=True,
            )

            print("Setting model...")
            self.neuro_model = PeftModel.from_pretrained(
                base_model,
                adapter_path
            )
            print("\033[92mPrompt ready！\033[0m")
        except Exception as e:
            print(f"\033[91m❌ 載入失敗: {e}\033[0m")
            self.neuro_model = None
        """
    async def setup_hook(self):
        # 載入模組
        for ext in self.extensions_list:
            try:
                await self.load_extension(ext)
                print(f"✅ 成功載入模組: {ext}")
            except Exception as e:
                print(f"❌ 模組 {ext} 載入失敗: {e}")

        # 同步斜線指令
        try:
            if not self.guild_ids:
                await self.tree.sync()
                print("✅ 指令已全域同步")
            else:
                for gid in self.guild_ids:
                    guild_obj = discord.Object(id=int(gid))
                    self.tree.copy_global_to(guild=guild_obj)
                    synced = await self.tree.sync(guild=guild_obj)
                    print(f"✅ 指令已同步至伺服器: {gid} | synced={len(synced)}")
        except Exception as e:
            print(f"⚠️ 同步失敗: {e}")

    async def on_ready(self):
        print(f'\033[1;95m機器人已上線 | 身份: {self.user}\033[0m')

    # 公告與控制功能
    async def send_controlled_message(self, mode, target_id, content):
        try:
            target = self.get_channel(int(target_id))
            if not target: return
            if mode == "ann":
                embed = discord.Embed(description=f"# 📢 系統公告\n\n{content}", color=0xff0000)
                embed.set_author(name="NuSo 系統核心", icon_url=self.user.avatar.url if self.user.avatar else None)
                embed.timestamp = datetime.now()
                await target.send(embed=embed)
            else:
                await target.send(content)
        except Exception as e:
            print(f"❌ 發送失敗: {e}")

# --- 啟動入口 ---
if __name__ == "__main__":
    bot = MyBot()
    token_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bot_token.txt")
    try:
        with open(token_path, "r") as f:
            token = f.read().strip()
        bot.run(token)
    except Exception as e:
        print(f"❌ 啟動失敗: {e}")