# app_streamlit.py
import streamlit as st
import os
from services.styling import inject_css
from modules.explore_dashboard import show_explore_page
from modules.ai_predictions import show_ai_predictions_page
from modules.custom_dashboard import show_custom_dashboard_page

# === CONFIGURATION ===
st.set_page_config(page_title="Inventory Forecast AI", layout="wide")
inject_css()

# === CREATE FOLDERS ===
os.makedirs("data/raw/forecast", exist_ok=True)
os.makedirs("data/raw/consumption", exist_ok=True)
os.makedirs("data/merged", exist_ok=True)
os.makedirs("data/custom/raw/forecast", exist_ok=True)
os.makedirs("data/custom/raw/consumption", exist_ok=True)
os.makedirs("data/custom/merged", exist_ok=True)

# === SIDEBAR ===
with st.sidebar:
    # Smaller Yazaki logo
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        logo_path = os.path.join(script_dir, "assets", "yazaa.png")
        
        if os.path.exists(logo_path):
            # Set width to 100px for smaller logo
            st.image(logo_path, width=300)  # Adjust this value as needed
        else:
            st.warning(f"Logo not found at: {logo_path}")
    except Exception as e:
        st.error(f"Error loading logo: {str(e)}")
    
    # Navigation section
    st.markdown("## Navigation")
    if "page" not in st.session_state:
        st.session_state.page = "Explore Data"

    selected_page = st.radio(
        "Select Section:", 
        ["Explore Data", "AI Predictions", "Custom Dashboard"],
        index=["Explore Data", "AI Predictions", "Custom Dashboard"].index(st.session_state.page)
    )
    st.session_state.page = selected_page

    st.markdown("---")

    if st.session_state.page != "Custom Dashboard":
        st.markdown("## Data Upload")
        forecast_files = st.file_uploader(
            "Upload Forecast Files", 
            type=None, 
            accept_multiple_files=True,
            help="Upload your forecast data files"
        )
        consumption_file = st.file_uploader(
            "Upload Consumption File", 
            type=None,
            help="Upload your consumption data file"
        )
        
        if st.button("Reset All", type="secondary"):
            st.experimental_rerun()
        
        st.caption("Files with the same name will be overwritten")

# === ROUTING ===
if st.session_state.page == "Explore Data":
    show_explore_page(forecast_files, consumption_file)
elif st.session_state.page == "AI Predictions":
    show_ai_predictions_page(forecast_files, consumption_file)
elif st.session_state.page == "Custom Dashboard":
    show_custom_dashboard_page()