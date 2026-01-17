import requests
from bs4 import BeautifulSoup
import datetime
import pytz
import os

# 1. 깃허브 설정에서 저장해둔 텔레그램 키를 가져옵니다.
BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

# 2. 알림을 받을 종목 리스트입니다. (요청하신 3개)
STOCKS = [
    {"name": "TIGER 미국배당다우존스타겟데일리커버드콜", "code": "0008S0"},
    {"name": "TIGER 미국배당다우존스타겟커버드콜2호", "code": "458760"},
    {"name": "RISE 200", "code": "148020"}
]

def send_telegram_message(message):
    if not BOT_TOKEN or not CHAT_ID:
        print("텔레그램 설정이 안 되어 있어 메시지를 못 보냅니다.")
        return
    
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": message}
    try:
        requests.post(url, data=data)
    except Exception as e:
        print(f"메시지 전송 실패: {e}")

def get_price(code):
    # 네이버 금융에서 데이터 가져오기
    try:
        url = f"https://finance.naver.com/item/main.naver?code={code}"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')

        # 가격 정보 찾기
        price_area = soup.select_one('div.no_today span.blind')
        if not price_area:
            return None # 코드가 잘못되었거나 페이지가 없으면 무시
            
        price = price_area.text
        
        # 전일 대비 정보 찾기
        exday = soup.select_one('div.no_exday')
        change_val = exday.select_one('em:nth-of-type(1) span.blind').text
        change_pct = exday.select_one('em:nth-of-type(2) span.blind').text
        
        # 아이콘으로 상승/하락 확인
        ico = exday.select_one('em:nth-of-type(1) span')['class']
        
        symbol = "-"
        sign = ""
        
        if 'ico_up' in ico:
            symbol = "▲"
            sign = "+"
        elif 'ico_down' in ico:
            symbol = "▼"
            sign = "-"
            
        return {
            "p": price, 
            "s": symbol, 
            "c": change_val, 
            "pct": f"{sign}{change_pct}%"
        }
    except:
        return None

def is_market_open():
    # 현재 한국 시간
    tz = pytz.timezone('Asia/Seoul')
    now = datetime.datetime.now(tz)
    
    # 1. 주말이면(토,일) 안 보냄
    if now.weekday() >= 5:
        return False
        
    # 2. 공휴일 체크 (삼성전자 주식 날짜로 오늘 장이 열렸는지 확인)
    try:
        url = "https://finance.naver.com/item/sise_day.naver?code=005930"
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # 가장 위에 있는 날짜(최신 영업일) 가져오기
        last_date = soup.select_one("span.tah.p10.gray03").text.strip()
        today = now.strftime("%Y.%m.%d")
        
        if last_date != today:
            print(f"오늘은 휴장일입니다. (네이버 기준 최신일: {last_date})")
            return False
    except:
        pass # 확인하다 에러 나면 그냥 평일이니 보냄

    return True

# 메인 실행 함수
if __name__ == "__main__":
    if is_market_open():
        lines = []
        for s in STOCKS:
            d = get_price(s['code'])
            if d:
                # 예시 양식: 종목명 / 현재가 / 기호변동액 / 등락률
                msg = f"{s['name']} / {d['p']}원 / {d['s']}{d['c']} / {d['pct']}"
                lines.append(msg)
        
        if lines:
            final_msg = "\n".join(lines)
            send_telegram_message(final_msg)
            print("전송 완료")
    else:
        print("오늘은 주말이거나 휴장일입니다.")
