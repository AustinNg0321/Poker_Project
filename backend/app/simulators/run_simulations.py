import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.simulators.simulation_logger import SimulationLogger
from app.simulators.v_0_1_sim import generate_log as v_0_1_log
from app.simulators.v_0_2_sim import generate_log as v_0_2_log
from app.simulators.v_0_3_sim import generate_log as v_0_3_log

def my_game_wrapper_0_1():
    return v_0_1_log(mc_sims_per_move=1000)

def my_game_wrapper_0_2():
    return v_0_2_log(mc_sims_per_move=1000)

def my_game_wrapper_0_3():
    return v_0_3_log()

if __name__ == '__main__':
    # Initialize the logger
    # example usage: python run_simulations.py
    logger = SimulationLogger(
        filepath='backend/app/simulators/results/v_0_1.csv', 
        version='v_0_1'
    )
    
    # Run 100 trials of v0.3
    logger.run_batch(batch_size=9861, run_game_func=my_game_wrapper_0_1, start_game_id=25140)
