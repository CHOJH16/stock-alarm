import requests
from bs4 import BeautifulSoup
import os

# 1. 설정값 가져오기
BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

# 2. 종목 리스트
STOCKS = [
    {"name": "TIGER 미국배당다우존스타겟데일리커버드콜", "code": "0008S0"},
    {"name": "TIGER 미국배당다우존스타겟커버드콜2호", "code": "458760"},
    {"name": "RISE 200", "code": "148020"}
]

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": message}
    # 결과 확인을 위해 응답을 출력
    res = requests.post(url, data=data)
    print(f"텔레그램 전송 결과: {res.status_code} {res.text}")

def get_price(code):
    try:
        url = f"https://finance.naver.com/item/main.naver?code={code}"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')

        # 가격 태그 찾기
        price_area = soup.select_one('div.no_today span.blind')
        if not price_area:
            return None # 코드가 틀리면 여기서 걸림
            
        price = price_area.text
        
        # 전일 대비
        exday = soup.select_one('div.no_exday')
        change_val = exday.select_one('em:nth-of-type(1) span.blind').text
        change_pct = exday.select_one('em:nth-of-type(2) span.blind').text
        
        # 아이콘 확인
        ico = exday.select_one('em:nth-of-type(1) span')['class']
        symbol = "▲" if 'ico_up' in ico else ("▼" if 'ico_down' in ico else "-")
        sign = "+" if 'ico_up' in ico else ("-" if 'ico_down' in ico else "")
            
        return f"{price}원 / {symbol}{change_val} / {sign}{change_pct}%"
    except Exception as e:
        print(f"[{code}] 에러 발생: {e}")
        return None

if __name__ == "__main__":
    print("--- 테스트 시작 ---")
    lines = []
    for s in STOCKS:
        result = get_price(s['code'])
        if result:
            msg = f"{s['name']} / {result}"
            lines.append(msg)
            print(f"데이터 확보 성공: {s['name']}")
        else:
            # 데이터 못 가져오면 에러 메시지를 보냄
            lines.append(f"{s['name']} : 데이터 확인 불가 (코드 확인 필요)")
            print(f"데이터 확보 실패: {s['name']}")
    
    if lines:
        final_msg = "\n".join(lines)
        send_telegram_message(final_msg)
    else:
        print("보낼 내용이 없습니다.")
    print("--- 테스트 종료 ---")
