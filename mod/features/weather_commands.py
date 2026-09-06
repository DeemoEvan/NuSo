from datetime import datetime

import aiohttp
import discord
from discord import app_commands


class WeatherView(discord.ui.View):
    def __init__(self, forecast_data, city_name, cwa_url):
        super().__init__(timeout=60)
        self.forecast_data = forecast_data
        self.city_name = city_name
        self.cwa_url = cwa_url

        self.add_item(discord.ui.Button(
            label="7日報導 (CWA)",
            url=self.cwa_url,
            style=discord.ButtonStyle.link,
            emoji="📅"
        ))

    def create_weather_embed(self, day_index):
        data = self.forecast_data['list'][day_index * 8]
        dt_txt = data['dt_txt']
        temp = round(data['main']['temp'])
        feel = round(data['main']['feels_like'])
        desc = data['weather'][0]['description']
        hum = data['main']['humidity']
        icon = data['weather'][0]['icon']

        day_label = "今日" if day_index == 0 else "明日"

        embed = discord.Embed(
            title=f"🌤️ {self.city_name} {day_label}天氣預報",
            description=f"**預測狀況**：{desc}\n預報時間：`{dt_txt}`",
            color=0x3498db if day_index == 0 else 0xe67e22,
            url=self.cwa_url,
            timestamp=datetime.now()
        )
        embed.set_thumbnail(url=f"http://openweathermap.org/img/wn/{icon}@2x.png")
        embed.add_field(name="🌡️ 溫度 / 體感", value=f"`{temp}°C` / `{feel}°C`", inline=True)
        embed.add_field(name="💧 濕度", value=f"`{hum}%`", inline=True)

        temp_max = round(data['main']['temp_max'])
        temp_min = round(data['main']['temp_min'])
        embed.add_field(name="📊 預計區間", value=f"最高 `{temp_max}°C` | 最低 `{temp_min}°C`", inline=False)
        embed.set_footer(text="點擊下方按鈕切換日期")
        return embed

    @discord.ui.button(label="今日天氣", style=discord.ButtonStyle.primary, emoji="🏠")
    async def today_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = self.create_weather_embed(0)
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="明天天氣", style=discord.ButtonStyle.success, emoji="⏭️")
    async def tomorrow_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = self.create_weather_embed(1)
        await interaction.response.edit_message(embed=embed, view=self)


class WeatherCommandsMixin:
    @app_commands.command(name="weather", description="查詢城市天氣，可點選按鈕查看明天預報")
    @app_commands.describe(city="請輸入城市名稱 (例如: Taipei)")
    async def weather(self, interaction: discord.Interaction, city: str):
        api_key = "b171e1ded37b0ad51a1a33157b263ea9"
        url = f"http://api.openweathermap.org/data/2.5/forecast?q={city}&appid={api_key}&units=metric&lang=zh_tw"

        await interaction.response.defer()

        cwa_map = {
            "Taipei": "63", "New Taipei": "65", "Taoyuan": "68", "Taichung": "66",
            "Tainan": "67", "Kaohsiung": "64", "Keelung": "10017", "Hsinchu": "10018",
            "Miaoli": "10005", "Changhua": "10007", "Nantou": "10008", "Yunlin": "10009",
            "Chiayi": "10010", "Pingtung": "10013", "Yilan": "10002", "Hualien": "10015",
            "Taitung": "10014", "Penghu": "10016", "Kinmen": "09020", "Lienchiang": "09007"
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    city_name = data['city']['name']

                    cwa_id = "index"
                    for key, val in cwa_map.items():
                        if key.lower() in city.lower():
                            cwa_id = f"County.html?CID={val}"
                            break
                    cwa_url = f"https://www.cwa.gov.tw/V8/C/W/County/{cwa_id}"

                    view = WeatherView(data, city_name, cwa_url)
                    embed = view.create_weather_embed(0)
                    await interaction.followup.send(embed=embed, view=view)
                else:
                    await interaction.followup.send(f"❌ 找不到城市：`{city}`，請確認英文拼字。", ephemeral=True)
