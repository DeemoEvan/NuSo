import asyncio
import random
from datetime import datetime, timedelta

import discord
from discord import app_commands


class FishCommandsMixin:
    @app_commands.command(name="fish", description="開始掛機釣魚（漁船影響速度、魚竿影響品質；次數 1~5000）")
    @app_commands.describe(times="釣魚次數（1~5000，預設 1）")
    @app_commands.guild_only()
    async def fish(self, interaction: discord.Interaction, times: int = 1):
        uid = interaction.user.id
        now = datetime.now()
        all_fishers = self.get_all_fishers()
        uid_str = str(uid)
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
                active_view = self._make_fish_active_view(uid)
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
        if times < 1 or times > 5000:
            await interaction.response.send_message("❌ `times` 必須介於 1~5000（例如：`/fish times:100`）。", ephemeral=True)
            return
        await self._handle_fish_start(interaction, times)

    async def finish_fishing(self, ctx, user_id_str):
        all_fishers = self.get_all_fishers()
        data = all_fishers.get(user_id_str)
        if not data:
            return

        bank = self.bot.get_cog('BankMod')
        if bank:
            try:
                bank.add_stats(data.get("guild_id"), int(user_id_str), coin=data.get("total_reward", 0))
                bank.save_data()
            except Exception as e:
                print(f"⚠️ 結算時寫入銀行失敗: {e}")

        self.remove_fisher(user_id_str)

        await self._send_fishing_embed(ctx, 'result', {
            'user_name': data.get('user_name'),
            'user_id': user_id_str,
            'rarity_counts': data.get('rarity_counts', {}),
            'total_reward': data.get('total_reward', 0)
        })

    async def do_fish_settlement(self, interaction_or_ctx, user_id_str):
        await self.finish_fishing(interaction_or_ctx, user_id_str)

    async def _handle_fish_start(self, interaction, times):
        bank = self.bot.get_cog('BankMod')
        user_data = bank.add_stats(interaction.guild.id, interaction.user.id)
        boat_lv = user_data.get("boat_level", 1)
        rod_lv = user_data.get("rod_level", 1)
        fish_skill_lv = user_data.get("fish_skill_level", 1)
        
        # 基礎成本 50 元，技能每等級降低 2%（最多 20 等級 = 40% 折扣）
        skill_discount = 1.0 - (fish_skill_lv - 1) * 0.02
        base_cost = times * 50
        cost = int(base_cost * skill_discount)
        
        if user_data.get("coin", 0) < cost:
            cost_needed = cost
            await interaction.response.send_message(f"❌ 現金不足！需要 `${cost_needed:,}`。", ephemeral=True)
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
            'discount': f"{(1-skill_discount)*100:.0f}%"
        }
        view = self._make_fish_confirm_view(interaction, times, cost, boat_lv, rod_lv, per_fish_time, duration, finish_time)
        embed = self._build_fishing_embed('start', data)
        await interaction.response.send_message(embed=embed, view=view)

    async def execute_fish_start(self, interaction: discord.Interaction, fish_view):
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

        # 魚竿等級影響稀有度
        bonus = rod_lv - 1
        # 釣魚技能也能提高稀有度（每等級 +0.5 稀有/傳說的權重）
        fish_skill_bonus = max(0, (user_data.get("fish_skill_level", 1) - 1) * 0.5)
        
        adj_weights = []
        for f in self.FISH_POOL:
            w = f["chance"]
            r = f["rarity"]
            # 技能和魚竿都能提高稀有魚的機率
            if r == "傳說":
                w += bonus * 1 + fish_skill_bonus
            elif r == "史詩":
                w += bonus * 1 + fish_skill_bonus
            elif r == "稀有":
                w += int(bonus * 0.5) + fish_skill_bonus * 0.5
            elif r == "垃圾":
                w = max(5, w - int(bonus * 1.3))
            elif r == "災難":
                w = max(1, w - int(bonus * 0.5))
            else:
                w = max(10, w - int(bonus * 0.8))
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
            "fish_skill_level": user_data.get("fish_skill_level", 1)
        }
        self.update_fisher(uid, fisher_data)

        hh, remainder = divmod(duration, 3600)
        mm, ss = divmod(remainder, 60)
        time_str = (f"{hh}小時" if hh > 0 else "") + (f"{mm}分" if mm > 0 else "") + f"{ss}秒"

        active_view = self._make_fish_active_view(uid)
        embed = discord.Embed(title="🚢 漁船已出海", color=0x2ecc71)
        embed.description = (
            f"👤 **釣客：** <@{uid}>\n"
            f"🚤 **漁船等級：** `Lv.{boat_lv}`\n"
            f"🎣 **魚竿等級：** `Lv.{rod_lv}`\n"
            f"⭐ **釣魚技能：** `Lv.{user_data.get('fish_skill_level', 1)}`\n"
            f"⏱️ **作業速度：** `{fish_view.per_fish_time:.1f}s` / 竿\n"
            f"⏳ **總計耗時：** `約 {time_str}`\n"
            f"🔔 **回港時間：** `{finish_time.strftime('%H:%M:%S')}`\n\n"
            "💡 可隨時利用/fish指令查看進度或中途返航"
        )
        await interaction.response.edit_message(embed=embed, view=active_view)

    async def background_fish_finisher(self, interaction, uid, duration):
        await asyncio.sleep(duration)

        all_fishers = self.get_all_fishers()
        if str(uid) in all_fishers:
            bank = self.bot.get_cog('BankMod')
            if not bank:
                print(f"❌ 無法取得銀行 Cog")
                return
            data = all_fishers[str(uid)]
            
            # 初始化變數
            level_ups = 0
            current_level = 1
            total_skill_exp = 0
            new_fish_list = []
            
            try:
                user_data = bank.add_stats(data.get("guild_id"), uid, coin=data.get("total_reward", 0))
                
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
                
                # 更新圖鑑
                fish_dex = user_data.get("fish_dex", {})
                new_fish_list = []
                for fish in data.get("fish_caught", []):
                    fish_id = str(fish.get("id", 0))
                    is_new = fish_id not in fish_dex
                    if is_new:
                        new_fish_list.append(fish)
                    fish_dex[fish_id] = fish_dex.get(fish_id, 0) + 1
                
                user_data["fish_dex"] = fish_dex
                
                print(f"✅ 用戶 {uid} - 技能經驗 +{total_skill_exp} (等級 {current_level}, 剩餘 EXP {user_data['fish_skill_exp']})")
                
                bank.save_data()
            except Exception as e:
                import traceback
                print(f"❌ background finisher 存入獎金失敗: {e}")
                print(traceback.format_exc())
            try:
                self.remove_fisher(str(uid))
            except Exception:
                pass

            summary = "\n".join([f"• {r}: {count}次" for r, count in data["rarity_counts"].items()])

            embed = discord.Embed(title="🏁 漁船回港結算", color=0xf1c40f)
            embed.description = f"<@{uid}> 你的船隊已滿載而歸！"
            embed.add_field(name="📊 捕獲統計", value=f"```\n{summary}\n```", inline=False)
            embed.add_field(name="💰 最終收益", value=f"**`${data.get('total_reward',0):,}`**", inline=True)
            
            # 技能經驗信息
            if level_ups > 0:
                embed.add_field(name="⭐ 釣魚技能", value=f"**升級了 {level_ups} 等！** 現在 `Lv.{current_level}` 🎉", inline=True)
            else:
                embed.add_field(name="⭐ 釣魚技能", value=f"`Lv.{current_level}` (+{total_skill_exp} 經驗)", inline=True)
            
            # 新魚種通知
            if new_fish_list:
                new_fish_text = "\n".join([f"{f.get('emoji')} **{f.get('name')}** ({f.get('rarity')})" for f in new_fish_list])
                embed.add_field(
                    name="🎉 新魚種解鎖",
                    value=new_fish_text,
                    inline=False
                )

            view = self._make_fishing_view(interaction)

            sent = False
            try:
                channel = self.bot.get_channel(data.get("channel_id"))
                if channel:
                    try:
                        thread_name = f"{data.get('user_name','玩家')} 的釣魚成果"
                        thread = await channel.create_thread(name=thread_name)
                        await thread.send(embed=embed, view=view)
                        sent = True
                    except Exception:
                        await channel.send(embed=embed, view=view)
                        sent = True
            except Exception:
                sent = False

            if not sent:
                try:
                    user = self.bot.get_user(uid)
                    if user:
                        await user.send(embed=embed)
                        sent = True
                except Exception:
                    pass

    @app_commands.command(name="fish_shop", description="查看與升級你的釣魚設備")
    @app_commands.guild_only()
    async def fish_shop(self, interaction: discord.Interaction):
        bank = self.bot.get_cog('BankMod')
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
        bank = self.bot.get_cog('BankMod')
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
            color=0xff0000
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

    @app_commands.command(name="fish_skill", description="查看你的釣魚技能等級和經驗")
    @app_commands.guild_only()
    async def fish_skill(self, interaction: discord.Interaction):
        bank = self.bot.get_cog('BankMod')
        if not bank or not hasattr(bank, 'add_stats'):
            return await interaction.response.send_message("❌ 銀行模組未就緒，請稍後重試。", ephemeral=True)
        
        user_data = bank.add_stats(interaction.guild.id, interaction.user.id)
        
        try:
            skill_lv = int(user_data.get("fish_skill_level", 1))
        except (TypeError, ValueError):
            skill_lv = 1
        try:
            skill_exp = int(user_data.get("fish_skill_exp", 0))
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
            progress_text = f"[{progress_bar}] {safe_exp}/100 EXP"
            exp_left = exp_needed - safe_exp
        
        # 計算效果
        cost_discount = (skill_lv - 1) * 2
        rarity_bonus = (skill_lv - 1) * 0.5
        
        embed = discord.Embed(
            title="⭐ 釣魚技能資訊",
            description=f"{interaction.user.mention} 的釣魚技能",
            color=0x9b59b6
        )
        
        # 等級進度
        embed.add_field(
            name="📊 等級進度",
            value=f"`Lv.{skill_lv}/20` • {progress_text}",
            inline=False
        )
        
        # 技能效果
        effects = f"💰 成本優惠：`{cost_discount}%`\n✨ 稀有度加成：`+{rarity_bonus:.1f}`"
        embed.add_field(
            name="🎣 技能效果",
            value=effects,
            inline=False
        )
        
        # 升級提示
        if skill_lv < 20:
            embed.add_field(
                name="🎯 升級進度",
                value=f"還需 `{exp_left}` 經驗升級",
                inline=False
            )
        
        embed.set_footer(text="使用 /fish 進行釣魚來獲得經驗" if skill_lv < 20 else "✨ 已達到最高等級！")
        embed.timestamp = datetime.now()
        
        await interaction.response.send_message(embed=embed)
    
    def _make_progress_bar(self, current: int, total: int, length: int = 10) -> str:
        """生成進度條"""
        filled = int((current / total) * length)
        bar = "█" * filled + "░" * (length - filled)
        percentage = int((current / total) * 100)
        return f"`[{bar}] {percentage}%`"

    @app_commands.command(name="fish_dex", description="查看你的釣魚圖鑑")
    @app_commands.guild_only()
    async def fish_dex(self, interaction: discord.Interaction):
        bank = self.bot.get_cog('BankMod')
        user_data = bank.add_stats(interaction.guild.id, interaction.user.id)
        fish_dex = user_data.get("fish_dex", {})
        
        # 統計圖鑑
        total_species = len(self.FISH_POOL)
        caught_species = len(fish_dex)
        completion = round((caught_species / total_species) * 100) if total_species > 0 else 0
        
        embed = discord.Embed(
            title="📖 你的釣魚圖鑑",
            description=f"{interaction.user.mention} 已捕獲 **{caught_species}/{total_species}** 種魚類",
            color=0x3498db
        )
        
        # 按稀有度分類
        by_rarity = {}
        for fish in self.FISH_POOL:
            rarity = fish["rarity"]
            if rarity not in by_rarity:
                by_rarity[rarity] = []
            by_rarity[rarity].append(fish)
        
        rarity_order = ["傳說", "史詩", "稀有", "普通", "垃圾", "災難"]
        
        for rarity in rarity_order:
            if rarity not in by_rarity:
                continue
            
            fish_list = by_rarity[rarity]
            fish_info = []
            caught_count = 0
            
            for fish in fish_list:
                fish_id = str(fish["id"])
                count = fish_dex.get(fish_id, 0)
                caught_count += 1 if count > 0 else 0
                
                status = "✅" if count > 0 else "❌"
                name = f"{status} {fish['emoji']} {fish['name']}"
                
                if count > 0:
                    fish_info.append(f"{name} (×{count})")
                else:
                    fish_info.append(name)
            
            fish_text = "\n".join(fish_info)
            progress = f"{caught_count}/{len(fish_list)}"
            
            embed.add_field(
                name=f"{'⭐' * (6 - rarity_order.index(rarity))} {rarity} ({progress})",
                value=fish_text,
                inline=False
            )
        
        # 完成度進度條
        progress_bar = self._make_progress_bar(caught_species, total_species)
        embed.add_field(
            name="🏆 圖鑑完成度",
            value=f"{progress_bar}\n**{completion}% 完成**",
            inline=False
        )
        
        embed.set_footer(text="繼續釣魚以解鎖更多魚種")
        embed.timestamp = datetime.now()
        
        await interaction.response.send_message(embed=embed)
