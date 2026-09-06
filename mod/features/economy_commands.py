from datetime import datetime

import discord
from discord import app_commands


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

        s_data = self.bank_cog.add_stats(interaction.guild.id, self.sender.id)
        r_data = self.bank_cog.add_stats(interaction.guild.id, self.receiver.id)

        if s_data["coin"] < self.total:
            return await interaction.response.send_message("❌ 餘額不足，轉帳取消。", ephemeral=True)

        s_data["coin"] -= self.total
        r_data["coin"] += self.amount
        self.bank_cog.save_data()

        embed = discord.Embed(title="💸 轉錢成功", color=0x2ecc71)
        embed.set_author(
            name=f"{self.sender.display_name} ➔ {self.receiver.display_name}",
            icon_url=self.sender.avatar.url if self.sender.avatar else None
        )

        embed.description = f"{self.sender.mention} 成功轉錢給 {self.receiver.mention}"

        embed.add_field(name="轉帳金額", value=f"`{self.amount:,}` 💰", inline=True)
        embed.add_field(name="手續費 (3%)", value=f"`{self.fee:,}` 💰", inline=True)
        embed.add_field(name="發送方支付", value=f"`{self.total:,}` 💰", inline=True)

        embed.add_field(name=f"{self.sender.display_name} 餘額", value=f"`{s_data['coin']:,}` 💰", inline=True)
        embed.add_field(name=f"{self.receiver.display_name} 餘額", value=f"`{r_data['coin']:,}` 💰", inline=True)

        embed.set_footer(text="轉錢操作已完成 (已扣除手續費並記錄)")
        embed.timestamp = datetime.now()

        await interaction.response.edit_message(content=None, embed=embed, view=None)

    @discord.ui.button(label="取消", style=discord.ButtonStyle.red)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="❌ 交易已取消。", embed=None, view=None)


class EconomyCommandsMixin:
    @app_commands.command(name="deposit", description="將身上的現金存入金庫")
    @app_commands.guild_only()
    async def deposit(self, interaction: discord.Interaction, amount: int):
        if amount <= 0:
            return await interaction.response.send_message("❌ 存入金額必須大於 0！", ephemeral=True)

        bank_cog = self.bot.get_cog('BankMod')
        if not bank_cog:
            return await interaction.response.send_message("❌ 系統錯誤：找不到金庫模組！", ephemeral=True)

        user_data = bank_cog.add_stats(interaction.guild.id, interaction.user.id)

        current_cash = user_data.get("coin", 0)
        if current_cash < amount:
            return await interaction.response.send_message(f"❌ 你手上的現金不足！(目前持有: `${current_cash:,}`)", ephemeral=True)

        user_data["coin"] -= amount
        user_data["bank_balance"] = user_data.get("bank_balance", 0) + amount

        bank_cog.save_data()

        embed = discord.Embed(title="🏦 金庫存款成功", color=0x2ecc71)
        embed.add_field(name="💰 存入金額", value=f"`${amount:,}`\n")
        embed.add_field(name="🏧 剩餘現金", value=f"`${user_data['coin']:,}` \n")
        embed.add_field(name="🏛️ 金庫總額", value=f"`${user_data['bank_balance']:,}` \n")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="withdraw", description="從金庫提領現金到身上")
    @app_commands.guild_only()
    async def withdraw(self, interaction: discord.Interaction, amount: int):
        if amount <= 0:
            return await interaction.response.send_message("❌ 提領金額必須大於 0！", ephemeral=True)

        bank_cog = self.bot.get_cog('BankMod')
        if not bank_cog:
            return await interaction.response.send_message("❌ 系統錯誤：找不到金庫模組！", ephemeral=True)

        user_data = bank_cog.add_stats(interaction.guild.id, interaction.user.id)

        current_bank = user_data.get("bank_balance", 0)
        if current_bank < amount:
            return await interaction.response.send_message(f"❌ 金庫存款不足！(目前存款: `${current_bank:,}`)", ephemeral=True)

        user_data["bank_balance"] -= amount
        user_data["coin"] += amount

        bank_cog.save_data()

        embed = discord.Embed(title="💵 現金提領成功", color=0x3498db)
        embed.add_field(name="💰 提領金額", value=f"`${amount:,}`")
        embed.add_field(name="🏧 剩餘存款", value=f"`${user_data['bank_balance']:,}`")
        embed.add_field(name="👜 目前持有現金", value=f"`${user_data['coin']:,}`")
        await interaction.response.send_message(embed=embed)

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

        fee = int(amount * 0.03)
        total_cost = amount + fee

        if user_data["coin"] < total_cost:
            return await interaction.response.send_message(
                f"❌ 餘額不足！你需要 `${total_cost:,}` (含手續費)，但目前只有 `${user_data['coin']:,}`",
                ephemeral=True
            )

        embed = discord.Embed(title="💸 確認轉錢", color=0xf39c12)
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
