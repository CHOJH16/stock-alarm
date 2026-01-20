import requests
from bs4 import BeautifulSoup
import os
import datetime
import pytz
import time # 시간 대기를 위해 추가

# 1. 텔레그램 설정값
BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

# 2. 종목 리스트
STOCKS = [
    {"name": "TIGER 미국배당다우존스타겟데일리커버드콜", "code": "0008S0"},
    {"name": "TIGER 미국배당다우존스타겟커버드콜2호", "code": "458760"},
    {"name": "RISE 200", "code": "148020"},
    {"name": "KODEX 200타겟위클리커버드콜", "code": "498400"},
    {"name": "삼성전자", "code": "005930"}
]

def send_telegram_message(message):
    if not BOT_TOKEN or not CHAT_ID:
        print("토큰 설정 오류")
        return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": message}
    try:
        requests.post(url, data=data)
    except Exception as e:
        print(f"전송 실패: {e}")

def get_stock_price(name, code):
    try:
        url = f"https://finance.naver.com/item/main.naver?code={code}"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        price_tag = soup.select_one(".no_today .blind")
        if not price_tag: return None
        price = price_tag.text

        exday = soup.select_one(".no_exday")
        ems = exday.select("em")
        change_amount = ems[0].select_one(".blind").text
        change_percent = ems[1].select_one(".blind").text
        
        first_em_class = ems[0].get("class", [])
        class_str = " ".join(first_em_class)

        symbol = "-"
        sign = ""
        if "up" in class_str:
            symbol = "🔺"
            sign = "+"
        elif "down" in class_str:
            symbol = "⬇️"
            sign = "-"
        
        return f"{price}원 / {symbol}{change_amount} / {sign}{change_percent}%"
    except Exception as e:
        print(f"[{name}] 에러: {e}")
        return None

def get_today_str(now):
    weekdays = ["월", "화", "수", "목", "금", "토", "일"]
    day_str = weekdays[now.weekday()]
    return f"{now.year}년 {now.month}월 {now.day}일({day_str})"

def wait_until_market_close():
    """
    3시 31분이 될 때까지 기다리는 함수
    """
    tz = pytz.timezone('Asia/Seoul')
    
    while True:
        now = datetime.datetime.now(tz)
        # 목표 시간: 오늘 오후 3시 31분 00초
        target_time = now.replace(hour=15, minute=31, second=0, microsecond=0)
        
        # 만약 이미 3시 31분이 지났다면? -> 바로 통과 (대기 종료)
        if now >= target_time:
            print(f"현재 시간({now.strftime('%H:%M:%S')})이 목표 시간보다 늦습니다. 즉시 실행합니다.")
            break
        
        # 아직 시간이 안 됐으면?
        time_diff = (target_time - now).total_seconds()
        print(f"현재 {now.strftime('%H:%M:%S')}... 15:31까지 약 {int(time_diff // 60)}분 남았습니다. 대기 중...")
        
        # 1분(60초) 쉬고 다시 체크
        time.sleep(60)

def is_market_open(now):
    # 주말 체크
    if now.weekday() >= 5:
        print(f"오늘은 주말({now.strftime('%A')})입니다.")
        return False
    
    # 공휴일 체크 (삼성전자 최신 영업일 비교)
    try:
        url = "https://finance.naver.com/item/sise_day.naver?code=005930"
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        latest_date_tag = soup.select_one("span.tah.p10.gray03")
        if latest_date_tag:
            latest_date_str = latest_date_tag.text.strip()
            today_str = now.strftime("%Y.%m.%d")
            
            if latest_date_str != today_str:
                print(f"오늘은 휴장일입니다. (최신 데이터: {latest_date_str})")
                return False
    except:
        pass
    
    return True

if __name__ == "__main__":
    # 1. 일단 켜지면 무조건 '주말/휴장일'인지 먼저 체크
    tz = pytz.timezone('Asia/Seoul')
    now_start = datetime.datetime.now(tz)
    
    if is_market_open(now_start):
        # 2. 장이 열리는 날이면, 3시 31분이 될 때까지 대기
        wait_until_market_close()
        
        # 3. 시간이 되어 깨어나면(혹은 이미 지났으면) 다시 현재 시간 갱신해서 메시지 발송
        now_final = datetime.datetime.now(tz)
        print("--- 데이터 수집 및 전송 시작 ---")
        
        date_header = get_today_str(now_final)
        lines = []
        for stock in STOCKS:
            result = get_stock_price(stock['name'], stock['code'])
            if result:
                lines.append(f"{stock['name']}\n{result}")
                print(f"성공: {stock['name']}")
            else:
                lines.append(f"{stock['name']}\n데이터 확인 불가")
        
        if lines:
            full_msg = f"{date_header}\n\n" + "\n\n".join(lines)
            send_telegram_message(full_msg)
            print("전송 완료")
            
    else:
        print("오늘은 발송하지 않습니다.")
