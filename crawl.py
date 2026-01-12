import pandas as pd
import requests
from bs4 import BeautifulSoup
from nba_api.stats.endpoints import leaguegamefinder
from nba_api.library.http import NBAStatsHTTP
import time
from datetime import datetime

# 🔥 GitHub Actions 타임아웃 대응 (기본 30초 → 60초)
NBAStatsHTTP.DEFAULT_TIMEOUT = 60


def fetch_season_games(season, retries=3, sleep_sec=10):
    """
    단일 시즌 NBA 경기 데이터 수집 (재시도 포함)
    """
    for attempt in range(1, retries + 1):
        try:
            print(f"📡 시즌 {season} 수집 시도 {attempt}/{retries}")
            gf = leaguegamefinder.LeagueGameFinder(
                league_id_nullable='00',
                season_nullable=season
            )
            df = gf.get_data_frames()[0]

            if df is not None and not df.empty:
                print(f"✅ 시즌 {season} 수집 성공 ({len(df)}건)")
                return df

            print(f"⚠️ 시즌 {season} 데이터 비어 있음")

        except Exception as e:
            print(f"⚠️ 시즌 {season} 실패: {e}")

        time.sleep(sleep_sec)

    print(f"❌ 시즌 {season} 수집 최종 실패")
    return None


def collect_real_data():
    print("🚀 [1/2] NBA 경기 데이터 수집 (2024년 ~ 현재 시즌)")

    try:
        all_dfs = []

        # 👉 2024 시즌(23-24)부터 현재 시즌(25-26)까지
        target_seasons = [
            '2025-26',
            '2024-25',
            '2023-24'
        ]

        for season in target_seasons:
            df = fetch_season_games(season)
            if df is not None:
                all_dfs.append(df)

            # rate-limit 회피
            time.sleep(5)

        if not all_dfs:
            raise Exception("NBA 경기 데이터 수집 완전 실패")

        final_df = pd.concat(all_dfs, ignore_index=True)

        # 날짜 처리
        final_df['GAME_DATE'] = pd.to_datetime(final_df['GAME_DATE'])
        final_df = final_df.sort_values('GAME_DATE', ascending=False)

        # 👉 2024년 1월 1일 이후 경기만 유지
        final_df = final_df[final_df['GAME_DATE'] >= pd.Timestamp('2024-01-01')]

        final_df.to_csv('nba_history_3years.csv', index=False, encoding='utf-8-sig')

        print(f"✅ 경기 데이터 저장 완료: {len(final_df)}건")
        print(
            f"📅 데이터 범위: "
            f"{final_df['GAME_DATE'].min().date()} ~ {final_df['GAME_DATE'].max().date()}"
        )

    except Exception as e:
        print(f"❌ 기록 수집 실패: {e}")
        return  # 경기 데이터 없으면 예측 의미 없음


    print("\n🚀 [2/2] 실시간 부상자 및 팀 뉴스(CBS Sports) 수집")

    try:
        url = "https://www.cbssports.com/nba/injuries/"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
        }

        res = requests.get(url, headers=headers, timeout=20)
        soup = BeautifulSoup(res.text, 'html.parser')

        news_data = []

        team_sections = soup.find_all('div', class_='TableBase')

        for section in team_sections:
            try:
                team_tag = section.find('span', class_='TeamName')
                if not team_tag:
                    continue

                team_name = team_tag.text.strip()
                rows = section.find_all('tr', class_='TableBase-bodyTr')

                issues = []

                for row in rows:
                    cols = row.find_all('td')
                    if len(cols) >= 5:
                        player = cols[0].text.strip()
                        injury = cols[3].text.strip()
                        status = cols[4].text.strip()
                        issues.append(f"{status}: {player} ({injury})")

                if issues:
                    news_data.append({
                        'TEAM': team_name,
                        'NEWS': " | ".join(issues)
                    })

            except Exception:
                continue

        if news_data:
            news_df = pd.DataFrame(news_data)
            news_df.to_csv('nba_news.csv', index=False, encoding='utf-8-sig')
            print(f"✅ 부상/뉴스 저장 완료 ({len(news_df)}팀)")
        else:
            print("⚠️ 수집된 뉴스 없음")

    except Exception as e:
        print(f"❌ 뉴스 크롤링 실패: {e}")


if __name__ == "__main__":
    collect_real_data()

