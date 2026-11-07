"""디자인 시스템 artifact 파일(v4)을 만든다.
- tokens.json: report.css의 :root 값에서 만든다(색/간격/글꼴).
- components/bundle.css: report.css에서 :root만 뺀 것. 색은 tokens.json이 정한다.
- components/<이름>/preview.html: build2.py의 실제 함수로 그린 조각. 리포트와 어긋나지 않게 한다.
사용: python3 -I ds_build4.py <tools/report 폴더> <출력 폴더(project)>"""
import base64, io, json, os, re, runpy, sys

REPORT, OUT = os.path.abspath(sys.argv[1]), os.path.abspath(sys.argv[2])
os.chdir(REPORT)
G = runpy.run_path(os.path.join(REPORT, "build2.py"), run_name="ds")
CSS = open(os.path.join(REPORT, "report.css"), encoding="utf-8").read()


def w(path, text):
    full = os.path.join(OUT, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    open(full, "w", encoding="utf-8").write(text)


# ---------- tokens.json ----------
root = re.search(r":root \{(.*?)\n\}", CSS, re.S).group(1)
vals = dict(re.findall(r"--([a-z0-9-]+):\s*([^;]+);", root))

USAGE = {
    "ink": "가장 진한 글자색이자 굵은 선(섹션 머리줄 2px, 0선). text와 같은 값.",
    "text": "본문 글자. 흰 바탕 위 18:1.",
    "text-2": "보조 글(설명, 근거 문장). 흰 바탕 위 9:1.",
    "text-3": "라벨, 축, 시간 같은 작은 글자. 흰 바탕 위 5:1.",
    "opp": "상대 팀. 상대 팀 막대, 오브젝트 아이콘, 표 위 선. 진하기는 아직 정하지 않았어요.",
    "line": "1px 선, 진 쪽 막대, 그래프의 '상대 팀 앞섬' 면, 보통 칩 바탕.",
    "bg": "페이지 바탕, 패널 안의 옅은 상자.",
    "panel": "패널, 표, 카드 면. 그림자 없이 line 1px로만 나눠요.",
    "panel-2": "패널 안의 둘째 면(차트의 중반부 띠, 국면 막대 칸). bg와 같은 값.",
    "line-soft": "표 안쪽 선, 막대 바탕. bg와 같은 값.",
    "dark": "포인트 2. 히어로 면, 고칠 점 번호, 개선점 상자, 지도 바탕, 레벨 배지.",
    "dark-line": "다크 면 안의 칸 구분선.",
    "on-dark": "다크 위 본문 글자.",
    "on-dark-2": "다크 위 라벨 글자.",
    "mint": "포인트 1(주로 쓰는 민트). 우리 팀, 좋음, 승리. 면, 막대, 칩, 다크 위 강조 글자에 써요.",
    "mint-ink": "흰 바탕 위에서 민트가 필요할 때만 쓰는 진한 민트. 내 챔피언 이름, 킬 표시, 우리 팀 오브젝트, 지도 마름모. 흰 바탕 위 4.5:1을 넘는 가장 밝은 민트예요.",
    "red": "패배, 죽음, 아쉬움, 손해 같은 부정적인 것. 면, 선, 큰 숫자, 히어로 빗금.",
    "red-ink": "흰 바탕 위의 빨강 글자(마이너스 골드, 잃은 것, 주요 순간 강조).",
    "on-accent": "민트나 빨강 면 위의 글자(검정).",
}
ORDER = ["bg", "panel", "panel-2", "line-soft", "line", "text", "ink", "text-2", "text-3", "opp",
         "mint", "mint-ink", "red", "red-ink", "dark", "dark-line", "on-dark", "on-dark-2", "on-accent"]
ctoks = []
for n in ORDER:
    v = vals[n].strip()
    m = re.fullmatch(r"var\(--([a-z0-9-]+)\)", v)
    ctoks.append({"name": n, "value": "{" + m.group(1) + "}" if m else v, "usage": USAGE[n]})
assert set(ORDER) >= {k for k, v in vals.items() if v.strip().startswith(("#", "var(--"))} - {"font-sans", "font-num"}, "색 빠짐"

SP_USE = {"s-1": "아이콘 사이.", "s-2": "칩 안 여백, 라벨과 값 사이.", "s-3": "목록 줄 간격.",
          "s-4": "패널끼리 간격, 모바일 바깥 여백.", "s-5": "패널 안 여백, 데스크톱 바깥 여백.",
          "s-6": "히어로와 큰 블록 안 여백.", "s-7": "두 단 사이.", "s-8": "섹션 사이."}
tokens = {
    "name": "Ranked Archive", "version": 4,
    "color": {"themes": [{"id": "light", "name": "라이트"}], "tokens": ctoks},
    "type": {
        "fonts": [{"family": "Pretendard Variable", "file": "fonts/PretendardVariable.woff2", "weight": "45 920"}],
        "families": {"sans": vals["font-sans"].strip(), "num": vals["font-num"].strip()},
        "groups": [
            {"name": "큰 숫자", "family": "num", "styles": [
                {"name": "result", "family": "sans", "fontSize": "80px", "lineHeight": 0.9, "fontWeight": 900, "letterSpacing": "-0.05em", "sample": "패배",
                 "usage": "히어로의 승리/패배 한 단어. 패배는 red, 승리는 mint."},
                {"name": "lp", "fontSize": "64px", "lineHeight": 0.9, "fontWeight": 900, "sample": "30 LP",
                 "usage": "히어로의 LP. Archivo를 가로로 넓게(font-stretch 125%)."},
                {"name": "big-n", "fontSize": "88px", "lineHeight": 0.85, "fontWeight": 900, "sample": "12",
                 "usage": "죽음 섹션의 데스 수. red, font-stretch 125%."},
                {"name": "sec-no", "fontSize": "56px", "lineHeight": 0.8, "fontWeight": 900, "sample": "04",
                 "usage": "섹션 번호. 속을 비우고 외곽선(1.5px)만, font-stretch 125%."},
                {"name": "stat", "fontSize": "32px", "lineHeight": 1.15, "fontWeight": 800, "sample": "13,893",
                 "usage": "히어로 스탯 칸의 값. font-stretch 112%, 숫자 폭 고정."},
                {"name": "ms-val", "fontSize": "24px", "lineHeight": 1.2, "fontWeight": 800, "sample": "−4,807",
                 "usage": "패널 안 작은 지표 값(14분 팀 골드 등)."},
            ]},
            {"name": "제목", "family": "sans", "styles": [
                {"name": "h2", "fontSize": "30px", "lineHeight": 1.1, "fontWeight": 800, "letterSpacing": "-0.02em", "sample": "죽음",
                 "usage": "섹션 제목. 위에 2px 머리줄, 왼쪽에 외곽선 번호."},
                {"name": "takeaway", "fontSize": "26px", "lineHeight": 1.38, "fontWeight": 800, "letterSpacing": "-0.03em",
                 "sample": "상대 정글이 안 보이면 라인을 당겨 받아요.", "usage": "다음 판 목표 한 문장(민트 면 위). 페이지에 한 번."},
                {"name": "lede", "fontSize": "22px", "lineHeight": 1.55, "fontWeight": 700, "letterSpacing": "-0.02em",
                 "sample": "중반부터 죽을 때마다 전령과 바론을 내줬어요.", "usage": "경기 요약 문장. 괄호 속 근거는 옅은 글자."},
                {"name": "sub-h", "fontSize": "17px", "lineHeight": 1.4, "fontWeight": 800, "sample": "주요 죽음", "usage": "섹션 안 작은 제목."},
                {"name": "card-title", "fontSize": "15px", "lineHeight": 1.4, "fontWeight": 800, "sample": "분당 골드 차이", "usage": "패널과 카드 제목."},
            ]},
            {"name": "본문", "family": "sans", "styles": [
                {"name": "body", "fontSize": "15px", "lineHeight": 1.6, "fontWeight": 400,
                 "sample": "상대 정글이 드래곤 쪽에서 마지막으로 보였다면 라인을 당겨 받으세요.", "usage": "본문. 줄 길이 70자 안쪽, text-2."},
                {"name": "small", "fontSize": "13px", "lineHeight": 1.5, "fontWeight": 400, "sample": "이즈리얼 51,440", "usage": "비교값, 주석."},
                {"name": "label", "fontSize": "12px", "lineHeight": 1.4, "fontWeight": 600, "sample": "15분 맞라인 골드", "usage": "라벨과 범례. text-3."},
            ]},
            {"name": "작은 숫자", "family": "num", "styles": [
                {"name": "time", "fontSize": "13px", "lineHeight": 1.6, "fontWeight": 600, "sample": "27:26", "usage": "게임 시간. 항상 m:ss."},
                {"name": "axis", "fontSize": "11px", "lineHeight": 1.2, "fontWeight": 500, "sample": "−2.5k", "usage": "차트 축 숫자. text-3."},
            ]},
        ],
    },
    "spacing": {"tokens": [{"name": k, "value": vals[k].strip(), "usage": SP_USE[k]} for k in SP_USE]},
    "radius": {"tokens": [
        {"name": "radius-0", "value": "0px", "usage": "기본값. 패널, 칩, 아이콘 모두 각지게."},
        {"name": "radius-round", "value": "50%", "usage": "룬, 장신구, 지도 위 죽은 곳, 죽음 번호에만."}]},
    "layout": {"tokens": [
        {"name": "rule", "value": vals["rule"].strip(), "usage": "섹션 머리줄 두께(text 색)."},
        {"name": "wrap", "value": vals["wrap"].strip(), "usage": "본문 최대 너비."},
        {"name": "nav-h", "value": vals["nav-h"].strip(), "usage": "위에 고정되는 섹션 이동 막대 높이."}]},
}
os.makedirs(OUT, exist_ok=True)
w("tokens.json", json.dumps(tokens, ensure_ascii=False, indent=1) + "\n")

# ---------- bundle.css ----------
bundle = re.sub(r":root \{.*?\n\}\n", "", CSS, count=1, flags=re.S)
assert ":root" not in bundle
bundle = bundle.replace("/* Ranked Archive", "/* Ranked Archive 컴포넌트 스타일. 색/간격/글꼴 값은 tokens.json에서 와요.\n   (원본: report.css) —", 1)
bundle += "\n/* 미리보기 칸 */\n.pv { padding: var(--s-5); background: var(--bg); }\n.pv .sec { margin-top: 0; }\n.pv-row { display: flex; flex-wrap: wrap; gap: var(--s-4); align-items: center; }\n"
w("components/bundle.css", bundle)


# ---------- 미리보기 ----------
def inline_imgs(h, small=False):
    from PIL import Image
    cache = {}

    def rep(m):
        p = m.group(2)
        if p not in cache:
            im = Image.open(os.path.join(REPORT, p)).convert("RGBA")
            name = os.path.basename(p)
            size = None if "map11" in name else ((48 if small else 96) if name.startswith("c_") else (36 if small else 56))
            if size:
                im = im.resize((size, size), Image.LANCZOS)
            bio = io.BytesIO(); im.save(bio, "WEBP", quality=80)
            cache[p] = "data:image/webp;base64," + base64.b64encode(bio.getvalue()).decode()
        return f'{m.group(1)}="{cache[p]}"'
    return re.sub(r'(src|href)="(img/[^"]+\.png)"', rep, h)


FONTS_LINK = '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wdth,wght@62..125,100..900&display=swap">'
CARDS = []


def preview(name, group, inner, readme, width=1240, small=False):
    CARDS.append((name, group, width, inner, small))
    w(f"components/{name}/README.md", f"# {name}\n\n{readme.strip()}\n")


def doc(name, group, height, width, inner, small=False):
    return (f'<!-- @dsCard group="{group}" height={height} width={width} -->\n<!doctype html>\n<html lang="ko">\n'
            f'<head><meta charset="utf-8"><title>{name}</title>{FONTS_LINK}</head>\n<body>\n{G["SPRITE"]}\n'
            f'<div class="pv">{inline_imgs(inner, small)}</div>\n</body>\n</html>\n')


def inner_of(sec_html):
    """섹션 하나에서 머리줄을 뺀 몸통."""
    return sec_html[sec_html.index("</header>") + len("</header>"):sec_html.rindex("</section>")]


ME = G["ME"]
sec = {k: G[k]() for k in ["sec_summary", "sec_flow", "sec_lane", "sec_deaths", "sec_team", "sec_build", "sec_check", "sec_memo"]}

preview("Hero", "레이아웃", G["hero"]().replace('class="hero', 'style="margin:0" class="hero', 1), """
리포트 맨 위의 다크 면이에요. 한 페이지에 한 번만 써요.

- 맨 위 빗금 띠: 패배는 `red`, 승리는 `mint`. 승패를 가장 먼저 알려주는 표시예요.
- 결과 단어(`result` 스타일)도 패배는 `red`, 승리는 `mint`.
- 오른쪽에 티어와 LP. LP는 Archivo를 가로로 넓게(125%) 써요.
- 아래 6칸 스탯: 값(`stat`), 한 줄 설명, 상대 원딜 값. 칸은 `dark-line` 1px로 나눠요.
- 데스 수처럼 나쁜 숫자만 `red`로 칠해요. 숫자마다 색을 넣지 않아요.
- 닉네임은 넣지 않아요.
""")

preview("SectionNav", "레이아웃", G["sitenav"]() + G["secnav"]().replace('<a ', '<a class="on" ', 1), """
페이지 맨 위의 페이지 탭과, 그 아래 섹션 이동 막대예요.

- 섹션 이동 막대는 스크롤해도 화면 위에 붙어 있어요(높이 `nav-h` 48px).
- 지금 보고 있는 섹션은 글자가 `text`로 진해지고 아래에 `mint` 3px 선이 생겨요.
- 번호는 Archivo, 이름은 Pretendard예요.
- 페이지 탭은 고정하지 않아요. 지금 페이지는 `ink` 3px 밑줄로 표시해요.
""")

preview("SectionHead", "레이아웃", G["section"]("04", '<p class="body" style="margin:0">섹션 내용이 여기 와요.</p>'), """
섹션의 시작을 알리는 머리줄이에요.

- 위에 `text` 색 2px 선(`rule`).
- 왼쪽에 속이 빈 큰 번호(`sec-no` 스타일, 외곽선 1.5px), 그 옆에 h2 제목.
- 영어 보조 라벨은 붙이지 않아요.
- 섹션 사이는 `s-8`(72px).
""", width=900)

chips = ('<div class="pv-row"><span class="chip chip-pos">좋음</span><span class="chip chip-mid">보통</span>'
         '<span class="chip chip-bad">아쉬움</span><span class="chip chip-pos">승리</span><span class="chip chip-bad">패배</span>'
         '<span class="chip chip-line">라인전</span><span class="chip chip-unknown">기록 없음</span></div>')
preview("Chip", "상태", chips, """
한두 단어로 상태를 붙이는 각진 칩이에요. 색에 뜻이 있어서 장식으로 쓰지 않아요.

| 칩 | 뜻 | 색 |
|---|---|---|
| `chip-pos` | 좋음, 승리 | `mint` 면 + 검정 글자 |
| `chip-mid` | 보통 | `line` 면 + `text-2` |
| `chip-bad` | 아쉬움, 패배 | `red` 면 + 흰 글자 |
| `chip-line` | 국면(라인전, 중반부, 후반부), 스펠 상태 | `bg` 면 + `text-2` |
| `chip-unknown` | 게임 중 기록이 없어서 모름 | 점선 테두리 |

- '모름'은 꼭 `chip-unknown`으로 보여줘요. 빈칸이나 0으로 두면 실제 값처럼 읽혀요.
- 메모로 판단하는 체크리스트 항목에는 칩을 달지 않아요.
""", width=900)

lo = ('<div class="pv-row">' + G["loadout"](ME) + G["items_row"](ME, "sm") + '</div>'
      '<div class="pv-row" style="background:var(--dark);padding:16px;margin-top:16px">' + G["loadout"](ME, big=True) + '</div>')
preview("Loadout", "아이콘", lo, """
챔피언 초상화 옆에 소환사 주문 2개와 룬(핵심 룬, 보조 룬)을 2×2로 묶은 아이콘 묶음이에요. OP.GG 전적 줄에서 가져온 형태예요.

- 왼쪽 열은 스펠(D, F 순서), 오른쪽 열은 핵심 룬과 보조 룬이에요.
- 룬과 장신구는 동그랗게, 나머지는 각지게.
- 초상화 오른쪽 아래에 레벨 배지(`dark` 면, Archivo 숫자).
- 아이템 줄은 6칸 + 장신구(4px 띄움). 빈 칸도 `line-soft` 면으로 자리를 지켜요.
- 아이콘은 Data Dragon에서 가져와요. 버전은 경기의 패치를 따라요(26.22 → 16.22.1).

| 크기 | 픽셀 | 쓰는 곳 |
|---|---|---|
| `ic-xs` | 22 | 표 안 아이템(팀 표는 25), 죽음 카드 안 얼굴 |
| `ic-sm` | 28 | 맞대결 머리, 스킬 |
| `ic-md` | 40 | 표의 챔피언, 빌드 순서 |
| `ic-lg` | 52 | 핵심 룬 |
| `ic-xl` | 88 | 히어로 초상화 |
""", width=900)

preview("Summary", "섹션", inner_of(sec["sec_summary"]), """
01 경기 요약이에요. 요약 문장 → 고칠 점 → 다음 판 목표 순서예요.

- 요약 문장은 `lede` 스타일. 괄호 속 근거(팀 골드 차이 등)는 옅은 글자예요.
- 고칠 점 번호는 `dark` 칸 + 흰 Archivo 숫자.
- 고칠 점 개수는 정해 두지 않아요. 체크리스트에서 '아쉬움'이 나온 항목 중 겹치지 않는 것만큼 써요.
- 다음 판 목표는 `mint` 면에 한 문장. 페이지에서 민트 면이 가장 크게 쓰이는 곳이에요.
""")

preview("GoldChart", "섹션", inner_of(sec["sec_flow"]), """
02 경기 흐름이에요. 분당 팀 골드 차이 차트와 유불리 운영, 집중력으로 이뤄져요.

**차트**
- 0선 위(우리 팀 앞섬)는 `mint` 면, 아래(상대 팀 앞섬)는 `line` 면.
- 팀 전체는 `text` 실선, 바텀 2대2는 `text-3` 점선.
- 위쪽 줄: 내 킬은 얇은 `mint-ink` 막대, 내 죽음은 `red` 사각 + 옅은 세로선.
- 아래쪽 줄: 오브젝트는 박스 없이 그림 아이콘만. 우리 팀 `mint-ink`, 상대 팀 `opp`.
- 배경 띠로 라인전(0~14분), 중반부(14~25분), 후반부를 나눠요.
- 차트는 파이썬에서 SVG로 그려서 자바스크립트 없이 보여요.

**숫자 색**
- 마이너스 골드 차이는 `red-ink`, 플러스는 기본 글자색이에요. 제목 옆 '(최종 …)' 값도 같은 규칙이에요.
- 유불리 운영의 '벌어짐' 구간과 숫자는 회색, '따라잡음'은 민트예요. 킬과 죽음 수는 검정으로 통일해요.
""")

preview("Butterfly", "섹션", inner_of(sec["sec_lane"]), """
03 라인전이에요. 맞대결 막대(나비 막대)와 레벨 표, 라인전 사실로 이뤄져요.

- 왼쪽은 항상 나와 우리 팀(`mint`), 오른쪽은 상대(`opp`).
- 이긴 쪽 막대만 색을 칠하고, 진 쪽은 `line`. 이긴 쪽 숫자를 굵게 해요.
- 많다고 좋다고 할 수 없는 값(받은 피해 등)은 양쪽 다 옅게 그려요.
- 레벨 표: 앞선 칸은 `mint` 면, 뒤처진 칸은 `opp` 면 + 흰 글자.
- LOL.PS처럼 2레벨 선점과 15분 지표를 보여줘요.
""")

d = sec["sec_deaths"]
top = d[d.index('<div class="death-top">'):d.index('<h3 class="sub-h">주요 죽음</h3>')]
preview("DeathMap", "섹션", top, """
04 죽음의 윗부분이에요. 지도, 데스 수, 국면 막대로 이뤄져요.

- 지도는 흑백으로 낮추고 `dark` 막을 덮어 점이 먼저 보이게 해요.
- 죽은 곳: `red` 원 + 검정 번호. 킬: 채운 `mint-ink` 마름모, 어시스트: 빈 `mint-ink` 마름모.
- 데스 수는 `big-n` 스타일(`red`).
- 국면 막대는 실제 경기 시간 비율로 나눠요. 칸마다 국면 이름, 구간 시간(0:00 ~ 14:00 등), 그 구간에 죽은 횟수를 적어요.
- 그 아래에 죽은 위치(라인, 강가, 정글, 본진)별 횟수와, 죽은 뒤 잃은 것 같은 요약 숫자를 둬요.
- 지도 밖의 죽음 번호는 원 없이 빨간 숫자로 써요.
""")

card = re.search(r'<article class="dcard">.*?</article>', d, re.S)
preview("DeathCard", "섹션", '<div class="dcards" style="grid-template-columns:1fr;max-width:620px">' + card.group(0) + '</div>', """
주요 죽음 하나를 정리하는 카드예요. LoLGPT의 '죽음마다 원인과 다음 행동'에서 가져왔어요.

순서: 번호, 시간, 국면, 위치 → 처치 그림(처치한 챔피언 + 도운 챔피언 → 흑백 내 초상화) → 6칸 사실 표 → 합류한 적 → 받은 피해 막대 → 상황 / 근거 / 개선점.

- 사실 표: 근처 아군, 근처 적, 가진 골드, 점멸, 팀 골드 차이, 죽은 뒤 잃은 것.
- 게임 중 기록이 없는 값은 `chip-unknown`.
- 받은 피해는 많은 순서로 `red` → `text-2` → `opp` → `line`. 챔피언마다 새 색을 만들지 않아요.
- 개선점만 `dark` 상자. 한 카드에 행동 하나.
- 합류한 적이 없는 카드도 그 칸 높이만큼 비워서, 나란한 카드의 아랫부분 높이를 맞춰요.
""", width=700)

preview("TeamTable", "섹션", inner_of(sec["sec_team"]), """
05 팀 기록이에요. 팀 합계 비교와 선수별 기록 표로 이뤄져요.

- 우리 팀 표는 위에 `mint` 3px, 상대 팀 표는 `opp` 3px.
- 내 줄은 왼쪽에 `mint` 4px 띠, 이름은 `mint-ink`.
- 팀에서 가장 높은 값(피해 등)은 굵게.
- 닉네임은 보여주지 않아요. 티어, LP, 연승, 최근 모스트 칸은 데이터가 생기면 넣어요.
""", small=True)

preview("Build", "섹션", inner_of(sec["sec_build"]), """
06 빌드예요. 아이템 시간표, 구매 순서, 룬, 스펠, 스킬로 이뤄져요.

- 아이템 시간표: 나와 상대의 완성 아이템을 같은 시간 축에 놓아요. 크게 늦은 구간은 `red` 선 + `red-ink` 숫자.
- 구매 순서: 코어 아이템은 크게 하고 `ink` 2px 테두리.
- 룬: 5칸 격자 하나에 주 룬 3칸 + 보조 룬 2칸. 같은 줄 아이콘은 크기와 높이를 맞춰요. 능력치 파편은 글씨 없이 아래에.
- 스킬 순서 표는 넣지 않아요.
""")

ck = sec["sec_check"]
preview("Checklist", "섹션", inner_of(ck), """
07 체크리스트예요. 원딜 9개 항목을 3열 격자로 보여줘요.

- 칸마다: 두 자리 번호, 상태 칩, 항목 이름, 근거 한두 줄.
- 칸 위 선과 칩: 좋음 `mint`, 아쉬움 `red`, 보통 `opp`. 메모로 판단하는 항목은 칩 없이 옅은 기본 선만.
- 맨 위에 상태별 개수를 요약해요.
- 미드(아리)일 때는 라인 주도권, 매혹(E) 활용, 시야 장악 항목을 더해요.
""")

preview("Memo", "섹션", inner_of(sec["sec_memo"]), """
08 메모예요. 데이터로 알 수 없는 것(채팅, 핑, 기분, 판단 이유)만 적어요.

- 흰 패널 하나에 `text-2` 본문.
- 비어 있으면 옅은 글자로 짧게 표시해요.
""", width=900)


# ---------- 높이 재기 ----------
def measure():
    import asyncio
    from playwright.async_api import async_playwright

    async def run():
        out = {}
        async with async_playwright() as p:
            b = await p.chromium.launch()
            for name, group, width, inner, _ in CARDS:
                pg = await b.new_page(viewport={"width": width, "height": 400})
                html = (f'<!doctype html><html lang="ko"><head><meta charset="utf-8">{FONTS_LINK}<style>{CSS}\n'
                        '.pv{padding:24px;background:var(--bg)} .pv .sec{margin-top:0} .pv-row{display:flex;flex-wrap:wrap;gap:16px;align-items:center}'
                        f'body{{margin:0}}</style></head><body>{G["SPRITE"]}<div class="pv">{inner}</div></body></html>')
                await pg.set_content(html, wait_until="load")
                await pg.wait_for_timeout(300)
                out[name] = await pg.evaluate("document.querySelector('.pv').getBoundingClientRect().height")
                await pg.close()
            await b.close()
        return out
    return asyncio.run(run())


H = measure()
for name, group, width, inner, small in CARDS:
    h = int(H[name]) + 8
    text = doc(name, group, h, width, inner, small)
    w(f"components/{name}/preview.html", text)
    print(f"{name:12s} {width}x{h}  {len(text.encode()) // 1024} KB")
