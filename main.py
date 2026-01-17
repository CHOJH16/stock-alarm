import requests
from bs4 import BeautifulSoup
import os

# 1. 설정값 가져오기
BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

# 2. 종목 리스트 (0008S0 포함)
STOCKS = [
    {"name": "TIGER 미국배당다우존스타겟데일리커버드콜", "code": "0008S0"},
    {"name": "TIGER 미국배당다우존스타겟커버드콜2호", "code": "458760"},
    {"name": "RISE 200", "code": "148020"}
]

def send_telegram_message(message):
    if not BOT_TOKEN or not CHAT_ID:
        print("토큰 설정 오류: Secrets 값을 확인해주세요.")
        return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": message}
    try:
        response = requests.post(url, data=data)
        print(f"텔레그램 전송 상태: {response.status_code}")
    except Exception as e:
        print(f"전송 중 에러 발생: {e}")

def get_stock_price(name, code):
    try:
        # 사용자가 주신 URL 그대로 사용
        url = f"https://finance.naver.com/item/main.naver?code={code}"
        
        # 봇이 아니라 사람처럼 보이게 하는 헤더 (중요)
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')

        # 1. 현재가 찾기 (p.no_today 또는 div.no_today)
        # 네이버 금융 페이지 구조상 'no_today' 클래스 안에 있는 blind 텍스트가 현재가입니다.
        price_tag = soup.select_one(".no_today .blind")
        
        if not price_tag:
            print(f"[{name}] 가격 태그를 찾을 수 없음. (페이지 구조가 다를 수 있음)")
            return None

        price = price_tag.text

        # 2. 등락폭 및 등락률 찾기 (div.no_exday)
        exday_div = soup.select_one(".no_exday")
        if not exday_div:
            return f"{price}원 / - / -"

        # 첫 번째 em은 변동금액, 두 번째 em은 등락률
        spans = exday_div.select("em span.blind")
        change_amount = spans[0].text if len(spans) > 0 else "0"
        change_percent = spans[1].text if len(spans) > 1 else "0.00"

        # 3. 상승/하락 기호 파악
        # 변동금액 앞의 span 클래스를 확인해서 아이콘을 결정
        ico_span = exday_div.select_one("em span")
        ico_class = ico_span.get('class', [])
        
        symbol = "-"
        sign = ""

        if 'ico_up' in ico_class:
            symbol = "▲"
            sign = "+"
        elif 'ico_down' in ico_class:
            symbol = "▼"
            sign = "-"
        elif 'ico_sam' in ico_class: # 보합
            symbol = "-"
            sign = ""
        
        # 결과 반환
        return f"{price}원 / {symbol}{change_amount} / {sign}{change_percent}%"

    except Exception as e:
        print(f"[{name}] 크롤링 에러: {e}")
        return None

if __name__ == "__main__":
    print("--- 주가 수집 시작 ---")
    lines = []
    
    for stock in STOCKS:
        result = get_stock_price(stock['name'], stock['code'])
        if result:
            # 최종 메시지 포맷: 종목명 / 가격 / 변동 / 등락률
            msg = f"{stock['name']} / {result}"
            lines.append(msg)
            print(f"성공: {msg}")
        else:
            lines.append(f"{stock['name']} : 데이터 수집 실패")
            print(f"실패: {stock['name']}")
            
    if lines:
        full_msg = "\n".join(lines)
        send_telegram_message(full_msg)
        print("--- 전체 전송 완료 ---")
    else:
        print("보낼 데이터가 없습니다.")
