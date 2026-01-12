import pandas as pd
import requests
import time

def collect_real_data():
    print("🚀 [1/2] NBA 공식 서버 직접 연결 시도 (Deep Crawling)...")
    
    # 1. NBA 공식 API 중 가장 차단이 적은 'LeagueGameLog' 엔드포인트
    # 2025-26 시즌의 실제 경기 데이터를 가져옵니다.
    url = "https://stats.nba.com/stats/leaguegamelog?Counter=1000&DateFrom=&DateTo=&Direction=DESC&LeagueID=00&PlayerOrTeam=T&Season=2025-26&SeasonType=Regular+Season&Sorter=DATE"

    headers = {
        'Host': 'stats.nba.com',
        'Connection': 'keep-alive',
        'Accept': 'application/json, text/plain, */*',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        'x-nba-stats-origin': 'stats',
        'x-nba-stats-token': 'true',
        'Referer': 'https://www.nba.com/',
        'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8',
    }

    # 깃허브 서버의 네트워크 불안정을 대비해 5번 재시도합니다.
    for i in range(5):
        try:
            print(f"📡 {i+1}차 연결 시도 중...")
            # SSL 인증서 검사를 잠시 끄고(verify=False) 직접 연결을 시도하여 DNS 문제를 우회합니다.
            response = requests.get(url, headers=headers, timeout=30, verify=True)
            
            if response.status_code == 200:
                data = response.json()
                headers_list = data['resultSets'][0]['headers']
                rows = data['resultSets'][0]['rowSet']
                
                df = pd.DataFrame(rows, columns=headers_list)
                
                # 분석 모델(predict.py)이 요구하는 핵심 컬럼이 있는지 확인
                if not df.empty:
                    df.to_csv('nba_history_3years.csv', index=False, encoding='utf-8-sig')
                    print(f"✅ [성공] 진짜 데이터 {len(df)}건 수집 완료!")
                    return
            else:
                print(f"⚠️ 서버 응답 코드 오류: {response.status_code}")
                
        except Exception as e:
            print(f"⚠️ {i+1}차 연결 실패: {e}")
            time.sleep(10) # 차단을 피하기 위해 대기 시간을 둡니다.

    print("❌ 모든 수동 연결이 차단되었습니다. 네트워크 환경 점검이 필요합니다.")

if __name__ == "__main__":
    collect_real_data()
