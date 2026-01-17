import requests
from bs4 import BeautifulSoup
import os
import datetime
import pytz

# 1. 텔레그램 설정값
BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

# 2. 종목 리스트 (총 4개)
STOCKS = [
    {"name": "TIGER 미국배당다우존스타겟데일리커버드콜", "code": "0008S0"},
    {"name": "TIGER 미국배당다우존스타겟커버드콜2호", "code": "458760"},
    {"name": "RISE 200", "code": "148020"},
    {"name": "KODEX 200타겟위클리커버드콜", "code": "498400"}
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

        # 1. 현재가
        price = soup.select_one(".no_today .blind").text

        # 2. 전일대비 정보
        exday = soup.select_one(".no_exday")
        ems = exday.select("em")
        
        # 데이터 추출 (변동액, 등락률)
        change_amount = ems[0].select_one(".blind").text
        change_percent = ems[1].select_one(".blind").text
        
        # 3. 부호 결정 (up/down 글자 포함 여부로 판단)
        first_em_class = ems[0].get("class", [])
        class_str = " ".join(first_em_class)

        symbol = "-"
        sign = ""

        if "up" in class_str:       # 상승
            symbol = "▲"
            sign = "+"
        elif "down" in class_str:   # 하락
            symbol = "▼"
            sign = "-"
        
        return f"{price}원 / {symbol}{change_amount} / {sign}{change_percent}%"

    except Exception as e:
        print(f"[{name}] 에러: {e}")
        return None

def get_today_str():
    # 한국 시간 가져오기
    tz = pytz.timezone('Asia/Seoul')
    now = datetime.datetime.now(tz)
    
    # 요일 변환
    weekdays = ["월", "화", "수", "목", "금", "토", "일"]
    day_str = weekdays[now.weekday()]
    
    # 포맷: 2026년 1월 17일(토)
    return f"{now.year}년 {now.month}월 {now.day}일({day_str})"

if __name__ == "__main__":
    print("--- 시작 ---")
    
    # 1. 날짜 헤더 생성
    date_header = get_today_str()
    
    # 2. 주식 데이터 수집
    lines = []
    for stock in STOCKS:
        result = get_stock_price(stock['name'], stock['code'])
        if result:
            lines.append(f"{stock['name']} / {result}")
            print(f"성공: {stock['name']}")
        else:
            lines.append(f"{stock['name']} / 데이터 수집 실패")
    
    # 3. 메시지 조립 및 전송
    if lines:
        # 날짜 + 한 줄 띄우기(\n\n) + 종목리스트
        full_message = f"{date_header}\n\n" + "\n".join(lines)
        send_telegram_message(full_message)
        print("전송 완료:\n" + full_message)
    else:
        print("데이터 없음")
