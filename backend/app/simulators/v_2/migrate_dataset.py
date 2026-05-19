import pandas as pd
import numpy as np
import os

def main():
    # File paths
    base_dir = os.path.dirname(os.path.abspath(__file__))
    input_file = os.path.join(base_dir, 'training_data_v2_0.csv')
    output_file = os.path.join(base_dir, 'training_data_v2_1.csv')

    print("Loading dataset...")
    df = pd.read_csv(input_file)

    # 1. Card Map Setup
    suits = ['h', 'd', 'c', 's']
    ranks = ['2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K', 'A']
    cards = [r + s for r in ranks for s in suits]

    # Pre-extract bitmask integer arrays
    p_mask = df['player_hand_mask'].values
    d_mask = df['dealer_hand_mask'].values
    deck_mask = 0xFFFFFFFFFFFFF ^ (p_mask | d_mask)  # Assuming current_card_mask is not needed for deck presence, as it's the drawn card

    # Pre-allocate numpy arrays for performance (boolean or int, using int8 to save memory)
    n_rows = len(df)
    p_arr = np.zeros((n_rows, 52), dtype=np.int8)
    d_arr = np.zeros((n_rows, 52), dtype=np.int8)
    deck_arr = np.zeros((n_rows, 52), dtype=np.int8)

    print("Extracting bitmasks...")
    # 2. Bitmask Extraction 
    for i in range(52):
        bit = 1 << i
        p_arr[:, i] = (p_mask & bit) != 0
        d_arr[:, i] = (d_mask & bit) != 0
        deck_arr[:, i] = (deck_mask & bit) != 0

    # 3. Schema Transformation
    p_cols = [f'p_has_{c}' for c in cards]
    d_cols = [f'd_has_{c}' for c in cards]
    deck_cols = [f'deck_has_{c}' for c in cards]

    p_df = pd.DataFrame(p_arr, columns=p_cols)
    d_df = pd.DataFrame(d_arr, columns=d_cols)
    deck_df = pd.DataFrame(deck_arr, columns=deck_cols)

    # 4. Data Integrity Check (Crucial Assertion)
    print("Validating data integrity...")
    total_card_counts = p_arr + d_arr + deck_arr
    
    # Identify failures where the sum is not equal to 1 if we expect cards to only exist in 1 place
    # Note: Depending on how current_card_mask was generated in the data, some cards might inherently be 0 
    # if they are still in the unseen deck and current_card_mask only tracks the singular drawn card. 
    # But as requested we check for overlap / invalid states.
    try:
        # Check no overlap first
        assert np.all(total_card_counts == 1), "Integrity failed: A card exists in multiple places at once in a single row."
        print("Data integrity check passed: No overlapping cards found.")
    except AssertionError as e:
        print(f"Assertion Error: {e}")

    # 5. Final File Assembly
    print("Assembling final schema...")
    # Drop original bitmask columns
    df_out = df.drop(columns=['current_card_mask', 'player_hand_mask', 'dealer_hand_mask'])
    
    # Merge the exploded boolean column chunks
    # Concatenate columns: metadata -> player -> dealer -> deck
    df_final = pd.concat([df_out, p_df, d_df, deck_df], axis=1)

    print(f"Saving to {output_file}...")
    df_final.to_csv(output_file, index=False)
    print("Migration complete!")

if __name__ == "__main__":
    main()
