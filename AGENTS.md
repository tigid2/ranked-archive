# AGENTS.md — 이 저장소에서 일하는 Claude가 먼저 읽는 규칙

## 항상 지키는 규칙 (어떤 작업이든 이 칸은 꼭 먼저 읽어요)
문서를 필요한 부분만 읽거나 아예 안 읽는 작업이라도 이 칸은 읽어요. 정말 중요한 규칙만 여기에 두고, 새로 생기면 여기에 더해요(11-21 사용자 요청).
1. **답은 항상 한국어로 해요.** 작업 보고와 짧은 답까지 모두요(11-19).
2. **리포트 화면 글자에 가운뎃점(·)을 쓰지 않아요.** "/"나 쉼표를 써요(11-20 다시 강조).
3. **공개하지 않는 판(`tools/report/public.json`에 없는 판)의 피드백 글은 저장소에 올리지 않아요.** PC `ranked-archive-workfiles\feedback\`에 두고, 리포트를 만들 때만 `tools/report/private-feedback/`에 복사해요(11-19).
4. **API 키와 GitHub 토큰은 어디에도 적지 않아요.** 기록 프로그램 `config.json`은 토큰이 있어서 읽지도 올리지도 않아요.
5. **리포트를 달라고 하면 피드백 글까지 끝낸 뒤 한 번에 줘요.** artifact 제목은 "리포트 - 내 챔피언 vs 상대 챔피언 · 월.일 시:분 승리/패배"(제목만 예외로 가운뎃점을 써요), 답 맨 마지막 줄에 그 이름만 적어요.
6. **PC 폴더와 저장소 쓰기 같은 허용은 작업을 시작할 때 한 번에 요청해요.** 막히면 거부됐다고 알리기만 하지 말고 필요한 허용을 부탁해요.

## 리포트 만들기 순서 (토큰 아끼는 순서, 11-21)
1. `git clone --depth 20` → `raw/`에서 최신 경기 ID 확인 → `python3 tools/report/report_data.py <ID>`
2. `python3 tools/report/fb_brief.py <ID> > /tmp/brief.txt` 를 실행하고 **이 파일 하나만** 읽어요. 데이터 구조를 이리저리 조회하지 않아요.
3. 피드백 글을 쓸 때 `knowledge/rules.md`는 통째로 읽지 않고 "글쓰기", "메모", "체크리스트"와 그 판에 필요한 장만 찾아 읽어요. 예시 피드백 파일은 읽지 않아요(형식은 아래).
4. 피드백을 `tools/report/private-feedback/<ID>.json`(공개 판은 `feedback/`)에 쓴 뒤 `bash tools/report/make_report.sh <ID>` **한 번만** 실행해요(데이터, 화면 빌드, 한 파일 리포트를 한꺼번에).
5. Playwright로 글자와 오류만 확인하고(스크린샷 X) `publish_files`로 올려요. 비공개 판 피드백은 PC `ranked-archive-workfiles\feedback\`에도 저장해요.
- 피드백 파일 형식: `summary`, `keyFixes[{title, body}]`(2개), `checklist[{mark: good|mid|bad|memo, name, why}]`(원딜 9개, 이름은 rules.md 체크리스트 그대로), `laneText`, `moments[{t, text, key?, crit?: good|bad}]`, `keyDeaths[{t, what, evidence, next}]`, `otherDeaths {}`, `build{아이템, 룬, 소환사 주문, gapAfter}`, `takeaway`, `memo{principle, kept, scene, questions[{q, a}], free}`, `swings{"<flow swings m0>": 글}`, `focus`.

롤 솔로 랭크 한 판마다 자세한 피드백을 만들어 쌓는 개인 프로젝트예요. 사용자는 플래티넘 원딜, 1차 목표는 에메랄드예요.

## 토큰 쓰는 원칙
- 필요한 파일만 읽어요. 큰 파일은 함수 위치를 grep으로 찾아서 그 부분만 읽어요.
- 리포트 HTML(아이콘과 글꼴이 들어 있어 수 MB)과 `docs/report/` 빌드 파일은 읽지 않아요. 리포트는 숫자 계산이 `tools/report/report_data.py`, 화면이 `web/src/`예요. 피드백 파일을 올리면 워크플로 "리포트 만들기"가 리포트를 다시 만들어요.
- 기준 데이터는 원본 경기를 읽지 말고 `benchmarks/`의 요약 파일만 읽어요.
- 토큰은 적게 들지만 결과가 틀릴 위험이 있는 방법은 먼저 사용자에게 물어봐요.
- 새 판 피드백은 판마다 새 대화에서 써요. 피드백에 쓸 숫자는 `tools/report/fb_brief.py`의 요약 한 장만 읽어요(11-21).

## 지키는 규칙
- 공개하지 않는 판(`tools/report/public.json`에 없는 판)의 피드백 글은 저장소에 올리지 않아요(11-19 사용자 요청). PC `ranked-archive-workfiles\feedback\`에 쓰고, 리포트를 만들 때 `tools/report/private-feedback/`에 복사해요. `.gitignore`가 막고 있으니 `git add -f`로 우회하지 않아요.
- API 키와 GitHub 토큰은 어디에도 적지 않아요. 기록 프로그램의 `config.json`은 저장소에 올리지 않아요.
- 유튜브 자막 같은 남의 글 원문은 저장소에 넣지 않아요(공개 저장소). 제 말로 바꾼 짧은 규칙과 출처 링크만 넣어요.
- 통계 사이트(lolalytics, 딥롤, OP.GG 등) 숫자는 최대한 가져다 써요(11-08 사용자가 넓힘). 패치마다 한 번, 내장 브라우저로 읽어서 숫자만 `benchmarks/sites/`에 저장해요. 워크플로로 자동으로 긁어 오지는 않아요(약관·차단). 리포트 화면에는 출처를 적지 않고, 데이터 파일에 사이트, 패치, 가져온 날짜를 적어요. 백분위와 10/15분 성장 지표는 계속 우리 데이터(Riot API)로 계산해요.
- 딥롤 상성 요약은 "최상위 티어에서 배운다" 규칙의 예외로 써요. 원문은 넣지 않고 제 말로 줄여서 "딥롤 요약 기반"으로 표시해요.
- 성장 지표(10/15분 CS, 골드, 아이템 완성 시간 등)는 Riot API로 직접 모아서 계산해요.
- 롤 지식(판단 규칙)은 최상위 티어의 강의/플레이에서 그대로 가져와요. 플래티넘 티어에 따른 시사점이 따로 있을 때만 그 규칙에 한 줄 덧붙여요. 비교용 숫자의 기준 티어(에메랄드~다이아)와는 별개예요.
- 피드백은 세 칸으로 나눠요: 자동 진단(규칙 + 정해진 문장, 토큰 0) / 확인 필요(규칙이 걸렸지만 해석이 갈림) / 판단(Claude가 씀). 자동 규칙은 `knowledge/auto-rules.md`에 있고, 규칙을 계속 고쳐 나가는 방법도 거기에 있어요.
- 피드백 글쓰기 규칙과 판단 규칙은 `knowledge/rules.md`에 있어요. 사용자가 바로잡은 내용은 근거와 함께 거기에 넣어요. 강의에서 나온 후보는 PC 작업 폴더의 `lectures/rule-candidates.md`에 두고, 채택된 것만 `rules.md`로 옮겨요(수집 방식은 그 폴더의 `lectures/README.md`).

## 작업 도구
폴더 구성, 실행 방법, 함수 위치는 `tools/README.md`를 보세요.

## 지금 진행 중인 계획
`notes/plan-2026-11.md`를 보세요.
