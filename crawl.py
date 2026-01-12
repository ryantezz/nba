import pandas as pd
import requests
from bs4 import BeautifulSoup
from nba_api.stats.endpoints import leaguegamefinder
import time
from datetime import datetime
import os

def collect_real_data():
    print("🚀 [1/2] NBA 최신(2025-26 시즌 포함) 데이터 수집 중...")

    try:
        all_dfs = []

        # 시즌별 명시적 호출 (안정성 핵심)
        target_seasons = ['2025-26', '2024-25', '2023-24']
        season_id_map = {
            '2025-26': '22025',
            '2024-25': '22024',
            '2023-24': '22023'
        }

        for season in target_seasons:
            print(f"📡 시즌 {season} 수집 중...")
            game_finder = leaguegamefinder.LeagueGameFinder(
                league_id_nullable='00',
                season_nullable=season
            )
            df = game_finder.get_data_frames()[0]
            all_dfs.append(df)
            time.sleep(1.5)  # rate limit 방지

        all_games = pd.concat(all_dfs, ignore_index=True)

        # 시즌 필터 (이중 안전장치)
        final_df = all_games[
            all_games['SEASON_ID'].isin(season_id_map.values())
        ].copy()

        final_df['GAME_DATE'] = pd.to_datetime(final_df['GAME_DATE'])
        final_df = final_df.sort_values('GAME_DATE', ascending=False)

        final_df.to_csv('nba_history_3years.csv', index=False, encoding='utf-8-sig')

        print(f"✅ 수집 완료: 총 {len(final_df)}건 저장 (nba_history_3years.csv)")
        print(f"📅 데이터 범위: {final_df['GAME_DATE'].min().date()} ~ {final_df['GAME_DATE'].max().date()}")

    except Exception as e:
        print(f"❌ 기록 수집 실패: {e}")

    print("\n🚀 [2/2] 실시간 부상자 및 주요 팀 뉴스(CBS Sports) 통합 크롤링 중...")

    try:
        url = "https://www.cbssports.com/nba/injuries/"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        res = requests.get(url, headers=headers, timeout=20)
        soup = BeautifulSoup(res.text, 'html.parser')

        news_data = []

        team_sections = soup.find_all('div', class_='TableBase')

        for section in team_sections:
            try:
                team_name = section.find('span', class_='TeamName')
                if not team_name:
                    continue

                team_name_raw = team_name.text.strip()
                rows = section.find_all('tr', class_='TableBase-bodyTr')

                team_issues = []

                for row in rows:
                    cols = row.find_all('td')
                    if len(cols) >= 5:
                        player = cols[0].text.strip()
                        injury = cols[3].text.strip()
                        status = cols[4].text.strip()
                        team_issues.append(f"{status}: {player}({injury})")

                if team_issues:
                    news_data.append({
                        'TEAM': team_name_raw,
                        'NEWS': " | ".join(team_issues)
                    })

            except Exception:
                continue

        if news_data:
            summary = pd.DataFrame(news_data)
            summary.to_csv('nba_news.csv', index=False, encoding='utf-8-sig')
            print(f"✅ 통합 뉴스 업데이트 완료 ({len(summary)}개 팀)")
        else:
            print("⚠️ 현재 업데이트된 주요 뉴스가 없습니다.")

    except Exception as e:
        print(f"❌ 뉴스 크롤링 실패: {e}")

if __name__ == "__main__":
    collect_real_data()
