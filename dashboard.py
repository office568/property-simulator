import streamlit as st
import pandas as pd
import plotly.express as px
from streamlit_gsheets import GSheetsConnection

# 1. PAGE CONFIGURATION
st.set_page_config(
    page_title="物件収支シミュレーター Pro", 
    layout="wide",
    initial_sidebar_state="expanded" 
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
        if df is not None and not df.empty:
            if 'owner_email' in df.columns and 'property_name' in df.columns:
                return df[df['owner_email'] == user_email].dropna(subset=['property_name'])
        return pd.DataFrame(columns=['property_name', 'owner_email'])
    except:
        return pd.DataFrame(columns=['property_name', 'owner_email'])

def save_to_google_sheets(name, user_email, data_dict):
    try:
        full_df = conn.read(ttl="0s")
    except:
        full_df = pd.DataFrame()
    
    clean_dict = {k: v for k, v in data_dict.items() if not k.startswith("user_") and "FormSubmit" not in k}
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

def delete_from_google_sheets(name, user_email):
    try:
        full_df = conn.read(ttl="0s")
        if full_df is not None and not full_df.empty:
            full_df = full_df[~((full_df.property_name == name) & (full_df.owner_email == user_email))]
            conn.update(data=full_df)
            st.cache_data.clear()
    except:
        pass

# 4. SESSION STATE INITIALIZATION
defaults = {
    "rent_total": 0, "shikikin": 0, "reikin": 0, "broker_fee": 0,
    "renov": 0, "furn": 0, "license": 0, "fire_work": 0, "other": 0,
    "num_types": 1, "fixed_costs": 0, "target_profit": 500000, 
    "val_prep": 2, "val_occ": 70.0, "val_ota": 15.0, "val_mgmt": 20.0, "val_cape": 3.0
}
for key, val in defaults.items():
    if key not in st.session_state: st.session_state[key] = val

for i in range(5):
    for k_suffix in ["name_", "c_", "a_", "cons_", "u_"]:
        k = f"{k_suffix}{i}"
        if k not in st.session_state:
            st.session_state[k] = f"タイプ {chr(65+i)}" if "name" in k else (1 if "c_" in k else 0)

# --- 5. SECURE LOGIN & BOT BYPASS ---
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

# --- 6. SIDEBAR: DATA CONTROLS (RESTORED) ---
st.sidebar.title(f"👤 {user_email}")
if st.sidebar.button("ログアウト"):
    del st.session_state["user_email"]
    st.query_params.clear()
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.markdown("### ☁️ クラウド読込・削除")

db = load_db(user_email)
if db.empty:
    st.sidebar.caption("保存されたデータはありません。")
else:
    target_prop = st.sidebar.selectbox("物件を選択", db['property_name'].tolist())
    c_load, c_del = st.sidebar.columns(2)
    if c_load.button("📥 読み込む", use_container_width=True):
        saved_row = db[db.property_name == target_prop].iloc[0]
        for key, value in saved_row.items():
            if key in ["property_name", "owner_email"]: continue
            st.session_state[key] = value
        st.rerun()
    if c_del.button("🗑️ 削除", use_container_width=True):
        delete_from_google_sheets(target_prop, user_email)
        st.rerun()

st.sidebar.markdown("---")

# --- 7. INPUT SECTIONS ---
with st.sidebar.expander("1. 初期費用・準備期間", expanded=True):
    rent_total = st.number_input("月額ローン及び家賃 (円)", min_value=0, step=1000, key="rent_total")
    val_prep = st.number_input("開業準備期間 (ヶ月) ⓘ", min_value=0, max_value=12, key="val_prep")
    prep_rent_cost = rent_total * val_prep
    
    st.markdown("---")
    shikikin = st.number_input("敷金 (円)", min_value=0, step=1000, key="shikikin")
    reikin = st.number_input("礼金 (円)", min_value=0, step=1000, key="reikin")
    broker_fee = st.number_input("仲介手数料 (円)", min_value=0, step=1000, key="broker_fee")
    renovation = st.number_input("リフォーム (円)", min_value=0, step=10000, key="renov")
    furniture_appliances = st.number_input("家具＋家電 (円)", min_value=0, step=10000, key="furn")
    license_fee = st.number_input("旅館業許可 (円)", min_value=0, step=1000, key="license")
    fire_safety_work = st.number_input("消防設備の工事 (円)", min_value=0, step=1000, key="fire_work")
    other_init = st.number_input("その他予備費 (円)", min_value=0, step=1000, key="other")

st.sidebar.markdown("### 2. 部屋別の設定")
num_types = int(st.sidebar.number_input("部屋の種類数", min_value=1, max_value=5, key="num_types"))
room_configs = []
for i in range(num_types):
    with st.sidebar.expander(f"タイプ {i+1}", expanded=True):
        r_count = st.number_input("部屋数", min_value=1, key=f"c_{i}")
        r_adr = st.number_input("ADR (円)", min_value=0, step=500, key=f"a_{i}")
        r_cons = st.number_input("消耗品/泊 (円)", min_value=0, step=10, key=f"cons_{i}")
        r_util = st.number_input("光熱費/泊 (円)", min_value=0, step=10, key=f"u_{i}")
        room_configs.append({"count": r_count, "adr": r_adr, "consumables": r_cons, "util_day": r_util})

with st.sidebar.expander("3. 運営コスト・稼働率", expanded=True):
    val_occ = st.number_input("想定稼働率 % ⓘ", min_value=0.0, max_value=100.0, step=0.1, key="val_occ")
    ota_fee_rate = st.number_input("OTA手数料 %", min_value=0.0, step=0.1, key="val_ota")
    management_fee_rate = st.number_input("管理費 %", min_value=0.0, step=0.5, key="val_mgmt")
    fixed_op_costs = st.number_input("固定運営費 (円)", min_value=0, step=1000, key="fixed_costs")
    cape_rate = st.number_input("メンテ (CAPEX) %", min_value=0.0, step=0.5, key="val_cape")

with st.sidebar.expander("4. 目標利益", expanded=True):
    target_profit_val = st.number_input("目標月間利益 (円)", min_value=0, step=10000, key="target_profit")

# --- 8. CALCULATIONS ---
days = 30
occ_rate = val_occ / 100
total_rev = sum(r['adr'] * r['count'] * days * occ_rate for r in room_configs)
total_var = sum((r['consumables'] + r['util_day']) * r['count'] * days * occ_rate for r in room_configs)
total_fees_rate = (ota_fee_rate + management_fee_rate + cape_rate) / 100
commissions = total_rev * total_fees_rate
monthly_exp = rent_total + total_var + fixed_op_costs + commissions
profit = total_rev - monthly_exp
startup_total = prep_rent_cost + shikikin + reikin + broker_fee + renovation + furniture_appliances + license_fee + fire_safety_work + other_init
payback = startup_total / profit if profit > 0 else 0

# --- 9. DASHBOARD (RESTORED) ---
st.subheader("📌 収支シミュレーション結果")
m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("初期投資合計", fmt(startup_total))
m2.metric("月間想定売上", fmt(total_rev))
m3.metric("月間費用合計", fmt(monthly_exp))
m4.metric("月間営業利益", fmt(profit))
m5.metric("投資回収期間", f"{payback:.1f} ヶ月" if profit > 0 else "回収不可")

st.divider()
cl, cr = st.columns(2)
with cl:
    st.subheader("💰 初期投資の内訳")
    df_i = pd.DataFrame({"項目": ["空家賃","敷金","礼金","仲介料","リフォーム","家具家電","許可","工事","他"],"金額": [prep_rent_cost, shikikin, reikin, broker_fee, renovation, furniture_appliances, license_fee, fire_safety_work, other_init]})
    st.plotly_chart(px.pie(df_i[df_i["金額"]>0], values='金額', names='項目', hole=0.5, color_discrete_sequence=px.colors.qualitative.Pastel), use_container_width=True)
with cr:
    st.subheader("💸 月間費用の詳細内訳")
    df_m = pd.DataFrame({"項目": ["家賃", "変動費", "固定費", "手数料", "利益"],"金額": [rent_total, total_var, fixed_op_costs, commissions, max(0, profit)]})
    st.plotly_chart(px.pie(df_m[df_m["金額"]>0], values='金額', names='項目', hole=0.5, color_discrete_sequence=px.colors.qualitative.Safe), use_container_width=True)

st.divider()

st.subheader("📈 戦略分析 (Strategy Analysis)")
col_a, col_b = st.columns([1, 2])
with col_a:
    fixed_all = rent_total + fixed_op_costs
    st.info("**ユニット分析**")
    st.metric("固定費合計", fmt(fixed_all))
    st.metric("目標利益", fmt(target_profit_val))
with col_b:
    st.write("**稼働率別の必要ADR目安**")
    be_data = []
    tot_rooms = sum(r['count'] for r in room_configs)
    for o in [30, 50, 70, 90]:
        nights = tot_rooms * 30 * (o/100)
        if nights > 0:
            var_night = sum((r['consumables'] + r['util_day']) * r['count'] for r in room_configs) / tot_rooms
            target_adr = ((fixed_all + target_profit_val) / nights + var_night) / (1 - total_fees_rate) if (1 - total_fees_rate) > 0 else 0
            be_data.append({"稼働率": f"{o}%", "目標達成ADR": f"¥{int(target_adr):,}"})
    st.table(be_data)

# SAVE ACTION
st.sidebar.markdown("---")
new_name = st.sidebar.text_input("物件名を入力して保存")
if st.sidebar.button("💾 クラウドに保存", use_container_width=True):
    if new_name:
        to_save = {k: v for k, v in st.session_state.items() if not k.startswith("user_")}
        save_to_google_sheets(new_name, user_email, to_save)
        st.sidebar.success("保存完了しました！")
        st.rerun()
    else: st.sidebar.error("物件名を入力してください。")
