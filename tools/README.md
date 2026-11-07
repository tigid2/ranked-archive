# 작업 도구

리포트 생성기, 분석 도구, 기록 프로그램 사본이 있어요. 필요한 파일만 꺼내 쓰고, 큰 파일은 함수 이름으로 grep해서 그 부분만 읽어요.

## 폴더
| 위치 | 내용 |
|---|---|
| `raw/` | 경기 원본(`*.json.gz`), 직접 넣은 게임 중 기록(`*.live.json`) |
| `analysis/` | `analyze.py` 분석 결과(`*.analysis.json`) |
| `feedback/` | 판별 피드백 글(`<경기ID>.json`) |
| `data/` | Data Dragon 데이터(`dd_*.json`), 흑백 지도(`map11_gray.png`) |
| `tools/report/` | 리포트 생성기 `build2.py`, 스타일 `report.css` |
| `tools/index/` | 기록 목록(첫 페이지) 시안 |
| `tools/fonts/` | 리포트에 넣는 글꼴 2개(Pretendard, Archivo, 둘 다 OFL) |
| `tools/` | `analyze.py`(분석), `inline_img.py`(아이콘을 넣어 한 파일로), `ds_build4.py`(디자인 시스템), `make_gray_map.py`(흑백 지도) |
| `logger/` | PC 기록 프로그램 사본. PC에서 실제로 돌아가는 건 `아카이브\lol-live-logger` 폴더예요. 토큰이 든 `config.json`은 저장소에 넣지 않아요. |

## 할 일별로 꺼낼 파일
| 할 일 | 필요한 파일 |
|---|---|
| 새 판 피드백 쓰기 | `raw/`, `tools/analyze.py`, `data/dd_*.json`, 예시로 `feedback/KR_8448036968.json`, `knowledge/rules.md` |
| 리포트 만들기/디자인 고치기 | `tools/report/`, `feedback/`, `analysis/`, `tools/inline_img.py` |
| 기록 목록(첫 페이지) | `tools/index/` |
| 디자인 시스템 artifact | `tools/ds_build4.py`, `tools/report/report.css` |
| 기록 프로그램 | `logger/` |

## 실행 방법
`pip install brotli fonttools pillow --break-system-packages`가 필요해요. 모두 저장소 맨 위에서 실행해요.
```
# 분석: 결과는 analysis/ 에 저장
python3 tools/analyze.py raw/KR_8448036968.json.gz Xayah raw/KR_8448036968.live.json data analysis

# 리포트: 피드백은 feedback/<경기ID>.json 을 자동으로 읽어요. 결과는 tools/report/ 에 저장
RA_MID=KR_8448036968 RA_CHAMP=Xayah RA_TIER="플래티넘 4" RA_LP=49 RA_OUT=xayah.html python3 tools/report/build2.py local
python3 tools/inline_img.py tools/report/xayah.html tools/report/xayah_single.html   # artifact에 올릴 한 파일

# 기록 목록 시안
python3 tools/index/build_index.py . tools/report /tmp/index.html
```
- 판마다 바꾸는 값은 환경 변수로 넣어요: `RA_MID`, `RA_CHAMP`, `RA_TIER`, `RA_LP`, `RA_OUT`. 다른 피드백 파일을 쓰려면 `RA_FB`.
- `local` 모드는 아이콘을 `tools/report/img/`에 내려받아요. `cdn` 모드는 GitHub Pages용이에요(아이콘은 Data Dragon 주소, 지도는 파일 안에 넣음). `RA_NOLINK=1`이면 메뉴 이동을 막아요(미리보기용).
- 스킬 아이콘에 `data/dd_champ_<챔피언>.json`이 필요해요. 지금은 카이사, 자야만 있어요.
- 만들어진 html과 아이콘 캐시는 저장소에 올리지 않아요(`.gitignore`).

## build2.py 함수 위치 (grep으로 찾기)
- 아이콘/이름: `asset`, `gray_map`, `cimg`
- 계산: `pf`, `purchases`, 오브젝트 정리 `merge_grubs`
- 히어로 `hero` / 01 요약 `sec_summary`
- 02 흐름: `gold_chart`, `swings`, `focus_stats`, `flow_extra`, `sec_flow`
- 03 라인전: `sup_block`, `bot_kills_fact`, `sec_lane`
- 04 죽음: `death_map`, `death_spells`, `sec_deaths`
- 05 팀 `sec_team` / 06 빌드 `item_timeline`, `sec_build` / 07 체크리스트 `sec_check` / 08 메모 `sec_memo`
- 페이지 조립 `page`, 글꼴 넣기 `embed`

`analyze.py`: 본체 `analyze`, 라인전 서폿/바텀 원딜 킬 `lane_support`

## 알아 둘 것
- 자야 판 게임 중 기록은 PC에서 직접 가져와서 `raw/KR_8448036968.live.json`에 있어요(`live/`에 두면 갱신 워크플로가 지워요). 28:45 죽음은 골드 1,465와 체력 흐름(67% → 2%), 23:53 죽음은 골드 1,925만 있어요.
- 카이사 판도 서폿 칸이 나와요(서폿 있을 때 CS 51 : 72, 없을 때 34 : 25, 바텀 원딜 킬 2 : 3). 카이사 피드백 글은 이 규칙으로 아직 다시 보지 않았어요.
- `analyze.py` 버그: 역할 퀘스트 신발의 완성 시간이 틀려요.
- `ds_build4.py`는 아직 v1 디자인 기준이라 지금 `report.css`(v4)로 돌리면 "색 빠짐"으로 멈춰요. 디자인 시스템을 v4로 갱신할 때 같이 고쳐요.
