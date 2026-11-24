"""artifact에 올릴 한 파일짜리 리포트 만들기

React 앱을 한 파일로 빌드한 것(web/dist-single/index.html)에 그 판의 데이터, 아이콘, 글꼴을 넣어요.
인터넷 주소를 하나도 안 쓰기 때문에 artifact에서도 그대로 보여요.

사용 (저장소 맨 위에서):
  (cd web && npm run build:single)                       # 화면 코드가 바뀌었을 때만
  python3 tools/report/single.py KR_8448036968            # 결과: tools/report/KR_8448036968_single.html
  python3 tools/report/single.py --make-base-font          # 미리 줄여 둔 한글 글꼴을 다시 만들 때만(글꼴을 바꿨을 때)
"""
import base64, io, json, os, re, sys, urllib.request
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
APP = os.path.join(ROOT, "web", "dist-single", "index.html")
CACHE = os.path.join(HERE, "img")  # .gitignore에 들어 있어요
MIRROR = "https://raw.githubusercontent.com/noxelisdev/LoL_DDragon/master/"
FONT_DIR = os.path.join(ROOT, "tools", "fonts")


def refs(x, out):
    """데이터 안의 모든 아이콘 경로(img 칸)를 모아요."""
    if isinstance(x, dict):
        for k, v in x.items():
            if k == "img" and isinstance(v, str):
                out.add(v)
            else:
                refs(v, out)
    elif isinstance(x, list):
        for v in x:
            refs(v, out)
    return out


def fetch(ref):
    """CDN 경로 → 미러에서 받기. 예: '16.22.1/img/item/1055.png' → 'latest/img/item/1055.png', 'img/perk-images/..' → 그대로"""
    local = os.path.join(CACHE, "r_" + ref.replace("/", "_"))
    if not os.path.exists(local):
        rel = re.sub(r"^\d+\.\d+\.\d+/", "latest/", ref)
        rel = rel.replace("champion/FiddleSticks.png", "champion/Fiddlesticks.png")  # 미러 파일 이름이 달라요(11-22)
        try:
            with urllib.request.urlopen(MIRROR + rel, timeout=20) as r:
                open(local, "wb").write(r.read())
        except Exception as e:  # noqa
            print("아이콘 못 받음", ref, e)
            return None
    return "data:image/png;base64," + base64.b64encode(open(local, "rb").read()).decode()


BASE_FONT = os.path.join(FONT_DIR, "PretendardBase.woff2")
EXTRA = "−±→←↑↓…–—"


def base_chars():
    """미리 줄여 둔 글꼴에 든 글자: 자주 쓰는 한글 2,350자 + 한글 표준 기호(한자 제외) + 영문/숫자 + EXTRA."""
    cs = set(chr(c) for c in range(32, 127)) | set(EXTRA)
    for b1 in list(range(0xA1, 0xAD)) + list(range(0xB0, 0xC9)):
        for b2 in range(0xA1, 0xFF):
            try:
                cs.add(bytes([b1, b2]).decode("euc-kr"))
            except UnicodeDecodeError:
                pass
    return cs


def subset_font(path, text):
    from fontTools import subset
    opts = subset.Options(); opts.flavor = "woff2"; opts.layout_features = ["*"]
    f = subset.load_font(os.path.join(FONT_DIR, path), opts)
    s = subset.Subsetter(opts); s.populate(text=text); s.subset(f)
    bio = io.BytesIO(); subset.save_font(f, bio, opts)
    return bio.getvalue()


def make_base_font():
    """PretendardBase.woff2를 한 번 만들어 저장소에 넣어 둬요(11-22). 판마다 글꼴을 줄이는 데 약 6초가 들었어요."""
    data = subset_font("PretendardVariable.woff2", "".join(sorted(base_chars())))
    open(BASE_FONT, "wb").write(data)
    print(f"{os.path.relpath(BASE_FONT, ROOT)}: {len(data) // 1024} KB")


def font_faces(text):
    """페이지에 쓰인 글자가 담긴 글꼴을 data: 주소로 만들어요.
    페이지 글자가 모두 미리 줄여 둔 글꼴(PretendardBase.woff2)에 있으면 그걸 그대로 써요(글꼴 줄이기 생략, 약 6초 절약).
    하나라도 없으면 예전처럼 페이지에 쓰인 글자만 남겨 새로 줄여요."""
    text = text + "".join(chr(c) for c in range(32, 127)) + EXTRA
    need = {c for c in text if ord(c) >= 32}
    faces = []
    for fam, path, rng in [("Pretendard Variable", "PretendardVariable.woff2", "45 920"),
                           ("Archivo", "archivo-latin-wdth-normal.woff2", "100 900")]:
        if fam.startswith("Pretendard") and os.path.exists(BASE_FONT) and need <= base_chars():
            data = open(BASE_FONT, "rb").read()
        else:
            data = subset_font(path, text)
        b64 = base64.b64encode(data).decode()
        st = "font-stretch:62% 125%;" if fam == "Archivo" else ""
        faces.append(f"@font-face{{font-family:'{fam}';src:url(data:font/woff2;base64,{b64}) format('woff2');font-weight:{rng};{st}font-display:swap}}")
    return "".join(faces)


def main(mid, out=None, lab=False, draft=False, compare=False):
    os.makedirs(CACHE, exist_ok=True)
    if not os.path.exists(APP):
        sys.exit("web/dist-single/index.html이 없어요. 먼저 (cd web && npm run build:single) 을 실행해 주세요.")
    app = open(APP, encoding="utf-8").read()
    src = os.path.join(HERE, "lab-data") if lab else os.path.join(ROOT, "docs", "report-data")  # 실험 데이터는 report_data.py --lab 이 만들어요
    if not lab and not os.path.exists(os.path.join(src, mid + ".json")):
        src = os.path.join(HERE, "private-data")  # 비공개 판(public.json에 없는 판)
    data = json.load(open(os.path.join(src, mid + ".json"), encoding="utf-8"))
    # 아이콘은 동시에 받아요. 새 작업 공간에서는 캐시가 비어 있어서, 하나씩 받으면 100개 넘게 약 30초가 걸렸어요(11-21).
    names = sorted(refs(data, set()))
    with ThreadPoolExecutor(16) as ex:
        assets = {r: u for r, u in zip(names, ex.map(fetch, names)) if u}
    blob = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    js = ("<script>window.__REPORT__=" + blob.replace("</", "<\\/") + ";window.__ASSETS__="
          + json.dumps(assets, separators=(",", ":")) + (";window.__LAB__=true" if lab else "") + (";window.__DRAFT__=true" if draft else "") + (";window.__COMPARE__=true" if compare else "") + ";</script>")
    title = f'{data["me"]["n"]} {"승리" if data["hero"]["win"] else "패배"} 리포트'
    html = app.replace("<title>경기 리포트</title>", f"<title>{title}</title>")
    html = html.replace("/*FONTS*/", font_faces(app + blob))
    html = html.replace('<div id="root"></div>', '<div id="root"></div>' + js, 1)
    if lab:
        title = "실험 · " + title
        html = html.replace(f"<title>{title[5:]}</title>", f"<title>{title}</title>")
    if draft:
        html = html.replace(f"<title>{title}</title>", f"<title>시안 · {title}</title>")
    if compare:
        html = html.replace(f"<title>{title}</title>", f"<title>세 버전 비교 · {title}</title>")
    out = out or os.path.join(HERE, mid + ("_lab" if lab else "_draft" if draft else "_compare" if compare else "") + "_single.html")
    open(out, "w", encoding="utf-8").write(html)
    print(f"{os.path.relpath(out, ROOT)}: 아이콘 {len(assets)}개, {len(html) // 1024} KB")


if __name__ == "__main__":
    # python3 tools/report/single.py <경기ID> [저장할 곳] [--lab|--draft|--compare]   --lab: 실험 페이지로, --draft: 01~07 새 배치 시안(본 리포트 데이터 그대로), --compare: 기본/첫 시안/정보 위계 시안을 섹션끼리 세로로 비교
    if "--make-base-font" in sys.argv:
        make_base_font(); sys.exit()
    a = [x for x in sys.argv[1:] if x not in ("--lab", "--draft", "--compare")]
    main(a[0], a[1] if len(a) > 1 else None, lab="--lab" in sys.argv, draft="--draft" in sys.argv, compare="--compare" in sys.argv)
