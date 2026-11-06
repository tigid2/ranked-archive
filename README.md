# 랭크 셀프 피드백 아카이브

솔로랭크 게임이 끝날 때마다 버튼을 눌러 경기 기록을 정리하는 개인용 저장소예요.

## 갱신하는 방법

1. 저장소 위쪽의 **Actions** 탭을 눌러요.
2. 왼쪽에서 **경기 기록 갱신**을 고르고, 오른쪽의 **Run workflow** 버튼을 눌러요.
3. 2~5분 뒤에 웹페이지에 새 판이 올라와요.

## 처음 한 번만 하는 설정

- Settings → Secrets and variables → Actions
  - **Secrets** 탭: `RIOT_API_KEY` 에 라이엇 개인 API 키
  - **Variables** 탭: `RIOT_ID` 에 `소환사명#태그`
- Settings → Pages: Source를 **Deploy from a branch**, 브랜치 `main`, 폴더 `/docs` 로 설정

## 만들어지는 파일

- `docs/index.html` : 전체 기록 페이지
- `docs/latest.md` : 가장 최근 판 리포트
- `docs/games/경기ID.md` : 판별 리포트
- `docs/data/*.json` : 기록 데이터
