import os
import re

with open('mod/Mod.py', 'r', encoding='utf-8') as f:
    text = f.read()

old_code = """                boat_lv = user_data.get("boat_level", 1)
                rod_lv = user_data.get("rod_level", 1)
                hub_view = FishingHubView(self, interaction.user.id, boat_lv, rod_lv)
                embed = hub_view._generate_embed()"""

new_code = """                boat_lv = user_data.get("boat_level", 1)
                rod_lv = user_data.get("rod_level", 1)
                last_times = status.get("times", 1)
                hub_view = FishingHubView(self, interaction.user.id, boat_lv, rod_lv, default_times=last_times)
                embed = hub_view._generate_embed()"""

if old_code in text:
    text = text.replace(old_code, new_code)
    with open('mod/Mod.py', 'w', encoding='utf-8') as f:
        f.write(text)
    print("Fixed Mod.py `fish` implementation.")
else:
    print("old_code not found")
