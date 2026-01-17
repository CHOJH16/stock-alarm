import requests
from bs4 import BeautifulSoup
import os

# 1. 텔레그램 설정값 가져오기
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
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        # 1. 현재가 가져오기
        price_tag = soup.select_one(".no_today .blind")
        if not price_tag:
            return f"{name} : 데이터 읽기 실패"
        price = price_tag.text

        # 2. 전일대비 및 등락률 가져오기
        # 네이버 금융의 '전일대비' 영역(no_exday) 분석
        exday_div = soup.select_one(".no_exday")
        
        # 첫 번째 em: 전일대비 변동액
        # 두 번째 em: 등락률
        ems = exday_div.select("em")
        
        if len(ems) < 2:
            return f"{price}원 / - / -"

        # 변동액 (숫자만 있음)
        change_amount = ems[0].select_one(".blind").text
        # 등락률 (숫자만 있음, % 없음)
        change_percent = ems[1].select_one(".blind").text

        # 3. 상승/하락 아이콘 확인하여 기호 결정
        # ems[0] 내부의 span 클래스를 보고 판단 ('ico_up', 'ico_down')
        ico_span = ems[0].select_one("span")
        classes = ico_span.get("class", [])

        symbol = "-"  # 기본값 (보합)
        sign = ""     # 부호 기본값

        if "ico_up" in classes:      # 상승
            symbol = "▲"
            sign = "+"
        elif "ico_down" in classes:  # 하락
            symbol = "▼"
            sign = "-"
        elif "ico_sam" in classes:   # 보합
            symbol = "-"
            sign = ""

        # 등락률에는 퍼센트(%) 기호를 붙여줌
        return f"{price}원 / {symbol}{change_amount} / {sign}{change_percent}%"

    except Exception as e:
        print(f"[{name}] 에러 발생: {e}")
        return None

if __name__ == "__main__":
    print("--- 주가 확인 및 전송 시작 ---")
    lines = []
    
    for stock in STOCKS:
        # 각 종목별 데이터 수집
        result = get_stock_price(stock['name'], stock['code'])
        if result:
            # 최종 메시지 조합: 종목명 / 결과값
            msg = f"{stock['name']} / {result}"
            lines.append(msg)
            print(f"생성된 메시지: {msg}")
    
    # 텔레그램 전송
    if lines:
        full_message = "\n".join(lines)
        send_telegram_message(full_message)
        print("전송 완료")
    else:
        print("보낼 내용이 없습니다.")
