"""피드백 글을 쓰기 전에 볼 한 장짜리 요약 (11-21)

리포트 데이터(report_data.py 결과), 분석 결과(analysis/), 라이엇 원본(raw/), 게임 중 기록(live.json)에서
피드백에 쓰는 숫자만 모아 글자로 출력해요. 위치 트랙이나 미니맵 문자열 같은 큰 칸은 출력하지 않아요.

사용 (저장소 맨 위에서, report_data.py를 먼저 실행):
  python3 tools/report/fb_brief.py KR_8467951138 > /tmp/brief.txt     # 그다음 이 파일 하나만 읽어요
"""
import gzip, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))


def mmss(sec):
    sec = int(round(sec))
    return f"{sec // 60}:{sec % 60:02d}"


def ms(t):
    return mmss(t / 1000)


def load(mid):
    for d in (os.path.join(ROOT, "docs", "report-data"), os.path.join(HERE, "private-data")):
        p = os.path.join(d, mid + ".json")
        if os.path.exists(p):
            rep = json.load(open(p, encoding="utf-8"))
            break
    else:
        sys.exit("리포트 데이터가 없어요. 먼저 python3 tools/report/report_data.py " + mid)
    ana = json.load(open(os.path.join(ROOT, "analysis", mid + ".analysis.json"), encoding="utf-8"))
    raw = json.load(gzip.open(os.path.join(ROOT, "raw", mid + ".json.gz")))
    lp = os.path.join(ROOT, "raw", mid + ".live.json")
    live = json.load(open(lp, encoding="utf-8")) if os.path.exists(lp) else None
    return rep, ana, raw, live


def names(xs):
    return ", ".join(x["n"] for x in xs) or "-"


def main(mid):
    rep, ana, raw, live = load(mid)
    P = print
    h = rep["hero"]
    pub = mid in json.load(open(os.path.join(HERE, "public.json"), encoding="utf-8")).get("public", []) if os.path.exists(os.path.join(HERE, "public.json")) else False  # 11-22: 예전엔 늘 False
    m = h["match"]
    P(f"# {mid}  {rep['me']['n']} vs {rep['opp']['n']}  {h['when']}  {'승리' if h['win'] else '패배'}  {mmss(h['durationSec'])}  패치 {h['patch']}  공개 {pub}")
    P(f"랭크 {h['rank']['tier']} {h['rank']['lp']}LP ({h['rank']['change']:+})  서폿 {m['duo']['n']} / 상대 서폿 {m['eduo']['n']}")
    k, d, a = h["kda"]
    P(f"KDA {k}/{d}/{a}  킬관여 {h['kp']}%  CS {h['cs']} (분당 {h['csPerMin']:.1f}, 상대 {h['oppCs']})  피해 {h['dmg']:,} (팀 {h['dmgShare']}%, 상대 {h['oppDmg']:,})  골드 {h['gold']:,} (상대 {h['oppGold']:,})  시야 {h['vision']} 와드 {h['wards']} 제어와드 {h['controlWards']}")
    if rep.get("nav", {}).get("prev"):
        pv = rep["nav"]["prev"]
        P(f"이전 판: {pv['champ']} vs {pv['opp']} {pv['when']} {'승' if pv['win'] else '패'}")
    fb = os.path.exists(os.path.join(ROOT, "feedback", mid + ".json")) or os.path.exists(os.path.join(HERE, "private-feedback", mid + ".json"))
    P(f"피드백 글 있음: {fb}  1초 위치(리플레이): {'있음' if os.path.exists(os.path.join(ROOT, 'raw', mid + '.pos.json.gz')) else '없음'}")
    P(f"artifact 제목: 리포트 - {rep['me']['n']} vs {rep['opp']['n']} · {h['when']} {'승리' if h['win'] else '패배'}")

    P("\n## 10명")
    # 우리 팀 = 내 승패와 같은 팀 (예전에는 첫 번째 참가자 팀을 '우리'로 봐서, 레드 팀일 때 뒤집혀 나왔어요. 11-22)
    for p in sorted(raw["match"]["info"]["participants"], key=lambda p: p["win"] != ana["win"]):
        P(f"{'우리' if p['win'] == ana['win'] else '상대'} {p['championName']:<12} {p['teamPosition']:<8} {p['kills']}/{p['deaths']}/{p['assists']}  피해 {p['totalDamageDealtToChampions']:,}  CS {p['totalMinionsKilled'] + p['neutralMinionsKilled']}  시야 {p['visionScore']}")

    L = rep["lane"]
    P("\n## 라인전")
    P("  ".join(f"{r['label']} {r['me']}:{r['opp']}" for r in L["rows"]))
    P("레벨 선점: " + "  ".join(f"{x['lv']}레벨 나 {x['me']} / 상대 {x['opp']}" for x in L["levels"]))
    s = L["support"]
    P(f"서폿 바텀 있음(분): {[x['min'] for x in s['atBot'] if x['in']]}  없음: {[x['min'] for x in s['atBot'] if not x['in']]}  CS 있을때 {s['with']['me']}:{s['with']['opp']} / 없을때 {s['without']['me']}:{s['without']['opp']}")
    b = L["botAdcKills"]
    P(f"14분 전 바텀 원딜 킬 {b['opp']} : 내 죽음 {b['me']}  상대 원딜 죽음 {[(x['t'], x['killer']) for x in b['oppDeaths']]}  내 죽음 {[(x['t'], x['killer']) for x in b['myDeaths']]}  솔로킬 {L['soloKills']}")

    F = rep["flow"]
    P("\n## 흐름 (팀 골드 차이)")
    P("  ".join(f"{p['min']}분 {p['team']:+,}" for p in F["points"] if p["min"] % 2 == 0 or p["min"] == F["points"][-1]["min"]))
    P(f"14분 {F['gd14']:+,}  25분 {F.get('gd25')}  최저 {F['gdMin']:+,}  최고 {F['peak']['min']}분 {F['peak']['v']:+,}  끝 {F['final']:+,}")
    P("변곡(swings, 피드백 swings 키 = m0): " + "  ".join(f"[{s['m0']}~{s['m1']}분 {s['delta']:+,} 킬{s['kills']} 죽음{s['deaths']}]" for s in F["swings"]))
    P("내 킬: " + ", ".join(ms(t) for t in F["myKills"]) + "   내 죽음: " + ", ".join(ms(t) for t in F["myDeaths"]))
    P("오브젝트: " + "  ".join(f"{ms(o['t'])} {o['name']}({'우리' if o['ours'] else '상대'})" for o in F["objs"]))
    P("오브젝트 30초 전 내 거리: " + "  ".join(f"{o['t']} {o['name']} {'우리' if o['ours'] else '상대'} {o.get('myDistance30sBefore')}{' (죽어 있음)' if o.get('iWasDead') else ''}" for o in ana.get("objectives", [])))

    P("\n## 교전")
    for f in ana.get("fights", []):
        P(f"{f['start']} {f['kills']} {f['zone']}  나 {'있음' if f['iWasIn'] else '없음'}{' 죽음' if f['iDied'] else ''}  직전 팀골드 {f['teamGoldDiffBefore']:+,}")

    D = rep["deaths"]
    P(f"\n## 죽음 {D['total']}번  구간 {[(p['name'], p['n']) for p in D['phases']]}  혼자 {D['alone']}  죽은 뒤 손해 {D['lostN']}  합류 {D['roamN']}")
    lived = {round(x["t"]): x for x in (live or {}).get("deaths", [])}
    for x in D["list"]:
        r = x.get("recap") or {}
        P(f"\n[{x['no']}] {x['t']} {x['phase']} {x['zone']}  킬 {x['killer']['n']}  도움 {names(x['assists'])}")
        P(f"  근처 아군 {names(x['alliesNear'])} / 적 {names(x['enemiesNear'])}  골드 {x['gold']}  팀골드 {x['teamGoldDiff']:+,}  죽은 뒤 손해 {x['lostAfter'] or '없음'}")
        P("  스펠: " + ", ".join(f"{s['n']} {s.get('label', '')}({s.get('verdict')})" for s in x["spells"]["list"]) if x["spells"].get("list") else f"  스펠: {x['spells'].get('state')}")
        P("  합류: " + ("  ".join(f"{a['who']['n']} {a['minuteMark']}에 {a['wasAt']}" for a in x.get("roams", [])) or "없음"))
        if x.get("fight"):
            P(f"  교전 {mmss(x['fight']['from'])}~{mmss(x['fight']['to'])} ({x['fight']['to'] - x['fight']['from']}초)")
        if r.get("rows"):
            P(f"  받은 피해 {r['total']:,}: " + "  ".join(f"{w['who']['n']} {w['v']:,}(" + ", ".join(f"{p['n']} {p['v']}" for p in w["parts"][:3]) + ")" + (f" 쓴 것 {[u['n'] for u in w['used']]}" if w["used"] else "") for w in r["rows"]))
        if r.get("me"):
            P(f"  내가 준 피해 {r['me']['v']:,}: " + ", ".join(f"{t['who']['n']} {t['v']:,}" for t in r["me"].get("to", [])))
        elif x.get("damage"):
            P("  받은 피해: " + ", ".join(f"{w['who']['n']} {w['v']:,}" for w in x["damage"]))
        ld = lived.get(round(x["sec"])) or next((v for kk, v in lived.items() if abs(kk - x["sec"]) <= 2), None)
        if ld:
            P("  체력(%): " + " ".join(f"{mmss(p['t'])} {p['hp']}" for p in ld.get("hpFlow", [])))

    B = rep["build"]
    P("\n## 빌드")
    t = B["timeline"]
    P("완성(나): " + "  ".join(f"{ms(i['t'])} {i['item']['n']}" for i in t["me"]))
    gaps = [ms(t["me"][i + 1]["t"] - t["me"][i]["t"]) for i in range(len(t["me"]) - 1)]
    P(f"간격(gapAfter n = n번째와 n+1번째 사이): {gaps}")
    P("완성(상대): " + "  ".join(f"{ms(i['t'])} {i['item']['n']}" for i in t["opp"]))
    P("들고 있던 골드: " + "  ".join(f"{g['min']}분 {g['currentGold']}" for g in ana.get("bankedGold", [])))
    ru = B["runes"]
    P(f"룬: {ru['keystone']['n']} / {', '.join(x['n'] for x in ru['minor'])} / {ru['secondary']['n']}: {', '.join(x['n'] for x in ru['sub'])}")
    P("스펠 사용: " + ", ".join(f"{s['n']} {s['casts']}번" for s in B["spells"]) + "   스킬: " + ", ".join(f"{s['key']} {s['casts']}" for s in B["skills"]) + f"   논타깃 적중 {B['skillshotsHit']} 회피 {B['skillshotsDodged']}")

    pg = ana.get("pings", {})
    lab = {"onMyWayPings": "가고 있음", "getBackPings": "물러나", "assistMePings": "도움 요청", "enemyMissingPings": "적 사라짐",
           "enemyVisionPings": "적 시야", "needVisionPings": "시야 필요", "dangerPings": "위험", "allInPings": "올인", "pushPings": "밀기",
           "holdPings": "대기", "commandPings": "명령", "retreatPings": "후퇴", "visionClearedPings": "시야 제거", "basicPings": "기본"}
    P("\n## 핑: " + ", ".join(f"{lab.get(k, k)} {v}" for k, v in sorted(pg.items(), key=lambda kv: -kv[1]) if v))


if __name__ == "__main__":
    main(sys.argv[1])
