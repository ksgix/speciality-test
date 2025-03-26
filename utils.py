from typing import Dict, Any, List
from config import SPECIALTIES_DATA 

def get_top_professions(profession_scores: Dict[str, int]) -> List[Dict[str, Any]]:
    sorted_specialties = sorted(
        profession_scores.items(), key=lambda item: item[1], reverse=True
    )

    top_specialties = sorted_specialties[:3]

    result = []
    for specialty, score in top_specialties:
        for spec_data in SPECIALTIES_DATA:
          if spec_data["specialty"] == specialty:
              result.append({
                  "specialty": specialty,
                  "score": score,
                  "description": spec_data["description"],
              })
              break

    return result