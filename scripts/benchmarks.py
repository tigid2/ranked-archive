"""기준 데이터 모으기 (계획 2단계)

KR 솔로 랭크 에메랄드~다이아 경기에서 원딜 챔피언(기본: 징크스, 애쉬, 미스포츠, 자야)이
원딜로 나온 판을 모아서, 리포트에서 비교할 숫자를 챔피언별로 정리해요.

- 원본 경기는 저장하지 않아요. 한 판에서 필요한 숫자만 뽑은 줄을 benchmarks/rows/<챔피언>.jsonl 에 쌓고,
  그걸로 benchmarks/<챔피언>.json 요약을 만들어요. 여러 번 돌리면 판 수가 늘어나요.
- 요청 제한(개인 키: 1초 20번, 2분 100번)을 넘지 않게 스스로 속도를 맞춰요.
- 실행 방법
    python scripts/benchmarks.py collect            # 수집 + 요약 (RIOT_API_KEY 필요)
    python scripts/benchmarks.py summarize          # 쌓인 줄로 요약만 다시 만들기
    python scripts/benchmarks.py test raw/*.json.gz # 저장소의 원본 경기로 뽑기 시험 (키 필요 없음)
- 환경 변수(모두 선택): BM_TARGET(챔피언당 판 수, 150), BM_MAX_MINUTES(120), BM_DAYS(14),
  BM_CHAMPS(Jinx,Ashe,MissFortune,Xayah), BM_TIERS(EMERALD,DIAMOND), BM_PATCH(auto = 최신 패치만, any = 전부)
"""
import collections
import glob
import gzip
import hashlib
import json
import os
import random
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BM_DIR = os.path.join(ROOT, "benchmarks")
ROWS_DIR = os.path.join(BM_DIR, "rows")
KST = timezone(timedelta(hours=9))

CHAMPS = [c.strip() for c in os.environ.get("BM_CHAMPS", "Jinx,Ashe,MissFortune,Xayah").split(",") if c.strip()]
TIERS = [t.strip().upper() for t in os.environ.get("BM_TIERS", "EMERALD,DIAMOND").split(",") if t.strip()]
TARGET = int(os.environ.get("BM_TARGET") or 150)
MAX_MINUTES = float(os.environ.get("BM_MAX_MINUTES") or 120)
DAYS = int(os.environ.get("BM_DAYS") or 14)
PATCH = (os.environ.get("BM_PATCH") or "auto").strip()
PER_PLAYER_CAP = 3        # 한 사람이 같은 챔피언으로 너무 많이 들어가지 않게 (장인 한 명에 숫자가 쏠리는 것 막기)
DIVISIONS = ["I", "II", "III", "IV"]
LEAGUE_PAGES = (1, 2)     # 구간마다 참가자 목록 몇 쪽을 볼지 (한 쪽에 약 200명)

# 요약에서 숫자를 보여 줄 최소 판 수. analyze.py도 이 값을 그대로 써요.
MIN_N = {"stat": 30, "matchup": 10, "build": 10}
MIN_PATCH_ROWS = 60       # 최신 패치 판 수가 이보다 적으면 바로 전 패치까지 합쳐요(최대 3개 패치)


# ---------------------------------------------------------------- 통신

class ApiError(Exception):
    def __init__(self, code, path):
        super().__init__(f"{code} {path}")
        self.code = code


class KeyExpired(Exception):
    """수집 도중 키가 만료되면 거기까지 모은 걸로 요약을 만들고 끝내요."""


class Limiter:
    """1초 19번, 2분 95번을 넘지 않게 기다려요(개인 키 제한보다 조금 낮게)."""
    def __init__(self, rules=((19, 1.0), (95, 120.0))):
        self.rules = rules
        self.calls = collections.deque()
        self.count = 0

    def wait(self):
        while True:
            now = time.time()
            while self.calls and now - self.calls[0] > max(w for _, w in self.rules):
                self.calls.popleft()
            sleep = 0
            for n, w in self.rules:
                recent = [t for t in self.calls if now - t < w]
                if len(recent) >= n:
                    sleep = max(sleep, w - (now - recent[0]) + 0.05)
            if sleep <= 0:
                break
            time.sleep(sleep)
        self.calls.append(time.time())
        self.count += 1


LIMIT = Limiter()


def http_json(url, headers=None):
    req = urllib.request.Request(url, headers=headers or {"User-Agent": "personal-lol-review"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def api_get(path, key, params=None, host="asia"):
    url = f"https://{host}.api.riotgames.com{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    headers = {"X-Riot-Token": key, "User-Agent": "personal-lol-review"}
    for _ in range(6):
        LIMIT.wait()
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
            if e.code in (401, 403):
                raise KeyExpired(path)
            raise ApiError(e.code, path)
        except (urllib.error.URLError, TimeoutError):
            time.sleep(3)
    raise ApiError(503, path)


# ---------------------------------------------------------------- 게임 데이터(아이템·챔피언 이름)

DD = {"item": {}, "champ": {}, "rune": {}, "style": {}, "version": None}


def load_dd():
    """최신 Data Dragon을 받아요. 안 되면 저장소 data/ 파일을 써요."""
    try:
        ver = http_json("https://ddragon.leagueoflegends.com/api/versions.json")[0]
        base = f"https://ddragon.leagueoflegends.com/cdn/{ver}/data/ko_KR"
        item, champ, runes = (http_json(f"{base}/{n}.json") for n in ("item", "champion", "runesReforged"))
        DD["version"] = ver
    except Exception as e:  # noqa: BLE001
        print(f"  Data Dragon을 못 받아서 저장소 파일을 써요: {e}")
        d = os.path.join(ROOT, "data")
        item = json.load(open(os.path.join(d, "dd_item.json"), encoding="utf-8"))
        champ = json.load(open(os.path.join(d, "dd_champion.json"), encoding="utf-8"))
        runes = json.load(open(os.path.join(d, "dd_runesReforged.json"), encoding="utf-8"))
        DD["version"] = item.get("version")
    DD["item"] = {int(k): v for k, v in item["data"].items()}
    DD["champ"] = {k: v["name"] for k, v in champ["data"].items()}
    for st in runes:
        DD["style"][st["id"]] = st["name"]
        for slot in st["slots"]:
            for r in slot["runes"]:
                DD["rune"][r["id"]] = r["name"]


def is_core(iid):
    """완성 아이템(신발 제외). analyze.py의 아이템 완성 기준과 같아요."""
    it = DD["item"].get(iid)
    if not it:
        return False
    tags = it.get("tags", [])
    return (not it.get("into")) and it.get("gold", {}).get("total", 0) >= 2200 and "Boots" not in tags \
        and "Consumable" not in tags


def patch_of(version):
    return ".".join(str(version).split(".")[:2])


# ---------------------------------------------------------------- 한 판에서 숫자 뽑기

def bot(pos):  # analyze.py의 BOT과 같은 기준 (1분 위치라 대략적)
    return pos["x"] > 9000 and pos["y"] < 6000


def extract_row(match, timeline, pid, tier=None):
    info = match["info"]
    frames = timeline["info"]["frames"]
    parts = {p["participantId"]: p for p in info["participants"]}
    me = parts[pid]
    team = me["teamId"]
    opp = next((p for p in info["participants"] if p["teamId"] != team and p["teamPosition"] == "BOTTOM"), None)
    sup = next((p for p in info["participants"] if p["teamId"] == team and p["teamPosition"] == "UTILITY"), None)

    def pf(m, p):
        return frames[min(m, len(frames) - 1)]["participantFrames"][str(p)]

    def cs(m, p):
        x = pf(m, p)
        return x["minionsKilled"] + x["jungleMinionsKilled"]

    def at(m):
        x = pf(m, pid)
        return {"cs": cs(m, pid), "gold": x["totalGold"], "xp": x["xp"]}

    t15 = at(15)
    t15["dmg"] = pf(15, pid)["damageStats"]["totalDamageDoneToChampions"]
    row = {"mid": match["metadata"]["matchId"], "patch": patch_of(info["gameVersion"]),
           "tier": tier, "win": bool(me["win"]), "dur": info["gameDuration"],
           "ph": hashlib.sha1(me["puuid"].encode()).hexdigest()[:10],
           "t10": at(10), "t15": t15,
           "dpm": round(me.get("challenges", {}).get("damagePerMinute")
                        or me["totalDamageDealtToChampions"] / (info["gameDuration"] / 60), 1),
           "vspm": round(me.get("challenges", {}).get("visionScorePerMinute")
                         or me["visionScore"] / (info["gameDuration"] / 60), 3)}
    if opp:
        row["opp"] = opp["championName"]
        row["oppGold15"] = pf(15, opp["participantId"])["totalGold"]
        row["oppCs15"] = cs(15, opp["participantId"])

    # 완성 아이템 순서 (구매 취소는 빼요)
    bought = []
    for f in frames:
        for e in f["events"]:
            if e.get("participantId") != pid:
                continue
            if e["type"] == "ITEM_PURCHASED":
                bought.append([e["itemId"], e["timestamp"]])
            elif e["type"] == "ITEM_UNDO" and e.get("beforeId"):
                for i in range(len(bought) - 1, -1, -1):
                    if bought[i][0] == e["beforeId"]:
                        bought.pop(i)
                        break
    cores, seen = [], set()
    for iid, ts in bought:
        if is_core(iid) and iid not in seen:
            seen.add(iid)
            cores.append([iid, ts // 1000])
    row["items"] = cores[:3]

    perks = me["perks"]["styles"]
    row["keystone"] = perks[0]["selections"][0]["perk"]
    row["styles"] = [perks[0]["style"], perks[1]["style"]]
    row["spells"] = sorted([me["summoner1Id"], me["summoner2Id"]])

    # 라인전(2:00~14:00) 서폿 위치와 그에 따른 CS. analyze.py의 lane_support와 같은 계산이에요.
    if sup:
        s = sup["participantId"]
        here = {m: bot(pf(m, s)["position"]) for m in range(2, 15)}
        w = {"min": 0, "cs": 0}
        wo = {"min": 0, "cs": 0}
        for m in range(2, 14):
            t = w if (here[m] and here[m + 1]) else wo
            t["min"] += 1
            t["cs"] += cs(m + 1, pid) - cs(m, pid)
        row["sup"] = {"withMin": w["min"], "withCs": w["cs"], "withoutMin": wo["min"], "withoutCs": wo["cs"]}
    return row


def usable(match, timeline=None):
    info = match["info"]
    if info.get("queueId") != 420 or info["gameDuration"] < 905:
        return False
    if any(p.get("gameEndedInEarlySurrender") for p in info["participants"]):
        return False
    if timeline is not None and len(timeline["info"]["frames"]) <= 15:
        return False
    return True


# ---------------------------------------------------------------- 요약

def stat(vals):
    vals = sorted(v for v in vals if v is not None)
    n = len(vals)
    if not n:
        return {"n": 0}

    def q(p):
        k = (n - 1) * p
        lo = int(k)
        hi = min(lo + 1, n - 1)
        return vals[lo] + (vals[hi] - vals[lo]) * (k - lo)
    r = lambda x: round(x, 2) if abs(x) < 20 else round(x, 1)  # noqa: E731
    return {"n": n, "mean": r(sum(vals) / n), "p25": r(q(0.25)), "median": r(q(0.5)), "p75": r(q(0.75))}


def win_rate(rows):
    return round(100 * sum(r["win"] for r in rows) / len(rows), 1) if rows else None


def item_name(iid):
    return DD["item"].get(iid, {}).get("name", str(iid))


def pick_rows(rows):
    """최신 패치만 쓰되, 판 수가 적으면 바로 전 패치까지 합쳐요(최대 3개)."""
    key = lambda p: tuple(int(x) for x in p.split("."))  # noqa: E731
    patches = sorted({r["patch"] for r in rows}, key=key, reverse=True)
    used, out = [], []
    for p in patches[:3]:
        used.append(p)
        out += [r for r in rows if r["patch"] == p]
        if len(out) >= MIN_PATCH_ROWS:
            break
    return out, used


def summarize(champ, rows):
    rows, patches = pick_rows(rows)
    s = {"champion": champ, "championKo": DD["champ"].get(champ, champ), "patches": patches,
         "tiers": TIERS, "updatedAt": datetime.now(KST).strftime("%Y-%m-%d %H:%M"), "games": len(rows),
         "winRate": win_rate(rows), "minN": MIN_N,
         "note": "기준 티어는 판을 찾은 참가자의 티어예요. 같은 판의 원딜 티어는 조금 다를 수 있어요."}
    m = {}
    for t in ("t10", "t15"):
        for k in ("cs", "gold", "xp"):
            m[f"{k}{t[1:]}"] = stat([r[t][k] for r in rows])
    m["dmg15"] = stat([r["t15"]["dmg"] for r in rows])
    m["dpm"] = stat([r["dpm"] for r in rows])
    m["vspm"] = stat([r["vspm"] for r in rows])
    m["goldDiff15"] = stat([r["t15"]["gold"] - r["oppGold15"] for r in rows if "oppGold15" in r])
    m["csDiff15"] = stat([r["t15"]["cs"] - r["oppCs15"] for r in rows if "oppCs15" in r])
    m["core1Time"] = stat([r["items"][0][1] for r in rows if len(r["items"]) >= 1])
    m["core2Time"] = stat([r["items"][1][1] for r in rows if len(r["items"]) >= 2])
    s["metrics"] = m

    # 서폿이 바텀에 있던 비율, 서폿 있을 때/없을 때 분당 CS
    sr = [r["sup"] for r in rows if "sup" in r]
    s["support"] = {
        "atBotShare": stat([x["withMin"] / 12 for x in sr]),
        "csPerMinWith": stat([x["withCs"] / x["withMin"] for x in sr if x["withMin"] >= 3]),
        "csPerMinWithout": stat([x["withoutCs"] / x["withoutMin"] for x in sr if x["withoutMin"] >= 3]),
    }

    # 상대 원딜별 15분 골드 차이 (판 수 3 이상만 저장, 보여 줄지는 minN.matchup으로 정해요)
    by_opp = collections.defaultdict(list)
    for r in rows:
        if "oppGold15" in r:
            by_opp[r["opp"]].append(r)
    s["matchups"] = sorted(
        [{"opp": o, "oppKo": DD["champ"].get(o, o), "n": len(v), "winRate": win_rate(v),
          "goldDiff15": stat([r["t15"]["gold"] - r["oppGold15"] for r in v])["median"]}
         for o, v in by_opp.items() if len(v) >= 3], key=lambda x: -x["n"])

    # 빌드: 첫 코어, 첫 두 코어 순서, 핵심 룬
    def ranking(keyf, namef, top):
        g = collections.defaultdict(list)
        for r in rows:
            k = keyf(r)
            if k is not None:
                g[k].append(r)
        out = [{"key": list(k) if isinstance(k, tuple) else k, "name": namef(k), "n": len(v),
                "share": round(100 * len(v) / len(rows), 1), "winRate": win_rate(v)} for k, v in g.items()]
        return sorted(out, key=lambda x: -x["n"])[:top]
    s["builds"] = {
        "core1": ranking(lambda r: r["items"][0][0] if r["items"] else None, item_name, 6),
        "core12": ranking(lambda r: tuple(i for i, _ in r["items"][:2]) if len(r["items"]) >= 2 else None,
                          lambda k: " → ".join(item_name(i) for i in k), 8),
        "keystone": ranking(lambda r: (r["keystone"], r["styles"][1]),
                            lambda k: f"{DD['rune'].get(k[0], k[0])} + {DD['style'].get(k[1], k[1])}", 5),
    }
    return s


# ---------------------------------------------------------------- 파일

def rows_path(champ):
    return os.path.join(ROWS_DIR, f"{champ}.jsonl")


def load_rows(champ):
    p = rows_path(champ)
    if not os.path.exists(p):
        return []
    return [json.loads(line) for line in open(p, encoding="utf-8") if line.strip()]


def append_row(champ, row):
    os.makedirs(ROWS_DIR, exist_ok=True)
    with open(rows_path(champ), "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")


def write_summaries():
    os.makedirs(BM_DIR, exist_ok=True)
    for c in CHAMPS:
        rows = load_rows(c)
        if not rows:
            continue
        s = summarize(c, rows)
        json.dump(s, open(os.path.join(BM_DIR, f"{c}.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"  {s['championKo']}: 요약 {s['games']}판 (패치 {', '.join(s['patches'])})")


# ---------------------------------------------------------------- 수집

def collect():
    key = os.environ.get("RIOT_API_KEY", "").strip()
    if not key:
        sys.exit("RIOT_API_KEY가 비어 있어요. 저장소 Settings > Secrets에 키를 넣어 주세요.")
    load_dd()
    patch = patch_of(DD["version"]) if PATCH == "auto" else (None if PATCH == "any" else PATCH)
    print(f"패치 {patch or '전부'}, 챔피언 {', '.join(CHAMPS)}, 목표 {TARGET}판, 최대 {MAX_MINUTES:.0f}분")
    deadline = time.time() + MAX_MINUTES * 60
    start_time = int((datetime.now(timezone.utc) - timedelta(days=DAYS)).timestamp())

    existing = {c: load_rows(c) for c in CHAMPS}
    done_mids = {r["mid"] for rows in existing.values() for r in rows}
    count = {c: sum(1 for r in existing[c] if patch is None or r["patch"] == patch) for c in CHAMPS}
    per_player = collections.Counter((c, r["ph"]) for c in CHAMPS for r in existing[c])
    print("  이미 있는 판:", ", ".join(f"{c} {count[c]}" for c in CHAMPS))

    # 1) 참가자 목록
    seeds = []
    try:
        for tier in TIERS:
            for div in DIVISIONS:
                for page in LEAGUE_PAGES:
                    entries = api_get(f"/lol/league/v4/entries/RANKED_SOLO_5x5/{tier}/{div}", key,
                                      {"page": page}, host="kr")
                    seeds += [(e["puuid"], f"{tier} {div}") for e in entries if e.get("puuid")]
    except KeyExpired:
        sys.exit("API 키가 틀렸거나 만료됐어요. Secrets의 RIOT_API_KEY를 확인해 주세요.")
    random.shuffle(seeds)
    print(f"  참가자 {len(seeds)}명을 찾았어요.")

    # 2) 경기 찾기
    stats = {"checked": 0, "kept": 0}
    try:
        find_games(key, seeds, patch, start_time, deadline, count, per_player, done_mids, stats)
    except KeyExpired:
        print("  도중에 API 키가 만료돼서 여기까지 모은 걸로 요약할게요.")
    print(f"끝: {stats['checked']}판 확인, {stats['kept']}판 저장, 요청 {LIMIT.count}번")
    print("  패치별 판 수:", ", ".join(f"{c} {count[c]}" for c in CHAMPS))
    write_summaries()


def find_games(key, seeds, patch, start_time, deadline, count, per_player, done_mids, stats):
    seen = set()
    for puuid, tier in seeds:
        if time.time() > deadline or all(count[c] >= TARGET for c in CHAMPS):
            break
        try:
            ids = api_get(f"/lol/match/v5/matches/by-puuid/{puuid}/ids", key,
                          {"queue": 420, "type": "ranked", "startTime": start_time, "count": 20})
        except ApiError:
            continue
        for mid in ids:
            if time.time() > deadline:
                break
            if mid in seen or mid in done_mids:
                continue
            seen.add(mid)
            try:
                m = api_get(f"/lol/match/v5/matches/{mid}", key)
            except ApiError:
                continue
            stats["checked"] += 1
            if stats["checked"] % 50 == 0:
                print(f"  {stats['checked']}판 확인, {stats['kept']}판 저장 — " + ", ".join(f"{c} {count[c]}" for c in CHAMPS))
            if not usable(m) or (patch and patch_of(m["info"]["gameVersion"]) != patch):
                continue
            cand = [p for p in m["info"]["participants"]
                    if p["teamPosition"] == "BOTTOM" and p["championName"] in count
                    and count[p["championName"]] < TARGET]
            cand = [p for p in cand if per_player[(p["championName"], hashlib.sha1(p["puuid"].encode()).hexdigest()[:10])]
                    < PER_PLAYER_CAP]
            if not cand:
                continue
            try:
                t = api_get(f"/lol/match/v5/matches/{mid}/timeline", key)
            except ApiError:
                continue
            if not usable(m, t):
                continue
            for p in cand:
                c = p["championName"]
                row = extract_row(m, t, p["participantId"], tier)
                append_row(c, row)
                count[c] += 1
                per_player[(c, row["ph"])] += 1
                stats["kept"] += 1


def test(paths):
    """저장소 원본 경기로 뽑기와 요약이 도는지 확인해요."""
    load_dd()
    rows = collections.defaultdict(list)
    for p in paths:
        d = json.load(gzip.open(p, "rt", encoding="utf-8"))
        m, t = d["match"], d["timeline"]
        print(os.path.basename(p), "사용 가능" if usable(m, t) else "사용 안 함(짧은 판/항복 등)")
        for x in m["info"]["participants"]:
            if x["teamPosition"] == "BOTTOM":
                r = extract_row(m, t, x["participantId"], "TEST")
                rows[x["championName"]].append(r)
                print(" ", x["championName"], json.dumps({k: r[k] for k in ("t10", "t15", "items", "sup", "opp")
                                                          if k in r}, ensure_ascii=False))
    for c, rs in rows.items():
        s = summarize(c, rs)
        print(c, json.dumps(s["metrics"]["cs15"], ensure_ascii=False), s["builds"]["core12"][:1])


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "collect"
    if mode == "collect":
        collect()
    elif mode == "summarize":
        load_dd()
        write_summaries()
    elif mode == "test":
        test(sys.argv[2:] or sorted(glob.glob(os.path.join(ROOT, "raw", "*.json.gz"))))
    else:
        sys.exit("collect / summarize / test 중 하나를 써 주세요.")
