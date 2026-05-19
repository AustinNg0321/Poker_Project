import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, root_mean_squared_error
import os

def train():
    # File paths
    base_dir = os.path.dirname(__file__)
    data_path = os.path.join(base_dir, 'training_data_v2_1.csv')
    
    # Load data
    print(f"Loading data from {data_path}...")
    df = pd.read_csv(data_path)

    # Drop target/irrelevant columns from features
    cols_to_drop = ['game_id', 'decision', 'game_won', 'final_player_rank', 'final_dealer_rank', 'move_num']
    X = df.drop(columns=[col for col in cols_to_drop if col in df.columns])
    
    y_player = df['final_player_rank']
    y_dealer = df['final_dealer_rank']

    print("Splitting data...")
    X_train, X_test, y_player_train, y_player_test, y_dealer_train, y_dealer_test = train_test_split(
        X, y_player, y_dealer, test_size=0.2, random_state=42
    )

    # Train player rank model
    print("Training Player Rank Model...")
    player_model = xgb.XGBRegressor(
        objective='reg:squarederror',
        n_estimators=1000,
        learning_rate=0.05,
        max_depth=6,
        early_stopping_rounds=50,
        random_state=42,
        eval_metric='rmse'
    )
    player_model.fit(
        X_train, y_player_train,
        eval_set=[(X_test, y_player_test)],
        verbose=100
    )

    # Train dealer rank model
    print("Training Dealer Rank Model...")
    dealer_model = xgb.XGBRegressor(
        objective='reg:squarederror',
        n_estimators=1000,
        learning_rate=0.05,
        max_depth=6,
        early_stopping_rounds=50,
        random_state=42,
        eval_metric='rmse'
    )
    dealer_model.fit(
        X_train, y_dealer_train,
        eval_set=[(X_test, y_dealer_test)],
        verbose=100
    )

    # Evaluation
    print("\n--- Validation Metrics ---")
    player_preds = player_model.predict(X_test)
    dealer_preds = dealer_model.predict(X_test)
    
    print("Player Rank Model:")
    print(f"  RMSE: {root_mean_squared_error(y_player_test, player_preds):.4f}")
    print(f"  MAE:  {mean_absolute_error(y_player_test, player_preds):.4f}")

    print("Dealer Rank Model:")
    print(f"  RMSE: {root_mean_squared_error(y_dealer_test, dealer_preds):.4f}")
    print(f"  MAE:  {mean_absolute_error(y_dealer_test, dealer_preds):.4f}")

    player_model_path = os.path.join(base_dir, 'player_rank_model_v2_1.json')
    dealer_model_path = os.path.join(base_dir, 'dealer_rank_model_v2_1.json')
    
    print(f"\nSaving models to {player_model_path} and {dealer_model_path}...")
    player_model.save_model(player_model_path)
    dealer_model.save_model(dealer_model_path)
    print("Done.")

if __name__ == '__main__':
    train()
