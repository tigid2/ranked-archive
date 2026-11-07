"""artifact에 올릴 한 파일짜리 리포트 만들기

React 앱을 한 파일로 빌드한 것(web/dist-single/index.html)에 그 판의 데이터, 아이콘, 글꼴을 넣어요.
인터넷 주소를 하나도 안 쓰기 때문에 artifact에서도 그대로 보여요.

사용 (저장소 맨 위에서):
  (cd web && npm run build:single)                       # 화면 코드가 바뀌었을 때만
  python3 tools/report/single.py KR_8448036968            # 결과: tools/report/KR_8448036968_single.html
"""
import base64, io, json, os, re, sys, urllib.request

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
    os.makedirs(CACHE, exist_ok=True)
    local = os.path.join(CACHE, "r_" + ref.replace("/", "_"))
    if not os.path.exists(local):
        rel = re.sub(r"^\d+\.\d+\.\d+/", "latest/", ref)
        try:
            with urllib.request.urlopen(MIRROR + rel, timeout=20) as r:
                open(local, "wb").write(r.read())
        except Exception as e:  # noqa
            print("아이콘 못 받음", ref, e)
            return None
    return "data:image/png;base64," + base64.b64encode(open(local, "rb").read()).decode()


def font_faces(text):
    """페이지에 쓰인 글자만 남긴 글꼴을 data: 주소로 만들어요."""
    from fontTools import subset
    text = text + "".join(chr(c) for c in range(32, 127)) + "−±→…—"
    faces = []
    for fam, path, rng in [("Pretendard Variable", "PretendardVariable.woff2", "45 920"),
                           ("Archivo", "archivo-latin-wdth-normal.woff2", "100 900")]:
        opts = subset.Options(); opts.flavor = "woff2"; opts.layout_features = ["*"]
        f = subset.load_font(os.path.join(FONT_DIR, path), opts)
        s = subset.Subsetter(opts); s.populate(text=text); s.subset(f)
        bio = io.BytesIO(); subset.save_font(f, bio, opts)
        b64 = base64.b64encode(bio.getvalue()).decode()
        st = "font-stretch:62% 125%;" if fam == "Archivo" else ""
        faces.append(f"@font-face{{font-family:'{fam}';src:url(data:font/woff2;base64,{b64}) format('woff2');font-weight:{rng};{st}font-display:swap}}")
    return "".join(faces)


def main(mid, out=None):
    if not os.path.exists(APP):
        sys.exit("web/dist-single/index.html이 없어요. 먼저 (cd web && npm run build:single) 을 실행해 주세요.")
    app = open(APP, encoding="utf-8").read()
    data = json.load(open(os.path.join(ROOT, "docs", "report-data", mid + ".json"), encoding="utf-8"))
    assets = {r: u for r in sorted(refs(data, set())) if (u := fetch(r))}
    blob = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    js = ("<script>window.__REPORT__=" + blob.replace("</", "<\\/") + ";window.__ASSETS__="
          + json.dumps(assets, separators=(",", ":")) + ";</script>")
    title = f'{data["me"]["n"]} {"승리" if data["hero"]["win"] else "패배"} 리포트'
    html = app.replace("<title>경기 리포트</title>", f"<title>{title}</title>")
    html = html.replace("/*FONTS*/", font_faces(app + blob))
    html = html.replace('<div id="root"></div>', '<div id="root"></div>' + js, 1)
    out = out or os.path.join(HERE, mid + "_single.html")
    open(out, "w", encoding="utf-8").write(html)
    print(f"{os.path.relpath(out, ROOT)}: 아이콘 {len(assets)}개, {len(html) // 1024} KB")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
