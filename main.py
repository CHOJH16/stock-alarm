import requests
from bs4 import BeautifulSoup
import os
import datetime
import pytz

# 1. 텔레그램 설정값 가져오기
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
        print("토큰 설정 오류: Secrets를 확인해주세요.")
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
        price_tag = soup.select_one(".no_today .blind")
        if not price_tag:
            return None
        price = price_tag.text

        # 2. 전일대비 정보
        exday = soup.select_one(".no_exday")
        ems = exday.select("em")
        
        change_amount = ems[0].select_one(".blind").text
        change_percent = ems[1].select_one(".blind").text
        
        # 3. 부호 결정 (🔺, ⬇️)
        first_em_class = ems[0].get("class", [])
        class_str = " ".join(first_em_class)

        symbol = "-"
        sign = ""

        if "up" in class_str:       # 상승
            symbol = "🔺"
            sign = "+"
        elif "down" in class_str:   # 하락
            symbol = "⬇️"
            sign = "-"
        
        return f"{price}원 / {symbol}{change_amount} / {sign}{change_percent}%"

    except Exception as e:
        print(f"[{name}] 에러: {e}")
        return None

def get_today_str(now):
    # 요일 변환
    weekdays = ["월", "화", "수", "목", "금", "토", "일"]
    day_str = weekdays[now.weekday()]
    return f"{now.year}년 {now.month}월 {now.day}일({day_str})"

def is_market_open(now):
    # 1. 주말 체크 (토=5, 일=6)
    if now.weekday() >= 5:
        print(f"오늘은 주말({now.strftime('%A')})이라 발송하지 않습니다.")
        return False
    
    # 2. 공휴일 체크 (삼성전자 주가 날짜로 확인)
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
                print(f"오늘은 휴장일입니다. (최신 영업일: {latest_date_str}, 오늘: {today_str})")
                return False
    except Exception as e:
        print(f"휴장일 체크 중 오류({e}), 평일이므로 일단 진행합니다.")
        return True

    return True

if __name__ == "__main__":
    tz = pytz.timezone('Asia/Seoul')
    now = datetime.datetime.now(tz)

    if is_market_open(now):
        print("--- 주가 확인 시작 ---")
        date_header = get_today_str(now)
        
        lines = []
        for stock in STOCKS:
            result = get_stock_price(stock['name'], stock['code'])
            if result:
                # [수정된 부분] 종목명을 첫 줄에, 데이터를 다음 줄에 배치
                formatted_msg = f"{stock['name']}\n{result}"
                lines.append(formatted_msg)
                print(f"성공: {stock['name']}")
            else:
                lines.append(f"{stock['name']}\n데이터 확인 불가")
        
        if lines:
            # [수정된 부분] 종목 사이에 빈 줄(\n\n)을 추가하여 연결
            full_msg = f"{date_header}\n\n" + "\n\n".join(lines)
            send_telegram_message(full_msg)
            print("전송 완료")
    else:
        print("오늘은 메시지를 보내지 않고 종료합니다.")
