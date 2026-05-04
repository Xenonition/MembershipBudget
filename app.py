import streamlit as st
import pandas as pd
import plotly.express as px

# --- DATA PREPARATION ---
# Load historical master data for install-to-MAU ratio
_df_master = pd.read_csv("Persib App - Performance - Master Data.csv", thousands=",")
_df_master.columns = _df_master.columns.str.replace("\n", " ", regex=False).str.strip()
_df_master["MAU"] = pd.to_numeric(_df_master["MAU"].astype(str).str.replace(",", ""), errors="coerce")
_df_master["Total Installs"] = pd.to_numeric(_df_master["Total Installs"].astype(str).str.replace(",", ""), errors="coerce")
_df_master = _df_master.dropna(subset=["Total Installs", "MAU"])
avg_install_mau_ratio = (_df_master["Total Installs"] / _df_master["MAU"]).mean()

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
target_revenue = st.sidebar.number_input("Seasonal Revenue Target (IDR)", value=20_000_000_000, step=1_000_000_000)
arpu = st.sidebar.slider("Target ARPU (IDR)", 20000, 100000, 36822)
conversion_rate = st.sidebar.slider("MPU/MAU Conversion (%)", 0.5, 10.0, 1.69) / 100
use_seasonality = st.sidebar.toggle("Weighted Growth (Follow Historical Seasonality 2025/26)", value=True)
growth_rate = st.sidebar.slider("Season Growth Rate (%)", 0, 300, 0, step=10,
    help="Linear growth ramp applied on top of weights. 0% = flat, 100% = April gets 2× the multiplier of June.")

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

**Defaults**
> ARPU: IDR 36,822 *(avg non-ticketing ARPU, historical)*  
> Conversion: 1.69% *(avg MPU/MAU, historical)*
""")

# --- CALCULATIONS ---
# Total Revenue = Total_MAU_Sum * Conv * ARPU
# Total_MAU_Sum = Target_Rev / (Conv * ARPU)
total_mau_required = target_revenue / (conversion_rate * arpu)
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

df_model = pd.DataFrame({
    "Month": months,
    "Target MAU": monthly_maus,
    "Purchasing Users": monthly_purchasing,
    "Revenue (IDR)": monthly_revenue,
})

# --- DASHBOARD ---
col1, col2, col3 = st.columns(3)
peak_mau_idx = monthly_maus.index(max(monthly_maus))
peak_mau_month = months[peak_mau_idx]
peak_mau_value = monthly_maus[peak_mau_idx]

total_required_installs = total_mau_required * avg_install_mau_ratio
required_installs_per_day = total_required_installs / (11 * 30)

col1.metric("Required Total MAU (Sum)", f"{total_mau_required:,.0f}")
col2.metric(f"Peak MAU ({peak_mau_month})", f"{peak_mau_value:,.0f}")
col3.metric("Required Installs / Day", f"{required_installs_per_day:,.0f}",
            help=f"Based on avg historical install-to-MAU ratio of {avg_install_mau_ratio:.2f}x")

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