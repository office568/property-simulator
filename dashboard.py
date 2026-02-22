import streamlit as st
import pandas as pd
import plotly.express as px
from streamlit_gsheets import GSheetsConnection

# 1. PAGE CONFIGURATION
st.set_page_config(
    page_title="Property Simulator Pro", 
    layout="wide",
    initial_sidebar_state="expanded" 
)

# 2. HELPER FUNCTIONS
def fmt(number):
    try:
        if pd.isna(number) or number == float('inf') or number == float('-inf'):
            return "¥0"
        return f"¥{int(number):,}"
    except:
        return "¥0"

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
    if not full_df.empty and 'property_name' in full_df.columns:
        full_df = full_df[~((full_df.property_name == name) & (full_df.owner_email == user_email))]
    new_df = pd.concat([full_df, pd.DataFrame([clean_dict])], ignore_index=True)
    conn.update(data=new_df)
    st.cache_data.clear()

def delete_from_google_sheets(name, user_email):
    try:
        full_df = conn.read(ttl="0s")
        if not full_df.empty:
            full_df = full_df[~((full_df.property_name == name) & (full_df.owner_email == user_email))]
            conn.update(data=full_df)
            st.cache_data.clear()
    except: pass

# 4. SESSION STATE INITIALIZATION
defaults = {
    "rent_total": 0, "shikikin": 0, "reikin": 0, "broker_fee": 0, "guar": 0,
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
            st.session_state[k] = f"Type {chr(65+i)}" if "name" in k else (1 if "c_" in k else 0)

# --- 5. LOGIN & BOT BYPASS ---
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
        st.title("🏡 Property Simulator")
        col1, col2 = st.columns(2)
        email_input = col1.text_input("Email").strip().lower()
        pass_input = col2.text_input("Passcode", type="password")
        if st.button("Login", use_container_width=True):
            if "@" in email_input and pass_input == MASTER_CODE:
                st.session_state["user_email"] = email_input
                st.rerun()
            else: st.error("Invalid credentials.")
        return False
    return True

if not check_user(): st.stop()
user_email = st.session_state["user_email"]

# --- 6. SIDEBAR: CLOUD ---
st.sidebar.title(f"👤 {user_email}")
if st.sidebar.button("Logout"):
    del st.session_state["user_email"]
    st.query_params.clear()
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.markdown("### ☁️ Cloud Save/Load")
db = load_db(user_email)
if not db.empty:
    target_prop = st.sidebar.selectbox("Select Property", db['property_name'].tolist())
    c_load, c_del = st.sidebar.columns(2)
    if c_load.button("📥 Load", use_container_width=True):
        saved_row = db[db.property_name == target_prop].iloc[0]
        for key, value in saved_row.items():
            if key in ["property_name", "owner_email"]: continue
            st.session_state[key] = value
        st.rerun()
    if c_del.button("🗑️ Delete", use_container_width=True):
        delete_from_google_sheets(target_prop, user_email)
        st.rerun()

# --- 7. INPUTS ---
with st.sidebar.expander("1. Initial Costs & Prep Period", expanded=True):
    rent_total = st.number_input("Monthly Rent/Loan (円)", min_value=0, step=1000, key="rent_total")
    val_prep = st.number_input("Prep Period (Months) ⓘ", min_value=0, max_value=12, key="val_prep")
    prep_rent_cost = rent_total * val_prep
    st.markdown("---")
    shikikin = st.number_input("Security Deposit (円)", min_value=0, step=1000, key="shikikin")
    reikin = st.number_input("Key Money (円)", min_value=0, step=1000, key="reikin")
    broker_fee = st.number_input("Broker Fee (円)", min_value=0, step=1000, key="broker_fee")
    guar_fee = st.number_input("Insurance/Guarantor Fee (円)", min_value=0, step=1000, key="guar")
    renovation = st.number_input("Renovation (円)", min_value=0, step=10000, key="renov")
    furn = st.number_input("Furniture/Appliances (円)", min_value=0, step=10000, key="furn")
    license_fee = st.number_input("License/Permits (円)", min_value=0, step=1000, key="license")
    fire_work = st.number_input("Fire Safety Works (円)", min_value=0, step=1000, key="fire_work")
    other_init = st.number_input("Other Startup Costs (円)", min_value=0, step=1000, key="other")

st.sidebar.markdown("### 2. Room Settings")
num_types = int(st.sidebar.number_input("Number of Room Types", min_value=1, max_value=5, key="num_types"))
room_configs = []
for i in range(num_types):
    with st.sidebar.expander(f"Room Type {i+1}", expanded=True):
        r_count = st.number_input(f"Room Count {i+1}", min_value=1, key=f"c_{i}")
        r_adr = st.number_input(f"ADR (円) {i+1}", min_value=0, step=500, key=f"a_{i}")
        r_cons = st.number_input(f"Consumables/Night {i+1}", min_value=0, step=10, key=f"cons_{i}")
        r_util = st.number_input(f"Utilities/Night {i+1}", min_value=0, step=10, key=f"u_{i}")
        room_configs.append({"count": r_count, "adr": r_adr, "cons": r_cons, "util": r_util})

with st.sidebar.expander("3. OpEx & Occupancy", expanded=True):
    val_occ = st.number_input("Occupancy % ⓘ", min_value=0.0, max_value=100.0, step=0.1, key="val_occ")
    ota_fee = st.number_input("OTA Commission %", min_value=0.0, step=0.1, key="val_ota")
    mgmt_fee = st.number_input("Management Fee %", min_value=0.0, step=0.5, key="val_mgmt")
    fixed_op = st.number_input("Monthly Fixed OpEx (円)", min_value=0, step=1000, key="fixed_costs")
    capex_r = st.number_input("Maintenance (CAPEX) %", min_value=0.0, step=0.5, key="val_cape")

with st.sidebar.expander("4. Profit Target", expanded=True):
    target_profit_val = st.number_input("Target Monthly Profit (円)", min_value=0, step=10000, key="target_profit")

# --- 8. CALCULATION ---
days = 30
occ_rate = val_occ / 100
total_rev = sum(r['adr'] * r['count'] * days * occ_rate for r in room_configs)
total_var_costs = sum((r['cons'] + r['util']) * r['count'] * days * occ_rate for r in room_configs)
fee_total_rate = (ota_fee + mgmt_fee + capex_r) / 100
commissions = total_rev * fee_total_rate
monthly_exp = rent_total + total_var_costs + fixed_op + commissions
profit = total_rev - monthly_exp
startup_total = prep_rent_cost + shikikin + reikin + broker_fee + guar_fee + renovation + furn + license_fee + fire_work + other_init
payback = startup_total / profit if profit > 0 else 0

# --- 9. DASHBOARD ---
st.subheader("📌 Key Results")
m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("Total Startup", fmt(startup_total))
m2.metric("Projected Revenue", fmt(total_rev))
m3.metric("Total Expenses", fmt(monthly_exp))
m4.metric("Operating Profit", fmt(profit))
m5.metric("Payback Period", f"{payback:.1f} Months" if profit > 0 else "N/A")

st.divider()
cl, cr = st.columns(2)
with cl:
    st.subheader("💰 Startup Breakdown")
    df_i = pd.DataFrame({"Item": ["Prep Rent","Deposit","Key Money","Broker","Insurance","Renov","Furniture","License","Fire Safety","Other"],"Value": [prep_rent_cost, shikikin, reikin, broker_fee, guar_fee, renovation, furn, license_fee, fire_work, other_init]})
    # Added unique ID to plotly chart
    st.plotly_chart(px.pie(df_i[df_i["Value"]>0], values='Value', names='Item', hole=0.5), use_container_width=True, key="startup_pie_chart")
with cr:
    st.subheader("💸 Monthly Expenses")
    df_m = pd.DataFrame({"Item": ["Rent", "Variable", "Fixed", "Fees", "Profit"],"Value": [rent_total, total_var_costs, fixed_op, commissions, max(0, profit)]})
    # Added unique ID to plotly chart
    st.plotly_chart(px.pie(df_m[df_m["Value"]>0], values='Value', names='Item', hole=0.5), use_container_width=True, key="monthly_pie_chart")

# --- 10. STRATEGY ANALYSIS ---
st.divider()
st.subheader("📈 Strategy & Pricing Analysis")

# SECTION A: UNIT & ADR BREAKDOWN
st.markdown("#### A. Required ADR for Breakeven vs. Target")
col_info, col_table = st.columns([1, 2])

with col_info:
    fixed_total = rent_total + fixed_op
    st.info("**Current Setup Summary**")
    st.metric("Total Monthly Fixed Costs", fmt(fixed_total))
    st.metric("Target Monthly Profit", fmt(target_profit_val))
    cm_ratio = (1 - fee_total_rate) * 100
    st.metric("Contribution Margin Ratio", f"{int(round(cm_ratio))}%")

with col_table:
    be_data = []
    tot_rooms = sum(r['count'] for r in room_configs)
    fee_denom = (1 - fee_total_rate)
    for o in range(10, 101, 10):
        nights = tot_rooms * 30 * (o/100)
        if nights > 0 and fee_denom > 0:
            var_night = sum((r['cons'] + r['util']) * r['count'] for r in room_configs) / tot_rooms if tot_rooms > 0 else 0
            be_adr = (fixed_total / nights + var_night) / fee_denom
            tg_adr = ((fixed_total + target_profit_val) / nights + var_night) / fee_denom
            be_data.append({"Occ": f"{o}%", "Breakeven ADR": fmt(be_adr), "Target Profit ADR": fmt(tg_adr)})
    st.table(pd.DataFrame(be_data))

# SECTION B: SENSITIVITY ANALYSIS
st.markdown("#### B. Sensitivity Analysis (Detailed Profit Breakdown)")
st.caption("Profitability at your CURRENT set price across different occupancy levels.")

sensitivity_rows = []
avg_adr_current = sum(r['adr'] * r['count'] for r in room_configs) / tot_rooms if tot_rooms > 0 else 0
avg_var_night = sum((r['cons'] + r['util']) * r['count'] for r in room_configs) / tot_rooms if tot_rooms > 0 else 0

for o in range(10, 101, 10):
    o_nights = tot_rooms * 30 * (o/100)
    o_rev = avg_adr_current * o_nights
    o_var = avg_var_night * o_nights
    o_fees = o_rev * fee_total_rate
    o_exp = fixed_total + o_var + o_fees
    o_profit = o_rev - o_exp
    o_margin = (o_profit / o_rev * 100) if o_rev > 0 else 0
    o_payback = startup_total / o_profit if o_profit > 0 else 0
    
    sensitivity_rows.append({
        "Occ %": f"{o}%",
        "Total Revenue": fmt(o_rev),
        "Total Expenses": fmt(o_exp),
        "Monthly Profit": fmt(o_profit),
        "Profit Margin": f"{round(o_margin, 1)}%",
        "Payback (Months)": f"{round(o_payback, 1)}" if o_payback > 0 else "N/A"
    })

st.table(pd.DataFrame(sensitivity_rows))

# SAVE BUTTON
st.sidebar.markdown("---")
new_name = st.sidebar.text_input("Name this Property to Save")
if st.sidebar.button("💾 Save to Cloud", use_container_width=True):
    if new_name:
        to_save = {k: v for k, v in st.session_state.items() if not k.startswith("user_")}
        save_to_google_sheets(new_name, user_email, to_save)
        st.sidebar.success("Saved!")
        st.rerun()
