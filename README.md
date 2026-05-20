# persib-revenue-simulator

Streamlit revenue modeling tool for the Persib App membership product. Models two scenarios interactively:

- **Revenue Target → MAU**: given an IDR seasonal revenue goal, back-calculates the required Monthly Active Users.
- **MAU Target → Revenue**: given a total season MAU, projects resulting revenue, costs, and net P&L.

Supports configurable product mix (MemberSIB Monthly/Annual, Passport Persib), conversion rates, historical seasonality weighting, growth ramps, and cost toggles (tech tier, TADA reward platform).

## Setup

```bash
pip install -e .
```

## Running

```bash
streamlit run app.py
```

## Data

Reference CSV files live in `data/`:

| File | Description |
|------|-------------|
| `performance_master_data.csv` | Historical monthly installs and MAU — used to derive install-to-MAU ratio |
| `performance_to_target.csv` | Season targets for reference |
| `forecast_cost.csv` | Forecast cost breakdown (ARPU scenarios, fixed/variable costs) |
| `revenue_model_scenarios.csv` | Saved scenario snapshots |
