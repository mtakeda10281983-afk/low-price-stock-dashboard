import streamlit as st
import pandas as pd
import os
import yfinance as yf

# ページの基本設定
st.set_page_config(
    page_title="低位株トレード実績ダッシュボード",
    page_icon="📈",
    layout="wide"
)

# データの保存先
LOG_DIR = r"C:\Users\m_tak\trading_data\logs"
master_file = os.path.join(LOG_DIR, "master_all_trades.csv")

st.title("📈 低位株AIスクリーニング＆実績トラッカー")
st.markdown("---")

# 企業名を取得する補助関数（キャッシュ付きで高速化）
@st.cache_data
def get_company_name(ticker):
    try:
        t = yf.Ticker(ticker)
        # yfinanceのinfoから会社名を取得（取得できない場合はコードをそのまま返す）
        info = t.info
        name = info.get('longName') or info.get('shortName') or ticker
        return name
    except:
        return ticker

# データの読み込み関数
@st.cache_data
def load_data():
    if os.path.exists(master_file):
        df = pd.read_csv(master_file, encoding='utf-8-sig')
        # 企業名列がなければ追加する
        if 'Name' not in df.columns and 'Ticker' in df.columns:
            df['Name'] = df['Ticker'].apply(get_company_name)
        return df
    return pd.DataFrame()

df_master = load_data()

if df_master.empty:
    st.info("ℹ️ まだマスターデータ（master_all_trades.csv）が生成されていません。「make_test_data.py」を実行するか、実際のスクリーニングを行ってください。")
else:
    # 日付列の確認と最新日の取得
    if 'Date' in df_master.columns:
        df_master['Date'] = pd.to_datetime(df_master['Date']).dt.strftime('%Y-%m-%d')
        latest_date = df_master['Date'].max()
    else:
        latest_date = "不明"

    # ==========================================
    # 1. 一番目立つところ：本日のスクリーニング銘柄
    # ==========================================
    st.markdown(f"### 🔥 本日の注目銘柄（日付: {latest_date}）")
    
    today_df = df_master[df_master['Date'] == latest_date] if 'Date' in df_master.columns else df_master
    
    if not today_df.empty:
        # セレクトボックスに「銘柄コード : 企業名」の形式で表示する
        today_df['Display_Name'] = today_df['Ticker'] + " (" + today_df['Name'] + ")"
        display_options = today_df['Display_Name'].unique().tolist()
        
        selected_display = st.selectbox("本日のヒット銘柄を選択して詳細を見る", display_options, key="today_select")
        
        # 選択された行のデータを抽出
        row_data = today_df[today_df['Display_Name'] == selected_display].iloc[0]
        selected_ticker = row_data['Ticker']
        company_name = row_data['Name']
        
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.markdown(f"#### 📊 {company_name}")
            st.metric(label="銘柄コード", value=selected_ticker)
            st.metric(label="基準株価 (Close)", value=f"{row_data.get('Close', 'N/A')} 円")
            st.markdown(f"**判定メモ / 要因:** {row_data.get('Info', '特記事項なし')}")
            
            if 'Score' in row_data:
                st.metric(label="AIスクリーニングスコア", value=f"{row_data['Score']}点")

        with col2:
            st.markdown("#### 📉 移動平均線（MA）付きチャート")
            with st.spinner('株価データを取得してチャートを描画中...'):
                try:
                    ticker_yf = yf.Ticker(selected_ticker)
                    hist = ticker_yf.history(period="6mo")
                    if not hist.empty:
                        hist['MA25'] = hist['Close'].rolling(window=25).mean()
                        hist['MA75'] = hist['Close'].rolling(window=75).mean()
                        
                        chart_data = hist[['Close', 'MA25', 'MA75']]
                        st.line_chart(chart_data)
                    else:
                        st.warning("株価データの取得に失敗しました。")
                except Exception as e:
                    st.error(f"チャート描画エラー: {e}")
    else:
        st.info("本日の日付に一致するスクリーニングデータはありません。")

    st.markdown("---")

    # ==========================================
    # 2. その下：今までのスクリーニング履歴一覧と騰落状況
    # ==========================================
    st.markdown("### 📚 過去のスクリーニング履歴＆パフォーマンス一覧")
    st.markdown("過去にヒットした全銘柄の一覧です。銘柄を選ぶと、そのデータの詳細や騰落状況を確認できます。")

    df_master['Display_Name'] = df_master['Ticker'] + " (" + df_master['Name'] + ")"
    all_display_options = df_master['Display_Name'].unique().tolist()
    
    selected_history_display = st.selectbox("履歴から銘柄を選択", all_display_options, key="history_select")
    selected_history_ticker = selected_history_display.split(" ")[0] # 銘柄コード部分を抽出

    # 選択された銘柄の過去履歴を抽出
    history_df = df_master[df_master['Ticker'] == selected_history_ticker].drop(columns=['Display_Name'])
    
    st.dataframe(history_df, use_container_width=True)

    # 選択した銘柄の長期チャート
    st.markdown(f"#### 📈 {selected_history_display} の長期チャートと値動き推移")
    try:
        hist_long = yf.Ticker(selected_history_ticker).history(period="1y")
        if not hist_long.empty:
            hist_long['MA25'] = hist_long['Close'].rolling(window=25).mean()
            st.line_chart(hist_long[['Close', 'MA25']])
    except Exception as e:
        st.info("長期チャートの読み込みに失敗しました。")