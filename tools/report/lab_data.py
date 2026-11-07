"""실험 페이지(lab) 데이터. 리포트에 넣어 볼 항목을 먼저 여기서 계산해요.

report_data.py의 build()가 불러서 리포트 데이터 JSON의 "lab" 칸에 넣어요.
기존 리포트 화면은 이 칸을 읽지 않아요. 항목을 정식 리포트로 옮기면 여기서 빼요.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "scripts"))
import benchmarks as B  # noqa: E402

POS_ORDER = ["TOP", "JUNGLE", "MIDDLE", "BOTTOM", "UTILITY"]
POS_KO = {"TOP": "탑", "JUNGLE": "정글", "MIDDLE": "미드", "BOTTOM": "원딜", "UTILITY": "서폿"}

# 플레이 스타일 그래프의 축과 축을 만드는 지표. 축 값은 지표 백분위의 평균이에요.
RADAR = [
    ("성장", ["cs15", "gold15", "xp15"]),
    ("라인전", ["goldDiff15", "csDiff15", "xpDiff15"]),
    ("전투", ["dpm", "kp", "dmg15"]),
    ("생존", ["deaths", "d14"]),
    ("시야", ["vspm", "wardsPm", "ctrl"]),
]


def _label(k):
    return next((lb for kk, lb, _, _ in B.METRICS if kk == k), k)


def build_lab(raw, A, ME, OPP, item_fn, champ_fn):
    info = raw["match"]["info"]
    frames = raw["timeline"]["info"]["frames"]
    events = [e for f in frames for e in f["events"]]
    P = info["participants"]
    dur = info["gameDuration"]
    my_team = ME["teamId"]
    me, opp = ME["participantId"], OPP["participantId"]
    last = len(frames) - 1

    def pf(m, pid):
        return frames[min(m, last)]["participantFrames"][str(pid)]

    def cs(m, pid):
        x = pf(m, pid)
        return x["minionsKilled"] + x["jungleMinionsKilled"]

    def team_sum(m, team, k):
        return sum(pf(m, p["participantId"])[k] for p in P if p["teamId"] == team)

    # ---------------- 분 단위 맞라인 비교 (끝까지)
    minute = []
    for m in range(0, last + 1):
        a, b = pf(m, me), pf(m, opp)
        minute.append({"m": m, "cs": [cs(m, me), cs(m, opp)], "gold": [a["totalGold"], b["totalGold"]],
                       "xp": [a["xp"], b["xp"]], "lv": [a["level"], b["level"]],
                       "teamXp": team_sum(m, my_team, "xp") - team_sum(m, 300 - my_team, "xp")})

    # ---------------- 구간별 성적 (라인전 / 중반 / 후반)
    kills = [e for e in events if e["type"] == "CHAMPION_KILL"]
    phases = []
    for name, lo, hi in (("라인전", 0, 14), ("중반", 14, 25), ("후반", 25, 999)):
        if lo * 60 >= dur:
            break
        hi_m = min(hi, last)
        t0, t1 = lo * 60000, min(hi * 60000, dur * 1000 + 1)
        ks = [e for e in kills if t0 <= e["timestamp"] < t1]
        gd = lambda m: pf(m, me)["totalGold"] - pf(m, opp)["totalGold"]  # noqa: E731
        tg = lambda m: team_sum(m, my_team, "totalGold") - team_sum(m, 300 - my_team, "totalGold")  # noqa: E731
        phases.append({
            "name": name, "from": lo, "to": hi_m if hi < 999 else None,
            "laneGold": gd(hi_m) - gd(lo), "teamGold": tg(hi_m) - tg(lo),
            "cs": [cs(hi_m, me) - cs(lo, me), cs(hi_m, opp) - cs(lo, opp)],
            "k": sum(e.get("killerId") == me for e in ks), "d": sum(e.get("victimId") == me for e in ks),
            "a": sum(me in e.get("assistingParticipantIds", []) for e in ks),
            "teamK": sum(1 for e in ks if any(p["participantId"] == e.get("killerId") and p["teamId"] == my_team for p in P)),
            "teamD": sum(1 for e in ks if any(p["participantId"] == e.get("victimId") and p["teamId"] == my_team for p in P)),
        })

    # ---------------- v2 숫자 (귀환, 방패, 와드) — 기준 데이터와 같은 함수로 계산
    x = {p["participantId"]: B.extra_stats(raw["match"], raw["timeline"], p["participantId"]) for p in P}
    my_sup = next((p for p in P if p["teamId"] == my_team and p["teamPosition"] == "UTILITY"), None)
    opp_sup = next((p for p in P if p["teamId"] != my_team and p["teamPosition"] == "UTILITY"), None)

    def back(pid):
        s = x[pid]
        if s.get("back1") is None:
            return None
        t = s["back1"] * 1000
        bought, undo = [], []
        for e in events:  # 첫 구매부터 45초 안에 산 것을 한 번의 귀환으로 봐요
            if e.get("participantId") != pid or not (t <= e["timestamp"] < t + 45000):
                continue
            if e["type"] == "ITEM_PURCHASED":
                bought.append(e["itemId"])
            elif e["type"] == "ITEM_UNDO" and e.get("beforeId") in bought:
                bought.remove(e["beforeId"])
        return {"t": s["back1"], "gold": s["back1Gold"], "death": s["back1Death"],
                "items": [item_fn(i) for i in bought if i not in (3340, 3363, 3364)]}

    def wardrow(p, who):
        s = x[p["participantId"]]
        return {"who": who, "c": champ_fn(p["championName"]), "ours": p["teamId"] == my_team,
                "ward1": s["ward1"], "wards14": s["wards14"], "wards": s["wards"],
                "wardsKilled": s["wardsKilled"], "ctrl": s["ctrl"]}

    wards = [wardrow(ME, "나"), wardrow(OPP, "상대 원딜")]
    if my_sup:
        wards.insert(1, wardrow(my_sup, "우리 서폿"))
    if opp_sup:
        wards.append(wardrow(opp_sup, "상대 서폿"))

    # ---------------- 팀 상세 지표, 피해 구성
    def prow(p):
        s = x[p["participantId"]]
        return {"c": champ_fn(p["championName"]), "pos": POS_KO.get(p["teamPosition"], ""),
                "me": p["participantId"] == me, "taken": p["totalDamageTaken"], "mitig": p["damageSelfMitigated"],
                "heal": p["totalHeal"], "shield": p.get("totalDamageShieldedOnTeammates", 0),
                "cc": p.get("timeCCingOthers", 0), "wards": p["wardsPlaced"], "wardsKilled": p["wardsKilled"],
                "ctrl": p.get("visionWardsBoughtInGame", 0), "plates": s["plates"]}

    def side(team):
        ps = sorted([p for p in P if p["teamId"] == team], key=lambda p: POS_ORDER.index(p["teamPosition"])
                    if p["teamPosition"] in POS_ORDER else 9)
        return [prow(p) for p in ps]

    def mix(team):
        ps = [p for p in P if p["teamId"] == team]
        ph = sum(p["physicalDamageDealtToChampions"] for p in ps)
        mg = sum(p["magicDamageDealtToChampions"] for p in ps)
        tr = sum(p["trueDamageDealtToChampions"] for p in ps)
        return {"phys": ph, "magic": mg, "true": tr}

    # ---------------- 기준 대비 (analyze.py가 계산해 둔 값)
    bm = A.get("benchmark") or {"available": False}
    radar = None
    if bm.get("available"):
        by = {m["key"]: m for m in bm["metrics"]}
        radar = []
        for axis, keys in RADAR:
            parts = [{"key": k, "label": _label(k), "pct": by[k]["pct"] if k in by else None} for k in keys]
            have = [p["pct"] for p in parts if p["pct"] is not None]
            radar.append({"axis": axis, "value": round(sum(have) / len(have)) if have else None, "parts": parts})
        bm = dict(bm, missing=[_label(k) for k in bm.get("missing", [])])
        for sl in bm.get("slots", []):  # 아이콘 주소를 넣어 둬요(artifact 한 파일에 그림을 넣으려고)
            for b in ([sl["mine"]] if sl.get("mine") else []) + sl["top"]:
                b["img"] = item_fn(b["id"])["img"]

    return {
        "minute": minute, "phases": phases,
        "back": {"me": back(me), "opp": back(opp)},
        "plates": {"me": x[me]["plates"], "opp": x[opp]["plates"],
                   "botTaken": x[me]["botPlates"], "botLost": x[me]["botPlatesLost"]},
        "wards": wards,
        "teamDetail": {"ours": side(my_team), "theirs": side(300 - my_team)},
        "dmgMix": {"ours": mix(my_team), "theirs": mix(300 - my_team)},
        "bench": bm, "radar": radar,
    }
