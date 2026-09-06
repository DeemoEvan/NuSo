import json
import os
import random

import discord
from discord import app_commands


BLACKJACK_AVATAR_URL = None


class GameCommandsMixin:
    @app_commands.command(name="blackjack", description="跟我玩一場 21 點！")
    @app_commands.describe(bet="下注金額")
    async def blackjack_cmd(self, interaction: discord.Interaction, bet: int):
        await self.start_blackjack(interaction, bet)

    async def start_blackjack(self, interaction: discord.Interaction, bet: int):
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

        suits = ["♠️", "♥️", "♦️", "♣️"]
        ranks = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]
        deck = [f"{v}{s}" for s in suits for v in ranks]
        random.shuffle(deck)

        try:
            bj_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "blackjack_control.json")
            bj_path = os.path.normpath(bj_path)
            if os.path.exists(bj_path):
                with open(bj_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                _ = data.get(str(interaction.user.id))
        except Exception as e:
            print(f"[BJ控制] 開局讀取失敗: {e}")

        p_hand = [deck.pop(), deck.pop()]
        d_hand = [deck.pop(), deck.pop()]

        view = self._make_blackjack_view(interaction, p_hand, d_hand, deck, self.calculate_hand, self.bank, bet)

        p_val = self.calculate_hand(p_hand)
        d_val_full = self.calculate_hand(d_hand)

        is_player_bj = (p_val == 21)
        is_dealer_bj = (d_val_full == 21)

        if is_player_bj or is_dealer_bj:
            payout = 0
            if is_player_bj and is_dealer_bj:
                msg, res_type, color = "🤝 雙方起手 BJ 平手！", 'draw', discord.Color.light_grey()
                payout = bet
                pnl_delta = 0
            elif is_player_bj:
                msg, res_type, color = "🎉 恭喜！起手 BlackJack (21點)！", 'win', discord.Color.gold()
                payout = int(bet + (bet * 1.5))
                pnl_delta = int(bet * 1.5)
            else:
                msg, res_type, color = "👻 莊家起手 BlackJack！你輸了。", 'loss', discord.Color.red()
                payout = 0
                pnl_delta = -bet

            user_data = self.bank.add_stats(interaction.guild.id, interaction.user.id, coin=payout)
            user_data["blackjack_pnl"] = user_data.get("blackjack_pnl", 0) + pnl_delta
            user_data["blackjack_games"] = user_data.get("blackjack_games", 0) + 1
            if res_type == 'win':
                user_data["blackjack_wins"] = user_data.get("blackjack_wins", 0) + 1
            self.bank.save_data()

            d_emojis = " ".join([view.get_card_emoji(c) for c in d_hand])
            p_emojis = " ".join([view.get_card_emoji(c) for c in p_hand])

            bj_pnl = user_data.get("blackjack_pnl", 0)
            pnl_str = f"{bj_pnl:+,}" if bj_pnl != 0 else "0"

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

            view.clear_items()

            retry_btn = discord.ui.Button(label=f"再玩一局 (${bet:,})", style=discord.ButtonStyle.blurple, emoji="🔄")

            async def retry_callback(ri: discord.Interaction):
                if str(ri.user.id) != str(interaction.user.id):
                    return
                await self.start_blackjack(ri, bet)

            retry_btn.callback = retry_callback
            view.add_item(retry_btn)

            double_bet = int(bet) * 2
            double_retry_btn = discord.ui.Button(label=f"雙倍下注 (${double_bet:,})", style=discord.ButtonStyle.danger, emoji="🔥")

            async def double_retry_callback(ri: discord.Interaction):
                if str(ri.user.id) != str(interaction.user.id):
                    return
                await self.start_blackjack(ri, double_bet)

            double_retry_btn.callback = double_retry_callback
            view.add_item(double_retry_btn)

            user_balance = user_data.get('coin', 0)
            if user_balance > 0:
                all_in_btn = discord.ui.Button(label=f"All In (${user_balance:,})", style=discord.ButtonStyle.danger, emoji="🤑")

                async def all_in_callback(ri: discord.Interaction):
                    if str(ri.user.id) != str(interaction.user.id):
                        return
                    current_stats = self.bank.add_stats(ri.guild.id, ri.user.id, coin=0)
                    bal = current_stats['coin']
                    if bal <= 0:
                        return await ri.response.send_message("❌ 沒錢了還想梭哈？", ephemeral=True)

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

    @app_commands.command(name="dragongate", description="玩一局刺激的射龍門！")
    @app_commands.describe(bet="你要下注的金額")
    async def dragongate(self, interaction: discord.Interaction, bet: int):
        if not self.bank or not hasattr(self.bank, 'add_stats'):
            self.bank = self._find_bank_cog()

        if bet < 100:
            return await interaction.response.send_message("❌ 最低下注金額為 $100！", ephemeral=True)

        user_data = self.bank.add_stats(interaction.guild.id, interaction.user.id, coin=0)

        if user_data['coin'] < bet:
            return await interaction.response.send_message(f"❌ 錢不夠！你目前只有 ${user_data['coin']:,}。", ephemeral=True)

        self.bank.add_stats(interaction.guild.id, interaction.user.id, coin=-bet)
        self.bank.save_data()
        user_data = self.bank.add_stats(interaction.guild.id, interaction.user.id, coin=0)

        suits = ["♠️", "♥️", "♦️", "♣️"]
        deck = [(s, v) for s in suits for v in range(1, 14)]
        random.shuffle(deck)

        view = self._make_dragongate_view(interaction, user_data, bet, deck)

        embed = discord.Embed(title="🐉 射龍門 (Shoot the Dragon Gate)", color=0xf1c40f)
        embed.add_field(name="⚖️ 目前門柱", value=f"{view.card_to_str(view.gate[0])}  ↔️  {view.card_to_str(view.gate[1])}", inline=False)
        embed.add_field(name="💰 下注金額", value=f"`${bet:,}` (已扣除)", inline=True)
        embed.set_footer(text="提示：撞柱賠兩倍！")

        await interaction.response.send_message(embed=embed, view=view)
