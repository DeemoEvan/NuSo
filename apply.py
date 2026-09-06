import os

with open('mod/Mod.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, l in enumerate(lines):
    if r'\n' in l and 'boat_lv' in l and 'last_times' in l:
        lines[i] = "            boat_lv = data.get('boat_level', 1)\n            rod_lv = data.get('rod_level', 1)\n            last_times = data.get('times', 1)\n            view = FishingHubView(self, uid, boat_lv, rod_lv, default_times=last_times)\n"

with open('mod/Mod.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)
print('Fixed successfully')
