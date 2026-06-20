#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.bus import PhysiologicalBus
from modules.pharmacology.pk_pd import PharmacologyModule


def run_case(name: str, weight=20.0, dose=12.5, gfr=70.0, baseline=70.0, aki=0, crrt=False, effluent=0.0):
    bus = PhysiologicalBus()
    bus.set('piperacillin_mg_kg_h', dose)
    bus.set('GFR', gfr)
    bus.set('GFR_baseline', baseline)
    bus.set('AKI_stage', aki)
    bus.set('CRRT_active', bool(crrt))
    bus.set('CRRT_effluent_mL_kg_h', effluent)
    mod = PharmacologyModule({'weight_kg': weight, 'age_y': 6.0, 'age_group': 'child'})
    mod.initialize(bus)
    for _ in range(int(1800 // 5)):
        mod.step(bus, 5.0)
    return {
        'case': name,
        'C_piperacillin_mg_L': round(float(bus.get('C_piperacillin_mg_L')), 3),
        'fT_above_MIC': round(float(bus.get('piperacillin_ft_above_MIC')), 3),
        'target_attainment': round(float(bus.get('piperacillin_target_attainment')), 3),
        'coverage_mod': round(float(bus.get('piperacillin_coverage_mod')), 3),
        'renal_factor': round(float(bus.get('piperacillin_renal_clearance_factor')), 3),
        'crrt_CL_L_min': round(float(bus.get('pk_crrt_piperacillin_CL_L_min')), 5),
        'supported_drugs': int(bus.get('pk_supported_drug_count')),
        'revision': int(bus.get('pk_extension_revision')),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--fail-on-review', action='store_true')
    args = parser.parse_args()
    rows = [
        run_case('standard', dose=12.5, gfr=70, baseline=70, aki=0),
        run_case('low_dose', dose=6.0, gfr=70, baseline=70, aki=0),
        run_case('augmented_clearance', dose=12.5, gfr=130, baseline=70, aki=0),
        run_case('aki', dose=12.5, gfr=25, baseline=70, aki=2),
        run_case('aki_crrt', dose=12.5, gfr=25, baseline=70, aki=2, crrt=True, effluent=35),
    ]
    review = []
    if rows[0]['C_piperacillin_mg_L'] <= rows[1]['C_piperacillin_mg_L']:
        review.append('standard dose should exceed low-dose concentration')
    if rows[2]['renal_factor'] <= rows[0]['renal_factor']:
        review.append('augmented clearance should increase renal factor')
    if rows[3]['renal_factor'] >= rows[0]['renal_factor']:
        review.append('AKI should reduce renal factor')
    if rows[4]['crrt_CL_L_min'] <= 0:
        review.append('CRRT case should add extracorporeal piperacillin clearance')
    if rows[0]['supported_drugs'] != 15 or rows[0]['revision'] != 117:
        review.append('PK extension metadata mismatch')
    summary = {'release':'v1.17-alpha', 'status':'REVIEW' if review else 'PASS', 'rows':len(rows), 'review_items':len(review), 'review':review, 'data':rows}
    print(json.dumps(summary, indent=2))
    return 1 if args.fail_on_review and review else 0

if __name__ == '__main__':
    raise SystemExit(main())
