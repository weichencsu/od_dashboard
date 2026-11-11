import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import sqlite3
import os
import shutil
import re


# ============================================================
# CONFIGURATION
# ============================================================

DB_NAME = "fuller_mill_data.db"
TEMP_DB_NAME = "fuller_mill_data_temp.db"

# Add future Fuller Excel files here.
# The label is used as the dataset name in the charts.
FULLER_FILES = {
    "Fuller Mill operating data 12 Sep 2026.xlsx": {
        "sheet_name": "Sheet1",
        "label": "SEP26"
    }
}

AGG_OPTIONS = ["per Hour", "per Shift", "per Day", "per Week", "per Month"]

COLORS = [
    "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
    "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf"
]

REQUIRED_COLS = [
    "TIME",
    "RPM",
    "FEED",
    "PEBBLE",
    "WATER",
    "SUMP",
    "POWER",
    "BEARING_PRESSURE",
    "SILICA",
    "FEEDMIN",
    "FEEDMAX",
    "CRUSHER_POWER"
]

OPTIONAL_COLS = [
    "LOAD",
    "LOADSETTING",
    "DENSITY"
]

SOURCE_COLS = [col for col in REQUIRED_COLS + OPTIONAL_COLS if col != "TIME"]
# ============================================================
# COLUMN MAPPING HELPERS
# ============================================================

def _norm(s):
    return re.sub(r"[^a-z0-9]+", "", str(s).lower())


KNOWN_COLUMN_MAP = {
    _norm("Timestamp"): "TIME",
    _norm("Time"): "TIME",
    _norm("Mill Speed RPM"): "RPM",
    _norm("Mill fresh feed rate tph"): "FEED",
    _norm("Pebble rate tph"): "PEBBLE",
    _norm("Mill feed water m3/h"): "WATER",
    _norm("Mill discharge sump water"): "SUMP",
    _norm("Mill power kW"): "POWER",
    _norm("Bearing Pressure kPa"): "BEARING_PRESSURE",
    _norm("Silica"): "SILICA",
    _norm("FeedMin"): "FEEDMIN",
    _norm("FeedMax"): "FEEDMAX",
    _norm("Crusher Power kW"): "CRUSHER_POWER",

    # Optional Svedala-style columns, if they appear in future Fuller files
    _norm("Mill load t"): "LOAD",
    _norm("Density"): "DENSITY",
    _norm("MillLoadSP"): "LOADSETTING",
    _norm("Load Setting"): "LOADSETTING",
}

FUZZY_RULES = [
    ("TIME", ["timestamp", "time", "date"], []),
    ("RPM", ["millspeedrpm", "speedrpm", "rpm", "millspeed"], []),
    ("PEBBLE", ["pebblerratetph", "pebblerrate", "pebble"], []),

    ("WATER", ["millfeedwaterm3h", "feedwaterm3h", "feedwater", "water"], ["sump", "discharge"]),
    ("SUMP", ["milldischargesumpwater", "dischargesumpwater", "sumpwater", "sump"], []),

    ("BEARING_PRESSURE", ["bearingpressurekpa", "bearingpressure", "bearing"], []),
    ("CRUSHER_POWER", ["crusherpowerkw", "crusherpower", "crusher"], []),

    ("POWER", ["millpowerkw", "millpower", "powerkw", "power"], ["crusher", "bear"]),

    ("FEEDMIN", ["feedmin", "minfeed", "minimumfeed"], []),
    ("FEEDMAX", ["feedmax", "maxfeed", "maximumfeed"], []),

    ("FEED", ["millfreshfeedratetph", "freshfeedratetph", "freshfeed", "feedratetph", "feed"], ["water", "min", "max"]),

    ("LOAD", ["millloadt", "millload", "loadt", "load"], ["setting", "sp"]),
    ("LOADSETTING", ["millloadsp", "loadsp", "loadsetting"], []),
    ("DENSITY", ["density"], []),
    ("SILICA", ["silica"], []),
]


def standardize_columns(df):
    """
    Maps raw Excel column names to the standard internal names used by this page.
    """
    rename_map = {}
    used_targets = set()

    for col in df.columns:
        norm_col = _norm(col)

        target = KNOWN_COLUMN_MAP.get(norm_col)

        if target is None:
            for candidate, includes, excludes in FUZZY_RULES:
                if candidate in used_targets:
                    continue

                if any(ex in norm_col for ex in excludes):
                    continue

                if any(inc in norm_col for inc in includes):
                    target = candidate
                    break

        if target and target not in used_targets:
            rename_map[col] = target
            used_targets.add(target)

    df = df.rename(columns=rename_map)

    for col in REQUIRED_COLS + OPTIONAL_COLS:
        if col not in df.columns:
            df[col] = np.nan

    return df[REQUIRED_COLS + OPTIONAL_COLS]


# ============================================================
# DATA PREPARATION
# ============================================================

def ensure_derived_columns(df):
    """
    Adds derived fields used by the charts:
    - CUMFEED
    - WATER_FEED_RATIO
    - MILL_AVAILABILITY

    Important:
    This function must NOT create a regular column called TIME.
    TIME is normally used as the DataFrame index.
    """
    for col in SOURCE_COLS:
        if col not in df.columns:
            df[col] = np.nan

    if "CUMFEED" not in df.columns:
        df["CUMFEED"] = df["FEED"].cumsum()

    if "WATER_FEED_RATIO" not in df.columns:
        df["WATER_FEED_RATIO"] = df["WATER"] / df["FEED"].replace(0, np.nan)

    if "MILL_AVAILABILITY" not in df.columns:
        if "RPM" in df.columns:
            running = (df["RPM"].fillna(0) >= 5).astype(float)
            df["MILL_AVAILABILITY"] = 100.0 * running.cumsum() / np.arange(1, len(df) + 1)
        else:
            df["MILL_AVAILABILITY"] = np.nan

    return df


def prepare_timeseries(df):
    """
    Cleans, resamples to hourly data, and creates derived columns.
    """
    df = df.copy()

    if "TIME" not in df.columns:
        df["TIME"] = np.nan

    df["TIME"] = pd.to_datetime(df["TIME"], errors="coerce")

    for col in REQUIRED_COLS + OPTIONAL_COLS:
        if col == "TIME":
            continue

        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        else:
            df[col] = np.nan

    df = df.dropna(subset=["TIME"])
    df = df[df["TIME"].dt.year > 1970]
    df = df.sort_values("TIME")
    df = df.set_index("TIME")
    df = df[~df.index.duplicated(keep="first")]

    if df.empty:
        df = pd.DataFrame(index=pd.DatetimeIndex([], name="TIME"))
    else:
        df = df.resample("h").mean(numeric_only=True)

    df = ensure_derived_columns(df)

    # Extra safety: TIME should be the index, not also a column.
    if df.index.name == "TIME" and "TIME" in df.columns:
        df = df.drop(columns=["TIME"])

    return df


def read_fuller_excel(file_path, sheet_name):
    """
    Reads a Fuller Excel file and tries a few common header/layout formats.
    """
    attempts = [
        {"header": 0, "skiprows": 0, "positional": False},
        {"header": 1, "skiprows": 0, "positional": False},
        {"header": 0, "skiprows": 1, "positional": False},
        {"header": None, "skiprows": 1, "positional": True},
        {"header": None, "skiprows": 0, "positional": True},
    ]

    last_error = None

    for attempt in attempts:
        try:
            if attempt["positional"]:
                df_raw = pd.read_excel(
                    file_path,
                    sheet_name=sheet_name,
                    header=None,
                    skiprows=attempt["skiprows"]
                )

                if df_raw.empty:
                    continue

                if df_raw.shape[1] >= len(REQUIRED_COLS):
                    df_raw.columns = REQUIRED_COLS + [
                        f"EXTRA_{i}" for i in range(len(REQUIRED_COLS), df_raw.shape[1])
                    ]
                else:
                    df_raw.columns = REQUIRED_COLS[:df_raw.shape[1]]
            else:
                df_raw = pd.read_excel(
                    file_path,
                    sheet_name=sheet_name,
                    header=attempt["header"],
                    skiprows=attempt["skiprows"]
                )

            df_std = standardize_columns(df_raw)

            if "TIME" not in df_std.columns:
                continue

            time_test = pd.to_datetime(df_std["TIME"], errors="coerce")
            if time_test.notna().sum() == 0:
                continue

            return prepare_timeseries(df_std)

        except Exception as e:
            last_error = e

    raise ValueError(f"Could not parse Fuller Excel file '{file_path}'. Last error: {last_error}")

def reset_index_for_db(df):
    """
    Safely converts the TIME-indexed DataFrame into a flat DataFrame
    for SQLite storage.

    This avoids the error:
    "cannot insert TIME, already exists"
    """
    df = df.copy()

    # If TIME is the index, remove any accidental TIME column first.
    if df.index.name == "TIME":
        if "TIME" in df.columns:
            df = df.drop(columns=["TIME"])
        df = df.reset_index()

    # If TIME is already a normal column, do not reset the index into another TIME column.
    elif "TIME" in df.columns:
        df = df.reset_index(drop=True)

    # Fallback: if there is no TIME column, promote the index.
    else:
        df = df.reset_index()
        if "index" in df.columns:
            df = df.rename(columns={"index": "TIME"})

    # Extra safety: remove duplicated column names, if any.
    df = df.loc[:, ~df.columns.duplicated()]

    return df


# ============================================================
# DATABASE FUNCTIONS
# ============================================================

def build_database():
    """
    Builds fuller_mill_data.db from the Fuller Excel files listed in FULLER_FILES.
    """
    missing_files = [f for f in FULLER_FILES.keys() if not os.path.exists(f)]

    if missing_files:
        st.error(
            "**Error: Required Fuller Excel files are missing:** "
            f"{', '.join(missing_files)}"
        )
        st.stop()

    with st.spinner("Building Fuller database from Excel files..."):
        conn = None

        try:
            if os.path.exists(TEMP_DB_NAME):
                os.remove(TEMP_DB_NAME)

            conn = sqlite3.connect(TEMP_DB_NAME)

            for file_name, cfg in FULLER_FILES.items():
                sheet_name = cfg.get("sheet_name", "Sheet1")
                label = cfg.get("label", "DATA")

                df = read_fuller_excel(file_name, sheet_name)

                table_name = f"df_FULLER_{label}"
                db_df = reset_index_for_db(df)
                db_df.to_sql(table_name, conn, if_exists="replace", index=False)

                st.write(f"Loaded `{file_name}` as dataset `{label}`.")

            conn.close()

            if os.path.exists(DB_NAME):
                os.remove(DB_NAME)

            shutil.move(TEMP_DB_NAME, DB_NAME)

            st.success(f"**Fuller database `{DB_NAME}` created successfully.**")

        except Exception as e:
            if conn is not None:
                conn.close()

            if os.path.exists(TEMP_DB_NAME):
                try:
                    os.remove(TEMP_DB_NAME)
                except Exception:
                    pass

            st.error(f"**Error while building Fuller database:** {e}")
            st.stop()


def load_data(force_rebuild=False):
    """
    Loads Fuller datasets from fuller_mill_data.db into st.session_state.fuller_datasets.
    """
    if force_rebuild or not os.path.exists(DB_NAME):
        build_database()

    datasets = {}

    try:
        conn = sqlite3.connect(DB_NAME)

        tables = pd.read_sql_query(
            "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'df_FULLER_%'",
            conn
        )["name"].tolist()

        if not tables:
            conn.close()
            build_database()
            conn = sqlite3.connect(DB_NAME)

            tables = pd.read_sql_query(
                "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'df_FULLER_%'",
                conn
            )["name"].tolist()

        for table in sorted(tables):
            label = table.replace("df_FULLER_", "")

            df = pd.read_sql_query(f'SELECT * FROM "{table}"', conn)

            if "TIME" in df.columns:
                df["TIME"] = pd.to_datetime(df["TIME"])
                df = df.set_index("TIME")
            else:
                df.index.name = "TIME"

            df = df.sort_index()
            df = ensure_derived_columns(df)

            datasets[label] = df

        conn.close()

    except Exception as e:
        st.error(f"**Error loading Fuller database:** {e}")
        st.stop()

    st.session_state.fuller_datasets = datasets


# ============================================================
# CHART HELPERS
# ============================================================

def get_resample_rule(agg_period):
    rules = {
        "per Hour": "h",
        "per Shift": "12h",
        "per Day": "D",
        "per Week": "W-MON",
        "per Month": "ME",
    }
    return rules.get(agg_period)


def get_raw_xy(df, x_col, y_col):
    """
    Returns raw x and y series for plotting.
    If x_col == 'TIME', the DataFrame DatetimeIndex is used.
    """
    if df is None or df.empty:
        return None, None

    if y_col not in df.columns:
        return None, None

    y = df[y_col]

    if x_col == "TIME":
        mask = y.notna()
        return df.index[mask], y[mask]

    if x_col not in df.columns:
        return None, None

    x = df[x_col]
    mask = y.notna() & x.notna()

    return x[mask], y[mask]


def get_aggregated_data(df, agg_period, x_col, y_col):
    """
    Aggregates x/y data by time period.
    If x_col == 'TIME', returns resampled DatetimeIndex as x.
    """
    if df is None or df.empty or y_col not in df.columns:
        return pd.Series(dtype=float), pd.Series(dtype=float)

    if agg_period not in AGG_OPTIONS:
        return get_raw_xy(df, x_col, y_col)

    rule = get_resample_rule(agg_period)

    if rule is None:
        return get_raw_xy(df, x_col, y_col)

    res = df.resample(rule).mean(numeric_only=True)

    if y_col not in res.columns:
        return pd.Series(dtype=float), pd.Series(dtype=float)

    y = res[y_col]

    if x_col == "TIME":
        mask = y.notna()
        return res.index[mask], y[mask]

    if x_col not in res.columns:
        return pd.Series(dtype=float), pd.Series(dtype=float)

    x = res[x_col]
    mask = y.notna() & x.notna()

    return x[mask], y[mask]


def plot_simple_chart(
    key,
    x_col,
    y_col,
    x_title,
    y_title,
    mode="lines",
    y_range=None,
    x_range=None
):
    """
    Generic Fuller chart builder.
    """
    agg_key = f"fuller_agg_{key}"
    fig_key = f"fuller_fig_{key}"

    if agg_key not in st.session_state:
        st.session_state[agg_key] = []

    if fig_key not in st.session_state:
        st.session_state[fig_key] = None

    col1, col2 = st.columns([3, 1])

    with col1:
        selected_agg = st.multiselect(
            "Select aggregation periods for this chart:",
            AGG_OPTIONS,
            default=st.session_state[agg_key],
            key=f"fuller_agg_multiselect_{key}"
        )

    with col2:
        update_chart = st.button("Update Chart", key=f"fuller_update_{key}")

    if update_chart:
        st.session_state[agg_key] = selected_agg

    if st.session_state[fig_key] is None or update_chart:
        fig = go.Figure()
        plotted = False

        datasets = st.session_state.get("fuller_datasets", {})

        for i, (label, df) in enumerate(datasets.items()):
            color = COLORS[i % len(COLORS)]

            x_raw, y_raw = get_raw_xy(df, x_col, y_col)

            if x_raw is None or len(y_raw) == 0:
                continue

            plotted = True

            if mode == "markers":
                fig.add_trace(
                    go.Scatter(
                        x=x_raw,
                        y=y_raw,
                        name=f"{y_title} - {label}",
                        mode="markers",
                        opacity=0.75,
                        marker=dict(color=color, size=5)
                    )
                )
            else:
                fig.add_trace(
                    go.Scatter(
                        x=x_raw,
                        y=y_raw,
                        name=f"{y_title} - {label}",
                        mode="lines",
                        opacity=0.85,
                        line=dict(color=color, width=2)
                    )
                )

            for agg_period in st.session_state[agg_key]:
                x_agg, y_agg = get_aggregated_data(df, agg_period, x_col, y_col)

                if len(y_agg) == 0:
                    continue

                if mode == "markers":
                    fig.add_trace(
                        go.Scatter(
                            x=x_agg,
                            y=y_agg,
                            name=f"{label} ({agg_period})",
                            mode="markers",
                            opacity=0.9,
                            marker=dict(color=color, size=6, symbol="diamond")
                        )
                    )
                else:
                    fig.add_trace(
                        go.Scatter(
                            x=x_agg,
                            y=y_agg,
                            name=f"{label} ({agg_period})",
                            mode="lines",
                            opacity=0.9,
                            line=dict(color=color, dash="dot", width=2)
                        )
                    )

        if not plotted:
            st.warning(f"No usable Fuller data found for `{y_title}`.")

        fig.update_yaxes(title_text=y_title, showgrid=True)
        fig.update_xaxes(title_text=x_title, showgrid=True)

        if y_range is not None:
            fig.update_yaxes(range=y_range)

        if x_range is not None:
            fig.update_xaxes(range=x_range)

        fig.update_layout(
            margin=dict(l=1, r=1, t=50, b=50),
            template="simple_white",
            showlegend=True,
            font=dict(size=12, color="Black"),
            height=640
        )

        fig.update_layout(
            legend=dict(
                yanchor="top",
                y=0.99,
                xanchor="left",
                x=0.03
            )
        )

        st.session_state[fig_key] = fig

    return st.session_state[fig_key]


def plot_feed_settings_vs_actual():
    """
    Fuller feed rate vs FeedMin / FeedMax settings.
    """
    key = "feed_settings"
    agg_key = f"fuller_agg_{key}"
    fig_key = f"fuller_fig_{key}"

    if agg_key not in st.session_state:
        st.session_state[agg_key] = []

    if fig_key not in st.session_state:
        st.session_state[fig_key] = None

    col1, col2 = st.columns([3, 1])

    with col1:
        selected_agg = st.multiselect(
            "Select aggregation periods for this chart:",
            AGG_OPTIONS,
            default=st.session_state[agg_key],
            key=f"fuller_agg_multiselect_{key}"
        )

    with col2:
        update_chart = st.button("Update Chart", key=f"fuller_update_{key}")

    if update_chart:
        st.session_state[agg_key] = selected_agg

    if st.session_state[fig_key] is None or update_chart:
        fig = go.Figure()
        plotted = False

        datasets = st.session_state.get("fuller_datasets", {})

        for i, (label, df) in enumerate(datasets.items()):
            color = COLORS[i % len(COLORS)]

            if "FEED" in df.columns and df["FEED"].notna().any():
                plotted = True
                fig.add_trace(
                    go.Scatter(
                        x=df.index,
                        y=df["FEED"],
                        name=f"Actual Feed - {label}",
                        mode="lines",
                        opacity=0.9,
                        line=dict(color=color, width=2)
                    )
                )

            if "FEEDMIN" in df.columns and df["FEEDMIN"].notna().any():
                plotted = True
                fig.add_trace(
                    go.Scatter(
                        x=df.index,
                        y=df["FEEDMIN"],
                        name=f"Feed Min - {label}",
                        mode="lines",
                        opacity=0.65,
                        line=dict(color=color, width=1, dash="dash")
                    )
                )

            if "FEEDMAX" in df.columns and df["FEEDMAX"].notna().any():
                plotted = True
                fig.add_trace(
                    go.Scatter(
                        x=df.index,
                        y=df["FEEDMAX"],
                        name=f"Feed Max - {label}",
                        mode="lines",
                        opacity=0.65,
                        line=dict(color=color, width=1, dash="dash")
                    )
                )

            for agg_period in st.session_state[agg_key]:
                trace_specs = [
                    ("FEED", "Actual Feed", None),
                    ("FEEDMIN", "Feed Min", "dash"),
                    ("FEEDMAX", "Feed Max", "dash"),
                ]

                for col, trace_label, dash in trace_specs:
                    x_agg, y_agg = get_aggregated_data(df, agg_period, "TIME", col)

                    if len(y_agg) == 0:
                        continue

                    fig.add_trace(
                        go.Scatter(
                            x=x_agg,
                            y=y_agg,
                            name=f"{trace_label} - {label} ({agg_period})",
                            mode="lines",
                            opacity=0.7,
                            line=dict(color=color, dash=dash, width=1.5)
                        )
                    )

        if not plotted:
            st.warning("No Fuller feed setting data found.")

        fig.update_yaxes(title_text="Fresh Feed - tph", showgrid=True)
        fig.update_xaxes(title_text="Time", showgrid=True)

        fig.update_layout(
            margin=dict(l=1, r=1, t=50, b=50),
            template="simple_white",
            showlegend=True,
            font=dict(size=12, color="Black"),
            height=640
        )

        fig.update_layout(
            legend=dict(
                yanchor="top",
                y=0.99,
                xanchor="left",
                x=0.03
            )
        )

        st.session_state[fig_key] = fig

    return st.session_state[fig_key]


# ============================================================
# STREAMLIT PAGE
# ============================================================

def app():
    st.subheader("Fuller Production Reporting", divider="rainbow")

    st.markdown(
        """
        This application visualises Fuller mill operating data.

        It reads data from a local SQLite database (`fuller_mill_data.db`).
        If the database does not exist, it will be created from the Fuller Excel files
        defined in `FULLER_PRODUCTION.py`.
        """
    )

    if "fuller_datasets" not in st.session_state:
        st.session_state.fuller_datasets = {}

    col1, col2 = st.columns([6, 1])

    with col2:
        reload_db = st.button("Reload Fuller DB", key="reload_fuller_db")

    if reload_db or not st.session_state.fuller_datasets:
        load_data(force_rebuild=reload_db)

    if not st.session_state.get("fuller_datasets"):
        st.error("No Fuller datasets could be loaded.")
        st.stop()

    st.info(
        "Loaded Fuller datasets: "
        + ", ".join(st.session_state.fuller_datasets.keys())
    )

    with st.expander("Preview loaded Fuller datasets", expanded=False):
        for label, df in st.session_state.fuller_datasets.items():
            st.markdown(f"**{label}**")
            st.dataframe(df.tail(5), use_container_width=True)

    plot_options = [
        "Pebble Rate vs CumFeed",
        "Milling Rate vs CumFeed",
        "Pebble Rate vs Time",
        "Cum Tons vs Time",
        "Fresh Feed vs Time",
        "Mill Runtime vs Time",

        "Mill Power vs Time",
        "Mill Power vs CumFeed",

        "Bearing Pressure vs Time",
        "Bearing Pressure vs CumFeed",
        "Bearing Pressure vs Fresh Feed",
        "Bearing Pressure vs Mill Power",

        "Crusher Power vs Time",
        "Crusher Power vs CumFeed",
        "Crusher Power vs Fresh Feed",
        "Crusher Power vs Mill Power",

        "Feed Settings vs Actual",
        "Silica vs CumFeed",
        "Silica Timeseries",
        "Water to Feed Ratio",
    ]

    selected_plot = st.selectbox(
        "Select a plot to display:",
        plot_options,
        key="fuller_plot_selector"
    )

    if selected_plot == "Pebble Rate vs CumFeed":
        st.subheader("Fuller Pebble Rate vs Cumulative Feed")
        fig = plot_simple_chart(
            key="pebble_cumfeed",
            x_col="CUMFEED",
            y_col="PEBBLE",
            x_title="Cumulative Tons Milled",
            y_title="Pebble Rate - tph",
            mode="lines"
        )
        st.plotly_chart(fig, use_container_width=True)

    elif selected_plot == "Milling Rate vs CumFeed":
        st.subheader("Fuller Milling Rate vs Cumulative Feed")
        fig = plot_simple_chart(
            key="milling_cumfeed",
            x_col="CUMFEED",
            y_col="FEED",
            x_title="Cumulative Tons Milled",
            y_title="Fresh Feed - tph",
            mode="lines"
        )
        st.plotly_chart(fig, use_container_width=True)

    elif selected_plot == "Pebble Rate vs Time":
        st.subheader("Fuller Pebble Rate vs Time")
        fig = plot_simple_chart(
            key="pebble_time",
            x_col="TIME",
            y_col="PEBBLE",
            x_title="Time",
            y_title="Pebble Rate - tph",
            mode="lines"
        )
        st.plotly_chart(fig, use_container_width=True)

    elif selected_plot == "Cum Tons vs Time":
        st.subheader("Fuller Cumulative Tons vs Time")
        fig = plot_simple_chart(
            key="cum_tons_time",
            x_col="TIME",
            y_col="CUMFEED",
            x_title="Time",
            y_title="Cumulative Tons - t",
            mode="lines"
        )
        st.plotly_chart(fig, use_container_width=True)

    elif selected_plot == "Fresh Feed vs Time":
        st.subheader("Fuller Fresh Feed vs Time")
        fig = plot_simple_chart(
            key="fresh_feed_time",
            x_col="TIME",
            y_col="FEED",
            x_title="Time",
            y_title="Fresh Feed - tph",
            mode="lines"
        )
        st.plotly_chart(fig, use_container_width=True)

    elif selected_plot == "Mill Runtime vs Time":
        st.subheader("Fuller Mill Runtime vs Time")
        fig = plot_simple_chart(
            key="mill_runtime_time",
            x_col="TIME",
            y_col="MILL_AVAILABILITY",
            x_title="Time",
            y_title="Mill Runtime - %",
            mode="lines",
            y_range=[0, 100]
        )
        st.plotly_chart(fig, use_container_width=True)

    elif selected_plot == "Mill Power vs Time":
        st.subheader("Fuller Mill Power vs Time")
        fig = plot_simple_chart(
            key="mill_power_time",
            x_col="TIME",
            y_col="POWER",
            x_title="Time",
            y_title="Mill Power - kW",
            mode="lines"
        )
        st.plotly_chart(fig, use_container_width=True)

    elif selected_plot == "Mill Power vs CumFeed":
        st.subheader("Fuller Mill Power vs Cumulative Feed")
        fig = plot_simple_chart(
            key="mill_power_cumfeed",
            x_col="CUMFEED",
            y_col="POWER",
            x_title="Cumulative Tons Milled",
            y_title="Mill Power - kW",
            mode="lines"
        )
        st.plotly_chart(fig, use_container_width=True)

    elif selected_plot == "Bearing Pressure vs Time":
        st.subheader("Fuller Bearing Pressure vs Time")
        fig = plot_simple_chart(
            key="bearing_pressure_time",
            x_col="TIME",
            y_col="BEARING_PRESSURE",
            x_title="Time",
            y_title="Bearing Pressure - kPa",
            mode="lines"
        )
        st.plotly_chart(fig, use_container_width=True)

    elif selected_plot == "Bearing Pressure vs CumFeed":
        st.subheader("Fuller Bearing Pressure vs Cumulative Feed")
        fig = plot_simple_chart(
            key="bearing_pressure_cumfeed",
            x_col="CUMFEED",
            y_col="BEARING_PRESSURE",
            x_title="Cumulative Tons Milled",
            y_title="Bearing Pressure - kPa",
            mode="lines"
        )
        st.plotly_chart(fig, use_container_width=True)

    elif selected_plot == "Bearing Pressure vs Fresh Feed":
        st.subheader("Fuller Bearing Pressure vs Fresh Feed")
        fig = plot_simple_chart(
            key="bearing_pressure_feed",
            x_col="FEED",
            y_col="BEARING_PRESSURE",
            x_title="Fresh Feed - tph",
            y_title="Bearing Pressure - kPa",
            mode="markers"
        )
        st.plotly_chart(fig, use_container_width=True)

    elif selected_plot == "Bearing Pressure vs Mill Power":
        st.subheader("Fuller Bearing Pressure vs Mill Power")
        fig = plot_simple_chart(
            key="bearing_pressure_power",
            x_col="POWER",
            y_col="BEARING_PRESSURE",
            x_title="Mill Power - kW",
            y_title="Bearing Pressure - kPa",
            mode="markers"
        )
        st.plotly_chart(fig, use_container_width=True)

    elif selected_plot == "Crusher Power vs Time":
        st.subheader("Fuller Crusher Power vs Time")
        fig = plot_simple_chart(
            key="crusher_power_time",
            x_col="TIME",
            y_col="CRUSHER_POWER",
            x_title="Time",
            y_title="Crusher Power - kW",
            mode="lines"
        )
        st.plotly_chart(fig, use_container_width=True)

    elif selected_plot == "Crusher Power vs CumFeed":
        st.subheader("Fuller Crusher Power vs Cumulative Feed")
        fig = plot_simple_chart(
            key="crusher_power_cumfeed",
            x_col="CUMFEED",
            y_col="CRUSHER_POWER",
            x_title="Cumulative Tons Milled",
            y_title="Crusher Power - kW",
            mode="lines"
        )
        st.plotly_chart(fig, use_container_width=True)

    elif selected_plot == "Crusher Power vs Fresh Feed":
        st.subheader("Fuller Crusher Power vs Fresh Feed")
        fig = plot_simple_chart(
            key="crusher_power_feed",
            x_col="FEED",
            y_col="CRUSHER_POWER",
            x_title="Fresh Feed - tph",
            y_title="Crusher Power - kW",
            mode="markers"
        )
        st.plotly_chart(fig, use_container_width=True)

    elif selected_plot == "Crusher Power vs Mill Power":
        st.subheader("Fuller Crusher Power vs Mill Power")
        fig = plot_simple_chart(
            key="crusher_power_mill_power",
            x_col="POWER",
            y_col="CRUSHER_POWER",
            x_title="Mill Power - kW",
            y_title="Crusher Power - kW",
            mode="markers"
        )
        st.plotly_chart(fig, use_container_width=True)

    elif selected_plot == "Feed Settings vs Actual":
        st.subheader("Fuller Feed Settings vs Actual")
        fig = plot_feed_settings_vs_actual()
        st.plotly_chart(fig, use_container_width=True)

    elif selected_plot == "Silica vs CumFeed":
        st.subheader("Fuller Silica vs Cumulative Feed")
        fig = plot_simple_chart(
            key="silica_cumfeed",
            x_col="CUMFEED",
            y_col="SILICA",
            x_title="Cumulative Tons Milled",
            y_title="Silica - %",
            mode="lines",
            y_range=[20, 50]
        )
        st.plotly_chart(fig, use_container_width=True)

    elif selected_plot == "Silica Timeseries":
        st.subheader("Fuller Silica Timeseries")
        fig = plot_simple_chart(
            key="silica_time",
            x_col="TIME",
            y_col="SILICA",
            x_title="Time",
            y_title="Silica - %",
            mode="lines",
            y_range=[20, 50]
        )
        st.plotly_chart(fig, use_container_width=True)

    elif selected_plot == "Water to Feed Ratio":
        st.subheader("Fuller Water to Feed Ratio vs Cumulative Feed")
        fig = plot_simple_chart(
            key="water_feed_ratio_cumfeed",
            x_col="CUMFEED",
            y_col="WATER_FEED_RATIO",
            x_title="Cumulative Tons Milled",
            y_title="Water to Feed Ratio - m³/t",
            mode="lines",
            y_range=[0, 2]
        )
        st.plotly_chart(fig, use_container_width=True)