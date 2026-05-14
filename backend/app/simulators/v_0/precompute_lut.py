import itertools
from collections import Counter
import json
import os
from treys import Card, Evaluator

def generate_lut():
    evaluator = Evaluator()
    
    RANKS = list(range(13))
    ALL_MULTISETS_5 = list(itertools.combinations_with_replacement(RANKS, 5)) 
    # Max 4 of any rank in a standard deck
    FILTERED_MULTISETS_5 = [m for m in ALL_MULTISETS_5 if not any(m.count(r) > 4 for r in set(m))] 
    
    def get_rank_str(r):
        return '23456789TJQKA'[r]
        
    suits = ['h', 'd', 'c', 's']
    
    lut_data = {}
    
    print(f"Generating LUT for {len(FILTERED_MULTISETS_5)} valid 5-card combinations...")
    
    for mset in FILTERED_MULTISETS_5:
        mset_counts = Counter(mset)
        
        # 1. Non-flush dummy hand (use alternating suits)
        nf_dummy = []
        suit_idx = 0
        for r, count in mset_counts.items():
            rank_str = get_rank_str(r)
            for _ in range(count):
                nf_dummy.append(Card.new(f"{rank_str}{suits[suit_idx % 4]}"))
                suit_idx += 1
                
        non_flush_score = evaluator.evaluate(nf_dummy[:5], [])
        
        # 2. Flush dummy hand
        flush_score = non_flush_score
        # Flushes are only possible if we have 5 distinct ranks (or fewer than 2 of any rank)
        if all(count <= 1 for count in mset_counts.values()):
            f_dummy = []
            for r, count in mset_counts.items():
                rank_str = get_rank_str(r)
                f_dummy.append(Card.new(f"{rank_str}h"))
            flush_score = evaluator.evaluate(f_dummy[:5], [])
            
        # Convert tuple back to string key for JSON serialization
        mset_key = ",".join(map(str, mset))
        lut_data[mset_key] = {
            "flush": flush_score,
            "non_flush": non_flush_score
        }

    output_path = os.path.join(os.path.dirname(__file__), 'multisets_lut.json')
    with open(output_path, 'w') as f:
        json.dump(lut_data, f, indent=2)
        
    print(f"Successfully wrote LUT to {output_path}")

if __name__ == "__main__":
    generate_lut()
