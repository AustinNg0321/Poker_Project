import sys
import os
import pandas as pd

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from app.simulators.v_0.simulation_logger import SimulationLogger
from app.simulators.v_0.v_0_1_sim import generate_log as v_0_1_log
from app.simulators.v_0.v_0_2_sim import generate_log as v_0_2_log
from app.simulators.v_0.v_0_3_sim import generate_log as v_0_3_log

def my_game_wrapper_0_1():
    return v_0_1_log(mc_sims_per_move=1000)

def my_game_wrapper_0_2():
    return v_0_2_log(mc_sims_per_move=1000)

def my_game_wrapper_0_3():
    return v_0_3_log()

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
    filepath = 'backend/app/simulators/results/v_0_1.csv'
    version = 'v_0_1'

    # initialize the logger
    logger = SimulationLogger(
        filepath=filepath,
        version=version
    )
    next_id = get_next_id(filepath)
    
    # Run 100 trials of v_0_1 for example
    logger.run_batch(batch_size=100, run_game_func=my_game_wrapper_0_1, start_game_id=next_id)
