import pandas as pd
import requests
from bs4 import BeautifulSoup
from nba_api.stats.endpoints import leaguegamefinder
import time

def collect_real_data():
    print("🚀 [1/2] NBA 최신 데이터 수집 중 (서버 차단 우회 모드)...")
    
    # 실제 브라우저처럼 보이기 위한 헤더 설정
    headers = {
        'Host': 'stats.nba.com',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'en-US,en;q=0.9,ko;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Referer': 'https://www.nba.com/',
        'Origin': 'https://www.nba.com'
    }

    max_retries = 3
    for attempt in range(max_retries):
        try:
            # 타임아웃을 100초로 대폭 늘리고, 헤더를 강제 주입
            game_finder = leaguegamefinder.LeagueGameFinder(
                league_id_nullable='00', 
                headers=headers, 
                timeout=100
            )
            all_games = game_finder.get_data_frames()[0]
            
            target_seasons = ['22025', '22024', '22023']
            final_df = all_games[all_games['SEASON_ID'].isin(target_seasons)].copy()
            final_df['GAME_DATE'] = pd.to_datetime(final_df['GAME_DATE'])
            final_df = final_df.sort_values('GAME_DATE', ascending=False)
            
            final_df.to_csv('nba_history_3years.csv', index=False, encoding='utf-8-sig')
            print(f"✅ 수집 완료: {len(final_df)}건 저장")
            break
            
        except Exception as e:
            print(f"⚠️ {attempt + 1}차 시도 실패: {e}")
            if attempt < max_retries - 1:
                # 다음 시도 전 대기 시간을 더 늘려 서버의 의심을 피함
                wait_time = 10 * (attempt + 1)
                print(f"⏳ {wait_time}초 후 다시 시도합니다...")
                time.sleep(wait_time)
            else:
                print("❌ NBA 서버가 현재 응답하지 않습니다. 잠시 후 다시 시도해 주세요.")

    # [2/2 뉴스 크롤링 부분은 이전과 동일하므로 생략하거나 그대로 유지]
    print("\n🚀 [2/2] CBS Sports 뉴스 업데이트 중...")
    # ... (생략)
