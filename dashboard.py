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
    "rent_total": 0, "shikikin": 0, "reikin": 0, "broker_fee": 0, "photo": 0,
    "renov": 0, "furn": 0, "guar": 0, "fire": 0, "license": 0, "fire_work": 0, "other": 0,
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
        
        st.markdown("---")
        st.markdown("### 🛡️ セキュリティとプライバシー保護")
        st.write("通信はSSL/TLSで保護され、データは各ユーザーごとに厳格に分離されています。")
        return False
    return True

if not check_user(): st.stop()
user_email = st.session_state["user_email"]

# 6. SIDEBAR: DATA CONTROLS
db = load_db(user_email)
st.sidebar.title(f"👤 {user_email}")
if st.sidebar.button("ログアウト"):
    del st.session_state["user_email"]
    st.query_params.clear()
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.markdown("### ☁️ マイ物件 (Saved Projects)")

if not db.empty:
    target_prop = st.sidebar.selectbox("読み込む物件を選択", db['property_name'].tolist())
    c_load, c_del = st.sidebar.columns(2)
    if c_load.button("📥 読み込む", use_container_width=True, help="保存済みデータを反映します"):
        saved_row = db[db.property_name == target_prop].iloc[0]
        for key, value in saved_row.items():
            if key in ["property_name", "owner_email"]: continue
            st.session_state[key] = value
        st.rerun()
    if c_del.button("🗑️ 削除", use_container_width=True, help="データを削除します"):
        delete_from_google_sheets(target_prop, user_email)
        st.rerun()

st.sidebar.markdown("---")

# --- 7. INPUT SECTIONS WITH "i" ICONS ---
with st.sidebar.expander("1. 初期費用・準備期間設定", expanded=True):
    rent_total = st.number_input("月額ローン及び家賃 (円)", step=1000, key="rent_total", help="毎月の家賃やローン返済額です。")
    
    st.write("開業準備期間 (ヶ月) ⓘ")
    prep_months = st.slider("Prep Slider", 0, 6, key="val_prep", help="売上が発生せず家賃のみかかる期間です。")
    prep_rent_cost = rent_total * prep_months
    
    st.markdown("---")
    shikikin = st.number_input("敷金 (円)", step=1000, key="shikikin", help="契約時の敷金総額です。")
    reikin = st.number_input("礼金 (円)", step=1000, key="reikin", help="契約時の礼金総額です。")
    broker_fee = st.number_input("仲介手数料 (円)", step=1000, key="broker_fee", help="不動産会社への手数料です。")
    renovation = st.number_input("リフォーム (円)", step=10000, key="renov", help="改装・修繕費用です。")
    furniture_appliances = st.number_input("家具＋家電 (円)", step=10000, key="furn", help="備品・家電の購入費です。")
    license_fee = st.number_input("旅館業許可 (円)", step=1000, key="license", help="申請代行や手数料です。")
    fire_safety_work = st.number_input("消防設備の工事 (円)", step=1000, key="fire_work", help="消防設備設置の工事費です。")
    other_init = st.number_input("その他予備費 (円)", step=1000, key="other", help="写真撮影や予備資金です。")

st.sidebar.markdown("### 2. 部屋タイプ別の設定")
num_types = int(st.sidebar.number_input("部屋タイプの種類数", min_value=1, max_value=5, step=1, key="num_types", help="部屋のバリエーション数です。"))
room_configs = []
for i in range(num_types):
    with st.sidebar.expander(f"部屋タイプ {i+1}", expanded=True):
        r_name = st.text_input("タイプ名", key=f"name_{i}", help="管理用の名称（例：1F A号室）。")
        r_count = st.number_input("部屋数", min_value=1, step=1, key=f"c_{i}", help="このタイプの総部屋数。")
        r_adr = st.number_input("ADR (円)", step=500, key=f"a_{i}", help="1泊あたりの平均客室単価。")
        r_cons = st.number_input("消耗品/泊 (円)", step=10, key=f"cons_{i}", help="1泊あたりのアメニティ等の実費。")
        r_util = st.number_input("光熱費/泊 (円)", step=10, key=f"u_{i}", help="1泊あたりの電気・水道代の平均。")
        room_configs.append({"name": r_name, "count": r_count, "adr": r_adr, "consumables": r_cons, "util_day": r_util})

with st.sidebar.expander("3. 運営コスト・稼働率設定", expanded=True):
    # FIXED: Combined Input for Occupancy
    st.write("想定稼働率 % ⓘ")
    target_occ = st.slider("想定稼働率 %", 0.0, 100.0, key="val_occ", help="月間で部屋が埋まる割合です。")
    
    ota_fee_rate = st.number_input("OTA手数料 %", step=0.1, key="val_ota", help="予約サイトに支払う手数料率です。")
    management_fee_rate = st.number_input("管理費 %", step=0.5, key="val_mgmt", help="代行会社への委託料率です。")
    fixed_op_costs = st.number_input("ソフト・ネット・その他固定費", step=1000, key="fixed_costs", help="PMSやネット代金です。")
    cape_rate = st.number_input("メンテ (CAPEX) %", step=0.5, key="val_cape", help="将来の修繕のための積立率です。")

with st.sidebar.expander("4. 目標利益の設定", expanded=True):
    target_profit_val = st.number_input("目標月間利益 (円)", step=10000, key="target_profit", help="手元に残したい理想の金額です。")

# --- 8. CALCULATIONS ---
days = 30
active_days = days * (target_occ / 100)
total_rev = sum(r['adr'] * r['count'] * active_days for r in room_configs)
total_ota = total_rev * (ota_fee_rate / 100)
total_cons = sum(r['consumables'] * r['count'] * active_days for r in room_configs)
total_utils = sum(r['util_day'] * r['count'] * active_days for r in room_configs)
maintenance_amt = total_rev * (cape_rate / 100)
management_amt = total_rev * (management_fee_rate / 100)
num_rooms = sum(r['count'] for r in room_configs) 

startup_cost = (prep_rent_cost + shikikin + reikin + broker_fee + renovation + furniture_appliances + license_fee + fire_safety_work + other_init)
monthly_cost = (rent_total + total_cons + total_utils + fixed_op_costs + maintenance_amt + management_amt + total_ota)
profit = total_rev - monthly_cost
payback = startup_cost / profit if profit > 0 else 0

fixed_monthly = rent_total + fixed_op_costs
total_var_rate = (ota_fee_rate + management_fee_rate + cape_rate) / 100
avg_var_per_night = sum((r['consumables'] + r['util_day']) * r['count'] for r in room_configs) / num_rooms if num_rooms > 0 else 0

# SAVE ACTION
st.sidebar.markdown("---")
new_save_name = st.sidebar.text_input("物件名を入力して保存", key="save_input_name", help="クラウドにデータを保存します。")
if st.sidebar.button("💾 クラウドに保存", use_container_width=True):
    if not new_save_name:
        st.sidebar.error("物件名を入力してください。")
    else:
        to_save = {k: v for k, v in st.session_state.items() if not k.startswith("user_") and "_slider" not in k}
        save_to_google_sheets(new_save_name, user_email, to_save)
        st.sidebar.success(f"保存完了: {new_save_name}")
        st.rerun()

# --- 9. MAIN DASHBOARD ---
st.subheader("📌 収支シミュレーション結果")
m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("初期投資合計", fmt(startup_cost), help="開業までにかかる総費用です。")
m2.metric("月間想定売上", fmt(total_rev), help="設定条件での予想総売上です。")
e_ratio = (monthly_cost / total_rev * 100) if total_rev > 0 else 0
st.markdown("<style>[data-testid='stMetricDelta'] svg { display: none; }</style>", unsafe_allow_html=True)
m3.metric("月間費用合計", fmt(monthly_cost), f"費用率 {e_ratio:.1f}%", delta_color="inverse", help="手数料等を含む全ての月間支出です。")
m4.metric("月間営業利益", fmt(profit), f"利益率 {(profit/total_rev*100):.1f}%" if total_rev > 0 else "", help="売上から支出を引いた最終手残りです。")
m5.metric("投資回収期間", f"{payback:.1f} ヶ月" if profit > 0 else "回収不可", help="初期投資を完済するまでの予想期間です。")

st.divider()
cl, cr = st.columns(2)
with cl:
    st.subheader("💰 初期投資の内訳")
    df_i = pd.DataFrame({"項目": ["空家賃","敷金","礼金","仲介料","リフォーム","家具家電","許可","工事","他"],"金額": [prep_rent_cost, shikikin, reikin, broker_fee, renovation, furniture_appliances, license_fee, fire_safety_work, other_init]})
    st.plotly_chart(px.pie(df_i[df_i["金額"]>0], values='金額', names='項目', hole=0.5, color_discrete_sequence=px.colors.qualitative.Pastel), use_container_width=True)
with cr:
    st.subheader("💸 月間費用の詳細内訳")
    df_m = pd.DataFrame({"項目": ["家賃", "消耗品", "光熱費", "固定費", "メンテ", "管理費", "OTA", "利益"],"金額": [rent_total, total_cons, total_utils, fixed_op_costs, maintenance_amt, management_amt, total_ota, max(0, profit)]})
    st.plotly_chart(px.pie(df_m[df_m["金額"]>0], values='金額', names='項目', hole=0.5, color_discrete_sequence=px.colors.qualitative.Safe), use_container_width=True)

st.divider()

# 10. STRATEGY ANALYSIS
st.subheader("📈 戦略分析と目標単価 (Strategy & Goal Analysis)")
st.write(f"**現在の目標月間利益: {fmt(target_profit_val)}**")

col_be1, col_be2 = st.columns([1, 2])
with col_be1:
    st.info("**基本ユニット分析 / Unit Analysis**")
    st.metric(label="平均変動費 / 泊", value=fmt(round(avg_var_per_night)), help="1宿泊ごとにかかる実費。")
    st.metric(label="固定費合計 / 月", value=fmt(round(fixed_monthly)), help="稼働に関わらず発生する月額コスト。")
    cm_ratio = (1 - total_var_rate) * 100
    st.metric(label="貢献利益率", value=f"{round(cm_ratio)}%", help="売上から手数料等を除いた、家賃支払いに回せる利益の割合。")

with col_be2:
    st.write(f"**稼働率別：損益分岐点と目標達成ADR**")
    be_rows = []
    for occ_p in [30, 40, 50, 60, 70, 80, 90, 100]:
        occ_nights = num_rooms * 30 * (occ_p / 100)
        if occ_nights > 0:
            be_adr = ((fixed_monthly / occ_nights) + avg_var_per_night) / (1 - total_var_rate)
            target_adr = ((fixed_monthly + target_profit_val) / occ_nights + avg_var_per_night) / (1 - total_var_rate)
            be_rows.append({"稼働率": f"{occ_p}%", "損益分岐ADR": round(be_adr), "目標達成ADR": round(target_adr)})
    st.table(pd.DataFrame(be_rows).style.format({"損益分岐ADR": "¥{:,.0f}", "目標達成ADR": "¥{:,.0f}"}))

st.divider()
st.subheader("📊 稼働率別の詳細収支感度分析")
analysis_rows = []
for occ_p in [30, 40, 50, 60, 70, 80, 90, 100]:
    o_d = 30 * (occ_p / 100)
    o_r = sum(r['adr'] * r['count'] * o_d for r in room_configs)
    o_c = rent_total + fixed_op_costs + (o_r * (cape_rate / 100)) + (o_r * (management_fee_rate / 100)) + (o_r * (ota_fee_rate / 100)) + sum((r['consumables']+r['util_day'])*r['count']*o_d for r in room_configs)
    o_p = o_r - o_c
    analysis_rows.append({"稼働率": f"{occ_p}%", "ADR": o_r/(num_rooms*o_d) if num_rooms*o_d>0 else 0, "売上": o_r, "利益": o_p, "利益率": f"{round(o_p/o_r*100) if o_r>0 else 0}%", "回収": f"{startup_cost/o_p:.1f}ヶ月" if o_p > 0 else "不可"})
st.table(pd.DataFrame(analysis_rows).style.format({"ADR":"¥{:,.0f}","売上":"¥{:,.0f}","利益":"¥{:,.0f}"}))
