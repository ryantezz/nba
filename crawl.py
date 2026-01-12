import pandas as pd
import requests
from bs4 import BeautifulSoup
from nba_api.stats.endpoints import leaguegamefinder
import time
import socket

def collect_real_data():
    print("🚀 [1/2] NBA 최신 데이터 수집 중 (타임아웃 강화)...")
    
    # 재시도 로직 설정
    max_retries = 3
    for attempt in range(max_retries):
        try:
            # 1. LeagueGameFinder 호출 시 타임아웃을 60초로 늘림
            game_finder = leaguegamefinder.LeagueGameFinder(
                league_id_nullable='00', 
                timeout=60 # 기존 30초에서 60초로 확장
            )
            all_games = game_finder.get_data_frames()[0]
            
            target_seasons = ['22025', '22024', '22023']
            final_df = all_games[all_games['SEASON_ID'].isin(target_seasons)].copy()
            final_df['GAME_DATE'] = pd.to_datetime(final_df['GAME_DATE'])
            final_df = final_df.sort_values('GAME_DATE', ascending=False)
            
            final_df.to_csv('nba_history_3years.csv', index=False, encoding='utf-8-sig')
            print(f"✅ 수집 완료: {len(final_df)}건 저장")
            break # 성공 시 루프 탈출
            
        except Exception as e:
            print(f"⚠️ {attempt + 1}차 시도 실패: {e}")
            if attempt < max_retries - 1:
                print("⏳ 5초 후 다시 시도합니다...")
                time.sleep(5)
            else:
                print("❌ 모든 재시도가 실패했습니다. NBA 서버 상태를 확인하세요.")

    print("\n🚀 [2/2] CBS Sports 통합 뉴스 크롤링 중...")
    try:
        url = "https://www.cbssports.com/nba/injuries/"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        res = requests.get(url, headers=headers, timeout=20)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        news_data = []
        team_sections = soup.find_all('div', class_='TableBase')
        for section in team_sections:
            try:
                team_name = section.find('span', class_='TeamName').text.strip()
                rows = section.find_all('tr', class_='TableBase-bodyTr')
                issues = [f"{r.find_all('td')[4].text.strip()}: {r.find_all('td')[0].text.strip()}" for r in rows if len(r.find_all('td')) >= 5]
                if issues:
                    news_data.append({'TEAM': team_name, 'NEWS': " | ".join(issues)})
            except: continue
            
        pd.DataFrame(news_data).to_csv('nba_news.csv', index=False, encoding='utf-8-sig')
        print(f"✅ 뉴스 업데이트 완료")
    except Exception as e:
        print(f"❌ 뉴스 크롤링 실패: {e}")

if __name__ == "__main__":
    collect_real_data()
