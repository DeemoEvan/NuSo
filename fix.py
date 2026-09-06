import os

file_path = "mod/features/views/game_views.py"

with open(file_path, "r", encoding="utf-8", errors="replace") as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    clean_line = line.replace('\x00', '')
    if clean_line.strip() == "import":
        break
    if clean_line.startswith("class RedPacketView("):
        break
    new_lines.append(clean_line)

content = "".join(new_lines).rstrip() + "\n\n"

code_to_append = """class RedPacketView(discord.ui.View):
    def __init__(self, bot, sender, packets: list, total_amount: int):
        super().__init__(timeout=86400)
        self.bot = bot
        self.sender = sender
        self.packets = packets
        self.total_amount = total_amount
        self.total_count = len(packets)
        self.claimed_users = {}

    @discord.ui.button(label="搶紅包！", style=discord.ButtonStyle.danger, emoji="🧧")
    async def claim_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id in self.claimed_users:
            await interaction.response.send_message("你已經搶過這個紅包囉！", ephemeral=True)
            return

        if not self.packets:
            await interaction.response.send_message("紅包已經被搶光了！", ephemeral=True)
            return

        amount = self.packets.pop()
        self.claimed_users[interaction.user.id] = amount

        bank = getattr(self.bot, "get_cog", lambda x: None)('BankMod')
        if bank:
            bank.add_stats(interaction.guild.id, interaction.user.id, coin=amount)

        claimed_count = len(self.claimed_users)

        embed = discord.Embed(
            title=f"🧧 {self.sender.display_name} 發了紅包！",
            description=f"總金額: `{self.total_amount}` 💰\\n進度: `{claimed_count}/{self.total_count}` 包",
            color=0xff0000
        )

        if not self.packets:
            button.disabled = True
            button.label = "已搶光"

            sorted_claimed = sorted(self.claimed_users.items(), key=lambda x: x[1], reverse=True)
            result_text = "\\n".join([f"<@{uid}> 搶到 `{amt}` 💰" for uid, amt in sorted_claimed])
            embed.add_field(name="領取結果", value=result_text, inline=False)
            
            lucky_king = sorted_claimed[0][0]
            unlucky = sorted_claimed[-1][0]
            embed.set_footer(text="紅包已全數被搶完") 
            
            await interaction.response.edit_message(embed=embed, view=self)
            await interaction.followup.send(f"你搶到了 `{amount}` 💰！\\n🧧 **{self.sender.display_name}** 的紅包已全數被搶光！\\n👑 手氣王是 <@{lucky_king}>！\\n💀 窮光蛋是 <@{unlucky}>！", ephemeral=False)
        else:
            await interaction.response.edit_message(embed=embed, view=self)
            await interaction.followup.send(f"你成功搶到了 `{amount}` 💰！", ephemeral=True)
"""

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)
    f.write(code_to_append)
