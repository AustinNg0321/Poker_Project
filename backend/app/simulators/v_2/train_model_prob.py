import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import root_mean_squared_error
import os

def train():
    base_dir = os.path.dirname(__file__)
    data_path = os.path.join(base_dir, 'training_data_v2_1.csv')
    
    print(f"Loading data from {data_path}...")
    df = pd.read_csv(data_path)

    # Drop target/irrelevant columns from features
    cols_to_drop = ['game_id', 'decision', 'final_player_rank', 'final_dealer_rank', 'move_num', 'game_won']
    X = df.drop(columns=[col for col in cols_to_drop if col in df.columns])
    
    # Target is the boolean win state, regress on it for probability
    y = df['game_won']

    print("Splitting data...")
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    print("Training Probability Model...")
    model = xgb.XGBRegressor(
        objective='reg:logistic',
        n_estimators=1000,
        learning_rate=0.05,
        max_depth=6,
        early_stopping_rounds=50,
        random_state=42,
        eval_metric='rmse'
    )
    model.fit(
        X_train, y_train,
        eval_set=[(X_test, y_test)],
        verbose=100
    )

    # Evaluation
    print("\n--- Validation Metrics ---")
    preds = model.predict(X_test)
    
    print("Probability Model:")
    print(f"  RMSE: {root_mean_squared_error(y_test, preds):.4f}")

    model_path = os.path.join(base_dir, 'player_prob_model_v2_1.json')
    print(f"\nSaving model to {model_path}...")
    model.save_model(model_path)
    print("Done.")

if __name__ == '__main__':
    train()
