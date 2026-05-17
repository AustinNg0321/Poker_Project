import pandas as pd
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score

# 1. Load the pristine data asset once
df = pd.read_csv('training_data_v2.csv')
if 'game_id' in df.columns:
    df = df.drop(columns=['game_id'])

# 2. Define the different data-filtering strategies you want to try
data_strategies = {
    "all_games": df,
    "winners_only": df[df['game_won'] == 1]
}

# 3. Define different feature configurations to test
feature_sets = {
    "all_features": [col for col in df.columns if col not in ['decision', 'final_player_rank', 'final_dealer_rank', 'game_won']],
    "no_lazy_clock_features": [col for col in df.columns if col not in ['decision', 'final_player_rank', 'final_dealer_rank', 'game_won', 'move_num', 'dealer_card_count', 'player_card_count', "cards_remaining_in_deck"]],
    "no_current_scores": [col for col in df.columns if col not in ['decision', 'final_player_rank', 'final_dealer_rank', 'game_won', 'move_num', 'dealer_card_count', 'current_player_rank_score', 'current_dealer_rank_score', 'player_card_count', "cards_remaining_in_deck"]]
}

# 4. Define different model hyperparameter limits
depths = [3, 5, 8]
learning_rates = [0.02, 0.1]

print("--- STARTING AUTOMATED EXPERIMENT LOOP ---")
leaderboard = []

# Loop through every single combination automatically
for data_name, current_df in data_strategies.items():
    for feature_name, current_features in feature_sets.items():
        for depth in depths:
            for lr in learning_rates:
                
                # Split the specific slice of data
                X = current_df[current_features]
                y = current_df['decision']
                
                X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
                
                # Train the specific variant
                model = xgb.XGBClassifier(max_depth=depth, learning_rate=lr, n_estimators=100, eval_metric='logloss', random_state=42)
                model.fit(X_train, y_train, verbose=False)
                
                # Evaluate accuracy
                preds = model.predict(X_test)
                acc = accuracy_score(y_test, preds)
                
                # Log the result
                result = {
                    "Data Strategy": data_name,
                    "Features": feature_name,
                    "Depth": depth,
                    "LR": lr,
                    "Test Accuracy": round(acc, 4)
                }
                leaderboard.append(result)
                print(f"Tested: Data={data_name} | Features={feature_name} | Depth={depth} | Acc={acc:.4f}")

# Accuracy only. For each model, I need to run simulations

# 5. Print out the winning combination
leaderboard_df = pd.DataFrame(leaderboard).sort_values(by="Test Accuracy", ascending=False)
print("\n--- ULTIMATE MODEL LEADERBOARD ---")
print(leaderboard_df.to_string(index=False))