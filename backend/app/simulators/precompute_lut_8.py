import itertools
from collections import Counter
import json
import os
from treys import Card, Evaluator

def generate_lut_8():
    evaluator = Evaluator()
    
    RANKS = list(range(13))
    ALL_MULTISETS_8 = list(itertools.combinations_with_replacement(RANKS, 8)) 
    # Max 4 of any rank in a standard deck
    FILTERED_MULTISETS_8 = [m for m in ALL_MULTISETS_8 if not any(m.count(r) > 4 for r in set(m))] 
    
    def get_rank_str(r):
        return '23456789TJQKA'[r]
        
    suits = ['h', 'd', 'c', 's']
    
    lut_data = {}
    
    print(f"Generating LUT for {len(FILTERED_MULTISETS_8)} valid 8-card combinations...")
    
    for mset in FILTERED_MULTISETS_8:
        mset_counts = Counter(mset)
        
        # 1. Non-flush dummy hand (use alternating suits)
        nf_dummy = []
        suit_idx = 0
        for r, count in mset_counts.items():
            rank_str = get_rank_str(r)
            for _ in range(count):
                nf_dummy.append(Card.new(f"{rank_str}{suits[suit_idx % 4]}"))
                suit_idx += 1
                
        # treys Evaluator evaluates 5 to 7 cards natively.
        # Since we have 8 cards, we manually iterate all 5-card combinations to find the best (lowest) score.
        best_score = 7463 # Max possible worse score + 1
        for combo in itertools.combinations(nf_dummy, 5):
            score = evaluator.evaluate(list(combo), [])
            if score < best_score:
                best_score = score
            
        # Convert tuple back to string key for JSON serialization
        mset_key = ",".join(map(str, mset))
        lut_data[mset_key] = {
            "non_flush": best_score
        }

    output_path = os.path.join(os.path.dirname(__file__), 'multisets_lut_8.json')
    with open(output_path, 'w') as f:
        json.dump(lut_data, f, indent=2)
        
    print(f"Successfully wrote LUT to {output_path}")

if __name__ == "__main__":
    generate_lut_8()
