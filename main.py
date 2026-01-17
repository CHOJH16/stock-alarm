import requests
from bs4 import BeautifulSoup
import os
import datetime
import pytz

# 1. 텔레그램 설정값 가져오기
BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

# 2. 종목 리스트 (0008S0 포함, 검증 완료된 리스트)
STOCKS = [
    {"name": "TIGER 미국배당다우존스타겟데일리커버드콜", "code": "0008S0"},
    {"name": "TIGER 미국배당다우존스타겟커버드콜2호", "code": "458760"},
    {"name": "RISE 200", "code": "148020"}
]

def send_telegram_message(message):
    if not BOT_TOKEN or not CHAT_ID:
        print("토큰 설정 오류: Github Secrets를 확인해주세요.")
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

        # 2. 전일대비 정보가 있는 구역
        exday = soup.select_one(".no_exday")
        ems = exday.select("em")
        
        # 데이터 추출
        change_amount = ems[0].select_one(".blind").text
        change_percent = ems[1].select_one(".blind").text
        
        # 3. 부호 결정 (방금 성공한 로직 그대로 적용)
        first_em_class = ems[0].get("class", [])
        class_str = " ".join(first_em_class) # 리스트를 문자열로 변환

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

def is_market_open():
    # 한국 시간 기준 설정
    tz = pytz.timezone('Asia/Seoul')
    now = datetime.datetime.now(tz)
    
    # 1. 주말 체크 (토=5, 일=6)
    if now.weekday() >= 5:
        print(f"오늘은 주말({now.strftime('%A')})이라 발송하지 않습니다.")
        return False
    
    # 2. 공휴일 체크 (삼성전자 주가 날짜로 확인)
    # 오늘이 평일이라도, 장이 안 열렸으면 네이버 금융 날짜가 오늘 날짜와 다름
    try:
        url = "https://finance.naver.com/item/sise_day.naver?code=005930"
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # 가장 최신 영업일 날짜 가져오기 (YYYY.MM.DD)
        latest_date = soup.select_one("span.tah.p10.gray03").text.strip()
        today_date = now.strftime("%Y.%m.%d")
        
        if latest_date != today_date:
            print(f"오늘은 휴장일입니다. (네이버 기준 최신일: {latest_date}, 오늘: {today_date})")
            return False
            
    except Exception as e:
        print(f"휴장일 체크 실패({e}), 평일이므로 일단 진행합니다.")
        return True

    return True

if __name__ == "__main__":
    # 장이 열린 날인지 먼저 확인
    if is_market_open():
        print("--- 주가 확인 시작 ---")
        lines = []
        for stock in STOCKS:
            result = get_stock_price(stock['name'], stock['code'])
            if result:
                # RISE 200 / 71,410원 / ▲780 / +1.10%
                msg = f"{stock['name']} / {result}"
                lines.append(msg)
                print(f"생성: {msg}")
        
        if lines:
            full_msg = "\n".join(lines)
            send_telegram_message(full_msg)
            print("전송 완료")
    else:
        # 주말이거나 휴장일이면 여기서 종료
        print("프로그램을 종료합니다.")
