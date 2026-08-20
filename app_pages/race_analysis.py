import streamlit as st
from datetime import datetime
import os
import fastf1
import matplotlib.pyplot as plt
import plotly.graph_objects as go
import pandas as pd
import decimal

os.makedirs('cache', exist_ok=True)
fastf1.Cache.enable_cache('cache')

st.title("F1 Driver Season Performance Dashboard")

current_year = datetime.now().year
years = list(range(2018, current_year + 1))

year = st.sidebar.selectbox("Select a year", years, index=len(years) - 1, key="race_year_select")

@st.cache_data
def load_schedule(year):
    schedule = fastf1.get_event_schedule(year)
    schedule = schedule[schedule['RoundNumber'] > 0]
    return schedule['EventName'].tolist()

race_names = load_schedule(year)

race = st.sidebar.selectbox("Select a race", race_names, key="race_race_select")

@st.cache_data
def load_drivers(year, race):
    session = fastf1.get_session(year, race, 'R')
    session.load(laps=False, telemetry=False, weather=False, messages=False)
    drivers = session.results['Abbreviation'].tolist()
    return drivers

with st.spinner(f"Loading drivers for {race} {year}..."):
    try:
        driver_list = load_drivers(year, race)
    except Exception:
        st.error("Data couldn't be loaded for this selection right now. This can happen on first load — try refreshing the page or picking a different race.")
        st.stop()

driver = st.sidebar.selectbox("Select a driver", driver_list, key="race_driver_select")

@st.cache_data
def load_laps(year, race, driver):
    session = fastf1.get_session(year, race, 'R')
    session.load(telemetry=False, weather=False, messages=False)
    laps = session.laps.pick_drivers(driver)
    return laps

with st.spinner(f"Loading lap times for {driver}..."):
    try:
        laps = load_laps(year, race, driver)
    except Exception:
        st.error("Data couldn't be loaded for this selection right now. This can happen on first load — try refreshing the page or picking a different driver/race.")
        st.stop()

compound_colors = {
    'HYPERSOFT': '#FF1493',
    'ULTRASOFT': '#9400D3',
    'SUPERSOFT': '#FF4500',
    'SOFT': '#E10600',
    'MEDIUM': '#FFD700',
    'HARD': '#FFFFFF',
    'INTERMEDIATE': '#00A651',
    'WET': '#0090FF'
}

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

def round_half_up(value, decimals=1):
    if pd.isna(value):
        return value
    d = decimal.Decimal(str(value))
    return float(d.quantize(decimal.Decimal('1.' + '0' * decimals), rounding=decimal.ROUND_HALF_UP))

tab1, tab2, tab3, tab4 = st.tabs(["Lap Times & Tires", "Pit Stop Time Loss", "Track Dominance Map", "Gap to Leader"])

with tab1:
    laps = laps.dropna(subset=['Compound', 'Stint'])

    fig, ax = plt.subplots(figsize=(12, 6))

    for stint_number in laps['Stint'].unique():
        stint_laps = laps[laps['Stint'] == stint_number]
        compound = stint_laps['Compound'].iloc[0]
        color = compound_colors.get(compound, 'gray')
        ax.plot(
            stint_laps['LapNumber'],
            stint_laps['LapTime'].dt.total_seconds(),
            color=color,
            marker='o',
            label=compound,
            markeredgecolor='white',
            markeredgewidth=0.5
        )

    ax.set_xlabel("Lap Number")
    ax.set_ylabel("Lap Time (seconds)")
    ax.set_title(f"{driver} Lap Times by Tire Compound - {race} {year}")

    handles, labels = ax.get_legend_handles_labels()
    by_label = dict(zip(labels, handles))
    legend = ax.legend(by_label.values(), by_label.keys(), facecolor=BG_COLOR, edgecolor='white')
    for text in legend.get_texts():
        text.set_color('white')

    style_matplotlib_ax(fig, ax)

    st.pyplot(fig)

with tab2:
    st.caption("Estimated by comparing pit in/out laps to the driver's average race pace. This is an approximation — it doesn't isolate the exact stationary time in the pit box from factors like traffic, fuel load, or Safety Car/VSC periods overlapping with the stop.")

    normal_pace_laps = laps.pick_quicklaps()
    normal_pace = normal_pace_laps['LapTime'].dt.total_seconds().mean()

    pit_laps = laps[laps['PitInTime'].notna() | laps['PitOutTime'].notna()].copy()

    if len(pit_laps) > 0:
        pit_laps['LapTimeSeconds'] = pit_laps['LapTime'].dt.total_seconds()
        pit_laps['TimeLost'] = pit_laps['LapTimeSeconds'] - normal_pace

        status_labels = {
            '1': 'Green',
            '2': 'Yellow Flag',
            '4': 'Safety Car',
            '5': 'Red Flag',
            '6': 'VSC',
            '7': 'VSC Ending'
        }

        def describe_conditions(track_status):
            if pd.isna(track_status) or track_status == '':
                return 'Unknown'
            codes = set(str(track_status))
            labels = [status_labels.get(code, f'Code {code}') for code in codes if code in status_labels and code != '1']
            if len(labels) == 0:
                return 'Green'
            return ', '.join(labels)

        pit_laps['Conditions'] = pit_laps['TrackStatus'].apply(describe_conditions)

        pit_laps['Status'] = pit_laps['LapTimeSeconds'].apply(
            lambda x: 'Completed' if pd.notna(x) else 'No lap time recorded (likely retirement)'
        )

        pit_laps['Reliable'] = pit_laps['Conditions'] == 'Green'

        display_table = pit_laps[['LapNumber', 'LapTimeSeconds', 'TimeLost', 'Status', 'Conditions']].copy()
        display_table = display_table.sort_values('LapNumber').reset_index(drop=True)
        display_table.columns = ['Lap Number', 'Lap Time (s)', 'Time Lost vs Normal Pace (s)', 'Status', 'Track Conditions']

        display_table['Lap Time (s)'] = display_table['Lap Time (s)'].apply(round_half_up).apply(lambda x: f"{x:.1f}" if pd.notna(x) else "—")
        display_table['Time Lost vs Normal Pace (s)'] = display_table['Time Lost vs Normal Pace (s)'].apply(round_half_up).apply(lambda x: f"{x:.1f}" if pd.notna(x) else "—")

        st.write(f"{driver}'s normal race pace: {normal_pace:.1f} seconds/lap")
        st.dataframe(display_table, hide_index=True)

        reliable_laps = pit_laps[pit_laps['Reliable']]
        affected_laps = pit_laps[~pit_laps['Reliable']]

        if len(reliable_laps) > 0:
            st.write(f"Estimated time lost to pit stops under normal conditions: {round_half_up(reliable_laps['TimeLost'].sum()):.1f} seconds")
        if len(affected_laps) > 0:
            st.caption(f"{len(affected_laps)} pit-related lap(s) occurred under Yellow Flag, Safety Car, or VSC conditions and were excluded from the total above, since their lap times reflect those conditions rather than the stop itself.")
    else:
        st.write(f"No pit stops detected for {driver} in this race.")

with tab3:
    driver2_options = [d for d in driver_list if d != driver]

    if len(driver2_options) > 0:
        driver2 = st.selectbox("Compare against", driver2_options, key="race_driver2_select")

        @st.cache_data
        def load_telemetry_comparison(year, race, driver1, driver2):
            session = fastf1.get_session(year, race, 'R')
            session.load(telemetry=True, weather=False, messages=False)

            lap1 = session.laps.pick_drivers(driver1).pick_fastest()
            lap2 = session.laps.pick_drivers(driver2).pick_fastest()

            tel1 = lap1.get_telemetry().add_distance()
            tel2 = lap2.get_telemetry().add_distance()

            num_minisectors = 25
            total_distance = tel1['Distance'].max()
            minisector_length = total_distance / num_minisectors

            tel1['Minisector'] = (tel1['Distance'] // minisector_length).astype(int)
            tel2['Minisector'] = (tel2['Distance'] // minisector_length).astype(int)

            avg_speed1 = tel1.groupby('Minisector')['Speed'].mean()
            avg_speed2 = tel2.groupby('Minisector')['Speed'].mean()

            comparison = pd.DataFrame({
                driver1: avg_speed1,
                driver2: avg_speed2
            })
            comparison['Fastest'] = comparison.idxmax(axis=1)

            tel1['Fastest'] = tel1['Minisector'].map(comparison['Fastest'])

            return tel1, comparison

        try:
            with st.spinner(f"Loading telemetry for {driver} vs {driver2}..."):
                tel1, comparison = load_telemetry_comparison(year, race, driver, driver2)

            fig2 = go.Figure()
            colors = {driver: '#00D2FF', driver2: '#E10600'}

            for minisector_num in sorted(tel1['Minisector'].unique()):
                segment = tel1[tel1['Minisector'] == minisector_num]
                fastest_driver = comparison.loc[minisector_num, 'Fastest']
                speed1 = comparison.loc[minisector_num, driver]
                speed2 = comparison.loc[minisector_num, driver2]

                hover_text = (
                    f"Minisector {minisector_num}<br>"
                    f"Fastest: {fastest_driver}<br>"
                    f"{driver}: {speed1:.1f} km/h<br>"
                    f"{driver2}: {speed2:.1f} km/h"
                )

                fig2.add_trace(go.Scatter(
                    x=segment['X'],
                    y=segment['Y'],
                    mode='lines',
                    line=dict(color=colors[fastest_driver], width=4),
                    showlegend=False,
                    hovertext=hover_text,
                    hoverinfo='text'
                ))

            for driver_name, color in colors.items():
                fig2.add_trace(go.Scatter(
                    x=[None], y=[None],
                    mode='lines',
                    line=dict(color=color, width=4),
                    name=driver_name
                ))

            fig2.update_layout(
                template='plotly_dark',
                paper_bgcolor=BG_COLOR,
                plot_bgcolor=BG_COLOR,
                title=f"Track Dominance: {driver} vs {driver2} - {race} {year}",
                xaxis_title="X position",
                yaxis_title="Y position",
                yaxis_scaleanchor="x"
            )

            st.plotly_chart(fig2)
        except Exception:
            st.write("Telemetry data isn't available for this race/driver combination. Try a different race or driver pair.")
    else:
        st.write("Need at least two drivers in this race to compare.")

with tab4:
    st.caption("Approximate — calculated by comparing cumulative race time per lap. May be slightly inaccurate for laps involving lapped traffic.")

    @st.cache_data
    def load_all_laps(year, race):
        session = fastf1.get_session(year, race, 'R')
        session.load(telemetry=False, weather=False, messages=False)
        return session.laps

    with st.spinner("Loading full race data for gap comparison..."):
        try:
            all_laps = load_all_laps(year, race)
        except Exception:
            st.error("Data couldn't be loaded for this selection right now. Try refreshing the page.")
            st.stop()

    @st.cache_data
    def get_race_winner(year, race):
        session = fastf1.get_session(year, race, 'R')
        session.load(laps=False, telemetry=False, weather=False, messages=False)
        winner = session.results[session.results['Position'] == 1]['Abbreviation'].iloc[0]
        return winner

    race_winner = get_race_winner(year, race)

    leader_times = all_laps[all_laps['Driver'] == race_winner].set_index('LapNumber')['Time']

    def calculate_gap(driver_code):
        driver_laps_all = all_laps[all_laps['Driver'] == driver_code].set_index('LapNumber')['Time']
        gap_seconds = (driver_laps_all - leader_times.reindex(driver_laps_all.index)).dt.total_seconds()
        return pd.DataFrame({
            'LapNumber': gap_seconds.index,
            'Gap': gap_seconds.values
        }).dropna()

    if driver == race_winner:
        st.write(f"{driver} won this race, so their gap to the winner is zero throughout.")

    gap_df = calculate_gap(driver)

    fig3, ax3 = plt.subplots(figsize=(12, 5))
    ax3.plot(gap_df['LapNumber'], gap_df['Gap'], color='#00D2FF', marker='o', markersize=3, label=driver)

    if 'driver2' in locals():
        gap_df2 = calculate_gap(driver2)
        ax3.plot(gap_df2['LapNumber'], gap_df2['Gap'], color='#E10600', marker='o', markersize=3, label=driver2)

    if 'pit_laps' in locals() and len(pit_laps) > 0:
        pit_in_laps = pit_laps[pit_laps['PitInTime'].notna()]
        pit_lap_numbers = pit_in_laps['LapNumber'].unique()
        pit_gap_points = gap_df[gap_df['LapNumber'].isin(pit_lap_numbers)]
        ax3.scatter(pit_gap_points['LapNumber'], pit_gap_points['Gap'], color='yellow', s=120, marker='v', zorder=5, label=f'{driver} pit stop')

    ax3.set_xlabel("Lap Number")
    ax3.set_ylabel("Gap to Leader (seconds)")
    ax3.set_title(f"Gap to {race_winner} (Race Winner) - {race} {year}")
    legend3 = ax3.legend(facecolor=BG_COLOR, edgecolor='white')
    for text in legend3.get_texts():
        text.set_color('white')
    style_matplotlib_ax(fig3, ax3)

    st.pyplot(fig3)