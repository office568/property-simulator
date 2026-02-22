import streamlit as st
import pandas as pd
import plotly.express as px
from streamlit_gsheets import GSheetsConnection

# 1. ページ設定
st.set_page_config(
    page_title="物件収支シミュレーター Pro", 
    layout="wide",
    initial_sidebar_state="expanded" 
)

# 2. ヘルパー関数（数字のフォーマット）
def fmt(number):
    try:
        if pd.isna(number) or number == float('inf') or number == float('-inf'):
            return "¥0"
        return f"¥{int(number):,}"
    except:
        return "¥0"

# 3. Googleスプレッドシート接続
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

# 4. セッション状態の初期化
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
            st.session_state[k] = f"タイプ {chr(65+i)}" if "name" in k else (1 if "c_" in k else 0)

# --- 5. ログイン・自動化対応 ---
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
        col1, col2 = st.columns(2)
        email_input = col1.text_input("メールアドレス").strip().lower()
        pass_input = col2.text_input("パスコード", type="password")
        if st.button("ログイン", use_container_width=True):
            if "@" in email_input and pass_input == MASTER_CODE:
                st.session_state["user_email"] = email_input
                st.rerun()
            else: st.error("認証情報が正しくありません。")
        return False
    return True

if not check_user(): st.stop()
user_email = st.session_state["user_email"]

# --- 6. サイドバー：クラウド管理 ---
st.sidebar.title(f"👤 {user_email}")
if st.sidebar.button("ログアウト"):
    del st.session_state["user_email"]
    st.query_params.clear()
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.markdown("### ☁️ クラウド読込・削除")
db = load_db(user_email)
if not db.empty:
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

# --- 7. 入力セクション ---
with st.sidebar.expander("1. 初期費用・準備期間設定", expanded=True):
    rent_total = st.number_input("月額ローン及び家賃 (円)", min_value=0, step=1000, key="rent_total", help="物件の毎月の家賃またはローン返済額です。")
    val_prep = st.number_input("開業準備期間 (ヶ月) ⓘ", min_value=0, max_value=12, key="val_prep", help="家具の設置や工事など、売上が発生せず家賃のみが発生する期間です。")
    prep_rent_cost = rent_total * val_prep
    st.markdown("---")
    shikikin = st.number_input("敷金 (円)", min_value=0, step=1000, key="shikikin", help="契約時に支払う敷金の総額です。")
    reikin = st.number_input("礼金 (円)", min_value=0, step=1000, key="reikin", help="契約時に支払う礼金の総額です。")
    broker_fee = st.number_input("仲介手数料 (円)", min_value=0, step=1000, key="broker_fee", help="不動産会社に支払う仲介手数料です。")
    guar_fee = st.number_input("保険会社費用 (円)", min_value=0, step=1000, key="guar", help="家賃保証会社や火災保険料の総額です。")
    renovation = st.number_input("リフォーム費用 (円)", min_value=0, step=10000, key="renov", help="改装や修繕にかかる費用です。")
    furn = st.number_input("家具・家電費用 (円)", min_value=0, step=10000, key="furn", help="ベッド、家電、備品の購入費用です。")
    license_fee = st.number_input("旅館業許可申請 (円)", min_value=0, step=1000, key="license", help="行政書士への依頼費用や申請手数料です。")
    fire_work = st.number_input("消防設備工事 (円)", min_value=0, step=1000, key="fire_work", help="誘導灯や火災報知器の設置工事費用です。")
    other_init = st.number_input("その他予備費 (円)", min_value=0, step=1000, key="other", help="写真撮影やその他諸経費です。")

st.sidebar.markdown("### 2. 部屋別の設定")
num_types = int(st.sidebar.number_input("部屋タイプの種類数", min_value=1, max_value=5, key="num_types", help="広さや料金が異なる部屋のバリエーション数です。"))
room_configs = []
for i in range(num_types):
    with st.sidebar.expander(f"部屋タイプ {i+1}", expanded=True):
        r_count = st.number_input(f"部屋数 {i+1}", min_value=1, key=f"c_{i}", help="このタイプの部屋がいくつあるか。")
        r_adr = st.number_input(f"ADR (円) {i+1}", min_value=0, step=500, key=f"a_{i}", help="1泊あたりの平均客室単価です。")
        r_cons = st.number_input(f"消耗品/泊 {i+1}", min_value=0, step=10, key=f"cons_{i}", help="1泊あたりにかかるアメニティ等の実費です。")
        r_util = st.number_input(f"光熱費/泊 {i+1}", min_value=0, step=10, key=f"u_{i}", help="1泊あたりの平均的な電気・水道代です。")
        room_configs.append({"count": r_count, "adr": r_adr, "cons": r_cons, "util": r_util})

with st.sidebar.expander("3. 運営コスト・稼働率設定", expanded=True):
    val_occ = st.number_input("想定稼働率 % ⓘ", min_value=0.0, max_value=100.0, step=0.1, key="val_occ", help="1ヶ月の中で部屋が埋まる割合です。")
    ota_fee = st.number_input("OTA手数料 %", min_value=0.0, step=0.1, key="val_ota", help="予約サイト（Airbnb等）に支払う手数料率です。")
    mgmt_fee = st.number_input("運営管理費 %", min_value=0.0, step=0.5, key="val_mgmt", help="管理会社に支払う委託料率です。")
    fixed_op = st.number_input("固定運営費 (円)", min_value=0, step=1000, key="fixed_costs", help="ネット代やシステム利用料など毎月固定の出費です。")
    capex_r = st.number_input("修繕積立 (CAPEX) %", min_value=0.0, step=0.5, key="val_cape", help="将来の修繕や備品交換のために売上から積み立てる割合です。")

with st.sidebar.expander("4. 目標利益の設定", expanded=True):
    target_profit_val = st.number_input("目標月間利益 (円)", min_value=0, step=10000, key="target_profit", help="毎月手元に残したい理想の利益額です。")

# --- 8. 計算ロジック ---
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

# --- 9. メインダッシュボード ---
st.subheader("📌 収支シミュレーション結果")
m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("初期投資合計", fmt(startup_total), help="物件をオープンするまでにかかる費用の総額です。")
m2.metric("月間想定売上", fmt(total_rev), help="現在の設定に基づいた月間の予想総売上です。")
m3.metric("月間費用合計", fmt(monthly_exp), help="家賃、手数料、光熱費など全ての支出の合計です。")
m4.metric("月間営業利益", fmt(profit), help="売上から費用を引いた最終的な手残り金額です。")
m5.metric("投資回収期間", f"{payback:.1f} ヶ月" if profit > 0 else "回収不可", help="初期投資を利益で完済するまでの期間です。")

st.divider()
cl, cr = st.columns(2)
with cl:
    st.subheader("💰 初期投資の内訳")
    df_i = pd.DataFrame({"項目": ["空家賃","敷金","礼金","仲介料","保険","リフォーム","家具家電","許可","消防工事","他"],"金額": [prep_rent_cost, shikikin, reikin, broker_fee, guar_fee, renovation, furn, license_fee, fire_work, other_init]})
    st.plotly_chart(px.pie(df_i[df_i["金額"]>0], values='金額', names='項目', hole=0.5, color_discrete_sequence=px.colors.qualitative.Pastel), use_container_width=True, key="startup_pie_jp")
with cr:
    st.subheader("💸 月間費用の詳細")
    df_m = pd.DataFrame({"項目": ["家賃", "変動費", "固定運営費", "各種手数料", "利益"],"金額": [rent_total, total_var_costs, fixed_op, commissions, max(0, profit)]})
    st.plotly_chart(px.pie(df_m[df_m["金額"]>0], values='金額', names='項目', hole=0.5, color_discrete_sequence=px.colors.qualitative.Safe), use_container_width=True, key="monthly_pie_jp")

# --- 10. 戦略分析 ---
st.divider()
st.subheader("📈 戦略分析 (Strategy & Pricing Analysis)")

# セクションA
st.markdown("#### A. 損益分岐点と目標単価の分析")
col_info, col_table = st.columns([1, 2])

with col_info:
    fixed_total = rent_total + fixed_op
    st.info("**現在の条件まとめ**")
    st.metric("月間固定費合計", fmt(fixed_total), help="稼働に関わらず発生するコストの合計です。")
    st.metric("目標利益額", fmt(target_profit_val), help="設定した利益目標です。")
    cm_ratio = (1 - fee_total_rate) * 100
    st.metric("貢献利益率", f"{int(round(cm_ratio))}%", help="売上100円につき、家賃等の固定費の支払いに回せる利益の割合です。")

with col_table:
    st.write("**稼働率別の必要ADR（客室単価）**")
    be_data = []
    tot_rooms = sum(r['count'] for r in room_configs)
    fee_denom = (1 - fee_total_rate)
    for o in range(10, 101, 10):
        nights = tot_rooms * 30 * (o/100)
        if nights > 0 and fee_denom > 0:
            var_night = sum((r['cons'] + r['util']) * r['count'] for r in room_configs) / tot_rooms if tot_rooms > 0 else 0
            be_adr = (fixed_total / nights + var_night) / fee_denom
            tg_adr = ((fixed_total + target_profit_val) / nights + var_night) / fee_denom
            be_data.append({"稼働率": f"{o}%", "損益分岐ADR": fmt(be_adr), "目標達成ADR": fmt(tg_adr)})
    st.table(pd.DataFrame(be_data))

# セクションB
st.markdown("#### B. 収支感度分析（詳細シミュレーション）")
st.caption("※現在の販売単価（ADR）を維持した状態で、稼働率が変化した場合の利益推移です。")

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
        "稼働率": f"{o}%",
        "想定総売上": fmt(o_rev),
        "総支出額": fmt(o_exp),
        "月間利益": fmt(o_profit),
        "利益率": f"{round(o_margin, 1)}%",
        "投資回収": f"{round(o_payback, 1)}ヶ月" if o_profit > 0 else "回収不可"
    })

st.table(pd.DataFrame(sensitivity_rows))

# 保存ボタン
st.sidebar.markdown("---")
new_name = st.sidebar.text_input("物件名を付けて保存")
if st.sidebar.button("💾 クラウドに保存", use_container_width=True):
    if new_name:
        to_save = {k: v for k, v in st.session_state.items() if not k.startswith("user_")}
        save_to_google_sheets(new_name, user_email, to_save)
        st.sidebar.success("保存が完了しました！")
        st.rerun()
