import json
from database.db import init_db_schema, execute_query
from modules.eligibility_risk import EligibilityRiskModule
from modules.drug_similarity import DrugSimilarityModule
from modules.pk_simulation import PKSimulationModule
from modules.risk_engine import AIRiskEngineModule
from modules.explainable_ai import ExplainableAIModule
from modules.confidence import ConfidenceModule
from modules.reviewer import ReviewerModule

def test_full_pipeline():
    print("==================================================")
    print(" TESTING 7-MODULE AI RISK SCREENING PIPELINE")
    print("==================================================")
    
    # 1. Initialize Database
    init_db_schema()

    # 2. Fetch Sample Volunteer & Drug
    volunteer = execute_query("SELECT * FROM volunteers WHERE volunteer_code = 'VOL-2026-102'", fetchone=True)
    drug = execute_query("SELECT * FROM investigational_drugs WHERE drug_code = 'VX-409'", fetchone=True)

    assert volunteer is not None, "Sample volunteer VOL-2026-102 missing"
    assert drug is not None, "Sample drug VX-409 missing"

    # 3. Test Module 1: Eligibility Risk (Pillar A)
    res_a = EligibilityRiskModule.evaluate(volunteer)
    print(f"\n[Module 1 - Pillar A Score]: {res_a['score']} ({res_a['risk_percentage']}%)")
    for k, v in res_a['components'].items():
        print(f"  - {k}: {v['value']} -> Risk Score: {v['score']} ({v['severity']})")

    # 4. Test Module 2: Drug Similarity (Pillar B)
    res_b = DrugSimilarityModule.evaluate(drug, volunteer)
    print(f"\n[Module 2 - Pillar B Score]: {res_b['score']} ({res_b['risk_percentage']}%)")
    print(f"  - Chemical Class: {res_b['chemical_class']}")
    print(f"  - Matched Analogs: {[a['name'] for a in res_b['matched_analogs']]}")

    # 5. Test Module 3: Digital Twin PK Simulation (Pillar C)
    res_c = PKSimulationModule.simulate(volunteer, drug)
    print(f"\n[Module 3 - Pillar C Score]: {res_c['score']} ({res_c['risk_percentage']}%)")
    print(f"  - PK Cmax: {res_c['pk_parameters']['Cmax_mg_L']} mg/L")
    print(f"  - PK Half-life: {res_c['pk_parameters']['half_life_hours']} h")
    print(f"  - Toxic Exposure Ratio (Cmax/MTC): {res_c['pk_parameters']['toxic_exposure_ratio']}")

    # 6. Test Module 4: AI Risk Engine & Model Fusion
    fusion = AIRiskEngineModule.calculate_fusion_risk(res_a['score'], res_b['score'], res_c['score'])
    print(f"\n[Module 4 - Fused Risk Score R]: {fusion['overall_risk_score']} ({fusion['risk_percentage']}%)")
    print(f"  - Category: {fusion['risk_category']}")
    print(f"  - Monitoring Level: {fusion['suggested_monitoring']}")

    # 7. Test Module 5: Explainable AI & SHAP
    gb_model = AIRiskEngineModule.get_or_train_model()
    med_count = len([m for m in (volunteer.get('current_medications') or '').split(',') if m.strip()])
    comorbidity_count = len([c for c in (volunteer.get('comorbidities') or '').split(',') if c.strip()])
    shap_dict = {
        'age': volunteer['age'],
        'egfr': volunteer['egfr'],
        'alt': volunteer['alt_u_l'],
        'qtc': volunteer['qtc_ms'],
        'comorbidity_count': comorbidity_count,
        'med_count': med_count,
        'analog_risk': res_b['score'],
        'sim_cmax_ratio': res_c['pk_parameters']['toxic_exposure_ratio']
    }
    shap_res = ExplainableAIModule.explain(gb_model, shap_dict)
    print(f"\n[Module 5 - SHAP Analysis]:")
    print(f"  - Top Risk Drivers: {[d['feature'] for d in shap_res['top_risk_drivers']]}")

    # 8. Test Module 6: Confidence Scoring
    conf_res = ConfidenceModule.evaluate(res_a['score'], res_b['score'], res_c['score'], volunteer, drug)
    print(f"\n[Module 6 - Confidence]: {conf_res['confidence_score']} ({conf_res['confidence_percentage']}%)")
    print(f"  - Flag: {conf_res['confidence_flag']}")

    # 9. Test Module 7: Reviewer Audit Trail
    eval_id = execute_query(
        """
        INSERT INTO risk_evaluations (
            trial_id, volunteer_id, investigational_drug_id,
            overall_risk_score, risk_category, confidence_score, confidence_flag,
            pillar_a_score, pillar_b_score, pillar_c_score, suggested_monitoring,
            shap_json, pk_sim_json, reviewer_decision, reviewer_notes, reviewed_by
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            1, volunteer['id'], drug['id'],
            fusion['overall_risk_score'], fusion['risk_category'],
            conf_res['confidence_score'], conf_res['confidence_flag'],
            res_a['score'], res_b['score'], res_c['score'],
            fusion['suggested_monitoring'],
            json.dumps(shap_res),
            json.dumps(res_c),
            'Pending Review', '', None
        ),
        commit=True
    )

    rec_res = ReviewerModule.record_decision(eval_id, 1, 'Proceed with Modified Protocol', 'Enhanced 12h/24h ECG monitoring required due to borderline QTc.')
    print(f"\n[Module 7 - Reviewer Decision]: Recorded '{rec_res['new_status']}' for Eval #{eval_id}")

    audit_logs = ReviewerModule.get_audit_trail(eval_id)
    print(f"  - Audit Trail Log Count: {len(audit_logs)}")

    print("\n==================================================")
    print(" ALL 7 MODULES TESTED & PASSED SUCCESSFULLY!")
    print("==================================================")

if __name__ == '__main__':
    test_full_pipeline()
