import os
import datetime
import requests
import pytz

BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

# 손으로 직접 실행(Run workflow)한 경우엔 요일/휴장 검사를 건너뛰고 무조건 발송
FORCE = os.environ.get('EVENT_NAME') == 'workflow_dispatch'

STOCKS = [
    {"name": "TIGER 미국배당다우존스타겟데일리커버드콜", "code": "0008S0"},
    {"name": "TIGER 미국배당다우존스타겟커버드콜2호", "code": "458760"},
    {"name": "RISE 200", "code": "148020"},
    {"name": "KODEX 200타겟위클리커버드콜", "code": "498400"},
    {"name": "삼성전자", "code": "005930"}
]

HEADERS = {
    'User-Agent': ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                   '(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36'),
    'Referer': 'https://finance.naver.com/',
    'Accept': 'application/json, text/plain, */*'
}

KST = pytz.timezone('Asia/Seoul')


def log(msg):
    print(msg, flush=True)


def send_telegram_message(message):
    if not BOT_TOKEN or not CHAT_ID:
        log("토큰 설정 오류: Secrets를 확인하세요.")
        return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        r = requests.post(url, data={"chat_id": CHAT_ID, "text": message}, timeout=15)
        log(f"텔레그램 응답 코드: {r.status_code}")
    except Exception as e:
        log(f"전송 실패: {e}")


def fetch_all(stocks):
    codes = ",".join(s['code'] for s in stocks)
    url = f"https://polling.finance.naver.com/api/realtime/domestic/stock/{codes}"
    result = {}
    try:
        res = requests.get(url, headers=HEADERS, timeout=15)
        res.raise_for_status()
        for d in res.json().get('datas', []):
            result[d.get('itemCode')] = d
    except Exception as e:
        log(f"일괄 조회 실패: {e}")

    for s in stocks:
        if s['code'] in result:
            continue
        try:
            burl = f"https://m.stock.naver.com/api/stock/{s['code']}/basic"
            r = requests.get(burl, headers=HEADERS, timeout=15)
            r.raise_for_status()
            result[s['code']] = r.json()
            log(f"예비 조회 성공: {s['name']}")
        except Exception as e:
            log(f"[{s['name']}] 조회 실패: {e}")
    return result


def format_line(d):
    price = d.get('closePrice')
    if not price:
        return None
    diff = str(d.get('compareToPreviousClosePrice', '0')).lstrip('+-')
    ratio = str(d.get('fluctuationsRatio', '0')).lstrip('+-')
    code = str(d.get('compareToPreviousPrice', {}).get('code', '3'))

    if code in ('1', '2'):
        symbol, sign = "🔺", "+"
    elif code in ('4', '5'):
        symbol, sign = "⬇️", "-"
    else:
        symbol, sign = "-", ""
    return f"{price}원 / {symbol}{diff} / {sign}{ratio}%"


def get_trade_date(data_map):
    """실제 시세가 체결된 날짜(장이 열린 마지막 날)를 찾는다."""
    dates = [str(d.get('localTradedAt', ''))[:10] for d in data_map.values()]
    dates = [x for x in dates if len(x) == 10]
    if not dates:
        return None
    return datetime.datetime.strptime(max(dates), "%Y-%m-%d").date()


def date_header(d):
    weekdays = ["월", "화", "수", "목", "금", "토", "일"]
    return f"{d.year}년 {d.month}월 {d.day}일({weekdays[d.weekday()]})"


if __name__ == "__main__":
    now = datetime.datetime.now(KST)
    log(f"현재 한국시간: {now.strftime('%Y-%m-%d %H:%M:%S')} / 수동실행={FORCE}")

    if now.weekday() >= 5 and not FORCE:
        log("오늘은 주말입니다. 발송하지 않습니다.")
        raise SystemExit

    data_map = fetch_all(STOCKS)
    if not data_map:
        log("시세 조회에 모두 실패했습니다.")
        raise SystemExit

    trade_date = get_trade_date(data_map)
    log(f"조회된 거래일: {trade_date}")

    if not FORCE and trade_date != now.date():
        log("오늘은 휴장일로 보입니다. 발송하지 않습니다.")
        raise SystemExit

    lines = []
    for stock in STOCKS:
        d = data_map.get(stock['code'])
        text = format_line(d) if d else None
        if text:
            lines.append(f"{stock['name']}\n{text}")
            log(f"성공: {stock['name']}")
        else:
            lines.append(f"{stock['name']}\n데이터 확인 불가")

    header = date_header(trade_date or now.date())
    send_telegram_message(f"{header}\n\n" + "\n\n".join(lines))
    log("작업 종료")
