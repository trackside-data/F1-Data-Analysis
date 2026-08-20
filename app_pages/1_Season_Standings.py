import streamlit as st
from datetime import datetime
import fastf1
from fastf1.ergast import Ergast
import matplotlib.pyplot as plt
import pandas as pd

fastf1.Cache.enable_cache('cache')

st.title("Season Standings & Schedule")

current_year = datetime.now().year
years = list(range(2018, current_year + 1))
year = st.selectbox("Select a season", years, index=len(years) - 1, key="standings_year_select")

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

official_team_names = {
    'Alpine F1 Team': 'BWT Alpine Formula One Team',
    'Aston Martin': 'Aston Martin Aramco Formula One Team',
    'Audi': 'Audi Revolut F1 Team',
    'Sauber': 'Audi Revolut F1 Team',
    'Cadillac': 'Cadillac Formula 1 Team',
    'Ferrari': 'Scuderia Ferrari HP',
    'Haas F1 Team': 'TGR Haas F1 Team',
    'McLaren': 'McLaren Mastercard F1 Team',
    'Mercedes': 'Mercedes-AMG PETRONAS Formula One Team',
    'RB F1 Team': 'Visa Cash App Racing Bulls Formula One Team',
    'Racing Bulls': 'Visa Cash App Racing Bulls Formula One Team',
    'Red Bull': 'Oracle Red Bull Racing',
    'Williams': 'Atlassian Williams F1 Team',
}

@st.cache_data(ttl=3600)
def load_driver_standings(year):
    standings = ergast.get_driver_standings(season=year)
    return standings.content[0]

@st.cache_data(ttl=3600)
def load_constructor_standings(year):
    standings = ergast.get_constructor_standings(season=year)
    return standings.content[0]

st.subheader("Driver Standings")

with st.spinner("Loading driver standings..."):
    driver_standings = load_driver_standings(year)

driver_table = driver_standings.copy()
driver_table['Driver'] = driver_table['givenName'] + ' ' + driver_table['familyName']
driver_table['Team'] = driver_table['constructorNames'].apply(
    lambda teams: teams[0] if isinstance(teams, list) and len(teams) > 0 else 'Unknown'
)
driver_table['Team'] = driver_table['Team'].replace(official_team_names)
driver_table = driver_table[['position', 'Driver', 'Team', 'points', 'wins']]
driver_table.columns = ['Position', 'Driver', 'Team', 'Points', 'Wins']

st.dataframe(driver_table, hide_index=True)

fig, ax = plt.subplots(figsize=(10, 6))
top_10 = driver_table.head(10)
ax.barh(top_10['Driver'], top_10['Points'], color='#00D2FF')
ax.invert_yaxis()
ax.set_xlabel("Points")
ax.set_title(f"Top 10 Drivers - {year}")
style_matplotlib_ax(fig, ax)
st.pyplot(fig)

st.subheader("Constructor Standings")

with st.spinner("Loading constructor standings..."):
    constructor_standings = load_constructor_standings(year)

constructor_table = constructor_standings[['position', 'constructorName', 'points', 'wins']].copy()
constructor_table.columns = ['Position', 'Constructor', 'Points', 'Wins']
constructor_table['ShortName'] = constructor_table['Constructor']
constructor_table['Constructor'] = constructor_table['Constructor'].replace(official_team_names)

st.dataframe(constructor_table[['Position', 'Constructor', 'Points', 'Wins']], hide_index=True)

fig2, ax2 = plt.subplots(figsize=(10, 6))
ax2.barh(constructor_table['ShortName'], constructor_table['Points'], color='#E10600')
ax2.invert_yaxis()
ax2.set_xlabel("Points")
ax2.set_title(f"Constructor Standings - {year}")
style_matplotlib_ax(fig2, ax2)
st.pyplot(fig2)

st.subheader("Season Schedule")

@st.cache_data
def load_full_schedule(year):
    schedule = fastf1.get_event_schedule(year)
    schedule = schedule[schedule['RoundNumber'] > 0]
    return schedule

schedule = load_full_schedule(year)

today = pd.Timestamp(datetime.now().date())
schedule_dates = schedule.copy()
schedule_dates['EventDate'] = schedule_dates['EventDate'].dt.normalize()
upcoming = schedule_dates[schedule_dates['EventDate'] >= today]

if len(upcoming) > 0:
    next_race = upcoming.iloc[0]
    days_until = (next_race['EventDate'] - today).days
    st.write(f"Next race: **{next_race['EventName']}** on {next_race['EventDate'].strftime('%B %d, %Y')} ({days_until} days away)")
else:
    st.write("No more races scheduled this season, or you're viewing a past season.")

schedule_display = schedule[['RoundNumber', 'EventName', 'Country', 'EventDate']].copy()
schedule_display.columns = ['Round', 'Grand Prix', 'Country', 'Date']
schedule_display['Date'] = schedule_display['Date'].dt.strftime('%B %d, %Y')
st.dataframe(schedule_display, hide_index=True)