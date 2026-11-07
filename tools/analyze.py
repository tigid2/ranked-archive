# -*- coding: utf-8 -*-
"""
한 판의 라이엇 원본 데이터(경기 상세 + 타임라인)와 게임 중 기록을 분석해서
피드백에 쓸 사실들을 JSON으로 정리해요. (Claude가 피드백 쓸 때 쓰는 도구)

사용: python3 tools/analyze.py raw/<경기>.json.gz <내 챔피언 영문 ID> [raw/<경기>.live.json|-] [data] [analysis]
 - 마지막 칸은 결과를 저장할 폴더예요. 없으면 경기 파일 옆에 저장해요.
"""
import gzip
import json
import math
import os
import sys

DD = {}


def load_dd(folder):
    def j(n):
        p = os.path.join(folder, f"dd_{n}.json")
        return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else None
    it, ch, sm, rn = j("item"), j("champion"), j("summoner"), j("runesReforged")
    DD["item"] = {int(k): v for k, v in (it or {}).get("data", {}).items()}
    DD["champ"] = {k.lower(): v["name"] for k, v in (ch or {}).get("data", {}).items()}
    DD["spell"] = {int(v["key"]): v["name"] for v in (sm or {}).get("data", {}).values()}
    DD["rune"], DD["style"] = {}, {}
    for st in rn or []:
        DD["style"][st["id"]] = st["name"]
        for slot in st["slots"]:
            for r in slot["runes"]:
                DD["rune"][r["id"]] = r["name"]
    DD["shard"] = {5008: "적응형 능력치", 5005: "공격 속도", 5007: "스킬 가속", 5002: "방어력", 5003: "마법 저항력",
                   5001: "체력 증가(성장)", 5011: "체력", 5010: "이동 속도", 5013: "강인함·둔화 저항"}


def cname(c):
    return DD.get("champ", {}).get(str(c).lower(), c)


def iname(i):
    return DD.get("item", {}).get(i, {}).get("name", f"아이템#{i}")


POS_KO = {"TOP": "탑", "JUNGLE": "정글", "MIDDLE": "미드", "BOTTOM": "원딜", "UTILITY": "서폿"}
DRAGON = (9866, 4414)
BARON = (5007, 10471)


def dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def zone(x, y, my_team):
    """맵 좌표를 사람이 읽을 수 있는 구역으로 바꿔요. (대략적인 구역)"""
    if x < 4600 and y < 4600 and x + y < 7000:
        return "블루팀 본진" if my_team != 100 else "우리 본진"
    if x > 10200 and y > 10200 and x + y > 22600:
        return "레드팀 본진" if my_team != 200 else "우리 본진"
    if y < 2300 or x > 12500:
        lane = "바텀 라인"
    elif x < 2300 or y > 12500:
        lane = "탑 라인"
    elif abs(x - y) < 1400:
        lane = "미드 라인"
    else:
        lane = None
    if lane:
        return lane
    if abs(x + y - 14800) < 1500:
        return "아래쪽 강가(드래곤 쪽)" if x > y else "위쪽 강가(바론 쪽)"
    blue_side = x + y < 14800
    ours = (blue_side and my_team == 100) or (not blue_side and my_team == 200)
    half = "아래쪽" if x > y else "위쪽"
    return f"{'우리' if ours else '상대'} {half} 정글"


def unit_name(raw):
    """라이엇 내부 이름(미니언, 포탑, 몬스터)을 한글로 바꿔요."""
    r = str(raw or "")
    if "Minion" in r:
        return "미니언"
    if "Turret" in r or "turret" in r:
        return "포탑"
    for k, v in (("Baron", "바론"), ("Dragon", "드래곤"), ("Herald", "전령"), ("Horde", "공허 유충"), ("Atakhan", "아타칸")):
        if k in r:
            return v
    return r or "기타"


def mmss(ms):
    s = int(ms // 1000)
    return f"{s // 60}:{s % 60:02d}"


def analyze(raw, champ_id, live=None):
    m, tl = raw["match"]["info"], raw["timeline"]["info"]
    parts = m["participants"]
    by = {p["participantId"]: p for p in parts}
    me = next(p for p in parts if p["championName"].lower() == champ_id.lower())
    my, team = me["participantId"], me["teamId"]
    enemy = 300 - team
    pos = me.get("teamPosition") or me.get("individualPosition")
    opp = next((p for p in parts if p["teamId"] == enemy and p.get("teamPosition") == pos), None)
    duo = next((p for p in parts if p["teamId"] == team and p.get("teamPosition") == ("UTILITY" if pos == "BOTTOM" else "BOTTOM")), None)
    eduo = next((p for p in parts if p["teamId"] == enemy and p.get("teamPosition") == ("UTILITY" if pos == "BOTTOM" else "BOTTOM")), None)
    frames = tl["frames"]
    events = [e for f in frames for e in f["events"]]
    dur = m["gameDuration"]
    mins = dur / 60

    def nm(pid):
        if pid in by:
            p = by[pid]
            side = "나" if pid == my else ("아군" if p["teamId"] == team else "적")
            return f"{cname(p['championName'])}({side})"
        return "미니언·포탑"

    def pf(minute, pid):
        if 0 <= minute < len(frames):
            return frames[minute]["participantFrames"].get(str(pid))
        return None

    def ppos(t_ms, pid):
        """t 시점에 가장 가까운 1분 기록의 위치 (1분 단위라 대략적)"""
        k = min(range(len(frames)), key=lambda i: abs(frames[i]["timestamp"] - t_ms))
        f = pf(k, pid)
        return (f["position"]["x"], f["position"]["y"]) if f else None, frames[k]["timestamp"]

    def cs(f):
        return f["minionsKilled"] + f["jungleMinionsKilled"]

    out = {"matchId": raw["match"]["metadata"]["matchId"], "version": m["gameVersion"], "durationSec": dur,
           "win": me["win"], "champion": cname(me["championName"]), "position": POS_KO.get(pos, pos),
           "opponent": cname(opp["championName"]) if opp else None,
           "duo": cname(duo["championName"]) if duo else None, "enemyDuo": cname(eduo["championName"]) if eduo else None}

    # 기본 기록
    tk = sum(p["kills"] for p in parts if p["teamId"] == team) or 1
    tdmg = sum(p["totalDamageDealtToChampions"] for p in parts if p["teamId"] == team) or 1
    ch = me.get("challenges", {})
    out["basic"] = {
        "kda": [me["kills"], me["deaths"], me["assists"]], "cs": me["totalMinionsKilled"] + me["neutralMinionsKilled"],
        "csPerMin": round((me["totalMinionsKilled"] + me["neutralMinionsKilled"]) / mins, 1),
        "gold": me["goldEarned"], "goldPerMin": round(me["goldEarned"] / mins),
        "damage": me["totalDamageDealtToChampions"], "damageShare": round(me["totalDamageDealtToChampions"] / tdmg * 100),
        "damageTaken": me["totalDamageTaken"], "killParticipation": round((me["kills"] + me["assists"]) / tk * 100),
        "vision": me["visionScore"], "wardsPlaced": me["wardsPlaced"], "wardsKilled": me["wardsKilled"],
        "controlWards": me.get("visionWardsBoughtInGame", 0), "turretDamage": me.get("damageDealtToTurrets", 0),
        "cs10": ch.get("laneMinionsFirst10Minutes"), "soloKills": ch.get("soloKills"),
        "skillshotsHit": ch.get("skillshotsHit"), "skillshotsDodged": ch.get("skillshotsDodged"),
        "maxCsAdvantage": ch.get("maxCsAdvantageOnLaneOpponent"), "teamDamagePct": ch.get("teamDamagePercentage"),
    }
    out["teams"] = [{"team": "우리" if p["teamId"] == team else "상대", "pos": POS_KO.get(p.get("teamPosition"), ""),
                     "champ": cname(p["championName"]), "me": p["participantId"] == my,
                     "kda": [p["kills"], p["deaths"], p["assists"]], "cs": p["totalMinionsKilled"] + p["neutralMinionsKilled"],
                     "gold": p["goldEarned"], "damage": p["totalDamageDealtToChampions"], "vision": p["visionScore"]}
                    for p in sorted(parts, key=lambda p: (p["teamId"] != team, ["TOP", "JUNGLE", "MIDDLE", "BOTTOM", "UTILITY"].index(p.get("teamPosition") or "UTILITY")))]

    # 분 단위 흐름
    flow = []
    for k in range(len(frames)):
        a = pf(k, my)
        b = pf(k, opp["participantId"]) if opp else None
        tg = sum(pf(k, p["participantId"])["totalGold"] for p in parts if p["teamId"] == team)
        eg = sum(pf(k, p["participantId"])["totalGold"] for p in parts if p["teamId"] == enemy)
        row = {"min": k, "teamGoldDiff": tg - eg, "gold": a["totalGold"], "cs": cs(a), "level": a["level"],
               "currentGold": a.get("currentGold")}
        if b:
            row.update(laneGoldDiff=a["totalGold"] - b["totalGold"], laneCsDiff=cs(a) - cs(b), laneXpDiff=a["xp"] - b["xp"])
        if duo and eduo:
            row["botGoldDiff"] = (a["totalGold"] + pf(k, duo["participantId"])["totalGold"]) - \
                ((b["totalGold"] if b else 0) + pf(k, eduo["participantId"])["totalGold"])
        flow.append(row)
    out["flow"] = flow

    def level_at(pid, lv):
        for e in events:
            if e["type"] == "LEVEL_UP" and e.get("participantId") == pid and e.get("level") == lv:
                return mmss(e["timestamp"])
        return None
    out["levels"] = {lv: {"me": level_at(my, lv), "opp": level_at(opp["participantId"], lv) if opp else None} for lv in (2, 3, 6, 11)}

    # 킬 이벤트 정리
    kills = []
    for e in events:
        if e["type"] != "CHAMPION_KILL":
            continue
        kills.append({"t": e["timestamp"], "killer": e.get("killerId", 0), "victim": e["victimId"],
                      "assists": e.get("assistingParticipantIds", []) or [], "pos": (e["position"]["x"], e["position"]["y"]),
                      "bounty": e.get("bounty", 0), "shutdown": e.get("shutdownBounty", 0), "dmg": e.get("victimDamageReceived", []) or []})

    # 교전 묶기: 20초 안에 이어진 킬은 같은 싸움으로 봐요
    fights, cur = [], []
    for k in kills:
        if cur and k["t"] - cur[-1]["t"] > 20000:
            fights.append(cur)
            cur = []
        cur.append(k)
    if cur:
        fights.append(cur)

    def fight_of(kill):
        for f in fights:
            if kill in f:
                ours = sum(1 for k in f if by.get(k["victim"], {}).get("teamId") == enemy)
                theirs = sum(1 for k in f if by.get(k["victim"], {}).get("teamId") == team)
                return {"start": mmss(f[0]["t"]), "end": mmss(f[-1]["t"]), "weKilled": ours, "weLost": theirs, "size": len(f)}
        return None

    objectives = []
    for e in events:
        if e["type"] == "ELITE_MONSTER_KILL":
            killer_team = e.get("killerTeamId") or by.get(e.get("killerId"), {}).get("teamId")
            name = {"DRAGON": "드래곤", "BARON_NASHOR": "바론", "RIFTHERALD": "전령", "HORDE": "공허 유충", "ATAKHAN": "아타칸"}.get(e["monsterType"], e["monsterType"])
            sub = {"FIRE_DRAGON": "화염", "WATER_DRAGON": "바다", "EARTH_DRAGON": "대지", "AIR_DRAGON": "바람", "HEXTECH_DRAGON": "마법공학",
                   "CHEMTECH_DRAGON": "화학공학", "ELDER_DRAGON": "장로"}.get(e.get("monsterSubType"), "")
            objectives.append({"t": e["timestamp"], "name": f"{sub} {name}".strip(), "ours": killer_team == team, "type": "monster"})
        elif e["type"] == "BUILDING_KILL":
            lane = {"TOP_LANE": "탑", "MID_LANE": "미드", "BOT_LANE": "바텀"}.get(e.get("laneType"), "")
            tier = {"OUTER_TURRET": "1차", "INNER_TURRET": "2차", "BASE_TURRET": "3차", "NEXUS_TURRET": "쌍둥이"}.get(e.get("towerType"), "")
            kind = "억제기" if e.get("buildingType") == "INHIBITOR_BUILDING" else "포탑"
            objectives.append({"t": e["timestamp"], "name": f"{lane} {tier} {kind}".replace("  ", " ").strip(),
                               "ours": e.get("teamId") == enemy, "type": "building"})

    # 내 데스 분석
    deaths = []
    for k in kills:
        if k["victim"] != my:
            continue
        t = k["t"]
        dpos = k["pos"]
        involved = [k["killer"]] + k["assists"]
        roams = []
        for pid in involved:
            if pid not in by or pid in ((opp or {}).get("participantId"), (eduo or {}).get("participantId")):
                continue
            # 1분 전 위치
            prev_k = max(0, int(t // 60000) - 0)
            f = pf(prev_k, pid)
            if f:
                p0 = (f["position"]["x"], f["position"]["y"])
                d = dist(p0, dpos)
                roams.append({"who": nm(pid), "role": POS_KO.get(by[pid].get("teamPosition"), ""),
                              "minuteMark": f"{prev_k}:00", "wasAt": zone(*p0, team), "distance": round(d)})
        allies_near, enemies_near = [], []
        near_k = round(t / 60000)
        for p in parts:
            if p["participantId"] == my:
                continue
            f = pf(min(near_k, len(frames) - 1), p["participantId"])
            if not f:
                continue
            d = dist((f["position"]["x"], f["position"]["y"]), dpos)
            if d < 2500:
                (allies_near if p["teamId"] == team else enemies_near).append(nm(p["participantId"]))
        dmg = {}
        for d in k["dmg"]:
            pid = d.get("participantId")
            if pid in by and by[pid]["teamId"] == team:
                continue  # 아군이 준 피해(일부 스킬 효과)는 빼요
            total = d.get("physicalDamage", 0) + d.get("magicDamage", 0) + d.get("trueDamage", 0)
            key = nm(pid) if pid in by else unit_name(d.get("name"))
            dmg[key] = dmg.get(key, 0) + total
        spells = {}
        for d in k["dmg"]:
            if d.get("participantId") in by and by[d["participantId"]]["teamId"] == enemy:
                total = d.get("physicalDamage", 0) + d.get("magicDamage", 0) + d.get("trueDamage", 0)
                sn = d.get("spellName") or "기본 공격"
                spells[sn] = spells.get(sn, 0) + total
        lost = [o for o in objectives if not o["ours"] and 0 < o["t"] - t <= 90000]
        # 들고 있던 골드: 1분 기록 사이에 번 골드를 비율로 더해서 추정해요.
        # 그 사이에 아이템을 샀으면 계산이 틀어지니까 '계산 불가'로 둬요.
        k0 = int(t // 60000)
        f0, f1 = pf(k0, my), pf(k0 + 1, my)
        bought = any(e["type"] == "ITEM_PURCHASED" and e.get("participantId") == my and frames[k0]["timestamp"] < e["timestamp"] <= t
                     for e in events)
        if f0 and not bought:
            earned = ((f1["totalGold"] - f0["totalGold"]) if f1 else 0) * (t - frames[k0]["timestamp"]) / 60000
            approx_gold = int(round((f0["currentGold"] + earned) / 10) * 10)
        else:
            approx_gold = None
        deaths.append({
            "t": mmss(t), "tMs": t, "zone": zone(*dpos, team), "killer": nm(k["killer"]),
            "assists": [nm(a) for a in k["assists"]], "alliesNear": allies_near, "enemiesNear": enemies_near,
            "roams": roams, "damage": sorted(dmg.items(), key=lambda kv: -kv[1])[:4],
            "topSpells": sorted(spells.items(), key=lambda kv: -kv[1])[:3],
            "approxGold": approx_gold, "shutdownGiven": k["shutdown"],
            "fight": fight_of(k), "lostAfter": [f"{mmss(o['t'])} {o['name']}" for o in lost],
            "teamGoldDiff": flow[min(int(t // 60000), len(flow) - 1)]["teamGoldDiff"],
        })
    if live:
        for d in deaths:
            ld = min(live.get("deaths", []), key=lambda x: abs(x["t"] * 1000 - d["tMs"]), default=None)
            if ld and abs(ld["t"] * 1000 - d["tMs"]) <= 6000:
                d["live"] = {"gold": ld.get("gold"), "hpFlow": ld.get("hpFlow"), "spells": ld.get("spells")}
    out["deaths"] = deaths
    # 미니맵 기록이 있으면 죽음마다 "죽인 적이 보였는지, 적 정글 마지막 위치, 주변 안개"를 붙여요
    if live and live.get("minimap"):
        out["minimap"] = minimap_view(live["minimap"], live.get("deaths", []), parts, frames, events, my, team, by,
                                      deaths, nm)

    # 내 킬·어시
    out["myKills"] = [{"t": mmss(k["t"]), "victim": nm(k["victim"]), "zone": zone(*k["pos"], team),
                       "withAllies": [nm(a) for a in k["assists"]], "solo": not k["assists"]} for k in kills if k["killer"] == my]

    # 오브젝트와 내 상태
    dead_windows = []
    for k in kills:
        if k["victim"] == my:
            lv = me["champLevel"]
            dead_windows.append((k["t"], k["t"] + 10000 + 2500 * min(18, max(1, flow[min(int(k['t'] // 60000), len(flow) - 1)]["level"]))))
    objs = []
    for o in objectives:
        if o["type"] != "monster":
            continue
        dead = any(a <= o["t"] <= b for a, b in dead_windows)
        p, _ = ppos(o["t"] - 30000, my)
        pit = DRAGON if "드래곤" in o["name"] else BARON if o["name"] in ("바론",) else None
        near = round(dist(p, pit)) if (p and pit) else None
        objs.append({"t": mmss(o["t"]), "name": o["name"], "ours": o["ours"], "iWasDead": dead, "myDistance30sBefore": near})
    out["objectives"] = objs
    out["buildings"] = [{"t": mmss(o["t"]), "name": o["name"], "ours": o["ours"]} for o in objectives if o["type"] == "building"]

    # 교전 요약
    out["fights"] = []
    for f in fights:
        if len(f) < 2:
            continue
        ours = sum(1 for k in f if by.get(k["victim"], {}).get("teamId") == enemy)
        theirs = sum(1 for k in f if by.get(k["victim"], {}).get("teamId") == team)
        mine = any(my in ([k["killer"]] + k["assists"]) or k["victim"] == my for k in f)
        out["fights"].append({"start": mmss(f[0]["t"]), "kills": f"{ours}:{theirs}", "iWasIn": mine,
                              "iDied": any(k["victim"] == my for k in f), "zone": zone(*f[0]["pos"], team),
                              "teamGoldDiffBefore": flow[min(int(f[0]['t'] // 60000), len(flow) - 1)]["teamGoldDiff"]})

    # 아이템 완성
    def completions(pid):
        res = []
        for e in events:
            if e["type"] == "ITEM_PURCHASED" and e.get("participantId") == pid:
                it = DD.get("item", {}).get(e["itemId"], {})
                tot = it.get("gold", {}).get("total", 0)
                if (not it.get("into") and tot >= 2200) or ("Boots" in it.get("tags", []) and tot >= 900):
                    res.append({"t": mmss(e["timestamp"]), "item": it.get("name", e["itemId"]), "gold": tot})
        return res
    out["items"] = {"me": completions(my), "opp": completions(opp["participantId"]) if opp else [],
                    "final": [iname(me.get(f"item{i}")) for i in range(7) if me.get(f"item{i}")]}
    # 돈을 많이 들고 있던 순간 (1분 기록 기준)
    out["bankedGold"] = [{"min": r["min"], "currentGold": r["currentGold"]} for r in flow if (r.get("currentGold") or 0) >= 1500]

    # 룬·스펠
    perks = me["perks"]
    out["runes"] = {"primary": DD.get("style", {}).get(perks["styles"][0]["style"]),
                    "secondary": DD.get("style", {}).get(perks["styles"][1]["style"]),
                    "picks": [{"rune": DD.get("rune", {}).get(s["perk"], s["perk"]), "vars": [s["var1"], s["var2"], s["var3"]]}
                              for st in perks["styles"] for s in st["selections"]],
                    "shards": [DD["shard"].get(perks["statPerks"][k], perks["statPerks"][k]) for k in ("offense", "flex", "defense")]}
    out["spells"] = [{"name": DD.get("spell", {}).get(me[f"summoner{i}Id"], me[f"summoner{i}Id"]), "casts": me.get(f"summoner{i}Casts")} for i in (1, 2)]
    out["skills"] = {"casts": [me.get(f"spell{i}Casts") for i in (1, 2, 3, 4)],
                     "immobilizations": ch.get("enemyChampionImmobilizations"),
                     "skillshotsHit": ch.get("skillshotsHit"), "skillshotsDodged": ch.get("skillshotsDodged")}
    pings = {k: me.get(k, 0) for k in ("onMyWayPings", "enemyMissingPings", "getBackPings", "assistMePings", "allInPings",
                                       "pushPings", "needVisionPings", "enemyVisionPings", "holdPings", "dangerPings",
                                       "retreatPings", "visionClearedPings", "basicPings", "commandPings")}
    out["pings"] = pings
    out["wardTimeline"] = {}
    for e in events:
        if e["type"] == "WARD_PLACED" and e.get("creatorId") == my and e.get("wardType") != "UNDEFINED":
            b = int(e["timestamp"] // 300000) * 5
            out["wardTimeline"][b] = out["wardTimeline"].get(b, 0) + 1
    # 라인전 서폿 위치와 바텀 원딜 킬 (원딜일 때만)
    if pos == "BOTTOM" and duo and opp:
        out["lane"] = lane_support(frames, events, my, opp["participantId"], duo["participantId"], team, by, nm)
    # 기준 데이터(에메랄드~다이아 같은 챔피언) 대비 (계획 3단계)
    if pos == "BOTTOM":
        out["benchmark"] = vs_benchmark(raw, my, me["championName"], m["gameVersion"])
    return out


# ---------------------------------------------------------------- 미니맵 (게임 중 기록)

MM_FIT_SCORE = 80   # 좌표를 맞출 때 쓰는 확실한 아이콘 점수(0~100)
MM_SEEN_SCORE = 60  # 이 점수 이상이고 자리도 그럴듯하면 "미니맵에 보였다"고 봐요
MM_FOG = 0.7        # 그 자리가 가장 밝았을 때보다 이 비율 아래로 어두우면 안개(시야 없음)로 봐요
MM_RING = (1300, 2600)  # 안개를 보는 범위: 내 주변 이 거리(맵 단위) 사이. 내 시야(약 1200) 바로 바깥이에요
MAP_MAX = 14870


def _norm(s):
    return "".join(ch for ch in (s or "").lower() if ch.isalnum())


def _fit1(pairs):
    """한 축의 직선 맞추기: 맵 좌표 = a × 화면 위치 + b"""
    n = len(pairs)
    sx = sum(p for p, _ in pairs)
    sy = sum(g for _, g in pairs)
    sxx = sum(p * p for p, _ in pairs)
    sxy = sum(p * g for p, g in pairs)
    den = n * sxx - sx * sx
    if not den:
        return None
    a = (n * sxy - sx * sy) / den
    return a, (sy - a * sx) / n


def _unpack(s, size):
    import base64
    import zlib
    b = zlib.decompress(base64.b64decode(s))
    return b if len(b) == size * size else None


def minimap_view(mm, live_deaths, parts, frames, events, my, team, by, deaths, nm):
    """기록 프로그램이 남긴 미니맵 기록으로 죽음마다 이런 걸 알아내요.
    ① 나를 죽인 적이 죽기 몇 초 전부터 미니맵에 보였는지 ② 적 정글이 마지막으로 보인 때와 자리
    ③ 죽을 때 내 주변(내 시야 바로 바깥)이 얼마나 안개였는지.
    미니맵의 화면 위치는 기록하지 않았으니, Riot 1분 위치 기록과 맞춰서 맵 좌표로 바꿔요."""
    import bisect
    res = {"available": False}
    players = mm.get("players") or []
    fr = mm.get("frames") or []
    if not players or len(fr) < 60:
        res["reason"] = "미니맵 기록이 거의 없음"
        return res
    by_name = {}
    for p in parts:
        by_name.setdefault(_norm(p["championName"]), []).append(p)
    pid_of = {}
    for i, pl in enumerate(players):
        c = by_name.get(_norm(pl["key"]))
        if c and len(c) == 1 and (c[0]["teamId"] == team) == bool(pl["ally"]):
            pid_of[i] = c[0]["participantId"]
    if len(pid_of) < 6:
        res["reason"] = "챔피언 이름을 맞추지 못함"
        return res
    idx_of = {v: k for k, v in pid_of.items()}
    times = [f[0] for f in fr]

    def near(t, tol):
        k = bisect.bisect_left(times, t)
        best = None
        for j in (k - 1, k):
            if 0 <= j < len(times) and abs(times[j] - t) <= tol and (best is None or abs(times[j] - t) < abs(times[best] - t)):
                best = j
        return best

    # 1) 좌표 맞추기: 1분마다 Riot이 준 위치와, 그 순간 미니맵에서 찾은 아이콘 위치
    pts = []
    for f in frames[1:]:
        j = near(f["timestamp"] / 1000, 1.0)
        if j is None:
            continue
        for i, x, y, s in fr[j][1]:
            pf = f["participantFrames"].get(str(pid_of.get(i)))
            if s >= MM_FIT_SCORE and pf:
                pts.append((x, y, pf["position"]["x"], pf["position"]["y"]))

    def errs(fx, fy, ps):
        return [math.hypot(fx[0] * p[0] + fx[1] - p[2], fy[0] * p[1] + fy[1] - p[3]) for p in ps]

    fx = fy = None
    for _ in range(4):
        if len(pts) < 8:
            break
        fx, fy = _fit1([(p[0], p[2]) for p in pts]), _fit1([(p[1], p[3]) for p in pts])
        if not fx or not fy:
            break
        e = errs(fx, fy, pts)
        med = sorted(e)[len(e) // 2]
        keep = [p for p, v in zip(pts, e) if v <= max(900, 2.5 * med)]
        if len(keep) == len(pts):
            break
        pts = keep
    if not fx or not fy or len(pts) < 8:
        res["reason"] = f"좌표를 맞출 점이 부족함({len(pts)}개)"
        return res
    e = sorted(errs(fx, fy, pts))
    med = e[len(e) // 2]
    ratio = abs(fx[0] / fy[0]) if fy[0] else 0
    if not (fx[0] > 0 and fy[0] < 0 and 0.8 <= ratio <= 1.25 and med <= 1200):
        res["reason"] = f"좌표가 맞지 않음(오차 중앙값 {round(med)}, 축 비율 {ratio:.2f})"
        return res
    res.update(available=True, fitPoints=len(pts), fitErrMedian=round(med), unitsPerPx=round(fx[0], 1),
               iconSize=mm.get("size"), msAvg=mm.get("msAvg"))

    def to_map(x, y):
        return fx[0] * x + fx[1], fy[0] * y + fy[1]

    # 2) 미니맵에 보인 기록. 잘못 찾은 아이콘을 두 가지로 걸러요.
    #   - 1분 기록 바로 근처(15초 안)인데 Riot 위치와 너무 멀면 빼요.
    #   - 2.5초 안에 가까운 자리에서 다시 찾히지 않으면 빼요. 진짜 아이콘은 이어서 보이고, 잘못 찾은 건 여기저기 튀어요.
    cand = {i: [] for i in pid_of}
    dropped = 0
    for t, dets in fr:
        for i, x, y, s in dets:
            if s < MM_SEEN_SCORE or i not in pid_of:
                continue
            gx, gy = to_map(x, y)
            if not (-600 <= gx <= MAP_MAX + 600 and -600 <= gy <= MAP_MAX + 600):
                dropped += 1
                continue
            ok = True
            for kk in (int(t // 60), int(t // 60) + 1):
                if 0 <= kk < len(frames):
                    pf = frames[kk]["participantFrames"].get(str(pid_of[i]))
                    dt = abs(frames[kk]["timestamp"] / 1000 - t)
                    if pf and dt <= 15 and math.hypot(gx - pf["position"]["x"], gy - pf["position"]["y"]) > 550 * dt + 1500:
                        ok = False
            if ok:
                cand[i].append((t, gx, gy))
            else:
                dropped += 1
    seen = {}
    for i, lst in cand.items():
        keep = []
        for k, (t, gx, gy) in enumerate(lst):
            nb = [lst[j] for j in (k - 1, k + 1) if 0 <= j < len(lst) and 0 < abs(lst[j][0] - t) <= 2.5]
            if any(math.hypot(gx - q[1], gy - q[2]) <= 800 * abs(q[0] - t) + 400 for q in nb):
                keep.append((t, gx, gy))
            else:
                dropped += 1
        seen[i] = keep
    res["droppedDetections"] = dropped

    def seen_info(pid, t):
        lst = seen.get(idx_of.get(pid))
        if lst is None:
            return {"seenFor": None, "lastSeenAgo": None}
        ts = [x[0] for x in lst]
        k = bisect.bisect_right(ts, t + 0.5) - 1
        if k < 0:
            return {"seenFor": 0, "lastSeenAgo": None}
        if t - ts[k] <= 2.0:
            j = k
            while j > 0 and ts[j] - ts[j - 1] <= 2.5 and t - ts[j - 1] <= 30:
                j -= 1
            return {"seenFor": round(t - ts[j], 1), "lastSeenAgo": 0}
        return {"seenFor": 0, "lastSeenAgo": round(t - ts[k], 1)}

    ej = next((p for p in parts if p["teamId"] != team and p.get("teamPosition") == "JUNGLE"), None)
    for d in deaths:
        t = d["tMs"] / 1000
        if near(t - 1.5, 2.0) is None:
            d["minimap"] = {"recorded": False}
            continue
        ev = next((x for x in events if x["type"] == "CHAMPION_KILL" and x.get("victimId") == my
                   and abs(x["timestamp"] - d["tMs"]) < 1500), None)
        ids = ([ev.get("killerId")] + (ev.get("assistingParticipantIds") or [])) if ev else []
        enemies = [x for x in ids if x in by and by[x]["teamId"] != team]
        info = {"recorded": True,
                "enemies": [{"name": nm(pid), "killer": pid == (ev or {}).get("killerId"), **seen_info(pid, t)}
                            for pid in enemies]}
        if ej and ej["participantId"] in idx_of:
            lst = [x for x in seen[idx_of[ej["participantId"]]] if x[0] <= t + 0.5]
            info["enemyJungle"] = {"name": nm(ej["participantId"]), "inKill": ej["participantId"] in enemies,
                                   "lastSeenAgo": max(0.0, round(t - lst[-1][0], 1)) if lst else None,
                                   "lastSeenZone": zone(lst[-1][1], lst[-1][2], team) if lst else None}
        # 3) 안개: 죽기 직전 밝기와 가장 밝았던 밝기를 비교해요. 내 자리는 Riot 킬 기록의 위치(정확한 값)를 써요
        ld = min(live_deaths, key=lambda x: abs(x["t"] * 1000 - d["tMs"]), default=None)
        snap = (ld or {}).get("minimap") if ld and abs(ld["t"] * 1000 - d["tMs"]) <= 6000 else None
        side = mm.get("regionSide")
        if snap and ev and side:
            info["fog"] = _fog(snap, ev["position"], fx, fy, side)
        d["minimap"] = info
    return res


def _fog(snap, pos, fx, fy, side):
    size = snap.get("size") or 96
    cur, ref = _unpack(snap["cur"], size), _unpack(snap["ref"], size)
    if not cur or not ref:
        return None
    k = size / side                       # 줄인 그림 1칸 = 영역 1/k px
    upx = abs(fx[0]) / k                  # 줄인 그림 1칸이 맵에서 몇 단위인지
    cx, cy = (pos["x"] - fx[1]) / fx[0] * k, (pos["y"] - fy[1]) / fy[0] * k
    r0, r1 = MM_RING[0] / upx, MM_RING[1] / upx
    ring = inner = ring_fog = inner_fog = 0
    for y in range(max(0, int(cy - r1) - 1), min(size, int(cy + r1) + 2)):
        for x in range(max(0, int(cx - r1) - 1), min(size, int(cx + r1) + 2)):
            r = math.hypot(x - cx, y - cy)
            if r > r1:
                continue
            gx, gy = fx[0] * x / k + fx[1], fy[0] * y / k + fy[1]
            if not (0 <= gx <= MAP_MAX and 0 <= gy <= MAP_MAX):
                continue
            rv = ref[y * size + x]
            if rv < 25:
                continue
            dark = cur[y * size + x] < MM_FOG * rv
            if r < r0 * 0.6:
                inner += 1
                inner_fog += dark
            elif r >= r0:
                ring += 1
                ring_fog += dark
    if ring < 5:
        return None
    # 내 바로 주변은 내 시야라 밝아야 해요. 여기가 어두우면 그림이나 좌표가 틀린 거라 믿지 않아요
    trusted = inner == 0 or inner_fog / inner <= 0.4
    return {"share": round(ring_fog / ring, 2), "trusted": trusted}


# ---------------------------------------------------------------- 기준 데이터 대비

BM_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "benchmarks")
def _band(v, st, direction):
    if v is None or not direction:
        return None
    lower_better = direction < 0
    good, bad = (v <= st["p25"], v >= st["p75"]) if lower_better else (v >= st["p75"], v <= st["p25"])
    return "상위 25%" if good else ("하위 25%" if bad else "중간 50%")


def _pct(v, vals, direction):
    """기준 판 중 이 판보다 못한 판의 비율(0~100). 같은 값은 반만 셉니다. 방향이 없으면 '작은 판 비율'."""
    vals = [x for x in vals if x is not None]
    if v is None or not vals:
        return None
    below = sum(x < v for x in vals) + 0.5 * sum(x == v for x in vals)
    p = 100 * below / len(vals)
    return round(100 - p if direction < 0 else p)


def vs_benchmark(raw, my, champ, version):
    """benchmarks/<챔피언>.json과 이 판 숫자를 비교해요. 판 수가 minN보다 적은 숫자는 넣지 않아요.
    이 판 숫자는 scripts/benchmarks.py의 extract_row로 똑같이 계산해요."""
    p = os.path.join(BM_DIR, f"{champ}.json")
    if not os.path.exists(p):
        return {"available": False, "reason": "이 챔피언의 기준 데이터가 아직 없어요."}
    bm = json.load(open(p, encoding="utf-8"))
    sys.path.insert(0, os.path.join(os.path.dirname(BM_DIR), "scripts"))
    import benchmarks as B  # noqa: E402
    B.DD["item"] = DD.get("item", {})
    row = B.extract_row(raw["match"], raw["timeline"], my)
    mine = B.metric_values(row)
    rows, _ = B.pick_rows(B.load_rows(champ))
    rvals = [B.metric_values(r) for r in rows]
    mn = bm["minN"]
    res = {"available": True, "games": bm["games"], "patches": bm["patches"], "tiers": bm["tiers"],
           "samePatch": ".".join(version.split(".")[:2]) in bm["patches"], "metrics": [], "missing": []}
    for k, label, direction, _ in B.METRICS:
        st = bm["metrics"].get(k, {})
        v = mine.get(k)
        if st.get("n", 0) < mn["stat"]:
            res["missing"].append(k)  # 기준 판 수가 모자라요(새로 늘린 숫자는 다시 모으기 전까지 여기)
            continue
        if v is None:
            continue
        res["metrics"].append({"key": k, "label": label, "mine": v, "median": st["median"], "p25": st["p25"],
                               "p75": st["p75"], "n": st["n"], "vsMedian": round(v - st["median"], 2),
                               "band": _band(v, st, direction), "lowerIsBetter": direction < 0, "dir": direction,
                               "pct": _pct(v, [x[k] for x in rvals], direction)})
    # 상대 원딜 상성
    opp = row.get("opp")
    mu = next((x for x in bm.get("matchups", []) if x["opp"] == opp), None)
    if mu and mu["n"] >= mn["matchup"]:
        res["matchup"] = {"opp": opp, "oppKo": mu["oppKo"], "n": mu["n"], "winRate": mu["winRate"],
                          "goldDiff15Median": mu["goldDiff15"], "mine": mine["goldDiff15"]}
    # 빌드: 내 첫 두 코어가 기준 데이터에서 몇 번째로 많이 쓰였는지
    core12 = [b for b in bm["builds"]["core12"] if b["n"] >= mn["build"]]
    my12 = [i for i, _ in row["items"][:2]]
    hit = next((i for i, b in enumerate(core12) if b["key"] == my12), None)
    res["build"] = {"mine": " → ".join(iname(i) for i in my12) if my12 else None,
                    "rank": hit + 1 if hit is not None else None,
                    "top": [{"name": b["name"], "share": b["share"], "winRate": b["winRate"], "n": b["n"]} for b in core12[:3]]}
    ks = [b for b in bm["builds"]["keystone"] if b["n"] >= mn["build"]]
    my_ks = [row["keystone"], row["styles"][1]]
    res["keystone"] = {"rank": next((i + 1 for i, b in enumerate(ks) if b["key"] == my_ks), None),
                       "top": [{"name": b["name"], "share": b["share"], "n": b["n"], "winRate": b["winRate"]} for b in ks[:3]]}
    # 슬롯별 코어(1~3번째)와 스펠: 많이 쓰는 것, 그때 승률, 완성 시간(중앙값)
    res["slots"] = []
    for i in range(3):
        top = [b for b in bm["builds"].get(f"core{i + 1}", []) if b["n"] >= mn["build"]]
        my_it = row["items"][i] if len(row["items"]) > i else None
        res["slots"].append({"mine": {"name": iname(my_it[0]), "id": my_it[0], "time": my_it[1]} if my_it else None,
                             "rank": next((j + 1 for j, b in enumerate(top) if my_it and b["key"] == my_it[0]), None),
                             "top": [{"name": b["name"], "id": b["key"], "share": b["share"], "winRate": b["winRate"],
                                      "n": b["n"], "time": b.get("time")} for b in top[:3]]})
    sp = [b for b in bm["builds"].get("spells", []) if b["n"] >= mn["build"]]
    res["spells"] = {"rank": next((i + 1 for i, b in enumerate(sp) if b["key"] == row["spells"]), None),
                     "top": [{"name": b["name"], "share": b["share"], "winRate": b["winRate"], "n": b["n"]} for b in sp[:3]]}
    # 게임 길이별 승률, 첫 킬·포탑·용
    res["lengthWin"] = [dict(b, here=b["from"] * 60 <= row["dur"] < b["to"] * 60) for b in bm.get("lengthWin", [])]
    res["objectives"] = {k: dict(v, mine=row["x"].get(k)) for k, v in bm.get("objectives", {}).items()
                         if v.get("n", 0) >= mn["stat"]}
    # 서폿이 바텀에 있던 비율
    su = bm.get("support", {})
    if "sup" in row and su.get("atBotShare", {}).get("n", 0) >= mn["stat"]:
        x = row["sup"]
        res["support"] = {"mineAtBotShare": round(x["withMin"] / 12, 2), "medianAtBotShare": su["atBotShare"]["median"],
                          "mineCsPerMinWith": round(x["withCs"] / x["withMin"], 2) if x["withMin"] else None,
                          "medianCsPerMinWith": su.get("csPerMinWith", {}).get("median"),
                          "mineCsPerMinWithout": round(x["withoutCs"] / x["withoutMin"], 2) if x["withoutMin"] else None,
                          "medianCsPerMinWithout": su.get("csPerMinWithout", {}).get("median")}
    return res


BOT = lambda p: p["x"] > 9000 and p["y"] < 6000  # 바텀 근처 (1분 위치라 대략적)


def lane_support(frames, events, my, opp, sup, team, by, nm, start=2, end=14):
    """라인전(2:00~14:00) 동안 아군 서폿이 바텀에 있었는지와, 그에 따라 나눈 CS.
    1분 구간 양 끝 모두 서폿이 바텀에 있으면 '서폿 있을 때', 아니면 '서폿 없을 때'로 CS 증가량을 더해요."""
    def f(m, pid):
        return frames[min(m, len(frames) - 1)]["participantFrames"][str(pid)]

    def cs(m, pid):
        x = f(m, pid)
        return x["minionsKilled"] + x["jungleMinionsKilled"]
    at = {m: BOT(f(m, sup)["position"]) for m in range(start, end + 1)}
    w, wo, away = {"me": 0, "opp": 0}, {"me": 0, "opp": 0}, []
    for m in range(start, end):
        both = at[m] and at[m + 1]
        t = w if both else wo
        t["me"] += cs(m + 1, my) - cs(m, my)
        t["opp"] += cs(m + 1, opp) - cs(m, opp)
        if not both:
            if away and away[-1][1] == m:
                away[-1][1] = m + 1
            else:
                away.append([m, m + 1])
    # 14:00까지 바텀 근처에서 맞라인 원딜이 죽은 것 / 내가 죽은 것. 서폿이나 정글이 막타를 친 것도 세요.
    kills = [e for e in events if e["type"] == "CHAMPION_KILL" and e["timestamp"] < end * 60000 and BOT(e["position"])]
    od = [{"t": mmss(e["timestamp"]), "killer": nm(e["killerId"])} for e in kills if e["victimId"] == opp]
    md = [{"t": mmss(e["timestamp"]), "killer": nm(e["killerId"])} for e in kills if e["victimId"] == my]
    return {"supportAtBot": {str(m): v for m, v in at.items()},
            "csWithSupport": w, "csWithoutSupport": wo,
            "supportAwayRanges": [f"{a}~{b}분" for a, b in away],
            "botAdcKills": {"opp": len(od), "me": len(md), "oppDeaths": od, "myDeaths": md}}


if __name__ == "__main__":
    raw = json.load(gzip.open(sys.argv[1], "rt", encoding="utf-8"))
    live = json.load(open(sys.argv[3], encoding="utf-8")) if len(sys.argv) > 3 and sys.argv[3] != "-" else None
    load_dd(sys.argv[4] if len(sys.argv) > 4 else os.path.dirname(sys.argv[1]))
    res = analyze(raw, sys.argv[2], live)
    out_dir = sys.argv[5] if len(sys.argv) > 5 else os.path.dirname(sys.argv[1])
    out = os.path.join(out_dir, os.path.basename(sys.argv[1]).replace(".json.gz", ".analysis.json"))
    json.dump(res, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    print("saved")
