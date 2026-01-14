import streamlit as st
import pandas as pd
import plotly.express as px
from streamlit_gsheets import GSheetsConnection
import io

# 1. PAGE CONFIGURATION
st.set_page_config(page_title="物件収支シミュレーター Pro", layout="wide")

# 2. HELPER FUNCTIONS
def fmt(number):
    try: return f"¥{int(number):,}"
    except: return "¥0"

# 3. GOOGLE SHEETS CONNECTION
conn = st.connection("gsheets", type=GSheetsConnection)

def load_db():
    try:
        df = conn.read(ttl="0s")
        return df.dropna(subset=['property_name'])
    except:
        return pd.DataFrame(columns=['property_name'])

def save_to_google_sheets(name, data_dict):
    df = load_db()
    clean_dict = {k: v for k, v in data_dict.items() if not k.startswith("FormSubmit") and "password" not in k and "confirm" not in k}
    clean_dict['property_name'] = str(name)
    if not df.empty and name in df['property_name'].values:
        df = df[df.property_name != name]
    df = pd.concat([df, pd.DataFrame([clean_dict])], ignore_index=True)
    conn.update(data=df)
    st.cache_data.clear()

def delete_from_google_sheets(name):
    df = load_db()
    if not df.empty:
        df = df[df.property_name != name]
        conn.update(data=df)
        st.cache_data.clear()

# 4. SESSION STATE INITIALIZATION
defaults = {
    "rent_total": 0, "shikikin": 0, "reikin": 0, "broker_fee": 0, "photo": 0,
    "renov": 0, "furn": 0, "guar": 0, "fire": 0, "license": 0, "fire_work": 0, "other": 0,
    "num_types": 2, "fixed_costs": 0, "val_prep": 2, "val_prep_num": 2,
    "val_occ": 70.0, "val_occ_num": 70.0, "val_ota": 15.0, "val_ota_num": 15.0,
    "val_mgmt": 20.0, "val_mgmt_num": 20.0, "val_cape": 3.0, "val_cape_num": 3.0,
    "confirm_delete": False
}
for key, val in defaults.items():
    if key not in st.session_state: st.session_state[key] = val

for i in range(5):
    for k_suffix in ["name_", "c_", "a_", "cons_", "u_"]:
        k = f"{k_suffix}{i}"
        if k not in st.session_state:
            st.session_state[k] = f"タイプ {chr(65+i)}" if "name" in k else (1 if "c_" in k else 0)

# Sync Callbacks
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

# 5. PASSWORD PROTECTION
def check_password():
    if "password_correct" not in st.session_state:
        st.title("🔒 Access Restricted")
        password_input = st.text_input("Please enter password", type="password")
        if st.button("Login"):
            if password_input == st.secrets["password"]:
                st.session_state["password_correct"] = True
                st.rerun()
            else:
                st.error("😕 Password incorrect")
        return False
    return True

if not check_password(): st.stop()

# 6. UI: SIDEBAR
db = load_db()
try: st.sidebar.image("logo.png", use_container_width=True)
except: pass

st.sidebar.title("🛠️ 条件設定")
st.sidebar.markdown("### ☁️ クラウド読込・削除")

if not db.empty:
    target_prop = st.sidebar.selectbox("保存済み物件を選択", db['property_name'].tolist())
    col_load, col_del = st.sidebar.columns(2)
    
    if col_load.button("📥 読み込む"):
        saved_row = db[db.property_name == target_prop].iloc[0]
        for key, value in saved_row.items():
            if key == "property_name": continue
            if pd.isna(value): st.session_state[key] = defaults.get(key, 0)
            elif "name_" in key: st.session_state[key] = str(value)
            elif "val_" in key or "rate" in key: st.session_state[key] = float(value)
            else:
                try: st.session_state[key] = int(value)
                except: st.session_state[key] = value
        st.session_state.val_prep_num = int(st.session_state.val_prep)
        st.session_state.val_occ_num = float(st.session_state.val_occ)
        st.session_state.val_ota_num = float(st.session_state.val_ota)
        st.session_state.val_mgmt_num = float(st.session_state.val_mgmt)
        st.session_state.val_cape_num = float(st.session_state.val_cape)
        st.rerun()

    if col_del.button("🗑️ 削除"):
        st.session_state.confirm_delete = True

    if st.session_state.confirm_delete:
        st.sidebar.error(f"本当に {target_prop} を削除しますか？")
        c1, c2 = st.sidebar.columns(2)
        if c1.button("✅ はい"):
            delete_from_google_sheets(target_prop)
            st.session_state.confirm_delete = False
            for key, val in defaults.items(): st.session_state[key] = val
            st.rerun()
        if c2.button("❌ いいえ"):
            st.session_state.confirm_delete = False
            st.rerun()

st.sidebar.markdown("---")

# SECTION 1: INITIAL INVESTMENT
with st.sidebar.expander("1. 初期費用・準備期間設定", expanded=True):
    rent_total = st.number_input("月額ローン及び家賃 (円)", step=1000, key="rent_total")
    st.write("開業準備期間 (ヶ月)")
    c_p1, c_p2 = st.columns([2, 1])
    prep_months = c_p1.slider("Slider Prep", 0, 6, key="val_prep", on_change=update_prep_num, label_visibility="collapsed")
    prep_months_num = c_p2.number_input("Num Prep", 0, 6, step=1, key="val_prep_num", on_change=update_prep_slider, label_visibility="collapsed")
    prep_rent_cost = rent_total * prep_months
    
    st.markdown("---")
    shikikin = st.number_input("敷金 (円)", step=1000, key="shikikin")
    reikin = st.number_input("礼金 (円)", step=1000, key="reikin")
    broker_fee = st.number_input("仲介手数料 (円)", step=1000, key="broker_fee")
    photo_shooting = st.number_input("写真撮影 (円)", step=1000, key="photo")
    renovation = st.number_input("リフォーム (円)", step=10000, key="renov")
    furniture_appliances = st.number_input("家具＋家電 (円)", step=10000, key="furn")
    guarantee_fee = st.number_input("保証会社費用 (円)", step=1000, key="guar")
    fire_insurance = st.number_input("火災保険 (円)", step=1000, key="fire")
    license_fee = st.number_input("旅館業許可 (円)", step=1000, key="license")
    fire_safety_work = st.number_input("消防設備の工事 (円)", step=1000, key="fire_work")
    other_init = st.number_input("その他予備費 (円)", step=1000, key="other")

# SECTION 2: ROOM CONFIG
st.sidebar.markdown("### 2. 部屋タイプ別の設定")
num_types = int(st.sidebar.number_input("部屋タイプの種類数", min_value=1, max_value=5, step=1, key="num_types"))
room_configs = []
for i in range(num_types):
    with st.sidebar.expander(f"部屋タイプ {i+1}", expanded=True):
        r_name = st.text_input("部屋タイプ名", key=f"name_{i}")
        r_count = st.number_input("部屋数", min_value=1, step=1, key=f"c_{i}")
        r_adr = st.number_input("平均単価 ADR (円)", step=500, key=f"a_{i}")
        r_cons = st.number_input("1日あたり消耗品 (円)", step=10, key=f"cons_{i}")
        r_util = st.number_input("1日あたり光熱費 (円)", step=10, key=f"u_{i}")
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
    fixed_op_costs = st.number_input("固定管理費 (円)", step=1000, key="fixed_costs")
    st.write("メンテナンス (CAPEX) %")
    c_cape1, c_cape2 = st.columns([2, 1])
    cape_rate = c_cape1.slider("S_Cape", 0.0, 10.0, step=0.5, key="val_cape", on_change=update_cape_num, label_visibility="collapsed")
    cape_num = c_cape2.number_input("N_Cape", 0.0, 10.0, step=0.5, key="val_cape_num", on_change=update_cape_slider, label_visibility="collapsed")

# 7. CALCULATIONS
days = 30
active_days = days * (target_occ / 100)
total_rev = sum(r['adr'] * r['count'] * active_days for r in room_configs)
total_ota = total_rev * (ota_fee_rate / 100)
total_cons = sum(r['consumables'] * r['count'] * active_days for r in room_configs)
total_utils = sum(r['util_day'] * r['count'] * active_days for r in room_configs)
maintenance_amt = total_rev * (cape_rate / 100)
management_amt = total_rev * (management_fee_rate / 100)
num_rooms = sum(r['count'] for r in room_configs) 
startup_cost = (prep_rent_cost + shikikin + reikin + broker_fee + photo_shooting + renovation + furniture_appliances + guarantee_fee + fire_insurance + license_fee + fire_safety_work + other_init)
monthly_cost = (rent_total + total_cons + total_utils + fixed_op_costs + maintenance_amt + management_amt + total_ota)
profit = total_rev - monthly_cost
payback = startup_cost / profit if profit > 0 else 0

# 8. SAVE & EXPORT SECTION
st.sidebar.markdown("---")
new_save_name = st.sidebar.text_input("新規物件名を入力して保存", key="save_input_name")
if st.sidebar.button("💾 クラウドに保存"):
    to_save = {k: v for k, v in st.session_state.items() if not k.startswith("password") and "_slider" not in k and "confirm" not in k}
    save_to_google_sheets(new_save_name, to_save)
    st.sidebar.success(f"保存完了: {new_save_name}")
    st.rerun()

# --- CSV EXPORT LOGIC ---
st.sidebar.markdown("### 📥 データ出力")
export_data = {
    "項目": ["物件名", "初期投資合計", "月間想定売上", "月間費用合計", "月間営業利益", "投資回収期間", "想定稼働率", "ADR"],
    "値": [new_save_name if new_save_name else "未設定", fmt(startup_cost), fmt(total_rev), fmt(monthly_cost), fmt(profit), f"{payback:.1f}ヶ月", f"{target_occ}%", fmt(total_rev/(num_rooms*active_days) if active_days>0 else 0)]
}
export_df = pd.DataFrame(export_data)
csv_buffer = io.StringIO()
export_df.to_csv(csv_buffer, index=False)
st.sidebar.download_button(
    label="📥 CSVエクスポート (配布用)",
    data=csv_buffer.getvalue(),
    file_name=f"simulation_{new_save_name}.csv",
    mime="text/csv",
)

# 9. MAIN DISPLAY
st.subheader("📌 収支シミュレーション結果")
m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("初期投資合計", fmt(startup_cost))
m2.metric("月間想定売上", fmt(total_rev))
e_ratio = (monthly_cost / total_rev * 100) if total_rev > 0 else 0
st.markdown("<style>[data-testid='stMetricDelta'] svg { display: none; }</style>", unsafe_allow_html=True)
m3.metric("月間費用合計", fmt(monthly_cost), f"費用率 {e_ratio:.1f}%", delta_color="inverse")
m4.metric("月間営業利益", fmt(profit), f"利益率 {(profit/total_rev)*100:.1f}%" if total_rev > 0 else "")
m5.metric("投資回収期間", f"{payback:.1f} ヶ月" if profit > 0 else "回収不可")

st.divider()
cl, cr = st.columns(2)
with cl:
    st.subheader("💰 初期投資の内訳")
    df_i = pd.DataFrame({"項目": ["空家賃","敷金","礼金","仲介料","写真","リフォーム","家具家電","保証","保険","許可","工事","他"],"金額": [prep_rent_cost, shikikin, reikin, broker_fee, photo_shooting, renovation, furniture_appliances, guarantee_fee, fire_insurance, license_fee, fire_safety_work, other_init]})
    st.plotly_chart(px.pie(df_i[df_i["金額"]>0], values='金額', names='項目', hole=0.5, color_discrete_sequence=px.colors.qualitative.Pastel), use_container_width=True)
with cr:
    st.subheader("💸 月間費用の詳細内訳")
    df_m = pd.DataFrame({"項目": ["家賃", "消耗品", "光熱費", "固定費", "メンテ", "管理費", "OTA", "利益"],"金額": [rent_total, total_cons, total_utils, fixed_op_costs, maintenance_amt, management_amt, total_ota, max(0, profit)]})
    st.plotly_chart(px.pie(df_m[df_m["金額"]>0], values='金額', names='項目', hole=0.5, color_discrete_sequence=px.colors.qualitative.Safe), use_container_width=True)

st.divider()
st.subheader("📊 稼働率別の感度分析")
analysis_rows = []
for occ_p in [30, 40, 50, 60, 70, 80, 90, 100]:
    o_d = days * (occ_p / 100)
    o_r = sum(r['adr'] * r['count'] * o_d for r in room_configs)
    o_c = rent_total + fixed_op_costs + (o_r * (cape_rate / 100)) + (o_r * (management_fee_rate / 100)) + (o_r * (ota_fee_rate / 100)) + sum((r['consumables']+r['util_day'])*r['count']*o_d for r in room_configs)
    o_p = o_r - o_c
    analysis_rows.append({"稼働率": f"{occ_p}%", "ADR": o_r/(num_rooms*o_d) if num_rooms*o_d>0 else 0, "RevPAR": o_r/(num_rooms*days), "GOPPAR": o_p/(num_rooms*days), "売上": o_r, "費用": o_c, "利益": o_p, "利益率": f"{(o_p/o_r*100):.1f}%" if o_r>0 else "0%", "回収": f"{startup_cost/o_p:.1f}ヶ月" if o_p > 0 else "不可"})
st.table(pd.DataFrame(analysis_rows).style.format({"ADR":"¥{:,.0f}","RevPAR":"¥{:,.0f}","GOPPAR":"¥{:,.0f}","売上":"¥{:,.0f}","費用":"¥{:,.0f}","利益":"¥{:,.0f}"}))
