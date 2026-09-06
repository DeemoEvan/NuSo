from datetime import datetime

import discord
import requests
from discord import app_commands


class StockCommandsMixin:
    @app_commands.command(name="stock_search", description="查詢股票(目前僅限美股)")
    @app_commands.describe(股票代碼="請輸入美股代碼，例如 AAPL 或 NVDA")
    @app_commands.checks.cooldown(1, 3.0, key=lambda i: i.user.id)
    async def stock(self, interaction: discord.Interaction, 股票代碼: str):
        await interaction.response.defer()
        data, source = await self.get_stock_data(股票代碼.upper())

        if not data:
            await interaction.followup.send(f"❌ 找不到股票代碼 `{股票代碼}`")
            return

        color = 0x2ecc71 if data['change'] >= 0 else 0xe74c3c
        embed = discord.Embed(title=f"📈 {data['name']} ({data['ticker']})", color=color, timestamp=datetime.now())
        embed.add_field(name="當前價格", value=f"**{data['price']:.2f} {data['currency']}**", inline=True)
        embed.add_field(name="漲跌幅", value=f"{data['change']:+.2f} ({data['percent']:+.2f}%)", inline=True)
        embed.set_footer(text=f"來源: {source} | 更新時間: {data['update_time']}")
        await interaction.followup.send(embed=embed)

    async def get_stock_data(self, ticker):
        today = datetime.now().strftime("%Y-%m-%d")
        cache = self.load_stock_cache()

        if today in cache and ticker in cache[today]:
            return cache[today][ticker], "JSON 快取"

        api_key = "7b125e135ebb41a89911571ba40e6f94"
        url = f"https://api.twelvedata.com/quote?symbol={ticker}&apikey={api_key}"

        try:
            res = requests.get(url).json()
            if ("code" in res and res["code"] != 200) and ticker.isdigit():
                ticker_tpe = f"{ticker}:TWSE"
                res = requests.get(f"https://api.twelvedata.com/quote?symbol={ticker_tpe}&apikey={api_key}").json()
                ticker = ticker_tpe

            if "code" in res and res["code"] != 200:
                return None, None

            stock_info = {
                "name": res.get("name", ticker),
                "ticker": ticker,
                "price": float(res['close']),
                "change": float(res['change']),
                "percent": float(res['percent_change']),
                "currency": res.get("currency", "USD"),
                "update_time": datetime.now().strftime("%H:%M:%S")
            }

            if today not in cache:
                cache = {today: {}}
            cache[today][ticker] = stock_info
            self.save_stock_cache(cache)
            return stock_info, "Twelve Data API"
        except Exception:
            return None, None

    @app_commands.command(name="stock_buy", description="購買股票並記錄成本")
    @app_commands.describe(股票代碼="股票代碼 (如: AAPL, NVDA)", 數量="購買的股數")
    @app_commands.guild_only()
    async def buy_stock(self, interaction: discord.Interaction, 股票代碼: str, 數量: int):
        if 數量 <= 0:
            await interaction.response.send_message("❌ 購買數量須大於 0", ephemeral=True)
            return

        await interaction.response.defer()
        bank = self.bot.get_cog('BankMod')
        data, source = await self.get_stock_data(股票代碼.upper())
        if not data:
            await interaction.followup.send(f"❌ 無法取得 `{股票代碼}` 的價格，交易取消。")
            return

        ticker = data['ticker']
        current_price = data['price']
        total_cost = int(current_price * 數量)
        gid, uid = str(interaction.guild.id), str(interaction.user.id)

        bank.users = bank.load_data()
        user_coin = bank.users.get(gid, {}).get(uid, {}).get("coin", 0)

        if user_coin < total_cost:
            await interaction.followup.send(f"❌ 金幣不足！需要 `{total_cost:,}`，你目前只有 `{user_coin:,}`。")
            return

        bank.add_stats(gid, uid, coin=-total_cost)
        user_data = bank.users[gid][uid]

        if "stocks" not in user_data:
            user_data["stocks"] = {}
        if "stock_costs" not in user_data:
            user_data["stock_costs"] = {}

        user_data["stocks"][ticker] = user_data["stocks"].get(ticker, 0) + 數量
        user_data["stock_costs"][ticker] = user_data["stock_costs"].get(ticker, 0) + total_cost
        bank.save_data()

        embed = discord.Embed(title="✅ 買入成交", color=0x2ecc71, timestamp=datetime.now())
        embed.description = f"已購入 **{數量}** 股 **{data['name']}**"
        embed.add_field(name="成交單價", value=f"`{current_price}`", inline=True)
        embed.add_field(name="總計花費", value=f"`💰 {total_cost:,}`", inline=True)
        embed.set_footer(text=f"來源: {source}")
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="stock_mine", description="查看投資組合")
    @app_commands.guild_only()
    async def portfolio(self, interaction: discord.Interaction):
        await interaction.response.defer()
        bank = self.bot.get_cog('BankMod')
        if not bank:
            return await interaction.followup.send("銀行系統異常。")

        bank.users = bank.load_data()
        gid, uid = str(interaction.guild.id), str(interaction.user.id)
        user_data = bank.users.get(gid, {}).get(uid, {})
        user_stocks = user_data.get("stocks", {})
        user_costs = user_data.get("stock_costs", {})

        if not user_stocks:
            return await interaction.followup.send("💡 你目前手頭上沒有任何持股。")

        cache = self.load_stock_cache()
        today = datetime.now().strftime("%Y-%m-%d")
        daily_cache = cache.get(today, {})
        embed = discord.Embed(title=f"📊 {interaction.user.display_name} 的投資組合", color=0x3498db, timestamp=datetime.now())
        total_market_value = 0
        total_investment = 0

        for ticker, amount in user_stocks.items():
            stock_info = daily_cache.get(ticker)
            cost = user_costs.get(ticker, 0)
            total_investment += cost

            if stock_info:
                current_price = stock_info['price']
                market_value = current_price * amount
                total_market_value += market_value

                profit = market_value - cost
                profit_percent = (profit / cost * 100) if cost > 0 else 0

                indicator = "🔺" if profit >= 0 else "🔻"
                profit_text = f"{indicator} `{int(profit):+}` ({profit_percent:+.2f}%)"

                price_text = (
                    f"現價: `{current_price}` | 市值: `💰{int(market_value)}`\n"
                    f"淨收益: **{profit_text}**"
                )
            else:
                price_text = "*請先使用 /stock_search 更新報價以計算損益*"

            embed.add_field(name=f"📌 {ticker} ({amount} 股)", value=price_text, inline=False)

        total_profit = total_market_value - total_investment
        total_profit_percent = (total_profit / total_investment * 100) if total_investment > 0 else 0
        profit_color = "🟢" if total_profit >= 0 else "🔴"

        summary_val = (
            f"💵 現金餘額: `{user_data.get('coin', 0):,}`\n"
            f"🏛️ 持股市值: `{int(total_market_value):,}`\n"
            f"📈 總盈虧: {profit_color} **`{int(total_profit):+}`** (`{total_profit_percent:+.2f}%`)"
        )
        embed.add_field(name="💰 資產總結", value=summary_val, inline=False)

        await interaction.followup.send(embed=embed)

    @app_commands.command(name="stock_sell", description="賣出股票並結算收益")
    @app_commands.describe(股票代碼="請輸入股票代碼", 數量="請輸入賣出數量")
    @app_commands.guild_only()
    async def sell_stock(self, interaction: discord.Interaction, 股票代碼: str, 數量: int):
        if 數量 <= 0:
            await interaction.response.send_message("賣出數量必須大於 0！", ephemeral=True)
            return

        await interaction.response.defer()
        bank = self.bot.get_cog('BankMod')

        data, source = await self.get_stock_data(股票代碼.upper())
        if not data:
            await interaction.followup.send(f"❌ 無法取得股票 `{股票代碼}` 的市價，交易取消。")
            return

        ticker = data['ticker']
        gid, uid = str(interaction.guild.id), str(interaction.user.id)

        bank.users = bank.load_data()
        user_data = bank.users.get(gid, {}).get(uid, {})
        user_stocks = user_data.get("stocks", {})

        if "stock_costs" not in user_data:
            user_data["stock_costs"] = {}

        current_hold = user_stocks.get(ticker, 0)
        if current_hold < 數量:
            await interaction.followup.send(f"❌ 持股不足！你手上的 `{ticker}` 只有 `{current_hold}` 股。")
            return

        sell_price = data['price']
        total_revenue = int(sell_price * 數量)
        original_total_cost = user_data["stock_costs"].get(ticker, 0)
        cost_to_remove = int((數量 / max(1, current_hold)) * original_total_cost)

        user_data["stocks"][ticker] -= 數量
        user_data["stock_costs"][ticker] = max(0, original_total_cost - cost_to_remove)

        if user_data["stocks"][ticker] <= 0:
            user_data["stocks"].pop(ticker, None)
            user_data["stock_costs"].pop(ticker, None)

        bank.add_stats(gid, uid, coin=total_revenue)
        bank.save_data()

        embed = discord.Embed(title="📉 賣出成交", color=0xe67e22, timestamp=datetime.now())
        embed.add_field(name="股票", value=f"{data['name']} ({ticker})", inline=True)
        embed.add_field(name="賣出數量", value=f"{數量} 股", inline=True)
        embed.add_field(name="成交單價", value=f"{sell_price} {data['currency']}", inline=True)
        embed.add_field(name="獲得金幣", value=f"💰 **{total_revenue:,}**", inline=False)

        estimated_profit = total_revenue - cost_to_remove
        profit_indicator = "🟢" if estimated_profit >= 0 else "🔴"
        embed.add_field(name="本次賣出損益", value=f"{profit_indicator} `{estimated_profit:+}`", inline=True)

        embed.set_footer(text=f"餘額：{user_data['coin']:,} | 剩餘持股：{user_data['stocks'].get(ticker, 0):,}")

        await interaction.followup.send(embed=embed)
