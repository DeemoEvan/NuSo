import asyncio
from datetime import datetime

import discord
import pyaudio


class FishingView(discord.ui.View):
    def __init__(self, interaction, cog_instance):
        super().__init__(timeout=None)
        self.cog = cog_instance
        self.uid = str(interaction.user.id)


class FishConfirmView(discord.ui.View):
    def __init__(self, interaction, cog_instance, times, cost, boat_lv, rod_lv, per_fish_time, duration, finish_time):
        super().__init__(timeout=60)
        self.interaction = interaction
        self.cog = cog_instance
        self.uid = interaction.user.id
        self.times = times
        self.cost = cost
        self.boat_lv = boat_lv
        self.rod_lv = rod_lv
        self.per_fish_time = per_fish_time
        self.duration = duration
        self.finish_time = finish_time
        self.pa = pyaudio.PyAudio()
        self.loop = asyncio.get_event_loop()

    @discord.ui.button(label="確認出海", style=discord.ButtonStyle.green)
    async def confirm_fish(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.uid:
            return await interaction.response.send_message("❌ 這不是你的按鈕哦！", ephemeral=True)
        await self.cog.execute_fish_start(interaction, self)


class FishActiveView(discord.ui.View):
    def __init__(self, cog_instance, user_id):
        super().__init__(timeout=None)
        self.cog = cog_instance
        self.uid = str(user_id)

    @discord.ui.button(label="🛑 中斷釣魚 (不退費)", style=discord.ButtonStyle.danger)
    async def cancel_fish(self, interaction: discord.Interaction, button: discord.ui.Button):
        if str(interaction.user.id) != self.uid:
            return await interaction.response.send_message("❌ 這不是你的按鈕哦！", ephemeral=True)
        all_fishers = self.cog.get_all_fishers()
        data = all_fishers.get(self.uid)
        if not data:
            return await interaction.response.send_message("⚠️ 找不到你的釣魚資料，可能已經結算了。", ephemeral=True)
        end_time = data.get("end_time")
        if isinstance(end_time, str):
            try:
                end_time = datetime.fromisoformat(end_time)
            except Exception:
                pass
        now = datetime.now()
        if end_time and now >= end_time:
            await interaction.response.send_message("✅ 你的船隻已經回港了，請使用 `/fish` 來收成！", ephemeral=True)
            return

        times = data.get("times", 1)
        original_cost = data.get("cost", times * 50)

        confirm_view = FishCancelConfirmView(self.cog, self.uid, original_cost, self)
        embed = discord.Embed(title="⚠️ 確認中斷釣魚？", color=0xff9900)
        embed.description = (
            f"你確定要**中止**這次出海嗎？\n\n"
            f"💸 **出海花費：** `${original_cost:,}`\n"
            f"⛔ **花費不會退還**\n\n"
            "請在下方確認操作："
        )
        await interaction.response.send_message(embed=embed, view=confirm_view, ephemeral=True)

class FishCancelConfirmView(discord.ui.View):
    def __init__(self, cog_instance, user_id, original_cost, active_view):
        super().__init__(timeout=30)
        self.cog = cog_instance
        self.uid = str(user_id)
        self.original_cost = original_cost
        self.active_view = active_view

    @discord.ui.button(label="是, 確認召回", style=discord.ButtonStyle.danger)
    async def confirm_cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if str(interaction.user.id) != self.uid:
            return

        all_fishers = self.cog.get_all_fishers()
        data = all_fishers.get(self.uid)
        if not data:
            return await interaction.response.edit_message(content="⚠️ 找不到你的釣魚資料，可能已經結算了。", embed=None, view=None)
        self.cog.remove_fisher(self.uid)

        for item in self.children:
            item.disabled = True

        embed = discord.Embed(title="🛑 中斷釣魚", color=0xe74c3c)
        embed.description = (
            f"<@{self.uid}> 已強制召回船隻。\n\n"
            f"💸 **出海花費：** `${self.original_cost:,}`\n"
            f"⛔ **花費不會退還**\n\n"
            "下次出海記得耐心等待！"
        )
        await interaction.response.edit_message(content="✅ 已確認中斷", embed=None, view=None)
        await interaction.followup.send(embed=embed)

    @discord.ui.button(label="否, 取消", style=discord.ButtonStyle.secondary)
    async def cancel_back(self, interaction: discord.Interaction, button: discord.ui.Button):
        if str(interaction.user.id) != self.uid:
            return

        await interaction.response.edit_message(content="✅ 已取消召回，船隻繼續作業。", embed=None, view=None)

class FishingTimesModal(discord.ui.Modal, title='設定釣魚次數'):
    def __init__(self, hub_view):
        super().__init__()
        self.hub_view = hub_view
        
        self.times_input = discord.ui.TextInput(
            label='你要釣幾次？(1~5000)',
            style=discord.TextStyle.short,
            placeholder='基礎每次 50 💰，會套用技能折扣',
            default=str(self.hub_view.times),
            required=True,
            min_length=1,
            max_length=4
        )
        self.add_item(self.times_input)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            times = int(self.times_input.value)
            if times < 1 or times > 5000:
                await interaction.response.send_message("❌ `times` 必須介於 1~5000 之間！", ephemeral=True)
                return
            self.hub_view.times = times
            embed = self.hub_view._generate_embed()
            await interaction.response.edit_message(embed=embed, view=self.hub_view)
        except ValueError:
            await interaction.response.send_message("❌ 請輸入有效的數字！", ephemeral=True)

class FishingHubView(discord.ui.View):
    def __init__(self, cog_instance, uid, guild_id, boat_lv, rod_lv, default_times=1):
        super().__init__(timeout=180)
        self.cog = cog_instance
        self.uid = uid
        self.guild_id = guild_id
        self.boat_lv = boat_lv
        self.rod_lv = rod_lv
        self.times = default_times
        self.per_fish_time = max(0.5, 10.0 - (boat_lv - 1) * 0.5)

    def _calc_discounted_cost(self):
        fish_skill_lv = 1
        bank = self.cog.bot.get_cog('BankMod') if hasattr(self.cog, 'bot') else None
        if bank and self.guild_id:
            try:
                user_data = bank.add_stats(self.guild_id, self.uid)
                fish_skill_lv = max(1, int(user_data.get("fish_skill_level", 1)))
            except Exception:
                fish_skill_lv = 1

        discount_ratio = 1.0 - max(0, fish_skill_lv - 1) * 0.02
        base_cost = self.times * 50
        final_cost = int(base_cost * discount_ratio)
        discount_pct = int((1 - discount_ratio) * 100)
        return final_cost, fish_skill_lv, discount_pct

    def _generate_embed(self):
        from datetime import timedelta
        cost, fish_skill_lv, discount_pct = self._calc_discounted_cost()
        duration = int(self.times * self.per_fish_time)
        hh, remainder = divmod(duration, 3600)
        mm, ss = divmod(remainder, 60)
        time_str = (f"{hh}小時" if hh > 0 else "") + (f"{mm}分" if mm > 0 else "") + f"{ss}秒"
        if not time_str: time_str = "0秒"
        
        embed = discord.Embed(title="🎣 釣魚管理面板", color=0x3498db)
        embed.description = (
            f"你的船隻目前在港口待命。\n\n"
            f"🔹 **預定出航次數:** `{self.times}` 次\n"
            f"🔹 **釣魚技能等級:** `Lv.{fish_skill_lv}`\n"
            f"🔹 **技能成本折扣:** `-{discount_pct}%`\n"
            f"🔹 **預估花費金幣:** `{cost:,}` 💰\n"
            f"🔹 **預估花費時間:** `{time_str}`\n\n"
            f"點擊「📝 設定次數」來修改數量，確認無誤後點擊「⚓ 確定派遣」出海！"
        )
        return embed

    @discord.ui.button(label="設定次數", style=discord.ButtonStyle.secondary, emoji="📝")
    async def set_times_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.uid:
            return await interaction.response.send_message("這不是你的面板哦！", ephemeral=True)
        await interaction.response.send_modal(FishingTimesModal(self))

    @discord.ui.button(label="確定派遣", style=discord.ButtonStyle.primary, emoji="⚓")
    async def depart_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.uid:
            return await interaction.response.send_message("這不是你的面板哦！", ephemeral=True)
            
        all_fishers = self.cog.get_all_fishers()
        if str(self.uid) in all_fishers:
            status = all_fishers[str(self.uid)]
            end_time = status.get("end_time")
            if end_time:
                for item in self.children: item.disabled = True
                await interaction.response.edit_message(view=self)
                return await interaction.followup.send("❌ 你已經派出船隻或有待收成的漁獲了！請先處理好再派新船。", ephemeral=True)

        self.cost, self.fish_skill_lv, self.discount_pct = self._calc_discounted_cost()
        self.duration = int(self.times * self.per_fish_time)
        from datetime import datetime, timedelta
        self.finish_time = datetime.now() + timedelta(seconds=self.duration)
        
        await self.cog.execute_fish_start(interaction, self)
