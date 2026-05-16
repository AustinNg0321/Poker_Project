import pandas as pd
for f in ['v_1_1_p07_1.csv', 'v_1_1_p08_1.csv', 'v_1_1_p09_1.csv']:
    df = pd.read_csv(f)
    print(f"--- {f} ---")
    print("Number of games:", df['Result'].value_counts())
    print("Number of wins:", df['Result'].sum())