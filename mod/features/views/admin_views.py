import json
import os

import discord


def load_allowed_users():
    config_path = "config.json"
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f).get("allowed_users", [])
    return []


def save_allowed_users(user_list):
    with open("config.json", "w", encoding="utf-8") as f:
        json.dump({"allowed_users": user_list}, f, indent=4)


class SecretModal(discord.ui.Modal, title='發布訊息'):
    secret_text = discord.ui.TextInput(
        label='內容',
        style=discord.TextStyle.paragraph,
        placeholder='在此輸入內容...',
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        view = SecretView(self.secret_text.value)
        embed = discord.Embed(
            title="隱藏訊息發好囉",
            description="點擊下方按鈕解鎖內容",
            color=0x2b2d31
        )
        embed.set_footer(text=f"由 {interaction.user.display_name} 發布")
        await interaction.response.send_message(embed=embed, view=view)


class SecretView(discord.ui.View):
    def __init__(self, secret_content):
        super().__init__(timeout=None)
        self.content = secret_content

    @discord.ui.button(label="Unlock", style=discord.ButtonStyle.secondary)
    async def unlock(self, interaction: discord.Interaction, button: discord.ui.Button):
        allowed_ids = load_allowed_users()
        if str(interaction.user.id) in allowed_ids:
            await interaction.response.send_message(f"{self.content}", ephemeral=True)
        else:
            await interaction.response.send_message("❌ 你的 ID 不在授權名單中。", ephemeral=True)


class RobBankView(discord.ui.View):
    def __init__(self, interaction, cog_instance, cost):
        super().__init__(timeout=300)
        self.interaction = interaction
        self.cog = cog_instance
        self.cost = cost
        self.participants = [interaction.user]

    @discord.ui.button(label="加入", style=discord.ButtonStyle.danger)
    async def join_rob(self, interaction: discord.Interaction, button: discord.ui.Button):
        uid = interaction.user.id

        if uid in self.cog.active_robbers:
            return await interaction.response.send_message("❌ 你已經在行動中，不能重複參加！", ephemeral=True)

        if interaction.user in self.participants:
            return await interaction.response.send_message("你已經在隊伍中了！", ephemeral=True)

        bank = self.cog.bot.get_cog('BankMod')
        user_data = bank.add_stats(interaction.guild.id, uid, coin=0)
        if user_data['coin'] < self.cost:
            return await interaction.response.send_message(f"❌ 錢不夠支付準備金 {self.cost:,}！", ephemeral=True)

        self.participants.append(interaction.user)
        self.cog.active_robbers.add(uid)

        if interaction.message and len(interaction.message.embeds) > 0:
            embed = interaction.message.embeds[0]
            participant_list = "\n".join([f"• {p.display_name}" for p in self.participants])
            embed.description = (
                f"**發起人：** {self.interaction.user.mention}\n"
                f"**準備金：** `${self.cost:,}`\n\n"
                f"👥 **已加入成員 ({len(self.participants)} 人)：**\n{participant_list}\n\n"
                "📋 **主持人確認人數後按「確認開始」按鈕**"
            )
            await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="確認開始", style=discord.ButtonStyle.green)
    async def confirm_start(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.interaction.user.id:
            return await interaction.response.send_message("❌ 只有發起人（主持人）可以確認開始！", ephemeral=True)

        for item in self.children:
            item.disabled = True
        if interaction.message and len(interaction.message.embeds) > 0:
            embed = interaction.message.embeds[0]
            participant_list = "\n".join([f"• {p.display_name}" for p in self.participants])
            embed.description = (
                f"**發起人：** {self.interaction.user.mention}\n"
                f"**準備金：** `${self.cost:,}`\n\n"
                f"👥 **已加入成員 ({len(self.participants)} 人)：**\n{participant_list}\n\n"
                "🚀 **行動開始中...**"
            )
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            await interaction.response.defer()
        await self.cog.start_robbery_logic(self.interaction, self.participants)

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        try:
            await self.interaction.edit_original_response(view=self)
        except Exception:
            pass
