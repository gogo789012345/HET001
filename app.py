import streamlit as st
import pandas as pd
import plotly.express as px
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# --- 頁面設定 ---
st.set_page_config(page_title="家庭開支紀錄", page_icon="🏠", layout="centered")

# --- 1. 高階密碼鎖 (主畫面版) ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.markdown("### 🔒 歡迎使用家庭記帳系統")
    pwd = st.text_input("請輸入專屬密碼解鎖：", type="password")
    
    if st.button("解鎖 🔓", use_container_width=True):
        if pwd == "0131":  # 👈 呢度換成你屋企專用嘅密碼
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("密碼錯誤，請再試一次！")
    st.stop()

# --- 2. 系統設定與 Google Sheets 連接 ---
SCOPE = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

@st.cache_resource
def init_connection():
    credentials = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"], scopes=SCOPE
    )
    return gspread.authorize(credentials)

# 👈 記得換返你個 Google Sheet 網址
SHEET_URL = "https://docs.google.com/spreadsheets/d/137HBHfJbBUjo2dlniC1hDARJcQUx0njlDVnyb-mFOdE/edit"

try:
    client = init_connection()
    sheet = client.open_by_url(SHEET_URL).sheet1
except Exception as e:
    st.error(f"無法連接 Google Sheets: {e}")
    st.stop()

# --- UI 頂部設計 ---
col1, col2 = st.columns([8, 2])
with col1:
    st.markdown("### 🏠 屋企開支隨手記") # 用 Markdown 做到細標題效果
with col2:
    if st.button("登出"):
        st.session_state.authenticated = False
        st.rerun()

# --- 3. 新增開支表單 ---
with st.form("expense_form", clear_on_submit=True):
    # 第一排
    col_a, col_b = st.columns(2)
    with col_a:
        date = st.date_input("日期", datetime.now())
        payer = st.selectbox("付款人", ["大臭", "小臭"]) # 👈 可自行更改稱呼
    with col_b:
        category = st.selectbox("類別", ["超市","街市", "食飯", "水費", "電費", "煤氣費", "上網費" , "管理費", "供樓", "日用品", "零食", "交通", "醫療", "其他"])
        amount = st.number_input("金額 ($)", min_value=0.0, step=10.0)
        
    # 第二排
    item = st.text_input("項目名稱 (例: 百佳買肉、中電電費)")
    
    # 預留位：如果你想加 AI 影收據，可以喺度加 st.camera_input
    # receipt_photo = st.camera_input("📸 影張收據自動填 (測試中)")
    
    submitted = st.form_submit_button("新增紀錄", use_container_width=True)
    
    if submitted:
        if amount == 0 or not item:
            st.warning("請填寫項目名稱同金額！")
        else:
            row_data = [date.strftime("%Y-%m-%d"), payer, category, item, amount, ""]
            sheet.append_row(row_data)
            st.success(f"✅ 成功紀錄！【{payer}】畀咗 ${amount} 買 {item}")

# --- 4. 家庭財務 Dashboard ---
st.divider()
st.markdown("### 📊 本月家庭財務概況")

try:
    records = sheet.get_all_records()
    if records:
        df = pd.DataFrame(records)
        df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce')
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
        
        # 只過濾今個月嘅數據出嚟分析
        current_month = datetime.now().month
        current_year = datetime.now().year
        df_month = df[(df['Date'].dt.month == current_month) & (df['Date'].dt.year == current_year)]
        
        if not df_month.empty:
            # 顯示本月總開支
            total_month = df_month['Amount'].sum()
            st.metric(f"{current_month}月總開支", f"$ {total_month:,.2f}")
            
            # 顯示邊個畀咗幾多錢 (公數對帳必備)
            st.caption("分擔情況：")
            payer_sum = df_month.groupby('Payer')['Amount'].sum()
            payer_cols = st.columns(len(payer_sum))
            for i, (p, amt) in enumerate(payer_sum.items()):
                payer_cols[i].metric(p, f"$ {amt:,.1f}")
            
            # 畫圓餅圖睇錢洗咗去邊
            fig = px.pie(
                df_month, 
                values='Amount', 
                names='Category',
                hole=0.4,
                title="各類別開支佔比"
            )
            fig.update_layout(margin=dict(t=30, b=0, l=0, r=0))
            st.plotly_chart(fig, use_container_width=True)
            
            with st.expander("📝 查看今個月詳細紀錄"):
                st.dataframe(df_month[['Date', 'Payer', 'Category', 'Item', 'Amount']].sort_values(by='Date', ascending=False), use_container_width=True)
        else:
            st.info("今個月仲未有開支紀錄喔！")
    else:
        st.info("目前系統仲未有任何紀錄。")
        
except Exception as e:

    st.error(f"無法產生圖表: {e}")


