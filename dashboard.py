import streamlit as st
import pandas as pd
import plotly.express as px
from streamlit_gsheets import GSheetsConnection

# 1. PAGE CONFIGURATION
st.set_page_config(
    page_title="物件収支シミュレーター Pro", 
    layout="wide",
    initial_sidebar_state="expanded" # Keep sidebar open for better UI
)

# 2. HELPER FUNCTIONS
def fmt(number):
    try: return f"¥{int(number):,}"
    except: return "¥0"

# 3. GOOGLE SHEETS CONNECTION
conn = st.connection("gsheets", type=GSheetsConnection)

def load_db(user_email):
    try:
        df = conn.read(ttl="0s")
        if df is not None and 'owner_email' in df.columns:
            return df[df['owner_email'] == user_email].dropna(subset=['property_name'])
        return pd.DataFrame(columns=['property_name', 'owner_email'])
    except:
        return pd.DataFrame(columns=['property_name', 'owner_email'])

def save_to_google_sheets(name, user_email, data_dict):
    try:
        full_df = conn.read(ttl="0s")
    except:
        full_df = pd.DataFrame()
    clean_dict = {k: v for k, v in data_dict.items() if not k.startswith("FormSubmit") and k != "user_email"}
    clean_dict['property_name'] = str(name)
    clean_dict['owner_email'] = str(user_email)
    if full_df is not None and not full_df.empty:
        if 'property_name' in full_df.columns and 'owner_email' in full_df.columns:
            full_df = full_df[~((full_df.property_name == name) & (full_df.owner_email == user_email))]
    else:
        full_df = pd.DataFrame()
    new_df = pd.concat([full_df, pd.DataFrame([clean_dict])], ignore_index=True)
    conn.update(data=new_df)
    st.cache_data.clear()

# 4. SESSION STATE INITIALIZATION
if "val_occ" not in st.session_state:
    st.session_state.val_occ = 70.0

defaults = {
    "rent_total": 0, "shikikin": 0, "reikin": 0, "broker_fee": 0,
    "renov": 0, "furn": 0, "license": 0, "fire_work": 0, "other": 0,
    "num_types": 1, "fixed_costs": 0, "target_profit": 500000, 
    "val_prep": 2, "val_ota": 15.0, "val_mgmt": 20.0, "val_cape": 3.0
}
for key, val in defaults.items():
    if key not in st.session_state: st.session_state[key] = val

for i in range(5):
    for k_suffix in ["name_", "c_", "a_", "cons_", "u_"]:
        k = f"{k_suffix}{i}"
        if k not in st.session_state:
            st.session_state[k] = f"タイプ {chr(65+i)}" if "name" in k else (1 if "c_" in k else 0)

# --- THE CRITICAL FIX: OCCUPANCY SYNC CALLBACKS ---
def update_slider():
    st.session_state.val_occ = st.session_state.occ_input

def update_input():
    st.session_state.occ_input = st.session_state.val_occ

# --- 5. SMART LOGIN & BOT BYPASS ---
def check_user():
    MASTER_CODE = "seirai@2026"
    query_params = st.query_params
    
    if "ping" in query_params:
        st.write("System Status: 200 OK")
        st.stop()

    if "email" in query_params and "code" in query_params:
        if query_params["code"] == MASTER_CODE:
            st.session_state["user_email"] = query_params["email"].lower()
    elif "email" in query_params and "user_email" not in st.session_state:
        st.session_state["user_email"] = query_params["email"].lower()

    if "user_email" not in st.session_state:
        st.title("🏡 物件収支シミュレーター")
        st.info("登録済みのメールアドレスとパスコードを入力してください。")
        col1, col2 = st.columns(2)
        email_input = col1.text_input("メールアドレス / Email").strip().lower()
        pass_input = col2.text_input("パスコード / Passcode", type="password")
        if st.button("ログイン / Login", use_container_width=True):
            if "@" in email_input and pass_input == MASTER_CODE:
                st.session_state["user_email"] = email_input
                st.rerun()
            else:
                st.error("入力内容に誤りがあります。")
        return False
    return True

if not check_user(): st.stop()
user_email = st.session_state["user_email"]

# 6. SIDEBAR: UI
db = load_db(user_email)
st.sidebar.title(f"👤 {user_email}")
if st.sidebar.button("ログアウト"):
    del st.session_state["user_email"]
    st.query_params.clear()
    st.rerun()

st.sidebar.markdown("---")
with st.sidebar.expander("1. 初期費用・準備期間", expanded=True):
    rent_total = st.number_input("月額ローン及び家賃 (円)", step=1000, key="rent_total", help="毎月の固定費です。")
    prep_months = st.slider("開業準備期間 (ヶ月) ⓘ", 0, 6, key="val_prep", help="売上ゼロで家賃のみかかる期間。")
    prep_rent_cost = rent_total * prep_months
    shikikin = st.number_input("敷金 (円)", step=1000, key="shikikin", help="初期費用の敷金です。")
    reikin = st.number_input("礼金 (円)", step=1000, key="reikin", help="初期費用の礼金です。")
    renov = st.number_input("リフォーム (円)", step=10000, key="renov", help="改装費用です。")
    furn = st.number_input("家具＋家電 (円)", step=10000, key="furn", help="備品購入費です。")
    other_init = st.number_input("その他予備費 (円)", step=1000, key="other", help="消防、許可申請、他諸経費。")

st.sidebar.markdown("### 2. 部屋別の設定")
num_types = int(st.sidebar.number_input("部屋の種類数", min_value=1, max_value=5, key="num_types"))
room_configs = []
for i in range(num_types):
    with st.sidebar.expander(f"タイプ {i+1}", expanded=True):
        r_count = st.number_input("部屋数", min_value=1, key=f"c_{i}")
        r_adr = st.number_input("ADR (円)", step=500, key=f"a_{i}", help="平均客室単価。")
        r_cons = st.number_input("消耗品/泊 (円)", step=10, key=f"cons_{i}")
        r_util = st.number_input("光熱費/泊 (円)", step=10, key=f"u_{i}")
        room_configs.append({"count": r_count, "adr": r_adr, "consumables": r_cons, "util_day": r_util})

with st.sidebar.expander("3. 運営コスト・稼働率", expanded=True):
    # --- STABLE DUAL WIDGET FOR OCCUPANCY ---
    st.write("想定稼働率 % ⓘ")
    occ_col1, occ_col2 = st.columns([2, 1])
    # The Slider
    occ_slider = occ_col1.slider("Occ Slider", 0.0, 100.0, step=0.5, key="val_occ", on_change=update_input, label_visibility="collapsed")
    # The Number Input
    occ_input = occ_col2.number_input("Occ Input", 0.0, 100.0, step=0.5, key="occ_input", on_change=update_slider, label_visibility="collapsed", help="月間の稼働割合。")
    
    # Sync Initial Value
    if "occ_input" not in st.session_state:
        st.session_state.occ_input = st.session_state.val_occ

    ota_fee = st.number_input("OTA手数料 %", step=0.1, key="val_ota", help="サイト手数料率。")
    mgmt_fee = st.number_input("管理費 %", step=0.5, key="val_mgmt", help="代行手数料率。")
    capex = st.number_input("修繕積立 %", step=0.5, key="val_cape", help="将来の修繕。")
    fixed_op = st.number_input("固定運営費 (円)", step=1000, key="fixed_costs", help="ネット・PMS等。")

with st.sidebar.expander("4. 目標利益", expanded=True):
    target_profit_val = st.number_input("目標月間利益 (円)", step=10000, key="target_profit")

# --- 8. CALCULATIONS ---
occ_rate = st.session_state.val_occ / 100
total_rev = sum(r['adr'] * r['count'] * 30 * occ_rate for r in room_configs)
total_var = sum((r['consumables'] + r['util_day']) * r['count'] * 30 * occ_rate for r in room_configs)
commissions = total_rev * ((ota_fee + mgmt_fee + capex) / 100)
monthly_exp = rent_total + total_var + fixed_op + commissions
profit = total_rev - monthly_exp
startup_total = prep_rent_cost + shikikin + reikin + renov + furn + other_init
payback = startup_total / profit if profit > 0 else 0

# --- 9. DASHBOARD ---
st.subheader("📌 収支シミュレーション結果")
m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("初期投資合計", fmt(startup_total), help="開業費用の総額です。")
m2.metric("月間想定売上", fmt(total_rev), help="予想される売上です。")
m3.metric("月間費用合計", fmt(monthly_exp), help="全ての支出合計です。")
m4.metric("月間営業利益", fmt(profit), help="手残りの利益です。")
m5.metric("投資回収期間", f"{payback:.1f} ヶ月" if profit > 0 else "回収不可")

st.divider()

st.subheader("📈 戦略分析 (Strategy Analysis)")
col_a, col_b = st.columns([1, 2])
with col_a:
    fixed_all = rent_total + fixed_op
    st.info("**ユニット分析**")
    st.metric("固定費合計", fmt(fixed_all))
    st.metric("目標利益", fmt(target_profit_val))
with col_b:
    st.write("**稼働率別の必要ADR**")
    be_data = []
    for o in [30, 50, 70, 90]:
        nights = sum(r['count'] for r in room_configs) * 30 * (o/100)
        if nights > 0:
            var_night = sum((r['consumables'] + r['util_day']) * r['count'] for r in room_configs) / sum(r['count'] for r in room_configs)
            # Math: ADR = ((Fixed + Profit) / Nights + Var) / (1 - FeeRate)
            fee_r = (ota_fee + mgmt_fee + capex) / 100
            target_adr = ((fixed_all + target_profit_val) / nights + var_night) / (1 - fee_r)
            be_data.append({"稼働率": f"{o}%", "目標達成ADR": f"¥{int(target_adr):,}"})
    st.table(be_data)

# SAVE
st.sidebar.markdown("---")
new_name = st.sidebar.text_input("物件名を入力して保存")
if st.sidebar.button("💾 クラウドに保存", use_container_width=True):
    if new_name:
        to_save = {k: v for k, v in st.session_state.items() if not k.startswith("user_") and "_input" not in k}
        save_to_google_sheets(new_name, user_email, to_save)
        st.sidebar.success("保存完了！")
    else: st.sidebar.error("名前を入力してください")
