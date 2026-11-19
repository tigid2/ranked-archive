"""판별 리포트 데이터 JSON 만들기 (React 리포트 화면이 읽는 파일)

예전 build2.py의 계산 부분만 떼어 냈어요. 화면(HTML)은 web/ 의 React 앱이 그려요.
닉네임(riotId, summonerName)은 넣지 않아요.

사용 (저장소 맨 위에서):
  python3 tools/report/report_data.py KR_8448036968        # 한 판
  python3 tools/report/report_data.py --all                # raw/ 의 모든 판 (analyze.py도 다시 돌려요)
결과: docs/report-data/<경기ID>.json, docs/report-data/index.json(만들어진 판 목록)
      단, tools/report/public.json 에 없는 판은 tools/report/private-data/<경기ID>.json 에만 만들어요(비공개).
"""
import gzip, json, os, re, sys, datetime as dt

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
DATA = os.path.join(ROOT, "data")
OUT_DIR = os.path.join(ROOT, "docs", "report-data")
PRIVATE_DIR = os.path.join(HERE, "private-data")  # 공개 목록(public.json)에 없는 판. 저장소에 올리지 않아요(.gitignore)


def public_ids():
    p = os.path.join(HERE, "public.json")
    return set(json.load(open(p, encoding="utf-8"))["public"]) if os.path.exists(p) else set()
VER = "16.22.1"  # 아이콘을 받을 Data Dragon 버전
SCHEMA = 1

DD_CH = json.load(open(os.path.join(DATA, "dd_champion.json"), encoding="utf-8"))["data"]
DD_IT = json.load(open(os.path.join(DATA, "dd_item.json"), encoding="utf-8"))["data"]
DD_SP = json.load(open(os.path.join(DATA, "dd_summoner.json"), encoding="utf-8"))["data"]
DD_RU = json.load(open(os.path.join(DATA, "dd_runesReforged.json"), encoding="utf-8"))
_SPP = os.path.join(DATA, "dd_spells.json")  # 챔피언 스킬 이름·아이콘(tools/report/dd_spells.py로 만들어요)
DD_SK = json.load(open(_SPP, encoding="utf-8"))["data"] if os.path.exists(_SPP) else {}
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
OBJ_KO = {"DRAGON": "드래곤", "BARON_NASHOR": "바론", "RIFTHERALD": "전령", "HORDE": "공허 유충"}
DRAKE_KO = {"WATER_DRAGON": "바다", "EARTH_DRAGON": "대지", "FIRE_DRAGON": "화염", "AIR_DRAGON": "바람",
            "HEXTECH_DRAGON": "마법공학", "CHEMTECH_DRAGON": "화학공학", "ELDER_DRAGON": "장로"}
OBJ_ICON = {"DRAGON": "dragon", "BARON_NASHOR": "baron", "RIFTHERALD": "herald", "HORDE": "grub",
            "TOWER": "tower", "INHIB": "inhib"}
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


def nav_of(mid):
    """docs/data/games.json에서 이 판 바로 앞 판과 바로 다음 판(시간 순)을 찾아요. 리포트 끝의 '다음 판'에 써요."""
    p = os.path.join(ROOT, "docs", "data", "games.json")
    if not os.path.exists(p):
        return None
    gs = sorted((g for g in json.load(open(p, encoding="utf-8")) if g.get("start")), key=lambda g: g["start"])
    i = next((k for k, g in enumerate(gs) if g["matchId"] == mid), None)
    if i is None:
        return None

    def brief(g):
        return {"id": g["matchId"], "champ": g["champion"], "opp": g["opponent"], "win": g["win"],
                "when": g["start"][5:10].replace("-", ".") + " " + g["start"][11:16]}
    return {"prev": brief(gs[i - 1]) if i > 0 else None, "next": brief(gs[i + 1]) if i + 1 < len(gs) else None}


# ---------- 한 판 ----------
def build(mid, champ_id=None, lab=False):
    raw = json.load(gzip.open(os.path.join(ROOT, "raw", mid + ".json.gz"), "rt", encoding="utf-8"))
    A = json.load(open(os.path.join(ROOT, "analysis", mid + ".analysis.json"), encoding="utf-8"))
    # 공개 판 피드백은 feedback/, 공개하지 않는 판은 tools/report/private-feedback/(저장소에 안 올림, 원본은 PC 작업 폴더)
    fb_path = os.path.join(ROOT, "feedback", mid + ".json")
    if not os.path.exists(fb_path):
        fb_path = os.path.join(ROOT, "tools", "report", "private-feedback", mid + ".json")
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
            if e.get("killerTeamId") not in (100, 200) or e["monsterType"] not in OBJ_ICON:
                continue  # 아이콘이 없는 몬스터(예전 아타칸 등)는 빼요
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
        "gd14": at(14), "gd25": at(25) if dur >= 25 * 60 else None,  # 25분 전에 끝난 판은 비워요
        "gdMin": min(f["teamGoldDiff"] for f in flow), "final": flow[-1]["teamGoldDiff"],
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
            # 리플레이 1초 위치가 있으면 칸 하나 = 그 1분(예: 2 = 2:00~3:00) 동안 서폿이 반 넘게 바텀에 있었는지.
            # 아래 CS 나누기와 같은 기준이라 칸과 숫자가 맞아요. 없으면 예전처럼 매분 그 순간 위치예요.
            "atBot": [{"min": int(k.split("~")[0]), "in": v >= L["supportShareMin"]} for k, v in L["supportBotShare"].items()]
            if L.get("supportBotShare") else [{"min": int(m), "in": bool(v)} for m, v in L["supportAtBot"].items()],
            "with": L["csWithSupport"], "without": L["csWithoutSupport"]},
        "botAdcKills": L["botAdcKills"] if L else None,
        "soloKills": {"me": solo(my_pid, opp_pid), "opp": solo(opp_pid, my_pid)},
        "first2": tsec(lv["2"]["me"]) < tsec(lv["2"]["opp"]) if "2" in lv and lv["2"]["me"] and lv["2"]["opp"] else None,
        "maxCsAdv": round(A["basic"].get("maxCsAdvantage") or 0),  # 라이엇 값이 32.00000002980232 같은 소수라서 정수로
        "levels": [{"lv": n, "me": v["me"], "opp": v["opp"],
                    "meAhead": tsec(v["me"]) < tsec(v["opp"]), "oppAhead": tsec(v["opp"]) < tsec(v["me"])}
                   for n, v in lv.items() if v["me"] and v["opp"]],  # 둘 중 하나라도 못 찍은 레벨(짧은 판의 11레벨 등)은 빼요
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
    # 1초 위치(리플레이)가 있는 판은 미니맵 리플레이와 교전 시간을 붙여요(11-19). 없으면 None.
    rp = replay_block(mid, P, ME, events, dur, S, my_deaths_ev, A)
    deaths["replay"] = rp["replay"] if rp else None
    live_p = os.path.join(ROOT, "raw", mid + ".live.json")
    live = json.load(open(live_p, encoding="utf-8")) if os.path.exists(live_p) else None
    per = death_extras(P, ME, events, dur, my_deaths_ev, rp["tracks"] if rp else None, live)
    for x in death_list:
        x.update(per.get(x["t"], {}))

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

    LAB = build_lab(raw, A, ME, OPP, item, champ, perk, spell, is_complete)
    return {
        "schema": SCHEMA, "matchId": mid, "generated": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "me": champ(CHAMP), "opp": champ(OPP["championName"]), "oppWith": josa(champ(OPP["championName"])["n"]),
        "hero": hero, "nav": nav_of(mid), "flow": flow_out, "lane": lane, "deaths": deaths, "team": teams, "build": build_out,
        "feedback": FB,
        # plus: 실험 리포트에서 본 리포트로 옮긴 칸(11-16). 구간별 성적, 맞라인 차이, 첫 귀환, 피해 구성, 사이트 통계.
        "plus": {**{k: LAB[k] for k in ("phases", "minute", "back", "dmgMix")},
                 "site": {k: v for k, v in (LAB["site"] or {}).items() if k not in ("length", "objectives")} or None},
        # 실험 리포트용(--lab). 나머지 실험 칸은 공개 사이트 데이터에 넣지 않아요.
        **({"lab": LAB} if lab else {}),
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


SPELL_VERDICT = {"held": ("미사용", "bad"), "used_before": ("사용", "line"),
                 "already_down": ("없음", "line"), "uncertain": ("판단 보류", "unknown")}
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


# ----- 04 죽음: 미니맵 리플레이 (11-19) -----
FIGHT_R = 1000      # 적 챔피언이 이 거리 안에 있으면 피해·CC를 주고받은 것으로 봐요(위치로 하는 추정)
TURRET_R = 850      # 살아 있는 적 포탑 사거리(750) + 몸 크기
COMBAT_KEEP = 5     # 롤 규칙: 마지막 전투 상호작용 뒤 5초가 지나면 비전투 상태
FIGHT_BACK = 300    # 교전 시작은 죽기 전 최대 이 초까지만 거슬러 찾아요
TURRETS = {  # 포탑 자리(게임 좌표). 추정 시야에만 써요.
    100: [(981, 10441), (1512, 6699), (1169, 4287), (5846, 6396), (5048, 4812), (3651, 3696),
          (10504, 1029), (6919, 1483), (4281, 1253), (1748, 2270), (2177, 1807)],
    200: [(4318, 13875), (7943, 13411), (10481, 13650), (8955, 8510), (9767, 10113), (11134, 11207),
          (13866, 4505), (13327, 8226), (13624, 10572), (12611, 13084), (13052, 12612)],
}
SLOT = {0: "Q", 1: "W", 2: "E", 3: "R"}


def replay_block(mid, P, ME, events, dur, S, my_deaths_ev, A):
    path = os.path.join(ROOT, "raw", mid + ".pos.json.gz")
    if not os.path.exists(path):
        return None
    d = json.load(gzip.open(path, "rt", encoding="utf-8"))
    if d.get("format") != 1:
        return None
    # 게임 좌표 → 지도 좌표(0~S)를 10배 한 정수. 화면에서 10으로 나눠요.
    gx = lambda x: round((x + 120) / 14990 * S * 10)
    gy = lambda y: round((S - (y + 120) / 15100 * S) * 10)
    my_team = ME["teamId"]
    tracks, champs = {}, []
    for i, enc in enumerate(d["pos"]):
        tr, t, x, y = {}, 0, 0, 0
        for k in range(0, len(enc), 3):
            t, x, y = t + enc[k], x + enc[k + 1], y + enc[k + 2]
            tr[t] = (x, y)
        tracks[i + 1] = tr
    by = {p["participantId"]: p for p in P}
    out_tracks = []
    for pid in range(1, 11):
        p = by[pid]
        c = champ(p["championName"])
        champs.append({**c, "us": p["teamId"] == my_team, "me": pid == ME["participantId"]})
        enc, pt, px, py = [], 0, 0, 0
        for t in sorted(tracks.get(pid, {})):
            x, y = tracks[pid][t]
            X, Y = gx(x), gy(y)
            enc += [t - pt, X - px, Y - py]
            pt, px, py = t, X, Y
        out_tracks.append(enc)
    idx = lambda pid: pid - 1  # 화면의 챔피언 번호(0~9)
    ev = []
    for e in events:
        t = round(e["timestamp"] / 1000)
        pos = e.get("position")
        if e["type"] == "CHAMPION_KILL":
            ev.append({"k": "kill", "t": t, "x": gx(pos["x"]), "y": gy(pos["y"]), "by": idx(e["killerId"]) if e["killerId"] else None,
                       "who": idx(e["victimId"]), "us": by[e["victimId"]]["teamId"] != my_team})
        elif e["type"] == "ELITE_MONSTER_KILL":
            m = e.get("monsterType")
            g = {"DRAGON": "dragon", "BARON_NASHOR": "baron", "RIFTHERALD": "herald", "HORDE": "grub"}.get(m, "dragon")
            ev.append({"k": "obj", "t": t, "x": gx(pos["x"]), "y": gy(pos["y"]), "g": g, "us": e.get("killerTeamId") == my_team})
        elif e["type"] == "BUILDING_KILL":
            g = "tower" if e.get("buildingType") == "TOWER_BUILDING" else "inhib"
            ev.append({"k": "bld", "t": t, "x": gx(pos["x"]), "y": gy(pos["y"]), "g": g, "us": e.get("teamId") != my_team})
    # 추정 시야용: 우리 팀 와드, 우리 팀 포탑(부서진 시각까지)
    wc = d.get("wardCols") or []
    wards = []
    for w in d.get("wards") or []:
        w = dict(zip(wc, w))
        cr = w.get("creator")
        if cr and cr in by and by[cr]["teamId"] == my_team and w.get("x") is not None:
            r = 500 if w.get("type") == "BLUE_TRINKET" else 900
            wards.append([round(w["t"]), round(w["end_t"] if w.get("end_t") else dur), gx(w["x"]), gy(w["y"]), round(r / 14990 * S * 10)])
    dead_at = {}
    for e in events:
        if e["type"] == "BUILDING_KILL" and e.get("buildingType") == "TOWER_BUILDING" and e.get("teamId") == my_team:
            p2 = (e["position"]["x"], e["position"]["y"])
            near = min(TURRETS[my_team], key=lambda q: (q[0] - p2[0]) ** 2 + (q[1] - p2[1]) ** 2)
            dead_at[near] = round(e["timestamp"] / 1000)
    turrets = [[gx(x), gy(y), dead_at.get((x, y), dur)] for x, y in TURRETS[my_team]]

    return {"replay": {"size": S, "len": dur, "champs": champs, "tracks": out_tracks, "events": ev,
                       "wards": wards, "turrets": turrets, "sight": round(1200 / 14990 * S * 10)},
            "tracks": tracks}


# ----- 04 죽음: 사망 정보(롤 Death Recap처럼) + 교전 시간 (11-20) -----
UNIT_KO = {"MINION": "미니언", "TOWER": "포탑", "MONSTER": "몬스터"}
UNIT_GLYPH = {"MINION": "minion", "TOWER": "tower"}
MONSTER_KO = [("Baron", "바론", "baron"), ("Dragon", "드래곤", "dragon"), ("RiftHerald", "전령", "herald"),
              ("Horde", "공허 유충", "grub"), ("Atakhan", "아타칸", "baron")]
SUMM_BY_NAME = {v["id"].lower(): k for k, v in DD_SP.items()}


def dmg_source(h, key):
    """피해 한 줄(victimDamageReceived/Dealt) → 무엇으로 넣은 피해인지 (묶는 키, 표시 정보)"""
    sl, sn = h.get("spellSlot"), (h.get("spellName") or "").lower()
    sk = DD_SK.get(key or "", {})
    if sl in SLOT:
        k = SLOT[sl]
        n, img = sk.get(k, (k, None))
        return k, {"slot": k, "n": n, "img": f"{VER}/img/{img}" if img else None}
    if sl in (4, 5) and sn:
        sid = SUMM_BY_NAME.get(sn) or ("SummonerSmite" if "smite" in sn else None)
        if sid:
            return sid, {"slot": "spell", "n": DD_SP[sid]["name"], "img": f"{VER}/img/spell/{sid}.png"}
    if h.get("basic") or "attack" in sn:
        return "AA", {"slot": "AA", "n": "기본 공격"}
    if (sl == 63 and sn and sn != "burning") or (sn and ("passive" in sn or "plant" in sn)):
        n, img = sk.get("P", ("패시브", None))
        return "P", {"slot": "P", "n": n, "img": f"{VER}/img/{img}" if img else None}
    m = re.match(r"^(\d{4})active$", sn)
    iid = m.group(1) if m else (str(sl) if isinstance(sl, int) and str(sl) in DD_IT else None)
    if iid and iid in DD_IT:
        return "I" + iid, {"slot": "item", "n": DD_IT[iid]["name"], "img": f"{VER}/img/item/{iid}.png"}
    return "ETC", {"slot": "etc", "n": "기타 효과"}


def _sum(h):
    return h.get("physicalDamage", 0), h.get("magicDamage", 0), h.get("trueDamage", 0)


def recap_rows(hits, by, key_of):
    """피해 목록을 '누가' 단위 줄로 묶어요. 줄마다 물리/마법/고정, 무엇으로(parts), 쓴 궁·스펠(used)."""
    rows = {}
    for h in hits:
        who = key_of(h)
        if who is None:
            continue
        r = rows.setdefault(who[0], {**who[1], "v": 0, "ph": 0, "mg": 0, "tr": 0, "parts": {}})
        ph, mg, tr = _sum(h)
        r["v"] += ph + mg + tr; r["ph"] += ph; r["mg"] += mg; r["tr"] += tr
        if who[2]:
            pk, info = dmg_source(h, who[2])
            pt = r["parts"].setdefault(pk, {**info, "v": 0, "ph": 0, "mg": 0, "tr": 0})
            pt["v"] += ph + mg + tr; pt["ph"] += ph; pt["mg"] += mg; pt["tr"] += tr
    out = []
    for r in rows.values():
        parts = sorted((p for p in r["parts"].values() if p["v"] > 0), key=lambda p: -p["v"])
        r["parts"] = parts
        r["used"] = [{"slot": p["slot"], "n": p["n"], "img": p.get("img")} for p in parts if p["slot"] in ("R", "spell")]
        if r["v"] > 0:
            out.append(r)
    return sorted(out, key=lambda r: -r["v"])


def death_recap(e, by, ME):
    my_team = ME["teamId"]

    def recv(h):
        pid = h.get("participantId")
        if pid in by:
            if by[pid]["teamId"] == my_team:
                return None  # 아군 효과로 잡힌 피해는 빼요
            p = by[pid]
            return pid, {"kind": "champ", "who": champ(p["championName"])}, p["championName"]
        t = h.get("type")
        if t == "MONSTER":
            nm = h.get("name") or ""
            n, g = next(((n, g) for k, n, g in MONSTER_KO if k in nm), ("정글 몬스터", "grub"))
            return "M" + n, {"kind": "monster", "who": {"k": None, "n": n, "glyph": g}}, None
        if t in UNIT_KO:
            return t, {"kind": t.lower(), "who": {"k": None, "n": UNIT_KO[t], "glyph": UNIT_GLYPH[t]}}, None
        return None
    rows = recap_rows(e.get("victimDamageReceived") or [], by, recv)
    dealt = e.get("victimDamageDealt")
    me = None
    if dealt is not None:
        mine = recap_rows(dealt, by, lambda h: ("me", {"kind": "me", "who": champ(ME["championName"])}, ME["championName"]))
        me = mine[0] if mine else {"kind": "me", "who": champ(ME["championName"]), "v": 0, "ph": 0, "mg": 0, "tr": 0, "parts": [], "used": []}
        # 누구에게 얼마나 넣었는지
        tg = {}
        for h in dealt:
            pid = h.get("participantId")
            if pid in by and by[pid]["teamId"] != my_team:
                tg[pid] = tg.get(pid, 0) + sum(_sum(h))
        me["to"] = [{"who": champ(by[p]["championName"]), "v": v} for p, v in sorted(tg.items(), key=lambda kv: -kv[1]) if v > 0]
    tot = [sum(r[k] for r in rows) for k in ("v", "ph", "mg", "tr")]
    return {"total": tot[0], "ph": tot[1], "mg": tot[2], "tr": tot[3], "rows": rows, "me": me,
            "given": (e.get("bounty") or 0) + (e.get("shutdownBounty") or 0)}


def combat_window(D, prev_death, ME, P, events, tracks, live, dur):
    """롤 전투 상태 규칙으로 교전 시작을 찾아요(11-20 사용자 기준).
    전투 상호작용: 적 챔피언·미니언·몬스터·포탑과 피해를 주고받거나 CC를 걸고받음. 마지막 상호작용 뒤 5초가 지나면 비전투.
    피해가 언제 들어갔는지는 데이터에 없어서 아래 흔적으로 추정해요.
      - 킬·어시·오브젝트·포탑 이벤트(정확한 시각)
      - 게임 중 기록: 5초 간격 기록에서 체력이 줄었거나 CS가 늘었으면 그 사이를 상호작용으로 봐요. 죽기 직전 1초 체력도.
      - 1초 위치: 적 챔피언이 1000 안, 살아 있는 적 포탑 사거리 안
    반환: (시작 초, 쓴 흔적 이름들) 또는 (None, [])"""
    lo = max(prev_death or 0, D - FIGHT_BACK)
    src = set()
    used = set()
    me, team = ME["participantId"], ME["teamId"]
    for ev in events:
        t = round(ev["timestamp"] / 1000)
        if not (lo <= t <= D):
            continue
        ty = ev["type"]
        if ty == "CHAMPION_KILL" and (ev.get("killerId") == me or me in (ev.get("assistingParticipantIds") or [])):
            src.add(t); used.add("이벤트")
        elif ty in ("ELITE_MONSTER_KILL", "BUILDING_KILL", "TURRET_PLATE_DESTROYED") and (
                ev.get("killerId") == me or me in (ev.get("assistingParticipantIds") or [])):
            src.add(t); used.add("이벤트")
    if live:
        sn = [x for x in live.get("snapshots") or [] if lo - 10 <= x["t"] <= D + 1]
        for a, b in zip(sn, sn[1:]):
            if a.get("dead") or b.get("dead") or b["t"] - a["t"] > 8:
                continue
            if b.get("hp", 100) < a.get("hp", 100) - 1 or b.get("cs", 0) > a.get("cs", 0):
                for s2 in range(int(a["t"]) + 1, int(b["t"]) + 1):
                    src.add(s2)
                used.add("게임 중 기록")
        dl = next((x for x in live.get("deaths") or [] if abs(x["t"] - D) <= 3), None)
        hf = (dl or {}).get("hpFlow") or []
        for a, b in zip(hf, hf[1:]):
            if b["hp"] < a["hp"] - 1:
                src.add(int(b["t"])); used.add("게임 중 기록")
    if tracks:
        mt = tracks.get(me, {})
        foes = [p["participantId"] for p in P if p["teamId"] != team]
        enemy_team = 300 - team
        gone = {}
        for ev in events:
            if ev["type"] == "BUILDING_KILL" and ev.get("buildingType") == "TOWER_BUILDING" and ev.get("teamId") == enemy_team:
                q = (ev["position"]["x"], ev["position"]["y"])
                near = min(TURRETS[enemy_team], key=lambda z: (z[0] - q[0]) ** 2 + (z[1] - q[1]) ** 2)
                gone[near] = round(ev["timestamp"] / 1000)
        for s2 in range(lo, D + 1):
            a = mt.get(s2)
            if not a:
                continue
            hit = any((lambda b: b and (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 <= FIGHT_R ** 2)(tracks.get(p, {}).get(s2)) for p in foes)
            if not hit:
                hit = any(s2 < gone.get(z, dur + 1) and (a[0] - z[0]) ** 2 + (a[1] - z[1]) ** 2 <= TURRET_R ** 2 for z in TURRETS[enemy_team])
            if hit:
                src.add(s2); used.add("위치")
    have_live = bool(live) and any(lo <= x["t"] < D - 2 for x in live.get("snapshots") or [])
    if not (tracks or have_live):
        return None, []  # 그 시간대 기록이 없으면 '계산 못 함'
    if not tracks and "게임 중 기록" not in used:
        used.add("게임 중 기록")
    src.add(D)  # 죽은 순간
    last, s2 = D, D
    while s2 >= lo:
        if s2 in src:
            last = s2
        elif last - s2 > COMBAT_KEEP:
            break
        s2 -= 1
    return last, sorted(used)


def death_extras(P, ME, events, dur, my_deaths_ev, tracks, live):
    """죽음마다: 사망 정보, 교전 시간(롤 기준 추정), 관여한 적이 다가온 시각(위치가 있을 때)"""
    by = {p["participantId"]: p for p in P}
    my_team = ME["teamId"]
    me_tr = (tracks or {}).get(ME["participantId"], {})

    def at(tr, s):
        for k in (0, -1, 1, -2, 2):
            if s + k in tr:
                return tr[s + k]
        return None

    def dist(a, b):
        return ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5 if a and b else None
    per, prev = {}, None
    for e in my_deaths_ev:
        D = round(e["timestamp"] / 1000)
        start, how = combat_window(D, prev, ME, P, events, tracks, live, dur)
        prev = D
        inv = [p for p in [e.get("killerId")] + e.get("assistingParticipantIds", []) if p and by[p]["teamId"] != my_team]
        joins = []
        if tracks:
            for p in inv:
                tr = tracks.get(p, {})
                first = next((s2 for s2 in range(max((start or D) - 5, D - 90), D + 1)
                              if (dist(at(me_tr, s2), at(tr, s2)) or 1e9) <= FIGHT_R), None)
                if first is not None:
                    joins.append({"t": first, "who": p - 1})
        per[mmss(e["timestamp"])] = {
            "sec": D,
            "fight": {"from": start, "to": D, "how": how} if start is not None else None,
            "joins": sorted(joins, key=lambda j: j["t"]),
            "recap": death_recap(e, by, ME),
        }
    return per


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
    # 리플레이 1초 위치(PC의 replay_worker.py가 올림)가 있으면 같이 써요. 없으면 1분 위치로 계산해요.
    res = AZ.analyze(raw, champ_id, live, AZ.load_track(os.path.join(ROOT, "raw", mid + ".pos.json.gz")))
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
    # --lab: 실험 리포트 데이터를 tools/report/lab-data/ 에 만들어요(저장소에 올리지 않음, artifact로만 봐요).
    lab = "--lab" in args
    args = [a for a in args if a != "--lab"]
    lab_dir = os.path.join(ROOT, "tools", "report", "lab-data")
    pub = public_ids()
    for d in (lab_dir if lab else OUT_DIR, PRIVATE_DIR):
        os.makedirs(d, exist_ok=True)
    champs = games_champ()
    if args and args[0] == "--all":
        mids = sorted(f[:-8] for f in os.listdir(os.path.join(ROOT, "raw")) if f.endswith(".json.gz") and not f.endswith(".pos.json.gz"))  # .pos는 리플레이 위치 파일
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
            data = build(mid, champ_id, lab)
        except Exception as e:  # 한 판이 실패해도 나머지는 만들어요
            print(mid, "실패:", type(e).__name__, e)
            continue
        out_dir = lab_dir if lab else (OUT_DIR if mid in pub else PRIVATE_DIR)
        if not lab and mid not in pub and os.path.exists(os.path.join(OUT_DIR, mid + ".json")):
            os.remove(os.path.join(OUT_DIR, mid + ".json"))  # 예전에 공개로 만든 파일은 사이트에서 내려요
        out = os.path.join(out_dir, mid + ".json")
        old = json.load(open(out, encoding="utf-8")) if os.path.exists(out) else None
        if old:  # 내용이 같으면 만든 시각만 바뀌지 않게 그대로 둬요(쓸데없는 커밋 막기)
            old_g, data_g = old.pop("generated", None), data.pop("generated")
            if old == data:
                print(mid, "바뀐 것 없음")
                continue
            data["generated"] = data_g
        json.dump(data, open(out, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
        print(mid, "→", os.path.relpath(out, ROOT), os.path.getsize(out) // 1024, "KB")
    if not lab:
        write_index()


if __name__ == "__main__":
    main(sys.argv[1:])
