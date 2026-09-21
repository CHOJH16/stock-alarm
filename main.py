import os
import time
import datetime
import requests
import pytz

# 1. 텔레그램 설정값
BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

# 2. 종목 리스트 (총 5개)
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


def send_telegram_message(message):
    if not BOT_TOKEN or not CHAT_ID:
        print("토큰 설정 오류")
        return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        requests.post(url, data={"chat_id": CHAT_ID, "text": message}, timeout=15)
    except Exception as e:
        print(f"전송 실패: {e}")


def fetch_all(stocks):
    """네이버 시세 JSON을 한 번에 가져온다. 실패하면 종목별로 재시도."""
    codes = ",".join(s['code'] for s in stocks)
    url = f"https://polling.finance.naver.com/api/realtime/domestic/stock/{codes}"
    result = {}
    try:
        res = requests.get(url, headers=HEADERS, timeout=15)
        res.raise_for_status()
        for d in res.json().get('datas', []):
            result[d.get('itemCode')] = d
    except Exception as e:
        print(f"일괄 조회 실패: {e}")

    # 빠진 종목은 예비 주소로 한 번 더 시도
    for s in stocks:
        if s['code'] in result:
            continue
        try:
            burl = f"https://m.stock.naver.com/api/stock/{s['code']}/basic"
            r = requests.get(burl, headers=HEADERS, timeout=15)
            r.raise_for_status()
            result[s['code']] = r.json()
            print(f"예비 조회 성공: {s['name']}")
        except Exception as e:
            print(f"[{s['name']}] 조회 실패: {e}")
    return result


def format_line(d):
    try:
        price = d.get('closePrice')
        if not price:
            return None
        diff = str(d.get('compareToPreviousClosePrice', '0')).lstrip('+-')
        ratio = str(d.get('fluctuationsRatio', '0')).lstrip('+-')
        code = str(d.get('compareToPreviousPrice', {}).get('code', '3'))

        if code in ('1', '2'):      # 상한, 상승
            symbol, sign = "🔺", "+"
        elif code in ('4', '5'):    # 하한, 하락
            symbol, sign = "⬇️", "-"
        else:                        # 보합
            symbol, sign = "-", ""

        return f"{price}원 / {symbol}{diff} / {sign}{ratio}%"
    except Exception as e:
        print(f"형식 변환 오류: {e}")
        return None


def traded_today(data_map, now):
    """오늘 실제로 거래가 있었는지(=휴장일이 아닌지) 확인"""
    today = now.strftime('%Y-%m-%d')
    for d in data_map.values():
        if str(d.get('localTradedAt', ''))[:10] == today:
            return True
    return False


def get_today_str(now):
    weekdays = ["월", "화", "수", "목", "금", "토", "일"]
    return f"{now.year}년 {now.month}월 {now.day}일({weekdays[now.weekday()]})"


def wait_a_bit_if_early():
    """혹시 15시 35분보다 일찍 실행되면 최대 40분까지만 짧게 대기"""
    limit = time.time() + 40 * 60
    while time.time() < limit:
        now = datetime.datetime.now(KST)
        target = now.replace(hour=15, minute=35, second=0, microsecond=0)
        if now >= target:
            return
        print(f"{now.strftime('%H:%M:%S')} - 15:35까지 대기 중")
        time.sleep(60)


if __name__ == "__main__":
    now = datetime.datetime.now(KST)

    if now.weekday() >= 5:
        print("오늘은 주말입니다. 발송하지 않습니다.")
        raise SystemExit

    wait_a_bit_if_early()

    now = datetime.datetime.now(KST)
    data_map = fetch_all(STOCKS)

    if not data_map:
        print("시세 조회 자체가 실패했습니다.")
        raise SystemExit

    if not traded_today(data_map, now):
        print("오늘은 휴장일로 보입니다. 발송하지 않습니다.")
        raise SystemExit

    lines = []
    for stock in STOCKS:
        d = data_map.get(stock['code'])
        text = format_line(d) if d else None
        if text:
            lines.append(f"{stock['name']}\n{text}")
            print(f"성공: {stock['name']}")
        else:
            lines.append(f"{stock['name']}\n데이터 확인 불가")

    full_msg = f"{get_today_str(now)}\n\n" + "\n\n".join(lines)
    send_telegram_message(full_msg)
    print("전송 완료")
