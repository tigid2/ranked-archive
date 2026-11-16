# 통계 사이트 숫자 가져오기

패치마다 한 번, 내장 브라우저로 사람이 보듯 한 페이지씩 읽어서 숫자만 `benchmarks/sites/`에 저장해요. 워크플로로 자동으로 긁지 않아요.

| 사이트 | 읽는 페이지 | 가져오는 것 | 저장 |
|---|---|---|---|
| lolalytics (전 세계, 에메랄드+) | `lolalytics.com/lol/<챔피언>/build/?tier=emerald_plus` | 승률·픽률, 상대 원딜별 승률, 코어 칸별 선택률·승률·평균 완성 분, 신발, 구매 순서, 룬, 스펠, 게임 길이별 승률, 첫 오브젝트 승률, 챔피언 평균 | `benchmarks/sites/lolalytics/<챔피언>.json` |
| LOL.PS (한국, 에메랄드+) | `lol.ps/champ/<번호>` | 14분 킬·죽음·도움·CS·포탑 방패·분당 피해 평균, 상대 원딜별 승률과 2·3·6레벨 선점 비율 | `benchmarks/sites/lolps.json` |

- lolalytics: 페이지를 열고 `tools/sites/lolalytics.js`를 실행하면 숫자만 담은 JSON이 나와요. 저장할 때는 필요한 줄만 줄여서 넣어요(파일의 `_meta.format` 참고).
- LOL.PS: 페이지가 스스로 읽는 숫자(`lane-phase`, `versus`, `champ-lane-features`)를 그대로 옮겨요.
- 지금 있는 챔피언: 징크스, 자야 (패치 16.22, 2026-11-16). 애쉬·미스 포츈은 아직이에요.
- 딥롤은 상성 승률·서폿 궁합이 있지만 위 두 곳과 겹쳐서 저장하지 않았어요. 레벨별 상대법 글은 빌드 페이지에서 찾지 못했어요.
- 쓰는 곳: `tools/report/site_data.py` → 실험 리포트의 `lab.site`.
