import pandas as pd
import requests
from bs4 import BeautifulSoup
from nba_api.stats.endpoints import leaguegamefinder
import time
from datetime import datetime, timedelta

############################################
# 1️⃣ NBA_API 기반 수집 (1차 시도)
############################################

def fetch_with_nba_api():
    print("📡 [PRIMARY] stats.nba.com (nba_api) 시도 중...")

    seasons = ['2025-26', '2024-25', '2023-24']
    all_dfs = []

    for season in seasons:
        for attempt in range(1, 4):
            try:
                print(f"  └ 시즌 {season} 시도 {attempt}/3")
                gf = leaguegamefinder.LeagueGameFinder(
                    league_id_nullable='00',
                    season_nullable=season
                )
                df = gf.get_data_frames()[0]

                if not df.empty:
                    all_dfs.append(df)
                    print(f"    ✅ 시즌 {season} 성공 ({len(df)}경기)")
                    break

            except Exception as e:
                print(f"    ⚠️ 실패: {e}")
                time.sleep(10)

        time.sleep(8)

    if not all_dfs:
        raise Exception("nba_api 전체 실패")

    final_df = pd.concat(all_dfs, ignore_index=True)
    final_df['GAME_DATE'] = pd.to_datetime(final_df['GAME_DATE'])
    final_df = final_df[final_df['GAME_DATE'] >= pd.Timestamp('2024-01-01')]
    final_df = final_df.sort_values('GAME_DATE', ascending=False)

    return final_df


############################################
# 2️⃣ NBA 공식 CDN 기반 수집 (Fallback)
############################################

def fetch_with_nba_cdn(days=120):
    print("🌐 [FALLBACK] NBA 공식 CDN(JSON) 사용")

    end_date = datetime.utcnow().date()
    start_date = end_date - timedelta(days=days)

    games = []

    date = start_date
    while date <= end_date:
        date_str = date.strftime("%Y-%m-%d")
        url = f"https://cdn.nba.com/static/json/liveData/scoreboard/todaysScoreboard_{date_str}.json"

        try:
            res = requests.get(url, timeout=10)
            if res.status_code == 200:
                data = res.json()
                game_list = data.get("scoreboard", {}).get("games", [])

                for g in game_list:
                    games.append({
                        "GAME_ID": g["gameId"],
                        "GAME_DATE": date_str,
                        "TEAM_ID": g["homeTeam"]["teamId"],
                        "TEAM_ABBREVIATION": g["homeTeam"]["teamTricode"],
                        "MATCHUP": f"{g['awayTeam']['teamTricode']} @ {g['homeTeam']['teamTricode']}",
                        "PTS": g["homeTeam"].get("score", 0),
                        "WL": None
                    })
                    games.append({
                        "GAME_ID": g["gameId"],
                        "GAME_DATE": date_str,
                        "TEAM_ID": g["awayTeam"]["teamId"],
                        "TEAM_ABBREVIATION": g["awayTeam"]["teamTricode"],
                        "MATCHUP": f"{g['awayTeam']['teamTricode']} @ {g['homeTeam']['teamTricode']}",
                        "PTS": g["awayTeam"].get("score", 0),
                        "WL": None
                    })

        except Exception:
            pass

        date += timedelta(days=1)
        time.sleep(0.3)

    if not games:
        raise Exception("CDN 데이터 수집 실패")

    df = pd.DataFrame(games)
    df['GAME_DATE'] = pd.to_datetime(df['GAME_DATE'])
    df = df.sort_values('GAME_DATE', ascending=False)

    print(f"✅ CDN 기반 경기 {len(df)}건 수집")
    return df


############################################
# 3️⃣ CBS Sports 부상/뉴스 (기존 유지)
############################################

def fetch_cbs_news():
    print("📰 CBS Sports 부상/뉴스 수집 중...")

    url = "https://www.cbssports.com/nba/injuries/"
    headers = {'User-Agent': 'Mozilla/5.0'}
    res = requests.get(url, headers=headers, timeout=20)
    soup = BeautifulSoup(res.text, 'html.parser')

    news_data = []

    team_sections = soup.find_all('div', class_='TableBase')

    for section in team_sections:
        team = section.find('span', class_='TeamName')
        if not team:
            continue

        team_name = team.text.strip()
        rows = section.find_all('tr', class_='TableBase-bodyTr')

        issues = []
        for row in rows:
            cols = row.find_all('td')
            if len(cols) >= 5:
                issues.append(
                    f"{cols[4].text.strip()}: {cols[0].text.strip()} ({cols[3].text.strip()})"
                )

        if issues:
            news_data.append({
                "TEAM": team_name,
                "NEWS": " | ".join(issues)
            })

    if news_data:
        pd.DataFrame(news_data).to_csv("nba_news.csv", index=False, encoding="utf-8-sig")
        print("✅ 부상/뉴스 저장 완료")


############################################
# 4️⃣ 메인 실행 로직
############################################

def collect_real_data():
    print("🚀 NBA 데이터 수집 파이프라인 시작")

    try:
        df = fetch_with_nba_api()
        source = "nba_api"
    except Exception as e:
        print(f"❌ nba_api 실패 → CDN fallback 전환 ({e})")
        df = fetch_with_nba_cdn()
        source = "nba_cdn"

    df.to_csv("nba_history_3years.csv", index=False, encoding="utf-8-sig")
    print(f"📁 경기 데이터 저장 완료 ({source})")

    fetch_cbs_news()
    print("🏁 crawl.py 종료")


if __name__ == "__main__":
    collect_real_data()
