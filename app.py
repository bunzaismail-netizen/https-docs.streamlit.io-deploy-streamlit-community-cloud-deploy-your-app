import streamlit as st
from streamlit_lottie import st_lottie
import requests
from requests.exceptions import RequestException
import sys
import os

# Add src directory to path once at startup (not in each page handler)
if "src" not in sys.path:
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

# At import time we only keep URL constants to avoid blocking network calls.
# Lotties will be fetched lazily when a page is shown using a cached loader.
# If loading fails, pages will show a static image fallback.

# Lottie URL constants (no network calls here)
lottie_home_url = "https://assets2.lottiefiles.com/packages/lf20_9cyyl8i4.json"
lottie_dashboard_url = "https://assets2.lottiefiles.com/packages/lf20_1pxqjqps.json"
lottie_upload_url = "https://assets2.lottiefiles.com/packages/lf20_tno6cg2w.json"
lottie_visualization_url = "https://assets2.lottiefiles.com/packages/lf20_tll0j4bb.json"
lottie_prediction_url = "https://assets2.lottiefiles.com/packages/lf20_5ngs2ksb.json"
lottie_report_url = "https://assets2.lottiefiles.com/packages/lf20_1cazwtnl.json"
lottie_about_url = "https://assets2.lottiefiles.com/packages/lf20_1pxqjqps.json"


@st.cache_data(ttl=60*60)
def cached_load_lottie(url: str, timeout: float = 2.0):
    """Fetch Lottie JSON with a short timeout and cache the result.

    Returns the parsed JSON on success or None on failure.
    """
    try:
        resp = requests.get(url, timeout=timeout)
        resp.raise_for_status()
        return resp.json()
    except RequestException:
        return None

# Updated rain animation URL for Visualization page
rain_anim = "https://assets2.lottiefiles.com/packages/lf20_Stt1RZ.json"

st.set_page_config(page_title="Climate Analysis Dashboard", layout="wide")

# Sidebar navigation
page = st.sidebar.radio(
    "Navigate",
    ["Home", "Dashboard", "Upload Data", "Visualization", "Prediction", "Report", "About"]
)

# Logout button in sidebar

# Page content with Lottie animation
if page == "Home":
    st.title("Home")
    lottie = cached_load_lottie(lottie_home_url)
    if lottie:
        st_lottie(lottie, height=200)
    else:
        st.info("Lottie animation could not be loaded.")
    st.markdown("""
    # Welcome to Climate Analysis Dashboard!
    Analyze climate and agricultural metrics with ease.
    This platform helps you manage, visualize, and report farm and climate data.
    Use the sidebar to navigate between Dashboard, Upload, Visualization, Prediction, and Reports.
    You can upload your own data, view trends, and generate professional reports.
    For help or more information, visit the About page.
    """)
elif page == "Dashboard":
    st.title("Dashboard")
    lottie = cached_load_lottie(lottie_dashboard_url)
    if lottie:
        st_lottie(lottie, height=200)
    else:
        st.info("Lottie animation could not be loaded.")

    from db_handler import DBHandler

    # Fetch farms
    try:
        with DBHandler() as db:
            farms = db.get_farms() if db else []
    except Exception as e:
        st.error(f"Database error: {e}")
        farms = []

    if not farms:
        st.warning("No farms found in the database. Please upload data or add a sample farm.")
    else:
        farm_names = [f["name"] for f in farms]
        selected_farm = st.selectbox("Select Farm", farm_names)
        farm_obj = next(f for f in farms if f["name"] == selected_farm)
        st.write(f"**Location:** {farm_obj['location']} | **Base Temp:** {farm_obj['base_temp']} °C")

        # Show summary stats
        with DBHandler() as db:
            summary = db.get_farm_summary(farm_obj["id"])
        st.subheader("Summary Statistics")
        st.write(f"Avg Temp: {summary.get('avg_temp', '--')}")
        st.write(f"Min Temp: {summary.get('min_temp', '--')}")
        st.write(f"Max Temp: {summary.get('max_temp', '--')}")
        st.write(f"Total Rainfall: {summary.get('total_rain', '--')}")
        st.write(f"Cumulative GDD: {summary.get('cumulative_gdd', '--')}")

        # Show climate/agri data table
        with DBHandler() as db:
            data = db.get_climate_data(farm_obj["id"], limit=50)
        if data:
            import pandas as pd
            df = pd.DataFrame(data)
            st.subheader("Climate & Agri Data Table")
            st.dataframe(df)
        else:
            st.info("No climate/agri data available for this farm.")
elif page == "Upload Data":
    st.title("Upload Data")
    lottie = cached_load_lottie(lottie_upload_url)
    if lottie:
        st_lottie(lottie, height=200)
    else:
        st.info("Lottie animation could not be loaded.")

    from db_handler import DBHandler

    # Farm selection
    try:
        with DBHandler() as db:
            farms = db.get_farms() if db else []
    except Exception as e:
        st.error(f"Database error: {e}")
        farms = []
    
    if not farms:
        st.warning("No farms found in the database. Please create a farm first.")
    else:
        farm_names = [f["name"] for f in farms]
        selected_farm = st.selectbox("Select Farm to Upload Data", farm_names)
        farm_obj = next(f for f in farms if f["name"] == selected_farm)

        # CSV upload
        st.markdown("---")
        st.subheader("Quick Setup: Add Sample Farm and Data")
        if st.button("Add Sample Farm and Data (for Prediction Demo)"):
            import pandas as pd
            # Split demo data into two DataFrames to guarantee both tables have all dates
            demo_dates = [
                "2025-10-01",
                "2025-10-02",
                "2025-10-03",
                "2025-10-04",
                "2025-10-05"
            ]
            climate_rows = [
                {"date": d, "temp_max": tmax, "temp_min": tmin, "rainfall": rain}
                for d, tmax, tmin, rain in zip(
                    demo_dates,
                    [32.5, 33.1, 31.8, 30.2, 29.9],
                    [18.2, 19.0, 17.5, 16.8, 16.0],
                    [12.0, 10.5, 8.0, 15.0, 20.0]
                )
            ]
            agri_rows = [
                {"date": d, "daily_gdd": gdd, "effective_rainfall": eff, "cumulative_gdd": cum}
                for d, gdd, eff, cum in zip(
                    demo_dates,
                    [15.0, 16.2, 14.5, 13.8, 13.0],
                    [5.0, 4.8, 4.5, 5.2, 6.0],
                    [120.0, 136.2, 150.7, 164.5, 177.5]
                )
            ]
            climate_df = pd.DataFrame(climate_rows)
            agri_df = pd.DataFrame(agri_rows)
            sample_farm_name = "DemoFarm"
            sample_location = "DemoLocation"
            sample_base_temp = 10.0
            with DBHandler() as db:
                # Create farm if not exists
                farms = db.get_farms()
                farm_db = next((f for f in farms if f["name"] == sample_farm_name and f["location"] == sample_location), None)
                if not farm_db:
                    db.execute_query(
                        "INSERT INTO farms (name, location, base_temp) VALUES (?, ?, ?)",
                        (sample_farm_name, sample_location, sample_base_temp)
                    )
                    farms = db.get_farms()
                    farm_db = next((f for f in farms if f["name"] == sample_farm_name and f["location"] == sample_location), None)
                farm_id = farm_db["id"] if farm_db else None
                if not farm_id:
                    st.error("Could not create or find the demo farm in the database.")
                else:
                    # Delete old data for this farm
                    db.delete_farm(farm_id)
                    # Re-create farm after delete
                    db.execute_query(
                        "INSERT INTO farms (name, location, base_temp) VALUES (?, ?, ?)",
                        (sample_farm_name, sample_location, sample_base_temp)
                    )
                    farms = db.get_farms()
                    farm_db = next((f for f in farms if f["name"] == sample_farm_name and f["location"] == sample_location), None)
                    farm_id = farm_db["id"] if farm_db else None
                    # Insert sample data, ensuring both tables have all dates
                    for _, row in climate_df.iterrows():
                        db.execute_query(
                            "INSERT INTO climate_data (farm_id, date, temp_max, temp_min, rainfall) VALUES (?, ?, ?, ?, ?)",
                            (farm_id, row["date"], row["temp_max"], row["temp_min"], row["rainfall"])
                        )
                    for _, row in agri_df.iterrows():
                        db.execute_query(
                            "INSERT INTO agri_metrics (farm_id, date, daily_gdd, effective_rainfall, cumulative_gdd) VALUES (?, ?, ?, ?, ?)",
                            (farm_id, row["date"], row["daily_gdd"], row["effective_rainfall"], row["cumulative_gdd"])
                        )
                    st.success("Demo farm and sample data added! Go to the Prediction page, select 'DemoLocation', and try a prediction.")
        st.subheader("Upload CSV File")
        uploaded_file = st.file_uploader("Choose a CSV file", type=["csv"])
        if uploaded_file is not None:
            import pandas as pd
            df = pd.read_csv(uploaded_file)
            st.write("Preview of uploaded data:")
            st.dataframe(df.head(10))
            # Add a button to delete all data for this farm before import
            if st.button("Delete ALL Data for This Farm Before Import", key="delete_farm_data"):
                with DBHandler() as db:
                    db.delete_farm(farm_obj["id"])
                st.success("All data for this farm has been deleted. You can now import fresh data.")
            if st.button("Import Data to Database"):
                # Accept both eff_rain/cum_gdd and effective_rainfall/cumulative_gdd
                required_climate = ["date", "temp_max", "temp_min", "rainfall"]
                required_agri = ["date", "daily_gdd", "effective_rainfall", "cumulative_gdd"]
                # Map legacy columns if present
                if "eff_rain" in df.columns:
                    df["effective_rainfall"] = df["eff_rain"]
                if "cum_gdd" in df.columns:
                    df["cumulative_gdd"] = df["cum_gdd"]
                # Auto-create farm if missing
                farm_name = farm_obj["name"] if "name" in farm_obj else None
                location = farm_obj["location"] if "location" in farm_obj else None
                base_temp = farm_obj["base_temp"] if "base_temp" in farm_obj else 10.0
                if farm_name and location:
                    with DBHandler() as db:
                        # Check if farm exists, else create
                        farms = db.get_farms()
                        farm_db = next((f for f in farms if f["name"] == farm_name and f["location"] == location), None)
                        if not farm_db:
                            db.execute_query(
                                "INSERT INTO farms (name, location, base_temp) VALUES (?, ?, ?)",
                                (farm_name, location, base_temp)
                            )
                            farms = db.get_farms()
                            farm_db = next((f for f in farms if f["name"] == farm_name and f["location"] == location), None)
                        farm_id = farm_db["id"] if farm_db else None
                        if not farm_id:
                            st.error("Could not create or find the farm in the database.")
                        else:
                            # Check for all required columns
                            missing_climate = [col for col in required_climate if col not in df.columns]
                            missing_agri = [col for col in required_agri if col not in df.columns]
                            if not missing_climate and not missing_agri:
                                for _, row in df.iterrows():
                                    db.execute_query(
                                        "INSERT OR IGNORE INTO climate_data (farm_id, date, temp_max, temp_min, rainfall) VALUES (?, ?, ?, ?, ?)",
                                        (farm_id, row["date"], row["temp_max"], row["temp_min"], row["rainfall"])
                                    )
                                    db.execute_query(
                                        "INSERT OR IGNORE INTO agri_metrics (farm_id, date, daily_gdd, effective_rainfall, cumulative_gdd) VALUES (?, ?, ?, ?, ?)",
                                        (farm_id, row["date"], row["daily_gdd"], row["effective_rainfall"], row["cumulative_gdd"])
                                    )
                                st.success("Data imported successfully!")
                            else:
                                st.error(f"CSV must contain columns: {', '.join(required_climate + required_agri)}")
                else:
                    st.error("Farm name or location missing. Please check your farm selection and CSV.")
elif page == "Visualization":
    import numpy as np
    st.title("Visualization")
    lottie = cached_load_lottie(lottie_visualization_url)
    if lottie:
        st_lottie(lottie, height=200)
    else:
        st.info("Lottie animation could not be loaded.")

    from db_handler import DBHandler

    # Farm selection
    with DBHandler() as db:
        farms = db.get_farms()
    if not farms:
        st.warning("No farms found in the database.")
    else:
        # Gather all unique locations from farms
        all_locations = sorted(set(f["location"] for f in farms if f["location"]))
        selected_locations = st.multiselect("Select Locations for Comparison", all_locations, default=all_locations[:1])
        st.write(f"Showing data for locations: **{', '.join(selected_locations)}**")

        # Find all farms at selected locations
        location_farms = [f for f in farms if f["location"] in selected_locations]
        # For map: get lat/lon if available, else use dummy coordinates
        map_data = []
        for f in location_farms:
            lat = f.get("lat", 20.0 + hash(f["location"]) % 30)
            lon = f.get("lon", 70.0 + hash(f["location"]) % 30)
            map_data.append({"lat": lat, "lon": lon, "location": f["location"]})
        import pandas as pd
        if map_data:
            map_df = pd.DataFrame(map_data)
            st.map(map_df)

        # For comparison, show metrics for each location
        metrics_by_location = {}
        for loc in selected_locations:
            farms_at_loc = [f for f in farms if f["location"] == loc]
            if farms_at_loc:
                with DBHandler() as db:
                    data = db.fetch_all(
                        """
                        SELECT c.date, c.temp_max, c.temp_min, c.rainfall,
                               m.daily_gdd, m.effective_rainfall, m.cumulative_gdd
                        FROM climate_data c
                        LEFT JOIN agri_metrics m ON c.farm_id = m.farm_id AND c.date = m.date
                        JOIN farms f ON c.farm_id = f.id
                        WHERE f.location=?
                        ORDER BY c.date ASC LIMIT 100
                        """, (loc,)
                    )
                columns = ["date", "temp_max", "temp_min", "rainfall", "daily_gdd", "effective_rainfall", "cumulative_gdd"]
                metrics_by_location[loc] = pd.DataFrame(data, columns=columns) if data else None
            else:
                metrics_by_location[loc] = None

        # Data selection
        metric = st.selectbox("Select Metric", ["temp_max", "temp_min", "rainfall", "daily_gdd", "effective_rainfall", "cumulative_gdd"])
        # Show metrics and graphs for each location side-by-side
        if not any(df is not None and not df.empty for df in metrics_by_location.values()):
            st.info("No data available for visualization for these locations.")
        else:
            for loc, df in metrics_by_location.items():
                st.markdown(f"### Location: {loc}")
                if df is None or df.empty:
                    st.info(f"No data for {loc}.")
                    continue
                col1, col2, col3 = st.columns([2,2,2])
                with col1:
                    st.markdown("**Climate Map (Demo)**")
                    st.image("https://raw.githubusercontent.com/holtzy/D3-graph-gallery/master/DATA/map_world.png", caption="World Climate Map", width='stretch')
                    st.markdown("**Today's Weather**")
                    import random
                    rain_anim_url = "https://assets2.lottiefiles.com/packages/lf20_Stt1RZ.json"
                    sun_anim_url = "https://assets2.lottiefiles.com/packages/lf20_4kx2q32n.json"
                    weather = random.choice(["Rain", "Sunny"])
                    if weather == "Rain":
                        rain_lottie = cached_load_lottie(rain_anim_url)
                        if rain_lottie:
                            st_lottie(rain_lottie, height=120)
                        else:
                            st.image("https://cdn-icons-png.flaticon.com/512/1163/1163624.png", width=80)
                        st.write(":umbrella: Rainy today!")
                    else:
                        sun_lottie = cached_load_lottie(sun_anim_url)
                        if sun_lottie:
                            st_lottie(sun_lottie, height=120)
                        else:
                            st.image("https://cdn-icons-png.flaticon.com/512/869/869869.png", width=80)
                        st.write(":sunny: Sunny today!")
                with col2:
                    st.markdown("**Key Metrics**")
                    if 'temp_max' in df.columns and 'rainfall' in df.columns:
                        st.metric("Mean Temp (Observed)", f"{df['temp_max'].mean():.1f} °C")
                        st.metric("Mean Temp (Scenario)", f"{df['temp_max'].max():.1f} °C")
                        st.metric("Rainfall (Total)", f"{df['rainfall'].sum():.1f} mm")
                    else:
                        st.info("No temperature or rainfall data available for this location.")
                with col3:
                    st.markdown("**Temperature Change Gauge**")
                    import matplotlib.pyplot as plt
                    if 'temp_max' in df.columns:
                        value = float(df['temp_max'].mean()) if not np.isnan(df['temp_max'].mean()) else 0
                        fig, ax = plt.subplots(figsize=(2,2))
                        ax.barh([0], [value], color="#ff4b4b")
                        ax.set_xlim(0, 50)
                        ax.set_yticks([])
                        ax.set_title("Temp Gauge")
                        st.pyplot(fig)
                    else:
                        st.info("No temperature data available for gauge.")
                st.markdown("---")
                st.subheader(f"{metric} Trend for {loc}")
                if metric in df.columns:
                    fig2, ax2 = plt.subplots(figsize=(8,3))
                    y = df[metric].to_numpy()
                    x = np.arange(len(y))
                    ax2.plot(x, y, color="#2563eb", linewidth=2)
                    if metric in ["temp_max", "temp_min"]:
                        mean_val = np.mean(y)
                        for i, val in enumerate(y):
                            if val < mean_val:
                                ax2.text(i, val, "☔", fontsize=14, ha='center', va='bottom')
                            else:
                                ax2.text(i, val, "☀", fontsize=14, ha='center', va='bottom')
                    ax2.set_xticks(x)
                    ax2.set_xticklabels(df["date"], rotation=45, fontsize=8)
                    ax2.set_xlabel("Date")
                    ax2.set_ylabel(metric)
                    ax2.set_title(f"{metric} Trend (Wavy)")
                    st.pyplot(fig2)
                else:
                    st.warning(f"No data for metric '{metric}' in this location.")
                st.markdown("---")
                st.subheader("Climate & Agri Data Table")
                st.dataframe(df)
        # ...existing code...
elif page == "Report":
    st.title("Report")
    st.image("https://cdn-icons-png.flaticon.com/512/3135/3135715.png", width=120, caption="Report Document")

    from db_handler import DBHandler
    import pandas as pd

    with DBHandler() as db:
        farms = db.get_farms()
    if not farms:
        st.warning("No farms found in the database.")
    else:
        farm_names = [f["name"] for f in farms]
        selected_farms = st.multiselect("Select Farms for Report", farm_names, default=farm_names[:1])
        st.subheader("Select Date Range")
        start_date = st.text_input("Start Date (YYYY-MM-DD)")
        end_date = st.text_input("End Date (YYYY-MM-DD)")

        st.subheader("Select User (for admin)")
        selected_user = st.text_input("Report User", value="Guest")

        # Diagnostic: Show available farm names and their date ranges
        with DBHandler() as db:
            farm_date_data = db.fetch_all(
                """
                SELECT f.name, MIN(c.date) as min_date, MAX(c.date) as max_date, COUNT(*) as records
                FROM farms f
                JOIN climate_data c ON c.farm_id = f.id
                GROUP BY f.id
                ORDER BY f.name
                """
            )
        diag_columns = ["Farm Name", "Earliest Date", "Latest Date", "Records"]
        df_diag = pd.DataFrame(farm_date_data, columns=diag_columns) if farm_date_data else pd.DataFrame(columns=diag_columns)
        st.markdown("**Available Farms and Date Ranges**")
        st.dataframe(df_diag)

        if st.button("Generate Report"):
            # Get selected farm IDs
            selected_farm_objs = [f for f in farms if f["name"] in selected_farms]
            selected_farm_ids = [f["id"] for f in selected_farm_objs]
            # Query data for selected farms and date range
            if not selected_farm_ids or not start_date or not end_date:
                st.warning("Please select farms and enter a valid date range.")
            else:
                with DBHandler() as db:
                    placeholders = ','.join(['?']*len(selected_farm_ids))
                    query = f"""
                        SELECT f.name as farm_name, c.date, c.temp_max, c.temp_min, c.rainfall,
                               m.daily_gdd, m.effective_rainfall, m.cumulative_gdd
                        FROM climate_data c
                        LEFT JOIN agri_metrics m ON c.farm_id = m.farm_id AND c.date = m.date
                        JOIN farms f ON c.farm_id = f.id
                        WHERE c.farm_id IN ({placeholders}) AND c.date >= ? AND c.date <= ?
                        ORDER BY c.date ASC
                    """
                    params = selected_farm_ids + [start_date, end_date]
                    data = db.fetch_all(query, tuple(params))
                columns = ["farm_name", "date", "temp_max", "temp_min", "rainfall", "daily_gdd", "effective_rainfall", "cumulative_gdd"]
                df_report = pd.DataFrame(data, columns=columns) if data else pd.DataFrame(columns=columns)
                if df_report.empty:
                    st.info("No data found for the selected farms and date range.")
                else:
                    st.subheader("Report Table")
                    st.dataframe(df_report)
                    # Show summary metrics
                    st.markdown("**Summary Metrics**")
                    st.write(f"Total Records: {len(df_report)}")
                    st.write(f"Mean Max Temp: {df_report['temp_max'].mean():.2f} °C")
                    st.write(f"Total Rainfall: {df_report['rainfall'].sum():.2f} mm")
                    # Download button
                    csv = df_report.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="Download Report as CSV",
                        data=csv,
                        file_name=f"climate_report_{selected_user}_{start_date}_to_{end_date}.csv",
                        mime="text/csv"
                    )
elif page == "About":
    st.title("About")
    lottie = cached_load_lottie(lottie_about_url)
    if lottie:
        st_lottie(lottie, height=200)
    else:
        st.image("https://cdn-icons-png.flaticon.com/512/2922/2922506.png", width=120)
    st.markdown("""
    ## About Climate Analysis Dashboard
    This dashboard helps you analyze climate and agricultural data, visualize trends, run AI-based predictions, and generate reports for your farms.
    
    - Use the sidebar to navigate between pages.
    - Upload your own data, view metrics, and compare locations.
    - The Prediction page uses regression to forecast climate metrics.
    - For help or feedback, contact the developer or visit the documentation.
    """)
elif page == "Prediction":
    st.title("Prediction")
    lottie = cached_load_lottie(lottie_prediction_url)
    if lottie:
        st_lottie(lottie, height=200)
    else:
        st.image("https://cdn-icons-png.flaticon.com/512/2910/2910798.png", width=120)

    from db_handler import DBHandler
    import pandas as pd
    import numpy as np
    from sklearn.linear_model import LinearRegression
    from sklearn.metrics import mean_squared_error

    # Section: Data Diagnostics
    st.subheader("Available Locations and Data Coverage")
    with DBHandler() as db:
        loc_date_data = db.fetch_all(
            """
            SELECT f.id, f.name, f.location, MIN(c.date) as min_date, MAX(c.date) as max_date, COUNT(*) as records
            FROM farms f
            JOIN climate_data c ON c.farm_id = f.id
            GROUP BY f.id, f.location
            ORDER BY f.location
            """
        )
    diag_columns = ["Farm ID", "Farm Name", "Location", "Earliest Date", "Latest Date", "Records"]
    df_diag = pd.DataFrame(loc_date_data, columns=diag_columns) if loc_date_data else pd.DataFrame(columns=diag_columns)
    st.dataframe(df_diag)

    # Section: Location Selection
    with DBHandler() as db:
        farms = db.get_farms()
    all_locations = sorted(set(f["location"] for f in farms if f["location"]))
    if "DemoLocation" not in all_locations:
        all_locations.append("DemoLocation")
    selected_location = st.selectbox("Select Location for Prediction", all_locations, index=all_locations.index("DemoLocation") if "DemoLocation" in all_locations else 0)
    st.write(f"Showing prediction for location: **{selected_location}**")

    # Section: Model Training & Diagnostics
    with DBHandler() as db:
        # Get farm IDs for the selected location
        farms = db.get_farms()
        farm_ids = [f["id"] for f in farms if f["location"] == selected_location]
        if not farm_ids:
            st.warning(f"No farms found for location: {selected_location}")
            df = pd.DataFrame()
        else:
            placeholders = ','.join(['?']*len(farm_ids))
            data = db.fetch_all(
                f"""
                SELECT c.date, c.temp_max, c.temp_min, c.rainfall,
                       m.daily_gdd, m.effective_rainfall, m.cumulative_gdd
                FROM farms f
                LEFT JOIN climate_data c ON c.farm_id = f.id
                LEFT JOIN agri_metrics m ON m.farm_id = f.id AND c.date = m.date
                WHERE f.id IN ({placeholders})
                ORDER BY c.date ASC LIMIT 200
                """, tuple(farm_ids)
            )
            df = pd.DataFrame(data, columns=["date", "temp_max", "temp_min", "rainfall", "daily_gdd", "effective_rainfall", "cumulative_gdd"])
    st.write("Historical Data Sample:")
    st.dataframe(df.head(10))
    # Diagnostics: Show raw climate_data and agri_metrics for this farm
    if farm_ids:
        st.markdown("**Raw climate_data for this farm:**")
        raw_climate = db.fetch_all("SELECT * FROM climate_data WHERE farm_id=? ORDER BY date ASC LIMIT 10", (farm_ids[0],))
        st.write(raw_climate)
        st.markdown("**Raw agri_metrics for this farm:**")
        raw_agri = db.fetch_all("SELECT * FROM agri_metrics WHERE farm_id=? ORDER BY date ASC LIMIT 10", (farm_ids[0],))
        st.write(raw_agri)

    # Diagnostic: Show actual columns present and missing
    st.markdown("**Available Columns in Data**")
    st.write(list(df.columns))

    feature_cols = ["temp_min", "rainfall", "daily_gdd", "effective_rainfall", "cumulative_gdd"]
    target_col = "temp_max"
    missing_cols = [col for col in feature_cols + [target_col] if col not in df.columns]
    if missing_cols:
        st.warning(f"Missing columns for prediction: {', '.join(missing_cols)}. Please check your data import and database.")
    elif df.empty:
        st.warning("No data available for regression. Please check your data coverage above.")
    else:
        df = df.dropna(subset=feature_cols + [target_col])
        if df.empty:
            st.warning("No complete records for regression. Please check data coverage above.")
        else:
            X = df[feature_cols].to_numpy()
            y = df[target_col].to_numpy()

            # Train regression model
            model = LinearRegression()
            model.fit(X, y)
            y_pred = model.predict(X)
            rmse = np.sqrt(mean_squared_error(y, y_pred))

            st.subheader("Model Performance")
            st.metric("Root Mean Squared Error (RMSE)", f"{rmse:.2f}")

            # Section: Future Prediction Input
            st.subheader("Enter Future Parameters for Prediction")
            temp_min_f = st.number_input("Min Temp (°C)", min_value=-50.0, max_value=60.0, value=20.0)
            rainfall_f = st.number_input("Rainfall (mm)", min_value=0.0, max_value=500.0, value=10.0)
            daily_gdd_f = st.number_input("Daily GDD", min_value=0.0, max_value=100.0, value=10.0)
            eff_rain_f = st.number_input("Effective Rainfall (mm)", min_value=0.0, max_value=100.0, value=5.0)
            cum_gdd_f = st.number_input("Cumulative GDD", min_value=0.0, max_value=10000.0, value=100.0)

            if st.button("Run AI Prediction"):
                X_future = np.array([[temp_min_f, rainfall_f, daily_gdd_f, eff_rain_f, cum_gdd_f]])
                pred_temp_max = model.predict(X_future)[0]
                st.success(f"Predicted Max Temp: {pred_temp_max:.2f} °C")

            # Section: Prediction vs Actual Graph
            st.subheader("Prediction vs Actual (Training Data)")
            import matplotlib.pyplot as plt
            fig, ax = plt.subplots(figsize=(8,4))
            ax.plot(df["date"].to_numpy(), y, label="Actual", color="#2563eb")
            ax.plot(df["date"].to_numpy(), y_pred, label="Predicted", color="#ff4b4b", linestyle="--")
            ax.set_xlabel("Date")
            ax.set_ylabel("Max Temp (°C)")
            ax.set_title("AI Regression Prediction vs Actual")
            ax.legend()
            ax.tick_params(axis='x', labelrotation=45)
            st.pyplot(fig)
