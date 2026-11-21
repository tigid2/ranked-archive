"""리포트 한 파일(..._single.html)을 Playwright로 열어 글자와 오류만 확인해요(스크린샷 X).
사용: python3 tools/report/check_page.py <경기ID>  [확인할 글자 ...]
피드백 파일의 keyFixes 제목은 저절로 확인해요. 문제가 없으면 마지막 줄이 "확인 끝: 문제 없음"이에요."""
import json, os, sys
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
mid = sys.argv[1]
page_path = os.path.join(HERE, f"{mid}_single.html")
want = list(sys.argv[2:])
for d in ("private-feedback", "feedback"):
    fp = os.path.join(HERE, d, mid + ".json")
    if os.path.exists(fp):
        fb = json.load(open(fp, encoding="utf-8"))
        want += [k["title"] for k in fb.get("keyFixes", [])]
        break

with sync_playwright() as pw:
    b = pw.chromium.launch()
    pg = b.new_page(viewport={"width": 1600, "height": 1000})
    errs = []
    pg.on("console", lambda m: m.type == "error" and errs.append(m.text))
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto("file://" + page_path)
    pg.wait_for_timeout(2500)
    t = pg.inner_text("body")
    b.close()

bad = []
if "·" in t:
    i = t.find("·")
    bad.append(f"가운뎃점 {t.count('·')}개, 첫 자리: {t[max(0, i - 30):i + 30]!r}")
if errs:
    bad.append(f"오류 {len(errs)}개: {errs[:3]}")
miss = [w for w in want if w not in t]
if miss:
    bad.append(f"화면에 없는 글자: {miss}")
print(f"글자 {len(t)}자")
print("\n".join(bad) if bad else "확인 끝: 문제 없음")
