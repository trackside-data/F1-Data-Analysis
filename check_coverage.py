import fastf1
import os

fastf1.Cache.enable_cache('cache')

years_to_check = [2021, 2024, 2025, 2026]

for year in years_to_check:
    print(f"\n=== {year} ===")
    try:
        schedule = fastf1.get_event_schedule(year)
        schedule = schedule[schedule['RoundNumber'] > 0]
        race_list = schedule['EventName'].tolist()
    except Exception as e:
        print(f"Could not load schedule: {e}")
        continue

    for race_name in race_list:
        race_clean = race_name.replace(' ', '_').replace('Grand_Prix', '').strip('_')
        prefix = f"{year}_{race_clean}"

        matching_files = [f for f in os.listdir('precomputed_data') if f.startswith(prefix)]
        pair_files = [f for f in matching_files if not f.endswith('_speeds.csv')]

        if len(pair_files) == 0:
            print(f"  MISSING ENTIRELY: {race_name}")
        elif len(pair_files) < 3:
            print(f"  PARTIAL ({len(pair_files)}/3 pairs): {race_name}")
        