import json
import os
import random
from datetime import datetime

import discord
from discord import app_commands


def load_allowed_users():
    config_path = "config.json"
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f).get("allowed_users", [])
    return []


def save_allowed_users(user_list):
    with open("config.json", "w", encoding="utf-8") as f:
        json.dump({"allowed_users": user_list}, f, indent=4)


class AdminProfileCommandsMixin:
    @app_commands.command(name="manage_secret", description="【Admin】Manage the secret message access list")
    @app_commands.describe(action="add or remove", target="User")
    async def manage_secret(self, interaction: discord.Interaction, action: str, target: discord.Member):
        your_id = 1170599058717560875
        if interaction.user.id != your_id:
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

    @app_commands.command(name="profile", description="查看你在本伺服器的個人資料與資產概況")
    @app_commands.guild_only()
    async def profile(self, interaction: discord.Interaction):
        await interaction.response.defer()

        gid, uid = str(interaction.guild.id), str(interaction.user.id)
        bank = self.bot.get_cog('BankMod')
        if not bank:
            return await interaction.followup.send("❌ 銀行系統模組未啟動。")

        bank.users = bank.load_data()
        user_data = bank.add_stats(interaction.guild.id, interaction.user.id, coin=0)

        coin = user_data.get("coin", 0)
        exp = user_data.get("exp", 0)

        user_stocks = user_data.get("stocks", {})
        total_stock_value = 0
        cache = self.load_stock_cache()
        today = datetime.now().strftime("%Y-%m-%d")
        daily_cache = cache.get(today, {})

        stock_summary = ""
        if user_stocks:
            for ticker, amount in user_stocks.items():
                info = daily_cache.get(ticker)
                if info:
                    value = info['price'] * amount
                    total_stock_value += value
                stock_summary += f"📈 {ticker}: `{amount:,}` 股\n"
        else:
            stock_summary = "目前無持股"

        embed = discord.Embed(
            title=f"{interaction.user.display_name} 的個人檔案",
            color=interaction.user.color,
            timestamp=datetime.now()
        )

        if interaction.user.avatar:
            embed.set_thumbnail(url=interaction.user.avatar.url)

        embed.add_field("經驗值: `{exp}`", inline=True)
        embed.add_field(name="💰 現金餘額", value=f"`{coin:,}` 金幣", inline=True)

        net_worth = coin + int(total_stock_value)
        embed.add_field(name="🏦 總資產淨值", value=f"**`{net_worth:,}`** 金幣", inline=False)
        embed.add_field(name="📦 股票庫存", value=stock_summary, inline=False)
        embed.set_footer(text=f"{interaction.user.display_name}")

        await interaction.followup.send(embed=embed)

    @app_commands.command(name="spin", description="花費金幣進行幸運大轉盤 (下注 5000)")
    @app_commands.guild_only()
    async def spin(self, interaction: discord.Interaction):
        bank = self.bot.get_cog('BankMod')
        if not bank:
            return await interaction.response.send_message("❌ 銀行系統未啟動。")

        bet = 5000
        user_data = bank.add_stats(interaction.guild.id, interaction.user.id, coin=0)
        if user_data["coin"] < bet:
            return await interaction.response.send_message(f"❌ 你的餘額不足！需要 `{bet:,}` 金幣。", ephemeral=True)

        user_data["coin"] -= bet

        items = ["🍎", "🍋‍🟩", "🍎", "🍋", "🍋‍🟩", "🍋", "🍇", "💎", "⭐"]
        result = [random.choice(items) for _ in range(3)]
        res_str = " | ".join(result)

        win_amount = 0
        if result[0] == result[1] == result[2]:
            if result[0] == "💎":
                win_amount = 100000
            elif result[0] == "⭐":
                win_amount = 5000
            else:
                win_amount = 50000
            msg = "🎊 **超級大獎！** 🎊"
        elif result[0] == result[1] or result[1] == result[2] or result[0] == result[2]:
            win_amount = 11000
            msg = "✨ **小獎！** ✨"
        else:
            msg = "💀 **可惜沒中獎，下次加油！**"

        user_data["coin"] += win_amount
        bank.save_data()

        embed = discord.Embed(title="🎡 NuSo 幸運轉盤", color=0xff8c00)
        embed.add_field(name="🎰 轉盤結果", value=f"```\n[ {res_str} ]\n```", inline=False)
        embed.add_field(name="結果", value=msg, inline=True)
        if win_amount > 0:
            embed.add_field(name="獲得獎金", value=f"💰 `{win_amount:,}`", inline=True)
        embed.set_footer(text=f"消耗: {bet:,} | 剩餘餘額: {user_data['coin']:,}")
        await interaction.response.send_message(embed=embed)
