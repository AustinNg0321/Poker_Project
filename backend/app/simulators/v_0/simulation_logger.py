import csv
import os
import time
import traceback

class SimulationLogger:
    def __init__(self, filepath='simulation_results.csv', version='v0.3_baseline'):
        self.filepath = filepath
        self.version = version
        self.header = [
            'Game_ID', 'Version', 'Result', 
            'Player_Score', 'Dealer_Score', 
            'Delta_Avg', 'Time_Taken'
        ]
        self._initialize_file()

    def _initialize_file(self):
        """Create the CSV and write the header if the file doesn't exist."""
        file_exists = os.path.isfile(self.filepath)
        with open(self.filepath, mode='a', newline='') as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(self.header)

    def log_game(self, game_id, result, player_score, dealer_score, delta_avg, time_taken):
        """Append a single game's result to the CSV."""
        with open(self.filepath, mode='a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                game_id, self.version, result, 
                player_score, dealer_score, 
                delta_avg, time_taken
            ])

    def run_batch(self, batch_size, run_game_func, start_game_id=1):
        """
        Runs a batch of games, robustly handling errors on individual games.
        
        :param batch_size: Number of games to run.
        :param run_game_func: A callable that takes no arguments (or a game_id) 
                              and returns (result, player_score, dealer_score, delta_avg).
        :param start_game_id: The starting ID for the batch.
        """
        print(f"Starting batch of {batch_size} games (Version: {self.version})...")
        success_count = 0
        error_count = 0

        for i in range(batch_size):
            game_id = start_game_id + i
            start_time = time.time()
            
            try:
                # Assuming run_game_func returns the 4 required metrics
                result, player_score, dealer_score, delta_avg = run_game_func()
                
                time_taken = time.time() - start_time
                self.log_game(game_id, result, player_score, dealer_score, delta_avg, time_taken)
                success_count += 1
                
            except Exception as e:
                error_count += 1
                time_taken = time.time() - start_time
                print(f"Error in Game {game_id}: {type(e).__name__} - {e}")
                traceback.print_exc()
                # Optionally log the error to the CSV or a separate error log
                # self.log_game(game_id, -1, -1, -1, 0, time_taken)

        print(f"Batch complete. Success: {success_count}, Errors: {error_count}")

# ==========================================
# Example Usage Wrapper
# ==========================================
if __name__ == '__main__':
    import random
    
    # Mock version of your run_game logic
    def mock_run_game():
        # Simulate game processing time
        time.sleep(random.uniform(0.01, 0.05))
        
        # Simulate an occasional error (1% chance)
        if random.random() < 0.01:
            raise ValueError("Random simulation crash!")
            
        result = random.choice([0, 1])
        player_score = random.randint(1, 7462)
        dealer_score = random.randint(1, 7462)
        delta_avg = round(random.uniform(-500.0, 500.0), 2)
        
        return result, player_score, dealer_score, delta_avg

    # 1. Initialize the logger
    logger = SimulationLogger(
        filepath='backend/app/simulators/simulation_results.csv', 
        version='v0.3_baseline'
    )
    
    # 2. Run a batch of 100 trials
    logger.run_batch(batch_size=100, run_game_func=mock_run_game, start_game_id=1)
