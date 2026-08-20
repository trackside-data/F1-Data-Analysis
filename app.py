import streamlit as st

race_analysis = st.Page("app_pages/race_analysis.py", title="Race Analysis", icon="🏎️")
season_standings = st.Page("app_pages/1_Season_Standings.py", title="Season Standings", icon="🏆")
head_to_head = st.Page("app_pages/2_Head_to_Head.py", title="Head to Head", icon="🤝")
qualifying_analysis = st.Page("app_pages/3_Qualifying_Analysis.py", title="Qualifying Analysis", icon="🏁")
prediction_helper = st.Page("app_pages/4_Prediction_Helper.py", title="Prediction Helper", icon="🔮")

pg = st.navigation([race_analysis, season_standings, head_to_head, qualifying_analysis, prediction_helper])
pg.run()