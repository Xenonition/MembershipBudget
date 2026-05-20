import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# --- DATA PREPARATION ---
# Load historical master data for install-to-MAU ratio
_df_master = pd.read_csv("data/performance_master_data.csv", thousands=",")
_df_master.columns = _df_master.columns.str.replace("\n", " ", regex=False).str.strip()
_df_master["MAU"] = pd.to_numeric(_df_master["MAU"].astype(str).str.replace(",", ""), errors="coerce")
_df_master["Total Installs"] = pd.to_numeric(_df_master["Total Installs"].astype(str).str.replace(",", ""), errors="coerce")
_df_master = _df_master.dropna(subset=["Total Installs", "MAU"])
avg_install_mau_ratio = (_df_master["Total Installs"] / _df_master["MAU"]).mean()

# Forecast CSV derived ratios (from Forecast Cost CSV, ARPU=45K scenario, constant across all months)
FC_INSTALL_MAU_RATIO   = 460_746 / 664_287   # ≈ 0.6934
FC_REGISTER_MAU_RATIO  = 322_522 / 664_287   # ≈ 0.4854

# Historical weights calculated from your June-April 2025/26 season
seasonality_weights = {
    "June": 0.0459, "July": 0.0502, "August": 0.0868, "September": 0.0867,
    "October": 0.0653, "November": 0.0781, "December": 0.1278, "January": 0.1493,
    "February": 0.1187, "March": 0.0896, "April": 0.1015
}

st.set_page_config(page_title="Revenue Target Simulator", layout="wide")
st.title("⚽ Persib App: IDR 20B Revenue Modeling")

# --- SIDEBAR INPUTS ---
st.sidebar.header("Target Variables")
modeling_mode = st.sidebar.radio(
    "Modeling Mode",
    ["Revenue Target → MAU", "MAU Target → Revenue"],
    help="Revenue Target: set IDR goal, back-calculate required MAU.\nMAU Target: set total season MAU, compute resulting revenue."
)

if modeling_mode == "Revenue Target → MAU":
    target_revenue_input = st.sidebar.number_input("Seasonal Revenue Target (IDR)", value=20_000_000_000, step=1_000_000_000)
    target_mau_input = None
else:
    target_mau_input = st.sidebar.number_input("Target Total Season MAU (Sum, 11 months)", value=5_000_000, step=100_000, min_value=1)
    target_revenue_input = None
# Product prices (from forecast CSV)
PRICE_MONTHLY  = 12_000
PRICE_ANNUAL   = 120_000
PRICE_PASSPORT = 5_500_000

st.sidebar.subheader("Product Mix (% of Purchasing Users)")
pct_monthly  = st.sidebar.slider("MemberSIB Monthly (%)", 0, 100, 90)
pct_annual   = st.sidebar.slider("MemberSIB Annual (%)",  0, 100 - pct_monthly, min(9, 100 - pct_monthly))
pct_passport = 100 - pct_monthly - pct_annual
st.sidebar.caption(f"Passport Persib: **{pct_passport}%** (derived)")

arpu = (pct_monthly  / 100 * PRICE_MONTHLY +
        pct_annual   / 100 * PRICE_ANNUAL   +
        pct_passport / 100 * PRICE_PASSPORT)
st.sidebar.metric("Blended ARPU", f"IDR {arpu:,.0f}")

conversion_rate = st.sidebar.slider("MPU/MAU Conversion (%)", 0.5, 10.0, 1.69) / 100

# Show the derived output as a live preview in the sidebar
if modeling_mode == "MAU Target → Revenue":
    _preview_revenue = target_mau_input * conversion_rate * arpu
    st.sidebar.metric("Estimated Season Revenue", f"IDR {_preview_revenue / 1e9:.2f}B",
                      help="Total MAU × Conversion Rate × ARPU (before cost deductions)")

use_seasonality = st.sidebar.toggle("Weighted Growth (Follow Historical Seasonality 2025/26)", value=True)
growth_rate = st.sidebar.slider("Season Growth Rate (%)", 0, 300, 0, step=10,
    help="Linear growth ramp applied on top of weights. 0% = flat, 100% = April gets 2× the multiplier of June.")

st.sidebar.divider()
st.sidebar.header("Cost Assumptions")
tech_high = st.sidebar.toggle("Tech Cost: High Scenario", value=False,
    help="Low: IDR 69.3M/mo infra | High: IDR 86.6M/mo infra")
use_tada = st.sidebar.toggle("Include TADA Reward Platform", value=False,
    help="Adds: Deposit (10% of rev) + Transaction fee (0.4% of rev) + Annual fee IDR 45M")
use_forecast_funnel = st.sidebar.toggle("Use Forecast CSV Install/Register Ratios", value=False,
    help="Off: uses historical master data install-to-MAU ratio. On: uses Forecast CSV ratios (Install/MAU=0.69, Register/MAU=0.49).")

st.sidebar.divider()
st.sidebar.header("Model Assumptions")
st.sidebar.markdown(f"""
**Revenue Formula**
> Monthly Revenue = MAU × Conversion Rate × ARPU  
> Season Total = Sum across all 11 months

**Season Length**
> 11 months (June – April)  
> 30 days/month assumed for daily calculations

**Seasonality Weights** *(2025/26 actuals)*
> Jun {seasonality_weights['June']:.1%} · Jul {seasonality_weights['July']:.1%} · Aug {seasonality_weights['August']:.1%}  
> Sep {seasonality_weights['September']:.1%} · Oct {seasonality_weights['October']:.1%} · Nov {seasonality_weights['November']:.1%}  
> Dec {seasonality_weights['December']:.1%} · Jan {seasonality_weights['January']:.1%} · Feb {seasonality_weights['February']:.1%}  
> Mar {seasonality_weights['March']:.1%} · Apr {seasonality_weights['April']:.1%}

**Install-to-MAU Ratio**
> Derived from historical master data  
> Avg ratio: **{avg_install_mau_ratio:.2f}x** (Total Installs ÷ MAU, per month)  
> Used to back-calculate required daily installs

**Linear Growth Ramp** *(stacked on weights)*
> Jun multiplier: **1.00×** → Apr multiplier: **{1 + growth_rate/100:.2f}×**  
> Renormalized so season total always = target

**Product Prices**
> MemberSIB Monthly: IDR 12,000  
> MemberSIB Annual: IDR 120,000  
> Passport Persib: IDR 5,500,000

**Defaults**
> Mix: 90% Monthly · 9% Annual · 1% Passport → ARPU IDR 76,600  
> Conversion: 1.69% *(avg MPU/MAU, historical)*
""")

# --- CALCULATIONS ---
# Two modes:
#   Revenue Target: Total_MAU_Sum = Target_Rev / (Conv * ARPU)
#   MAU Target:     Target_Rev = Total_MAU_Sum * Conv * ARPU
if modeling_mode == "Revenue Target → MAU":
    target_revenue = target_revenue_input
    total_mau_required = target_revenue / (conversion_rate * arpu)
else:
    total_mau_required = target_mau_input
    target_revenue = total_mau_required * conversion_rate * arpu
avg_mau = total_mau_required / 11

# Monthly breakdown
months = list(seasonality_weights.keys())
n = len(months)
base_weights = [seasonality_weights[m] for m in months] if use_seasonality else [1 / n] * n
growth_multipliers = [1 + (growth_rate / 100) * (i / (n - 1)) for i in range(n)]
combined = [b * g for b, g in zip(base_weights, growth_multipliers)]
combined_sum = sum(combined)
norm_weights = [c / combined_sum for c in combined]
monthly_maus = [total_mau_required * w for w in norm_weights]

monthly_purchasing = [mau * conversion_rate for mau in monthly_maus]
monthly_revenue = [pu * arpu for pu in monthly_purchasing]

# --- COST CALCULATIONS ---
# Fixed costs per month (from forecast CSV, monthly values)
infra_monthly = 86_625_000 if tech_high else 69_300_000
fixed_per_month = (
    infra_monthly  +
    100_000_000    +  # Tech manpower
    100_000_000    +  # Marketing tools (CRM + Attribution + Analytics)
    30_000_000     +  # Acquisition campaign
    30_000_000     +  # Tactical / ad hoc
    150_000_000    +  # Marketing manpower
    208_333_333    +  # Exclusive content production
    50_000_000        # Reward manpower
)
# Variable costs as % of monthly revenue
var_pct = 0.10 + 0.10  # Prize redemption (10%) + PBI commission (10%)
if use_tada:
    var_pct += 0.10 + 0.004  # TADA deposit (10%) + transaction fee (0.4%)

monthly_costs = [
    fixed_per_month
    + monthly_revenue[i] * var_pct
    + (45_000_000 if use_tada and i == 0 else 0)   # TADA annual fee in June only
    for i in range(n)
]
monthly_net    = [monthly_revenue[i] - monthly_costs[i] for i in range(n)]
cumulative_net = [sum(monthly_net[:i + 1]) for i in range(n)]

season_total_cost = sum(monthly_costs)
season_net        = sum(monthly_net)
net_pct           = season_net / target_revenue
breakeven_month   = next((months[i] for i in range(n) if cumulative_net[i] >= 0), "Not reached")

df_model = pd.DataFrame({
    "Month": months,
    "Target MAU": monthly_maus,
    "Purchasing Users": monthly_purchasing,
    "Revenue (IDR)": monthly_revenue,
})

# --- DASHBOARD ---
col1, col2, col3, col4 = st.columns(4)

# Net to PBB summary row
st.subheader("Season Summary")
s1, s2, s3, s4 = st.columns(4)
s1.metric(
    "Total Revenue" if modeling_mode == "Revenue Target → MAU" else "Projected Revenue",
    f"IDR {target_revenue / 1e9:.2f}B",
    help=None if modeling_mode == "Revenue Target → MAU" else "Derived: Total MAU × Conversion × ARPU"
)
s2.metric("Total Cost", f"IDR {season_total_cost / 1e9:.2f}B",
          delta=f"{-season_total_cost / target_revenue:.1%} of revenue", delta_color="inverse")
s3.metric("Net to PBB", f"IDR {season_net / 1e9:.2f}B",
          delta=f"{net_pct:.1%} of revenue",
          delta_color="normal" if season_net >= 0 else "inverse")
s4.metric("Break-Even Month", breakeven_month)

st.divider()
peak_mau_idx = monthly_maus.index(max(monthly_maus))
peak_mau_month = months[peak_mau_idx]
peak_mau_value = monthly_maus[peak_mau_idx]

active_install_mau_ratio   = FC_INSTALL_MAU_RATIO  if use_forecast_funnel else avg_install_mau_ratio
active_register_mau_ratio  = FC_REGISTER_MAU_RATIO if use_forecast_funnel else avg_install_mau_ratio * 0.70

total_required_installs = total_mau_required * active_install_mau_ratio
required_installs_per_day = total_required_installs / (11 * 30)

col1.metric("Required Total MAU (Sum)", f"{total_mau_required:,.0f}")
col2.metric(f"Peak MAU ({peak_mau_month})", f"{peak_mau_value:,.0f}")
col3.metric("Required Installs / Day", f"{required_installs_per_day:,.0f}",
            help=f"{'Forecast CSV ratio' if use_forecast_funnel else 'Master data ratio'}: {active_install_mau_ratio:.4f} installs per MAU")
col4.metric("Blended ARPU", f"IDR {arpu:,.0f}",
            help=f"{pct_monthly}% Monthly · {pct_annual}% Annual · {pct_passport}% Passport")

st.subheader("Monthly MAU Target")
fig_mau = px.line(df_model, x="Month", y="Target MAU", markers=True,
                  title="Target MAU per Month")
fig_mau.update_traces(text=df_model["Target MAU"].map(lambda v: f"{v:,.0f}"),
                      textposition="top center", mode="lines+markers+text")
fig_mau.update_layout(yaxis_title="MAU")
st.plotly_chart(fig_mau, use_container_width=True)

st.subheader("Monthly Purchasing Users")
fig_pu = px.line(df_model, x="Month", y="Purchasing Users", markers=True,
                 title="Purchasing Users per Month")
fig_pu.update_traces(text=df_model["Purchasing Users"].map(lambda v: f"{v:,.0f}"),
                     textposition="top center", mode="lines+markers+text")
fig_pu.update_layout(yaxis_title="Purchasing Users")
st.plotly_chart(fig_pu, use_container_width=True)

st.subheader("Monthly Revenue")
fig_rev = px.line(df_model, x="Month", y="Revenue (IDR)", markers=True,
                  title="Revenue per Month (IDR)")
fig_rev.update_traces(text=df_model["Revenue (IDR)"].map(lambda v: f"IDR {v/1_000_000:.1f}M"),
                      textposition="top center", mode="lines+markers+text")
fig_rev.update_layout(yaxis_title="Revenue (IDR)")
st.plotly_chart(fig_rev, use_container_width=True)

# --- MONTHLY BREAKDOWN TABLE ---
st.subheader("Monthly Breakdown")

# Derive per-product buyer counts from MPU and mix
mpu_list       = monthly_purchasing
mau_list       = monthly_maus
install_list   = [mau * active_install_mau_ratio for mau in mau_list]
register_list  = [mau * active_register_mau_ratio for mau in mau_list]

buyers_monthly  = [mpu * (pct_monthly  / 100) for mpu in mpu_list]
buyers_annual   = [mpu * (pct_annual   / 100) for mpu in mpu_list]
buyers_passport = [mpu * (pct_passport / 100) for mpu in mpu_list]

df_table = pd.DataFrame({
    "Month":              months,
    "Revenue (IDR)":      [f"IDR {v:,.0f}" for v in monthly_revenue],
    "MPU":                [f"{v:,.0f}" for v in mpu_list],
    "ARPU (IDR)":         [f"IDR {arpu:,.0f}"] * n,
    "MAU":                [f"{v:,.0f}" for v in mau_list],
    "Register":           [f"{v:,.0f}" for v in register_list],
    "Install":            [f"{v:,.0f}" for v in install_list],
    "MemberSIB Monthly":  [f"{v:,.0f}" for v in buyers_monthly],
    "MemberSIB Annual":   [f"{v:,.0f}" for v in buyers_annual],
    "Passport Persib":    [f"{v:,.0f}" for v in buyers_passport],
})
df_table = df_table.set_index("Month")
st.dataframe(df_table, use_container_width=True)

# --- P&L CHART ---
st.divider()
st.subheader("Monthly P&L & Cumulative Break-Even")

df_pl = pd.DataFrame({
    "Month":          months,
    "Revenue":        monthly_revenue,
    "Total Cost":     monthly_costs,
    "Monthly Net":    monthly_net,
    "Cumulative Net": cumulative_net,
})

fig_pl = go.Figure()
fig_pl.add_bar(x=df_pl["Month"], y=df_pl["Revenue"],
               name="Revenue", marker_color="#2196F3",
               text=[f"IDR {v/1e6:.0f}M" for v in monthly_revenue],
               textposition="outside")
fig_pl.add_bar(x=df_pl["Month"], y=df_pl["Total Cost"],
               name="Total Cost", marker_color="#F44336",
               text=[f"IDR {v/1e6:.0f}M" for v in monthly_costs],
               textposition="outside")
fig_pl.add_scatter(x=df_pl["Month"], y=df_pl["Cumulative Net"],
                   name="Cumulative Net P&L", mode="lines+markers+text",
                   text=[f"IDR {v/1e6:.0f}M" for v in cumulative_net],
                   textposition="top center",
                   line=dict(color="#4CAF50", width=2),
                   marker=dict(size=8),
                   yaxis="y2")
fig_pl.add_hline(y=0, line_dash="dash", line_color="gray", yref="y2",
                 annotation_text="Break-even line", annotation_position="bottom right")
fig_pl.update_layout(
    barmode="group",
    title="Monthly Revenue vs Cost · Cumulative Net P&L (right axis)",
    yaxis=dict(title="IDR / Month"),
    yaxis2=dict(title="Cumulative Net (IDR)", overlaying="y", side="right", showgrid=False),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
)
st.plotly_chart(fig_pl, use_container_width=True)