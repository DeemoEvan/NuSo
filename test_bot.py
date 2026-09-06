"""跑法：python test_bot.py  —— 檢查存檔與結構，不需要連上 Discord。"""
import ast
import collections
import json
import os
import tempfile

import mod.Mod as M
from mod.bank import BankMod

ROOT = os.path.dirname(os.path.abspath(__file__))


def test_paths_inside_repo():
    """資料路徑都必須落在專案內，不能是硬編的別台機器路徑。"""
    for name in ("FISHER_PATH", "CLAIM_PATH", "KEYWORDS_PATH", "BJ_CONTROL_PATH"):
        p = getattr(M.MyCommands, name)
        assert os.path.abspath(p).startswith(ROOT), f"{name} 指向專案外: {p}"


def test_no_duplicate_methods():
    """同一個 class 裡不准有同名方法 —— 後面那份會無聲蓋掉前面那份。"""
    dupes = []
    for rel in ("mod/Mod.py", "mod/bank.py", "main.py"):
        tree = ast.parse(open(os.path.join(ROOT, rel), encoding="utf-8").read())
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            seen = collections.defaultdict(list)
            for b in node.body:
                if isinstance(b, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    seen[b.name].append(b.lineno)
            dupes += [f"{rel}:{node.name}.{n} {ls}" for n, ls in seen.items() if len(ls) > 1]
    assert not dupes, "重複定義: " + ", ".join(dupes)


def test_no_disk_reload_of_bank():
    """bank.users 一旦在 await 期間被換掉，別的指令手上的 user_data 就變孤兒。"""
    src = open(os.path.join(ROOT, "mod", "Mod.py"), encoding="utf-8").read()
    assert "load_data()" not in src, "Mod.py 不該自己重新載入銀行資料"

    bank_src = open(os.path.join(ROOT, "mod", "bank.py"), encoding="utf-8").read()
    assert bank_src.count("self.users = self.load_data()") == 1, \
        "bank.py 只該在 __init__ 載入一次"


def test_fisher_roundtrip():
    """寫入→讀回→刪除，最後一筆刪掉後檔案必須真的變空。"""
    cog = M.MyCommands.__new__(M.MyCommands)
    with tempfile.TemporaryDirectory() as d:
        cog.FISHER_PATH = os.path.join(d, "active_fishers.json")

        cog.update_fisher("111", {"total_reward": 500, "guild_id": 1})
        cog.update_fisher("222", {"total_reward": 900, "guild_id": 1})
        assert set(cog.get_all_fishers()) == {"111", "222"}, "新增第二個人蓋掉了第一個人"
        assert cog.get_all_fishers()["111"]["total_reward"] == 500

        cog.remove_fisher("111")
        assert set(cog.get_all_fishers()) == {"222"}

        cog.remove_fisher("222")
        assert cog.get_all_fishers() == {}, "刪掉最後一筆後紀錄還在，會被重複結算"


def test_bank_save_is_atomic():
    """save_data 寫到一半失敗，不能把正式存檔洗掉。"""
    with tempfile.TemporaryDirectory() as d:
        bank = BankMod.__new__(BankMod)
        bank.data_file = os.path.join(d, "user_stats.json")
        bank.users = {}
        bank.add_stats(1, 42, coin=250)
        bank.save_data()

        good = json.load(open(bank.data_file, encoding="utf-8"))
        assert good["1"]["42"]["coin"] > 0

        # 讓 json.dump 寫到一半才炸掉（object() 不能序列化）
        bank.users = {"1": {"42": {"coin": object()}}}
        try:
            bank.save_data()
        except TypeError:
            pass
        else:
            raise AssertionError("預期要拋 TypeError")

        assert json.load(open(bank.data_file, encoding="utf-8")) == good, \
            "寫檔中途失敗把正式存檔洗掉了"


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            fn()
            print(f"PASS {name}")
