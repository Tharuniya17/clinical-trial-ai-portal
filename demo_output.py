import json
from database.db import init_db_schema, execute_query
from modules.eligibility_risk import EligibilityRiskModule
from modules.drug_similarity import DrugSimilarityModule
from modules.pk_simulation import PKSimulationModule
from modules.risk_engine import AIRiskEngineModule
from modules.explainable_ai import ExplainableAIModule
from modules.confidence import ConfidenceModule
from modules.reviewer import ReviewerModule

def run_and_print_demo():
    init_db_schema()

    volunteers = execute_query("SELECT * FROM volunteers", fetchall=True)
    drug = execute_query("SELECT * FROM investigational_drugs WHERE drug_code = 'VX-409'", fetchone=True)
    trial = execute_query("SELECT * FROM clinical_trials WHERE trial_code = 'CT-2026-NEXUS-01'", fetchone=True)

    print("\n" + "="*80)
    print("      CLINICAL TRIAL AI RISK SCREENING SYSTEM - EXPLICIT MODULE OUTPUT")
    print("="*80)
    print(f"Trial Protocol: {trial['trial_code']} - {trial['trial_name']} ({trial['phase']})")
    print(f"Investigational Drug: {drug['drug_name']} ({drug['chemical_class']}, Pathway: {drug['metabolic_pathway']})")
    print("="*80 + "\n")

    for vol in volunteers:
        print("--------------------------------------------------------------------------------")
        print(f" VOLUNTEER PROFILE: {vol['volunteer_code']} ({vol['age']}y {vol['gender']})")
        print(f" Organ Metrics: eGFR={vol['egfr']} mL/min, ALT={vol['alt_u_l']} U/L, QTc={vol['qtc_ms']} ms, BP={vol['systolic_bp']}/{vol['diastolic_bp']} mmHg")
        print(f" Comorbidities: {vol['comorbidities'] or 'None'}")
        print(f" Current Meds:  {vol['current_medications'] or 'None'}")
        print(f" PGx Genotype:  CYP2D6: {vol['cyp2d6_genotype']} | CYP2C19: {vol['cyp2c19_genotype']}")
        print("--------------------------------------------------------------------------------")

        # Module 1: Eligibility & Clinical Risk (Pillar A)
        res_a = EligibilityRiskModule.evaluate(vol)
        print(f"\n[MODULE 1 -- PILLAR A: ELIGIBILITY & CLINICAL RISK SCORE]: {res_a['score']} ({res_a['risk_percentage']}%)")
        print("  Component Breakdown:")
        for comp_name, details in res_a['components'].items():
            print(f"    - {comp_name:<30}: {details['value']} --> Score: {details['score']} [{details['severity']}]")
        
        if res_a['ddi_alerts']:
            print("  [ALERT] Polypharmacy DDI Matrix Alerts (Pairwise Drug Interactions):")
            for ddi in res_a['ddi_alerts']:
                print(f"    - [{ddi['severity']}] {ddi['drug_pair']}: {ddi['mechanism']}")
                print(f"      Effect: {ddi['clinical_effect']}")
                print(f"      Mitigation: {ddi['mitigation']}")

        # Module 2: Drug Similarity & CYP Lookup (Pillar B)
        res_b = DrugSimilarityModule.evaluate(drug, vol)
        print(f"\n[MODULE 2 -- PILLAR B: DRUG SIMILARITY & CYP LOOKUP SCORE]: {res_b['score']} ({res_b['risk_percentage']}%)")
        print(f"  Chemical Class Similarity: {res_b['chemical_class']} (Analog Risk: {res_b['analog_risk']})")
        print(f"  Matched Approved/Recalled Analogs:")
        for analog in res_b['matched_analogs']:
            bb = " [FDA Black Box]" if analog.get('black_box') else ""
            wd = " [WITHDRAWN]" if analog.get('withdrawn') else ""
            print(f"    - {analog['name']} (Similarity: {analog['similarity']*100:.0f}%){bb}{wd}: {', '.join(analog['adverse_events'])}")

        if res_b['cyp_interactions']:
            print("  [PGX] CYP Enzyme Inhibitor/Inducer & PGx Lookup Flags:")
            for cyp in res_b['cyp_interactions']:
                print(f"    - [{cyp['severity']}] Enzyme: {cyp['enzyme']} | Agent: {cyp['medication']} | Type: {cyp['type']}")
                print(f"      Effect: {cyp['effect']}")
                print(f"      Rec: {cyp['recommendation']}")

        # Module 3: Digital Twin PK ODE Simulation (Pillar C)
        res_c = PKSimulationModule.simulate(vol, drug)
        pk = res_c['pk_parameters']
        print(f"\n[MODULE 3 -- PILLAR C: DIGITAL TWIN PK SIMULATION SCORE]: {res_c['score']} ({res_c['risk_percentage']}%)")
        print(f"  Simulated Pharmacokinetic Metrics (48-Hour ADME Model):")
        print(f"    - Cmax (Peak Exposure)       : {pk['Cmax_mg_L']} mg/L")
        print(f"    - Tmax (Time to Peak)        : {pk['Tmax_hours']} hours")
        print(f"    - AUC (Total Exposure)       : {pk['AUC_mg_h_L']} mg*h/L")
        print(f"    - Elimination Half-life t1/2 : {pk['half_life_hours']} hours")
        print(f"    - Individualized Clearance CL: {pk['clearance_L_h']} L/h")
        print(f"    - Minimum Toxic Conc (MTC)   : {pk['mtc_threshold_mg_L']} mg/L")
        print(f"    - Toxic Exposure Ratio Cmax/MTC: {pk['toxic_exposure_ratio']} (Risk: {'EXCEEDED MTC' if pk['toxic_exposure_ratio'] > 1.0 else 'Safe Margin'})")

        # Module 4: AI Risk Engine & Multi-Pillar Model Fusion
        fusion = AIRiskEngineModule.calculate_fusion_risk(res_a['score'], res_b['score'], res_c['score'])
        print(f"\n[MODULE 4 -- AI RISK ENGINE & MULTI-PILLAR FUSION]:")
        print(f"  Formula: R = 0.40 * {res_a['score']} + 0.35 * {res_b['score']} + 0.25 * {res_c['score']}")
        print(f"  OVERALL FUSED RISK SCORE (R) : {fusion['overall_risk_score']} ({fusion['risk_percentage']}%)")
        print(f"  RISK CATEGORY LEVEL          : {fusion['risk_category'].upper()}")
        print(f"  SUGGESTED MONITORING LEVEL   : {fusion['suggested_monitoring']}")

        # Module 5: Explainable AI & SHAP Contribution
        gb_model = AIRiskEngineModule.get_or_train_model()
        med_count = len([m for m in (vol.get('current_medications') or '').split(',') if m.strip()])
        comorbidity_count = len([c for c in (vol.get('comorbidities') or '').split(',') if c.strip()])
        shap_dict = {
            'age': vol['age'],
            'egfr': vol['egfr'],
            'alt': vol['alt_u_l'],
            'qtc': vol['qtc_ms'],
            'comorbidity_count': comorbidity_count,
            'med_count': med_count,
            'analog_risk': res_b['score'],
            'sim_cmax_ratio': pk['toxic_exposure_ratio']
        }
        shap_res = ExplainableAIModule.explain(gb_model, shap_dict)
        print(f"\n[MODULE 5 -- EXPLAINABLE AI (SHAP FEATURE IMPACT)]:")
        print(f"  Base Expected Risk Value: {shap_res['base_value']}")
        print(f"  Top Risk Increasing Drivers:")
        for d in shap_res['top_risk_drivers']:
            print(f"    - {d['feature']:<30} (Value: {d['value']}) --> SHAP Contribution: +{d['shap_value']*100:.1f}%")
        print(f"  Top Protective Factors:")
        for p in shap_res['top_protective_factors']:
            print(f"    - {p['feature']:<30} (Value: {p['value']}) --> SHAP Contribution: {p['shap_value']*100:.1f}%")

        # Module 6: Confidence & Calibration Engine
        conf_res = ConfidenceModule.evaluate(res_a['score'], res_b['score'], res_c['score'], vol, drug)
        print(f"\n[MODULE 6 -- CONFIDENCE & CALIBRATION ENGINE]:")
        print(f"  Confidence Score   : {conf_res['confidence_score']} ({conf_res['confidence_percentage']}%)")
        print(f"  Confidence Status  : {conf_res['confidence_flag']}")
        print(f"  Evaluation Details : {conf_res['warning_message']}")

        # Module 7: Reviewer Decision & Audit History
        print(f"\n[MODULE 7 -- HUMAN REVIEWER DECISION PANEL]:")
        if vol['volunteer_code'] == 'VOL-2026-101':
            rec_decision = 'Proceed'
            notes = 'Volunteer displays excellent renal/hepatic biomarkers. Standard Phase-1 protocol approved.'
        else:
            rec_decision = 'Proceed with Modified Protocol'
            notes = 'Borderline eGFR (52 mL/min) and CYP2D6 Poor Metabolizer phenotype detected. Requires enhanced 12h/24h ECG & renal lab monitoring.'

        # Save evaluation in database
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
                trial['id'], vol['id'], drug['id'],
                fusion['overall_risk_score'], fusion['risk_category'],
                conf_res['confidence_score'], conf_res['confidence_flag'],
                res_a['score'], res_b['score'], res_c['score'],
                fusion['suggested_monitoring'],
                json.dumps(shap_res),
                json.dumps(res_c),
                rec_decision, notes, 1
            ),
            commit=True
        )

        ReviewerModule.record_decision(eval_id, 1, rec_decision, notes)
        audit_trail = ReviewerModule.get_audit_trail(eval_id)
        
        print(f"  Final Decision Recorded : {rec_decision}")
        print(f"  Investigator Notes      : {notes}")
        print(f"  Audit Trail History ({len(audit_trail)} logs):")
        for log in audit_trail:
            print(f"    - [{log['timestamp']}] Action: {log['action']} | Status: {log['new_status']} | By: {log['reviewer_name']}")
        
        print("\n" + "="*80 + "\n")

if __name__ == '__main__':
    run_and_print_demo()
