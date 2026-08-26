# 성경읽기 챌린지 텔레그램 봇

매일 한국시간 아침 6시 30분에 자동으로 "어제까지 진행률"과 "오늘의 읽기 분량"을
그룹방에 올리고, 버튼 클릭으로 인증을 받아 Google Sheets에 기록하는 봇입니다.
365일 완주하면 자동으로 축하 메시지를 보내고 조용해집니다.

---

## 파일 구성

| 파일 | 역할 |
|---|---|
| `bot.py` | 봇의 전체 로직 (읽기 계획 계산, 자동 발송, 인증 처리, 명령어, 구글 시트 연동) |
| `requirements.txt` | 필요한 파이썬 패키지 목록 |
| `.env.example` | 필요한 환경변수 견본 (실제 값은 여기 안 넣고 Render에만 등록) |
| `README.md` | 이 문서 |

---

## 명령어

| 명령어 | 설명 |
|---|---|
| `/activate` | 이 그룹방을 매일 알림 받는 방으로 등록 |
| `/setstart YYYY-MM-DD` | 챌린지 시작일 설정 (다시 입력하면 언제든 새로 시작 가능) |
| `/today` | 오늘 분량 + 어제까지 진행률을 즉시 게시 (테스트/확인용, 시간과 무관하게 바로 실행됨) |
| `/progress` | 지금 이 순간 기준 멤버별 진행률 확인 |

매일 한국시간 06:30에 `/today`와 같은 내용이 자동으로 올라옵니다(`daily_job`).
365일째 다음날에는 자동으로 완주 축하 메시지가 한 번 오고, 그 이후엔
새로 `/setstart`를 입력하기 전까지 조용히 대기합니다.

---

## 처음부터 만들기

### 1. 텔레그램 봇 만들기
1. **@BotFather**와 대화 → `/newbot` → 이름/username 설정 → **토큰(BOT_TOKEN)** 발급
2. 그룹방에 봇 초대 (채팅방 정보 → 멤버 추가 → username 검색)
3. **BotFather → `/mybots` → 봇 선택 → Bot Settings → Group Privacy → Turn off**
   - 프라이버시 모드를 꺼두면 그룹 메시지 관련 문제가 줄어듭니다. (단, `/명령어`나
     버튼 클릭은 원래 프라이버시 모드와 무관하게 항상 봇에게 전달됩니다.)

### 2. Google Sheets + 서비스 계정 준비
1. **sheets.google.com**에서 새 스프레드시트 생성 → URL의 `/d/`와 `/edit` 사이 값이
   시트 ID (`GOOGLE_SHEET_ID`)
2. **console.cloud.google.com**에서 새 프로젝트 생성
3. **API 및 서비스 → 라이브러리**에서 `Google Sheets API`, `Google Drive API` 둘 다 **사용(Enable)**
4. **API 및 서비스 → 사용자 인증 정보 → 사용자 인증 정보 만들기 → 서비스 계정** 생성
5. 생성된 서비스 계정 → **키(Keys) → 키 추가 → 새 키 만들기 → JSON** → 다운로드
6. JSON 파일 안의 `client_email` 값을 복사
7. 1번 시트로 돌아가서 **공유** → 그 이메일을 **편집자**로 추가
   - 이 단계를 빠뜨리면 봇이 시트에 접근하지 못해 명령어가 조용히 실패합니다
     (겉으로는 아무 반응도 없어 보여서 원인 찾기 까다로움).

### 3. GitHub에 코드 올리기
1. github.com → 새 저장소 생성 (예: `bible-reading-bot`)
2. 저장소 페이지 → **Add file → Upload files** → `bot.py`, `requirements.txt`,
   `.env.example` 업로드 → **Commit changes**

### 4. Render에 배포
1. **render.com** → GitHub으로 로그인 → **New + → Web Service**
   - Background Worker가 아니라 **Web Service**를 선택해야 무료(Free) 요금제를
     쓸 수 있습니다. (Background Worker는 2026년 기준 무료 옵션이 사라졌습니다.)
2. 저장소 연결 후 설정:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: **`python3 bot.py`**
     - `python`이 아니라 **`python3`**입니다. 오타(`phthon3` 등)로
       `Exited with status 127` 에러가 나는 경우가 실제로 많았습니다. 복사해서
       붙여넣는 걸 추천합니다.
   - Instance Type: **Free**
3. **Environment** 탭에서 아래 값들을 등록:

   | Key | Value |
   |---|---|
   | `BOT_TOKEN` | BotFather에서 받은 토큰 |
   | `GOOGLE_SHEET_ID` | 시트 ID |
   | `GOOGLE_CREDENTIALS_JSON` | 서비스 계정 JSON 파일 전체 내용을 그대로 붙여넣기 |
   | `PYTHON_VERSION` | `3.11.9` |
   | `PYTHONUNBUFFERED` | `1` (로그가 실시간으로 바로 찍히게 함) |

   - Render는 최신 파이썬(3.14 등)을 기본으로 쓰는데, 이게 `python-telegram-bot`
     라이브러리와 충돌해서 `RuntimeError: There is no current event loop in thread
     'MainThread'` 에러가 났습니다. **`PYTHON_VERSION=3.11.9`로 반드시 고정**해주세요.
     (참고로 `runtime.txt` 파일 방식은 Render에서 인식되지 않았습니다.)
   - `GOOGLE_CREDENTIALS_JSON`을 메모장 등으로 복사할 때, 서비스 계정 키 파일이
     여러 개 다운로드되어 있다면 정확히 이번에 만든 파일(안의 `client_email`이
     시트에 공유한 이메일과 일치하는 것)을 사용해야 합니다. 두 파일 내용을
     합쳐서 붙여넣으면 `JSONDecodeError: Extra data`가 납니다.
4. **Deploy** 클릭

### 5. 배포 후 확인
1. **Logs** 탭에서 에러 없이 `헬스체크 서버 시작`, `봇 시작`이 찍히는지 확인
2. 그룹방에서 `/activate` → `/setstart 2026-09-01` → `/today` 순으로 테스트

---

## 문제가 생겼을 때 (실제로 겪었던 것들)

**`Exited with status 127`**
→ Start Command 오타 확인 (`python3 bot.py`가 정확히 맞는지)

**`RuntimeError: There is no current event loop in thread 'MainThread'`**
→ `PYTHON_VERSION=3.11.9` 환경변수가 등록되어 있는지 확인 (Render가 기본으로
너무 최신 파이썬을 쓰면 발생)

**`telegram.error.InvalidToken`**
→ `BOT_TOKEN` 값이 정확한지, 앞뒤 공백이 들어가지 않았는지 확인

**`telegram.error.Conflict: terminated by other getUpdates request`**
→ 같은 토큰으로 두 프로세스가 동시에 폴링 중이라는 뜻. 보통 재배포 직후
1분 이내에 저절로 사라집니다. 계속되면:
- 컴퓨터에서 로컬로 `python bot.py`를 실행 중인 창이 남아있지 않은지 확인
- Render에 서비스가 중복으로 떠 있지 않은지 확인
- 그래도 안 되면 BotFather에서 토큰을 재발급받아 교체 (가장 확실한 해결책)

**`json.decoder.JSONDecodeError: Extra data`**
→ `GOOGLE_CREDENTIALS_JSON`에 잘못된/중복된 내용이 붙여넣어진 것. 서비스 계정
JSON 파일 하나만 정확히 전체 복사해서 다시 붙여넣기

**`/activate` 등 명령어에 봇이 아예 무반응**
→ 웹훅이 남아있는지 확인:
```
https://api.telegram.org/bot<토큰>/getWebhookInfo
```
`"url":""`이 아니면:
```
https://api.telegram.org/bot<토큰>/deleteWebhook?drop_pending_updates=true
```
→ 그래도 안 되면 구글 시트 공유 설정(서비스 계정 이메일이 편집자로 추가됐는지) 재확인
→ Render Logs를 Live tail로 열어두고 실시간으로 어디서 막히는지 확인

**"요청한 파일이 없습니다" (구글 시트 열 때)**
→ `GOOGLE_SHEET_ID` 값이 실제로 존재하는 시트의 ID가 맞는지 재확인

---

## 진행률을 구글 시트에서 표로 보고 싶다면

시트에 `summary`라는 새 탭을 만들고 아래 수식을 넣으면 자동 집계표가 만들어집니다.

- A1: `이름`, B1: `인증일수`, C1: `진행률(%)`, E1: `경과일수`
- F1 (경과일수 계산, 서식을 숫자로 지정해야 함):
  ```
  =TODAY()-DATEVALUE(VLOOKUP("start_date",config!A:B,2,FALSE))+1
  ```
- A2 (이름 자동 추출):
  ```
  =UNIQUE(FILTER(checkins!B2:B,checkins!B2:B<>""))
  ```
- B2 (인증일수):
  ```
  =ARRAYFORMULA(IF(A2:A="","",COUNTIF(checkins!B:B,A2:A)))
  ```
- C2 (진행률%, MIN이 배열과 안 맞아서 IF로 대체):
  ```
  =ARRAYFORMULA(IF(A2:A="","",IFERROR(IF(ROUND(B2:B/$F$1*100,0)>100,100,ROUND(B2:B/$F$1*100,0)),"")))
  ```

---

## 잠들지 않게 하기 (무료 요금제 필수)

Render 무료 Web Service는 15분간 요청이 없으면 잠듭니다. **cron-job.org**에서
무료 계정을 만들고, Render 서비스 주소(`https://서비스이름.onrender.com`)로
10분마다 접속하는 크론잡을 만들어두면 항상 깨어있습니다.

---

## 다른 채팅방에서도 쓰고 싶다면

지금 코드는 하나의 채팅방(하나의 `chat_id`, 하나의 `start_date`)만 지원하도록
되어 있습니다. 다른 그룹방에서도 `/activate`, `/setstart`를 하면 지금 방 설정을
덮어써버립니다.

- **간단한 방법**: 방마다 새 봇 + 새 구글 시트 + 새 Render 서비스를 만들기
  (이 문서 그대로 반복)
- **효율적인 방법**: 코드를 고쳐서 `chat_id`별로 시작일과 인증 기록을 따로
  관리하도록 만들기 (봇 하나로 여러 방 지원 가능, 별도 개발 필요)

## 커스터마이징 아이디어
- 발송 시각 변경: `bot.py`의 `run_daily(..., time=datetime.time(hour=6, minute=30, tzinfo=KST))`
- 특정 요일 쉬기: `daily_job` 맨 앞에서 `today.weekday()` 체크 후 `return`
- 미인증자 저녁 리마인더: 저녁 시간대에 별도 `run_daily` 잡 추가
