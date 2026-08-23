"""
성경읽기 챌린지 텔레그램 봇
- 매일 정해진 시간에 그룹방에 오늘의 읽기 분량을 올리고
- 멤버들이 버튼을 눌러 인증하면 Google Sheets에 기록합니다.

필요한 것:
  - BOT_TOKEN            : BotFather에서 발급받은 토큰
  - GOOGLE_SHEET_ID       : 기록용 구글 시트 ID
  - GOOGLE_CREDENTIALS_JSON : 서비스 계정 키(JSON) 전체 내용을 문자열로

명령어:
  /activate   : 이 그룹을 매일 알림을 받을 방으로 등록 (그룹방에서 실행)
  /setstart YYYY-MM-DD : 챌린지 시작일 설정
  /today      : 오늘 분량 즉시 게시 (테스트용)
  /progress   : 멤버별 진행률 확인
"""

import os
import json
import datetime
import logging

import gspread
from google.oauth2.service_account import Credentials
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, ContextTypes
)

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("bible-bot")

# ---------- 성경 읽기 계획 계산 (웹앱과 동일한 로직) ----------

OT_BOOKS = [
    ("창세기", 50), ("출애굽기", 40), ("레위기", 27), ("민수기", 36), ("신명기", 34),
    ("여호수아", 24), ("사사기", 21), ("룻기", 4), ("사무엘상", 31), ("사무엘하", 24),
    ("열왕기상", 22), ("열왕기하", 25), ("역대상", 29), ("역대하", 36), ("에스라", 10),
    ("느헤미야", 13), ("에스더", 10), ("욥기", 42), ("시편", 150),
    ("전도서", 12), ("아가", 8), ("이사야", 66), ("예레미야", 52), ("예레미야애가", 5),
    ("에스겔", 48), ("다니엘", 12), ("호세아", 14), ("요엘", 3), ("아모스", 9),
    ("오바댜", 1), ("요나", 4), ("미가", 7), ("나훔", 3), ("하박국", 3),
    ("스바냐", 3), ("학개", 2), ("스가랴", 14), ("말라기", 4),
]
NT_BOOKS = [
    ("마태복음", 28), ("마가복음", 16), ("누가복음", 24), ("요한복음", 21), ("사도행전", 28),
    ("로마서", 16), ("고린도전서", 16), ("고린도후서", 13), ("갈라디아서", 6), ("에베소서", 6),
    ("빌립보서", 4), ("골로새서", 4), ("데살로니가전서", 5), ("데살로니가후서", 3), ("디모데전서", 6),
    ("디모데후서", 4), ("디도서", 3), ("빌레몬서", 1), ("히브리서", 13), ("야고보서", 5),
    ("베드로전서", 5), ("베드로후서", 3), ("요한1서", 5), ("요한2서", 1), ("요한3서", 1),
    ("유다서", 1), ("요한계시록", 22),
]
TOTAL_DAYS = 365


def build_sequence(books):
    seq = []
    for name, chapters in books:
        for c in range(1, chapters + 1):
            seq.append((name, c))
    return seq


def distribute(seq, days):
    total = len(seq)
    result = []
    prev = 0
    for d in range(1, days + 1):
        idx = round(total * d / days)
        result.append(seq[prev:idx])
        prev = idx
    return result


OT_PLAN = distribute(build_sequence(OT_BOOKS), TOTAL_DAYS)
NT_PLAN = distribute(build_sequence(NT_BOOKS), TOTAL_DAYS)


def format_chunk(chunk):
    if not chunk:
        return None
    parts = []
    cur_book, start, end = chunk[0][0], chunk[0][1], chunk[0][1]
    for book, ch in chunk[1:]:
        if book == cur_book and ch == end + 1:
            end = ch
        else:
            parts.append(f"{cur_book} {start}장" if start == end else f"{cur_book} {start}~{end}장")
            cur_book, start, end = book, ch, ch
    parts.append(f"{cur_book} {start}장" if start == end else f"{cur_book} {start}~{end}장")
    return ", ".join(parts)


def proverbs_chapter(date_obj):
    dom = date_obj.day
    return dom if dom <= 31 else None


def get_plan_day_index(date_obj, start_date):
    idx = (date_obj - start_date).days + 1
    if idx < 1:
        return None
    return min(idx, TOTAL_DAYS)


def build_today_text(date_obj, start_date):
    idx = get_plan_day_index(date_obj, start_date)
    weekday = ["월", "화", "수", "목", "금", "토", "일"][date_obj.weekday()]
    header = f"📖 {date_obj.year}.{date_obj.month}.{date_obj.day} ({weekday})"
    if idx is None:
        return f"{header}\n아직 챌린지 시작 전입니다. (시작일: {start_date})", idx
    ot = format_chunk(OT_PLAN[idx - 1])
    nt = format_chunk(NT_PLAN[idx - 1])
    prov = proverbs_chapter(date_obj)
    lines = [header, f"DAY {idx} / {TOTAL_DAYS}", ""]
    lines.append(f"구약 · {ot if ot else '오늘 분량 없음'}")
    lines.append(f"신약 · {nt if nt else '쉬어가는 날'}")
    lines.append(f"잠언 · {prov}장" if prov else "잠언 · -")
    return "\n".join(lines), idx


# ---------- Google Sheets 연동 ----------

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


def get_sheet():
    creds_json = os.environ["GOOGLE_CREDENTIALS_JSON"]
    creds_dict = json.loads(creds_json)
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    gc = gspread.authorize(creds)
    sh = gc.open_by_key(os.environ["GOOGLE_SHEET_ID"])
    return sh


def ensure_worksheets(sh):
    titles = [ws.title for ws in sh.worksheets()]
    if "config" not in titles:
        ws = sh.add_worksheet("config", rows=10, cols=2)
        ws.update("A1:B1", [["key", "value"]])
    if "checkins" not in titles:
        ws = sh.add_worksheet("checkins", rows=1000, cols=3)
        ws.update("A1:C1", [["date", "name", "user_id"]])


def get_config_value(sh, key, default=None):
    ws = sh.worksheet("config")
    records = ws.get_all_records()
    for row in records:
        if row.get("key") == key:
            return row.get("value")
    return default


def set_config_value(sh, key, value):
    ws = sh.worksheet("config")
    records = ws.get_all_records()
    for i, row in enumerate(records, start=2):
        if row.get("key") == key:
            ws.update(f"B{i}", [[value]])
            return
    ws.append_row([key, value])


def add_checkin(sh, date_str, name, user_id):
    ws = sh.worksheet("checkins")
    records = ws.get_all_records()
    for row in records:
        if row.get("date") == date_str and str(row.get("user_id")) == str(user_id):
            return False  # 이미 인증함
    ws.append_row([date_str, name, str(user_id)])
    return True


def get_all_checkins(sh):
    ws = sh.worksheet("checkins")
    return ws.get_all_records()


# ---------- 텔레그램 핸들러 ----------

def kst_today():
    # 필요하면 실제 타임존 라이브러리로 교체하세요. 여기선 서버 로컬 시간 기준.
    return datetime.date.today()


async def cmd_activate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sh = get_sheet()
    ensure_worksheets(sh)
    chat_id = update.effective_chat.id
    set_config_value(sh, "chat_id", str(chat_id))
    await update.message.reply_text("이 방이 성경읽기 챌린지 알림방으로 등록되었습니다 ✅\n/setstart YYYY-MM-DD 로 시작일을 설정해주세요.")


async def cmd_setstart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sh = get_sheet()
    ensure_worksheets(sh)
    if not context.args:
        await update.message.reply_text("사용법: /setstart 2026-09-01")
        return
    date_str = context.args[0]
    try:
        datetime.date.fromisoformat(date_str)
    except ValueError:
        await update.message.reply_text("날짜 형식이 올바르지 않습니다. 예: 2026-09-01")
        return
    set_config_value(sh, "start_date", date_str)
    await update.message.reply_text(f"챌린지 시작일이 {date_str} 로 설정되었습니다.")


async def post_today_message(chat_id, context: ContextTypes.DEFAULT_TYPE, sh, start_date):
    today = kst_today()
    text, idx = build_today_text(today, start_date)
    if idx is None:
        await context.bot.send_message(chat_id=chat_id, text=text)
        return
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ 오늘 읽었어요", callback_data=f"check:{today.isoformat()}")
    ]])
    await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=keyboard)


async def cmd_today(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sh = get_sheet()
    ensure_worksheets(sh)
    start_date_str = get_config_value(sh, "start_date")
    if not start_date_str:
        await update.message.reply_text("먼저 /setstart YYYY-MM-DD 로 시작일을 설정해주세요.")
        return
    start_date = datetime.date.fromisoformat(start_date_str)
    await post_today_message(update.effective_chat.id, context, sh, start_date)


async def daily_job(context: ContextTypes.DEFAULT_TYPE):
    sh = get_sheet()
    ensure_worksheets(sh)
    chat_id = get_config_value(sh, "chat_id")
    start_date_str = get_config_value(sh, "start_date")
    if not chat_id or not start_date_str:
        return
    start_date = datetime.date.fromisoformat(start_date_str)
    await post_today_message(int(chat_id), context, sh, start_date)


async def on_check_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    _, date_str = query.data.split(":")
    user = query.from_user
    name = user.full_name or user.username or str(user.id)

    sh = get_sheet()
    ensure_worksheets(sh)
    added = add_checkin(sh, date_str, name, user.id)

    if added:
        await query.answer("인증 완료! 📖")
    else:
        await query.answer("이미 인증하셨어요 :)")

    # 현재까지 인증한 사람 이름을 버튼 아래 텍스트에 반영
    records = get_all_checkins(sh)
    names_today = sorted({r["name"] for r in records if r["date"] == date_str})
    base_text = query.message.text.split("\n\n---")[0]
    new_text = base_text + "\n\n---\n✅ 인증: " + (", ".join(names_today) if names_today else "-")
    try:
        await query.edit_message_text(
            text=new_text,
            reply_markup=query.message.reply_markup
        )
    except Exception as e:
        log.warning("메시지 수정 실패: %s", e)


async def cmd_progress(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sh = get_sheet()
    ensure_worksheets(sh)
    start_date_str = get_config_value(sh, "start_date")
    if not start_date_str:
        await update.message.reply_text("먼저 /setstart YYYY-MM-DD 로 시작일을 설정해주세요.")
        return
    start_date = datetime.date.fromisoformat(start_date_str)
    today = kst_today()
    elapsed = max((today - start_date).days + 1, 1)

    records = get_all_checkins(sh)
    counts = {}
    for r in records:
        d = datetime.date.fromisoformat(r["date"])
        if start_date <= d <= today:
            counts[r["name"]] = counts.get(r["name"], 0) + 1

    if not counts:
        await update.message.reply_text("아직 인증 기록이 없습니다.")
        return

    rows = sorted(counts.items(), key=lambda x: (-x[1], x[0]))
    lines = [f"📊 진행률 (경과 {elapsed}일 기준)\n"]
    for name, cnt in rows:
        pct = min(100, round(cnt / elapsed * 100))
        lines.append(f"{name} — {cnt}일 인증 ({pct}%)")
    await update.message.reply_text("\n".join(lines))


def main():
    token = os.environ["BOT_TOKEN"]
    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("activate", cmd_activate))
    app.add_handler(CommandHandler("setstart", cmd_setstart))
    app.add_handler(CommandHandler("today", cmd_today))
    app.add_handler(CommandHandler("progress", cmd_progress))
    app.add_handler(CallbackQueryHandler(on_check_button, pattern=r"^check:"))

    # 매일 06:00 (서버 시간 기준)에 자동 게시
    app.job_queue.run_daily(daily_job, time=datetime.time(hour=6, minute=0))

    log.info("봇 시작")
    app.run_polling()


if __name__ == "__main__":
    main()
