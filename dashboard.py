import streamlit as st
import pandas as pd
import plotly.express as px

# 1. PAGE CONFIGURATION (Must be at the very top)
st.set_page_config(page_title="物件収支シミュレーター Pro", layout="wide")

# 2. PASSWORD PROTECTION LOGIC
def check_password():
    """Returns True if the user had the correct password."""
    def password_entered():
        """Checks whether a password entered by the user is correct."""
        if st.session_state["password"] == st.secrets["password"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # delete password from session state
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.title("🔒 Access Restricted")
        st.text_input(
            "Please enter the access password", type="password", on_change=password_entered, key="password"
        )
        return False
    elif not st.session_state["password_correct"]:
        st.title("🔒 Access Restricted")
        st.text_input(
            "Please enter the access password", type="password", on_change=password_entered, key="password"
        )
        st.error("😕 Password incorrect")
        return False
    else:
        return True

if not check_password():
    st.stop()

# 3. HELPER FUNCTIONS
def fmt(number):
    return f"¥{int(number):,}"

# 4. DASHBOARD UI STARTS HERE
st.title("🏨 物件収支シミュレーター（新規物件検証用）")

# --- Sidebar: Configuration ---

# --- LOGO SECTION (Moved to the Top) ---
try:
    # Adding a small empty space before the logo
    st.sidebar.write("") 
    st.sidebar.image("logo.png", use_container_width=True)
except:
    st.sidebar.info("💡 Please upload 'logo.png' to GitHub to display your logo here.")

# Now the Title shows BELOW the logo
st.sidebar.title("🛠️ 条件設定")

# Section 1: Initial Investment (Startup Costs - 10 Items)
with st.sidebar.expander("1. 初期費用・準備期間設定", expanded=True):
    rent_total = st.number_input("月額ローン及び家賃 (円)", value=0, step=1000, format="%d")
    prep_months = st.slider("開業準備期間 (ヶ月)", 0, 6, 2)
    prep_rent_cost = rent_total * prep_months
    
    st.markdown("---")
    st.write("▼ 初期費用明細")
    shikikin = st.number_input("敷金 (円)", value=0, step=10000, format="%d")
    reikin = st.number_input("礼金 (円)", value=0, step=10000, format="%d")
    broker_fee = st.number_input("仲介手数料 (円)", value=0, step=10000, format="%d")
    photo_shooting = st.number_input("写真撮影 (円)", value=0, step=5000, format="%d")
    renovation = st.number_input("リフォーム (円)", value=0, step=100000, format="%d")
    furniture_appliances = st.number_input("家具＋家電 (円)", value=0, step=100000, format="%d")
    guarantee_fee = st.number_input("保証会社費用 (円)", value=0, step=10000, format="%d")
    fire_insurance = st.number_input("火災保険 (円)", value=0, step=5000, format="%d")
    license_fee = st.number_input("旅館業許可 (円)", value=0, step=10000, format="%d")
    fire_safety_work = st.number_input("消防設備の工事 (円)", value=0, step=10000, format="%d")
    other_init = st.number_input("その他予備費 (円)", value=0, step=10000, format="%d")

total_investment = (prep_rent_cost + shikikin + reikin + broker_fee + photo_shooting + 
                    renovation + furniture_appliances + guarantee_fee + 
                    fire_insurance + license_fee + fire_safety_work + other_init)

# Section 2: Room Type Configuration
st.sidebar.markdown("### 2. 部屋タイプ別の設定")
num_types = st.sidebar.number_input("部屋タイプの種類数", min_value=1, max_value=5, value=2)

room_configs = []
for i in range(int(num_types)):
    with st.sidebar.expander(f"部屋タイプ {i+1} の詳細", expanded=True):
        name = st.text_input(f"部屋タイプ名 {i+1}", value=f"タイプ {chr(65+i)}", key=f"name_{i}")
        count = st.number_input(f"部屋数 ({name})", min_value=1, value=1, key=f"c_{i}")
        adr_input = st.number_input(f"平均単価 ADR ({name})", value=0, step=1000, format="%d", key=f"a_{i}")
        consumables_input = st.number_input(f"1日あたり消耗品 ({name})", value=0, step=100, format="%d", key=f"cons_{i}")
        util_day_input = st.number_input(f"1日あたり光熱費 ({name})", value=0, step=100, key=f"u_{i}")
        room_configs.append({"name": name, "count": count, "adr": adr_input, "consumables": consumables_input, "util_day": util_day_input})

# Section 3: Operating Parameters
with st.sidebar.expander("3. 運営コスト・稼働率設定", expanded=True):
    target_occ = st.slider("全体の想定稼働率 %", 10, 100, 70)
    ota_fee_rate = st.slider("OTA手数料率 %", 0, 30, 15)
    management_fee_rate = st.slider("管理費用 %", 0.0, 40.0, 20.0, step=0.5)
    fixed_op_costs = st.number_input("固定管理費 (ソフト、Wifi等)", value=0, step=1000, format="%d")
    cape_rate = st.slider("メンテナンス (修理、CAPEX, FF&E等) %", 0.0, 10.0, 3.0, step=0.5)

# --- Calculation Logic ---
days = 30
total_rev = 0
total_ota_fee = 0
total_consumables = 0
total_utilities = 0
total_rooms = sum(r['count'] for r in room_configs) 
a_days = days * (target_occ / 100)

for r in room_configs:
    r_rev = r['adr'] * r['count'] * a_days
    total_rev += r_rev
    total_ota_fee += (r_rev * (ota_fee_rate / 100))
    total_consumables += (r['consumables'] * r['count'] * a_days)
    total_utilities += (r['util_day'] * r['count'] * a_days)

maintenance_cost = total_rev * (cape_rate / 100)
management_cost = total_rev * (management_fee_rate / 100)

monthly_operating_cost = (rent_total + total_consumables + total_utilities + 
                          fixed_op_costs + maintenance_cost + management_cost + total_ota_fee)

monthly_profit = total_rev - monthly_operating_cost
bep = total_investment / monthly_profit if monthly_profit > 0 else 0

# --- Dashboard Display Metrics ---
st.subheader("📌 収支シミュレーション結果")
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("初期投資合計", fmt(total_investment))
c2.metric("月間想定売上", fmt(total_rev))

# Expense Ratio in RED (delta_color="inverse")
expense_ratio = (monthly_operating_cost / total_rev * 100) if total_rev > 0 else 0
st.markdown("<style>[data-testid='stMetricDelta'] svg { display: none; }</style>", unsafe_allow_html=True)
c3.metric("月間費用合計", fmt(monthly_operating_cost), f"費用率 {expense_ratio:.1f}%", delta_color="inverse")

c4.metric("月間営業利益", fmt(monthly_profit), f"利益率 {(monthly_profit/total_rev)*100:.1f}%" if total_rev > 0 else "")
c5.metric("投資回収期間", f"{bep:.1f} ヶ月" if monthly_profit > 0 else "回収不可")

st.divider()

# --- Charts Section ---
col_inv, col_cost = st.columns(2)

with col_inv:
    st.subheader("💰 初期投資の内訳")
    inv_df = pd.DataFrame({
        "項目": ["空家賃","敷金","礼金","仲介料","写真","リフォーム","家具家電","保証会社費用","火災保険","許可","消防工事","他"],
        "金額": [prep_rent_cost, shikikin, reikin, broker_fee, photo_shooting, renovation, furniture_appliances, guarantee_fee, fire_insurance, license_fee, fire_safety_work, other_init]
    })
    fig_inv = px.pie(inv_df[inv_df["金額"]>0], values='金額', names='項目', hole=0.5, color_discrete_sequence=px.colors.qualitative.Pastel)
    st.plotly_chart(fig_inv, use_container_width=True)

with col_cost:
    st.subheader("💸 月間費用の詳細内訳")
    cost_detail_df = pd.DataFrame({
        "項目": ["家賃", "消耗品", "光熱費", "固定管理費", "メンテナンス", "管理費用", "OTA手数料", "営業利益"],
        "金額": [rent_total, total_consumables, total_utilities, fixed_op_costs, maintenance_cost, management_cost, total_ota_fee, max(0, monthly_profit)]
    })
    fig_monthly = px.pie(cost_detail_df[cost_detail_df["金額"]>0], values='金額', names='項目', hole=0.5, color_discrete_sequence=px.colors.qualitative.Safe)
    st.plotly_chart(fig_monthly, use_container_width=True)

st.divider()

# --- Sensitivity Analysis Table ---
st.subheader("📊 稼働率別の感度分析")
sens_data = []
for o in [30, 40, 50, 60, 70, 80, 90, 100]:
    o_occ_days = days * (o / 100)
    o_rev = sum(r['adr'] * r['count'] * o_occ_days for r in room_configs)
    o_ota = o_rev * (ota_fee_rate/100)
    o_cons = sum(r['consumables']*r['count']*o_occ_days for r in room_configs)
    o_util = sum(r['util_day']*r['count']*o_occ_days for r in room_configs)
    o_capex = o_rev * (cape_rate / 100)
    o_mgmt = o_rev * (management_fee_rate / 100)
    
    o_total_cost = rent_total + fixed_op_costs + o_capex + o_mgmt + o_ota + o_cons + o_util
    o_prof = o_rev - o_total_cost
    
    o_margin = (o_prof / o_rev * 100) if o_rev > 0 else 0
    o_adr = o_rev / (total_rooms * o_occ_days) if (total_rooms * o_occ_days) > 0 else 0
    o_revpar = o_rev / (total_rooms * days) if (total_rooms * days) > 0 else 0
    o_goppar = o_prof / (total_rooms * days) if (total_rooms * days) > 0 else 0
    
    sens_data.append({
        "稼働率": f"{o}%",
        "ADR": o_adr,
        "RevPAR": o_revpar,
        "GOPPAR": o_goppar,
        "売上": o_rev, 
        "費用合計": o_total_cost,
        "営業利益": o_prof, 
        "利益率": f"{o_margin:.1f}%",
        "回収期間": f"{total_investment/o_prof:.1f}ヶ月" if o_prof > 0 else "回収不可"
    })

st.table(pd.DataFrame(sens_data).style.format({
    "ADR": "¥{:,.0f}",
    "RevPAR": "¥{:,.0f}",
    "GOPPAR": "¥{:,.0f}",
    "売上": "¥{:,.0f}", 
    "費用合計": "¥{:,.0f}", 
    "営業利益": "¥{:,.0f}"
}))
