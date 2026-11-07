"""기록 목록(첫 페이지) 시안을 만든다.
- 실제 판: 저장소의 docs/data/games.json + raw/ + docs/data/rank_history.json
- 하루 경계: 새벽 6시(KST). 경기 '시작' 시간 기준이라 6시 전에 시작한 판은 끝난 시간과 상관없이 전날 기록이다.
- 예시 날짜: 색감과 배치를 보려고 넣은 가짜 데이터. 화면에 '예시'라고 표시하고 피드백은 만들지 않는다.
사용: python3 -I build_index.py <저장소> <tools/report 폴더(report.css, img/)> <출력 html>"""
import base64, datetime as dt, gzip, html, io, json, os, random, re, sys, urllib.request

REPO, REPORT, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(REPO, "data")
IMG = os.path.join(HERE, "img")
os.makedirs(IMG, exist_ok=True)
MIRROR = "https://raw.githubusercontent.com/noxelisdev/LoL_DDragon/master/"
KST = dt.timezone(dt.timedelta(hours=9))
esc = html.escape

DD_CH = json.load(open(os.path.join(DATA, "dd_champion.json")))["data"]
DD_SP = json.load(open(os.path.join(DATA, "dd_summoner.json")))["data"]
DD_RU = json.load(open(os.path.join(DATA, "dd_runesReforged.json")))
SPELL_KEY = {}
for k, v in DD_SP.items():
    if v["key"] not in SPELL_KEY or "_" not in k:
        SPELL_KEY[v["key"]] = k
PERK, STYLE = {}, {}
for s in DD_RU:
    STYLE[s["id"]] = (s["name"], s["icon"])
    for sl in s["slots"]:
        for r in sl["runes"]:
            PERK[r["id"]] = (r["name"], r["icon"])

REPORT_LINKS = {"KR_8447066522": "https://claude.ai/artifact/Ukou2E2Nt9NN9V2GJdoL1U",
                "KR_8448036968": "https://claude.ai/artifact/GTomga1baAKoPXm3HUN1xj"}  # 지금 리포트가 있는 판
LIVE_PARTIAL = {"KR_8448036968"}  # PC에서 직접 가져온 게임 중 기록이 일부만 있는 판 (저장소에는 아직 없음)


def fetch(rel, name):
    dst = os.path.join(IMG, name)
    if not os.path.exists(dst):
        src = os.path.join(REPORT, "img", name)
        if os.path.exists(src):
            open(dst, "wb").write(open(src, "rb").read())
        else:
            with urllib.request.urlopen(MIRROR + rel, timeout=20) as r:
                open(dst, "wb").write(r.read())
    return dst


def data_uri(path, size):
    from PIL import Image
    im = Image.open(path).convert("RGBA")
    if size:
        im = im.resize((size, size), Image.LANCZOS)
    bio = io.BytesIO(); im.save(bio, "WEBP", quality=85)
    return "data:image/webp;base64," + base64.b64encode(bio.getvalue()).decode()


_cache = {}


def champ(key, size=80):
    k = ("c", key, size)
    if k not in _cache:
        _cache[k] = data_uri(fetch(f"latest/img/champion/{key}.png", f"c_{key}.png"), size)
    return _cache[k]


def spell(sid):
    key = SPELL_KEY[str(sid)]
    k = ("s", key)
    if k not in _cache:
        _cache[k] = data_uri(fetch(f"latest/img/spell/{key}.png", f"s_{key}.png"), 44)
    return _cache[k], DD_SP[key]["name"]


def perk(icon):
    k = ("p", icon)
    if k not in _cache:
        _cache[k] = data_uri(fetch(f"img/{icon}", "p_" + os.path.basename(icon)), 44)
    return _cache[k]


def cname(key):
    return DD_CH[key]["name"]


def game_day(start):
    """새벽 6시 기준 날짜. 시작 시간만 본다."""
    return (start - dt.timedelta(hours=6)).date()


WD = "월화수목금토일"


def num(n):
    return f"{n:,}"


def signed(n):
    return ("+" if n > 0 else "−" if n < 0 else "±") + f"{abs(n):,}"


def mmss(sec):
    return f"{sec // 60}:{sec % 60:02d}"


# ---------- 실제 판 ----------
games_idx = json.load(open(os.path.join(REPO, "docs", "data", "games.json")))
hist = json.load(open(os.path.join(REPO, "docs", "data", "rank_history.json")))
TIER_KO = {"IRON": "아이언", "BRONZE": "브론즈", "SILVER": "실버", "GOLD": "골드", "PLATINUM": "플래티넘",
           "EMERALD": "에메랄드", "DIAMOND": "다이아몬드", "MASTER": "마스터"}
ROMAN = {"I": 1, "II": 2, "III": 3, "IV": 4}
lp_after = {h["matchId"]: h["entry"] for h in hist}
order = sorted(games_idx, key=lambda g: g["start"])

real = []
prev_entry = None
for g in order:
    start = dt.datetime.fromisoformat(g["start"]).astimezone(KST)
    raw = json.load(gzip.open(os.path.join(REPO, "raw", g["matchId"] + ".json.gz")))
    info = raw["match"]["info"]
    me = next(p for p in info["participants"] if p["championName"] == g["championId"])
    e = lp_after.get(g["matchId"])
    lp = None
    # LP 변화는 바로 앞 판의 기록과 같은 티어일 때만 계산한다(앞 판 기록이 없으면 모름).
    if e and prev_entry and e["tier"] == prev_entry["tier"] and e["rank"] == prev_entry["rank"] \
            and e["wins"] + e["losses"] == prev_entry["wins"] + prev_entry["losses"] + 1:
        lp = e["leaguePoints"] - prev_entry["leaguePoints"]
    prev_entry = e
    real.append({
        "id": g["matchId"], "start": start, "end": start + dt.timedelta(seconds=g["durationSec"]),
        "champ": g["championId"], "opp": next((k for k, v in DD_CH.items() if v["name"] == g["opponent"]), None),
        "win": g["win"], "k": g["kills"], "d": g["deaths"], "a": g["assists"], "cs": g["cs"], "cspm": g["csPerMin"],
        "gd15": g.get("goldDiff15"), "dur": g["durationSec"], "pos": g["position"], "lp": lp,
        "rank": f'{TIER_KO[e["tier"]]} {ROMAN[e["rank"]]} {e["leaguePoints"]}LP' if e else None,
        "live": g.get("liveLog", False), "spells": [me["summoner1Id"], me["summoner2Id"]],
        "keystone": me["perks"]["styles"][0]["selections"][0]["perk"], "sub": me["perks"]["styles"][1]["style"],
        "lvl": me["champLevel"], "example": False, "report": REPORT_LINKS.get(g["matchId"]),
    })
latest_rank = hist[-1]["entry"] if hist else None

# ---------- 예시 날짜 ----------
rng = random.Random(7)
POOL = ["Jinx", "Jinx", "Jinx", "Ashe", "MissFortune", "Xayah", "Ahri", "Leona", "Rell", "Nautilus", "Seraphine", "Kaisa"]
OPPS = ["Ezreal", "Caitlyn", "Varus", "Kalista", "Lucian", "Draven", "Jhin", "Sivir", "Viktor", "Syndra", "Thresh", "Lulu"]
EX_DAYS = [(11, 4, 4, 21), (11, 3, 2, 19), (11, 1, 6, 14), (10, 31, 1, 23), (10, 30, 3, 20), (10, 28, 5, 18), (10, 27, 2, 22), (10, 25, 7, 13)]
example = []
for m, d, n, hour in EX_DAYS:
    t = dt.datetime(2026, m, d, hour, rng.randint(0, 50), tzinfo=KST)
    for _ in range(n):
        dur = rng.randint(1350, 2300)
        win = rng.random() < 0.5
        ch = rng.choice(POOL)
        k, dd, a = rng.randint(1, 12), rng.randint(1, 10), rng.randint(2, 16)
        cs = int(dur / 60 * rng.uniform(5.2, 8.1))
        example.append({"id": None, "start": t, "end": t + dt.timedelta(seconds=dur), "champ": ch, "opp": rng.choice(OPPS),
                        "win": win, "k": k, "d": dd, "a": a, "cs": cs, "cspm": round(cs / (dur / 60), 1),
                        "gd15": rng.randint(-3000, 3000), "dur": dur, "pos": "원딜", "lp": rng.randint(17, 24) * (1 if win else -1),
                        "rank": None, "live": None, "example": True, "report": None})
        t = t + dt.timedelta(seconds=dur + rng.randint(120, 900))

# ---------- 날짜로 묶기 ----------
days = {}
for g in real + example:
    days.setdefault(game_day(g["start"]), []).append(g)
for v in days.values():
    v.sort(key=lambda g: g["start"])
day_keys = sorted(days, reverse=True)

COLORS = [("#3fe0e6", "#111214"), ("#c6f24e", "#111214"), ("#ffd23f", "#111214"), ("#ff9a3c", "#111214"),
          ("#ff8fd0", "#111214"), ("#b7a4ff", "#111214"), ("#3d7bff", "#ffffff"), ("#2fbf71", "#111214"),
          ("#1a1b1e", "#f2f3f5"), ("#dfe1e5", "#111214")]


def back_of(hexc):
    """뒤판/탭 색: 밝은 색은 어둡게, 어두운 색은 밝게."""
    r, g, b = (int(hexc[i:i + 2], 16) for i in (1, 3, 5))
    lum = 0.2126 * r + 0.7152 * g + 0.0722 * b
    f = 0.82 if lum > 60 else None
    if f:
        r, g, b = (int(c * f) for c in (r, g, b))
    else:
        r, g, b = (int(c + (255 - c) * 0.14) for c in (r, g, b))
    return f"#{r:02x}{g:02x}{b:02x}"


def day_summary(gs):
    w = sum(g["win"] for g in gs)
    lps = [g["lp"] for g in gs]
    known = [x for x in lps if x is not None]
    cnt = {}
    for g in gs:
        cnt[g["champ"]] = cnt.get(g["champ"], 0) + 1
    top = max(cnt.items(), key=lambda x: (x[1], -[g["champ"] for g in gs].index(x[0])))
    k = sum(g["k"] for g in gs); d = sum(g["d"] for g in gs); a = sum(g["a"] for g in gs)
    return {"n": len(gs), "w": w, "l": len(gs) - w, "lp": sum(known) if known else None, "lp_known": len(known),
            "top": top, "first": gs[0]["start"], "last": gs[-1]["end"], "kda": (k + a) / max(d, 1),
            "play": sum(g["dur"] for g in gs), "example": all(g["example"] for g in gs)}


def lp_text(s):
    if s["lp"] is None:
        return '<span class="f-unk">기록 없음</span>'
    t = signed(s["lp"])
    if s["lp_known"] < s["n"]:
        t += f' <small>({s["n"]}판 중 {s["lp_known"]}판)</small>'
    return t


def folder(day, i):
    gs = days[day]; s = day_summary(gs)
    bg, fg = COLORS[i % len(COLORS)]
    champs = []
    for g in reversed(gs):  # 최근 판이 앞
        if g["champ"] not in champs:
            champs.append(g["champ"])
    sheets = "".join(f'<span class="sheet" style="--i:{j}"><img src="{champ(c, 72)}" alt="{esc(cname(c))}"></span>'
                     for j, c in enumerate(champs[:4]))
    more = f'<span class="sheet sheet-more" style="--i:{min(len(champs), 4)}">+{len(champs) - 4}</span>' if len(champs) > 4 else ""
    wl = "".join(f'<i class="{"w" if g["win"] else "l"}" title="{"승리" if g["win"] else "패배"}">{"승" if g["win"] else "패"}</i>' for g in gs)
    ex = '<span class="f-ex">예시</span>' if s["example"] else ""
    rows = [("판 수", f'{s["n"]}판'), ("승/패", f'{s["w"]}승 {s["l"]}패'), ("LP 변화", lp_text(s)),
            ("가장 많이 한 챔피언", f'{esc(cname(s["top"][0]))} {s["top"][1]}판' if s["top"][1] > 1 or s["n"] == 1 else f'{len(champs)}명, 1판씩'),
            ("시간", f'{s["first"]:%H:%M} ~ {s["last"]:%H:%M}')]
    dl = "".join(f'<div><dt>{a}</dt><i></i><dd>{b}</dd></div>' for a, b in rows)
    return (f'<a class="folder" href="#day-{day:%Y-%m-%d}" style="--f:{bg};--fb:{back_of(bg)};--fi:{fg}">'
            f'<span class="f-tab"></span><span class="f-back"></span><span class="f-sheets">{sheets}{more}</span>'
            f'<span class="f-front"><span class="f-top"><span class="f-date"><b class="num">{day:%m.%d}</b>'
            f'<span>{WD[day.weekday()]}요일</span></span>{ex}</span>'
            f'<span class="f-wl">{wl}</span><dl class="f-rows">{dl}</dl></span></a>')


def loadout(g):
    if g["example"]:
        return f'<div class="portrait"><img class="ic ic-md" src="{champ(g["champ"])}" alt="{esc(cname(g["champ"]))}"></div>'
    s1, n1 = spell(g["spells"][0]); s2, n2 = spell(g["spells"][1])
    kn, kp = PERK[g["keystone"]]; sn, sp = STYLE[g["sub"]]
    return (f'<div class="loadout"><div class="portrait"><img class="ic ic-md" src="{champ(g["champ"])}" alt="{esc(cname(g["champ"]))}">'
            f'<span class="lvl">{g["lvl"]}</span></div><div class="loadout-grid">'
            f'<img class="ic ic-xs" src="{s1}" alt="{esc(n1)}" title="{esc(n1)}">'
            f'<img class="ic ic-xs ic-rune" src="{perk(kp)}" alt="{esc(kn)}" title="{esc(kn)}">'
            f'<img class="ic ic-xs" src="{s2}" alt="{esc(n2)}" title="{esc(n2)}">'
            f'<img class="ic ic-xs ic-rune ic-style" src="{perk(sp)}" alt="{esc(sn)}" title="{esc(sn)}"></div></div>')


def game_row(g, idx):
    kda = (g["k"] + g["a"]) / max(g["d"], 1)
    gd = "" if g["gd15"] is None else f'<span class="num{" neg" if g["gd15"] < 0 else ""}">{signed(g["gd15"])}</span>'
    lp = '<span class="muted">기록 없음</span>' if g["lp"] is None else f'<span class="num{" neg" if g["lp"] < 0 else ""}">{signed(g["lp"])}</span>'
    if g["example"]:
        live = '<span class="chip chip-line">예시</span>'
        link = '<span class="muted small">없음</span>'
    else:
        live = ('<span class="chip chip-pos">있음</span>' if g["live"] else
                '<span class="chip chip-mid">일부</span>' if g["id"] in LIVE_PARTIAL else '<span class="chip chip-unknown">기록 없음</span>')
        link = (f'<a class="g-link" href="{g["report"]}" target="_blank" rel="noopener">리포트 보기 →</a>' if g["report"]
                else '<span class="muted small">아직 없음</span>')
    opp = f'<span class="g-vs">vs {esc(cname(g["opp"]))}</span>' if g["opp"] else ""
    nxt = "" if g["start"].date() == (g["start"] - dt.timedelta(hours=6)).date() else '<span class="g-next">다음 날</span>'
    return (f'<li class="game {"is-win" if g["win"] else "is-loss"}">'
            f'<div class="g-time"><span class="g-no num">{idx:02d}</span><time class="num">{g["start"]:%H:%M}</time>{nxt}</div>'
            f'<div class="g-res"><span class="chip {"chip-pos" if g["win"] else "chip-bad"}">{"승리" if g["win"] else "패배"}</span>'
            f'<span class="g-dur num">{mmss(g["dur"])}</span></div>'
            f'<div class="g-champ">{loadout(g)}<div><b>{esc(cname(g["champ"]))}</b>{opp}</div></div>'
            f'<div class="g-stat"><span class="label">KDA</span><b class="num">{g["k"]}/<span class="death">{g["d"]}</span>/{g["a"]}</b><span class="small muted">평점 {kda:.2f}</span></div>'
            f'<div class="g-stat"><span class="label">CS</span><b class="num">{g["cs"]}</b><span class="small muted">분당 {g["cspm"]}</span></div>'
            f'<div class="g-stat"><span class="label">15분 맞라인 골드</span><b class="num-b">{gd}</b></div>'
            f'<div class="g-stat"><span class="label">LP</span><b class="num-b">{lp}</b>'
            f'<span class="small muted">{esc(g["rank"] or "")}</span></div>'
            f'<div class="g-stat"><span class="label">게임 중 기록</span><span>{live}</span></div>'
            f'<div class="g-go">{link}</div></li>')


def day_view(day, i):
    gs = days[day]; s = day_summary(gs)
    bg, fg = COLORS[i % len(COLORS)]
    seq = "".join(f'<li class="{"w" if g["win"] else "l"}"><span class="chip {"chip-pos" if g["win"] else "chip-bad"}">'
                  f'{"승" if g["win"] else "패"}</span><time class="num">{g["start"]:%H:%M}</time></li>' for g in gs)
    lp = "기록 없음" if s["lp"] is None else signed(s["lp"])
    lp_sub = "" if s["lp"] is None or s["lp_known"] == s["n"] else f'{s["n"]}판 중 {s["lp_known"]}판만 기록'
    tiles = [("판 수", f'{s["n"]}', f'{s["w"]}승 {s["l"]}패'), ("LP 변화", lp, lp_sub),
             ("평균 평점", f'{s["kda"]:.2f}', "(킬+어시스트)/데스"), ("플레이 시간", f'{s["play"] // 3600}:{s["play"] % 3600 // 60:02d}', "게임 시간 합")]
    tl = "".join(f'<div class="d-tile"><span class="label">{a}</span><b class="num{" neg" if a == "LP 변화" and s["lp"] is not None and s["lp"] < 0 else ""}">{b}</b>'
                 f'<span class="small muted">{c}</span></div>' for a, b, c in tiles)
    ex = '<span class="chip chip-line">예시 데이터</span>' if s["example"] else ""
    rows = "".join(game_row(g, j + 1) for j, g in enumerate(gs))
    return (f'<section class="dayview" id="day-{day:%Y-%m-%d}" hidden>'
            f'<a class="back" href="#">← 경기 기록</a>'
            f'<header class="day-head" style="--f:{bg};--fb:{back_of(bg)};--fi:{fg}"><span class="dh-tab"></span>'
            f'<div class="dh-body"><div class="dh-title"><h1><b class="num">{day:%m.%d}</b> {WD[day.weekday()]}요일</h1>{ex}</div>'
            f'<p class="dh-sub">{s["first"]:%H:%M}에 시작해서 {"다음 날 " if s["last"].date() > day else ""}{s["last"]:%H:%M}에 끝났어요.</p></div></header>'
            f'<div class="d-tiles">{tl}</div>'
            f'<h2 class="sub-h">하루 흐름</h2><ol class="d-seq">{seq}</ol>'
            f'<h2 class="sub-h">경기</h2><ol class="games">{rows}</ol></section>')


# ---------- 페이지 ----------
groups = {}
for i, day in enumerate(day_keys):
    groups.setdefault((day.year, day.month), []).append((day, i))
lists = "".join(f'<section class="month"><header class="m-head"><h2><b class="num">{m}</b>월</h2></header>'
                f'<div class="folders">{"".join(folder(d, i) for d, i in items)}</div></section>'
                for (y, m), items in groups.items())
views = "".join(day_view(d, i) for i, d in enumerate(day_keys))

rk = f'{TIER_KO[latest_rank["tier"]]} {ROMAN[latest_rank["rank"]]}' if latest_rank else "기록 없음"
lpn = latest_rank["leaguePoints"] if latest_rank else ""
n_real = len(real); w_real = sum(g["win"] for g in real)
head = f'''<header class="list-head">
  <div class="lh-title"><div class="stripes"></div><h1>경기 기록</h1>
  <p class="muted">솔로 랭크만 모아요. 새벽 6시 전에 시작한 판은 전날 기록이에요.</p></div>
  <div class="lh-stats">
    <div><span class="label">지금 랭크</span><b>{rk} <span class="num">{lpn}</span><small>LP</small></b></div>
    <div><span class="label">기록한 판</span><b class="num">{n_real}</b><span class="small muted">{w_real}승 {n_real - w_real}패</span></div>
  </div>
</header>'''

SITENAV = ('<nav class="sitenav" aria-label="페이지"><ul><li><a class="on" href="#">경기 기록</a></li>'
           '<li><a href="#">챔피언 노트</a></li><li><a href="#">상성 노트</a></li></ul></nav>')
JS = '''<script>
(function () {
  var list = document.getElementById('list');
  function show() {
    var id = location.hash.slice(1), v = id && document.getElementById(id);
    document.querySelectorAll('.dayview').forEach(function (s) { s.hidden = s !== v; });
    list.hidden = !!v;
    window.scrollTo(0, 0);
  }
  window.addEventListener('hashchange', show); show();
})();
</script>'''

REPORT_CSS = open(os.path.join(REPORT, "report.css"), encoding="utf-8").read()
INDEX_CSS = open(os.path.join(HERE, "index.css"), encoding="utf-8").read()
page = f'''<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>경기 기록</title>
<style>/*FONTS*/
{REPORT_CSS}
{INDEX_CSS}</style>
</head>
<body>
<main class="wrap">
{SITENAV}
<div id="list">{head}{lists}</div>
{views}
<div class="page-end"></div>
</main>
{JS}
</body>
</html>'''


def embed(out):
    from fontTools import subset
    text = re.sub(r"<[^>]+>", " ", out) + "".join(chr(c) for c in range(32, 127)) + "−±→←…—"
    faces = []
    FD = os.path.join(REPO, "tools", "fonts")
    for fam, path, rng_ in [
        ("Pretendard Variable", os.path.join(FD, "PretendardVariable.woff2"), "45 920"),
        ("Archivo", os.path.join(FD, "archivo-latin-wdth-normal.woff2"), "100 900"),
    ]:
        opts = subset.Options(); opts.flavor = "woff2"; opts.layout_features = ["*"]
        f = subset.load_font(path, opts)
        s = subset.Subsetter(opts); s.populate(text=text); s.subset(f)
        bio = io.BytesIO(); subset.save_font(f, bio, opts)
        st = "font-stretch:62% 125%;" if fam == "Archivo" else ""
        faces.append(f"@font-face{{font-family:'{fam}';src:url(data:font/woff2;base64,{base64.b64encode(bio.getvalue()).decode()}) format('woff2');font-weight:{rng_};{st}font-display:swap}}")
    return out.replace("/*FONTS*/", "".join(faces))


open(OUT, "w", encoding="utf-8").write(embed(page))
print("days", len(day_keys), "real", [(g["id"], f'{game_day(g["start"])}') for g in real])
print("written", os.path.getsize(OUT) // 1024, "KB")
