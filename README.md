# 성경읽기 챌린지 텔레그램 봇

매일 자동으로 오늘의 읽기 분량을 그룹방에 올리고, 버튼 클릭으로 인증을 받아
Google Sheets에 기록하는 봇입니다.

## 1. 텔레그램 봇 만들기
1. 텔레그램에서 **@BotFather** 검색 → `/newbot` 실행
2. 봇 이름, username 설정 후 나오는 **토큰**을 복사 (`BOT_TOKEN`)
3. 그룹방에 봇을 초대

## 2. Google Sheets 준비
1. https://sheets.google.com 에서 새 스프레드시트 생성 → URL의 시트 ID 복사
   (`https://docs.google.com/spreadsheets/d/여기부분/edit`) → `GOOGLE_SHEET_ID`
2. https://console.cloud.google.com 에서 프로젝트 생성
3. **API 및 서비스 > 라이브러리**에서 `Google Sheets API`, `Google Drive API` 활성화
4. **사용자 인증 정보 > 서비스 계정 만들기** → 키(JSON) 생성 및 다운로드
5. 다운로드한 JSON 파일을 열어 안의 `client_email` 값을 복사
6. 1번에서 만든 스프레드시트를 열어 **공유** → 방금 복사한 이메일을 **편집자**로 추가
7. JSON 파일 전체 내용을 한 줄 문자열로 → `GOOGLE_CREDENTIALS_JSON`

## 3. 로컬에서 테스트 (선택)
```bash
pip install -r requirements.txt
export BOT_TOKEN="..."
export GOOGLE_SHEET_ID="..."
export GOOGLE_CREDENTIALS_JSON='{"type": "service_account", ...}'
python bot.py
```
그룹방에서 `/activate` → `/setstart 2026-09-01` → `/today` 순서로 테스트하세요.

## 4. 24시간 배포하기 (Render.com 예시, 무료 가능)
1. 이 폴더를 GitHub 저장소로 올림
2. https://render.com 가입 → **New > Background Worker** 선택
3. GitHub 저장소 연결
4. Build Command: `pip install -r requirements.txt`
5. Start Command: `python bot.py`
6. Environment 탭에서 `BOT_TOKEN`, `GOOGLE_SHEET_ID`, `GOOGLE_CREDENTIALS_JSON` 세 개 등록
7. Deploy → 로그에 "봇 시작"이 뜨면 완료

> Background Worker 타입을 쓰는 이유: 이 봇은 웹훅이 아닌 폴링 방식이라
> 상시 실행되는 워커 형태가 웹 서비스보다 적합하고 설정이 단순합니다.

## 5. 사용법 (그룹방 안에서)
| 명령어 | 설명 |
|---|---|
| `/activate` | 이 방을 매일 알림 받는 방으로 등록 |
| `/setstart 2026-09-01` | 챌린지 시작일 설정 |
| `/today` | 오늘 분량 즉시 게시 (버튼 포함) |
| `/progress` | 멤버별 인증 진행률 확인 |

매일 06:00(서버 시간 기준)에 자동으로 오늘 분량 메시지가 올라오고,
멤버들이 "✅ 오늘 읽었어요" 버튼을 누르면 자동으로 인증 기록됩니다.
시간대를 한국시간(KST) 기준으로 정확히 맞추려면 `bot.py`의
`run_daily(..., time=...)` 부분에 타임존을 지정하거나 서버 시간대를 Asia/Seoul로 설정하세요.

## 커스터마이징 아이디어
- `/progress`를 이름순 정렬로 바꾸고 싶다면 `sorted(counts.items(), key=lambda x: x[0])`로 변경
- 특정 요일은 쉬고 싶다면 `daily_job`에서 요일 체크 후 return
- 인증 안 한 사람에게 리마인더를 보내고 싶다면 저녁 시간에 별도 `run_daily` 잡 추가 가능
