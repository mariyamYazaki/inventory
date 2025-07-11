# services/styling.py
def inject_css():
    from streamlit import markdown

    markdown("""
    <style>
        .stButton>button { background-color: #4CAF50; color: white; padding: 10px 24px; }
        .stDownloadButton>button { background-color: #2196F3; color: white; }
        .error-box { background-color: #FFEBEE; padding: 10px; border-left: 4px solid #F44336; }
        .file-info { font-size: 0.9em; color: #666; margin-top: -10px; }
        .warning-box { background-color: #FFF3E0; padding: 10px; border-left: 4px solid #FF9800; }

        /* KPI Cards */
        .kpi-card {
            background: white; border-radius: 16px; padding: 24px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.08);
            height: 100%; position: relative;
        }
        .kpi-header { display: flex; align-items: center; margin-bottom: 16px; }
        .kpi-icon {
            width: 50px; height: 50px; border-radius: 12px;
            display: flex; align-items: center; justify-content: center;
            font-size: 24px; margin-right: 16px;
        }
        .kpi-title { font-size: 16px; font-weight: 600; color: #555; margin: 0; }
        .kpi-value { font-size: 36px; font-weight: 700; margin: 8px 0; color: #222; }
        .kpi-description { font-size: 14px; color: #777; margin: 0; }

        .plant-badge {
            display: inline-flex; align-items: center; padding: 6px 12px;
            border-radius: 20px; font-size: 14px; margin-right: 8px;
            background-color: #f5f5f5;
        }
        .plant-badge-icon { margin-right: 6px; font-size: 16px; }
    </style>
    """, unsafe_allow_html=True)