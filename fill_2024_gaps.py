import fastf1
import pandas as pd
import os
import itertools

fastf1.Cache.enable_cache('cache')

def get_minisector_comparison(tel1, driver1, tel2, driver2):
    num_minisectors = 25
    total_distance = tel1['Distance'].max()
    minisector_length = total_distance / num_minisectors

    tel1 = tel1.copy()
    tel2 = tel2.copy()
    tel1['Minisector'] = (tel1['Distance'] // minisector_length).astype(int)
    tel2['Minisector'] = (tel2['Distance'] // minisector_length).astype(int)

    avg_speed1 = tel1.groupby('Minisector')['Speed'].mean()
    avg_speed2 = tel2.groupby('Minisector')['Speed'].mean()

    comparison = pd.DataFrame({driver1: avg_speed1, driver2: avg_speed2})
    comparison['Fastest'] = comparison.idxmax(axis=1)

    tel1['Fastest'] = tel1['Minisector'].map(comparison['Fastest'])
    return tel1, comparison

def process_race(year, race_name):
    print(f"Reprocessing {year} {race_name}...")
    try:
        session = fastf1.get_session(year, race_name, 'R')
        session.load(telemetry=True, weather=False, messages=False)
    except Exception as e:
        print(f"  Could not load session: {e}")
        return

    podium = session.results.sort_values('Position').head(3)['Abbreviation'].tolist()

    telemetry_cache = {}
    for drv in podium:
        try:
            lap = session.laps.pick_drivers(drv).pick_fastest()
            telemetry_cache[drv] = lap.get_telemetry().add_distance()
        except Exception:
            print(f"  Skipping {drv}, no valid lap data")

    race_clean = race_name.replace(' ', '_').replace('Grand_Prix', '').strip('_')

    for driver1, driver2 in itertools.combinations(telemetry_cache.keys(), 2):
        try:
            tel1, comparison = get_minisector_comparison(
                telemetry_cache[driver1], driver1,
                telemetry_cache[driver2], driver2
            )
            output = tel1[['X', 'Y', 'Minisector', 'Fastest']].copy()
            base_name = f"precomputed_data/{year}_{race_clean}_{driver1}_vs_{driver2}"

            reverse_base = f"precomputed_data/{year}_{race_clean}_{driver2}_vs_{driver1}"
            if os.path.exists(f"{reverse_base}.csv"):
                print(f"  {driver1} vs {driver2} already covered (as {driver2} vs {driver1})")
                continue
            if os.path.exists(f"{base_name}.csv"):
                print(f"  {driver1} vs {driver2} already covered")
                continue

            output.to_csv(f"{base_name}.csv", index=False)
            comparison.to_csv(f"{base_name}_speeds.csv")
            print(f"  Saved {driver1} vs {driver2}")
        except Exception as e:
            print(f"  Failed {driver1} vs {driver2}: {e}")

races_to_fill = [
    (2024, 'Bahrain Grand Prix'),
    (2024, 'Monaco Grand Prix'),
    (2024, 'British Grand Prix'),
    (2024, 'Italian Grand Prix'),
    (2024, 'Abu Dhabi Grand Prix'),
]

for year, race_name in races_to_fill:
    process_race(year, race_name)