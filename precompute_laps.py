import fastf1
import os

fastf1.Cache.enable_cache('cache')
os.makedirs('precomputed_laps', exist_ok=True)

years_to_process = [2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026]

def process_race(year, race_name):
    race_clean = race_name.replace(' ', '_').replace('Grand_Prix', '').strip('_')
    filename = f"precomputed_laps/{year}_{race_clean}_laps.csv"

    if os.path.exists(filename):
        return

    print(f"Processing {year} {race_name}...")
    try:
        session = fastf1.get_session(year, race_name, 'R')
        session.load(telemetry=False, weather=False, messages=False)
        session.laps.to_csv(filename, index=False)
        print(f"  Saved {filename}")
    except Exception as e:
        print(f"  Could not load session: {e}")

for year in years_to_process:
    try:
        schedule = fastf1.get_event_schedule(year)
        schedule = schedule[schedule['RoundNumber'] > 0]
        race_list = schedule['EventName'].tolist()
    except Exception as e:
        print(f"Could not load schedule for {year}: {e}")
        continue

    for race_name in race_list:
        process_race(year, race_name)