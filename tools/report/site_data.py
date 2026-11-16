"""통계 사이트 숫자(benchmarks/sites/)를 이 판과 나란히 놓을 수 있는 모양으로 바꿔요.

사이트 숫자는 패치마다 한 번 내장 브라우저로 읽어서 저장해요(tools/sites/README.md).
파일이 없는 챔피언은 None을 돌려주고, 화면은 그 칸을 비워 둬요.
"""
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SITES = os.path.join(ROOT, "benchmarks", "sites")
LEN_EDGES = [0, 15, 20, 25, 30, 35, 40, 999]
OBJ = [("First Blood", "첫 킬", "champion"), ("First Tower", "첫 포탑", "tower"), ("First Drake", "첫 용", "dragon"),
       ("First Herald", "첫 전령", "riftHerald"), ("First Baron", "첫 바론", "baron")]


def _load(path):
    return json.load(open(path, encoding="utf-8")) if os.path.exists(path) else None


def _norm(name):
    return re.sub(r"[^a-z]", "", name.lower())


def _row(r, keys):
    return dict(zip(keys, r))


def build_site(raw, ME, OPP, x, events, frames, complete_fn, item_fn, champ_fn, perk_fn, spell_fn):
    lola = _load(os.path.join(SITES, "lolalytics", ME["championName"] + ".json"))
    ps = (_load(os.path.join(SITES, "lolps.json")) or {}).get(str(ME["championId"]))
    if not lola and not ps:
        return None
    info = raw["match"]["info"]
    dur = info["gameDuration"]
    me, opp = ME["participantId"], OPP["participantId"]
    out = {"patch": (lola or {}).get("patch") or "16.22"}

    # ---------------- 챔피언 전체 승률, 상성
    if lola:
        out["champ"] = {"win": lola["win"], "pick": lola["pick"], "games": lola["games"], "avg": lola["avg"]}
    mu = {}
    if lola:
        hit = next((r for r in lola.get("bottom", []) if _norm(r[0]) == _norm(OPP["championName"])), None)
        if hit:
            mu["world"] = {"win": hit[1], "games": hit[3]}
    if ps and str(OPP["championId"]) in ps["vs"]:
        v = ps["vs"][str(OPP["championId"])]
        mu["kr"] = {"win": v[0], "games": v[1]}
        mu["lv"] = [{"lv": lv, "first": v[i]} for lv, i in ((2, 2), (3, 3), (6, 4)) if v[i] is not None]
    if mu:
        # 이 판에서 그 레벨을 누가 먼저 찍었는지
        def lv_time(pid, lv):
            return next((e["timestamp"] for e in events if e["type"] == "LEVEL_UP" and e.get("participantId") == pid
                         and e.get("level") == lv), None)
        for r in mu.get("lv", []):
            a, b = lv_time(me, r["lv"]), lv_time(opp, r["lv"])
            r["mine"] = None if a is None or b is None else a <= b
        out["matchup"] = mu

    # ---------------- 14분 라인전 숫자 (같은 챔피언 평균과 나란히)
    if ps:
        last = len(frames) - 1

        def cs14(pid):
            f = frames[min(14, last)]["participantFrames"][str(pid)]
            return f["minionsKilled"] + f["jungleMinionsKilled"]

        def kda14(pid):
            ks = [e for e in events if e["type"] == "CHAMPION_KILL" and e["timestamp"] < 14 * 60000]
            return (sum(e.get("killerId") == pid for e in ks), sum(e.get("victimId") == pid for e in ks),
                    sum(pid in e.get("assistingParticipantIds", []) for e in ks))

        f = ps["f"]
        mk, ok = kda14(me), kda14(opp)
        mins = max(dur / 60, 1)
        n = ps["total"]
        out["lane14"] = {"games": ps["count"], "of": n, "rows": [
            {"label": "14분 CS", "me": cs14(me), "opp": cs14(opp), "avg": round(f["avgCsAt14min"]), "rank": f["avgCsAt14minRank"], "dir": 1},
            {"label": "14분 전 킬", "me": mk[0], "opp": ok[0], "avg": f["avgKillsAt14min"], "rank": f["avgKillsAt14minRank"], "dir": 1},
            {"label": "14분 전 죽음", "me": mk[1], "opp": ok[1], "avg": f["avgDeathsAt14min"], "rank": f["avgDeathsAt14minRank"], "dir": -1},
            {"label": "14분 전 도움", "me": mk[2], "opp": ok[2], "avg": f["avgAssistsAt14min"], "rank": f["avgAssistsAt14minRank"], "dir": 1},
            {"label": "포탑 방패", "me": x[me]["plates"], "opp": x[opp]["plates"], "avg": f["avgTurretPlatesTaken"], "rank": f["avgTurretPlatesTakenRank"], "dir": 1},
            {"label": "분당 챔피언 피해", "me": round(ME["totalDamageDealtToChampions"] / mins), "opp": round(OPP["totalDamageDealtToChampions"] / mins),
             "avg": round(f["avgDamageDealtToChampionsPerMin"]), "rank": f["avgDamageDealtToChampionsPerMinRank"], "dir": 1},
        ]}

    if not lola:
        return out

    # ---------------- 빌드: 코어 칸, 신발, 순서
    dd_item = json.load(open(os.path.join(ROOT, "data", "dd_item.json"), encoding="utf-8"))["data"]

    def is_boots(i):
        it = dd_item.get(str(i), {})
        return "Boots" in it.get("tags", []) and i != 1001

    bought = {}
    for e in events:
        if e["type"] == "ITEM_PURCHASED" and e.get("participantId") == me and e["itemId"] not in bought:
            bought[e["itemId"]] = e["timestamp"] // 1000
    core = sorted([(t, i) for i, t in bought.items() if complete_fn(i) and not is_boots(i)])
    boots = sorted([(t, i) for i, t in bought.items() if is_boots(i)])
    K = ["id", "win", "pick", "games", "min"]

    def opt(r):
        o = _row(r, K)
        o["item"] = item_fn(o["id"])
        return o

    slots = []
    for k, rows in enumerate(lola["slots"]):
        mine = core[k] if k < len(core) else None
        top = [opt(r) for r in rows[:3]]
        s = {"no": k + 1, "top": top, "mine": None}
        if mine:
            hit = next((opt(r) for r in rows if r[0] == mine[1]), None)
            s["mine"] = {"item": item_fn(mine[1]), "time": mine[0], "stat": hit,
                         "rank": next((i + 1 for i, r in enumerate(rows) if r[0] == mine[1]), None)}
        if mine or k < 3:
            slots.append(s)
    out["slots"] = slots
    if boots:
        hit = next((opt(r) for r in lola["boots"] if r[0] == boots[0][1]), None)
        out["boots"] = {"item": item_fn(boots[0][1]), "time": boots[0][0], "stat": hit, "top": [opt(r) for r in lola["boots"][:2]]}
    if len(core) >= 2 and boots:
        order = [i for _, i in sorted([core[0], boots[0], core[1]])]
        sets = lola["sets"]
        hit = next(((n + 1, r) for n, r in enumerate(sets) if r[0] == order), None)
        out["order"] = {"mine": [item_fn(i) for i in order],
                        "rank": hit[0] if hit else None, "stat": _row(hit[1][1:], ["win", "pick", "games"]) if hit else None,
                        "top": [dict(_row(r[1:], ["win", "pick", "games"]), items=[item_fn(i) for i in r[0]]) for r in sets[:3]]}

    # ---------------- 룬, 스펠
    by = {r[0]: _row(r, ["id", "win", "pick", "games"]) for r in lola["runes1"]}
    by2 = {r[0]: _row(r, ["id", "win", "pick", "games"]) for r in lola["runes2"]}
    st = ME["perks"]["styles"]
    out["runes"] = [dict(perk_fn(s["perk"]), stat=(by if n == 0 else by2).get(s["perk"]), main=(n == 0 and j == 0))
                    for n in (0, 1) for j, s in enumerate(st[n]["selections"])]
    mine_sp = sorted([ME["summoner1Id"], ME["summoner2Id"]])
    sp = [dict(_row(r[1:], ["win", "pick", "games"]), spells=[spell_fn(i) for i in r[0]], mine=sorted(r[0]) == mine_sp) for r in lola["spells"]]
    out["spells"] = {"top": sp[:3], "mine": next((s for s in sp if s["mine"]), None), "mineSpells": [spell_fn(i) for i in mine_sp]}

    # ---------------- 게임 길이별 승률, 첫 오브젝트
    out["length"] = [{"from": LEN_EDGES[i], "to": LEN_EDGES[i + 1], "games": g, "win": round(100 * w / g, 1) if g else None,
                      "here": LEN_EDGES[i] * 60 <= dur < LEN_EDGES[i + 1] * 60} for i, (g, w) in enumerate(lola["len"])][1:]
    my_team = next(t for t in info["teams"] if t["teamId"] == ME["teamId"])
    out["objectives"] = [{"name": ko, "mine": bool(my_team["objectives"].get(key, {}).get("first")),
                          "secure": lola["obj"][en][0], "winWith": lola["obj"][en][1], "winWithout": lola["obj"][en][3]}
                         for en, ko, key in OBJ if en in lola["obj"]]
    return out
