import requests
from bs4 import BeautifulSoup
import os
import datetime
import pytz
import time

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

        # 현재가
        price_tag = soup.select_one(".no_today .blind")
        if not price_tag: return None
        price = price_tag.text

        # 전일대비
        exday = soup.select_one(".no_exday")
        ems = exday.select("em")
        change_amount = ems[0].select_one(".blind").text
        change_percent = ems[1].select_one(".blind").text
        
        # 부호 (🔺, ⬇️)
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
    3시 31분이 될 때까지 대기
    """
    tz = pytz.timezone('Asia/Seoul')
    
    while True:
        now = datetime.datetime.now(tz)
        target_time = now.replace(hour=15, minute=31, second=0, microsecond=0)
        
        # 이미 3시 31분이 지났으면 반복 종료 (바로 실행)
        if now >= target_time:
            print(f"현재 시간({now.strftime('%H:%M:%S')})이 15:31을 지났습니다. 즉시 실행합니다.")
            break
        
        # 아직 시간이 안 됐으면 대기
        time_diff = (target_time - now).total_seconds()
        print(f"현재 {now.strftime('%H:%M:%S')}... 15:31까지 대기 중 ({int(time_diff)}초 남음)")
        
        # 30초마다 체크
        time.sleep(30)

def is_market_open(now):
    # 주말 체크
    if now.weekday() >= 5:
        print(f"오늘은 주말({now.strftime('%A')})입니다.")
        return False
    
    # 휴장일 체크
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
                print(f"오늘은 휴장일입니다. (최신 영업일: {latest_date_str})")
                return False
    except:
        pass
    
    return True

if __name__ == "__main__":
    tz = pytz.timezone('Asia/Seoul')
    now_start = datetime.datetime.now(tz)
    
    # 1. 장이 열리는 날인지 확인
    if is_market_open(now_start):
        # 2. 3시 31분까지 대기 (시세 조회 전)
        wait_until_market_close()
        
        # 3. 대기 끝난 후 시세 조회 및 전송
        print("--- 데이터 수집 시작 ---")
        now_final = datetime.datetime.now(tz)
        date_header = get_today_str(now_final)
        
        lines = []
        for stock in STOCKS:
            result = get_stock_price(stock['name'], stock['code'])
            if result:
                # [양식] 종목명 줄바꿈, 이모지 적용
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
