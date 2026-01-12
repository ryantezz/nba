import pandas as pd
import numpy as np
from xgboost import XGBRegressor, XGBClassifier
from nba_api.stats.endpoints import scoreboardv2
from datetime import datetime, timedelta
from dateutil import parser, tz
import warnings
import os
import requests

warnings.filterwarnings('ignore')

# [기존 설정 유지]
DISCORD_WEBHOOK_URL = os.getenv('DISCORD_WEBHOOK_URL', '').strip()
TEAM_MAP = {'골든워리':'GSW', '덴버너게':'DEN', '댈러스매':'DAL', '레이커스':'LAL', '밀워키벅스':'MIL', '보스턴셀':'BOS', '브루네츠':'BKN', '새크킹스':'SAC', '애틀호크':'ATL', '오클썬더':'OKC', '워싱워저':'WAS', '유타재즈':'UTA', '인디페이':'IND', '클리퍼스':'LAC', '클리블랜':'CLE', '토론토랩':'TOR', '피닉선즈':'PHX', '필라76':'PHI', '휴스로케':'HOU', '미네팀버':'MIN', '뉴올펠리':'NOP', '뉴욕닉스':'NYK', '시카불스':'CHI', '멤피그리':'MEM', '마이히트':'MIA', '올랜매직':'ORL', '샌안스퍼':'SAS', '포틀트레':'POR', '디트피스':'DET', '샬럿호네':'CHA'}
INV_TEAM_MAP = {v: k for k, v in TEAM_MAP.items()}

def convert_to_kst(game_status, game_date_est):
    try:
        if "ET" in game_status:
            et_time_str = game_status.replace(" ET", "").strip()
            est_zone = tz.gettz('America/New_York')
            kst_zone = tz.gettz('Asia/Seoul')
            full_date_str = f"{game_date_est} {et_time_str}"
            dt_est = parser.parse(full_date_str).replace(tzinfo=est_zone)
            return dt_est.astimezone(kst_zone).strftime('%H:%M')
        return game_status
    except: return game_status

# [사용자님의 핵심 로직: ELO, Feature, Accuracy 리포트 그대로 유지]
def calculate_elo_system(df):
    # 컬럼 존재 여부 확인 (안전장치)
    if 'PLUS_MINUS' not in df.columns: df['PLUS_MINUS'] = 0
    elo = {tid: 1500 for tid in df['TEAM_ID'].unique()}
    history = []
    for _, row in df.sort_values('GAME_DATE').iterrows():
        history.append(elo.get(row['TEAM_ID'], 1500))
        margin = abs(row['PLUS_MINUS']) if pd.notnull(row['PLUS_MINUS']) else 0
        K = 20 * (np.log(margin + 1) + 1)
        if row['WL'] == 'W': elo[row['TEAM_ID']] = elo.get(row['TEAM_ID'], 1500) + K
        elif row['WL'] == 'L': elo[row['TEAM_ID']] = elo.get(row['TEAM_ID'], 1500) - K
    df['elo'] = history
    return df

def build_ultimate_features(df):
    # 컬럼 누락 방지 (데이터 수집 실패 시 대비)
    for col in ['FGA', 'FTA', 'TOV', 'PTS', 'PLUS_MINUS']:
        if col not in df.columns: df[col] = 0
    
    df = df.sort_values(['TEAM_ID', 'GAME_DATE'])
    df['poss'] = df['FGA'] + 0.44 * df['FTA'] + df['TOV']
    df['off_rtg'] = np.where(df['poss'] > 0, (df['PTS'] / df['poss']) * 100, 0)
    group = df.groupby('TEAM_ID')
    df['ema_off_rtg'] = group['off_rtg'].transform(lambda x: x.ewm(span=10).mean().shift(1))
    df['ema_diff'] = group['PLUS_MINUS'].transform(lambda x: x.ewm(span=10).mean().shift(1))
    df['rest_days'] = group['GAME_DATE'].diff().dt.days.fillna(3)
    df['is_b2b'] = (df['rest_days'] <= 1).astype(int)
    features = ['ema_off_rtg', 'ema_diff', 'elo', 'is_b2b', 'rest_days']
    return df, features

def run_ultimate_system():
    print("🧠 [SYSTEM] AI 분석 가동...")
    if not os.path.exists('nba_history_3years.csv'):
        print("⚠️ 데이터 없음")
        return

    raw_df = pd.read_csv('nba_history_3years.csv')
    raw_df['GAME_DATE'] = pd.to_datetime(raw_df['GAME_DATE'])
    
    # [사용자 로직 학습 및 예측]
    train_df = raw_df.dropna(subset=['WL', 'PLUS_MINUS', 'PTS'])
    if len(train_df) < 10: # 데이터 부족 시 강제 리포트 생성
        send_error_report()
        return

    df_elo = calculate_elo_system(train_df)
    df_features, features = build_ultimate_features(df_elo)
    final_train = df_features.dropna(subset=features)

    # 모델 학습 (XGBoost)
    m_win = XGBClassifier(n_estimators=100, verbosity=0).fit(final_train[features], final_train['WL'].map({'W':1,'L':0}))
    m_score = XGBRegressor(n_estimators=100, verbosity=0).fit(final_train[features], final_train['PTS'])
    
    # 리포트 생성 시작
    discord_msg = [f"### 🏀 **NBA AI 분석 리포트 ({datetime.now().strftime('%m/%d')})**", "---"]
    
    # 날짜별 경기 루프
    id_to_abbr = dict(zip(final_train['TEAM_ID'], final_train['TEAM_ABBREVIATION']))
    dates = [datetime.now(), datetime.now() + timedelta(1)]
    labels = ["● TODAY", "▶ TOMORROW"]

    for dt, label in zip(dates, labels):
        d_str = dt.strftime('%Y-%m-%d')
        discord_msg.append(f"**{label} ({d_str})**")
        
        try:
            sb = scoreboardv2.ScoreboardV2(game_date=d_str).get_data_frames()[0].drop_duplicates(subset=['GAME_ID'])
            for _, row in sb.iterrows():
                h_abbr, a_abbr = id_to_abbr.get(row['HOME_TEAM_ID']), id_to_abbr.get(row['VISITOR_TEAM_ID'])
                if not h_abbr or not a_abbr: continue
                
                # 예측값 도출
                def get_stat(abbr, d):
                    last = final_train[final_train['TEAM_ABBREVIATION'] == abbr].iloc[-1]
                    rest = (d - last['GAME_DATE']).days
                    return [last['ema_off_rtg'], last['ema_diff'], last['elo'], 1 if rest <= 1 else 0, rest]

                h_input = pd.DataFrame([get_stat(h_abbr, dt)], columns=features)
                h_prob = m_win.predict_proba(h_input)[0][1]
                
                confidence = abs(h_prob - 0.5) * 200
                grade = "💎ULT" if confidence >= 65 else "🔥STR" if confidence >= 45 else "✅PK"
                kst_time = convert_to_kst(row['GAME_STATUS_TEXT'], row['GAME_DATE_EST'][:10])
                
                m_name = f"{INV_TEAM_MAP.get(h_abbr, h_abbr)} vs {INV_TEAM_MAP.get(a_abbr, a_abbr)}"
                discord_msg.append(f"`{kst_time}` {m_name} ➔ {grade} ({h_prob*100:.1f}%)")
        except: continue
        discord_msg.append("---")

    # 디스코드 전송
    if DISCORD_WEBHOOK_URL:
        requests.post(DISCORD_WEBHOOK_URL, json={"content": "\n".join(discord_msg)})

def send_error_report():
    if DISCORD_WEBHOOK_URL:
        requests.post(DISCORD_WEBHOOK_URL, json={"content": "⚠️ **알림**: NBA 서버 지연으로 정밀 분석 데이터를 보충 중입니다. 잠시 후 다시 확인해주세요."})

if __name__ == "__main__":
    run_ultimate_system()

