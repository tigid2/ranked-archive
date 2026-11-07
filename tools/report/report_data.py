"""판별 리포트 데이터 JSON 만들기 (React 리포트 화면이 읽는 파일)

예전 build2.py의 계산 부분만 떼어 냈어요. 화면(HTML)은 web/ 의 React 앱이 그려요.
닉네임(riotId, summonerName)은 넣지 않아요.

사용 (저장소 맨 위에서):
  python3 tools/report/report_data.py KR_8448036968        # 한 판
  python3 tools/report/report_data.py --all                # raw/ 의 모든 판 (analyze.py도 다시 돌려요)
결과: docs/report-data/<경기ID>.json, docs/report-data/index.json(만들어진 판 목록)
"""
import gzip, json, os, re, sys, datetime as dt

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
DATA = os.path.join(ROOT, "data")
OUT_DIR = os.path.join(ROOT, "docs", "report-data")
VER = "16.22.1"  # 아이콘을 받을 Data Dragon 버전
SCHEMA = 1

DD_CH = json.load(open(os.path.join(DATA, "dd_champion.json"), encoding="utf-8"))["data"]
DD_IT = json.load(open(os.path.join(DATA, "dd_item.json"), encoding="utf-8"))["data"]
DD_SP = json.load(open(os.path.join(DATA, "dd_summoner.json"), encoding="utf-8"))["data"]
DD_RU = json.load(open(os.path.join(DATA, "dd_runesReforged.json"), encoding="utf-8"))
KO2KEY = {v["name"]: k for k, v in DD_CH.items()}
SPELL_KEY = {}
for _k, _v in DD_SP.items():
    if _v["key"] not in SPELL_KEY or "_" not in _k:
        SPELL_KEY[_v["key"]] = _k
PERK, STYLE = {}, {}
for _s in DD_RU:
    STYLE[_s["id"]] = (_s["name"], _s["icon"])
    for _sl in _s["slots"]:
        for _r in _sl["runes"]:
            PERK[_r["id"]] = (_r["name"], _r["icon"])
SHARD = {5005: ("공격 속도", "StatModsAttackSpeedIcon.png"), 5008: ("적응형 능력치", "StatModsAdaptiveForceIcon.png"),
         5001: ("체력 증가(성장)", "StatModsHealthScalingIcon.png"), 5011: ("체력", "StatModsHealthPlusIcon.png"),
         5007: ("스킬 가속", "StatModsCDRScalingIcon.png"), 5010: ("이동 속도", "StatModsMovementSpeedIcon.png"),
         5013: ("강인함/둔화 저항", "StatModsTenacityIcon.png"), 5002: ("방어력", "StatModsArmorIcon.png"),
         5003: ("마법 저항력", "StatModsMagicResIcon.png")}
NONCHAMP = {"미니언": "minion", "바론": "baron", "포탑": "tower", "드래곤": "dragon", "전령": "herald"}
OBJ_KO = {"DRAGON": "드래곤", "BARON_NASHOR": "바론", "RIFTHERALD": "전령", "HORDE": "공허 유충", "ATAKHAN": "아타칸"}
DRAKE_KO = {"WATER_DRAGON": "바다", "EARTH_DRAGON": "대지", "FIRE_DRAGON": "화염", "AIR_DRAGON": "바람",
            "HEXTECH_DRAGON": "마법공학", "CHEMTECH_DRAGON": "화학공학", "ELDER_DRAGON": "장로"}
OBJ_ICON = {"DRAGON": "dragon", "BARON_NASHOR": "baron", "RIFTHERALD": "herald", "HORDE": "grub",
            "TOWER": "tower", "INHIB": "inhib", "ATAKHAN": "atakhan"}
ORDER = ["TOP", "JUNGLE", "MIDDLE", "BOTTOM", "UTILITY"]
POS_KO = {"TOP": "탑", "JUNGLE": "정글", "MIDDLE": "미드", "BOTTOM": "원딜", "UTILITY": "서폿"}


# ---------- 아이콘 주소 ----------
# 주소는 Data Dragon CDN(https://ddragon.leagueoflegends.com/cdn/) 기준 경로로만 적어요.
# 화면은 이 앞에 CDN 주소를 붙이고, artifact용 한 파일은 이 경로로 그림을 받아 파일 안에 넣어요.
from lab_data import build_lab  # noqa: E402


def champ(key, name=None):
    if not key:
        n = name or "?"
        return {"k": None, "n": n, "glyph": NONCHAMP.get(n, "minion")}
    return {"k": key, "n": name or (DD_CH[key]["name"] if key in DD_CH else key),
            "img": f"{VER}/img/champion/{key}.png"}


def champ_label(label):
    """analyze.py의 '이즈리얼(적)' 같은 이름 → 챔피언 아이콘 정보"""
    n = label.split("(")[0]
    return champ(KO2KEY.get(n), n)


def is_complete(i):
    d = DD_IT.get(str(i), {})
    tags = d.get("tags", [])
    if "Consumable" in tags or "Trinket" in tags:
        return False
    return not d.get("into") and d.get("gold", {}).get("total", 0) >= 900


def item(i):
    if not i:
        return None
    return {"id": i, "n": DD_IT.get(str(i), {}).get("name", str(i)), "img": f"{VER}/img/item/{i}.png", "done": is_complete(i)}


def spell(sid):
    k = SPELL_KEY[str(sid)]
    return {"key": k, "n": DD_SP[k]["name"], "img": f"{VER}/img/spell/{k}.png"}


def perk(pid):
    n, p = PERK[pid]
    return {"n": n, "img": "img/" + p}


def style(sid):
    n, p = STYLE[sid]
    return {"n": n, "img": "img/" + p}


def shard(sid):
    n, f = SHARD.get(sid, (str(sid), "StatModsAdaptiveForceIcon.png"))
    return {"n": n, "img": "img/perk-images/StatMods/" + f}


def mmss(ms):
    s = int(ms // 1000)
    return f"{s // 60}:{s % 60:02d}"


def tsec(t):
    m, s = t.split(":")
    return int(m) * 60 + int(s)


def phase(sec):
    return "라인전" if sec < 14 * 60 else ("중반부" if sec < 25 * 60 else "후반부")


def josa(word, batchim="과", none="와"):
    ch = word[-1]
    if "가" <= ch <= "힣":
        return word + (batchim if (ord(ch) - 0xAC00) % 28 else none)
    return word + none


def rank_of(mid):
    """docs/data/games.json의 rankAfter('플래티넘 4 49LP') → {'tier', 'lp'}"""
    p = os.path.join(ROOT, "docs", "data", "games.json")
    if not os.path.exists(p):
        return None
    g = next((x for x in json.load(open(p, encoding="utf-8")) if x["matchId"] == mid), None)
    m = re.match(r"(.+?)\s*(\d+)\s*LP$", (g or {}).get("rankAfter") or "")
    return {"tier": m.group(1), "lp": int(m.group(2)), "change": g.get("lpChange")} if m else None


# ---------- 한 판 ----------
def build(mid, champ_id=None):
    raw = json.load(gzip.open(os.path.join(ROOT, "raw", mid + ".json.gz"), "rt", encoding="utf-8"))
    A = json.load(open(os.path.join(ROOT, "analysis", mid + ".analysis.json"), encoding="utf-8"))
    fb_path = os.path.join(ROOT, "feedback", mid + ".json")
    FB = json.load(open(fb_path, encoding="utf-8")) if os.path.exists(fb_path) else None
    CHAMP = champ_id or A["champion"]

    info = raw["match"]["info"]
    frames = raw["timeline"]["info"]["frames"]
    events = [e for f in frames for e in f["events"]]
    P = info["participants"]
    ME = next(p for p in P if p["championName"] == CHAMP)
    MY_TEAM = ME["teamId"]
    OPP = next(p for p in P if p["teamId"] != MY_TEAM and p["teamPosition"] == ME["teamPosition"])
    my_pid, opp_pid = ME["participantId"], OPP["participantId"]
    dur = info["gameDuration"]
    mins = dur / 60
    flow = A["flow"]

    def pf(minute, pid):
        f = frames[min(minute, len(frames) - 1)]["participantFrames"][str(pid)]
        return {"gold": f["totalGold"], "cs": f["minionsKilled"] + f["jungleMinionsKilled"], "xp": f["xp"]}

    kills_ev = [e for e in events if e["type"] == "CHAMPION_KILL"]
    my_deaths_ev = [e for e in kills_ev if e["victimId"] == my_pid]
    my_kills_ev = [e for e in kills_ev if e["killerId"] == my_pid]
    my_assist_ev = [e for e in kills_ev if my_pid in e.get("assistingParticipantIds", [])]

    def purchases(pid):
        out = []
        for e in events:
            if e.get("participantId") != pid:
                continue
            if e["type"] == "ITEM_PURCHASED":
                out.append([e["timestamp"], e["itemId"]])
            elif e["type"] == "ITEM_UNDO":
                for j in range(len(out) - 1, -1, -1):
                    if out[j][1] == e.get("beforeId"):
                        out.pop(j)
                        break
        return out

    my_purch, opp_purch = purchases(my_pid), purchases(opp_pid)

    # 오브젝트·건물
    objs = []
    for e in events:
        if e["type"] == "ELITE_MONSTER_KILL":
            if e.get("killerTeamId") not in (100, 200):
                continue
            n = OBJ_KO.get(e["monsterType"], e["monsterType"])
            if e["monsterType"] == "DRAGON":
                n = DRAKE_KO.get(e.get("monsterSubType"), "") + " 드래곤"
            objs.append({"t": e["timestamp"], "kind": e["monsterType"], "name": n, "ours": e["killerTeamId"] == MY_TEAM})
        elif e["type"] == "BUILDING_KILL":
            lane = {"TOP_LANE": "탑", "MID_LANE": "미드", "BOT_LANE": "바텀"}.get(e.get("laneType"), "")
            if e.get("buildingType") == "INHIBITOR_BUILDING":
                n, kind = f"{lane} 억제기", "INHIB"
            else:
                tt = {"OUTER_TURRET": "1차", "INNER_TURRET": "2차", "BASE_TURRET": "3차", "NEXUS_TURRET": "쌍둥이"}.get(e.get("towerType"), "")
                n, kind = f"{lane} {tt} 포탑".strip(), "TOWER"
            objs.append({"t": e["timestamp"], "kind": kind, "name": n, "ours": e["teamId"] != MY_TEAM})
    objs = merge_grubs(objs)
    for o in objs:
        o["icon"] = OBJ_ICON.get(o["kind"], "tower")

    team_rows = {MY_TEAM: [], 300 - MY_TEAM: []}
    for p in sorted(P, key=lambda p: ORDER.index(p["teamPosition"])):
        team_rows[p["teamId"]].append(p)
    team_kills = {t: sum(p["kills"] for p in rows) for t, rows in team_rows.items()}
    team_obj = {t["teamId"]: t["objectives"] for t in info["teams"]}

    def loadout(p):
        return {"champ": champ(p["championName"]), "level": p["champLevel"],
                "spells": [spell(p["summoner1Id"]), spell(p["summoner2Id"])],
                "keystone": perk(p["perks"]["styles"][0]["selections"][0]["perk"]),
                "subStyle": style(p["perks"]["styles"][1]["style"])}

    def items_of(p):
        return [item(p[f"item{i}"]) for i in range(7)]  # 마지막(7번째)은 장신구

    cs_of = lambda p: p["totalMinionsKilled"] + p["neutralMinionsKilled"]
    k, d, a = ME["kills"], ME["deaths"], ME["assists"]

    # ----- 히어로 -----
    t = dt.datetime.fromtimestamp(info["gameStartTimestamp"] / 1000, dt.timezone(dt.timedelta(hours=9)))
    duo = next(p for p in team_rows[MY_TEAM] if p["teamPosition"] == "UTILITY")
    eduo = next(p for p in team_rows[300 - MY_TEAM] if p["teamPosition"] == "UTILITY")
    gv = info["gameVersion"].split(".")
    hero = {
        "win": ME["win"], "when": f"{t.month}.{t.day:02d} {t.hour:02d}:{t.minute:02d}", "startIso": t.isoformat(),
        "patch": f"{int(gv[0]) + 10}.{gv[1]}", "durationSec": dur, "rank": rank_of(mid),
        "loadout": loadout(ME), "items": items_of(ME),
        "match": {"me": champ(CHAMP), "duo": champ(duo["championName"]), "opp": champ(OPP["championName"]), "eduo": champ(eduo["championName"])},
        "kda": [k, d, a], "kdaRatio": (k + a) / max(d, 1), "kp": A["basic"]["killParticipation"],
        "cs": cs_of(ME), "csPerMin": cs_of(ME) / mins, "oppCs": cs_of(OPP),
        "dmg": ME["totalDamageDealtToChampions"], "dmgShare": A["basic"]["damageShare"], "oppDmg": OPP["totalDamageDealtToChampions"],
        "gold": ME["goldEarned"], "goldPerMin": ME["goldEarned"] / mins, "oppGold": OPP["goldEarned"],
        "lane15": {"gold": flow[min(15, len(flow) - 1)]["laneGoldDiff"], "cs": flow[min(15, len(flow) - 1)]["laneCsDiff"]},
        "vision": ME["visionScore"], "wards": ME["wardsPlaced"], "controlWards": A["basic"].get("controlWards", 0),
    }

    # ----- 02 흐름 -----
    sw = swings(flow, dur, my_kills_ev, my_deaths_ev)
    ts = [e["timestamp"] for e in my_deaths_ev]
    cut = next((f["min"] for f in flow if f["teamGoldDiff"] <= -3000), None)
    cs_at = lambda m: next(f["cs"] for f in flow if f["min"] == m)
    peak = max(flow, key=lambda f: f["teamGoldDiff"])
    at = lambda m: flow[min(m, len(flow) - 1)]["teamGoldDiff"]
    flow_out = {
        "points": [{"min": f["min"], "team": f["teamGoldDiff"], "bot": f["botGoldDiff"]} for f in flow],
        "myKills": [e["timestamp"] for e in my_kills_ev], "myDeaths": ts, "objs": objs,
        "gd14": at(14), "gd25": at(25) if dur >= 25 * 60 else None,  # 25분 전에 끝난 판은 비워요 "gdMin": min(f["teamGoldDiff"] for f in flow), "final": flow[-1]["teamGoldDiff"],
        "peak": {"min": peak["min"], "v": peak["teamGoldDiff"]}, "swings": sw,
        "focus": {"chain": sum(1 for x, y in zip(ts, ts[1:]) if y - x <= 120000), "cut": cut,
                  "before": cs_at(cut) / cut if cut else None,
                  "after": (cs_at(flow[-1]["min"]) - cs_at(cut)) / max(dur / 60 - cut, 1) if cut else None,
                  "alone": sum(1 for x in A["deaths"] if not x["alliesNear"] or x["fight"]["size"] == 1)},
    }

    # ----- 03 라인전 -----
    m10, o10, m15, o15 = pf(10, my_pid), pf(10, opp_pid), pf(15, my_pid), pf(15, opp_pid)
    lv = A["levels"]
    L = A.get("lane")

    def solo(killer, victim, until=14 * 60000):
        return sum(1 for e in kills_ev if e["killerId"] == killer and e["victimId"] == victim
                   and not e.get("assistingParticipantIds") and e["timestamp"] < until)
    lane = {
        "rows": [{"label": lab, "me": m[key], "opp": o[key]} for lab, m, o, key in [
            ("10분 CS", m10, o10, "cs"), ("10분 골드", m10, o10, "gold"), ("10분 경험치", m10, o10, "xp"),
            ("15분 CS", m15, o15, "cs"), ("15분 골드", m15, o15, "gold"), ("15분 경험치", m15, o15, "xp")]],
        "support": None if not L else {
            "atBot": [{"min": int(m), "in": bool(v)} for m, v in L["supportAtBot"].items()],
            "with": L["csWithSupport"], "without": L["csWithoutSupport"]},
        "botAdcKills": L["botAdcKills"] if L else None,
        "soloKills": {"me": solo(my_pid, opp_pid), "opp": solo(opp_pid, my_pid)},
        "first2": tsec(lv["2"]["me"]) < tsec(lv["2"]["opp"]) if "2" in lv else None,
        "maxCsAdv": A["basic"].get("maxCsAdvantage", 0),
        "levels": [{"lv": n, "me": v["me"], "opp": v["opp"],
                    "meAhead": tsec(v["me"]) < tsec(v["opp"]), "oppAhead": tsec(v["opp"]) < tsec(v["me"])} for n, v in lv.items()],
    }

    # ----- 04 죽음 -----
    S = 460

    def mp(pos):
        return {"x": round((pos["x"] + 120) / 14990 * S, 1), "y": round(S - (pos["y"] + 120) / 15100 * S, 1)}
    idx = {mmss(e["timestamp"]): i for i, e in enumerate(my_deaths_ev, 1)}
    death_list = []
    for x in A["deaths"]:
        lg = (x.get("live") or {}).get("gold")
        death_list.append({
            "no": idx.get(x["t"]), "t": x["t"], "phase": phase(tsec(x["t"])), "zone": x["zone"],
            "killer": champ_label(x["killer"]), "assists": [champ_label(n) for n in x["assists"]],
            "alliesNear": [champ_label(n) for n in x["alliesNear"]], "enemiesNear": [champ_label(n) for n in x["enemiesNear"]],
            "gold": lg if lg is not None else x["approxGold"], "goldFromLive": lg is not None,
            "spells": death_spells(x, ME), "teamGoldDiff": x["teamGoldDiff"], "lostAfter": x["lostAfter"],
            "roams": [{"who": champ_label(r["who"]), "minuteMark": r["minuteMark"], "wasAt": r["wasAt"]} for r in x["roams"]],
            "damage": [{"who": champ_label(n), "v": v} for n, v in x["damage"]],
        })
    ph = {"라인전": 0, "중반부": 0, "후반부": 0}
    for e in my_deaths_ev:
        ph[phase(e["timestamp"] / 1000)] += 1
    zk = {"라인": 0, "강가": 0, "정글": 0, "본진": 0}
    for x in A["deaths"]:
        z = x["zone"]
        zk["강가" if "강가" in z else "정글" if "정글" in z else "본진" if "본진" in z else "라인"] += 1
    deaths = {
        "total": d, "list": death_list,
        "map": {"size": S, "deaths": [dict(mp(e["position"]), t=mmss(e["timestamp"]), no=i) for i, e in enumerate(my_deaths_ev, 1)],
                "kills": [dict(mp(e["position"]), t=mmss(e["timestamp"]), solid=e in my_kills_ev) for e in my_kills_ev + my_assist_ev]},
        # 게임이 일찍 끝나면 없는 구간은 빼고, 마지막 구간은 경기 끝 시간에서 잘라요.
        "phases": [{"name": lab, "n": ph[lab], "from": a2, "to": min(b2, dur)} for lab, a2, b2 in
                   [("라인전", 0, 14 * 60), ("중반부", 14 * 60, 25 * 60), ("후반부", 25 * 60, dur)] if a2 < dur],
        "zones": [{"name": z, "n": n} for z, n in zk.items()],
        "lostN": sum(1 for x in A["deaths"] if x["lostAfter"]),
        "roamN": sum(1 for x in A["deaths"] if any(r["distance"] > 4000 for r in x["roams"])),
        "alone": sum(1 for x in A["deaths"] if not x["alliesNear"]),
    }

    # ----- 05 팀 -----
    us, th = MY_TEAM, 300 - MY_TEAM

    def team(tid):
        rows = team_rows[tid]
        kp_of = lambda p: (p["kills"] + p["assists"]) / max(team_kills[tid], 1)
        tops = {"kp": max(map(kp_of, rows)), "gold": max(p["goldEarned"] for p in rows), "cs": max(map(cs_of, rows)),
                "dmg": max(p["totalDamageDealtToChampions"] for p in rows)}
        return {"ours": tid == MY_TEAM, "win": rows[0]["win"], "kills": team_kills[tid], "players": [{
            "me": p["participantId"] == my_pid, "pos": POS_KO[p["teamPosition"]], "loadout": loadout(p),
            "kda": [p["kills"], p["deaths"], p["assists"]], "kdaRatio": (p["kills"] + p["assists"]) / max(p["deaths"], 1),
            "kp": round(kp_of(p) * 100), "topKp": kp_of(p) == tops["kp"],
            "dmg": p["totalDamageDealtToChampions"], "topDmg": p["totalDamageDealtToChampions"] == tops["dmg"],
            "gold": p["goldEarned"], "topGold": p["goldEarned"] == tops["gold"],
            "cs": cs_of(p), "topCs": cs_of(p) == tops["cs"], "vision": p["visionScore"], "items": items_of(p)} for p in rows]}

    def tot(f):
        return [sum(f(p) for p in team_rows[us]), sum(f(p) for p in team_rows[th])]
    ob = lambda key: [team_obj[us][key]["kills"], team_obj[th][key]["kills"]]
    teams = {
        "maxDmg": max(p["totalDamageDealtToChampions"] for p in P),
        "compare": [{"label": lab, "v": v, "neutral": lab == "받은 피해"} for lab, v in [
            ("킬", [team_kills[us], team_kills[th]]), ("골드", tot(lambda p: p["goldEarned"])),
            ("챔피언 피해", tot(lambda p: p["totalDamageDealtToChampions"])), ("받은 피해", tot(lambda p: p["totalDamageTaken"])),
            ("CS", tot(cs_of)), ("시야 점수", tot(lambda p: p["visionScore"])), ("포탑", ob("tower")),
            ("드래곤", ob("dragon")), ("공허 유충", ob("horde")), ("바론", ob("baron"))]],
        "ours": team(us), "theirs": team(th),
    }

    # ----- 06 빌드 -----
    sel = ME["perks"]["styles"]
    prim, sub = sel[0], sel[1]
    sh = ME["perks"]["statPerks"]
    casts = {x["name"]: x["casts"] for x in A["spells"]}
    sk = A["skills"]["casts"]
    cfile = os.path.join(DATA, f"dd_champ_{CHAMP}.json")
    cdet = json.load(open(cfile, encoding="utf-8"))["data"][CHAMP]["spells"] if os.path.exists(cfile) else None
    my_spells = [spell(ME["summoner1Id"]), spell(ME["summoner2Id"])]
    for s in my_spells:
        s["casts"] = casts.get(s["n"], 0)
    build_out = {
        "timeline": {
            "me": [{"t": t_, "item": item(i)} for t_, i in my_purch if is_complete(i)],
            "opp": [{"t": t_, "item": item(i)} for t_, i in opp_purch if is_complete(i)]},
        "buys": [{"t": g["t0"], "items": [item(i) for i in g["items"]]} for g in groups(my_purch)],
        "runes": {"primary": style(prim["style"]), "secondary": style(sub["style"]),
                  "keystone": perk(prim["selections"][0]["perk"]),
                  "minor": [perk(x["perk"]) for x in prim["selections"][1:]],
                  "sub": [perk(x["perk"]) for x in sub["selections"]],
                  "shards": [shard(s) for s in [sh["offense"], sh["flex"], sh["defense"]]]},
        "spells": my_spells,
        "skills": [{"key": "QWER"[i], "casts": sk[i], "perMin": sk[i] / mins,
                    "n": cdet[i]["name"] if cdet else "QWER"[i],
                    "img": f"{VER}/img/spell/{cdet[i]['image']['full']}" if cdet else None} for i in range(4)],
        "skillshotsHit": A["skills"].get("skillshotsHit"), "skillshotsDodged": A["skills"].get("skillshotsDodged"),
    }

    return {
        "schema": SCHEMA, "matchId": mid, "generated": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "me": champ(CHAMP), "opp": champ(OPP["championName"]), "oppWith": josa(champ(OPP["championName"])["n"]),
        "hero": hero, "flow": flow_out, "lane": lane, "deaths": deaths, "team": teams, "build": build_out,
        "feedback": FB,
        # 실험 페이지(?lab=1)용. 기존 리포트 화면은 읽지 않아요.
        "lab": build_lab(raw, A, ME, OPP, item, champ),
    }


def merge_grubs(objs, gap=30000):
    """공허 유충은 세 마리가 모여 있어서, 이어서(앞 유충과 gap 안에) 잡힌 것은 한 묶음으로 본다.
    묶음 안에서 더 많이 먹은 팀 하나만 남긴다(같은 수면 둘 다 남긴다)."""
    rest, gs = [], []
    for o in objs:
        if o["kind"] != "HORDE":
            rest.append(o)
        elif gs and o["t"] - gs[-1][-1]["t"] <= gap:
            gs[-1].append(o)
        else:
            gs.append([o])
    for g in gs:
        cnt = {True: [x for x in g if x["ours"]], False: [x for x in g if not x["ours"]]}
        top = max(len(v) for v in cnt.values())
        for ours, xs in cnt.items():
            if xs and len(xs) == top:
                rest.append({"t": xs[0]["t"], "kind": "HORDE", "name": f"공허 유충 {len(xs)}마리", "ours": ours})
    return sorted(rest, key=lambda o: o["t"])


def groups(purch, gap=45000):
    g = []
    for t, i in purch:
        if g and t - g[-1]["t1"] <= gap:
            g[-1]["items"].append(i)
            g[-1]["t1"] = t
        else:
            g.append({"t0": t, "t1": t, "items": [i]})
    return g


def swings(flow, dur, my_kills_ev, my_deaths_ev, th=1500):
    """분당 팀 골드 차이를 '따라잡음/벌어짐' 구간으로 나눈다(th 이상 움직여야 방향이 바뀐 걸로 본다)."""
    pts = [(f["min"], f["teamGoldDiff"]) for f in flow]
    piv = [pts[0]]
    ext, d = pts[0], 0
    for m, v in pts[1:]:
        if d >= 0 and v >= ext[1] or d <= 0 and v <= ext[1]:
            if d == 0 and abs(v - piv[-1][1]) >= th:
                d = 1 if v > piv[-1][1] else -1
            ext = (m, v) if (d != 0 or abs(v - piv[-1][1]) >= abs(ext[1] - piv[-1][1])) else ext
        if d != 0 and abs(v - ext[1]) >= th and (v - ext[1]) * d < 0:
            piv.append(ext); ext, d = (m, v), -d
        elif d == 0 and abs(v - piv[-1][1]) > abs(ext[1] - piv[-1][1]):
            ext = (m, v)
    piv.append(ext)
    if piv[-1][0] != pts[-1][0]:
        piv.append(pts[-1])
    # 끝에 남은 아주 짧고 작은 움직임(예: 21~21분 +237)은 구간으로 치지 않아요.
    if len(piv) > 2 and abs(piv[-1][1] - piv[-2][1]) < th and piv[-1][0] - piv[-2][0] <= 1:
        piv.pop()
    out = []
    for n, ((m0, v0), (m1, v1)) in enumerate(zip(piv, piv[1:]), 1):
        a, b = m0 * 60000, m1 * 60000 if n < len(piv) - 1 else dur * 1000 + 1  # 마지막 구간은 경기 끝까지
        out.append({"m0": m0, "m1": m1, "delta": v1 - v0,
                    "kills": sum(1 for e in my_kills_ev if a <= e["timestamp"] < b),
                    "deaths": sum(1 for e in my_deaths_ev if a <= e["timestamp"] < b)})
    return out


SPELL_VERDICT = {"held": ("들고 죽음", "bad"), "used_before": ("직전에 씀", "line"),
                 "already_down": ("쿨타임", "line"), "uncertain": ("판단 보류", "unknown")}
NO_RESULT = {None, "not_visible", "unknown"}


def death_spells(x, ME):
    """죽을 때 스펠 2개의 상태.
    state: 'none' = 게임 중 기록이 아예 없음('기록 없음'), 'unseen' = 기록은 있는데 스펠 칸을 못 봄('확인 못 함'),
           'each' = 스펠마다 결과(verdict가 없으면 그 스펠만 '확인 못 함')"""
    sps = x.get("spells") or (x.get("live") or {}).get("spells") or []
    live = {str(sp.get("key")): sp.get("verdict") for sp in sps}
    out = []
    for sid in [ME["summoner1Id"], ME["summoner2Id"]]:
        s = spell(sid)
        v = live.get(s["key"])
        if v not in NO_RESULT:
            lab, tone = SPELL_VERDICT.get(v, ("확인 못 함", "unknown"))
            s.update(verdict=v, label=lab, tone=tone)
        out.append(s)
    state = "none" if not live else ("unseen" if all(s.get("verdict") is None for s in out) else "each")
    return {"state": state, "list": out}


def run_analyze(mid, champ_id):
    """분석 결과가 없을 때 analyze.py를 불러서 만들어요."""
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    import analyze as AZ
    raw_p = os.path.join(ROOT, "raw", mid + ".json.gz")
    live_p = os.path.join(ROOT, "raw", mid + ".live.json")
    if not os.path.exists(live_p):
        # 경기 기록 갱신이 짝지어 둔 게임 중 기록(live/)이 있으면 raw/ 로 복사해 두고 써요(live/ 파일은 나중에 지워질 수 있어서).
        lf = live_file_of(mid)
        if lf and os.path.exists(os.path.join(ROOT, "live", lf)):
            open(live_p, "wb").write(open(os.path.join(ROOT, "live", lf), "rb").read())
    raw = json.load(gzip.open(raw_p, "rt", encoding="utf-8"))
    live = json.load(open(live_p, encoding="utf-8")) if os.path.exists(live_p) else None
    AZ.load_dd(DATA)
    res = AZ.analyze(raw, champ_id, live)
    os.makedirs(os.path.join(ROOT, "analysis"), exist_ok=True)
    json.dump(res, open(os.path.join(ROOT, "analysis", mid + ".analysis.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def write_index():
    """만들어진 리포트 목록(화면이 '다른 판' 링크에 써요)."""
    items = []
    for f in sorted(os.listdir(OUT_DIR)):
        if not f.startswith("KR_") or not f.endswith(".json"):
            continue
        r = json.load(open(os.path.join(OUT_DIR, f), encoding="utf-8"))
        items.append({"matchId": r["matchId"], "start": r["hero"]["startIso"], "champ": r["me"]["n"], "win": r["hero"]["win"],
                      "hasFeedback": r["feedback"] is not None})
    items.sort(key=lambda x: x["start"], reverse=True)
    json.dump(items, open(os.path.join(OUT_DIR, "index.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def live_file_of(mid):
    p = os.path.join(ROOT, "docs", "data", "games.json")
    g = next((x for x in json.load(open(p, encoding="utf-8")) if x["matchId"] == mid), None) if os.path.exists(p) else None
    return (g or {}).get("liveFile")


def games_champ():
    p = os.path.join(ROOT, "docs", "data", "games.json")
    return {g["matchId"]: g["championId"] for g in json.load(open(p, encoding="utf-8"))} if os.path.exists(p) else {}


def main(args):
    os.makedirs(OUT_DIR, exist_ok=True)
    champs = games_champ()
    if args and args[0] == "--all":
        mids = sorted(f[:-8] for f in os.listdir(os.path.join(ROOT, "raw")) if f.endswith(".json.gz"))
    else:
        mids = args
    for mid in mids:
        champ_id = champs.get(mid)
        try:
            # 분석은 매번 다시 해요(몇 초 안 걸려요). analyze.py나 기준 데이터가 바뀌어도 리포트가 따라가게 하려고요.
            if champ_id:
                run_analyze(mid, champ_id)
            elif not os.path.exists(os.path.join(ROOT, "analysis", mid + ".analysis.json")):
                print(mid, "챔피언을 몰라서 건너뜀(games.json에 없음)")
                continue
            data = build(mid, champ_id)
        except Exception as e:  # 한 판이 실패해도 나머지는 만들어요
            print(mid, "실패:", type(e).__name__, e)
            continue
        out = os.path.join(OUT_DIR, mid + ".json")
        old = json.load(open(out, encoding="utf-8")) if os.path.exists(out) else None
        if old:  # 내용이 같으면 만든 시각만 바뀌지 않게 그대로 둬요(쓸데없는 커밋 막기)
            old_g, data_g = old.pop("generated", None), data.pop("generated")
            if old == data:
                print(mid, "바뀐 것 없음")
                continue
            data["generated"] = data_g
        json.dump(data, open(out, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
        print(mid, "→", os.path.relpath(out, ROOT), os.path.getsize(out) // 1024, "KB")
    write_index()


if __name__ == "__main__":
    main(sys.argv[1:])
