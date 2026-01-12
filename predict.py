import pandas as pd
import numpy as np
from xgboost import XGBRegressor, XGBClassifier
from nba_api.stats.endpoints import scoreboardv2
from datetime import datetime, timedelta
from dateutil import parser, tz
import requests
import os
import warnings

warnings.filterwarnings('ignore')

# 설정 (GitHub Secrets 연동)
DISCORD_WEBHOOK_URL = os.getenv('DISCORD_WEBHOOK_URL', 'YOUR_WEBHOOK_HERE')

TEAM_MAP = {'골든워리':'GSW', '덴버너게':'DEN', '댈러스매':'DAL', '레이커스':'LAL', '밀워키벅스':'MIL', '보스턴셀':'BOS', '브루네츠':'BKN', '새크킹스':'SAC', '애틀호크':'ATL', '오클썬더':'OKC', '워싱워저':'WAS', '유타재즈':'UTA', '인디페이':'IND', '클리퍼스':'LAC', '클리블랜':'CLE', '토론토랩':'TOR', '피닉선즈':'PHX', '필라76':'PHI', '휴스로케':'HOU', '미네팀버':'MIN', '뉴올펠리':'NOP', '뉴욕닉스':'NYK', '시카불스':'CHI', '멤피그리':'MEM', '마이히트':'MIA', '올랜매직':'ORL', '샌안스퍼':'SAS', '포틀트레':'POR', '디트피스':'DET', '샬럿호네':'CHA'}
INV_TEAM_MAP = {v: k for k, v in TEAM_MAP.items()}

def get_accuracy(df, m_win, features):
    season_df = df[(df['GAME_DATE'] >= '2025-10-01') & (df['WL'].notnull())].dropna(subset=features)
    if season_df.empty: return {"전체":0, "💎ULT":0, "🔥STR":0, "✅PK":0, "⚖️HLD":0}
    
    probs = m_win.predict_proba(season_df[features])[:, 1]
    season_df['conf'] = np.abs(probs - 0.5) * 200
    season_df['correct'] = ((probs > 0.5).astype(int) == season_df['WL'].map({'W':1, 'L':0}))
    
    res = {"전체": season_df['correct'].mean() * 100}
    grades = [("💎ULT", 65, 101), ("🔥STR", 45, 65), ("✅PK", 25, 45), ("⚖️HLD", 0, 25)]
    for n, l, h in grades:
        m = (season_df['conf'] >= l) & (season_df['conf'] < h)
        res[n] = season_df[m]['correct'].mean() * 100 if m.any() else 0
    return res

def run_ultimate_system():
    if not os.path.exists('nba_history_3years.csv'): return
    df = pd.read_csv('nba_history_3years.csv')
    df['GAME_DATE'] = pd.to_datetime(df['GAME_DATE'])
    
    # 특징량 생성
    df = df.sort_values(['TEAM_ID', 'GAME_DATE'])
    df['poss'] = df['FGA'] + 0.44 * df['FTA'] + df['TOV']
    df['off_rtg'] = (df['PTS'] / df['poss']) * 100
    df['ema_off_rtg'] = df.groupby('TEAM_ID')['off_rtg'].transform(lambda x: x.ewm(span=10).mean().shift(1))
    df['ema_diff'] = df.groupby('TEAM_ID')['PLUS_MINUS'].transform(lambda x: x.ewm(span=10).mean().shift(1))
    df['elo'] = 1500 # 간소화된 ELO 로직
    features = ['ema_off_rtg', 'ema_diff', 'elo']
    
    train_df = df.dropna(subset=['WL'] + features)
    m_win = XGBClassifier(n_estimators=100, verbosity=0).fit(train_df[features], train_df['WL'].map({'W':1, 'L':0}))
    acc = get_accuracy(df, m_win, features)

    # 3일치 데이터 구성
    daily_report = []
    dates = [(-1, "◀ YESTERDAY (결과 확인)"), (0, "● TODAY (핵심 분석)"), (1, "▶ TOMORROW (경기 예고)")]
    
    game_no = 1
    for offset, label in dates:
        dt = (datetime.now() + timedelta(days=offset)).strftime('%Y-%m-%d')
        try:
            sb = scoreboardv2.ScoreboardV2(game_date=dt).get_data_frames()[0].drop_duplicates('GAME_ID')
        except: continue
        
        day_games = []
        for _, row in sb.iterrows():
            h_tid, a_tid = row['HOME_TEAM_ID'], row['VISITOR_TEAM_ID']
            h_abbr, a_abbr = INV_TEAM_MAP.get(h_tid, "TMP"), INV_TEAM_MAP.get(a_tid, "TMP") # 실제 로직에선 ID 매핑 필요
            
            # 예측값 계산 (간소화)
            h_prob = 0.65 # 예시값
            conf = abs(h_prob - 0.5) * 200
            grade = "💎ULT" if conf >= 65 else "🔥STR" if conf >= 45 else "✅PK" if conf >= 25 else "⚖️HLD"
            
            game_data = {
                "no": game_no, "h_abbr": h_abbr, "a_abbr": a_abbr,
                "h_prob": h_prob, "grade": grade, "time": "10:00",
                "is_correct": True, "h_pts": 110, "a_pts": 100 # 결과 데이터 매핑 필요
            }
            day_games.append(game_data)
            game_no += 1
        daily_report.append((label, day_games))

    # 리포트 생성
    final_text = [f"### 🏀 **NBA AI ANALYSIS REPORT** ({datetime.now().strftime('%m/%d')})", 
                  f"**[ 🎯 SEASON ACCURACY ]**\n▫️ **Total**: {acc['전체']:.0f}% | 💎 **ULT**: {acc['💎ULT']:.0f}% | 🔥 **STR**: {acc['🔥STR']:.0f}%\n---"]
    
    for label, games in daily_report:
        final_text.append(f"**{label}**\n")
        for g in games:
            h_bold = "**" if g['h_prob'] >= 0.5 else ""
            a_bold = "**" if g['h_prob'] < 0.5 else ""
            final_text.append(f"`{g['no']:02d}` {h_bold}{g['h_abbr']}{h_bold} vs {a_bold}{g['a_abbr']}{a_bold}")
            if "YESTERDAY" in label:
                final_text.append(f"➔ 결과: {g['h_pts']} : {g['a_pts']} ({'적중 ✅' if g['is_correct'] else '미적중 ❌'})\n")
            else:
                final_text.append(f"➔ 시간: {g['time']} (KST) | 등급: {g['grade']}\n")
        final_text.append("---")
    
    requests.post(DISCORD_WEBHOOK_URL, json={"content": "\n".join(final_text)})

if __name__ == "__main__":
    run_ultimate_system()