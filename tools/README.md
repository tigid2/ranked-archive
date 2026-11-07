# 작업 도구

리포트 생성기, 분석 도구, 기록 프로그램 사본이 있어요. 필요한 파일만 꺼내 쓰고, 큰 파일은 함수 이름으로 grep해서 그 부분만 읽어요.

## 폴더
| 위치 | 내용 |
|---|---|
| `raw/` | 경기 원본(`*.json.gz`), 직접 넣은 게임 중 기록(`*.live.json`) |
| `analysis/` | `analyze.py` 분석 결과(`*.analysis.json`) |
| `feedback/` | 판별 피드백 글(`<경기ID>.json`) |
| `data/` | Data Dragon 데이터(`dd_*.json`), 흑백 지도(`map11_gray.png`) |
| `tools/report/` | 리포트 데이터 만들기 `report_data.py`, artifact용 한 파일 `single.py`, 스타일 `report.css`(React 화면도 이 파일을 그대로 써요), 예전 생성기 `build2.py` |
| `web/` | React 리포트 화면(Vite). 빌드하면 `docs/report/`에 저장돼요. 실험 페이지(`?lab=1`)는 `web/src/lab/`, 데이터는 `tools/report/lab_data.py`. |
| `docs/report-data/` | 판별 리포트 데이터(`<경기ID>.json`, 닉네임 없음)와 목록 `index.json`. 화면이 열릴 때 읽어요. |
| `tools/index/` | 기록 목록(첫 페이지) 시안 |
| `tools/fonts/` | 리포트에 넣는 글꼴 2개(Pretendard, Archivo, 둘 다 OFL) |
| `tools/` | `analyze.py`(분석), `inline_img.py`(예전 생성기 결과에 아이콘을 넣어 한 파일로), `ds_build4.py`(디자인 시스템), `make_gray_map.py`(흑백 지도) |
| `benchmarks/` | 기준 데이터 요약(`<챔피언>.json`)과 판별 숫자 줄(`rows/<챔피언>.jsonl`). 워크플로 "기준 데이터 모으기"가 만들어요. 읽을 때는 요약 파일만 읽어요. |
| `logger/` | PC 기록 프로그램 사본. PC에서 실제로 돌아가는 건 `아카이브\lol-live-logger` 폴더예요. 토큰이 든 `config.json`은 저장소에 넣지 않아요. |

## 할 일별로 꺼낼 파일
| 할 일 | 필요한 파일 |
|---|---|
| 새 판 피드백 쓰기 | `analysis/<경기ID>.analysis.json`, 예시로 `feedback/KR_8448036968.json`, `knowledge/rules.md` (피드백 파일만 올리면 리포트는 워크플로가 다시 만들어요) |
| 리포트 숫자/계산 고치기 | `tools/report/report_data.py` |
| 리포트 화면/디자인 고치기 | `web/src/` 의 해당 섹션 파일, `tools/report/report.css` |
| 기록 목록(첫 페이지) | `tools/index/` |
| 디자인 시스템 artifact | `tools/ds_build4.py`, `tools/report/report.css` |
| 기록 프로그램 | `logger/` |

## 실행 방법
`pip install brotli fonttools pillow --break-system-packages`가 필요해요(한 파일 만들기 글꼴용). React 화면은 Node 22가 필요해요. 모두 저장소 맨 위에서 실행해요.
```
# 분석: 결과는 analysis/ 에 저장
python3 tools/analyze.py raw/KR_8448036968.json.gz Xayah raw/KR_8448036968.live.json data analysis

# 리포트 데이터: raw/ 의 모든 판을 다시 분석하고 docs/report-data/<경기ID>.json 을 만들어요(4판에 1초 안쪽)
python3 tools/report/report_data.py --all
python3 tools/report/report_data.py KR_8448036968        # 한 판만

# React 화면 (web/ 에서). 처음 한 번 npm ci
cd web && npm ci && npm run build && cd ..                # GitHub Pages용 → docs/report/
cd web && npm run build:single && cd ..                   # artifact용 틀 → web/dist-single/
python3 tools/report/single.py KR_8448036968              # artifact에 올릴 한 파일 → tools/report/KR_8448036968_single.html
python3 tools/report/single.py KR_8448036968 --lab        # 실험 페이지 한 파일 → tools/report/KR_8448036968_lab_single.html

# 기준 데이터: 저장소 원본 경기로 뽑기 시험(키 필요 없음) / 쌓인 줄로 요약만 다시 만들기
python3 scripts/benchmarks.py test
python3 scripts/benchmarks.py summarize

# 기록 목록 시안
python3 tools/index/build_index.py . tools/report /tmp/index.html
```
- 리포트 주소: `https://tigid2.github.io/ranked-archive/report/?id=<경기ID>`. 화면은 열릴 때 `docs/report-data/<경기ID>.json`을 읽어요. 그래서 새 판이 들어와도 화면을 다시 빌드하지 않아요.
- 챔피언, 티어/LP는 `docs/data/games.json`에서 가져와요(예전처럼 환경 변수로 넣지 않아요).
- 피드백 파일이 없으면 숫자 리포트만 나와요(요약·체크리스트 칸은 "아직 없어요", 죽음은 모두 카드로).
- 아이콘은 데이터에 Data Dragon CDN 기준 경로(`img` 칸)로만 들어 있어요. 사이트는 CDN 주소를 붙이고, `single.py`는 미러에서 받아 파일 안에 넣어요(캐시는 `tools/report/img/`).
- 스킬 아이콘에 `data/dd_champ_<챔피언>.json`이 필요해요. 지금은 카이사, 자야만 있어요. 없으면 글자(QWER)만 나와요.
- 만들어진 한 파일 html, 아이콘 캐시, `web/node_modules`, `web/dist-single`은 저장소에 올리지 않아요(`.gitignore`). `docs/report/`(Pages용 빌드)는 올려요.

## 워크플로
- "경기 기록 갱신": 경기를 받은 뒤 `report_data.py --all`까지 돌려서 새 판 리포트 데이터를 같이 저장해요.
- "리포트 만들기"(`report.yml`): `feedback/`, `web/`, `tools/report/`, `tools/analyze.py`, `benchmarks/*.json`을 올리면 자동으로 돌아요. 리포트 데이터와 화면을 다시 만들어 저장해요. 손으로도 실행할 수 있어요.

## React 화면 파일 (web/src/)
- `main.jsx` 데이터 읽기, `Report.jsx` 페이지 조립과 메뉴, `ui.jsx` 공통 조각(아이콘, 숫자 모양, 비교 막대)
- `sections/`: `Hero` / `Summary`(01) / `Flow`(02, 골드 차트 `GoldChart`) / `Lane`(03) / `Deaths`(04, 지도 `DeathMap`, 카드 `DeathCard`) / `Team`(05) / `Build`(06) / `Check`(07 체크리스트, 08 메모)

## report_data.py 함수 위치
- 아이콘 정보 `champ`, `item`, `spell`, `perk`, 본체 `build`(섹션별로 hero/flow/lane/deaths/team/build 칸을 만듦), 유불리 구간 `swings`, 죽을 때 스펠 `death_spells`, 분석 다시 돌리기 `run_analyze`

## build2.py (예전 생성기)
React 화면이 같은 결과를 내는 걸 확인했어요(11-08, 카이사·자야 판 스크린샷 비교). 지금은 `ds_build4.py`(디자인 시스템)가 이 파일을 불러 써서 남겨 뒀어요. 디자인 시스템을 다시 정할 때 같이 지워요.
예전 실행 방법: `RA_MID=… RA_CHAMP=… RA_TIER=… RA_LP=… RA_OUT=x.html python3 tools/report/build2.py local`

### build2.py 함수 위치 (grep으로 찾기)
- 아이콘/이름: `asset`, `gray_map`, `cimg`
- 계산: `pf`, `purchases`, 오브젝트 정리 `merge_grubs`
- 히어로 `hero` / 01 요약 `sec_summary`
- 02 흐름: `gold_chart`, `swings`, `focus_stats`, `flow_extra`, `sec_flow`
- 03 라인전: `sup_block`, `bot_kills_fact`, `sec_lane`
- 04 죽음: `death_map`, `death_spells`, `sec_deaths`
- 05 팀 `sec_team` / 06 빌드 `item_timeline`, `sec_build` / 07 체크리스트 `sec_check` / 08 메모 `sec_memo`
- 페이지 조립 `page`, 글꼴 넣기 `embed`

`analyze.py`: 본체 `analyze`, 라인전 서폿/바텀 원딜 킬 `lane_support`, 기준 데이터 대비 `vs_benchmark`(결과의 `benchmark` 칸)

`scripts/benchmarks.py`: 한 판에서 숫자 뽑기 `extract_row`, 요약 `summarize`, 수집 `collect`/`find_games`, 요청 속도 `Limiter`

## 알아 둘 것
- 기준 데이터의 이 판 숫자는 `analyze.py`가 `scripts/benchmarks.py`의 `extract_row`를 그대로 불러서 계산해요. 계산 방법을 바꿀 때는 `extract_row` 한 곳만 고치고 `summarize`로 요약을 다시 만들어요.
- 기준 데이터의 티어는 "판을 찾은 참가자"의 티어예요. 그 판의 원딜 티어를 따로 확인하지는 않아요(요청 수를 아끼려고).
- 자야 판 게임 중 기록은 PC에서 직접 가져와서 `raw/KR_8448036968.live.json`에 있어요(`live/`에 두면 갱신 워크플로가 지워요). 28:45 죽음은 골드 1,465와 체력 흐름(67% → 2%), 23:53 죽음은 골드 1,925만 있어요.
- 카이사 판도 서폿 칸이 나와요(서폿 있을 때 CS 51 : 72, 없을 때 34 : 25, 바텀 원딜 킬 2 : 3). 카이사 피드백 글은 이 규칙으로 아직 다시 보지 않았어요.
- `analyze.py` 버그: 역할 퀘스트 신발의 완성 시간이 틀려요.
- `ds_build4.py`는 아직 v1 디자인 기준이라 지금 `report.css`(v4)로 돌리면 "색 빠짐"으로 멈춰요. 디자인 시스템을 v4로 갱신할 때 같이 고쳐요.
