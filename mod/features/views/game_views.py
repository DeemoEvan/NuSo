import json
import os
import random

import discord


BLACKJACK_AVATAR_URL = None


class BlackjackView(discord.ui.View):
    def _rank_to_key(self, rank):
        face_map = {"J": "j", "Q": "q", "K": "k", "A": "a"}
        return face_map.get(rank, rank)

    def __init__(self, interaction, p_hand, d_hand, deck, calc_func, bank, bet, cog_instance):
        super().__init__(timeout=180)
        self.main_interaction = interaction
        self.p_hand = p_hand
        self.d_hand = d_hand
        self.deck = deck
        self.calc = calc_func
        self.bank = bank
        self.bet = bet
        self.uid = str(interaction.user.id)
        self.gid = str(interaction.guild.id)
        self.cog = cog_instance
        self.root_dir = os.path.dirname(os.path.abspath(__file__))
        self.DATA_PATH = os.path.join(self.root_dir, "active_fishers.json")
        self.suits_map = {"♠️": "s", "♥️": "h", "♦️": "d", "♣️": "c"}
        self.card_emoji_ids = {
            "sq": 1472706402933018726, "sk": 1472706401557020763, "sj": 1472706399996743731, "sa": 1472706398029746329,
            "s10": 1472706396343505030, "s9": 1472706394628165642, "s8": 1472706393004965888, "s7": 1472706391629107321,
            "s6": 1472706389938933834, "s5": 1472706388374589560, "s4": 1472706386889670821, "s3": 1472706385266475113,
            "s2": 1472706384217768150,
            "hq": 1472706380468191446, "hk": 1472706378538680432, "hj": 1472706376986791996, "ha": 1472706375183368267,
            "h10": 1472706373749047464, "h9": 1472706372608069906, "h8": 1472706370875691210, "h7": 1472706369327988927,
            "h6": 1472706367931420722, "h5": 1472706365977002186, "h4": 1472706364039102556, "h3": 1472706362214584340,
            "h2": 1472706360700567552,
            "dq": 1472706358850752532, "dk": 1472706357139341444, "dj": 1472706355117953114, "da": 1472706353599615157,
            "d10": 1472706351971958939, "d9": 1472706349652508722, "d8": 1472706348109271060, "d7": 1472706346397995028,
            "d6": 1472706344233599242, "d5": 1472706342606082161, "d4": 1472706341230608414, "d3": 1472706339842031824,
            "d2": 1472706338160377926,
            "cq": 1472706336142790770, "ck": 1472706334481973419, "cj": 1472706332749598770, "ca": 1472706330988122245,
            "c10": 1472706329499013212, "c9": 1472706327401726165, "c8": 1472706325761888336, "c7": 1472706324340015225,
            "c6": 1472706322926669844, "c5": 1472706321383162012, "c4": 1472706319793393860, "c3": 1472706318304284833,
            "c2": 1472706316375031879,
            "card_back": 1472706314969944247,
        }

    def _get_bj_control(self):
        try:
            bj_path = os.path.join(self.root_dir, "blackjack_control.json")
            if os.path.exists(bj_path):
                with open(bj_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return data.get(str(self.uid))
        except Exception as e:
            print(f"[BJ控制] 讀取失敗: {e}")
        return None

    def _card_value(self, card):
        rank = card[:-2]
        if rank in ("J", "Q", "K"):
            return 10
        if rank == "A":
            return 11
        return int(rank)

    def get_controlled_card(self, who, for_dealer=False):
        control = self._get_bj_control()
        mode = (control or {}).get("mode", "").lower()
        if mode == 'w':
            if who == 'player':
                cur = self.calc(self.p_hand)
                if cur >= 18:
                    safe_cards = []
                    for i, card in enumerate(self.deck):
                        val = self.calc(self.p_hand + [card])
                        if val <= 21:
                            rank = str(card[:-2]).upper()
                            if rank in ('A', '2', '3'):
                                safe_cards.append((i, card))
                    if safe_cards:
                        idx, card = safe_cards[0]
                        return self.deck.pop(idx)
                for i, card in enumerate(self.deck):
                    val = self.calc(self.p_hand + [card])
                    if val <= 21:
                        return self.deck.pop(i)
                return self.deck.pop()
            elif who == 'dealer' and for_dealer:
                p_val = self.calc(self.p_hand)
                d_val = self.calc(self.d_hand)
                if p_val >= 19:
                    for i, card in enumerate(self.deck):
                        val = self.calc(self.d_hand + [card])
                        if val < p_val and val >= 17:
                            return self.deck.pop(i)
                    min_card = None
                    min_val = 99
                    for i, card in enumerate(self.deck):
                        val = self.calc(self.d_hand + [card])
                        if val <= 21 and val < min_val:
                            min_card = (i, card)
                            min_val = val
                    if min_card:
                        idx, card = min_card
                        return self.deck.pop(idx)
                elif p_val <= 16:
                    for i, card in enumerate(self.deck):
                        val = self.calc(self.d_hand + [card])
                        if val > 21:
                            return self.deck.pop(i)
                return self.deck.pop()
        if mode == 'l':
            if who == 'player':
                cur = self.calc(self.p_hand)
                if cur <= 16:
                    idx = random.randrange(len(self.deck))
                    return self.deck.pop(idx)
                else:
                    for i, card in enumerate(self.deck):
                        val = self.calc(self.p_hand + [card])
                        if val > 21:
                            return self.deck.pop(i)
                    max_card = max(enumerate(self.deck), key=lambda x: self._card_value(x[1]))
                    return self.deck.pop(max_card[0])
            elif who == 'dealer' and for_dealer:
                p_val = self.calc(self.p_hand)
                d_val = self.calc(self.d_hand)
                best = None
                for i, card in enumerate(self.deck):
                    val = self.calc(self.d_hand + [card])
                    if d_val < 17 and val > p_val and val <= 21:
                        if val == 21:
                            return self.deck.pop(i)
                        if not best or val < best[1]:
                            best = (i, val)
                if best:
                    return self.deck.pop(best[0])
        return self.deck.pop()

    def get_card_emoji(self, card_str, use_card_back=False):
        if use_card_back:
            eid = self.card_emoji_ids.get("card_back")
            if eid:
                return f"<:card_back:{eid}>"
            return "🂠"
        rank = card_str[:-2]
        suit_icon = card_str[-2:]
        suit = self.suits_map.get(suit_icon, "s")
        key = f"{suit}{self._rank_to_key(rank)}"
        eid = self.card_emoji_ids.get(key)
        if eid:
            return f"<:{key}:{eid}>"
        return "🃏"

    @discord.ui.button(label="要牌", style=discord.ButtonStyle.primary)
    async def hit(self, interaction: discord.Interaction, button: discord.ui.Button):
        if str(interaction.user.id) != self.uid:
            return await interaction.response.send_message("這不是你的牌局！", ephemeral=True)

        card = self.get_controlled_card('player')
        self.p_hand.append(card)
        p_val = self.calc(self.p_hand)

        if len(self.p_hand) == 5 and p_val <= 21:
            msg, res_type, color = "🎉 恭喜！過五關！", 'win', discord.Color.purple()
            payout = int(self.bet + (self.bet * 1.25))
            pnl_delta = int(self.bet * 1.25)

            self.clear_items()
            self.bank.users = self.bank.load_data()
            user_data = self.bank.add_stats(self.gid, self.uid, coin=payout)
            user_data["blackjack_pnl"] = user_data.get("blackjack_pnl", 0) + pnl_delta
            user_data["blackjack_wins"] = user_data.get("blackjack_wins", 0) + 1
            user_data["blackjack_games"] = user_data.get("blackjack_games", 0) + 1
            self.bank.save_data()

            d_val = self.calc(self.d_hand)
            d_val_str = f"{d_val} 🔥" if d_val == 21 else f"{d_val}"
            d_emojis = " ".join([self.get_card_emoji(c) for c in self.d_hand])
            p_val_str = f"{p_val} 🔥" if p_val == 21 else f"{p_val}"
            p_emojis = " ".join([self.get_card_emoji(c) for c in self.p_hand])

            bj_pnl = user_data.get("blackjack_pnl", 0)
            pnl_str = f"{bj_pnl:+,}" if bj_pnl != 0 else "0"
            win_loss_line = f"✅ 贏得 {int(self.bet * 1.25):,} 💰"

            total_games = user_data.get("blackjack_games", 1)
            wins = user_data.get("blackjack_wins", 0)
            win_rate = (wins / total_games * 100) if total_games > 0 else 0

            embed = discord.Embed(
                title="🎰 21點 遊戲結算 (5-Card Charlie)",
                description=(
                    f"### {msg}\n\n"
                    f"### {win_loss_line}\n\n"
                    f"➡️ 勝率 {win_rate:.1f}% 總場次 {total_games:,}\n\n"
                    f"**🎰 莊家手牌：**\n# {d_val_str} {d_emojis}\n\n"
                    f"**你的手牌：**\n# {p_val_str} {p_emojis}"
                ),
                color=color
            )
            embed.set_footer(text=f"下注: {self.bet:,} | 餘額: {user_data.get('coin', 0):,} | 總盈虧: {pnl_str}", icon_url=interaction.user.display_avatar.url)
            if BLACKJACK_AVATAR_URL:
                embed.set_thumbnail(url=BLACKJACK_AVATAR_URL)

            retry_btn = discord.ui.Button(label=f"再玩一局 (${self.bet:,})", style=discord.ButtonStyle.blurple, emoji="🔄")

            async def retry_callback(ri: discord.Interaction):
                if str(ri.user.id) != self.uid:
                    return
                await self.cog.start_blackjack(ri, self.bet)

            retry_btn.callback = retry_callback
            self.add_item(retry_btn)

            double_bet = int(self.bet) * 2
            double_retry_btn = discord.ui.Button(label=f"雙倍下注 (${double_bet:,})", style=discord.ButtonStyle.danger, emoji="🔥")

            async def double_retry_callback(ri: discord.Interaction):
                if str(ri.user.id) != self.uid:
                    return
                await self.cog.start_blackjack(ri, double_bet)

            double_retry_btn.callback = double_retry_callback
            self.add_item(double_retry_btn)

            user_balance = user_data.get('coin', 0)
            if user_balance > 0:
                all_in_btn = discord.ui.Button(label=f"All In (${user_balance:,})", style=discord.ButtonStyle.danger, emoji="🤑")

                async def all_in_callback(ri: discord.Interaction):
                    if str(ri.user.id) != self.uid:
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
                        await self.cog.start_blackjack(cri, final_bal)

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
                self.add_item(all_in_btn)

            await interaction.response.edit_message(embed=embed, view=self)
            return

        if p_val > 21:
            await self.finish_game(interaction, "💥 你爆牌了！莊家獲勝。", discord.Color.red(), 'loss')
        else:
            await self.update_display(interaction)

    @discord.ui.button(label="結束", style=discord.ButtonStyle.danger)
    async def stand(self, interaction: discord.Interaction, button: discord.ui.Button):
        if str(interaction.user.id) != self.uid:
            return await interaction.response.send_message("這不是你的牌局！", ephemeral=True)

        d_val = self.calc(self.d_hand)
        while d_val < 17:
            card = self.get_controlled_card('dealer', for_dealer=True)
            self.d_hand.append(card)
            d_val = self.calc(self.d_hand)

        p_val = self.calc(self.p_hand)
        if d_val > 21:
            msg, res_type, color = "🎊 莊家爆牌！你贏了！", 'win', discord.Color.green()
        elif p_val > d_val:
            msg, res_type, color = f"🎉 你以 {p_val} 點擊敗莊家 {d_val} 點！", 'win', discord.Color.green()
        elif p_val < d_val:
            msg, res_type, color = f"👻 莊家 {d_val} 點勝出，你輸了。", 'loss', discord.Color.red()
        else:
            msg, res_type, color = "🤝 雙方平手，退回賭注。", 'draw', discord.Color.light_grey()

        await self.finish_game(interaction, msg, color, res_type)

    def _build_hand_display(self, value, cards, hide_second=True):
        if hide_second and len(cards) >= 2:
            emojis = self.get_card_emoji(cards[0]) + " " + self.get_card_emoji(None, use_card_back=True)
        else:
            emojis = " ".join([self.get_card_emoji(c) for c in cards])
        val_str = f"{value} 🔥" if value == 21 else f"{value}"
        return f"# {val_str} {emojis}"

    async def update_display(self, interaction):
        embed = discord.Embed(title="🕐 21點遊戲進行中", color=0x3498db)

        d_val = self.calc([self.d_hand[0]])
        d_display = self._build_hand_display(d_val, self.d_hand, hide_second=True)
        p_val = self.calc(self.p_hand)
        p_display = self._build_hand_display(p_val, self.p_hand, hide_second=False)
        embed.description = f"**莊家手牌：**\n{d_display}\n\n**你的手牌：**\n{p_display}"

        self.bank.users = self.bank.load_data()
        user_data = self.bank.add_stats(int(self.gid), int(self.uid), coin=0)
        bj_pnl = user_data.get("blackjack_pnl", 0)
        pnl_str = f"{bj_pnl:+,}" if bj_pnl != 0 else "0"
        embed.set_footer(text=f"下注: {self.bet:,} | 餘額: {user_data.get('coin', 0):,} | 總盈虧: {pnl_str}", icon_url=interaction.user.display_avatar.url)
        if BLACKJACK_AVATAR_URL:
            embed.set_thumbnail(url=BLACKJACK_AVATAR_URL)

        await interaction.response.edit_message(embed=embed, view=self)

    async def finish_game(self, interaction, result_text, color, result_type):
        self.clear_items()

        self.bank.users = self.bank.load_data()

        payout = 0
        res = str(result_type).strip().lower()
        if res == 'win':
            payout = int(self.bet) * 2
        elif res == 'draw':
            payout = int(self.bet)

        user_data = self.bank.add_stats(self.gid, self.uid, coin=payout)

        pnl_delta = 0
        if res == 'win':
            pnl_delta = int(self.bet)
            user_data["blackjack_wins"] = user_data.get("blackjack_wins", 0) + 1
        elif res == 'loss':
            pnl_delta = -int(self.bet)
        user_data["blackjack_pnl"] = user_data.get("blackjack_pnl", 0) + pnl_delta
        user_data["blackjack_games"] = user_data.get("blackjack_games", 0) + 1
        self.bank.save_data()

        d_val = self.calc(self.d_hand)
        d_val_str = f"{d_val} 🔥" if d_val == 21 else f"{d_val}"
        d_emojis = " ".join([self.get_card_emoji(c) for c in self.d_hand])
        p_val = self.calc(self.p_hand)
        p_val_str = f"{p_val} 🔥" if p_val == 21 else f"{p_val}"
        p_emojis = " ".join([self.get_card_emoji(c) for c in self.p_hand])

        win_loss_line = ""
        if res == 'win':
            win_loss_line = f"✅ 贏得 {int(self.bet):,} 💰"
        elif res == 'loss':
            win_loss_line = f"❌ 損失 {int(self.bet):,} 💰"
        else:
            win_loss_line = "🤝 平手 退回賭注"

        total_games = user_data.get("blackjack_games", 1)
        wins = user_data.get("blackjack_wins", 0)
        win_rate = (wins / total_games * 100) if total_games > 0 else 0
        stats_line = f"➡️ 勝率 {win_rate:.1f}% 總場次 {total_games}"

        bj_pnl = user_data.get("blackjack_pnl", 0)
        pnl_str = f"{bj_pnl:+,}" if bj_pnl != 0 else "0"

        embed = discord.Embed(
            title="🎰 21點 遊戲結算",
            description=(
                f"### {result_text}\n\n"
                f"### {win_loss_line}\n\n"
                f"{stats_line}\n\n"
                f"**🎰 莊家手牌：**\n# {d_val_str} {d_emojis}\n\n"
                f"**你的手牌：**\n# {p_val_str} {p_emojis}"
            ),
            color=color
        )
        embed.set_footer(text=f"下注: {self.bet:,} | 餘額: {user_data['coin']:,} | 總盈虧: {pnl_str}", icon_url=interaction.user.display_avatar.url)
        if BLACKJACK_AVATAR_URL:
            embed.set_thumbnail(url=BLACKJACK_AVATAR_URL)

        retry_btn = discord.ui.Button(label=f"再玩一局 (${self.bet:,})", style=discord.ButtonStyle.blurple, emoji="🔄")

        async def retry_callback(ri: discord.Interaction):
            if str(ri.user.id) != self.uid:
                return
            await self.cog.start_blackjack(ri, self.bet)

        retry_btn.callback = retry_callback
        self.add_item(retry_btn)

        double_bet = int(self.bet) * 2
        double_retry_btn = discord.ui.Button(label=f"雙倍下注 (${double_bet:,})", style=discord.ButtonStyle.danger, emoji="🔥")

        async def double_retry_callback(ri: discord.Interaction):
            if str(ri.user.id) != self.uid:
                return
            await self.cog.start_blackjack(ri, double_bet)

        double_retry_btn.callback = double_retry_callback
        self.add_item(double_retry_btn)

        user_balance = user_data.get('coin', 0)
        if user_balance > 0:
            all_in_btn = discord.ui.Button(label=f"All In (${user_balance:,})", style=discord.ButtonStyle.danger, emoji="🤑")

            async def all_in_callback(ri: discord.Interaction):
                if str(ri.user.id) != self.uid:
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
                    await self.cog.start_blackjack(cri, final_bal)

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
            self.add_item(all_in_btn)

        await interaction.response.edit_message(embed=embed, view=self)

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        try:
            await self.main_interaction.edit_original_response(view=self)
        except Exception:
            pass


class DragonGateView(discord.ui.View):
    def __init__(self, interaction, user_data, bet, deck, cog, bank):
        super().__init__(timeout=60)
        self.interaction = interaction
        self.user_data = user_data
        self.bet = bet
        self.deck = deck
        self.cog = cog
        self.bank = bank
        self.gate = sorted([self.deck.pop(), self.deck.pop()], key=lambda x: x[1])
        self.is_pair = self.gate[0][1] == self.gate[1][1]

    def card_to_str(self, card):
        suit, val = card
        names = {1: "A", 11: "J", 12: "Q", 13: "K"}
        return f"{suit}{names.get(val, val)}"

    async def _start_new_round(self, interaction: discord.Interaction, bet: int):
        user_data = self.bank.add_stats(interaction.guild.id, interaction.user.id, coin=0)
        if user_data.get("coin", 0) < bet:
            return await interaction.response.send_message(
                f"❌ 餘額不足，開新局需要 `${bet:,}`，你目前只有 `${user_data.get('coin', 0):,}`。",
                ephemeral=True
            )

        self.bank.add_stats(interaction.guild.id, interaction.user.id, coin=-bet)
        self.bank.save_data()
        user_data = self.bank.add_stats(interaction.guild.id, interaction.user.id, coin=0)

        suits = ["♠️", "♥️", "♦️", "♣️"]
        deck = [(s, v) for s in suits for v in range(1, 14)]
        random.shuffle(deck)
        view = DragonGateView(interaction, user_data, bet, deck, self.cog, self.bank)

        embed = discord.Embed(title="🐉 射龍門 (Shoot the Dragon Gate)", color=0xf1c40f)
        embed.add_field(name="⚖️ 目前門柱", value=f"{view.card_to_str(view.gate[0])}  ↔️  {view.card_to_str(view.gate[1])}", inline=False)
        embed.add_field(name="💰 下注金額", value=f"`${bet:,}` (已扣除)", inline=True)
        embed.set_footer(text="提示：撞柱賠兩倍！")
        await interaction.response.edit_message(content=None, embed=embed, view=view)

    @discord.ui.button(label="射門！ (Shoot)", style=discord.ButtonStyle.green)
    async def shoot(self, interaction: discord.Interaction, button: discord.ui.Button):
        if str(interaction.user.id) != str(self.interaction.user.id):
            return await interaction.response.send_message("這不是你的賭局！", ephemeral=True)

        shoot_card = self.deck.pop()
        p1, p2 = self.gate[0][1], self.gate[1][1]
        val = shoot_card[1]

        result = ""
        pnl = 0
        coin_delta = 0
        if val == p1 or val == p2:
            result = f"😱 **撞柱了！！** 賠兩倍！"
            pnl = -self.bet * 2
            coin_delta = -self.bet
        elif p1 < val < p2:
            result = f"🎊 **射中了！** 恭喜贏得獎金！"
            pnl = self.bet
            coin_delta = self.bet * 2
        else:
            result = f"💨 **射偏了...** 賭金沒收。"
            pnl = -self.bet
            coin_delta = 0

        await self.finish_game(interaction, shoot_card, result, pnl, coin_delta)

    @discord.ui.button(label="不射 (Fold)", style=discord.ButtonStyle.gray)
    async def fold(self, interaction: discord.Interaction, button: discord.ui.Button):
        loss = self.bet // 2
        refund = self.bet - loss
        self.user_data["coin"] += refund
        self.bank.save_data()

        retry_btn = discord.ui.Button(label=f"再來一局 (${self.bet:,})", style=discord.ButtonStyle.blurple, emoji="🔄")

        async def retry_callback(ri: discord.Interaction):
            if str(ri.user.id) != str(self.interaction.user.id):
                return
            await self._start_new_round(ri, self.bet)

        retry_btn.callback = retry_callback

        double_bet = int(self.bet) * 2
        double_retry_btn = discord.ui.Button(label=f"雙倍下注 (${double_bet:,})", style=discord.ButtonStyle.danger, emoji="🔥")

        async def double_retry_callback(ri: discord.Interaction):
            if str(ri.user.id) != str(self.interaction.user.id):
                return
            await self._start_new_round(ri, double_bet)

        double_retry_btn.callback = double_retry_callback

        retry_view = discord.ui.View()
        retry_view.add_item(retry_btn)
        retry_view.add_item(double_retry_btn)

        await interaction.response.edit_message(content=f"🏳️ 你退縮了，損失一半賭金 (${loss:,})。", embed=None, view=retry_view)

    async def finish_game(self, interaction, shoot_card, result, pnl, coin_delta):
        self.user_data["coin"] += coin_delta
        self.bank.save_data()

        embed = discord.Embed(title="🐉 射龍門結果", color=0x00ff00 if pnl > 0 else 0xff0000)
        embed.add_field(name="門柱", value=f"{self.card_to_str(self.gate[0])}  ↔️  {self.card_to_str(self.gate[1])}", inline=False)
        embed.add_field(name="你的牌", value=f"🎯 **{self.card_to_str(shoot_card)}**", inline=False)
        embed.description = f"### {result}\n你的損益: `{pnl:+,}`\n目前餘額: `${self.user_data['coin']:,}`"

        retry_btn = discord.ui.Button(label=f"再來一局 (${self.bet:,})", style=discord.ButtonStyle.blurple, emoji="🔄")

        async def retry_callback(ri: discord.Interaction):
            if str(ri.user.id) != str(self.interaction.user.id):
                return
            await self._start_new_round(ri, self.bet)

        retry_btn.callback = retry_callback

        double_bet = int(self.bet) * 2
        double_retry_btn = discord.ui.Button(label=f"雙倍下注 (${double_bet:,})", style=discord.ButtonStyle.danger, emoji="🔥")

        async def double_retry_callback(ri: discord.Interaction):
            if str(ri.user.id) != str(self.interaction.user.id):
                return
            await self._start_new_round(ri, double_bet)

        double_retry_btn.callback = double_retry_callback

        retry_view = discord.ui.View()
        retry_view.add_item(retry_btn)
        retry_view.add_item(double_retry_btn)

        await interaction.response.edit_message(embed=embed, view=retry_view)

class RedPacketView(discord.ui.View):
    def __init__(self, bot, sender, packets: list, total_amount: int):
        super().__init__(timeout=180)
        self.bot = bot
        self.sender = sender
        self.packets = packets
        self.total_amount = total_amount
        self.total_count = len(packets)
        self.claimed_users = {}

    async def on_timeout(self):
        remaining = sum(self.packets)
        if remaining > 0:
            bank = getattr(self.bot, "get_cog", lambda x: None)('BankMod')
            if bank:
                bank.add_stats(self.message.guild.id, self.sender.id, coin=remaining)
        
        for item in self.children:
            item.disabled = True

        if hasattr(self, 'message') and self.message:
            embed = self.message.embeds[0]
            if remaining > 0:
                embed.description += f"\n\n**⏰ 紅包已超時！剩下 `{remaining}` 💰 已退還。**"
            else:
                embed.description += "\n\n**⏰ 紅包已超時！**"
                
            embed.set_footer(text="紅包已過期")
            
            if self.claimed_users:
                sorted_claimed = sorted(self.claimed_users.items(), key=lambda x: x[1], reverse=True)
                result_text = "\n".join([f"<@{uid}> 搶到 `{amt}` 💰" for uid, amt in sorted_claimed])
                
                # Check if field exists
                has_field = False
                for i, field in enumerate(embed.fields):
                    if field.name == "領取結果":
                        embed.set_field_at(i, name="領取結果", value=result_text, inline=False)
                        has_field = True
                        break
                if not has_field:
                    embed.add_field(name="領取結果", value=result_text, inline=False)
            
            try:
                await self.message.edit(embed=embed, view=self)
            except Exception as e:
                pass

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

        remaining_money = sum(self.packets)
        embed = discord.Embed(
            title=f"🧧 {self.sender.display_name} 發了紅包！",
            description=f"總金額: `{self.total_amount}` 💰\n剩餘金額: `{remaining_money}` 💰\n進度: `{claimed_count}/{self.total_count}` 包",
            color=0xff0000
        )

        if not self.packets:
            button.disabled = True
            button.label = "已搶光"

            sorted_claimed = sorted(self.claimed_users.items(), key=lambda x: x[1], reverse=True)
            result_text = "\n".join([f"<@{uid}> 搶到 `{amt}` 💰" for uid, amt in sorted_claimed])
            embed.add_field(name="領取結果", value=result_text, inline=False)
            
            embed.set_footer(text="紅包已全數被搶完") 
            
            await interaction.response.edit_message(embed=embed, view=self)
            await interaction.followup.send(f"你搶到了 `{amount}` 💰！\n🧧 **{self.sender.display_name}** 的紅包已全數被搶光！", ephemeral=False)
        else:
            await interaction.response.edit_message(embed=embed, view=self)
            await interaction.followup.send(f"你成功搶到了 `{amount}` 💰！", ephemeral=True)
