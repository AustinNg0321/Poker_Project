import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, mean_absolute_error
import os

def train():
    # File paths
    base_dir = os.path.dirname(__file__)
    data_path = os.path.join(base_dir, 'training_data_v2.csv')
    model_path = os.path.join(base_dir, 'poker_bot_regressor_0.json')

    # Load data
    print("Loading data...")
    df = pd.read_csv(data_path)

    # Drop metadata
    if 'game_id' in df.columns:
        df = df.drop(columns=['game_id'])

    # --- CRITICAL FIX: Drop Future Target Leaks and Decision ---
    # We remove 'decision' because we are predicting game outcome, not player choices.
    # We remove game metadata and future variables that the bot won't see mid-game.
    cols_to_drop = [
        'decision', 'final_player_rank', 'final_dealer_rank', 'move_num', "game_won", "current_card_mask",
        #"current_player_rank_score", "current_dealer_rank_score"
    ]
    
    X = df.drop(columns=[col for col in cols_to_drop if col in df.columns])
    y = df['game_won']  # Target is now actual game outcome (1 for win, 0 for loss)

    # Stratified Train/Test split (maintains consistent win/loss distributions)
    print("Splitting data...")
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    # Initialize XGBoost Regressor
    print("Initializing model...")
    model = xgb.XGBRegressor(
        objective='binary:logistic',
        max_depth=5,            # <-- Lowered from 8 to prevent overfitting
        learning_rate=0.05,     # <-- Dropped from 0.1 for a more careful, precise gradient descent
        n_estimators=1000,       # <-- Bumped up because a smaller learning rate needs more rounds
        eval_metric='logloss',
        random_state=42,
        early_stopping_rounds=20 # <-- Slightly extended to give the slower learning rate room to breathe
    )

    # Train model
    print("Training model...")
    model.fit(
        X_train, y_train,
        eval_set=[(X_test, y_test)],
        verbose=20
    )

    # Evaluation
    print("\n--- Evaluation Metrics ---")
    y_train_pred = model.predict(X_train)
    y_test_pred = model.predict(X_test)

    # Compute Regression Error metrics
    train_rmse = np.sqrt(mean_squared_error(y_train, y_train_pred))
    test_rmse = np.sqrt(mean_squared_error(y_test, y_test_pred))
    test_mae = mean_absolute_error(y_test, y_test_pred)

    print(f"Train RMSE (Avg probability deviation): {train_rmse:.4f}")
    print(f"Test RMSE (Avg probability deviation):  {test_rmse:.4f}")
    print(f"Test MAE (Mean Absolute Error):         {test_mae:.4f}\n")

    # Feature Importance
    print("--- Top 5 Important Features ---")
    importance = model.feature_importances_
    features = X.columns
    sorted_idx = np.argsort(importance)[::-1]
    
    for i in range(min(5, len(features))):
        print(f"{i+1}. {features[sorted_idx[i]]}: {importance[sorted_idx[i]]:.4f}")

    # Save Model
    print(f"\nSaving model to {model_path}...")
    model.save_model(model_path)
    print("Training complete and model saved.")

if __name__ == '__main__':
    train()