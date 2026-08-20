import streamlit as st
from datetime import datetime
import fastf1
import pandas as pd

fastf1.Cache.enable_cache('cache')

st.title("Prediction Helper")
st.caption("Helps you make informed picks for race predictor games, using historical data. This isn't a guarantee of what will happen, just a data-backed starting point for your own picks.")

current_year = datetime.now().year

@st.cache_data(ttl=3600)
def load_full_schedule(year):
    schedule = fastf1.get_event_schedule(year)
    schedule = schedule[schedule['RoundNumber'] > 0]
    return schedule

schedule = load_full_schedule(current_year)

today = pd.Timestamp(datetime.now().date())
schedule_dates = schedule.copy()
schedule_dates['EventDate'] = schedule_dates['EventDate'].dt.normalize()
upcoming = schedule_dates[schedule_dates['EventDate'] >= today]

if len(upcoming) == 0:
    st.write("No upcoming races found for this season yet. Check back once the next season's schedule is released.")
else:
    next_race = upcoming.iloc[0]
    days_until = (next_race['EventDate'] - today).days
    st.subheader(f"Next race: {next_race['EventName']} ({current_year})")
    st.write(f"{next_race['EventDate'].strftime('%B %d, %Y')} — {days_until} days away")

    st.subheader("Recent Driver Form")
    st.caption("Based on each driver's average finishing position over their last 5 races, weighted so more recent races count more.")

    @st.cache_data(ttl=3600)
    def load_recent_form():
        past_races = schedule_dates[schedule_dates['EventDate'] < today].sort_values('EventDate', ascending=False)
        recent_race_names = past_races['EventName'].head(5).tolist()

        form_data = {}
        for race_index, race_name in enumerate(recent_race_names):
            weight = 5 - race_index
            try:
                race_session = fastf1.get_session(current_year, race_name, 'R')
                race_session.load(laps=False, telemetry=False, weather=False, messages=False)
                results = race_session.results[['Abbreviation', 'Position']]
                for _, row in results.iterrows():
                    driver = row['Abbreviation']
                    if driver not in form_data:
                        form_data[driver] = []
                    if pd.notna(row['Position']):
                        form_data[driver].append((row['Position'], weight))
            except Exception:
                continue

        avg_form = {}
        for driver, weighted_positions in form_data.items():
            if len(weighted_positions) > 0:
                total_weight = sum(w for p, w in weighted_positions)
                weighted_sum = sum(p * w for p, w in weighted_positions)
                avg_form[driver] = weighted_sum / total_weight

        return avg_form

    with st.spinner("Analyzing recent race results..."):
        avg_form = load_recent_form()

    if len(avg_form) == 0:
        st.write("Not enough recent race data available yet this season.")
    else:
        form_df = pd.DataFrame(list(avg_form.items()), columns=['Driver', 'Weighted Avg Finish Position'])
        form_df = form_df.sort_values('Weighted Avg Finish Position').reset_index(drop=True)
        form_df['Weighted Avg Finish Position'] = form_df['Weighted Avg Finish Position'].round(1)
        st.dataframe(form_df, hide_index=True)

    st.subheader("Recent Qualifying Pace")
    st.caption("Based on each driver's average qualifying position over their last 5 races, weighted so more recent races count more.")

    @st.cache_data(ttl=3600)
    def load_recent_qualifying():
        past_races = schedule_dates[schedule_dates['EventDate'] < today].sort_values('EventDate', ascending=False)
        recent_race_names = past_races['EventName'].head(5).tolist()

        quali_data = {}
        for race_index, race_name in enumerate(recent_race_names):
            weight = 5 - race_index
            try:
                quali_session = fastf1.get_session(current_year, race_name, 'Q')
                quali_session.load(laps=False, telemetry=False, weather=False, messages=False)
                results = quali_session.results[['Abbreviation', 'Position']]
                for _, row in results.iterrows():
                    driver = row['Abbreviation']
                    if driver not in quali_data:
                        quali_data[driver] = []
                    if pd.notna(row['Position']):
                        quali_data[driver].append((row['Position'], weight))
            except Exception:
                continue

        avg_quali = {}
        for driver, weighted_positions in quali_data.items():
            if len(weighted_positions) > 0:
                total_weight = sum(w for p, w in weighted_positions)
                weighted_sum = sum(p * w for p, w in weighted_positions)
                avg_quali[driver] = weighted_sum / total_weight

        return avg_quali

    with st.spinner("Analyzing recent qualifying results..."):
        avg_quali = load_recent_qualifying()

    if len(avg_quali) == 0:
        st.write("Not enough recent qualifying data available yet this season.")
    else:
        quali_df = pd.DataFrame(list(avg_quali.items()), columns=['Driver', 'Weighted Avg Qualifying Position'])
        quali_df = quali_df.sort_values('Weighted Avg Qualifying Position').reset_index(drop=True)
        quali_df['Weighted Avg Qualifying Position'] = quali_df['Weighted Avg Qualifying Position'].round(1)
        st.dataframe(quali_df, hide_index=True)

    st.subheader("Suggested Podium Pick")
    st.caption("Combines recent race form and recent qualifying pace into one ranking, weighted equally. This is a simple model, not a scientific prediction — use it as a starting point, not a final answer.")

    if len(avg_form) == 0 or len(avg_quali) == 0:
        st.write("Not enough data yet to generate a suggested podium.")
        sorted_drivers = []
        combined_scores = {}
    else:
        combined_drivers = set(avg_form.keys()) & set(avg_quali.keys())

        combined_scores = {}
        for driver in combined_drivers:
            combined_scores[driver] = (avg_form[driver] + avg_quali[driver]) / 2

        sorted_drivers = sorted(combined_scores.items(), key=lambda x: x[1])

        podium = sorted_drivers[:3]

        medal_labels = ["🥇 P1", "🥈 P2", "🥉 P3"]
        for i, (driver, score) in enumerate(podium):
            st.write(f"{medal_labels[i]}: **{driver}** (combined score: {score:.1f})")

        if len(sorted_drivers) > 3:
            st.write("Other strong contenders:")
            others = sorted_drivers[3:6]
            other_names = ", ".join([d for d, s in others])
            st.write(other_names)

    st.subheader("Predict a Specific Driver's Finish")
    st.caption("Shows where a specific driver ranks using the same combined score as the podium pick above. This is a relative ranking based on recent form, not a guaranteed exact position.")

    if len(sorted_drivers) == 0:
        st.write("Not enough data to predict individual driver finishes.")
    else:
        driver_options = [d for d, s in sorted_drivers]
        selected_driver = st.selectbox("Select a driver", driver_options, key="predict_driver_select")

        predicted_rank = driver_options.index(selected_driver) + 1
        selected_score = combined_scores[selected_driver]

        st.write(f"Predicted finishing position: **P{predicted_rank}** (out of {len(driver_options)} drivers with recent data)")
        st.write(f"Combined score: {selected_score:.1f}")

        if selected_driver in avg_form:
            st.write(f"Recent race form (weighted avg finish): {avg_form[selected_driver]:.1f}")
        if selected_driver in avg_quali:
            st.write(f"Recent qualifying pace (weighted avg grid position): {avg_quali[selected_driver]:.1f}")

    st.subheader("Historical Performance at This Track")
    st.caption(f"Average finishing position for each driver in past editions of the {next_race['EventName']}, going back up to 5 years. Some drivers may have limited history here if they're new, or if the track is new to the calendar.")

    @st.cache_data(ttl=3600)
    def load_track_history(event_name, current_year):
        track_data = {}
        for past_year in range(current_year - 5, current_year):
            try:
                past_session = fastf1.get_session(past_year, event_name, 'R')
                past_session.load(laps=False, telemetry=False, weather=False, messages=False)
                results = past_session.results[['Abbreviation', 'Position']]
                for _, row in results.iterrows():
                    driver = row['Abbreviation']
                    if driver not in track_data:
                        track_data[driver] = []
                    track_data[driver].append(row['Position'])
            except Exception:
                continue
        return track_data

    with st.spinner("Loading track history..."):
        track_data = load_track_history(next_race['EventName'], current_year)

    avg_track = {}
    for driver, positions in track_data.items():
        valid_positions = [p for p in positions if pd.notna(p)]
        if len(valid_positions) > 0:
            avg_track[driver] = sum(valid_positions) / len(valid_positions)

    if len(avg_track) == 0:
        st.write("No historical data available for this track yet.")
    else:
        track_df = pd.DataFrame(list(avg_track.items()), columns=['Driver', 'Avg Finish at This Track (last 5 years)'])
        track_df = track_df.sort_values('Avg Finish at This Track (last 5 years)').reset_index(drop=True)
        track_df['Avg Finish at This Track (last 5 years)'] = track_df['Avg Finish at This Track (last 5 years)'].round(1)
        st.dataframe(track_df, hide_index=True)
    st.subheader("Recent Team (Constructor) Form")
    st.caption("Average finishing position across both cars for each team, over the last 5 races, weighted so more recent races count more. This reflects the strength of the car itself, separate from individual driver skill.")

    @st.cache_data(ttl=3600)
    def load_team_form():
        past_races = schedule_dates[schedule_dates['EventDate'] < today].sort_values('EventDate', ascending=False)
        recent_race_names = past_races['EventName'].head(5).tolist()

        team_data = {}
        for race_index, race_name in enumerate(recent_race_names):
            weight = 5 - race_index
            try:
                race_session = fastf1.get_session(current_year, race_name, 'R')
                race_session.load(laps=False, telemetry=False, weather=False, messages=False)
                results = race_session.results[['TeamName', 'Position']]
                for _, row in results.iterrows():
                    team = row['TeamName']
                    if team not in team_data:
                        team_data[team] = []
                    if pd.notna(row['Position']):
                        team_data[team].append((row['Position'], weight))
            except Exception:
                continue

        avg_team = {}
        for team, weighted_positions in team_data.items():
            if len(weighted_positions) > 0:
                total_weight = sum(w for p, w in weighted_positions)
                weighted_sum = sum(p * w for p, w in weighted_positions)
                avg_team[team] = weighted_sum / total_weight

        return avg_team

    with st.spinner("Analyzing recent team performance..."):
        avg_team = load_team_form()

    if len(avg_team) == 0:
        st.write("Not enough recent team data available yet this season.")
    else:
        team_df = pd.DataFrame(list(avg_team.items()), columns=['Team', 'Weighted Avg Finish Position (Both Cars)'])
        team_df = team_df.sort_values('Weighted Avg Finish Position (Both Cars)').reset_index(drop=True)
        team_df['Weighted Avg Finish Position (Both Cars)'] = team_df['Weighted Avg Finish Position (Both Cars)'].round(1)
        st.dataframe(team_df, hide_index=True)
    st.subheader("Recent Reliability (DNF Rate)")
    st.caption("Percentage of a driver's last 5 races that ended in a DNF (did not finish), based on classification status. A high DNF rate is a real risk factor worth weighing against the other signals above.")

    @st.cache_data(ttl=3600)
    def load_reliability():
        past_races = schedule_dates[schedule_dates['EventDate'] < today].sort_values('EventDate', ascending=False)
        recent_race_names = past_races['EventName'].head(5).tolist()

        reliability_data = {}
        for race_name in recent_race_names:
            try:
                race_session = fastf1.get_session(current_year, race_name, 'R')
                race_session.load(laps=False, telemetry=False, weather=False, messages=False)
                results = race_session.results[['Abbreviation', 'Status']]
                for _, row in results.iterrows():
                    driver = row['Abbreviation']
                    if driver not in reliability_data:
                        reliability_data[driver] = []
                    status = str(row['Status'])
                    finished = status == 'Finished' or status.startswith('+')
                    reliability_data[driver].append(finished)
            except Exception:
                continue

        dnf_rate = {}
        for driver, finish_flags in reliability_data.items():
            if len(finish_flags) > 0:
                dnfs = sum(1 for f in finish_flags if not f)
                dnf_rate[driver] = (dnfs / len(finish_flags)) * 100

        return dnf_rate

    with st.spinner("Analyzing recent reliability..."):
        dnf_rate = load_reliability()

    if len(dnf_rate) == 0:
        st.write("Not enough recent race data available yet this season.")
    else:
        dnf_df = pd.DataFrame(list(dnf_rate.items()), columns=['Driver', 'DNF Rate (last 5 races, %)'])
        dnf_df = dnf_df.sort_values('DNF Rate (last 5 races, %)').reset_index(drop=True)
        dnf_df['DNF Rate (last 5 races, %)'] = dnf_df['DNF Rate (last 5 races, %)'].round(0)
        st.dataframe(dnf_df, hide_index=True)