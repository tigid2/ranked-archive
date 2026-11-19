"""data/icons/*.svg(사용자가 그린 오브젝트 아이콘)로 그림 아이콘 묶음(SPRITE)을 다시 만들어요.
web/src/ui.jsx와 tools/report/build2.py의 SPRITE 안 <symbol>을 바꿔요.
ORDER에 없는 아이콘은 묶음에서 빠져요(아타칸은 게임에서 사라져서 지웠어요).
사용: python3 tools/make_sprite.py"""
import os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ICONS = os.path.join(ROOT, "data", "icons")
ORDER = ["dragon", "baron", "herald", "grub", "tower", "inhib", "minion"]
TARGETS = [os.path.join(ROOT, "web", "src", "ui.jsx"), os.path.join(ROOT, "tools", "report", "build2.py")]


def symbol(name):
    s = open(os.path.join(ICONS, f"{name}.svg"), encoding="utf-8").read()
    vb = re.search(r'viewBox="([^"]+)"', s).group(1)
    body = re.search(r"<svg[^>]*>(.*)</svg>", s, re.S).group(1)
    body = " ".join(line.strip() for line in body.strip().splitlines())
    return f'<symbol id="i-{name}" viewBox="{vb}">{body}</symbol>'


for path in TARGETS:
    src = open(path, encoding="utf-8").read()
    m = re.search(r'(<svg class="sprite"[^>]*>\n)(.*?)(\n</svg>)', src, re.S)
    old = {re.search(r'id="i-([a-z]+)"', l).group(1): l for l in m.group(2).splitlines()}
    lines = [symbol(n) if os.path.exists(os.path.join(ICONS, f"{n}.svg")) else old[n] for n in ORDER if n in old or
             os.path.exists(os.path.join(ICONS, f"{n}.svg"))]
    src = src[:m.start(2)] + "\n".join(lines) + src[m.end(2):]
    open(path, "w", encoding="utf-8").write(src)
    print(os.path.relpath(path, ROOT), len(lines), "개")
