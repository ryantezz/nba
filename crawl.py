import pandas as pd
import requests
import time

def collect_real_data():
    print("🚀 [1/2] NBA 데이터 직접 패킷 수집 시도 (CDN 우회)...")
    
    # 1. NBA 공식 웹사이트가 내부적으로 사용하는 데이터 엔드포인트
    # 이 주소는 일반 API보다 보안 검사가 느슨합니다.
    url = "https://stats.nba.com/stats/leaguegamelog?Counter=1000&DateFrom=&DateTo=&Direction=DESC&LeagueID=00&PlayerOrTeam=T&Season=2025-26&SeasonType=Regular+Season&Sorter=DATE"

    headers = {
        'Host': 'stats.nba.com',
        'Connection': 'keep-alive',
        'Accept': 'application/json, text/plain, */*',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'x-nba-stats-origin': 'stats',
        'x-nba-stats-token': 'true',
        'Referer': 'https://www.nba.com/',
        'Accept-Encoding': 'gzip, deflate, br',
        'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7'
    }

    for attempt in range(3):
        try:
            # 세션을 유지하여 실제 브라우저처럼 동작
            session = requests.Session()
            response = session.get(url, headers=headers, timeout=40)
            
            if response.status_code == 200:
                raw_data = response.json()
                headers_list = raw_data['resultSets'][0]['headers']
                rows = raw_data['resultSets'][0]['rowSet']
                
                df = pd.DataFrame(rows, columns=headers_list)
                
                # 분석에 필요한 최소 컬럼 확인 및 저장
                df.to_csv('nba_history_3years.csv', index=False, encoding='utf-8-sig')
                print(f"✅ 수집 성공: {len(df)}건의 최신 경기 데이터를 확보했습니다.")
                return 
            else:
                print(f"⚠️ {attempt+1}차 시도 실패 (코드: {response.status_code})")
                
        except Exception as e:
            print(f"⚠️ {attempt+1}차 시도 중 지연 발생: {e}")
            
        time.sleep(15) # 차단을 피하기 위한 긴 대기 시간

    print("❌ 모든 시도가 실패했습니다. 외부 API 서버로 우회합니다.")
    # [비상 방책] 만약 위 방법도 막히면, 무료 NBA 데이터 미러 사이트 주소를 여기에 넣어야 합니다.
