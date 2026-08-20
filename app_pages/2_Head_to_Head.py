import streamlit as st
from datetime import datetime
import fastf1
from fastf1.ergast import Ergast
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

fastf1.Cache.enable_cache('cache')

st.title("Head to Head: Career Stats")
st.caption("Career totals are pulled from every race, sprint, and qualifying session on record, not just 2018 onward. DNF is estimated from each race's finishing status.")

ergast = Ergast()

BG_COLOR = "#15151E"

def style_matplotlib_ax(fig, ax):
    fig.patch.set_facecolor(BG_COLOR)
    ax.set_facecolor(BG_COLOR)
    ax.tick_params(colors='white')
    ax.xaxis.label.set_color('white')
    ax.yaxis.label.set_color('white')
    ax.title.set_color('white')
    for spine in ax.spines.values():
        spine.set_color('white')
    ax.grid(True, color='gray', alpha=0.3)

@st.cache_data(ttl=3600)
def load_recent_drivers():
    current_year = datetime.now().year
    drivers = {}
    for yr in range(2018, current_year + 1):
        try:
            info = ergast.get_driver_info(season=yr)
            for _, row in info.iterrows():
                drivers[row['driverId']] = f"{row['givenName']} {row['familyName']}"
        except Exception:
            continue
    return drivers

with st.spinner("Loading driver list..."):
    driver_dict = load_recent_drivers()

driver_ids = sorted(driver_dict.keys(), key=lambda d: driver_dict[d])

driver1_id = st.selectbox("Driver 1", driver_ids, format_func=lambda d: driver_dict[d], key="h2h_driver1")
remaining_ids = [d for d in driver_ids if d != driver1_id]
driver2_id = st.selectbox("Driver 2", remaining_ids, format_func=lambda d: driver_dict[d], key="h2h_driver2")

@st.cache_data(ttl=3600)
def load_career_race_results(driver_id):
    all_frames = []
    offset = 0
    page_size = 100
    for _ in range(20):
        response = ergast.get_race_results(driver=driver_id, limit=page_size, offset=offset)
        if len(response.content) == 0:
            break
        all_frames.append(pd.concat(response.content, ignore_index=True))
        if len(response.content) < page_size:
            break
        offset += page_size
    if len(all_frames) == 0:
        return pd.DataFrame()
    return pd.concat(all_frames, ignore_index=True)

@st.cache_data(ttl=3600)
def load_career_qualifying_results(driver_id):
    all_frames = []
    offset = 0
    page_size = 100
    for _ in range(20):
        response = ergast.get_qualifying_results(driver=driver_id, limit=page_size, offset=offset)
        if len(response.content) == 0:
            break
        all_frames.append(pd.concat(response.content, ignore_index=True))
        if len(response.content) < page_size:
            break
        offset += page_size
    if len(all_frames) == 0:
        return pd.DataFrame()
    return pd.concat(all_frames, ignore_index=True)

@st.cache_data(ttl=3600)
def load_career_sprint_results(driver_id):
    all_frames = []
    offset = 0
    page_size = 100
    for _ in range(20):
        response = ergast.get_sprint_results(driver=driver_id, limit=page_size, offset=offset)
        if len(response.content) == 0:
            break
        all_frames.append(pd.concat(response.content, ignore_index=True))
        if len(response.content) < page_size:
            break
        offset += page_size
    if len(all_frames) == 0:
        return pd.DataFrame()
    return pd.concat(all_frames, ignore_index=True)

def compute_career_stats(driver_id):
    races = load_career_race_results(driver_id)
    qualis = load_career_qualifying_results(driver_id)

    total_races = len(races)
    if total_races == 0:
        return {'Races': 0, 'Wins': 0, 'Podiums': 0, 'Poles': 0, 'Fastest Laps': 0, 'Career Points': 0, 'DNFs': 0, 'Win %': 0, 'Podium %': 0}

    wins = int((races['position'] == 1).sum())
    podiums = int((races['position'] <= 3).sum())

    sprints = load_career_sprint_results(driver_id)
    sprint_points = sprints['points'].sum() if len(sprints) > 0 else 0
    points = races['points'].sum() + sprint_points

    fastest_laps = int((races['fastestLapRank'] == 1).sum())

    finished_mask = (races['status'] == 'Finished') | (races['status'].str.startswith('+', na=False))
    dnfs = int((~finished_mask).sum())

    poles = int((qualis['position'] == 1).sum()) if len(qualis) > 0 else 0

    return {
        'Races': total_races,
        'Wins': wins,
        'Podiums': podiums,
        'Poles': poles,
        'Fastest Laps': fastest_laps,
        'Career Points': points,
        'DNFs': dnfs,
        'Win %': round(wins / total_races * 100, 1),
        'Podium %': round(podiums / total_races * 100, 1),
    }

with st.spinner(f"Loading career stats for {driver_dict[driver1_id]} and {driver_dict[driver2_id]}..."):
    stats1 = compute_career_stats(driver1_id)
    stats2 = compute_career_stats(driver2_id)

comparison_df = pd.DataFrame({
    'Stat': list(stats1.keys()),
    driver_dict[driver1_id]: list(stats1.values()),
    driver_dict[driver2_id]: list(stats2.values()),
})

st.dataframe(comparison_df, hide_index=True)

categories = ['Wins', 'Podiums', 'Poles', 'Fastest Laps']
values1 = [stats1[c] for c in categories]
values2 = [stats2[c] for c in categories]

x = np.arange(len(categories))
width = 0.35

fig, ax = plt.subplots(figsize=(10, 6))
ax.bar(x - width/2, values1, width, label=driver_dict[driver1_id], color='#00D2FF')
ax.bar(x + width/2, values2, width, label=driver_dict[driver2_id], color='#E10600')
ax.set_xticks(x)
ax.set_xticklabels(categories)
ax.set_ylabel("Count")
ax.set_title(f"{driver_dict[driver1_id]} vs {driver_dict[driver2_id]}")
legend = ax.legend(facecolor=BG_COLOR, edgecolor='white')
for text in legend.get_texts():
    text.set_color('white')
style_matplotlib_ax(fig, ax)

st.pyplot(fig)