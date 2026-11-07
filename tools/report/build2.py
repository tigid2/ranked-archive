"""경기 리포트 v3 — raw 데이터 + 분석 결과 + 피드백 글을 한 페이지로 만든다.

사용: python3 tools/report/build2.py [local|cdn]   (결과는 tools/report/ 에 저장)
 - local: 아이콘을 img/ 폴더에 내려받아 상대 경로로 쓴다 (미리보기·artifact용)
 - cdn  : Data Dragon CDN 주소를 그대로 쓴다 (GitHub Pages용)
"""
import base64, gzip, html, json, os, sys, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..", "..")  # 저장소 맨 위
DATA = os.path.join(ROOT, "data")
MODE = sys.argv[1] if len(sys.argv) > 1 else "local"
VER = "16.22.1"
MIRROR = "https://raw.githubusercontent.com/noxelisdev/LoL_DDragon/master/"
CDN = f"https://ddragon.leagueoflegends.com/cdn/"
MID = os.environ.get("RA_MID", "KR_8447066522")
CHAMP = os.environ.get("RA_CHAMP", "Kaisa")
OUT_NAME = os.environ.get("RA_OUT")

raw = json.load(gzip.open(os.path.join(ROOT, "raw", MID + ".json.gz")))
A = json.load(open(os.path.join(ROOT, "analysis", MID + ".analysis.json")))
FB = json.load(open(os.environ.get("RA_FB") or os.path.join(ROOT, "feedback", MID + ".json"), encoding="utf-8"))
DD_CH = json.load(open(os.path.join(DATA, "dd_champion.json")))["data"]
DD_IT = json.load(open(os.path.join(DATA, "dd_item.json")))["data"]
DD_SP = json.load(open(os.path.join(DATA, "dd_summoner.json")))["data"]
DD_RU = json.load(open(os.path.join(DATA, "dd_runesReforged.json")))

info = raw["match"]["info"]
frames = raw["timeline"]["info"]["frames"]
events = [e for f in frames for e in f["events"]]
P = info["participants"]
ME = next(p for p in P if p["championName"] == CHAMP)
ME_KO = DD_CH[CHAMP]["name"]
MY_TEAM = ME["teamId"]
OPP = next(p for p in P if p["teamId"] != MY_TEAM and p["teamPosition"] == ME["teamPosition"])
by_pid = {p["participantId"]: p for p in P}

# ---------- 이름·아이콘 ----------
KO2KEY = {v["name"]: k for k, v in DD_CH.items()}
SPELL_KEY = {}
for k, v in DD_SP.items():
    if v["key"] not in SPELL_KEY or "_" not in k:
        SPELL_KEY[v["key"]] = k
SPELL_KO = {k: v["name"] for k, v in DD_SP.items()}
PERK = {}
STYLE = {}
for s in DD_RU:
    STYLE[s["id"]] = (s["name"], s["icon"])
    for sl in s["slots"]:
        for r in sl["runes"]:
            PERK[r["id"]] = (r["name"], r["icon"])
SHARD = {5005: ("공격 속도", "StatModsAttackSpeedIcon.png"), 5008: ("적응형 능력치", "StatModsAdaptiveForceIcon.png"),
         5001: ("체력 증가(성장)", "StatModsHealthScalingIcon.png"), 5011: ("체력", "StatModsHealthPlusIcon.png"),
         5007: ("스킬 가속", "StatModsCDRScalingIcon.png"), 5010: ("이동 속도", "StatModsMovementSpeedIcon.png"),
         5013: ("강인함/둔화 저항", "StatModsTenacityIcon.png")}

os.makedirs(os.path.join(HERE, "img"), exist_ok=True)


def asset(remote_rel, cdn_rel, local_name):
    """remote_rel: 미러 기준 경로, cdn_rel: ddragon 기준 경로"""
    if MODE == "cdn":
        return CDN + cdn_rel
    dst = os.path.join(HERE, "img", local_name)
    if not os.path.exists(dst):
        try:
            with urllib.request.urlopen(MIRROR + remote_rel, timeout=20) as r:
                open(dst, "wb").write(r.read())
        except Exception as e:  # noqa
            print("아이콘 못 받음", remote_rel, e)
            return ""
    return "img/" + local_name


def champ_img(key):
    return asset(f"latest/img/champion/{key}.png", f"{VER}/img/champion/{key}.png", f"c_{key}.png")


def item_img(i):
    return asset(f"latest/img/item/{i}.png", f"{VER}/img/item/{i}.png", f"i_{i}.png")


def spell_img(sid):
    k = SPELL_KEY[str(sid)]
    return asset(f"latest/img/spell/{k}.png", f"{VER}/img/spell/{k}.png", f"s_{k}.png"), SPELL_KO[k]


def perk_img(path, name):
    return asset(f"img/{path}", f"img/{path}", "p_" + os.path.basename(path))


def shard_img(sid):
    n, f = SHARD[sid]
    p = f"perk-images/StatMods/{f}"
    return asset(f"img/{p}", f"img/{p}", "p_" + f), n


def skill_img(fname):
    return asset(f"latest/img/spell/{fname}", f"{VER}/img/spell/{fname}", "k_" + fname)


def gray_map():
    """흑백 지도. iOS Safari는 SVG 이미지에 CSS filter를 안 먹여서, 미리 흑백으로 만든 파일을 써요
    (tools/make_gray_map.py로 만든 data/map11_gray.png). cdn 모드에서는 파일 안에 넣어요."""
    src = os.path.join(DATA, "map11_gray.png")
    if MODE == "cdn":
        return "data:image/png;base64," + base64.b64encode(open(src, "rb").read()).decode()
    dst = os.path.join(HERE, "img", "map11_gray.png")
    if not os.path.exists(dst):
        open(dst, "wb").write(open(src, "rb").read())
    return "img/map11_gray.png"


MAP_IMG = gray_map()

esc = html.escape


def ko_champ(p):
    return DD_CH[p["championName"]]["name"] if p["championName"] in DD_CH else p["championName"]


def key_of(label):
    """'이즈리얼(적)' → 'Ezreal'"""
    n = label.split("(")[0]
    return KO2KEY.get(n)


NONCHAMP = {"미니언": "minion", "바론": "baron", "포탑": "tower", "드래곤": "dragon", "전령": "herald"}


def gi(name, cls="gi"):
    return f'<svg class="{cls}" aria-hidden="true"><use href="#i-{name}"/></svg>'


def cimg(key, size="md", extra="", title=None):
    if not key:
        t = title or "?"
        return f'<span class="ic ic-{size} ic-glyph {extra}" title="{esc(t)}">{gi(NONCHAMP.get(t, "minion"))}</span>'
    t = title or DD_CH[key]["name"]
    return f'<img class="ic ic-{size} {extra}" src="{champ_img(key)}" alt="{esc(t)}" title="{esc(t)}">'


def iimg(i, size="sm", extra=""):
    if not i:
        return f'<span class="ic ic-{size} ic-empty {extra}"></span>'
    n = DD_IT.get(str(i), {}).get("name", str(i))
    return f'<img class="ic ic-{size} {extra}" src="{item_img(i)}" alt="{esc(n)}" title="{esc(n)}">'


def mmss(ms):
    s = int(ms // 1000)
    return f"{s // 60}:{s % 60:02d}"


def tsec(t):
    m, s = t.split(":")
    return int(m) * 60 + int(s)


def num(n):
    return f"{n:,}"


def signed(n):
    return ("+" if n > 0 else "−" if n < 0 else "±") + f"{abs(n):,}"


# ---------- 계산 ----------
dur = info["gameDuration"]
mins = dur / 60
my_pid, opp_pid = ME["participantId"], OPP["participantId"]


def pf(minute, pid):
    f = frames[min(minute, len(frames) - 1)]["participantFrames"][str(pid)]
    return {"gold": f["totalGold"], "cs": f["minionsKilled"] + f["jungleMinionsKilled"], "xp": f["xp"], "lvl": f["level"]}


kills_ev = [e for e in events if e["type"] == "CHAMPION_KILL"]
my_deaths_ev = [e for e in kills_ev if e["victimId"] == my_pid]
my_kills_ev = [e for e in kills_ev if e["killerId"] == my_pid]
my_assist_ev = [e for e in kills_ev if my_pid in e.get("assistingParticipantIds", [])]


def phase(sec):
    return "라인전" if sec < 14 * 60 else ("중반부" if sec < 25 * 60 else "후반부")


# 아이템 구매 (되돌리기 반영)
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


def is_complete(i):
    d = DD_IT.get(str(i), {})
    tags = d.get("tags", [])
    if "Consumable" in tags or "Trinket" in tags:
        return False
    return not d.get("into") and d.get("gold", {}).get("total", 0) >= 900


def groups(purch, gap=45000):
    g = []
    for t, i in purch:
        if g and t - g[-1]["t1"] <= gap:
            g[-1]["items"].append(i)
            g[-1]["t1"] = t
        else:
            g.append({"t0": t, "t1": t, "items": [i]})
    return g


my_purch = purchases(my_pid)
opp_purch = purchases(opp_pid)

# 오브젝트·건물
OBJ_KO = {"DRAGON": "드래곤", "BARON_NASHOR": "바론", "RIFTHERALD": "전령", "HORDE": "공허 유충", "ATAKHAN": "아타칸"}
DRAKE_KO = {"WATER_DRAGON": "바다", "EARTH_DRAGON": "대지", "FIRE_DRAGON": "화염", "AIR_DRAGON": "바람",
            "HEXTECH_DRAGON": "마법공학", "CHEMTECH_DRAGON": "화학공학", "ELDER_DRAGON": "장로"}
objs = []
for e in events:
    if e["type"] == "ELITE_MONSTER_KILL":
        if e.get("killerTeamId") not in (100, 200):  # 아무도 안 먹고 사라진 것(예: 바론 나올 때 사라진 전령)
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


def merge_grubs(objs, gap=30000):
    """공허 유충은 세 마리가 모여 있어서, 이어서(앞 유충과 gap 안에) 잡힌 것은 한 묶음으로 본다.
    묶음 안에서 더 많이 먹은 팀 하나만 남긴다(같은 수면 둘 다 남긴다)."""
    rest, groups = [], []
    for o in objs:
        if o["kind"] != "HORDE":
            rest.append(o)
        elif groups and o["t"] - groups[-1][-1]["t"] <= gap:
            groups[-1].append(o)
        else:
            groups.append([o])
    for g in groups:
        cnt = {True: [x for x in g if x["ours"]], False: [x for x in g if not x["ours"]]}
        top = max(len(v) for v in cnt.values())
        for ours, xs in cnt.items():
            if xs and len(xs) == top:
                rest.append({"t": xs[0]["t"], "kind": "HORDE", "name": f"공허 유충 {len(xs)}마리", "ours": ours})
    return sorted(rest, key=lambda o: o["t"])


objs = merge_grubs(objs)
OBJ_ICON = {"DRAGON": "dragon", "BARON_NASHOR": "baron", "RIFTHERALD": "herald", "HORDE": "grub", "TOWER": "tower", "INHIB": "inhib", "ATAKHAN": "atakhan"}

flow = A["flow"]
team_rows = {MY_TEAM: [], 300 - MY_TEAM: []}
ORDER = ["TOP", "JUNGLE", "MIDDLE", "BOTTOM", "UTILITY"]
POS_KO = {"TOP": "탑", "JUNGLE": "정글", "MIDDLE": "미드", "BOTTOM": "원딜", "UTILITY": "서폿"}
for p in sorted(P, key=lambda p: ORDER.index(p["teamPosition"])):
    team_rows[p["teamId"]].append(p)
team_kills = {t: sum(p["kills"] for p in rows) for t, rows in team_rows.items()}
team_obj = {t["teamId"]: t["objectives"] for t in info["teams"]}


# ---------- 조각: 아이콘 묶음 ----------
def loadout(p, big=False):
    """OP.GG식: 초상화 + 레벨 / 스펠 2개 / 핵심 룬 + 보조 빌드"""
    key = p["championName"]
    s1, n1 = spell_img(p["summoner1Id"])
    s2, n2 = spell_img(p["summoner2Id"])
    ks = p["perks"]["styles"][0]["selections"][0]["perk"]
    sub = p["perks"]["styles"][1]["style"]
    kn, kp = PERK[ks]
    sn, sp = STYLE[sub]
    size = "xl" if big else "md"
    return (f'<div class="loadout {"loadout-big" if big else ""}">'
            f'<div class="portrait">{cimg(key, size)}<span class="lvl">{p["champLevel"]}</span></div>'
            f'<div class="loadout-grid">'
            f'<img class="ic ic-xs" src="{s1}" alt="{esc(n1)}" title="{esc(n1)}">'
            f'<img class="ic ic-xs ic-rune" src="{perk_img(kp, kn)}" alt="{esc(kn)}" title="{esc(kn)}">'
            f'<img class="ic ic-xs" src="{s2}" alt="{esc(n2)}" title="{esc(n2)}">'
            f'<img class="ic ic-xs ic-rune ic-style" src="{perk_img(sp, sn)}" alt="{esc(sn)}" title="{esc(sn)}">'
            f'</div></div>')


def items_row(p, size="sm"):
    its = "".join(iimg(p[f"item{i}"], size) for i in range(6))
    return f'<div class="items">{its}<span class="trinket">{iimg(p["item6"], size)}</span></div>'


# ---------- 아이콘 묶음 (글자 대신 쓰는 그림 아이콘) ----------
SPRITE = '''<svg class="sprite" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
<symbol id="i-dragon" viewBox="0 0 24 24"><path d="M3 20 8 10 6 3l5 4 4-3-1 5 7 2-5 3 1 6-5-4z"/></symbol>
<symbol id="i-baron" viewBox="0 0 24 24"><path d="M6 9 7.5 3 10 7l2-4 2 4 2.5-4L18 9z"/><path fill-rule="evenodd" d="M4 21c0-7 3.5-11 8-11s8 4 8 11l-4-2.5-4 2.5-4-2.5zm8-8a2 2 0 1 0 0 4 2 2 0 0 0 0-4z"/></symbol>
<symbol id="i-herald" viewBox="0 0 24 24"><path fill-rule="evenodd" d="M1.5 12C5 5.5 19 5.5 22.5 12 19 18.5 5 18.5 1.5 12zm10.5-4a4 4 0 1 0 0 8 4 4 0 0 0 0-8zm0 2.4a1.6 1.6 0 1 1 0 3.2 1.6 1.6 0 0 1 0-3.2z"/></symbol>
<symbol id="i-grub" viewBox="0 0 24 24"><circle cx="12" cy="7" r="4"/><circle cx="6.5" cy="16" r="4"/><circle cx="17.5" cy="16" r="4"/></symbol>
<symbol id="i-tower" viewBox="0 0 24 24"><path d="M6 3h3v2h2V3h2v2h2V3h3v6l-2 2 1 10H7l1-10-2-2z"/></symbol>
<symbol id="i-inhib" viewBox="0 0 24 24"><path fill-rule="evenodd" d="M12 1.5 20.5 12 12 22.5 3.5 12zm0 5.5L8 12l4 5 4-5z"/></symbol>
<symbol id="i-atakhan" viewBox="0 0 24 24"><path d="M3 2c1.5 6 4.5 9 9 9s7.5-3 9-9c1.5 8-1.5 14-9 20C4.5 16 1.5 10 3 2z"/></symbol>
<symbol id="i-minion" viewBox="0 0 24 24"><path d="M12 2 20 5.5V12c0 4.5-3.2 8-8 10-4.8-2-8-5.5-8-10V5.5z"/></symbol>
</svg>'''

OB_LEGEND = [("dragon", "드래곤"), ("grub", "공허 유충"), ("herald", "전령"), ("baron", "바론"), ("tower", "포탑"), ("inhib", "억제기")]


# ---------- 차트: 골드 흐름 ----------
def gold_chart():
    # 오브젝트 아이콘이 겹치면 아래로 쌓아요. 3줄 이상이면 그만큼 차트를 늘려서 시간 글자와 겹치지 않게 해요.
    xmax_ = dur / 60
    lastx_, nrows = {}, 1
    for o in objs:
        x_ = 64 + (1120 - 64 - 16) * (o["t"] / 60000) / xmax_
        r_ = 0
        while abs(lastx_.get(r_, -99) - x_) < 21:
            r_ += 1
        lastx_[r_] = x_
        nrows = max(nrows, r_ + 1)
    W, H = 1120, 380 + max(0, nrows - 2) * 22
    L, R, T, B = 64, 16, 66, 84 + max(0, nrows - 2) * 22
    ch = H - T - B
    xmax = dur / 60
    vals = [f["teamGoldDiff"] for f in flow] + [f["botGoldDiff"] for f in flow]
    step = 2500
    vmax = max(step, -(-max(vals) // step) * step)
    vmin = min(-step, (min(vals) // step) * step)

    def X(m):
        return L + (W - L - R) * m / xmax

    def Y(v):
        return T + ch * (vmax - v) / (vmax - vmin)

    pts = [(min(f["min"], xmax), f["teamGoldDiff"]) for f in flow]
    pts[-1] = (xmax, pts[-1][1])
    line = " ".join(f"{X(m):.1f},{Y(v):.1f}" for m, v in pts)
    area = f"{X(0):.1f},{Y(0):.1f} " + line + f" {X(xmax):.1f},{Y(0):.1f}"
    bot = " ".join(f"{X(min(f['min'], xmax)):.1f},{Y(f['botGoldDiff']):.1f}" for f in flow)
    g = [f'<svg class="chart" viewBox="0 0 {W} {H}" role="img" aria-label="분당 팀 골드 차이와 바텀 2대2 골드 차이">',
         '<defs><clipPath id="cp-pos"><rect x="0" y="0" width="%d" height="%.1f"/></clipPath>' % (W, Y(0)),
         '<clipPath id="cp-neg"><rect x="0" y="%.1f" width="%d" height="%d"/></clipPath></defs>' % (Y(0), W, H)]
    for a, b, lab in [(0, 14, "라인전"), (14, 25, "중반부"), (25, xmax, "후반부")]:
        g.append(f'<rect class="band{" band-alt" if lab == "중반부" else ""}" x="{X(a):.1f}" y="{T}" width="{X(b) - X(a):.1f}" height="{ch}"/>')
        g.append(f'<text class="ax-phase" x="{X(a) + 8:.1f}" y="{T + 16}">{lab}</text>')
    v = vmin
    while v <= vmax:
        cls = "grid grid-zero" if v == 0 else "grid"
        g.append(f'<line class="{cls}" x1="{L}" x2="{W - R}" y1="{Y(v):.1f}" y2="{Y(v):.1f}"/>')
        lab = "0" if v == 0 else (f"+{v / 1000:g}k" if v > 0 else f"−{abs(v) / 1000:g}k")
        g.append(f'<text class="ax" x="{L - 8}" y="{Y(v) + 4:.1f}" text-anchor="end">{lab}</text>')
        v += step
    for m in range(0, int(xmax) + 1, 5):
        g.append(f'<text class="ax" x="{X(m):.1f}" y="{H - 6}" text-anchor="middle">{m}:00</text>')
    g.append(f'<polygon class="area-pos" points="{area}" clip-path="url(#cp-pos)"/>')
    g.append(f'<polygon class="area-neg" points="{area}" clip-path="url(#cp-neg)"/>')
    g.append(f'<polyline class="ln-bot" points="{bot}"/>')
    g.append(f'<polyline class="ln-team" points="{line}"/>')
    for e in my_kills_ev:
        x = X(e["timestamp"] / 60000)
        g.append(f'<rect class="mk-kill" x="{x - 1.5:.1f}" y="{T - 52}" width="3" height="12"><title>{mmss(e["timestamp"])} 내 킬</title></rect>')
    for i, e in enumerate(my_deaths_ev, 1):
        x = X(e["timestamp"] / 60000)
        g.append(f'<line class="mk-death-line" x1="{x:.1f}" x2="{x:.1f}" y1="{T - 19}" y2="{T + ch}"/>')
        g.append(f'<rect class="mk-death" x="{x - 5:.1f}" y="{T - 29}" width="10" height="10"><title>{mmss(e["timestamp"])} {i}번째 죽음</title></rect>')
    g.append(f'<text class="ax-k" x="{L - 8}" y="{T - 42}" text-anchor="end">킬</text>')
    g.append(f'<text class="ax-k" x="{L - 8}" y="{T - 20}" text-anchor="end">죽음</text>')
    oy = T + ch + 10
    g.append(f'<text class="ax-k" x="{L - 8}" y="{oy + 14}" text-anchor="end">오브젝트</text>')
    lastx = {}
    for o in objs:
        x = X(o["t"] / 60000)
        row = 0
        while abs(lastx.get(row, -99) - x) < 21:
            row += 1
        lastx[row] = x
        y = oy + row * 22
        cls = "ob-ours" if o["ours"] else "ob-theirs"
        g.append(f'<g><title>{mmss(o["t"])} {esc(o["name"])} ({"우리 팀" if o["ours"] else "상대 팀"})</title>'
                 f'<use class="{cls}" href="#i-{OBJ_ICON.get(o["kind"], "tower")}" x="{x - 10:.1f}" y="{y}" width="20" height="20"/></g>')
    g.append("</svg>")
    return "".join(g)


# ---------- 지도: 죽은 곳/킬한 곳 ----------
def death_map():
    S = 460

    def P2(pos):
        return (pos["x"] + 120) / 14990 * S, S - (pos["y"] + 120) / 15100 * S
    g = [f'<svg class="map" viewBox="0 0 {S} {S}" role="img" aria-label="소환사의 협곡에서 내가 죽은 곳과 킬한 곳">',
         f'<image href="{MAP_IMG}" x="0" y="0" width="{S}" height="{S}" class="map-img"/>',
         f'<rect class="map-veil" x="0" y="0" width="{S}" height="{S}"/>']
    for e in my_kills_ev + my_assist_ev:
        x, y = P2(e["position"])
        solid = e in my_kills_ev
        rot = f'x="{x - 6.5:.1f}" y="{y - 6.5:.1f}" width="13" height="13" transform="rotate(45 {x:.1f} {y:.1f})"'
        g.append(f'<g><title>{mmss(e["timestamp"])} {"킬" if solid else "어시스트"}</title><rect class="{"mp-kill" if solid else "mp-assist"}" {rot}/></g>')
    for i, e in enumerate(my_deaths_ev, 1):
        x, y = P2(e["position"])
        g.append(f'<g><title>{mmss(e["timestamp"])} {i}번째 죽음</title><circle class="mp-death" cx="{x:.1f}" cy="{y:.1f}" r="12"/>'
                 f'<text class="mp-num" x="{x:.1f}" y="{y + 4.5:.1f}" text-anchor="middle">{i}</text></g>')
    g.append("</svg>")
    return "".join(g)


# ---------- 섹션 ----------
SECTIONS = [("01", "경기 요약"), ("02", "경기 흐름"), ("03", "라인전"), ("04", "죽음"),
            ("05", "팀 기록"), ("06", "빌드"), ("07", "체크리스트"), ("08", "메모")]


def josa(word, batchim="과", none="와"):
    """받침이 있으면 batchim(과/을/이), 없으면 none(와/를/가)을 붙인다."""
    ch = word[-1]
    if "가" <= ch <= "힣":
        return word + (batchim if (ord(ch) - 0xAC00) % 28 else none)
    return word + none


def section(no, body):
    title = dict(SECTIONS)[no]
    return (f'<section class="sec" id="s{no}"><header class="sec-head">'
            f'<span class="sec-no" aria-hidden="true">{no}</span><h2>{title}</h2></header>{body}</section>')


k, d, a = ME["kills"], ME["deaths"], ME["assists"]
kda_ratio = (k + a) / max(d, 1)
cs = ME["totalMinionsKilled"] + ME["neutralMinionsKilled"]
opp_cs = OPP["totalMinionsKilled"] + OPP["neutralMinionsKilled"]
dmg_share = A["basic"]["damageShare"]
kp = A["basic"]["killParticipation"]
OPP_KO = ko_champ(OPP)


def tile(label, value, sub, cmp=None):
    c = f'<span class="tile-cmp">{cmp}</span>' if cmp else ""
    return f'<div class="tile"><span class="label">{label}</span><span class="tile-value">{value}</span><span class="tile-sub">{sub}</span>{c}</div>'


def hero():
    win = ME["win"]
    import datetime as dt
    t = dt.datetime.fromtimestamp(info["gameStartTimestamp"] / 1000, dt.timezone(dt.timedelta(hours=9)))
    duo = next(p for p in team_rows[MY_TEAM] if p["teamPosition"] == "UTILITY")
    eduo = next(p for p in team_rows[300 - MY_TEAM] if p["teamPosition"] == "UTILITY")
    tiles = "".join([
        tile("KDA", f'{k}<i>/</i><span class="death">{d}</span><i>/</i>{a}', f"평점 {kda_ratio:.2f}", f"킬 관여 {kp}%"),
        tile("CS", f"{cs}", f"분당 {cs / mins:.1f}", f"{OPP_KO} {opp_cs}"),
        tile("챔피언 피해", num(ME["totalDamageDealtToChampions"]), f"팀 내 {dmg_share}%", f'{OPP_KO} {num(OPP["totalDamageDealtToChampions"])}'),
        tile("골드", num(ME["goldEarned"]), f"분당 {ME['goldEarned'] / mins:.0f}", f'{OPP_KO} {num(OPP["goldEarned"])}'),
        tile("15분 맞라인 골드", f'<span class="{"neg" if flow[15]["laneGoldDiff"] < 0 else ""}">{signed(flow[15]["laneGoldDiff"])}</span>', f"{josa(OPP_KO)} 비교", f'CS {signed(flow[15]["laneCsDiff"])}'),
        tile("시야 점수", str(ME["visionScore"]), f"와드 {ME['wardsPlaced']}개 설치", f"제어 와드 {A['basic']['controlWards']}개"),
    ])
    return f'''
<section class="hero {'is-win' if win else 'is-loss'}">
  <div class="stripes" aria-hidden="true"></div>
  <div class="hero-top">
    <div class="hero-id">
      {loadout(ME, big=True)}
      <div class="hero-title">
        <p class="hero-meta"><span>솔로랭크</span><span class="num">{t.month}.{t.day:02d} {t.hour:02d}:{t.minute:02d}</span><span>패치 {int(info["gameVersion"].split(".")[0]) + 10}.{info["gameVersion"].split(".")[1]}</span></p>
        <h1><span class="res">{"승리" if win else "패배"}</span><span class="dur">{dur // 60}:{dur % 60:02d}</span></h1>
        <p class="hero-match">
          {cimg(CHAMP, "sm")}{cimg(duo["championName"], "sm")}
          <span class="vs">VS</span>
          {cimg(OPP["championName"], "sm")}{cimg(eduo["championName"], "sm")}
        </p>
      </div>
    </div>
    <div class="hero-lp">
      <span class="lp-tier">{os.environ.get("RA_TIER", "플래티넘 4")}</span>
      <span class="lp-num">{os.environ.get("RA_LP", "30")}<small>LP</small></span>
    </div>
  </div>
  <div class="hero-items">{items_row(ME, "md")}</div>
  <div class="tiles">{tiles}</div>
</section>'''


LINKS_ON = MODE == "cdn" and os.environ.get("RA_NOLINK") != "1"  # RA_NOLINK=1: 다른 페이지로 가는 링크를 막아요(미리보기용)


def sitenav():
    tabs = [("경기 기록", "index.html", True), ("챔피언 노트", "champions.html", False), ("상성 노트", "matchups.html", False)]
    lis = "".join(f'<li><a class="{"on" if on else ""}" href="{"../" + href if LINKS_ON else "#"}">{t}</a></li>' for t, href, on in tabs)
    return f'<nav class="sitenav" aria-label="페이지"><ul>{lis}</ul></nav>'


def secnav():
    lis = "".join(f'<li><a href="#s{n}"><span class="num">{n}</span>{t}</a></li>' for n, t in SECTIONS)
    return f'<nav class="secnav" aria-label="섹션 이동"><ol>{lis}</ol></nav>'


def lede_html(t):
    """괄호 안 근거는 연한 글자로."""
    import re
    return re.sub(r"\(([^)]*)\)", lambda m: f'<span class="aside">({m.group(1)})</span>', esc(t))


def sec_summary():
    fixes = "".join(
        f'<li class="fix"><span class="fix-no">{i}</span><div><h3>{esc(f["title"])}</h3><p>{esc(f["body"])}</p></div></li>'
        for i, f in enumerate(FB["keyFixes"], 1))
    body = f'''
<div class="sum-grid">
  <p class="lede">{lede_html(FB["summary"])}</p>
  <ol class="fixes">{fixes}</ol>
  <aside class="takeaway"><span class="label">다음 판 목표</span><p>{esc(FB["takeaway"])}</p></aside>
</div>'''
    return section("01", body)


# ---------- 유불리 운영 / 집중력 ----------
def swings(th=1500):
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
    out = []
    for (m0, v0), (m1, v1) in zip(piv, piv[1:]):
        a, b = m0 * 60000, m1 * 60000 if m1 != pts[-1][0] else dur * 1000 + 1
        out.append({"m0": m0, "m1": m1, "delta": v1 - v0,
                    "kills": sum(1 for e in my_kills_ev if a <= e["timestamp"] < b),
                    "deaths": sum(1 for e in my_deaths_ev if a <= e["timestamp"] < b)})
    return out


def focus_stats():
    ts = [e["timestamp"] for e in my_deaths_ev]
    chain = sum(1 for a, b in zip(ts, ts[1:]) if b - a <= 120000)
    cut = next((f["min"] for f in flow if f["teamGoldDiff"] <= -3000), None)
    def cs_at(m):
        return next(f["cs"] for f in flow if f["min"] == m)
    end_m = flow[-1]["min"]
    before = cs_at(cut) / cut if cut else None
    after = (cs_at(end_m) - cs_at(cut)) / max(dur / 60 - cut, 1) if cut else None
    alone = sum(1 for x in A["deaths"] if not x["alliesNear"] or x["fight"]["size"] == 1)
    return chain, cut, before, after, alone


def flow_extra():
    sw = swings()
    total = dur / 60
    strip = "".join(
        f'<span class="sw-seg {"up" if w["delta"] > 0 else "down"}" style="width:{(min(w["m1"], total) - w["m0"]) / total * 100:.2f}%" '
        f'title="{w["m0"]}~{w["m1"]}분 {signed(w["delta"])}"></span>' for w in sw)
    notes = FB.get("swings", {})
    rows = "".join(f'''<li class="{"up" if w["delta"] > 0 else "down"}">
  <span class="sw-time num">{w["m0"]}~{min(w["m1"], dur // 60)}분</span>
  <span class="sw-kind">{"따라잡음" if w["delta"] > 0 else "벌어짐"} <b class="num">{signed(w["delta"])}</b></span>
  <span class="sw-me">킬 <b class="num{" k" if w["kills"] else ""}">{w["kills"]}</b> 죽음 <b class="num{" d" if w["deaths"] else ""}">{w["deaths"]}</b></span>
  <span class="sw-note">{esc(notes.get(str(w["m0"]), ""))}</span></li>''' for w in sw)
    peak = max(flow, key=lambda f: f["teamGoldDiff"])
    chain, cut, before, after, alone = focus_stats()
    cs_txt = f'<b class="num">{before:.1f}</b><i>→</i><b class="num">{after:.1f}</b>' if cut else '<b class="num">-</b>'
    return f'''
<div class="flow-extra">
  <div class="panel">
    <div class="panel-head"><h3>유불리 운영</h3><span class="label">가장 앞섰을 때 <b class="num">{signed(peak["teamGoldDiff"])}</b> ({peak["min"]}분)</span></div>
    <div class="sw-strip">{strip}</div>
    <ol class="sw-list">{rows}</ol>
  </div>
  <div class="panel focus">
    <div class="panel-head"><h3>집중력</h3></div>
    <dl class="focus-stats">
      <div><dt>죽고 2분 안에 또 죽음</dt><dd><b class="num{" d" if chain else ""}">{chain}</b>번</dd></div>
      <div><dt>{f"분당 CS, {cut}분 전과 후" if cut else "분당 CS"}</dt><dd>{cs_txt}</dd></div>
      <div><dt>혼자 잡힌 죽음</dt><dd><b class="num{" d" if alone else ""}">{alone}</b>번</dd></div>
    </dl>
    <p class="body">{esc(FB.get("focus", ""))}</p>
  </div>
</div>'''


def sec_flow():
    mom = "".join(
        f'<li class="{"m-key" if m.get("key") else ""} {("m-crit-" + m["crit"]) if m.get("crit") else ""}"><time>{m["t"]}</time><span>{esc(m["text"])}</span></li>'
        for m in FB["moments"])
    gd14 = flow[14]["teamGoldDiff"]; gd25 = flow[25]["teamGoldDiff"]; gdmin = min(f["teamGoldDiff"] for f in flow)
    shown = {OBJ_ICON.get(o["kind"], "tower") for o in objs}
    obl = ("".join(f'<li>{gi(i)}{n}</li>' for i, n in OB_LEGEND if i in shown)
           + '<li class="sep" aria-hidden="true"></li>'
           + f'<li class="lg-ours">{gi("tower")}<span class="muted">우리 팀</span></li><li class="lg-theirs">{gi("tower")}<span class="muted">상대 팀</span></li>')
    body = f'''
<div class="panel">
  <div class="panel-head">
    <h3>분당 골드 차이 <span class="h-final">(최종 <b class="num{" neg" if flow[-1]["teamGoldDiff"] < 0 else ""}">{signed(flow[-1]["teamGoldDiff"])}</b>)</span></h3>
    <ul class="legend">
      <li><span class="lg lg-pos"></span>우리 팀 앞섬</li>
      <li><span class="lg lg-neg"></span>상대 팀 앞섬</li>
      <li><span class="lg lg-team"></span>팀 전체</li>
      <li><span class="lg lg-bot"></span>바텀 2대2</li>
      <li><span class="lg lg-death"></span>내가 죽음</li>
      <li><span class="lg lg-kill"></span>내 킬</li>
    </ul>
  </div>
  <div class="chart-wrap">{gold_chart()}</div>
  <div class="flow-foot">
    <div class="mini-stats">
      <div><span class="label">14분 팀 골드</span><span class="ms-val {"neg" if gd14 < 0 else ""}">{signed(gd14)}</span></div>
      <div><span class="label">25분 팀 골드</span><span class="ms-val {"neg" if gd25 < 0 else ""}">{signed(gd25)}</span></div>
      <div><span class="label">가장 크게 밀렸을 때</span><span class="ms-val {"neg" if gdmin < 0 else ""}">{signed(gdmin)}</span></div>
    </div>
    <ul class="ob-legend">{obl}</ul>
  </div>
</div>
{flow_extra()}
<h3 class="sub-h">주요 순간</h3>
<ol class="moments">{mom}</ol>'''
    return section("02", body)


def bf_row(label, mine, theirs, fmt=num, neutral=False):
    tot = max(mine + theirs, 1)
    lw = mine / tot * 100 if mine + theirs else 50
    win = "" if neutral else ("mine" if mine > theirs else ("theirs" if theirs > mine else ""))
    return (f'<div class="bf-row {win}"><span class="bf-v bf-l">{fmt(mine)}</span>'
            f'<div class="bf-bar"><span class="bf-a" style="width:{lw:.1f}%"></span><span class="bf-b" style="width:{100 - lw:.1f}%"></span></div>'
            f'<span class="bf-v bf-r">{fmt(theirs)}</span><span class="bf-label">{label}</span></div>')


def solo(killer, victim, until=14 * 60000):
    return sum(1 for e in kills_ev if e["killerId"] == killer and e["victimId"] == victim
               and not e.get("assistingParticipantIds") and e["timestamp"] < until)


def sup_block(L):
    """라인전 동안 아군 서폿이 바텀에 있었는지(1분마다)와, 있을 때/없을 때로 나눈 CS."""
    cells = "".join(f'<span class="{"in" if v else ""}">{m}</span>' for m, v in L["supportAtBot"].items())
    w, wo = L["csWithSupport"], L["csWithoutSupport"]
    return f'''
    <div class="sup">
      <h3 class="panel-title">아군 서폿 위치</h3>
      <div class="sup-strip">{cells}</div>
      <div class="sup-foot"><ul class="legend"><li><span class="lg lg-sup-in"></span>바텀에 있음</li><li><span class="lg lg-sup-out"></span>바텀에 없음</li></ul></div>
      <div class="sup-cs">
        <div><span class="label">서폿이 있을 때 CS</span><b>{w["me"]} : {w["opp"]}</b></div>
        <div><span class="label">서폿이 없을 때 CS</span><b>{wo["me"]} : {wo["opp"]}</b></div>
      </div>
    </div>'''


def bot_kills_fact(L):
    """14분까지 바텀 근처에서 맞라인 원딜이 죽은 횟수 : 내가 죽은 횟수 (서폿/정글 막타 포함)"""
    k = L["botAdcKills"]
    cls = "num pos" if k["opp"] > k["me"] else "num"
    return (f'<div><span class="label" title="14분까지 바텀 근처에서 원딜이 죽은 횟수. 서폿이 막타를 친 것도 셉니다.">바텀 원딜 킬</span>'
            f'<b class="{cls}">{k["opp"]} : {k["me"]}</b></div>')


def sec_lane():
    m10, o10, m15, o15 = pf(10, my_pid), pf(10, opp_pid), pf(15, my_pid), pf(15, opp_pid)
    L = A.get("lane")  # analyze.py가 원딜 판에만 만들어요. 없으면 예전처럼 솔로킬을 보여요.
    rows = "".join([
        bf_row("10분 CS", m10["cs"], o10["cs"]),
        bf_row("10분 골드", m10["gold"], o10["gold"]),
        bf_row("10분 경험치", m10["xp"], o10["xp"]),
        bf_row("15분 CS", m15["cs"], o15["cs"]),
        bf_row("15분 골드", m15["gold"], o15["gold"]),
        bf_row("15분 경험치", m15["xp"], o15["xp"]),
    ])
    lv = A["levels"]
    first2 = tsec(lv["2"]["me"]) < tsec(lv["2"]["opp"])
    sk_me, sk_opp = solo(my_pid, opp_pid), solo(opp_pid, my_pid)
    heads = "".join(f'<span class="lv-n">{n}</span>' for n in lv)
    me_cells = "".join(f'<span class="{"ahead" if tsec(v["me"]) < tsec(v["opp"]) else ""}">{v["me"]}</span>' for v in lv.values())
    op_cells = "".join(f'<span class="{"behind" if tsec(v["opp"]) < tsec(v["me"]) else ""}">{v["opp"]}</span>' for v in lv.values())
    body = f'''
<div class="lane-grid">
  <div class="panel">
    <div class="bf-head">
      <span class="bf-who">{cimg(CHAMP, "sm")}<span class="me-name">{ME_KO}</span></span>
      <span class="bf-who">{OPP_KO}{cimg(OPP["championName"], "sm")}</span>
    </div>
    <div class="bf">{rows}</div>{sup_block(L) if L else ""}
  </div>
  <div class="panel">
    <div class="lane-facts">
      <div><span class="label">2레벨 선점</span><b class="{"me-name" if first2 else ""}">{ME_KO if first2 else OPP_KO}</b></div>
      {bot_kills_fact(L) if L else f'<div><span class="label">라인전 솔로킬</span><b class="num">{sk_me} : {sk_opp}</b></div>'}
      <div><span class="label">최대 CS 우위</span><b class="pos">+{A["basic"]["maxCsAdvantage"]}</b></div>
    </div>
    <h3 class="panel-title">레벨 도달 시간</h3>
    <div class="lv-grid"><span class="lv-h lv-n">레벨</span>{heads}<span class="lv-h">{ME_KO}</span>{me_cells}<span class="lv-h">{OPP_KO}</span>{op_cells}</div>
    <p class="body">{esc(FB["laneText"])}</p>
  </div>
</div>'''
    return section("03", body)


def chip_phase(sec):
    return f'<span class="chip chip-line">{phase(sec)}</span>'


def nm(n):
    return n.split("(")[0]


def damage_bar(dmg):
    tot = sum(v for _, v in dmg) or 1
    segs = "".join(f'<span class="dmg-seg dmg-{i}" style="width:{v / tot * 100:.1f}%" title="{esc(nm(n))} {v:,}"></span>' for i, (n, v) in enumerate(dmg))
    labels = "".join(f'<li>{cimg(key_of(n), "xs", title=nm(n))}<span>{esc(nm(n))}</span><b>{v:,}</b></li>' for n, v in dmg)
    return f'<div class="dmg"><div class="dmg-bar">{segs}</div><ul class="dmg-list">{labels}</ul></div>'


def lost_list(lost):
    if not lost:
        return '<span class="muted">없음</span>'
    return "".join(f'<span class="lost">{esc(x)}</span>' for x in lost)


def faces(lst, size="xs"):
    if not lst:
        return '<span class="muted">없음</span>'
    return "".join(cimg(key_of(n), size, title=nm(n)) for n in lst)


SPELL_VERDICT = {"held": ("들고 죽음", "chip-bad"), "used_before": ("직전에 씀", "chip-line"),
                 "already_down": ("쿨타임", "chip-line"), "uncertain": ("판단 보류", "chip-unknown"),
                 "not_visible": ("확인 못 함", "chip-unknown"), "unknown": ("확인 못 함", "chip-unknown")}


NO_RESULT = {None, "not_visible", "unknown"}  # 기록 프로그램이 스펠 칸을 못 본 경우


def death_spells(x):
    """죽을 때 스펠 2개의 상태.
    결과가 있으면 스펠마다 칩. 결과가 없으면 칩 대신 글자만(no-rec):
    게임 중 기록이 아예 없으면 '기록 없음', 기록은 있는데 스펠 칸을 못 봤으면 '확인 못 함'."""
    ids = [ME["summoner1Id"], ME["summoner2Id"]]
    # 스펠 판정은 분석 결과의 death["live"]["spells"]에 있어요 (예전에는 death["spells"]만 봐서 항상 '기록 없음'이 나왔어요)
    sps = x.get("spells") or (x.get("live") or {}).get("spells") or []
    live = {str(sp.get("key")): sp.get("verdict") for sp in sps}
    icons = []
    for sid in ids:
        src, name = spell_img(sid)
        icons.append((f'<img class="ic ic-xs" src="{src}" alt="{esc(name)}" title="{esc(name)}">', live.get(SPELL_KEY[str(sid)])))
    if not live:
        return "".join(i for i, _ in icons) + '<span class="no-rec">기록 없음</span>'
    if all(v in NO_RESULT for _, v in icons):
        return "".join(i for i, _ in icons) + '<span class="no-rec">확인 못 함</span>'
    out = []
    for icon, v in icons:
        if v in NO_RESULT:
            out.append(f'<span class="d-spell">{icon}<span class="no-rec">확인 못 함</span></span>')
        else:
            lab, cls = SPELL_VERDICT.get(v, ("확인 못 함", "chip-unknown"))
            out.append(f'<span class="d-spell">{icon}<span class="chip {cls}">{lab}</span></span>')
    return "".join(out)


def sec_deaths():
    D = {x["t"]: x for x in A["deaths"]}
    idx = {mmss(e["timestamp"]): i for i, e in enumerate(my_deaths_ev, 1)}
    cards = []
    for kd in FB["keyDeaths"]:
        x = D[kd["t"]]
        roams = "".join(f'<li>{cimg(key_of(r["who"]), "xs")}<span><span class="num">{r["minuteMark"]}</span> {esc(r["wasAt"])}</span></li>' for r in x["roams"])
        lg = (x.get("live") or {}).get("gold")  # 게임 중 기록이 있으면 실제로 들고 있던 골드를 써요
        gold = f'{lg:,}' if lg is not None else (f'{x["approxGold"]:,}' if x["approxGold"] is not None else "계산 불가")
        cards.append(f'''
<article class="dcard">
  <header class="dcard-head">
    <span class="dnum">{idx.get(kd["t"], "")}</span>
    <time>{x["t"]}</time>
    {chip_phase(tsec(x["t"]))}
    <span class="dzone">{esc(x["zone"])}</span>
  </header>
  <div class="dcard-kill">
    <div class="kchain">{cimg(key_of(x["killer"]), "md")}{f'<span class="kchain-plus">{faces(x["assists"])}</span>' if x["assists"] else ""}</div>
    <span class="karrow" aria-hidden="true"></span>
    <div class="kvictim">{cimg(CHAMP, "md", "is-dead")}</div>
  </div>
  <dl class="dfacts">
    <div><dt>근처 아군</dt><dd>{faces(x["alliesNear"])}</dd></div>
    <div><dt>근처 적</dt><dd>{faces(x["enemiesNear"])}</dd></div>
    <div><dt>보유 골드</dt><dd class="num">{gold}</dd></div>
    <div><dt>스펠</dt><dd class="d-spells">{death_spells(x)}</dd></div>
    <div><dt>팀 골드 차이</dt><dd class="num {"neg" if x["teamGoldDiff"] < 0 else ""}">{signed(x["teamGoldDiff"])}</dd></div>
    <div><dt title="죽은 뒤 90초 안에 잃은 포탑/오브젝트">손해</dt><dd>{lost_list(x["lostAfter"])}</dd></div>
  </dl>
  {f'<ul class="roams"><li class="roams-h">합류한 적</li>{roams}</ul>' if roams else '<div class="roams-slot"></div>'}
  <div class="dcard-dmg"><span class="label">받은 피해</span>{damage_bar(x["damage"])}</div>
  <div class="dcard-text">
    <p><b>상황</b><span>{esc(kd["what"])}</span></p>
    <p><b>근거</b><span>{esc(kd["evidence"])}</span></p>
    <p class="next"><b>개선점</b><span>{esc(kd["next"])}</span></p>
  </div>
</article>''')
    rows = []
    for t, txt in FB["otherDeaths"].items():
        x = D[t]
        rows.append(f'<tr><td><span class="dnum">{idx.get(t, "")}</span></td><td class="num">{t}</td><td>{chip_phase(tsec(t))}</td>'
                    f'<td class="faces">{cimg(key_of(x["killer"]), "xs")}{faces(x["assists"]) if x["assists"] else ""}</td>'
                    f'<td>{esc(txt)}</td><td>{lost_list(x["lostAfter"])}</td></tr>')
    ph = {"라인전": 0, "중반부": 0, "후반부": 0}
    for e in my_deaths_ev:
        ph[phase(e["timestamp"] / 1000)] += 1
    lost_n = sum(1 for x in A["deaths"] if x["lostAfter"])
    alone = sum(1 for x in A["deaths"] if not x["alliesNear"])
    roam_n = sum(1 for x in A["deaths"] if any(r["distance"] > 4000 for r in x["roams"]))
    def zone_kind(z):
        return "강가" if "강가" in z else "정글" if "정글" in z else "본진" if "본진" in z else "라인"
    zk = {"라인": 0, "강가": 0, "정글": 0, "본진": 0}
    for x in A["deaths"]:
        zk[zone_kind(x["zone"])] += 1
    zone_cells = "".join(f'<div><span class="label">{z}</span><b>{n}</b></div>' for z, n in zk.items())
    spans = [("라인전", 0, 14 * 60), ("중반부", 14 * 60, 25 * 60), ("후반부", 25 * 60, dur)]
    segs = "".join(f'<div class="ptl-seg" style="flex:{b2 - a2}"><div class="ptl-top"><span class="ptl-name">{lab}</span>'
                   f'<span class="ptl-n">{ph[lab]}<small>번</small></span></div><span class="ptl-range">{a2 // 60}:00 ~ {b2 // 60}:{b2 % 60:02d}</span></div>'
                   for lab, a2, b2 in spans)
    phase_bar = f'<div class="ptl"><div class="ptl-bar">{segs}</div></div>'
    other = ('''<h3 class="sub-h">나머지 죽음</h3>
<div class="table-wrap"><table class="tbl">
<thead><tr><th>#</th><th>시간</th><th>구간</th><th>처치</th><th>내용</th><th title="죽은 뒤 90초 안에 잃은 포탑/오브젝트">손해</th></tr></thead>
<tbody>''' + "".join(rows) + "</tbody></table></div>") if rows else ""
    body = f'''
<div class="death-top">
  <div class="panel map-panel">
    {death_map()}
    <ul class="legend legend-map">
      <li><span class="lg lg-mdeath"></span>죽은 곳</li>
      <li><span class="lg lg-mkill"></span>킬</li>
      <li><span class="lg lg-massist"></span>어시스트</li>
    </ul>
  </div>
  <div class="death-stats">
    <div class="big-stat"><span class="big-n">{d}</span><span class="big-l">데스</span></div>
    {phase_bar}
    <div class="zones"><span class="label">죽은 위치</span><div class="zone-row">{zone_cells}</div></div>
    <ul class="dlist-stats">
      <li><span class="ds-n">{lost_n}</span><span>죽은 뒤 90초 안에 포탑/오브젝트를 잃음</span></li>
      <li title="1분 전에 4,000 거리 넘게 떨어져 있던 적"><span class="ds-n">{roam_n}</span><span>멀리서 합류한 적에게 죽음</span></li>
      <li><span class="ds-n">{alone}</span><span>근처에 아군 없이 죽음</span></li>
    </ul>
  </div>
</div>
<h3 class="sub-h">주요 죽음</h3>
<div class="dcards">{''.join(cards)}</div>
{other}'''
    return section("04", body)


def sec_team():
    mx = max(p["totalDamageDealtToChampions"] for p in P)

    def team_table(tid):
        rows = team_rows[tid]
        win = rows[0]["win"]
        trs = []
        kp_of = lambda p: (p["kills"] + p["assists"]) / max(team_kills[tid], 1)
        cs_of = lambda p: p["totalMinionsKilled"] + p["neutralMinionsKilled"]
        top_kp, top_gold, top_cs = max(map(kp_of, rows)), max(p["goldEarned"] for p in rows), max(map(cs_of, rows))
        top_dmg = max(p["totalDamageDealtToChampions"] for p in rows)
        hi = lambda on: " t-top" if on else ""
        for p in rows:
            me = p["participantId"] == my_pid
            dm = p["totalDamageDealtToChampions"]
            kdr = (p["kills"] + p["assists"]) / max(p["deaths"], 1)
            kpp = round((p["kills"] + p["assists"]) / max(team_kills[tid], 1) * 100)
            trs.append(f'''<tr class="{"is-me" if me else ""}">
<td class="t-pos">{POS_KO[p["teamPosition"]]}</td>
<td class="t-champ-td"><div class="t-champ">{loadout(p)}<span class="t-name">{esc(ko_champ(p))}</span></div></td>
<td class="t-kda"><span class="num">{p["kills"]} / {p["deaths"]} / {p["assists"]}</span><span class="t-sub">평점 {kdr:.2f}, 관여 <span class="{hi(kp_of(p) == top_kp).strip()}">{kpp}%</span></span></td>
<td class="t-dmg"><span class="num{hi(dm == top_dmg)}">{num(dm)}</span><span class="t-bar"><i style="width:{dm / mx * 100:.1f}%"></i></span></td>
<td class="num{hi(p["goldEarned"] == top_gold)}">{num(p["goldEarned"])}</td>
<td class="num{hi(cs_of(p) == top_cs)}">{cs_of(p)}</td>
<td class="num">{p["visionScore"]}</td>
<td class="t-items">{items_row(p, "xs")}</td></tr>''')
        name = "우리 팀" if tid == MY_TEAM else "상대 팀"
        return f'''<div class="team {"team-ours" if tid == MY_TEAM else "team-theirs"}">
<div class="team-head"><span class="team-name">{name}</span><span class="chip {"chip-pos" if win else "chip-bad"}">{"승리" if win else "패배"}</span>
<span class="team-k num">{team_kills[tid]}킬</span></div>
<div class="table-wrap"><table class="tbl tbl-team"><colgroup><col class="c-pos"><col class="c-champ"><col class="c-kda"><col class="c-dmg"><col class="c-gold"><col class="c-cs"><col class="c-vis"><col class="c-items"></colgroup><thead><tr><th></th><th>챔피언</th><th>KDA</th><th>챔피언 피해</th><th>골드</th><th>CS</th><th>시야</th><th class="t-items">아이템</th></tr></thead>
<tbody>{''.join(trs)}</tbody></table></div></div>'''
    us, th = MY_TEAM, 300 - MY_TEAM

    def tot(f):
        return sum(f(p) for p in team_rows[us]), sum(f(p) for p in team_rows[th])
    comp_rows = ([
        bf_row("킬", team_kills[us], team_kills[th]),
        bf_row("골드", *tot(lambda p: p["goldEarned"])),
        bf_row("챔피언 피해", *tot(lambda p: p["totalDamageDealtToChampions"])),
        bf_row("받은 피해", *tot(lambda p: p["totalDamageTaken"]), neutral=True),
        bf_row("CS", *tot(lambda p: p["totalMinionsKilled"] + p["neutralMinionsKilled"])),
        bf_row("시야 점수", *tot(lambda p: p["visionScore"])),
        bf_row("포탑", team_obj[us]["tower"]["kills"], team_obj[th]["tower"]["kills"]),
        bf_row("드래곤", team_obj[us]["dragon"]["kills"], team_obj[th]["dragon"]["kills"]),
        bf_row("공허 유충", team_obj[us]["horde"]["kills"], team_obj[th]["horde"]["kills"]),
        bf_row("바론", team_obj[us]["baron"]["kills"], team_obj[th]["baron"]["kills"]),
    ])
    head = '<div class="bf-head"><span class="bf-who">우리 팀</span><span class="bf-who">상대 팀</span></div>'
    cols = "".join(f'<div>{head}<div class="bf">{"".join(comp_rows[i:i + 5])}</div></div>' for i in (0, 5))
    body = f'''
<div class="panel team-cmp"><div class="bf-team">{cols}</div></div>
{team_table(us)}
{team_table(th)}'''
    return section("05", body)


def item_timeline():
    """완성 아이템을 시간 축 위에 놓아서 나와 맞라인 상대의 성장 속도를 바로 비교한다."""
    def pos(t):
        return t / (dur * 1000) * 100

    def row(purch, key, label, cls, extra=""):
        done = [(t, i) for t, i in purch if is_complete(i)]
        its = "".join(f'<div class="itl-it" style="left:{pos(t):.2f}%">{iimg(i, "sm")}<time>{mmss(t)}</time></div>' for t, i in done)
        return f'<div class="itl-row {cls}"><div class="itl-who">{cimg(key, "sm")}<span class="{"me-name" if cls == "mine" else ""}">{label}</span></div><div class="itl-track">{extra}{its}</div></div>', done
    mine = [(t, i) for t, i in my_purch if is_complete(i)]
    gap = ""
    if len(mine) >= 2:
        # 피드백 글에서 짚은 구간을 표시해요. 'gapAfter'가 n이면 n번째와 n+1번째 완성 아이템 사이 (기본 1)
        j = min(int(FB.get("build", {}).get("gapAfter", 1)) - 1, len(mine) - 2)
        (t1, _), (t2, _) = mine[j], mine[j + 1]
        gap = (f'<span class="itl-gap" style="left:{pos(t1):.2f}%;width:{pos(t2) - pos(t1):.2f}%" title="완성 아이템 사이 시간"></span>'
               f'<span class="itl-gap-l" style="left:{(pos(t1) + pos(t2)) / 2:.2f}%">{mmss(t2 - t1)}</span>')
    r1, _ = row(my_purch, CHAMP, ME_KO, "mine", gap)
    r2, _ = row(opp_purch, OPP["championName"], OPP_KO, "theirs")
    ticks = "".join(f'<span style="left:{m * 60000 / (dur * 1000) * 100:.2f}%">{m}:00</span>' for m in range(0, int(dur // 60) + 1, 5))
    return f'<div class="itl">{r1}{r2}<div class="itl-axis"><div></div><div>{ticks}</div></div></div>'


def buy_list(purch):
    cells = []
    for g in groups(purch):
        ic = "".join(iimg(i, "md", "is-core") if is_complete(i) else iimg(i, "xs") for i in g["items"])
        cells.append(f'<li><div class="bt-items">{ic}</div><time>{mmss(g["t0"])}</time></li>')
    return f'<ol class="bt-list">{"".join(cells)}</ol>'


def sec_build():
    sel = ME["perks"]["styles"]
    prim, sub = sel[0], sel[1]

    def rimg(perk, size):
        n, pth = PERK[perk["perk"]]
        return f'<img class="ic {size} ic-rune" src="{perk_img(pth, n)}" alt="{esc(n)}" title="{esc(n)}">', n
    pn, pp = STYLE[prim["style"]]
    sn, sp = STYLE[sub["style"]]
    key_i, key_n = rimg(prim["selections"][0], "ic-lg")

    def cell(x, cls=""):
        i, n = rimg(x, "ic-md")
        return f'<div class="r-cell {cls}">{i}<span>{esc(n)}</span></div>'
    mincells = "".join(cell(x, "pmin") for x in prim["selections"][1:])
    subcells = "".join(cell(x, "psub s1" if j == 0 else "psub") for j, x in enumerate(sub["selections"]))
    sh = ME["perks"]["statPerks"]
    shards = "".join(f'<img class="ic ic-rune" src="{shard_img(s)[0]}" alt="{shard_img(s)[1]}" title="{shard_img(s)[1]}">' for s in [sh["offense"], sh["flex"], sh["defense"]])
    s1, n1 = spell_img(ME["summoner1Id"])
    s2, n2 = spell_img(ME["summoner2Id"])
    casts = {x["name"]: x["casts"] for x in A["spells"]}
    sk = A["skills"]["casts"]
    cdet = json.load(open(os.path.join(DATA, f"dd_champ_{CHAMP}.json"), encoding="utf-8"))["data"][CHAMP]["spells"]
    kimgs = [x["image"]["full"] for x in cdet]
    knames = [x["name"] for x in cdet]
    skills = "".join(
        f'<li><span class="sk-k"><img class="ic ic-xs" src="{skill_img(kimgs[i])}" alt="" title="{knames[i]}">{"QWER"[i]}</span>'
        f'<b>{sk[i]}</b><span class="muted">분당 {sk[i] / mins:.1f}</span></li>' for i in range(4))
    fb = FB["build"]

    def note(t):
        return f'<p class="body">{esc(t)}</p>' if t else ""
    body = f'''
<div class="panel">
  <div class="panel-head"><h3>완성 아이템 시점</h3></div>
  {item_timeline()}
  {note(fb["아이템"])}
  <div class="buys"><h3 class="panel-title">전체 구매 순서</h3>{buy_list(my_purch)}</div>
</div>
<div class="build-grid">
  <div class="panel">
    <h3 class="panel-title">룬</h3>
    <div class="runes">
      <div class="r-h p"><img class="ic ic-xs ic-rune" src="{perk_img(pp, pn)}" alt="">{pn}</div>
      <div class="r-h s"><img class="ic ic-xs ic-rune" src="{perk_img(sp, sn)}" alt="">{sn}</div>
      <div class="r-big p">{key_i}<span>{esc(key_n)}</span></div>
      {subcells}
      {mincells}
      <div class="r-shards">{shards}</div>
    </div>
    {note(fb["룬"])}
  </div>
  <div class="panel">
    <h3 class="panel-title">소환사 주문</h3>
    <ul class="spells">
      <li><img class="ic ic-md" src="{s1}" alt=""><span>{n1}</span><b>{casts.get(n1, 0)}<small>번</small></b></li>
      <li><img class="ic ic-md" src="{s2}" alt=""><span>{n2}</span><b>{casts.get(n2, 0)}<small>번</small></b></li>
    </ul>
    {note(fb["소환사 주문"])}
    <h3 class="panel-title panel-gap">스킬 사용</h3>
    <ul class="skills">{skills}</ul>
    <p class="body small">논타깃 스킬 적중 {A["skills"]["skillshotsHit"]}번, 피한 스킬 {A["skills"]["skillshotsDodged"]}번</p>
  </div>
</div>'''
    return section("06", body)


def sec_check():
    MARK = {"good": ("좋음", "chip-pos"), "mid": ("보통", "chip-mid"), "bad": ("아쉬움", "chip-bad")}
    cnt = {k: 0 for k in MARK}
    for c in FB["checklist"]:
        if c["mark"] in cnt:
            cnt[c["mark"]] += 1
    rows = "".join(
        f'<li class="ck ck-{c["mark"]}"><span class="ck-no">{i:02d}</span>'
        + (f'<span class="chip {MARK[c["mark"]][1]}">{MARK[c["mark"]][0]}</span>' if c["mark"] in MARK else '')
        + f'<h3>{esc(c["name"])}</h3><p>{esc(c["why"])}</p></li>' for i, c in enumerate(FB["checklist"], 1))
    summ = "".join(f'<li><span class="chip {MARK[k][1]}">{MARK[k][0]}</span><b>{v}</b></li>' for k, v in cnt.items())
    return section("07", f'<ul class="ck-sum">{summ}</ul><ol class="cklist">{rows}</ol>')


def sec_memo():
    m = FB.get("memo") or ""
    body = f'<div class="memo"><p>{esc(m)}</p></div>' if m else '<div class="memo is-empty"><p>이 판은 메모가 없어요.</p></div>'
    return section("08", body)


SPY = '''<script>
(() => {
  const nav = document.querySelector('.secnav ol');
  const links = [...nav.querySelectorAll('a')];
  const byId = new Map(links.map(a => [a.getAttribute('href').slice(1), a]));
  const set = id => {
    links.forEach(l => l.classList.toggle('on', l === byId.get(id)));
    const a = byId.get(id);
    if (a) nav.scrollTo({ left: a.offsetLeft - 16, behavior: 'smooth' });
  };
  const io = new IntersectionObserver(es => es.forEach(e => e.isIntersecting && set(e.target.id)),
    { rootMargin: '-40% 0px -55% 0px' });
  document.querySelectorAll('section.sec').forEach(s => io.observe(s));
})();
</script>'''


# ---------- 글꼴 ----------
FONT_DIR = os.path.join(ROOT, "tools", "fonts")
CSS = open(os.path.join(HERE, "report.css"), encoding="utf-8").read()


def page():
    head_fonts = ""
    if MODE == "cdn":
        head_fonts = ('<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wdth,wght@62..125,100..900&display=swap">'
                      '<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.min.css">')
    body = (hero() + secnav() + sec_summary() + sec_flow() + sec_lane() + sec_deaths() + sec_team() + sec_build() + sec_check() + sec_memo())
    return f'''<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{ME_KO} {"승리" if ME["win"] else "패배"} 리포트</title>
{head_fonts}
<style>/*FONTS*/
{CSS}</style>
</head>
<body>
{SPRITE}
<main class="wrap">
{sitenav()}
{body}
<div class="page-end"></div>
</main>
{SPY}
</body>
</html>'''


def embed(out):
    """local 모드: 페이지에 쓰인 글자만 남긴 글꼴을 data: 주소로 넣는다."""
    from fontTools import subset
    import re, io
    text = re.sub(r"<[^>]+>", " ", out) + "".join(chr(c) for c in range(32, 127)) + "−±→…—"
    faces = []
    for fam, path, rng in [
        ("Pretendard Variable", os.path.join(FONT_DIR, "PretendardVariable.woff2"), "45 920"),
        ("Archivo", os.path.join(FONT_DIR, "archivo-latin-wdth-normal.woff2"), "100 900"),
    ]:
        opts = subset.Options(); opts.flavor = "woff2"; opts.layout_features = ["*"]
        f = subset.load_font(path, opts)
        s = subset.Subsetter(opts); s.populate(text=text); s.subset(f)
        bio = io.BytesIO(); subset.save_font(f, bio, opts)
        b64 = base64.b64encode(bio.getvalue()).decode()
        st = "font-stretch:62% 125%;" if fam == "Archivo" else ""
        faces.append(f"@font-face{{font-family:'{fam}';src:url(data:font/woff2;base64,{b64}) format('woff2');font-weight:{rng};{st}font-display:swap}}")
        print(fam, "subset", len(bio.getvalue()) // 1024, "KB")
    return out.replace("/*FONTS*/", "".join(faces))


if __name__ in ("__main__", "ds"):
    out = page()
    if MODE != "cdn":
        out = embed(out)
    open(os.path.join(HERE, OUT_NAME or ("index.html" if MODE != "cdn" else "index_cdn.html")), "w", encoding="utf-8").write(out)
    print("written", len(out) // 1024, "KB")
