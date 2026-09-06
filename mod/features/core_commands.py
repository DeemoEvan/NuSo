import asyncio
import random

import discord
from discord import app_commands


class CoreCommandsMixin:
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

        bank = self.bot.get_cog('BankMod')
        if not bank:
            return await interaction.response.send_message("❌ 系統錯誤，找不到銀行模組！", ephemeral=True)
        try:
            bank.add_stats(interaction.guild.id, interaction.user.id, coin=100000)
            bank.save_data()
        except Exception as e:
            print(f"[紅包] 發錢失敗: {e}")
            return await interaction.response.send_message("❌ 發放金幣時發生錯誤，請聯絡管理員。", ephemeral=True)

        user_claims.append(code)
        claims[uid] = user_claims
        self.save_claims(claims)

        embed = discord.Embed(title="🧧 新春大紅包領取成功！", color=0xFF0000)
        embed.description = "恭喜你獲得了 100,000 金幣！祝你大年初一開春大吉！"
        embed.set_footer(text=f"本次領取密語：{code}")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="choose", description="幫你從多個選項中選一個")
    @app_commands.describe(選項="請輸入選項，空格分隔")
    async def choose(self, interaction: discord.Interaction, 選項: str):
        selection_list = 選項.split()
        picked = random.choice(selection_list) if selection_list else "沒給選項標題"
        await interaction.response.send_message(f"NuSo 幫你選了：**{picked}**")

    @app_commands.command(name="ping", description="檢查延遲")
    async def ping(self, interaction: discord.Interaction):
        await interaction.response.send_message(f"機器人延遲為 {round(self.bot.latency * 1000)}ms")

    @app_commands.command(name="idiom_start", description="開始一個成語接龍遊戲")
    @app_commands.describe(word="請輸入一個四字成語作為開頭")
    async def idiom_start(self, interaction: discord.Interaction, word: str):
        if len(word) != 4:
            await interaction.response.send_message("請輸入一個四字成語！", ephemeral=True)
            return
        self.last_word = word
        await interaction.response.send_message(f"🏁 成語接龍開始！\n當前成語：**{word}**\n請接下一個字：**{word[-1]}**")

    @app_commands.command(name="secret", description="丟出一個只有特定人才能解鎖的訊息")
    @app_commands.guild_only()
    async def drop_secret(self, interaction: discord.Interaction):
        await interaction.response.send_modal(self._make_secret_modal())

    @app_commands.command(name="rob_bank", description="發起一場大型搶劫行動（主持人確認後開始）")
    @app_commands.guild_only()
    async def rob_bank_cmd(self, interaction: discord.Interaction):
        uid = interaction.user.id
        cost = 10000
        if uid in self.active_robbers:
            return await interaction.response.send_message("❌ 你已經在隊伍中或行動中，不能重複發起！", ephemeral=True)

        bank = self.bot.get_cog('BankMod')
        user_data = bank.add_stats(interaction.guild.id, interaction.user.id, coin=0)

        if user_data['coin'] < cost:
            return await interaction.response.send_message(f"❌ 錢不夠支付準備金 {cost:,}！", ephemeral=True)

        self.active_robbers.add(uid)

        view = self._make_rob_bank_view(interaction, cost)
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
        if not bank:
            return

        gid = interaction.guild.id
        cost = 10000
        fail_fee = 50000
        count = len(participants)

        try:
            for p in participants:
                bank.add_stats(gid, p.id, coin=-cost)
            bank.save_data()

            current_content = f"👥 **參與成員：** {', '.join([p.display_name for p in participants])}\n🎬 **行動代號：百萬劫案**"
            try:
                drama_msg = await interaction.channel.send(current_content)
            except discord.Forbidden:
                return await interaction.followup.send("⚠️ 機器人缺少在該頻道『傳送訊息』的權限！", ephemeral=True)

            stages = ['prep', 'entry', 'vault_drill', 'vault_open', 'loot', 'police', 'skirmish', 'escape']
            for stage in stages:
                await asyncio.sleep(2.0)
                lucky_guy = random.choice(participants).display_name
                plot_template = random.choice(self.ROB_PLOTS[stage])
                new_line = f"\n> {plot_template.format(user=lucky_guy)}"
                current_content += new_line
                try:
                    await drama_msg.edit(content=current_content)
                except Exception:
                    break
                if stage in ['vault_drill', 'skirmish']:
                    await asyncio.sleep(1.5)

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
            print(f"🚨 搶劫邏輯發生錯誤: {e}")
            await interaction.channel.send("🚨 行動中途發生意外（系統錯誤），計畫被迫中止！")

        finally:
            for p in participants:
                if p.id in self.active_robbers:
                    self.active_robbers.remove(p.id)
            print("🔓 搶案流程結束，已釋放所有參與者狀態。")
