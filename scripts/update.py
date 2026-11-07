# -*- coding: utf-8 -*-
"""
깃허브 Actions에서 실행되는 경기 기록 갱신 스크립트.

- 저장소 Secrets의 RIOT_API_KEY, Variables의 RIOT_ID 를 사용해요.
- 마지막 갱신 이후의 새 솔로랭크 게임만 받아와요.
- 판별 리포트(docs/games/*.md), 최신 판(docs/latest.md),
  전체 기록 페이지(docs/records.html), 기록 데이터(docs/data/*.json)를 만들어요.
"""

import gzip
import html
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(ROOT, "docs")
DATA = os.path.join(DOCS, "data")
GAMES_DIR = os.path.join(DOCS, "games")
GAMES_JSON = os.path.join(DATA, "games.json")
RANK_JSON = os.path.join(DATA, "rank_history.json")
# 전체 기록 페이지. 새 디자인이 나오기 전까지는 사이트에 공개하지 않아요(docs/_config.yml의 exclude).
# 사이트 첫 페이지(docs/index.html)는 "준비 중" 화면이고, 이 스크립트는 건드리지 않아요.
RECORDS_HTML = os.path.join(DOCS, "records.html")
LIVE_DIR = os.path.join(ROOT, "live")  # 내 컴퓨터의 게임 중 기록 프로그램이 올리는 파일
RAW_DIR = os.path.join(ROOT, "raw")    # 라이엇 원본 데이터 (경기 상세 + 타임라인, 압축) - 피드백할 때 직접 분석용
RAW_BACKFILL = 5                       # 한 번 갱신할 때 원본이 없는 예전 경기를 최대 몇 판까지 채울지

REGIONAL = "asia"   # 계정, 경기 기록
PLATFORM = "kr"     # 랭크 정보
SOLO_QUEUE = 420
QUEUE_KO = {420: "솔로랭크", 440: "자유랭크", 400: "일반", 430: "일반", 490: "빠른 대전", 450: "칼바람",
            830: "AI 대전", 840: "AI 대전", 850: "AI 대전", 870: "AI 대전", 880: "AI 대전", 890: "AI 대전"}
FIRST_RUN_LIMIT = 3  # 처음 실행할 때는 최근 3판만 받아요.
KST = timezone(timedelta(hours=9))

POS_KO = {"TOP": "탑", "JUNGLE": "정글", "MIDDLE": "미드", "BOTTOM": "원딜", "UTILITY": "서폿"}
TEAM_KO = {100: "블루팀", 200: "레드팀"}
SKILL_KEYS = {1: "Q", 2: "W", 3: "E", 4: "R"}
MONSTER_KO = {"DRAGON": "드래곤", "BARON_NASHOR": "바론", "RIFTHERALD": "전령",
              "HORDE": "공허 유충", "ATAKHAN": "아타칸"}
DRAGON_KO = {"FIRE_DRAGON": "화염", "WATER_DRAGON": "바다", "EARTH_DRAGON": "대지", "AIR_DRAGON": "바람",
             "HEXTECH_DRAGON": "마법공학", "CHEMTECH_DRAGON": "화학공학", "ELDER_DRAGON": "장로"}
SPELL_FALLBACK = {1: "정화", 3: "탈진", 4: "점멸", 6: "유체화", 7: "회복", 11: "강타",
                  12: "순간이동", 14: "점화", 21: "방어막", 32: "표식"}
TIERS = ["IRON", "BRONZE", "SILVER", "GOLD", "PLATINUM", "EMERALD", "DIAMOND", "MASTER", "GRANDMASTER", "CHALLENGER"]
TIER_KO = {"IRON": "아이언", "BRONZE": "브론즈", "SILVER": "실버", "GOLD": "골드", "PLATINUM": "플래티넘",
           "EMERALD": "에메랄드", "DIAMOND": "다이아몬드", "MASTER": "마스터", "GRANDMASTER": "그랜드마스터",
           "CHALLENGER": "챌린저"}
DIV_NUM = {"IV": 4, "III": 3, "II": 2, "I": 1}

SPELL_ID_FALLBACK = {"SummonerFlash": "점멸", "SummonerHeal": "회복", "SummonerBarrier": "방어막",
                     "SummonerExhaust": "탈진", "SummonerDot": "점화", "SummonerTeleport": "순간이동",
                     "SummonerHaste": "유체화", "SummonerBoost": "정화", "SummonerSmite": "강타"}
# 들고 죽었을 때 '살 수 있었던 스펠'로 보지 않는 것들 (공격용·이동용)
NOT_ESCAPE_SPELLS = {"SummonerDot", "SummonerSmite", "SummonerTeleport"}

NAMES = {"champ": {}, "item": {}, "spell": {}, "spell_id": {}}


class ApiError(Exception):
    def __init__(self, code, path):
        super().__init__(f"{code} {path}")
        self.code = code


# ---------------------------------------------------------------- 통신

def http_json(url, headers=None):
    req = urllib.request.Request(url, headers=headers or {"User-Agent": "personal-lol-review"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode("utf-8"))


def api_get(path, key, params=None, host=REGIONAL):
    url = f"https://{host}.api.riotgames.com{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    headers = {"X-Riot-Token": key, "User-Agent": "personal-lol-review"}
    for _ in range(6):
        try:
            return http_json(url, headers)
        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait = int(e.headers.get("Retry-After") or 10)
                print(f"  요청이 많아서 {wait}초 기다릴게요.")
                time.sleep(wait)
                continue
            if e.code >= 500:
                time.sleep(3)
                continue
            raise ApiError(e.code, path)
    raise ApiError(503, path)


def load_names():
    try:
        version = http_json("https://ddragon.leagueoflegends.com/api/versions.json")[0]
        base = f"https://ddragon.leagueoflegends.com/cdn/{version}/data/ko_KR"
        for cid, c in http_json(f"{base}/champion.json")["data"].items():
            NAMES["champ"][cid.lower()] = c["name"]
        for iid, it in http_json(f"{base}/item.json")["data"].items():
            NAMES["item"][int(iid)] = it["name"]
        for sid, s in http_json(f"{base}/summoner.json")["data"].items():
            NAMES["spell"][int(s["key"])] = s["name"]
            NAMES["spell_id"][sid] = s["name"]
    except Exception as e:
        print(f"  한글 이름을 못 받아와서 영어 이름으로 표시할게요. ({e})")


def champ_ko(eng):
    return NAMES["champ"].get(str(eng).lower(), eng)


def item_ko(iid):
    return NAMES["item"].get(iid, f"아이템#{iid}")


def spell_id_ko(key):
    base = str(key or "")
    for k in (base, base.replace("Upgrade", "")):
        if k in NAMES["spell_id"]:
            return NAMES["spell_id"][k]
        if k in SPELL_ID_FALLBACK:
            return SPELL_ID_FALLBACK[k]
    return base or "스펠"


def spell_ko(sid):
    return NAMES["spell"].get(sid) or SPELL_FALLBACK.get(sid, f"주문#{sid}")


# ---------------------------------------------------------------- 보조 함수

def mmss(ms):
    s = int(ms // 1000)
    return f"{s // 60}:{s % 60:02d}"


def zone(pos):
    """맵 좌표를 대략적인 구역 이름으로 바꿔요."""
    if not pos:
        return "위치 정보 없음"
    x, y = pos.get("x", 0), pos.get("y", 0)
    if x < 4000 and y < 4000:
        return "블루 본진 근처"
    if x > 10800 and y > 10800:
        return "레드 본진 근처"
    if abs(x - y) < 1600:
        return "미드 라인"
    if y < 3000 or x > 11900:
        return "바텀 라인"
    if x < 3000 or y > 11900:
        return "탑 라인"
    return "아래쪽(바텀 쪽) 정글·강" if y < x else "위쪽(탑 쪽) 정글·강"


def pos_of(p):
    return p.get("teamPosition") or p.get("individualPosition") or ""


def cs_of(p):
    return p.get("totalMinionsKilled", 0) + p.get("neutralMinionsKilled", 0)


def signed(n):
    return f"+{n}" if n > 0 else str(n)


def read_json(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return default


def write_json(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)


# ---------------------------------------------------------------- 랭크

def rank_score(entry):
    """티어·단계·LP를 한 줄의 숫자로 바꿔서 LP 변화를 계산해요."""
    t = TIERS.index(entry["tier"]) if entry.get("tier") in TIERS else 0
    div = DIV_NUM.get(entry.get("rank"), 1)
    return t * 400 + (4 - div) * 100 + entry.get("leaguePoints", 0)


def rank_text(entry):
    if not entry:
        return "-"
    tier = TIER_KO.get(entry["tier"], entry["tier"])
    if entry["tier"] in ("MASTER", "GRANDMASTER", "CHALLENGER"):
        return f"{tier} {entry['leaguePoints']}LP"
    return f"{tier} {DIV_NUM.get(entry['rank'], entry['rank'])} {entry['leaguePoints']}LP"


def get_solo_rank(key, puuid):
    entries = None
    try:
        entries = api_get(f"/lol/league/v4/entries/by-puuid/{puuid}", key, host=PLATFORM)
    except ApiError:
        try:
            s = api_get(f"/lol/summoner/v4/summoners/by-puuid/{puuid}", key, host=PLATFORM)
            entries = api_get(f"/lol/league/v4/entries/by-summoner/{s['id']}", key, host=PLATFORM)
        except (ApiError, KeyError) as e:
            print(f"  랭크 정보를 받지 못했어요. 경기 기록은 그대로 저장할게요. ({e})")
            return None
    solo = next((e for e in entries if e.get("queueType") == "RANKED_SOLO_5x5"), None)
    if not solo:
        return None
    return {k: solo.get(k) for k in ("tier", "rank", "leaguePoints", "wins", "losses")}


# ---------------------------------------------------------------- 원본 저장

def raw_path(mid):
    return os.path.join(RAW_DIR, f"{mid}.json.gz")


def save_raw(mid, match, timeline):
    os.makedirs(RAW_DIR, exist_ok=True)
    with gzip.open(raw_path(mid), "wt", encoding="utf-8") as f:
        json.dump({"match": match, "timeline": timeline}, f, ensure_ascii=False, separators=(",", ":"))


def backfill_raw(key, games):
    """원본이 없는 예전 경기의 원본을 받아서 저장해요."""
    missing = [g["matchId"] for g in games if not os.path.exists(raw_path(g["matchId"]))][:RAW_BACKFILL]
    for mid in missing:
        try:
            save_raw(mid, api_get(f"/lol/match/v5/matches/{mid}", key),
                     api_get(f"/lol/match/v5/matches/{mid}/timeline", key))
            print(f"  예전 경기 {mid}의 원본을 저장했어요.")
        except ApiError as e:
            print(f"  예전 경기 {mid}의 원본을 받지 못했어요. ({e})")


# ---------------------------------------------------------------- 게임 중 기록

def load_live_logs():
    logs = []
    if os.path.isdir(LIVE_DIR):
        for name in os.listdir(LIVE_DIR):
            if name.endswith(".json"):
                try:
                    l = read_json(os.path.join(LIVE_DIR, name), None)
                    if l:
                        l["_file"] = name
                        logs.append(l)
                except Exception:
                    pass
    return logs


def clean_live_logs(games, hours=3):
    """솔로랭크 경기와 짝지어지지 않은 게임 중 기록(일반 게임 등)은 3시간이 지나면 지워요.
    기록 프로그램은 게임 중에 랭크인지 일반인지 알 수 없어서 일단 올리기 때문이에요."""
    used = {g.get("liveFile") for g in games}
    now_ms = datetime.now(timezone.utc).timestamp() * 1000
    for l in load_live_logs():
        if l["_file"] not in used and now_ms - l.get("startEpochMs", now_ms) > hours * 3600 * 1000:
            os.remove(os.path.join(LIVE_DIR, l["_file"]))
            print(f"  솔로랭크가 아닌 게임의 게임 중 기록을 지웠어요: {l['_file']}")


def find_live_log(match, puuid, logs):
    """경기 시작 시간과 챔피언으로 게임 중 기록을 짝지어요."""
    info = match["info"]
    me = next(p for p in info["participants"] if p["puuid"] == puuid)
    start = info.get("gameStartTimestamp", info.get("gameCreation", 0))
    best, gap = None, 6 * 60 * 1000
    for l in logs:
        if str(l.get("champion", "")).lower() != str(me["championName"]).lower():
            continue
        d = abs(l.get("startEpochMs", 0) - start)
        if d < gap:
            best, gap = l, d
    return best


def live_death_lines(ld):
    """게임 중 기록의 데스 한 건을 리포트 문장으로 바꿔요."""
    lines = []
    if ld.get("gold") is not None:
        lines.append(f"  - 들고 있던 골드: **{ld['gold']:,}**")
    flow = ld.get("hpFlow") or []
    if flow:
        t0 = ld["t"]
        picks = []
        for sec in (10, 5, 2):
            cand = [f for f in flow if f["t"] <= t0 - sec + 0.6]
            if cand and (not picks or cand[-1] is not picks[-1][1]):
                picks.append((sec, cand[-1]))
        if picks:
            lines.append("  - 죽기 전 내 체력: " + " → ".join(f"{sec}초 전 {f['hp']}%" for sec, f in picks))
    texts = []
    for sp in ld.get("spells") or []:
        name = spell_id_ko(sp.get("key"))
        v = sp.get("verdict")
        if v == "held":
            texts.append(f"**{name} 들고 죽음**")
        elif v == "used_before":
            texts.append(f"{name}: 죽기 직전에 사용")
        elif v == "already_down":
            texts.append(f"{name}: 이미 쿨타임")
        elif v == "uncertain":
            texts.append(f"{name}: 판단 보류(화면은 봤지만 근거가 부족)")
        elif v in ("not_visible", "unknown"):
            texts.append(f"{name}: 확인 못 함(화면이 안 보임)")
    if texts:
        lines.append("  - 스펠: " + " / ".join(texts))
    return lines


def held_escape_spell(ld):
    return any(sp.get("verdict") == "held" and str(sp.get("key", "")).replace("Upgrade", "") not in NOT_ESCAPE_SPELLS
               for sp in ld.get("spells") or [])


# ---------------------------------------------------------------- 판별 리포트

def build_report(match, timeline, puuid, live=None):
    """경기 하나를 리포트(마크다운)와 요약(dict)으로 만들어요."""
    info = match["info"]
    parts = info["participants"]
    by_pid = {p["participantId"]: p for p in parts}
    me = next(p for p in parts if p["puuid"] == puuid)
    my_pid, my_team = me["participantId"], me["teamId"]
    enemy_team = 300 - my_team
    my_pos = pos_of(me)
    opp = next((p for p in parts if p["teamId"] == enemy_team and pos_of(p) == my_pos), None)

    def name(pid):
        if pid in by_pid:
            p = by_pid[pid]
            who = "나" if pid == my_pid else ("아군" if p["teamId"] == my_team else "적")
            return f"{champ_ko(p['championName'])}({who})"
        return "미니언·포탑 등"

    duration_s = info.get("gameDuration", 0)
    if duration_s > 100000:
        duration_s //= 1000
    minutes = max(duration_s / 60, 1)
    frames = timeline["info"]["frames"]
    events = [ev for f in frames for ev in f.get("events", [])]

    def pf(minute, pid):
        if minute < len(frames):
            return frames[minute]["participantFrames"].get(str(pid))
        return None

    def frame_cs(f):
        return f.get("minionsKilled", 0) + f.get("jungleMinionsKilled", 0)

    team_kills = sum(p["kills"] for p in parts if p["teamId"] == my_team) or 1
    team_dmg = sum(p["totalDamageDealtToChampions"] for p in parts if p["teamId"] == my_team) or 1
    start = datetime.fromtimestamp(info.get("gameStartTimestamp", info.get("gameCreation", 0)) / 1000, KST)

    gold15 = cs15 = None
    if opp and pf(15, my_pid) and pf(15, opp["participantId"]):
        a, b = pf(15, my_pid), pf(15, opp["participantId"])
        gold15 = a["totalGold"] - b["totalGold"]
        cs15 = frame_cs(a) - frame_cs(b)

    summary = {
        "matchId": match["metadata"]["matchId"],
        "start": start.isoformat(),
        "champion": champ_ko(me["championName"]),
        "championId": me["championName"],
        "position": POS_KO.get(my_pos, my_pos),
        "opponent": champ_ko(opp["championName"]) if opp else None,
        "win": bool(me["win"]),
        "kills": me["kills"], "deaths": me["deaths"], "assists": me["assists"],
        "cs": cs_of(me), "csPerMin": round(cs_of(me) / minutes, 1),
        "goldDiff15": gold15, "csDiff15": cs15,
        "visionScore": me["visionScore"],
        "durationSec": duration_s,
        "liveLog": bool(live),
        "liveFile": (live or {}).get("_file"),
        "queue": info.get("queueId"),
    }
    live_deaths = list((live or {}).get("deaths") or [])
    if live and live.get("spellCheck"):
        summary["spellHeldDeaths"] = sum(1 for d in live_deaths if held_escape_spell(d))

    L = []
    w = L.append
    result = "승리" if me["win"] else "패배"
    if me.get("gameEndedInSurrender"):
        result += " (항복)"

    w(f"# {start:%Y-%m-%d %H:%M} {summary['champion']} {summary['position']} {result}")
    w("")
    w("[← 전체 기록으로]({{BACK}})")
    w("")
    w(f"- 경기 ID: {summary['matchId']}")
    w(f"- 게임 시간: {duration_s // 60}분 {duration_s % 60}초 / 내 팀: {TEAM_KO.get(my_team)}")
    if opp:
        w(f"- 맞라인 상대: {summary['opponent']}")
    w("{{RANK}}")
    w("")

    w("## 1. 양 팀 기록")
    w("")
    w("| 팀 | 포지션 | 챔피언 | K/D/A | CS | 골드 | 챔피언 피해 | 시야 점수 |")
    w("|---|---|---|---|---|---|---|---|")
    order = ["TOP", "JUNGLE", "MIDDLE", "BOTTOM", "UTILITY"]
    for team in (my_team, enemy_team):
        team_parts = sorted([p for p in parts if p["teamId"] == team],
                            key=lambda p: order.index(pos_of(p)) if pos_of(p) in order else 9)
        for p in team_parts:
            mark = " ← 나" if p["participantId"] == my_pid else ""
            w(f"| {'우리' if team == my_team else '상대'} | {POS_KO.get(pos_of(p), pos_of(p))} | "
              f"{champ_ko(p['championName'])}{mark} | {p['kills']}/{p['deaths']}/{p['assists']} | "
              f"{cs_of(p)} | {p['goldEarned']:,} | {p['totalDamageDealtToChampions']:,} | {p['visionScore']} |")
    w("")

    w("## 2. 내 기본 기록")
    w("")
    kp = (me["kills"] + me["assists"]) / team_kills * 100
    w(f"- K/D/A: {me['kills']}/{me['deaths']}/{me['assists']} (킬 관여율 {kp:.0f}%)")
    w(f"- CS: {cs_of(me)} (분당 {cs_of(me) / minutes:.1f}) / 골드: {me['goldEarned']:,} (분당 {me['goldEarned'] / minutes:.0f})")
    w(f"- 챔피언 피해: {me['totalDamageDealtToChampions']:,} (팀 내 비중 {me['totalDamageDealtToChampions'] / team_dmg * 100:.0f}%)"
      f" / 받은 피해: {me['totalDamageTaken']:,}")
    w(f"- 포탑 피해: {me.get('damageDealtToBuildings', 0):,}")
    w(f"- 시야: 점수 {me['visionScore']} / 와드 설치 {me.get('wardsPlaced', 0)} / 와드 제거 {me.get('wardsKilled', 0)}"
      f" / 제어 와드 구매 {me.get('visionWardsBoughtInGame', 0)}")
    w(f"- 소환사 주문: {spell_ko(me.get('summoner1Id'))}, {spell_ko(me.get('summoner2Id'))}")
    items = [item_ko(me.get(f"item{i}")) for i in range(7) if me.get(f"item{i}")]
    w(f"- 최종 아이템: {', '.join(items) if items else '없음'}")
    ch = me.get("challenges") or {}
    extra = [("laneMinionsFirst10Minutes", "10분까지 라인 미니언 처치"),
             ("maxCsAdvantageOnLaneOpponent", "맞라인 상대보다 최대로 앞선 CS"),
             ("soloKills", "솔로킬"), ("turretPlatesTaken", "포탑 방패 획득"),
             ("skillshotsHit", "논타깃 스킬 적중"), ("skillshotsDodged", "논타깃 스킬 회피"),
             ("controlWardsPlaced", "제어 와드 설치")]
    got = [f"{label} {round(ch[k], 1) if isinstance(ch[k], float) else ch[k]}" for k, label in extra if k in ch]
    if got:
        w(f"- 그 밖의 기록: {' / '.join(got)}")
    w("")

    w("## 3. 시간대별 차이 (+면 내가 앞섬)")
    w("")
    checkpoints = [m for m in (5, 10, 15, 20, 25, 30) if m < len(frames)]
    if opp:
        w(f"맞라인 상대({summary['opponent']})와 비교")
        w("")
        w("| 시간 | 내 골드 | 상대 골드 | 골드 차이 | 내 CS | 상대 CS | CS 차이 | 레벨 (나:상대) |")
        w("|---|---|---|---|---|---|---|---|")
        for m in checkpoints:
            a, b = pf(m, my_pid), pf(m, opp["participantId"])
            if not a or not b:
                continue
            w(f"| {m}분 | {a['totalGold']:,} | {b['totalGold']:,} | {signed(a['totalGold'] - b['totalGold'])} | "
              f"{frame_cs(a)} | {frame_cs(b)} | {signed(frame_cs(a) - frame_cs(b))} | {a['level']}:{b['level']} |")
        w("")

    if my_pos in ("BOTTOM", "UTILITY"):
        mine_bot = [p["participantId"] for p in parts if p["teamId"] == my_team and pos_of(p) in ("BOTTOM", "UTILITY")]
        their_bot = [p["participantId"] for p in parts if p["teamId"] == enemy_team and pos_of(p) in ("BOTTOM", "UTILITY")]
        if len(mine_bot) == 2 and len(their_bot) == 2:
            w("바텀 2대2 골드 합 비교")
            w("")
            w("| 시간 | 우리 바텀 | 상대 바텀 | 차이 |")
            w("|---|---|---|---|")
            for m in checkpoints:
                fa = [pf(m, pid) for pid in mine_bot]
                fb = [pf(m, pid) for pid in their_bot]
                if None in fa or None in fb:
                    continue
                ga, gb = sum(f["totalGold"] for f in fa), sum(f["totalGold"] for f in fb)
                w(f"| {m}분 | {ga:,} | {gb:,} | {signed(ga - gb)} |")
            w("")

    w("팀 전체 골드 비교")
    w("")
    w("| 시간 | 우리 팀 | 상대 팀 | 차이 |")
    w("|---|---|---|---|")
    last = len(frames) - 1
    for m in checkpoints + ([last] if last not in checkpoints and last > 0 else []):
        f = frames[m]["participantFrames"]
        ga = sum(f[str(p["participantId"])]["totalGold"] for p in parts if p["teamId"] == my_team and str(p["participantId"]) in f)
        gb = sum(f[str(p["participantId"])]["totalGold"] for p in parts if p["teamId"] == enemy_team and str(p["participantId"]) in f)
        label = f"{m}분" if m in checkpoints else f"{m}분(종료 직전)"
        w(f"| {label} | {ga:,} | {gb:,} | {signed(ga - gb)} |")
    w("")

    def level_time(pid, lv):
        for ev in events:
            if ev.get("type") == "LEVEL_UP" and ev.get("participantId") == pid and ev.get("level") == lv:
                return mmss(ev["timestamp"])
        return "-"

    if opp:
        w(f"- 6레벨 달성: 나 {level_time(my_pid, 6)} / 상대 {level_time(opp['participantId'], 6)}")
        w(f"- 11레벨 달성: 나 {level_time(my_pid, 11)} / 상대 {level_time(opp['participantId'], 11)}")
        w("")

    w("## 4. 내 킬·데스·어시스트 장면")
    w("")
    w("위치는 맵 좌표로 계산한 대략적인 구역이에요.")
    if live:
        w("골드·체력·스펠은 게임 중 기록 프로그램이 남긴 값이에요.")
    elif live is None:
        w("게임 중 기록이 없어서 골드는 1분 단위 기록으로 계산한 대략적인 값이에요.")
    w("")
    for ev in events:
        if ev.get("type") != "CHAMPION_KILL":
            continue
        killer, victim = ev.get("killerId", 0), ev.get("victimId")
        assists = ev.get("assistingParticipantIds", []) or []
        t, where = mmss(ev["timestamp"]), zone(ev.get("position"))
        if victim == my_pid:
            helpers = ", ".join(name(a) for a in assists) or "없음(혼자 잡음)"
            w(f"- **{t} 데스** / {where} / 처치: {name(killer)} / 도운 적: {helpers}")
            dmg = {}
            for d in ev.get("victimDamageReceived", []) or []:
                total = d.get("physicalDamage", 0) + d.get("magicDamage", 0) + d.get("trueDamage", 0)
                src = d.get("participantId")
                label = name(src) if src in by_pid else (d.get("name") or "기타")
                dmg[label] = dmg.get(label, 0) + total
            if dmg:
                top = sorted(dmg.items(), key=lambda kv: -kv[1])[:4]
                w("  - 죽기 직전 받은 피해: " + ", ".join(f"{k} {v:,}" for k, v in top))
            if ev.get("shutdownBounty"):
                w(f"  - 내 현상금 {ev['shutdownBounty']}골드가 상대에게 넘어감")
            t_sec = ev["timestamp"] / 1000
            ld = min(live_deaths, key=lambda d: abs(d["t"] - t_sec), default=None)
            if ld is not None and abs(ld["t"] - t_sec) <= 6:
                live_deaths.remove(ld)
                for line in live_death_lines(ld):
                    w(line)
            else:
                f = pf(int(t_sec // 60), my_pid)
                if f and f.get("currentGold") is not None:
                    w(f"  - 들고 있던 골드: 약 {f['currentGold']:,} (1분 단위 기록이라 대략적인 값)")
        elif killer == my_pid:
            w(f"- {t} 킬 / {where} / 잡은 적: {name(victim)}"
              + (f" / 함께한 아군: {', '.join(name(a) for a in assists)}" if assists else " / 솔로킬"))
        elif my_pid in assists:
            w(f"- {t} 어시스트 / {where} / 잡은 적: {name(victim)} / 처치: {name(killer)}")
    w("")

    w("## 5. 오브젝트·포탑 흐름")
    w("")
    plates = {my_team: 0, enemy_team: 0}
    for ev in events:
        typ = ev.get("type")
        t = mmss(ev.get("timestamp", 0))
        if typ == "ELITE_MONSTER_KILL":
            team = ev.get("killerTeamId") or by_pid.get(ev.get("killerId"), {}).get("teamId")
            mon = MONSTER_KO.get(ev.get("monsterType"), ev.get("monsterType"))
            if ev.get("monsterSubType"):
                mon = f"{DRAGON_KO.get(ev['monsterSubType'], ev['monsterSubType'])} {mon}"
            w(f"- {t} {'우리 팀' if team == my_team else '상대 팀'} {mon} 처치")
        elif typ == "BUILDING_KILL":
            owner = ev.get("teamId")
            kind = "억제기" if ev.get("buildingType") == "INHIBITOR_BUILDING" else "포탑"
            lane = {"TOP_LANE": "탑", "MID_LANE": "미드", "BOT_LANE": "바텀"}.get(ev.get("laneType"), "")
            tier = {"OUTER_TURRET": "1차", "INNER_TURRET": "2차", "BASE_TURRET": "3차",
                    "NEXUS_TURRET": "쌍둥이"}.get(ev.get("towerType"), "")
            who = "우리 팀이 상대" if owner == enemy_team else "상대 팀이 우리"
            w(" ".join(s for s in [f"- {t}", who, lane, tier, kind, "파괴"] if s))
        elif typ == "TURRET_PLATE_DESTROYED":
            owner = ev.get("teamId")
            if owner in plates:
                plates[300 - owner] += 1
    w(f"- 포탑 방패 획득: 우리 팀 {plates[my_team]}개 / 상대 팀 {plates[enemy_team]}개")
    w("")

    w("## 6. 내 아이템 구매 순서와 스킬 순서")
    w("")
    buys = []
    for ev in events:
        if ev.get("participantId") != my_pid:
            continue
        if ev.get("type") == "ITEM_PURCHASED":
            buys.append((ev["timestamp"], ev["itemId"]))
        elif ev.get("type") == "ITEM_UNDO":
            for i in range(len(buys) - 1, -1, -1):
                if buys[i][1] == ev.get("beforeId"):
                    buys.pop(i)
                    break
    w("- 구매: " + (" → ".join(f"{mmss(t)} {item_ko(i)}" for t, i in buys) if buys else "기록 없음"))
    skills = [SKILL_KEYS.get(ev.get("skillSlot"), "?") for ev in events
              if ev.get("type") == "SKILL_LEVEL_UP" and ev.get("participantId") == my_pid]
    w("- 스킬: " + (" ".join(skills) if skills else "기록 없음"))
    w("")

    w("## 7. 내 와드 설치 흐름 (5분 단위)")
    w("")
    buckets = {}
    for ev in events:
        if ev.get("type") == "WARD_PLACED" and ev.get("creatorId") == my_pid and ev.get("wardType") != "UNDEFINED":
            b = int(ev["timestamp"] // 300000) * 5
            buckets[b] = buckets.get(b, 0) + 1
    w(" / ".join(f"{b}~{b + 5}분 {buckets[b]}개" for b in sorted(buckets)) if buckets else "기록 없음")
    w("")

    return summary, "\n".join(L)


def page(md, title, back, rank_line):
    safe_title = title.replace('"', "'")
    body = md.replace("{{BACK}}", back).replace("{{RANK}}", rank_line)
    return f'---\nlayout: default\ntitle: "{safe_title}"\n---\n\n{body}\n'


# ---------------------------------------------------------------- 전체 기록 페이지

def build_index(games, rank_hist, riot_id):
    def esc(s):
        return html.escape(str(s))

    recent = [g for g in games if g.get("queue", SOLO_QUEUE) == SOLO_QUEUE][:10]
    stats = ""
    if recent:
        wins = sum(g["win"] for g in recent)
        avg_cs = sum(g["csPerMin"] for g in recent) / len(recent)
        avg_d = sum(g["deaths"] for g in recent) / len(recent)
        g15 = [g["goldDiff15"] for g in recent if g.get("goldDiff15") is not None]
        avg_g15 = signed(round(sum(g15) / len(g15))) if g15 else "-"
        stats = (
            f'<div class="stat"><b>{wins}승 {len(recent) - wins}패</b><span>최근 {len(recent)}판</span></div>'
            f'<div class="stat"><b>{avg_cs:.1f}</b><span>평균 분당 CS</span></div>'
            f'<div class="stat"><b>{avg_d:.1f}</b><span>평균 데스</span></div>'
            f'<div class="stat"><b>{avg_g15}</b><span>15분 골드 차이 평균</span></div>'
        )

    current = rank_text(rank_hist[-1]["entry"]) if rank_hist and rank_hist[-1].get("entry") else "랭크 정보 없음"

    rows = []
    for g in games:
        d = datetime.fromisoformat(g["start"])
        lp = g.get("lpChange")
        lp_txt = signed(lp) + "LP" if lp is not None else ""
        g15 = signed(g["goldDiff15"]) if g.get("goldDiff15") is not None else "-"
        rows.append(
            f'<tr class="{"win" if g["win"] else "loss"}">'
            f'<td>{d:%m.%d %H:%M}'
            f'{"<small>" + esc(QUEUE_KO.get(g.get("queue"), "기타")) + "</small>" if g.get("queue", SOLO_QUEUE) != SOLO_QUEUE else ""}</td>'
            f'<td>{"승" if g["win"] else "패"}</td>'
            f'<td><a href="games/{esc(g["matchId"])}.html">{esc(g["champion"])}</a>'
            f'<small>{esc(g["position"])}{" vs " + esc(g["opponent"]) if g.get("opponent") else ""}</small></td>'
            f'<td>{g["kills"]}/{g["deaths"]}/{g["assists"]}</td>'
            f'<td>{g["csPerMin"]}</td>'
            f'<td>{g15}</td>'
            f'<td>{esc(lp_txt)}</td></tr>'
        )

    updated = datetime.now(KST)
    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>랭크 셀프 피드백 아카이브</title>
<style>
  body {{ font-family: -apple-system, "Apple SD Gothic Neo", "Malgun Gothic", sans-serif; margin: 0; background: #f6f7f9; color: #1d1f23; }}
  main {{ max-width: 860px; margin: 0 auto; padding: 32px 20px 60px; }}
  h1 {{ font-size: 22px; margin: 0 0 4px; }}
  .sub {{ color: #6b7280; font-size: 14px; margin-bottom: 24px; }}
  .rank {{ font-size: 18px; font-weight: 700; margin-bottom: 20px; }}
  .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 12px; margin-bottom: 28px; }}
  .stat {{ background: #fff; border-radius: 12px; padding: 16px; }}
  .stat b {{ display: block; font-size: 22px; }}
  .stat span {{ color: #6b7280; font-size: 13px; }}
  table {{ width: 100%; border-collapse: collapse; background: #fff; border-radius: 12px; overflow: hidden; font-size: 14px; }}
  th, td {{ padding: 12px 10px; text-align: left; border-bottom: 1px solid #eef0f3; }}
  th {{ color: #6b7280; font-weight: 600; font-size: 13px; }}
  td small {{ display: block; color: #6b7280; font-size: 12px; }}
  tr.win td:nth-child(2) {{ color: #2563eb; font-weight: 700; }}
  tr.loss td:nth-child(2) {{ color: #dc2626; font-weight: 700; }}
  a {{ color: inherit; font-weight: 600; }}
</style>
</head>
<body>
<main>
  <h1>랭크 셀프 피드백 아카이브</h1>
  <div class="sub">{esc(riot_id)} · 솔로랭크 · 마지막 갱신 {updated:%Y-%m-%d %H:%M}</div>
  <div class="rank">현재 {esc(current)}</div>
  <div class="stats">{stats}</div>
  <table>
    <thead><tr><th>날짜</th><th>결과</th><th>챔피언</th><th>K/D/A</th><th>분당 CS</th><th>15분 골드 차이</th><th>LP</th></tr></thead>
    <tbody>
    {''.join(rows) if rows else '<tr><td colspan="7">아직 기록이 없어요.</td></tr>'}
    </tbody>
  </table>
</main>
</body>
</html>
"""


# ---------------------------------------------------------------- 실행

def main():
    key = os.environ.get("RIOT_API_KEY", "").strip()
    riot_id = os.environ.get("RIOT_ID", "").strip()
    wait_for_new = os.environ.get("WAIT_FOR_NEW", "true").lower() != "false"
    if not key:
        sys.exit("RIOT_API_KEY가 비어 있어요. 저장소 Settings > Secrets에 키를 넣어 주세요.")
    if "#" not in riot_id:
        sys.exit("RIOT_ID가 비어 있거나 #태그가 없어요. 저장소 Settings > Variables에 '이름#태그'로 넣어 주세요.")
    name, tag = riot_id.rsplit("#", 1)

    try:
        acct = api_get(f"/riot/account/v1/accounts/by-riot-id/{urllib.parse.quote(name)}/{urllib.parse.quote(tag)}", key)
    except ApiError as e:
        if e.code in (401, 403):
            sys.exit("API 키가 틀렸거나 만료됐어요. Secrets의 RIOT_API_KEY를 확인해 주세요.")
        if e.code == 404:
            sys.exit(f"'{riot_id}' 계정을 찾지 못했어요. Variables의 RIOT_ID 철자를 확인해 주세요.")
        raise
    puuid = acct["puuid"]

    os.makedirs(LIVE_DIR, exist_ok=True)
    if not os.path.exists(os.path.join(LIVE_DIR, "README.md")):
        with open(os.path.join(LIVE_DIR, "README.md"), "w", encoding="utf-8") as f:
            f.write("내 컴퓨터의 게임 중 기록 프로그램이 올리는 파일이에요. 솔로랭크 경기와 짝지어지지 않은 기록은 3시간 뒤에 지워져요.\n")
    os.makedirs(RAW_DIR, exist_ok=True)
    readme = os.path.join(RAW_DIR, "README.md")
    if not os.path.exists(readme):
        with open(readme, "w", encoding="utf-8") as f:
            f.write("라이엇 API 원본 데이터(경기 상세 + 타임라인)를 경기마다 압축해서 저장하는 폴더예요. 피드백할 때 직접 분석하는 데 써요.\n")

    games = read_json(GAMES_JSON, [])
    known = {g["matchId"] for g in games}
    skipped = set(read_json(os.path.join(DATA, "skipped.json"), []))

    new_ids = []
    tries = 6 if wait_for_new else 1
    for attempt in range(tries):
        ids = api_get(f"/lol/match/v5/matches/by-puuid/{puuid}/ids", key,
                      {"queue": SOLO_QUEUE, "start": 0, "count": 20})
        new_ids = [i for i in ids if i not in known and i not in skipped]
        if new_ids:
            break
        if attempt < tries - 1:
            print("아직 새 게임 기록이 안 올라왔어요. 1분 뒤에 다시 확인할게요.")
            time.sleep(60)
    if not new_ids:
        print("새 솔로랭크 게임이 없어요.")
        backfill_raw(key, games)
        clean_live_logs(games)
        if not os.path.exists(RECORDS_HTML):
            with open(RECORDS_HTML, "w", encoding="utf-8") as f:
                f.write(build_index(games, read_json(RANK_JSON, []), riot_id))
        return
    if not games:
        # 처음 실행할 때는 최근 몇 판만 기록하고, 그보다 예전 판은 앞으로도 받지 않아요.
        skipped.update(new_ids[FIRST_RUN_LIMIT:])
        new_ids = new_ids[:FIRST_RUN_LIMIT]

    load_names()
    os.makedirs(GAMES_DIR, exist_ok=True)

    live_logs = load_live_logs()
    added = []  # (경기 ID, 요약, 리포트), 오래된 판부터
    for mid in reversed(new_ids):
        print(f"{mid} 경기 데이터를 받는 중...")
        try:
            match = api_get(f"/lol/match/v5/matches/{mid}", key)
            timeline = api_get(f"/lol/match/v5/matches/{mid}/timeline", key)
        except ApiError as e:
            print(f"  이 경기는 받지 못해서 건너뛸게요. ({e})")
            continue
        if match["info"].get("gameDuration", 0) < 300:
            print("  다시하기(5분 미만) 게임이라 기록하지 않을게요.")
            skipped.add(mid)
            continue
        save_raw(mid, match, timeline)
        live = find_live_log(match, puuid, live_logs)
        if live:
            print("  게임 중 기록을 찾아서 같이 정리할게요.")
        summary, md = build_report(match, timeline, puuid, live)
        added.append((mid, summary, md))

    # 랭크는 지금 시점에 한 번만 받아서, 이번에 추가된 가장 최근 판에 붙여요.
    # LP 변화는 이번에 1판만 추가됐을 때만 계산해요. (여러 판이면 판별로 나눌 수 없어서)
    rank_hist = read_json(RANK_JSON, [])
    entry = get_solo_rank(key, puuid) if added else None
    lp_change = None
    if entry:
        prev = next((r["entry"] for r in reversed(rank_hist) if r.get("entry")), None)
        if prev and len(added) == 1 and added[-1][1].get("queue", SOLO_QUEUE) == SOLO_QUEUE:
            lp_change = rank_score(entry) - rank_score(prev)
        rank_hist.append({"time": datetime.now(KST).isoformat(), "entry": entry, "matchId": added[-1][0]})

    for i, (mid, summary, md) in enumerate(added):
        is_newest = i == len(added) - 1
        rank_line = ""
        if is_newest and entry and summary.get("queue", SOLO_QUEUE) == SOLO_QUEUE:
            summary["rankAfter"] = rank_text(entry)
            summary["lpChange"] = lp_change
            rank_line = f"- 이 판 이후 랭크: {rank_text(entry)}" + (f" ({signed(lp_change)}LP)" if lp_change is not None else "")
        title = f"{summary['start'][:10]} {summary['champion']} {'승리' if summary['win'] else '패배'}"
        with open(os.path.join(GAMES_DIR, f"{mid}.md"), "w", encoding="utf-8") as f:
            f.write(page(md, title, "../", rank_line))
        if is_newest:
            with open(os.path.join(DOCS, "latest.md"), "w", encoding="utf-8") as f:
                f.write(page(md, "최근 판 리포트", "./", rank_line))

    games = sorted([s for _, s, _ in added] + games, key=lambda g: g["start"], reverse=True)
    backfill_raw(key, games)
    clean_live_logs(games)
    write_json(GAMES_JSON, games)
    write_json(RANK_JSON, rank_hist)
    write_json(os.path.join(DATA, "skipped.json"), sorted(skipped))
    with open(RECORDS_HTML, "w", encoding="utf-8") as f:
        f.write(build_index(games, rank_hist, riot_id))
    print(f"완료! 새 게임 {len(added)}판을 추가했어요.")


if __name__ == "__main__":
    main()
