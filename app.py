"""DemandRange app. Start it with:  streamlit run app.py"""
import json

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

from demandrange.config import (FEATURE_LIMITS, PLAIN, REPORT_DIR,
                                SAMPLE_DATA_PATH)
from demandrange.data import load_sites_csv
from demandrange.finance import Assumptions
from demandrange.forecast import forecast_site
from demandrange.service import get_model as _get_model, model_info

st.set_page_config(page_title="DemandRange", page_icon="⚡", layout="wide")

PRESETS = {
    "Typical farming village": dict(households=400, business_per_100=8.0, night_light=0.4,
                                    dist_to_grid_km=30.0, market=False, schools_clinics=1,
                                    energy_spend_usd=9.0),
    "Market town": dict(households=1200, business_per_100=22.0, night_light=1.4,
                        dist_to_grid_km=12.0, market=True, schools_clinics=4,
                        energy_spend_usd=14.0),
    "Remote hamlet": dict(households=120, business_per_100=2.0, night_light=0.1,
                          dist_to_grid_km=60.0, market=False, schools_clinics=0,
                          energy_spend_usd=7.0),
}


@st.cache_resource(show_spinner="Preparing the model (first run only)...")
def get_model():
    return _get_model()


def apply_preset():
    p = PRESETS[st.session_state["preset"]]
    for k, v in p.items():
        st.session_state[k] = v


model = get_model()
for k, v in PRESETS["Typical farming village"].items():
    st.session_state.setdefault(k, v)

# ---------- Sidebar: describe the village ----------
with st.sidebar:
    st.header("Describe the village")
    st.selectbox("Start from an example", list(PRESETS), key="preset", on_change=apply_preset)
    name = st.text_input("Village name", "Example village")
    lat = st.number_input("Latitude (for the map)", value=9.07, format="%.4f")
    lon = st.number_input("Longitude (for the map)", value=7.40, format="%.4f")
    lim = FEATURE_LIMITS
    households = st.slider("Households", lim["households"][0], lim["households"][1], key="households")
    business = st.slider("Businesses per 100 households", lim["business_per_100"][0],
                         lim["business_per_100"][1], key="business_per_100")
    night = st.slider("Night-time light level", lim["night_light"][0], lim["night_light"][1],
                      key="night_light", help="0 = dark. Comes from satellite data (VIIRS).")
    dist = st.slider("Distance to the grid (km)", lim["dist_to_grid_km"][0],
                     lim["dist_to_grid_km"][1], key="dist_to_grid_km")
    market = st.checkbox("A market within 5 km", key="market")
    schools = st.slider("Schools and clinics nearby", lim["schools_clinics"][0],
                        lim["schools_clinics"][1], key="schools_clinics")
    spend = st.slider("Current monthly energy spend per household ($)",
                      lim["energy_spend_usd"][0], lim["energy_spend_usd"][1],
                      key="energy_spend_usd", help="Candles, kerosene, batteries, diesel.")
    sun = st.slider("Sunshine in the poorest month (kWh per m2 per day)", 2.0, 7.0, 4.5, 0.1,
                    help="Look it up for your village at power.larc.nasa.gov (free), or in the API.")
    with st.expander("Loan and tariff assumptions (placeholders)"):
        customers = st.number_input("Customers to connect", 20, 5000, 400, step=20)
        capex = st.number_input("Build cost per customer ($)", 100, 3000, 600, step=50)
        opex = st.number_input("Running cost per customer per year ($)", 5, 200, 25, step=5)
        tariff = st.number_input("Tariff ($ per kWh)", 0.10, 1.50, 0.45, step=0.05)
        debt_share = st.slider("Share paid by loan", 0.0, 1.0, 0.7, step=0.05)
        rate = st.slider("Interest rate", 0.02, 0.25, 0.10, step=0.01)
        tenor = st.slider("Loan length (years)", 3, 20, 10)
        dscr = st.slider("Safety margin lenders ask for (x)", 1.0, 2.0, 1.2, step=0.1)

site = dict(households=households, business_per_100=business, night_light=night,
            dist_to_grid_km=dist, market_within_5km=int(market),
            schools_clinics=schools, energy_spend_usd=spend)
assump = Assumptions(customers, capex, opex, tariff, debt_share, rate, tenor, dscr)
solar = {"annual_kwh_m2_day": sun, "worst_month_kwh_m2_day": sun, "worst_month": "poorest month"}
out = forecast_site(model, site, name=name, assumptions=assump, solar=solar)
curve, avg, fin, prod = out["curve"], out["years_avg"], out["finance"], out["productive_use"]

# ---------- Main page ----------
st.title("DemandRange")
st.write("How much power will each customer use? A range you can defend, "
         "before anyone builds the mini-grid.")
_info = model_info(model)
if _info["warning"]:
    st.warning(_info["warning"])

tab1, tab2, tab3, tab4 = st.tabs(["Forecast", "Why this range", "Lender memo", "How well it works"])

with tab1:
    c1, c2, c3 = st.columns(3)
    c1.metric("Middle case, years 1 to 3", f"{avg['p50']:.1f} kWh")
    c2.metric("Low to high case", f"{avg['p10']:.1f} to {avg['p90']:.1f} kWh")
    c3.metric("Chance it covers the loan", f"{fin['prob_cover_debt']*100:.0f}%",
              help=f"Needs {fin['breakeven_kwh']:.1f} kWh per customer per month.")
    fig, ax = plt.subplots(figsize=(7, 3.6), dpi=130)
    ax.fill_between(curve["year"], curve["p10"], curve["p90"], color="#9CC9C6", alpha=0.7,
                    label="Low to high case")
    ax.plot(curve["year"], curve["p50"], color="#0B7A75", lw=2.4, marker="o", label="Middle case")
    ax.axhline(fin["breakeven_kwh"], color="#14213D", ls="--", lw=1.2,
               label=f"Needed to cover the loan ({fin['breakeven_kwh']:.1f})")
    ax.set_xlabel("Years after connection")
    ax.set_ylabel("kWh per customer per month")
    ax.set_xticks(curve["year"])
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(frameon=False, fontsize=8)
    fig.tight_layout()
    st.pyplot(fig)
    plt.close(fig)
    sz = out["sizing"]
    st.subheader("What system the forecast implies")
    z1, z2, z3 = st.columns(3)
    for col, key, lab in ((z1, "low_case", "Low case"), (z2, "middle_case", "Middle case"), (z3, "high_case", "High case")):
        col.metric(lab, f"{sz['sizes'][key]['pv_kwp']:.0f} kW solar", f"{sz['sizes'][key]['battery_kwh']:.0f} kWh battery", delta_color="off")
    cw = sz["cost_of_wrong"]
    st.caption(f"Cost of being wrong, using the ESMAP benchmark of about USD {cw['capex_per_person_usd']:.0f} per person: "
               f"each 10% sizing error here is about USD {cw['capex_per_10pct_sizing_error_usd']:,.0f}.")
    left, right = st.columns([1, 1])
    with left:
        st.subheader("Daytime businesses")
        st.write(f"Estimated load factor **{prod['load_factor']*100:.0f}%**. "
                 f"Each kWh costs about **{prod['cost_saving_vs_household_only_pct']:.0f}% less** "
                 "than on a households-only system.")
        for a in prod["anchors"]:
            st.write("• " + a)
    with right:
        st.subheader("Location")
        st.map(pd.DataFrame({"lat": [lat], "lon": [lon]}), zoom=8)

with tab2:
    st.write("Each row changes one input and shows how the middle case moves "
             "(kWh per customer per month, year 2).")
    d = out["drivers"].copy()
    d["change_kwh"] = d["change_kwh"].round(2)
    st.dataframe(d.rename(columns={"what_changes": "If this changes", "change_kwh": "Middle case moves by"}),
                 hide_index=True, use_container_width=True)
    st.subheader("What the model relies on overall")
    if SAMPLE_DATA_PATH.exists():
        imp = model.feature_importance(load_sites_csv(SAMPLE_DATA_PATH))
        imp.index = [PLAIN[i] for i in imp.index]
        st.bar_chart(imp)

with tab3:
    st.markdown(out["memo"])
    st.download_button("Download memo", out["memo"], file_name=f"{name.replace(' ', '_')}_memo.md",
                       mime="text/markdown")

with tab4:
    vpath = REPORT_DIR / "validation.json"
    if vpath.exists():
        res = json.loads(vpath.read_text())
        s, r, g = res["held_out_sites"], res["held_out_regions"], res["growth_year0_to_year3_pct"]
        r = r if "mae_kwh" in r else {"mae_kwh": "n/a", "improvement_vs_baseline_pct": "n/a"}
        a, b, c = st.columns(3)
        a.metric("Typical error, unseen villages", f"{s['mae_kwh']} kWh",
                 f"{s['improvement_vs_baseline_pct']}% better than guessing the average")
        b.metric("Typical error, unseen region", f"{r['mae_kwh']} kWh",
                 f"{r['improvement_vs_baseline_pct']}% better than guessing the average")
        c.metric("Range hit rate (aim: 80%)", f"{s['range_coverage_pct']}%")
        st.write(f"Growth from year 0 to year 3: actual {g['actual']}%, predicted {g['predicted']}%.")
        st.caption(res["data_note"])
        png = REPORT_DIR / "validation.png"
        if png.exists():
            st.image(str(png))
    else:
        st.write("Run `python run_pipeline.py` to create the validation results.")
