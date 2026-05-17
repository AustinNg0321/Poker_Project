import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score
import os

def train():
    # File paths
    base_dir = os.path.dirname(__file__)
    data_path = os.path.join(base_dir, 'training_data_v2.csv')
    model_path = os.path.join(base_dir, 'poker_bot_v2_0.json')

    # Load data
    print("Loading data...")
    df = pd.read_csv(data_path)

    # Drop metadata
    if 'game_id' in df.columns:
        df = df.drop(columns=['game_id'])

    # --- CRITICAL FIX: Drop Future Target Leaks ---
    # We remove 'decision' because it's our target.
    # We remove 'final_player_rank', 'final_dealer_rank', and 'game_won' 
    # because the bot won't know these values during live gameplay!
    cols_to_drop = cols_to_drop = [
    'decision', 'final_player_rank', 'final_dealer_rank', 'game_won',
    'move_num', 'dealer_card_count', 'player_card_count', "cards_remaining_in_deck"  # <-- Dropping the lazy features!
]
    X = df.drop(columns=[col for col in cols_to_drop if col in df.columns])
    y = df['decision']

    # Stratified Train/Test split
    print("Splitting data...")
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    # Initialize XGBoost Classifier
    print("Initializing model...")
    model = xgb.XGBClassifier(
        max_depth=8,
        learning_rate=0.1,
        n_estimators=150,
        eval_metric='logloss',
        random_state=42,
        early_stopping_rounds=15
    )

    # Train model
    print("Training model...")
    model.fit(
        X_train, y_train,
        eval_set=[(X_test, y_test)],
        verbose=10
    )

    # Evaluation
    print("\n--- Evaluation Metrics ---")
    y_train_pred = model.predict(X_train)
    y_test_pred = model.predict(X_test)

    train_acc = accuracy_score(y_train, y_train_pred)
    test_acc = accuracy_score(y_test, y_test_pred)

    print(f"Training Accuracy: {train_acc:.4f}")
    print(f"Testing Accuracy:  {test_acc:.4f}\n")

    print("Classification Report (Test Set):")
    print(classification_report(y_test, y_test_pred))

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