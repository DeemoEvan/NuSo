import os

filepath = 'mod/Mod.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace literal \n with actual newline characters
fixed_content = content.replace("\\n            ", "\n            ")

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(fixed_content)

print(f"Fixed literal \\n characters in {filepath}")
