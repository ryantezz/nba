import pandas as pd
import requests
import time
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from nba_api.stats.endpoints import leaguegamefinder


# =========================
# 1️⃣ PRIMARY: nba_api (시도만 하고 실패해도 OK)
# =========================
def fetch_with_nba_api():
    print("📡 [PRIMARY] stats.nba.com (nba_api) 시도 중...")

    seasons = ["2025-26", "2024-25", "2023-24"]
    dfs = []

    for season in seasons:
        for attempt in range(3):
            try:
                print(f"  └ 시즌 {season} 시도 {attempt+1}/3")
                gf = leaguegamefinder.LeagueGameFinder(
                    league_id_nullable="00",
                    season_nullable=season
                )
                df = gf.get_data_frames()[0]
                if not df.empty:
                    dfs.append(df)
                break
            except Exception as e:
                print(f"    ⚠️ 실패: {e}")
                time.sleep(5)

    if not dfs:
        raise Exception("nba_api 전체 실패")

    final_df = pd.concat(dfs, ignore_index=True)
    final_df["GAME_DATE"] = pd.to_datetime(final_df["GAME_DATE"])
    return final_df


# =========================
# 2️⃣ FALLBACK: NBA 공식 CDN (핵심 해결책)
# =========================
def fetch_with_nba_cdn(days=450):
    print("🌐 [FALLBACK] NBA 공식 CDN(JSON) 사용")

    end_date = datetime.utcnow().date()
    start_date = end_date - timedelta(days=days)

    games = []

    date = start_date
    while date <= end_date:
        date_str = date.strftime("%Y%m%d")  # 🔥 중요
        url = f"https://cdn.nba.com/static/json/liveData/scoreboard/scoreboard_{date_str}.json"

        try:
            res = requests.get(url, timeout=10)
            if res.status_code != 200:
                date += timedelta(days=1)
                continue

            data = res.json()
            game_list = data.get("scoreboard", {}).get("games", [])

            for g in game_list:
                matchup = f"{g['awayTeam']['teamTricode']} @ {g['homeTeam']['teamTricode']}"

                games.append({
                    "GAME_ID": g["gameId"],
                    "GAME_DATE": date,
                    "TEAM_ID": g["homeTeam"]["teamId"],
                    "TEAM_ABBREVIATION": g["homeTeam"]["teamTricode"],
                    "MATCHUP": matchup,
                    "PTS": g["homeTeam"].get("score", 0),
                    "WL": None
                })

                games.append({
                    "GAME_ID": g["gameId"],
                    "GAME_DATE": date,
                    "TEAM_ID": g["awayTeam"]["teamId"],
                    "TEAM_ABBREVIATION": g["awayTeam"]["teamTricode"],
                    "MATCHUP": matchup,
                    "PTS": g["awayTeam"].get("score", 0),
                    "WL": None
                })

        except Exception:
            pass

        date += timedelta(days=1)
        time.sleep(0.25)

    if not games:
        raise Exception("CDN 데이터 수집 실패")

    df = pd.DataFrame(games)
    df["GAME_DATE"] = pd.to_datetime(df["GAME_DATE"])
    df = df.sort_values("GAME_DATE", ascending=False)

    print(f"✅ CDN 기반 경기 {len(df)}건 수집 성공")
    return df


# =========================
# 3️⃣ CBS Sports 부상자 뉴스
# =========================
def fetch_injury_news():
    print("🚑 [NEWS] CBS Sports 부상자 뉴스 수집 중...")

    url = "https://www.cbssports.com/nba/injuries/"
    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    res = requests.get(url, headers=headers)
    soup = BeautifulSoup(res.text, "html.parser")

    news_data = []

    tables = soup.find_all("table")
    for table in tables:
        rows = table.find_all("tr")
        for row in rows[1:]:
            cols = row.find_all("td")
            if len(cols) >= 5:
                player = cols[0].text.strip()
                team = cols[1].text.strip()
                injury = cols[3].text.strip()
                status = cols[4].text.strip()

                news_data.append({
                    "TEAM": team,
                    "NEWS": f"{status}: {player} ({injury})"
                })

    if news_data:
        df = pd.DataFrame(news_data)
        df.to_csv("nba_news.csv", index=False, encoding="utf-8-sig")
        print(f"✅ 부상자 뉴스 {len(df)}건 저장")
    else:
        print("⚠️ 부상자 뉴스 없음")


# =========================
# 4️⃣ 메인 파이프라인
# =========================
def collect_real_data():
    print("🚀 NBA 데이터 수집 파이프라인 시작")

    try:
        df = fetch_with_nba_api()
        print("✅ nba_api 성공")
    except Exception as e:
        print(f"❌ nba_api 실패 → CDN fallback 전환 ({e})")
        df = fetch_with_nba_cdn()

    df.to_csv("nba_history_3years.csv", index=False, encoding="utf-8-sig")
    print(f"📁 nba_history_3years.csv 저장 완료 ({len(df)}건)")

    fetch_injury_news()


if __name__ == "__main__":
    collect_real_data()

