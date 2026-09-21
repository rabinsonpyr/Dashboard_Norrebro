

import streamlit as st

# Must be the very first Streamlit command — before importing anything
# (like config.py) that itself touches st.secrets or other Streamlit APIs.
st.set_page_config(page_title="Sales Dashboard (Tandoori Masala, Nørrebro)", layout="wide")

import io
import datetime
import logging

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

import config


PERSON_COLORS = {"Rabinson": "#FF6B35", "Sapana": "#0074D9"}
import drive_utils

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("dashboard")


def check_password() -> bool:
    if not config.APP_PASSWORD:
        st.error(
            "No APP_PASSWORD configured. Add it under this app's Settings → "
            "Secrets on Streamlit Cloud."
        )
        st.stop()

    if st.session_state.get("authenticated"):
        return True

    st.title("🔒 Sales Dashboard (Tandoori Masala, Nørrebro)")
    pwd = st.text_input("Password", type="password")
    if st.button("Enter"):
        if pwd == config.APP_PASSWORD:
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("Incorrect password.")
    return False


if not check_password():
    st.stop()

# Data loading — fetch the Excel file from Google Drive (via service account)

def fetch_all_sheets() -> dict:
    """Downloads the current workbook from Drive as a dict of {sheet_name: DataFrame}."""
    if not config.GOOGLE_DRIVE_FILE_ID:
        st.error(
            "No GOOGLE_DRIVE_FILE_ID configured. Add it under this app's "
            "Settings → Secrets on Streamlit Cloud."
        )
        st.stop()
    try:
        raw_bytes = drive_utils.download_excel_bytes(config.GOOGLE_DRIVE_FILE_ID)
        return pd.read_excel(io.BytesIO(raw_bytes), sheet_name=None)
    except Exception as e:
        st.error(
            f"Could not read the Excel file from Google Drive ({e}). Make sure "
            "the service account has access to the file and GOOGLE_DRIVE_FILE_ID "
            "is correct."
        )
        st.stop()


def save_all_sheets(sheets: dict) -> None:
    """Writes every sheet back to the same Drive file, preserving all of them."""
    out_buf = io.BytesIO()
    with pd.ExcelWriter(out_buf, engine="openpyxl") as writer:
        for sheet_name, sheet_df in sheets.items():
            sheet_df.to_excel(writer, sheet_name=sheet_name, index=False)
    out_buf.seek(0)
    drive_utils.upload_excel_bytes(config.GOOGLE_DRIVE_FILE_ID, out_buf.read())


def fetch_raw_excel() -> pd.DataFrame:
    """Downloads just the main (first) sheet, unmodified/uncleaned."""
    sheets = fetch_all_sheets()
    main_sheet_name = list(sheets.keys())[0]
    return sheets[main_sheet_name]


@st.cache_data(ttl=config.REFRESH_SECONDS, show_spinner="Fetching latest data...")
def load_data() -> pd.DataFrame:
    df = fetch_raw_excel()

    required = [
        config.COL_DATE, config.COL_SALES, config.COL_WOLT,
        config.COL_UBEREATS, config.COL_TOTAL, config.COL_TIPS,
        config.COL_PERSON, config.COL_CASH,
    ]
    missing = [c for c in required if c not in df.columns]
    if missing:
        st.error(f"Missing expected columns in the Excel file: {missing}")
        st.stop()

    df[config.COL_DATE] = pd.to_datetime(df[config.COL_DATE], errors="coerce")
    df[config.COL_PERSON] = df[config.COL_PERSON].astype(str).str.strip()

    num_cols = [config.COL_SALES, config.COL_WOLT, config.COL_UBEREATS,
                config.COL_TOTAL, config.COL_TIPS, config.COL_CASH]
    for c in num_cols:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    df = df.dropna(subset=[config.COL_DATE]).reset_index(drop=True)
    df = df.sort_values(config.COL_DATE).reset_index(drop=True)
    df["Day"] = df[config.COL_DATE].dt.day_name()
    return df


WH_COLS = ["Date", "Day", "Person", "Start Time", "End Time", "Hours Worked"]


@st.cache_data(ttl=config.REFRESH_SECONDS, show_spinner=False)
def load_working_hours() -> pd.DataFrame:
    sheets = fetch_all_sheets()
    wh = sheets.get(config.WORKING_HOURS_SHEET)
    if wh is None or wh.empty:
        return pd.DataFrame(columns=WH_COLS)
    return wh


def get_all_known_people(sales_df: pd.DataFrame) -> list:
    """Names from both the sales sheet and the working hours sheet, so a
    name typed into either form shows up as a suggestion everywhere."""
    names = set()
    if not sales_df.empty:
        names.update(sales_df[config.COL_PERSON].dropna().unique().tolist())
    wh_df = load_working_hours()
    if not wh_df.empty:
        names.update(wh_df["Person"].dropna().unique().tolist())
    return sorted(names)


df = load_data()

st.title("📊 Sales Dashboard (Tandoori Masala, Nørrebro)")

col_title, col_refresh = st.columns([5, 1])
with col_refresh:
    if st.button("🔄 Refresh now"):
        st.cache_data.clear()
        st.rerun()

st.caption(f"Data auto-refreshes at least every {config.REFRESH_SECONDS} seconds.")

# Add today's entry — writes a new row directly to the Google Drive file
with st.expander("➕ Add a day's entry", expanded=False):
    existing_people = get_all_known_people(df)

    person_choice = st.selectbox("Person", options=existing_people + ["Someone new..."], key="entry_person")
    new_person_name = ""
    if person_choice == "Someone new...":
        new_person_name = st.text_input("Enter name", key="entry_new_person_name")

    with st.form("add_entry_form", clear_on_submit=True):
        entry_date = st.date_input("Date", value=datetime.date.today())

        c1, c2, c3 = st.columns(3)
        tillty_val = c1.number_input(f"{config.COL_SALES} ({config.CURRENCY})", min_value=0.0, step=1.0)
        wolt_val = c2.number_input(f"{config.COL_WOLT} ({config.CURRENCY})", min_value=0.0, step=1.0)
        ubereats_val = c3.number_input(f"{config.COL_UBEREATS} ({config.CURRENCY})", min_value=0.0, step=1.0)

        c4, c5 = st.columns(2)
        tips_val = c4.number_input(f"{config.COL_TIPS} ({config.CURRENCY})", min_value=0.0, step=1.0)
        cash_val = c5.number_input(f"{config.COL_CASH} ({config.CURRENCY})", min_value=0.0, step=1.0)

        computed_total = tillty_val + wolt_val + ubereats_val
        st.caption(f"{config.COL_TOTAL} (auto-calculated): **{computed_total:,.0f} {config.CURRENCY}**")

        submitted = st.form_submit_button("Save entry")

        if submitted:
            final_person = new_person_name.strip() if person_choice == "Someone new..." else person_choice
            if not final_person:
                st.error("Please enter a person's name.")
            else:
                sheets = fetch_all_sheets()
                main_sheet_name = list(sheets.keys())[0]
                new_row = {
                    config.COL_DATE: pd.Timestamp(entry_date),
                    config.COL_SALES: tillty_val,
                    config.COL_WOLT: wolt_val,
                    config.COL_UBEREATS: ubereats_val,
                    config.COL_TOTAL: computed_total,
                    config.COL_TIPS: tips_val,
                    config.COL_PERSON: final_person,
                    config.COL_CASH: cash_val,
                }
                sheets[main_sheet_name] = pd.concat(
                    [sheets[main_sheet_name], pd.DataFrame([new_row])], ignore_index=True
                )
                save_all_sheets(sheets)

                st.cache_data.clear()
                st.success(f"Saved entry for {final_person} on {entry_date}.")
                st.rerun()

# Add staff working hours — writes to a separate "Working Hours" sheet
with st.expander("🕐 Add staff working hours", expanded=False):
    wh_existing_people = get_all_known_people(df)

    wh_person_choice = st.selectbox("Person", options=wh_existing_people + ["Someone new..."], key="wh_person")
    wh_new_name = ""
    if wh_person_choice == "Someone new...":
        wh_new_name = st.text_input("Enter name", key="wh_new_name")

    with st.form("add_hours_form", clear_on_submit=True):
        wh_date = st.date_input("Date", value=datetime.date.today(), key="wh_date")

        c1, c2 = st.columns(2)
        start_time = c1.time_input("Start time", key="wh_start")
        end_time = c2.time_input("End time", key="wh_end")

        wh_submitted = st.form_submit_button("Save working hours")

        if wh_submitted:
            final_wh_person = wh_new_name.strip() if wh_person_choice == "Someone new..." else wh_person_choice
            if not final_wh_person:
                st.error("Please enter a person's name.")
            else:
                start_dt = datetime.datetime.combine(wh_date, start_time)
                end_dt = datetime.datetime.combine(wh_date, end_time)
                hours_worked = (end_dt - start_dt).total_seconds() / 3600
                if hours_worked < 0:  # shift crosses midnight
                    hours_worked += 24

                sheets = fetch_all_sheets()
                wh_df = sheets.get(config.WORKING_HOURS_SHEET)
                if wh_df is None or wh_df.empty:
                    wh_df = pd.DataFrame(columns=WH_COLS)

                new_wh_row = {
                    "Date": pd.Timestamp(wh_date),
                    "Day": wh_date.strftime("%A"),
                    "Person": final_wh_person,
                    "Start Time": start_time.strftime("%H:%M"),
                    "End Time": end_time.strftime("%H:%M"),
                    "Hours Worked": round(hours_worked, 2),
                }
                wh_df = pd.concat([wh_df, pd.DataFrame([new_wh_row])], ignore_index=True)
                sheets[config.WORKING_HOURS_SHEET] = wh_df
                save_all_sheets(sheets)

                st.cache_data.clear()
                st.success(f"Saved {hours_worked:.1f}h for {final_wh_person} on {wh_date}.")
                st.rerun()

with st.expander("🔍 Debug info (click if the dashboard looks empty)"):
    st.write(f"Rows loaded: **{len(df)}**")
    if not df.empty:
        st.write(f"Date range: **{df[config.COL_DATE].min().date()}** to **{df[config.COL_DATE].max().date()}**")
        st.write("Unique values in Person column:", df[config.COL_PERSON].dropna().unique().tolist())

# ---- Sidebar filters ----
st.sidebar.header("Filters")
min_date, max_date = df[config.COL_DATE].min().date(), df[config.COL_DATE].max().date()

if min_date == max_date:
    st.sidebar.info(f"Only one date in the data so far: {min_date}")
    date_range = (min_date, max_date)
else:
    date_range = st.sidebar.date_input(
        "Date range", value=(min_date, max_date), min_value=min_date, max_value=max_date
    )
    if not isinstance(date_range, (tuple, list)) or len(date_range) != 2:
        date_range = (min_date, max_date)

people = sorted(df[config.COL_PERSON].dropna().unique().tolist())
if st.sidebar.button("Reset filters"):
    st.rerun()
selected_people = st.sidebar.multiselect("Person", options=people, default=people)

start, end = pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1])
df = df[(df[config.COL_DATE].dt.normalize() >= start) & (df[config.COL_DATE].dt.normalize() <= end)]
if selected_people:
    df = df[df[config.COL_PERSON].isin(selected_people)]

if df.empty:
    st.warning(
        "No data for the selected filters. Try clicking **Reset filters** in the "
        "sidebar, or expand the Debug info box above."
    )
    st.stop()

# KPI row 
total_revenue = df[config.COL_TOTAL].sum()
total_tips = df[config.COL_TIPS].sum()
total_cash = df[config.COL_CASH].sum()
days_recorded = df[config.COL_DATE].nunique()
avg_daily_revenue = df[config.COL_TOTAL].mean()

kpi_cards = [
    ("💰", "Total Revenue", f"{total_revenue:,.0f} {config.CURRENCY}", "#667eea", "#764ba2"),
    ("💵", "Total Tips", f"{total_tips:,.0f} {config.CURRENCY}", "#f2994a", "#e67e22"),
    ("🪙", "Total Cash Held", f"{total_cash:,.0f} {config.CURRENCY}", "#11998e", "#38ef7d"),
    ("📅", "Days Recorded", f"{days_recorded}", "#396afc", "#2948ff"),
    ("📈", "Avg Daily Revenue", f"{avg_daily_revenue:,.0f} {config.CURRENCY}", "#ee0979", "#ff6a00"),
]

cards_html = "".join(
    f'<div style="flex:1; min-width:170px; background:linear-gradient(135deg,{c1},{c2}); '
    f'color:white; border-radius:16px; padding:22px 12px; text-align:center; '
    f'box-shadow:0 4px 14px rgba(0,0,0,0.15);">'
    f'<div style="font-size:30px; line-height:1;">{icon}</div>'
    f'<div style="font-size:24px; font-weight:700; margin-top:8px; white-space:nowrap;">{value}</div>'
    f'<div style="font-size:13px; opacity:0.9; margin-top:6px;">{label}</div>'
    f'</div>'
    for icon, label, value, c1, c2 in kpi_cards
)

st.markdown(
    f'<div style="display:flex; gap:14px; flex-wrap:wrap; justify-content:center; margin-bottom:8px;">{cards_html}</div>',
    unsafe_allow_html=True,
)

st.divider()

# Revenue trend over time
st.subheader("Revenue Over Time")

CHANNEL_COLORS = {
    config.COL_SALES: "#1f77b4",     # blue
    config.COL_WOLT: "#F5A623",      # orange
    config.COL_UBEREATS: "#06C167",  # green
}

daily_channel = (
    df.groupby(config.COL_DATE)[[config.COL_SALES, config.COL_WOLT, config.COL_UBEREATS]]
    .sum()
    .reset_index()
)
daily_channel["Computed Total"] = (
    daily_channel[config.COL_SALES] + daily_channel[config.COL_WOLT] + daily_channel[config.COL_UBEREATS]
)
melted = daily_channel.melt(
    id_vars=[config.COL_DATE],
    value_vars=[config.COL_SALES, config.COL_WOLT, config.COL_UBEREATS],
    var_name="Channel", value_name="Revenue",
)

fig1 = px.area(
    melted, x=config.COL_DATE, y="Revenue", color="Channel",
    color_discrete_map=CHANNEL_COLORS,
    labels={config.COL_DATE: "Date", "Revenue": f"Revenue ({config.CURRENCY})"},
)
fig1.update_xaxes(tickformat="%Y-%m-%d<br>(%a)", dtick="D1", hoverformat="%Y-%m-%d (%A)")
fig1.update_traces(
    mode="lines+markers",
    marker=dict(size=6),
    hovertemplate=f"%{{fullData.name}}: %{{y:,.0f}} {config.CURRENCY}<extra></extra>",
)
# Hidden trace purely so "Total" shows up in the combined hover tooltip
fig1.add_trace(go.Scatter(
    x=daily_channel[config.COL_DATE],
    y=daily_channel["Computed Total"],
    mode="lines",
    line=dict(width=0),
    opacity=0,
    showlegend=False,
    hovertemplate=f"💰 <b>Total Sales</b>: %{{y:,.0f}} {config.CURRENCY}<extra></extra>",
))
fig1.update_layout(hovermode="x unified")
st.plotly_chart(fig1, use_container_width=True)

col_a, col_b, col_c = st.columns(3)

with col_a:
    st.subheader("Revenue Share by Channel")
    totals = {
        config.COL_SALES: df[config.COL_SALES].sum(),
        config.COL_WOLT: df[config.COL_WOLT].sum(),
        config.COL_UBEREATS: df[config.COL_UBEREATS].sum(),
    }
    fig2 = px.pie(
        names=list(totals.keys()), values=list(totals.values()), hole=0.4,
        color=list(totals.keys()),
        color_discrete_map=CHANNEL_COLORS,
    )
    fig2.update_traces(hovertemplate=f"%{{label}}: %{{value:,.0f}} {config.CURRENCY} (%{{percent}})<extra></extra>")
    st.plotly_chart(fig2, use_container_width=True)

with col_b:
    st.subheader("Tips by Person")
    tips_by_person = (
        df.groupby(config.COL_PERSON)[config.COL_TIPS]
        .sum()
        .sort_values(ascending=False)
        .reset_index()
    )
    fig3 = px.bar(
        tips_by_person, x=config.COL_PERSON, y=config.COL_TIPS, color=config.COL_PERSON,
        color_discrete_map=PERSON_COLORS,
        labels={config.COL_PERSON: "Person", config.COL_TIPS: f"Tips ({config.CURRENCY})"},
        text=config.COL_TIPS,
    )
    fig3.update_traces(texttemplate=f"%{{y:,.0f}} {config.CURRENCY}", textposition="outside")
    fig3.update_layout(showlegend=False)
    st.plotly_chart(fig3, use_container_width=True)

with col_c:
    st.subheader("Cash Held by Person")
    cash_by_person = (
        df.groupby(config.COL_PERSON)[config.COL_CASH]
        .sum()
        .sort_values(ascending=False)
        .reset_index()
    )
    fig5 = px.bar(
        cash_by_person, x=config.COL_PERSON, y=config.COL_CASH, color=config.COL_PERSON,
        color_discrete_map=PERSON_COLORS,
        labels={config.COL_PERSON: "Person", config.COL_CASH: f"Cash ({config.CURRENCY})"},
        text=config.COL_CASH,
    )
    fig5.update_traces(texttemplate=f"%{{y:,.0f}} {config.CURRENCY}", textposition="outside")
    fig5.update_layout(showlegend=False)
    st.plotly_chart(fig5, use_container_width=True)

st.subheader("Total Sales per Day")

ts_min_date = daily_channel[config.COL_DATE].min().date()
ts_max_date = daily_channel[config.COL_DATE].max().date()

if ts_min_date == ts_max_date:
    ts_range = (ts_min_date, ts_max_date)
    st.caption(f"Only one date available: {ts_min_date}")
else:
    ts_range = st.date_input(
        "Select a date or date range for this chart",
        value=(ts_min_date, ts_max_date),
        min_value=ts_min_date, max_value=ts_max_date,
        key="ts_range",
    )
    if not isinstance(ts_range, (tuple, list)):
        ts_range = (ts_range, ts_range)
    elif len(ts_range) == 1:
        ts_range = (ts_range[0], ts_range[0])

ts_start, ts_end = pd.to_datetime(ts_range[0]), pd.to_datetime(ts_range[1])
ts_daily_channel = daily_channel[
    (daily_channel[config.COL_DATE] >= ts_start) & (daily_channel[config.COL_DATE] <= ts_end)
]
ts_melted = melted[(melted[config.COL_DATE] >= ts_start) & (melted[config.COL_DATE] <= ts_end)]

if ts_melted.empty:
    st.info("No data for the selected date(s).")
else:
    fig4 = px.bar(
        ts_melted, x=config.COL_DATE, y="Revenue", color="Channel",
        color_discrete_map=CHANNEL_COLORS,
        labels={config.COL_DATE: "Date", "Revenue": f"Revenue ({config.CURRENCY})"},
        barmode="stack",
    )
    fig4.update_xaxes(tickformat="%Y-%m-%d<br>(%a)", dtick="D1", hoverformat="%Y-%m-%d (%A)")
    fig4.update_traces(hovertemplate=f"%{{fullData.name}}: %{{y:,.0f}} {config.CURRENCY}<extra></extra>")

    # Hidden trace purely so "Total Sales" shows up in the combined hover tooltip
    fig4.add_trace(go.Scatter(
        x=ts_daily_channel[config.COL_DATE],
        y=ts_daily_channel["Computed Total"],
        mode="lines",
        line=dict(width=0),
        opacity=0,
        showlegend=False,
        hovertemplate=f"💰 <b>Total Sales</b>: %{{y:,.0f}} {config.CURRENCY}<extra></extra>",
    ))
    fig4.update_layout(hovermode="x unified")
    st.plotly_chart(fig4, use_container_width=True)

st.subheader("Staff Working Hours")
wh_preview = load_working_hours()
if wh_preview.empty:
    st.info("No working hours recorded yet. Add some using the form above.")
else:
    wh_preview = wh_preview.copy()
    wh_preview["Date"] = pd.to_datetime(wh_preview["Date"])

    tab_by_date, tab_by_person = st.tabs(["📅 By Date", "🧑 By Person"])

    with tab_by_date:
        wh_dates = sorted(wh_preview["Date"].dt.date.unique(), reverse=True)
        picked_date = st.selectbox("View shifts for date", options=wh_dates, key="wh_view_date")
        day_rows = wh_preview[wh_preview["Date"].dt.date == picked_date]

        if day_rows.empty:
            st.info("No working hours recorded for this date yet.")
        else:
            total_hours_that_day = day_rows["Hours Worked"].sum()
            st.metric("Total Hours Worked", f"{total_hours_that_day:.1f} h")

            gantt_rows = []
            for _, r in day_rows.iterrows():
                start_dt = datetime.datetime.combine(
                    picked_date, datetime.datetime.strptime(r["Start Time"], "%H:%M").time()
                )
                end_dt = datetime.datetime.combine(
                    picked_date, datetime.datetime.strptime(r["End Time"], "%H:%M").time()
                )
                if end_dt <= start_dt:  # shift crosses midnight
                    end_dt += datetime.timedelta(days=1)
                gantt_rows.append({
                    "Person": r["Person"],
                    "Start": start_dt,
                    "End": end_dt,
                    "Shift": f"{r['Start Time']} – {r['End Time']} ({r['Hours Worked']:.1f}h)",
                })
            gantt_df = pd.DataFrame(gantt_rows)

            fig_gantt = px.timeline(
                gantt_df, x_start="Start", x_end="End", y="Person", color="Person",
                color_discrete_map=PERSON_COLORS, text="Shift",
            )
            fig_gantt.update_yaxes(autorange="reversed", title=None)
            fig_gantt.update_xaxes(tickformat="%H:%M", title="Time")
            fig_gantt.update_traces(textposition="inside", insidetextanchor="middle")
            fig_gantt.update_layout(showlegend=False)
            st.plotly_chart(fig_gantt, use_container_width=True)

    with tab_by_person:
        wh_people = sorted(wh_preview["Person"].dropna().unique().tolist())
        picked_person = st.selectbox("View hours for", options=wh_people, key="wh_view_person")
        person_rows = wh_preview[wh_preview["Person"] == picked_person].copy()

        if person_rows.empty:
            st.info("No working hours recorded for this person yet.")
        else:
            person_rows = person_rows.sort_values("Date", ascending=False)
            total_hours_person = person_rows["Hours Worked"].sum()
            shifts_count = len(person_rows)

            m1, m2 = st.columns(2)
            m1.metric("Total Hours Worked", f"{total_hours_person:.1f} h")
            m2.metric("Shifts Recorded", f"{shifts_count}")

            fig_person = px.bar(
                person_rows.sort_values("Date"), x="Date", y="Hours Worked",
                color_discrete_sequence=[PERSON_COLORS.get(picked_person, "#636EFA")],
                labels={"Date": "Date", "Hours Worked": "Hours"},
            )
            fig_person.update_xaxes(tickformat="%Y-%m-%d<br>(%a)", dtick="D1")
            fig_person.update_traces(
                hovertemplate="%{x}<br>%{y:.1f} h<extra></extra>",
                text=person_rows.sort_values("Date")["Hours Worked"].map(lambda h: f"{h:.1f}h"),
                textposition="outside",
            )
            st.plotly_chart(fig_person, use_container_width=True)

st.subheader("Raw Data")
display_cols = [config.COL_DATE, "Day", config.COL_PERSON, config.COL_SALES,
                 config.COL_WOLT, config.COL_UBEREATS, config.COL_TOTAL,
                 config.COL_TIPS, config.COL_CASH]
display_cols = [c for c in display_cols if c in df.columns]
money_cols = [c for c in [config.COL_SALES, config.COL_WOLT, config.COL_UBEREATS,
                          config.COL_TOTAL, config.COL_TIPS, config.COL_CASH] if c in display_cols]
table_df = df[display_cols].sort_values(config.COL_DATE, ascending=False).copy()
table_df[config.COL_DATE] = table_df[config.COL_DATE].dt.strftime("%Y-%m-%d")

show_all_rows = st.checkbox("Show all rows", value=False)
rows_to_show = table_df if show_all_rows else table_df.head(5)

st.dataframe(
    rows_to_show.style.format({c: f"{{:,.0f}} {config.CURRENCY}" for c in money_cols}),
    use_container_width=True,
    hide_index=True,
)
if not show_all_rows and len(table_df) > 5:
    st.caption(f"Showing 5 most recent of {len(table_df)} rows. Check the box above to see all.")
