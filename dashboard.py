import streamlit as st
import pandas as pd
import plotly.express as px
import os

# 1. PAGE CONFIGURATION
st.set_page_config(page_title="物件収支シミュレーター Pro", layout="wide")

# 2. SYNC CALLBACK FUNCTIONS
def update_prep_slider(): st.session_state.val_prep = st.session_state.val_prep_num
def update_prep_num(): st.session_state.val_prep_num = st.session_state.val_prep
def update_occ_slider(): st.session_state.val_occ = st.session_state.val_occ_num
def update_occ_num(): st.session_state.val_occ_num = st.session_state.val_occ
def update_ota_slider(): st.session_state.val_ota = st.session_state.val_ota_num
def update_ota_num(): st.session_state.val_ota_num = st.session_state.val_ota
def update_mgmt_slider(): st.session_state.val_mgmt = st.session_state.val_mgmt_num
def update_mgmt_num(): st.session_state.val_mgmt_num = st.session_state.val_mgmt
def update_cape_slider(): st.session_state.val_cape = st.session_state.val_cape_num
def update_cape_num(): st.session_state.val_cape_num = st.session_state.val_cape

# 3. INITIALIZE SESSION STATE DEFAULTS
if "val_prep" not in st.session_state: st.session_state.val_prep = 2
if "val_prep_num" not in st.session_state: st.session_state.val_prep_num = 2
if "val_occ" not in st.session_state: st.session_state.val_occ = 70.0
if "val_occ_num" not in st.session_state: st.session_state.val_occ_num = 70.0
if "val_ota" not in st.session_state: st.session_state.val_ota = 15.0
if "val_ota_num" not in st.session_state: st.session_state.val_ota_num = 15.0
if "val_mgmt" not in st.session_state: st.session_state.val_mgmt = 20.0
if "val_mgmt_num" not in st.session_state: st.session_state.val_mgmt_num = 20.0
if "val_cape" not in st.session_state: st.session_state.val_cape = 3.0
if "val_cape_num" not in st.session_state: st.session_state.val_cape_num = 3.0

# 4. PASSWORD PROTECTION
def check_password():
    def password_entered():
        if st.session_state["password"] == st.secrets["password"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False
    if "password_correct" not in st.session_state:
        st.title("🔒 Access Restricted")
        st.text_input("Please enter password", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.title("🔒 Access Restricted")
        st.text_input("Please enter password", type="password", on_change=password_entered, key="password")
        st.error("😕 Password incorrect")
        return False
    return True

if not check_password(): st.stop()

# 5. DATA STORAGE LOGIC (CSV)
DB_FILE = "properties.csv"

def save_data(name, data_dict):
    df = pd.read_csv(DB_FILE) if os.path.exists(DB_FILE) else pd.DataFrame()
    new_row = pd.DataFrame([data_dict])
    new_row['property_name'] = name
    if not df.empty:
        df = df[df.property_name != name] # Overwrite if exists
    df = pd.concat([df, new_row], ignore_index=True)
    df.to_csv(DB_FILE, index=False)

def load_db():
    return pd.read_csv(DB_FILE) if os.path.exists(DB_FILE) else pd.DataFrame()

# 6. UI & SIDEBAR
st.title("🏨 物件収支シミュレーター Pro")
try:
    st.sidebar.write("")
    st.sidebar.image("logo.png", use_container_width=True)
except:
    st.sidebar.info("💡 'logo.png' not found.")

st.sidebar.title("🛠️ 条件設定")

# SECTION 1: INITIAL INVESTMENT
with st.sidebar.expander("1. 初期費用・準備期間設定", expanded=True):
    rent_total = st.number_input("月額ローン及び家賃 (円)", value=0, step=1000, key="rent_total")
    st.write("開業準備期間 (ヶ月)")
    c_p1, c_p2 = st.columns([2, 1])
    prep_months = c_p1.slider("Slider", 0, 6, key="val_prep", on_change=update_prep_num, label_visibility="collapsed")
    prep_months_num = c_p2.number_input("Num", 0, 6, key="val_prep_num", on_change=update_prep_slider, label_visibility="collapsed")
    prep_rent_cost = rent_total * prep_months
    
    st.markdown("---")
    shikikin = st.number_input("敷金 (円)", value=0, key="shikikin")
    reikin = st.number_input("礼金 (円)", value=0, key="reikin")
    broker_fee = st.number_input("仲介手数料 (円)", value=0, key="broker_fee")
    photo_shooting = st.number_input("写真撮影 (円)", value=0, key="photo")
    renovation = st.number_input("リフォーム (円)", value=0, key="renov")
    furniture_appliances = st.number_input("家具＋家電 (円)", value=0, key="furn")
    guarantee_fee = st.number_input("保証会社費用 (円)", value=0, key="guar")
    fire_insurance = st.number_input("火災保険 (円)", value=0, key="fire")
    license_fee = st.number_input("旅館業許可 (円)", value=0, key="license")
    fire_safety_work = st.number_input("消防設備の工事 (円)", value=0, key="fire_work")
    other_init = st.number_input("その他予備費 (円)", value=0, key="other")

# SECTION 2: ROOM CONFIG
st.sidebar.markdown("### 2. 部屋タイプ別の設定")
num_types = st.sidebar.number_input("部屋タイプの種類数", min_value=1, max_value=5, value=2, key="num_types")
room_configs = []
for i in range(int(num_types)):
    with st.sidebar.expander(f"部屋タイプ {i+1}", expanded=True):
        r_name = st.text_input(f"名 {i+1}", value=f"タイプ {chr(65+i)}", key=f"name_{i}")
        r_count = st.number_input(f"数 {i+1}", min_value=1, value=1, key=f"c_{i}")
        r_adr = st.number_input(f"ADR {i+1}", value=0, key=f"a_{i}")
        r_cons = st.number_input(f"消耗品 {i+1}", value=0, key=f"cons_{i}")
        r_util = st.number_input(f"光熱費 {i+1}", value=0, key=f"u_{i}")
        room_configs.append({"name": r_name, "count": r_count, "adr": r_adr, "consumables": r_cons, "util_day": r_util})

# SECTION 3: OPERATING PARAMS
with st.sidebar.expander("3. 運営コスト・稼働率設定", expanded=True):
    st.write("全体の想定稼働率 %")
    c_occ1, c_occ2 = st.columns([2, 1])
    target_occ = c_occ1.slider("S_Occ", 10.0, 100.0, step=0.1, key="val_occ", on_change=update_occ_num, label_visibility="collapsed")
    target_occ_num = c_occ2.number_input("N_Occ", 10.0, 100.0, step=0.1, key="val_occ_num", on_change=update_occ_slider, label_visibility="collapsed")
    
    st.write("OTA手数料率 %")
    c_ota1, c_ota2 = st.columns([2, 1])
    ota_fee_rate = c_ota1.slider("S_OTA", 0.0, 30.0, step=0.1, key="val_ota", on_change=update_ota_num, label_visibility="collapsed")
    ota_fee_num = c_ota2.number_input("N_OTA", 0.0, 30.0, step=0.1, key="val_ota_num", on_change=update_ota_slider, label_visibility="collapsed")
    
    st.write("管理費用 %")
    c_mgmt1, c_mgmt2 = st.columns([2, 1])
    management_fee_rate = c_mgmt1.slider("S_Mgmt", 0.0, 40.0, step=0.5, key="val_mgmt", on_change=update_mgmt_num, label_visibility="collapsed")
    mgmt_fee_num = c_mgmt2.number_input("N_Mgmt", 0.0, 40.0, step=0.5, key="val_mgmt_num", on_change=update_mgmt_slider, label_visibility="collapsed")
    
    fixed_op_costs = st.number_input("固定管理費", value=0, key="fixed_costs")
    
    st.write("メンテナンス (CAPEX) %")
    c_cape1, c_cape2 = st.columns([2, 1])
    cape_rate = c_cape1.slider("S_Cape", 0.0, 10.0, step=0.5, key="val_cape", on_change=update_cape_num, label_visibility="collapsed")
    cape_num = c_cape2.number_input("N_Cape", 0.0, 10.0, step=0.5, key="val_cape_num", on_change=update_cape_slider, label_visibility="collapsed")

# SAVE/LOAD SECTION
st.sidebar.markdown("---")
st.sidebar.subheader("💾 プロパティ保存・読み込み")
prop_name = st.sidebar.text_input("物件名を入力", key="new_prop_name")

if st.sidebar.button("Save Property"):
    current_data = {k: v for k, v in st.session_state.items() if not k.startswith("password") and not k.startswith("val_") and "_slider" not in k}
    # Manually add the synced values
    current_data['val_prep'] = st.session_state.val_prep
    current_data['val_occ'] = st.session_state.val_occ
    current_data['val_ota'] = st.session_state.val_ota
    current_data['val_mgmt'] = st.session_state.val_mgmt
    current_data['val_cape'] = st.session_state.val_cape
    save_data(prop_name, current_data)
    st.sidebar.success(f"Saved: {prop_name}")

db = load_db()
if not db.empty:
    selected_prop = st.sidebar.selectbox("保存済み物件を選択", db['property_name'].tolist())
    if st.sidebar.button("Load Property"):
        row = db[db.property_name == selected_prop].iloc[0]
        for key, value in row.items():
            if key != "property_name": st.session_state[key] = value
        # Refresh the synced values
        st.session_state.val_prep_num = st.session_state.val_prep
        st.session_state.val_occ_num = st.session_state.val_occ
        st.session_state.val_ota_num = st.session_state.val_ota
        st.session_state.val_mgmt_num = st.session_state.val_mgmt
        st.session_state.val_cape_num = st.session_state.val_cape
        st.rerun()

# --- CALCULATION LOGIC ---
days = 30
a_days = days * (target_occ / 100)
total_rev = sum(r['adr'] * r['count'] * a_days for r in room_configs)
total_ota_fee = total_rev * (ota_fee_rate / 100)
total_consumables = sum(r['consumables'] * r['count'] * a_days for r in room_configs)
total_utilities = sum(r['util_day'] * r['count'] * a_days for r in room_configs)
maintenance_cost = total_rev * (cape_rate / 100)
management_cost = total_rev * (management_fee_rate / 100)
total_rooms = sum(r['count'] for r in room_configs) 
total_inv = (prep_rent_cost + shikikin + reikin + broker_fee + photo_shooting + renovation + furniture_appliances + guarantee_fee + fire_insurance + license_fee + fire_safety_work + other_init)

monthly_op_cost = (rent_total + total_consumables + total_utilities + fixed_op_costs + maintenance_cost + management_cost + total_ota_fee)
profit = total_rev - monthly_op_cost
bep = total_inv / profit if profit > 0 else 0

# --- MAIN DISPLAY ---
st.subheader("📌 収支シミュレーション結果")
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("初期投資合計", fmt(total_inv))
c2.metric("月間想定売上", fmt(total_rev))
exp_ratio = (monthly_op_cost / total_rev * 100) if total_rev > 0 else 0
st.markdown("<style>[data-testid='stMetricDelta'] svg { display: none; }</style>", unsafe_allow_html=True)
c3.metric("月間費用合計", fmt(monthly_op_cost), f"費用率 {exp_ratio:.1f}%", delta_color="inverse")
c4.metric("月間営業利益", fmt(profit), f"利益率 {(profit/total_rev*100):.1f}%" if total_rev > 0 else "")
c5.metric("投資回収期間", f"{bep:.1f} ヶ月" if profit > 0 else "回収不可")

st.divider()
col_inv, col_cost = st.columns(2)
with col_inv:
    st.subheader("💰 初期投資の内訳")
    inv_df = pd.DataFrame({"項目": ["空家賃","敷金","礼金","仲介料","写真","リフォーム","家具家電","保証費用","保険","許可","消防","他"],
                           "金額": [prep_rent_cost, shikikin, reikin, broker_fee, photo_shooting, renovation, furniture_appliances, guarantee_fee, fire_insurance, license_fee, fire_safety_work, other_init]})
    st.plotly_chart(px.pie(inv_df[inv_df["金額"]>0], values='金額', names='項目', hole=0.5, color_discrete_sequence=px.colors.qualitative.Pastel), use_container_width=True)

with col_cost:
    st.subheader("💸 月間費用の詳細内訳")
    cost_df = pd.DataFrame({"項目": ["家賃", "消耗品", "光熱費", "固定費", "メンテ", "管理費", "OTA", "利益"],
                            "金額": [rent_total, total_consumables, total_utilities, fixed_op_costs, maintenance_cost, management_cost, total_ota_fee, max(0, profit)]})
    st.plotly_chart(px.pie(cost_df[cost_df["金額"]>0], values='金額', names='項目', hole=0.5, color_discrete_sequence=px.colors.qualitative.Safe), use_container_width=True)

st.divider()
st.subheader("📊 稼働率別の感度分析")
sens_data = []
for o in [30, 40, 50, 60, 70, 80, 90, 100]:
    o_days = days * (o / 100)
    o_rev = sum(r['adr'] * r['count'] * o_days for r in room_configs)
    o_cost = rent_total + fixed_op_costs + (o_rev * (cape_rate / 100)) + (o_rev * (management_fee_rate / 100)) + (o_rev * (ota_fee_rate / 100)) + sum((r['consumables']+r['util_day'])*r['count']*o_days for r in room_configs)
    o_prof = o_rev - o_cost
    sens_data.append({"稼働率": f"{o}%", "ADR": o_rev/(total_rooms*o_days) if total_rooms*o_days>0 else 0, "RevPAR": o_rev/(total_rooms*days), "GOPPAR": o_prof/(total_rooms*days), "売上": o_rev, "費用": o_cost, "利益": o_prof, "利益率": f"{(o_prof/o_rev*100):.1f}%" if o_rev>0 else "0%", "回収": f"{total_inv/o_prof:.1f}ヶ月" if o_prof > 0 else "不可"})
st.table(pd.DataFrame(sens_data).style.format({"ADR":"¥{:,.0f}","RevPAR":"¥{:,.0f}","GOPPAR":"¥{:,.0f}","売上":"¥{:,.0f}","費用":"¥{:,.0f}","利益":"¥{:,.0f}"}))
