import pandas as pd
import requests
import time
from datetime import datetime, timedelta
from bs4 import BeautifulSoup


# =========================
# 1️⃣ NBA 공식 CDN에서 경기 데이터 수집 (유일한 실사용 루트)
# =========================
def fetch_with_nba_cdn(days=180):
    print("🌐 [CDN] NBA 공식 scoreboard JSON 수집 시작")

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Accept": "application/json",
        "Referer": "https://www.nba.com/",
        "Origin": "https://www.nba.com"
    }

    # 🔥 핵심: 어제까지만 수집 (UTC 기준)
    end_date = datetime.utcnow().date() - timedelta(days=1)
    start_date = end_date - timedelta(days=days)

    games = []

    date = start_date
    while date <= end_date:
        date_str = date.strftime("%Y%m%d")
        url = f"https://cdn.nba.com/static/json/liveData/scoreboard/scoreboard_{date_str}.json"

        try:
            res = requests.get(url, headers=headers, timeout=10)
            if res.status_code != 200:
                date += timedelta(days=1)
                continue

            data = res.json()
            game_list = data.get("scoreboard", {}).get("games", [])

            if not game_list:
                date += timedelta(days=1)
                continue

            for g in game_list:
                matchup = f"{g['awayTeam']['teamTricode']} @ {g['homeTeam']['teamTricode']}"

                # 홈팀
                games.append({
                    "GAME_ID": g["gameId"],
                    "GAME_DATE": date,
                    "TEAM_ID": g["homeTeam"]["teamId"],
                    "TEAM_ABBREVIATION": g["homeTeam"]["teamTricode"],
                    "MATCHUP": matchup,
                    "PTS": g["homeTeam"].get("score", 0),
                    "WL": None
                })

                # 원정팀
                games.append({
                    "GAME_ID": g["gameId"],
                    "GAME_DATE": date,
                    "TEAM_ID": g["awayTeam"]["teamId"],
                    "TEAM_ABBREVIATION": g["awayTeam"]["teamTricode"],
                    "MATCHUP": matchup,
                    "PTS": g["awayTeam"].get("score", 0),
                    "WL": None
                })

        except Exception as e:
            print(f"⚠️ CDN 요청 오류 ({date}): {e}")

        date += timedelta(days=1)
        time.sleep(0.2)

    if not games:
        print("❌ CDN에서 경기 데이터 없음 (정상 종료)")
        return pd.DataFrame()

    df = pd.DataFrame(games)
    df["GAME_DATE"] = pd.to_datetime(df["GAME_DATE"])
    df = df.sort_values("GAME_DATE", ascending=False)

    print(f"✅ CDN 경기 데이터 {len(df)}건 수집 완료")
    return df


# =========================
# 2️⃣ CBS Sports 부상자 뉴스
# =========================
def fetch_injury_news():
    print("🚑 [NEWS] CBS Sports 부상자 뉴스 수집")

    url = "https://www.cbssports.com/nba/injuries/"
    headers = {"User-Agent": "Mozilla/5.0"}

    res = requests.get(url, headers=headers, timeout=15)
    soup = BeautifulSoup(res.text, "html.parser")

    news = []

    rows = soup.select("table tr")[1:]
    for row in rows:
        cols = row.find_all("td")
        if len(cols) >= 5:
            news.append({
                "TEAM": cols[1].text.strip(),
                "NEWS": f"{cols[4].text.strip()}: {cols[0].text.strip()} ({cols[3].text.strip()})"
            })

    if news:
        pd.DataFrame(news).to_csv("nba_news.csv", index=False, encoding="utf-8-sig")
        print(f"✅ 부상자 뉴스 {len(news)}건 저장")
    else:
        print("⚠️ 부상자 뉴스 없음")


# =========================
# 3️⃣ MAIN PIPELINE
# =========================
def collect_real_data():
    print("🚀 NBA 데이터 수집 파이프라인 시작")

    df = fetch_with_nba_cdn(days=180)

    if df.empty:
        print("❌ 경기 데이터 없음 → 이전 데이터 유지")
        return

    df.to_csv("nba_history_3years.csv", index=False, encoding="utf-8-sig")
    print(f"📁 nba_history_3years.csv 저장 완료 ({len(df)}건)")

    fetch_injury_news()


if __name__ == "__main__":
    collect_real_data()

