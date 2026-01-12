import pandas as pd
import requests
import time
import os

def collect_real_data():
    print("🚀 [1/2] NBA 서버 직접 연결 시도 (우회 헤더 적용)...")
    
    # NBA 서버가 신뢰하는 브라우저 정보 (User-Agent 핵심)
    headers = {
        'Host': 'stats.nba.com',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://www.nba.com/',
        'Origin': 'https://www.nba.com',
        'x-nba-stats-origin': 'stats',
        'x-nba-stats-token': 'true'
    }

    # 리그 게임 데이터를 가져오는 직접 주소
    url = "https://stats.nba.com/stats/leaguegamefinder?LeagueID=00&Season=2025-26&SeasonType=Regular+Season"

    for attempt in range(3):
        try:
            # 30초 내에 응답 없으면 끊고 재시도하도록 설정
            response = requests.get(url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                headers_list = data['resultSets'][0]['headers']
                rows = data['resultSets'][0]['rowSet']
                
                df = pd.DataFrame(rows, columns=headers_list)
                df.to_csv('nba_history_3years.csv', index=False, encoding='utf-8-sig')
                print(f"✅ 수집 성공: {len(df)}개의 경기 데이터를 가져왔습니다.")
                return # 성공하면 즉시 종료
            else:
                print(f"⚠️ 서버 응답 코드 오류: {response.status_code}")
                
        except Exception as e:
            print(f"⚠️ {attempt + 1}차 시도 중 지연 발생: {e}")
            time.sleep(10) # 차단을 피하기 위해 10초 대기 후 재시도

    print("❌ NBA 서버 응답 없음. 데이터를 수집할 수 없습니다.")

if __name__ == "__main__":
    collect_real_data()
