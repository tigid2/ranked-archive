"""챔피언 스킬 이름·아이콘 표(data/dd_spells.json)를 만들어요. 사망 정보 칸에서 Q/W/E/R/패시브 아이콘에 써요.
패치마다 한 번: python3 tools/report/dd_spells.py  (Data Dragon 미러의 championFull.json을 받아요)"""
import json, os, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.normpath(os.path.join(HERE, "..", "..", "data", "dd_spells.json"))
URL = "https://raw.githubusercontent.com/noxelisdev/LoL_DDragon/master/latest/data/ko_KR/championFull.json"

d = json.load(urllib.request.urlopen(URL, timeout=60))
out = {"version": d["version"], "data": {}}
for key, c in d["data"].items():
    row = {"P": [c["passive"]["name"], "passive/" + c["passive"]["image"]["full"]]}
    for k, s in zip("QWER", c["spells"]):
        row[k] = [s["name"], "spell/" + s["image"]["full"]]
    out["data"][key] = row
json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print(OUT, len(out["data"]), "챔피언")
