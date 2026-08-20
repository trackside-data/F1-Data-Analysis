import streamlit as st
from datetime import datetime
import fastf1
from fastf1.ergast import Ergast
import matplotlib.pyplot as plt
import pandas as pd

fastf1.Cache.enable_cache('cache')

st.title("Qualifying vs Race Performance")
st.caption("Compares each race's starting grid position to the final classified result. Positive means the driver gained positions during the race; negative means they lost positions. Grid position 0 (pit lane start or no qualifying time) is excluded from the average, since there's no meaningful 'grid position' to compare against.")

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

current_year = datetime.now().year
years = list(range(2018, current_year + 1))
year = st.selectbox("Select a season", years, index=len(years) - 1, key="quali_year_select")

@st.cache_data(ttl=3600)
def load_season_drivers(year):
    info = ergast.get_driver_info(season=year)
    return {row['driverId']: f"{row['givenName']} {row['familyName']}" for _, row in info.iterrows()}

with st.spinner("Loading drivers..."):
    driver_dict = load_season_drivers(year)

driver_ids = sorted(driver_dict.keys(), key=lambda d: driver_dict[d])
driver_id = st.selectbox("Select a driver", driver_ids, format_func=lambda d: driver_dict[d], key="quali_driver_select")

@st.cache_data(ttl=3600)
def load_season_results(year, driver_id):
    response = ergast.get_race_results(season=year, driver=driver_id, limit=1000)
    frames = []
    for i, race_df in enumerate(response.content):
        race_df = race_df.copy()
        race_df['raceName'] = response.description.iloc[i]['raceName']
        race_df['round'] = response.description.iloc[i]['round']
        frames.append(race_df)
    if len(frames) == 0:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True).sort_values('round').reset_index(drop=True)

with st.spinner(f"Loading {driver_dict[driver_id]}'s {year} results..."):
    results = load_season_results(year, driver_id)

if len(results) == 0:
    st.write("No results found for this driver/season combination.")
else:
    results['PositionsGained'] = results['grid'] - results['position']
    valid_results = results[results['grid'] > 0].copy()

    st.subheader("Positions Gained or Lost Per Race")

    fig, ax = plt.subplots(figsize=(12, 6))
    colors = ['#00A651' if v >= 0 else '#E10600' for v in valid_results['PositionsGained']]
    ax.bar(valid_results['raceName'], valid_results['PositionsGained'], color=colors)
    ax.axhline(0, color='white', linewidth=1)
    ax.set_ylabel("Positions Gained (+) / Lost (-)")
    ax.set_title(f"{driver_dict[driver_id]} - {year}")
    plt.setp(ax.get_xticklabels(), rotation=75, ha='right')
    style_matplotlib_ax(fig, ax)
    st.pyplot(fig)

    st.subheader("Grid Position vs Finish Position")

    fig2, ax2 = plt.subplots(figsize=(8, 8))
    ax2.scatter(valid_results['grid'], valid_results['position'], color='#00D2FF', s=80, edgecolors='white', zorder=3)
    max_pos = max(valid_results['grid'].max(), valid_results['position'].max())
    ax2.plot([0, max_pos + 1], [0, max_pos + 1], color='gray', linestyle='--', label='Finished where they started')
    ax2.invert_yaxis()
    ax2.invert_xaxis()
    ax2.set_xlabel("Grid Position")
    ax2.set_ylabel("Finish Position")
    ax2.set_title(f"{driver_dict[driver_id]} - {year}")
    legend = ax2.legend(facecolor=BG_COLOR, edgecolor='white')
    for text in legend.get_texts():
        text.set_color('white')
    style_matplotlib_ax(fig2, ax2)
    st.pyplot(fig2)

    avg_gained = valid_results['PositionsGained'].mean()
    best_race = valid_results.loc[valid_results['PositionsGained'].idxmax()]
    worst_race = valid_results.loc[valid_results['PositionsGained'].idxmin()]

    st.write(f"Average positions gained per race: **{avg_gained:.1f}**")
    st.write(f"Best race: **{best_race['raceName']}** (started {int(best_race['grid'])}, finished {int(best_race['position'])}, gained {int(best_race['PositionsGained'])})")
    st.write(f"Worst race: **{worst_race['raceName']}** (started {int(worst_race['grid'])}, finished {int(worst_race['position'])}, lost {int(-worst_race['PositionsGained'])})")