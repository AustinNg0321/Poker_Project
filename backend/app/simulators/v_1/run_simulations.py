import sys
import os
import pandas as pd

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from app.simulators.v_1.simulation_logger import SimulationLogger
from app.simulators.v_1.v_1_0_sim import generate_log as v_1_0_log

def my_game_wrapper_1_0():
    return v_1_0_log()

# good enough for relatively small CSV files (e.g. <100k rows). 
# may optimize later if needed
def get_next_id(filename):
    if not os.path.exists(filename):
        return 1
    df = pd.read_csv(filename)

    # FIX: Return 1 if the CSV exists but has no data rows
    if df.empty or pd.isna(df['Game_ID'].max()):
       return 1
    return df['Game_ID'].max() + 1

# example usage: run from the project root directory
if __name__ == '__main__':
    filepath = 'backend/app/simulators/results/v_1_0_unfinished_1.csv'
    version = 'v_1_0_unfinished'

    # initialize the logger
    logger = SimulationLogger(
        filepath=filepath,
        version=version
    )
    next_id = get_next_id(filepath)
    
    # Run 100 trials of v_0_1 for example
    logger.run_batch(batch_size=5213, run_game_func=my_game_wrapper_1_0, start_game_id=next_id)
