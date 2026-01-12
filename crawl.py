import pandas as pd
import requests
from bs4 import BeautifulSoup
from nba_api.stats.endpoints import leaguegamefinder
import time

def collect_real_data():
    print("🚀 [1/2] NBA 최신(2025-26 시즌 포함) 데이터 수집 중...")
    try:
        # NBA 정규시즌 데이터 호출
        game_finder = leaguegamefinder.LeagueGameFinder(league_id_nullable='00')
        all_games = game_finder.get_data_frames()[0]
        
        # 최근 3개 시즌 필터링 (22025: 25-26시즌)
        target_seasons = ['22025', '22024', '22023']
        final_df = all_games[all_games['SEASON_ID'].isin(target_seasons)].copy()
        
        final_df['GAME_DATE'] = pd.to_datetime(final_df['GAME_DATE'])
        final_df = final_df.sort_values('GAME_DATE', ascending=False)
        
        # 학습용 데이터 저장
        final_df.to_csv('nba_history_3years.csv', index=False, encoding='utf-8-sig')
        print(f"✅ 수집 완료: {len(final_df)}건 저장")
        
    except Exception as e:
        print(f"❌ 데이터 수집 실패: {e}")

    print("\n🚀 [2/2] CBS Sports 통합 뉴스 크롤링 중...")
    try:
        url = "https://www.cbssports.com/nba/injuries/"
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers)
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