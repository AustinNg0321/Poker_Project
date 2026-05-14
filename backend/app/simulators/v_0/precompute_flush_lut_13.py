import sys
import os
import json

# Dynamically add the 'backend' directory to Python's module search path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from treys import Card
from app.evaluators.evaluator import get_best_score

def generate_flush_lut_13():
    flush_dict = {}
    
    for mask in range(8192):
        # Format the mask as a 13-character binary string padding with zeros
        bin_str = f"{mask:013b}"
        
        # In Python >= 3.10, you can use mask.bit_count()
        if mask.bit_count() >= 5:
            # We use spades ('s') as a placeholder suit since flush scoring only cares about ranks
            hand = [Card.new(f"{'23456789TJQKA'[r]}s") for r in range(13) if mask & (1 << r)]
            flush_dict[bin_str] = get_best_score(hand)
        else:
            flush_dict[bin_str] = 0

    with open("flush_lut_13_bit.json", "w") as f:
        json.dump(flush_dict, f, indent=4)

if __name__ == "__main__":
    generate_flush_lut_13()
