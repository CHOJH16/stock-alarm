import requests
from bs4 import BeautifulSoup
import os

# 1. 텔레그램 설정값
BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

# 2. 종목 리스트
STOCKS = [
    {"name": "TIGER 미국배당다우존스타겟데일리커버드콜", "code": "0008S0"},
    {"name": "TIGER 미국배당다우존스타겟커버드콜2호", "code": "458760"},
    {"name": "RISE 200", "code": "148020"}
]

def send_telegram_message(message):
    if not BOT_TOKEN or not CHAT_ID:
        print("토큰 설정 오류")
        return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": message}
    requests.post(url, data=data)

def get_stock_price(name, code):
    try:
        url = f"https://finance.naver.com/item/main.naver?code={code}"
        headers = {'User-Agent': 'Mozilla/5.0'}
        
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        # 1. 현재가
        price = soup.select_one(".no_today .blind").text

        # 2. 전일대비 정보가 있는 구역 가져오기
        exday = soup.select_one(".no_exday")
        
        # 3. 데이터 추출
        # 첫 번째 em: 가격 변동폭 / 두 번째 em: 퍼센트
        ems = exday.select("em")
        
        change_amount = ems[0].select_one(".blind").text
        change_percent = ems[1].select_one(".blind").text
        
        # 4. 부호 결정 (가장 확실한 방법: 상위 태그인 em의 클래스를 확인)
        # 네이버는 <em class="no_up"> 또는 <em class="no_down">을 씁니다.
        first_em_class = ems[0].get("class", []) # 리스트 형태 예: ['no_up']
        
        # 기본값 설정
        symbol = "-"
        sign = ""

        # 리스트를 문자열로 바꿔서 검사 (확실한 방법)
        class_str = " ".join(first_em_class)

        if "up" in class_str:       # 클래스 이름에 'up'이 있으면 무조건 상승
            symbol = "▲"
            sign = "+"
        elif "down" in class_str:   # 클래스 이름에 'down'이 있으면 무조건 하락
            symbol = "▼"
            sign = "-"
        
        # 결과 반환
        return f"{price}원 / {symbol}{change_amount} / {sign}{change_percent}%"

    except Exception as e:
        print(f"[{name}] 에러: {e}")
        return f"{name} / 데이터 확인 불가"

if __name__ == "__main__":
    lines = []
    for s in STOCKS:
        res = get_stock_price(s['name'], s['code'])
        lines.append(f"{s['name']} / {res}")
        print(res)

    if lines:
        send_telegram_message("\n".join(lines))
