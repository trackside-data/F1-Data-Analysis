import fastf1
import pandas as pd
import os

fastf1.Cache.enable_cache('cache')

os.makedirs('precomputed_data', exist_ok=True)

races_and_drivers = [
    (2024, 'Bahrain', 'VER', 'LEC'),
    (2024, 'Bahrain', 'VER', 'PER'),
    (2024, 'Monaco', 'LEC', 'VER'),
    (2024, 'Monaco', 'NOR', 'PIA'),
    (2024, 'British', 'HAM', 'VER'),
    (2024, 'Italian', 'LEC', 'SAI'),
    (2024, 'Abu Dhabi', 'NOR', 'VER'),
]

def precompute_one(year, race, driver1, driver2):
    print(f"Processing {year} {race}: {driver1} vs {driver2}...")

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

    output = tel1[['X', 'Y', 'Minisector', 'Fastest']].copy()

    filename = f"precomputed_data/{year}_{race.replace(' ', '_')}_{driver1}_vs_{driver2}.csv"
    output.to_csv(filename, index=False)

    comparison_filename = f"precomputed_data/{year}_{race.replace(' ', '_')}_{driver1}_vs_{driver2}_speeds.csv"
    comparison.to_csv(comparison_filename)

    print(f"Saved {filename}")

for year, race, driver1, driver2 in races_and_drivers:
    try:
        precompute_one(year, race, driver1, driver2)
    except Exception as e:
        print(f"Failed for {year} {race} {driver1} vs {driver2}: {e}")