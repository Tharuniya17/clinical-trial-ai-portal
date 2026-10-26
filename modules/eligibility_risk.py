import json

class EligibilityRiskModule:
    """
    Module 1: Pillar A - Physiology, Lab Markers & Polypharmacy DDI Matrix Risk Assessment
    Evaluates organ functions (eGFR, LFTs, QTc), comorbidity burden, prior ADRs,
    and runs a pairwise Drug-Drug Interaction (DDI) Matrix lookup across concurrent medications.
    """
    
    # High-Risk Pairwise Drug-Drug Interaction Knowledge Base
    DDI_MATRIX_RULES = [
        {
            'med1': ['amlodipine', 'diltiazem', 'verapamil'],
            'med2': ['simvastatin', 'atorvastatin', 'lovastatin'],
            'severity': 'Moderate',
            'interaction': 'CYP3A4 / Transporter Competition',
            'clinical_effect': 'Increased statin exposure. Risk of rhabdomyolysis and myopathy.',
            'mitigation': 'Cap statin dose or monitor CPK levels.'
        },
        {
            'med1': ['metoprolol', 'carvedilol', 'propranolol'],
            'med2': ['fluoxetine', 'paroxetine', 'bupropion', 'amiodarone'],
            'severity': 'Major',
            'interaction': 'CYP2D6 Inhibition of Beta-Blocker',
            'clinical_effect': 'Marked bradycardia, heart block, and profound hypotension.',
            'mitigation': 'ECG monitoring; reduce beta-blocker dosage.'
        },
        {
            'med1': ['warfarin', 'apixaban', 'rivaroxaban', 'dabigatran'],
            'med2': ['aspirin', 'ibuprofen', 'naproxen', 'ketorolac', 'clopidogrel'],
            'severity': 'Major',
            'interaction': 'Synergistic Pharmacodynamic Anticoagulation',
            'clinical_effect': 'Severe GI bleeding, intracranial hemorrhage risk.',
            'mitigation': 'Avoid co-administration or monitor INR closely.'
        },
        {
            'med1': ['lisinopril', 'enalapril', 'losartan', 'valsartan'],
            'med2': ['spironolactone', 'eplerenone', 'triamterene', 'potassium'],
            'severity': 'Major',
            'interaction': 'RAAS Pathway Dual Blockade',
            'clinical_effect': 'Severe hyperkalemia (> 5.5 mEq/L) and lethal arrhythmia risk.',
            'mitigation': 'Serum potassium monitoring at baseline and day 3.'
        },
        {
            'med1': ['amiodarone', 'sotalol', 'haloperidol', 'azithromycin'],
            'med2': ['citalopram', 'escitalopram', 'methadone', 'levofloxacin', 'ondansetron'],
            'severity': 'Critical',
            'interaction': 'Synergistic IKr Cardiac Potassium Channel Inhibition',
            'clinical_effect': 'Additive QTc prolongation. Severe risk of Torsades de Pointes.',
            'mitigation': 'Continuous telemetry / 12-lead ECG monitoring.'
        },
        {
            'med1': ['metformin'],
            'med2': ['contrast', 'topiramate', 'ranolazine'],
            'severity': 'Moderate',
            'interaction': 'Renal Clearance Competition',
            'clinical_effect': 'Risk of lactic acidosis in setting of borderline renal clearance.',
            'mitigation': 'Monitor serum creatinine / eGFR.'
        }
    ]

    @classmethod
    def evaluate_ddi_matrix(cls, current_medications_str):
        """
        Runs pairwise Drug-Drug Interaction (DDI) Matrix lookup on volunteer's medications.
        """
        if isinstance(current_medications_str, str):
            meds = [m.strip().lower() for m in current_medications_str.split(',') if m.strip()]
        else:
            meds = [str(m).strip().lower() for m in (current_medications_str or [])]

        ddi_alerts = []
        ddi_score_modifier = 0.0

        for i in range(len(meds)):
            for j in range(i + 1, len(meds)):
                m1, m2 = meds[i], meds[j]
                
                for rule in cls.DDI_MATRIX_RULES:
                    match1 = any(k in m1 for k in rule['med1']) and any(k in m2 for k in rule['med2'])
                    match2 = any(k in m2 for k in rule['med1']) and any(k in m1 for k in rule['med2'])
                    
                    if match1 or match2:
                        severity = rule['severity']
                        mod = 0.35 if severity == 'Critical' else (0.25 if severity == 'Major' else 0.15)
                        ddi_score_modifier += mod
                        
                        ddi_alerts.append({
                            'drug_pair': f"{m1.title()} + {m2.title()}",
                            'severity': severity,
                            'mechanism': rule['interaction'],
                            'clinical_effect': rule['clinical_effect'],
                            'mitigation': rule['mitigation']
                        })

        return ddi_alerts, min(ddi_score_modifier, 0.50)

    @staticmethod
    def evaluate(volunteer):
        risk_components = {}
        total_weight = 0.0
        weighted_score = 0.0

        # 1. Renal Function (eGFR)
        egfr = float(volunteer.get('egfr', 90))
        if egfr < 30:
            renal_risk = 0.95
        elif egfr < 60:
            renal_risk = 0.65
        elif egfr < 80:
            renal_risk = 0.30
        else:
            renal_risk = 0.05
        risk_components['Renal Function (eGFR)'] = {
            'value': f"{egfr} mL/min/1.73m²",
            'score': renal_risk,
            'weight': 0.25,
            'severity': 'High' if renal_risk > 0.6 else ('Medium' if renal_risk > 0.2 else 'Low')
        }
        weighted_score += renal_risk * 0.25
        total_weight += 0.25

        # 2. Hepatic Function (ALT / AST / Bilirubin)
        alt = float(volunteer.get('alt_u_l', 25))
        ast = float(volunteer.get('ast_u_l', 25))
        bili = float(volunteer.get('bilirubin_mg_dl', 0.8))
        
        alt_fold = alt / 40.0
        ast_fold = ast / 40.0
        bili_fold = bili / 1.2
        
        max_hepatic_fold = max(alt_fold, ast_fold, bili_fold)
        if max_hepatic_fold > 3.0:
            hepatic_risk = 0.90
        elif max_hepatic_fold > 2.0:
            hepatic_risk = 0.70
        elif max_hepatic_fold > 1.5:
            hepatic_risk = 0.40
        else:
            hepatic_risk = 0.05
        risk_components['Hepatic Function (LFT)'] = {
            'value': f"ALT: {alt} U/L, AST: {ast} U/L, Bili: {bili} mg/dL",
            'score': hepatic_risk,
            'weight': 0.20,
            'severity': 'High' if hepatic_risk > 0.6 else ('Medium' if hepatic_risk > 0.2 else 'Low')
        }
        weighted_score += hepatic_risk * 0.20
        total_weight += 0.20

        # 3. Cardiac Safety (QTc Interval & BP)
        qtc = float(volunteer.get('qtc_ms', 410))
        sbp = float(volunteer.get('systolic_bp', 120))
        dbp = float(volunteer.get('diastolic_bp', 80))
        
        qtc_risk = 0.05
        if qtc >= 480:
            qtc_risk = 0.95
        elif qtc >= 450:
            qtc_risk = 0.60
        elif qtc >= 430:
            qtc_risk = 0.30

        bp_risk = 0.05
        if sbp >= 160 or dbp >= 100:
            bp_risk = 0.70
        elif sbp >= 140 or dbp >= 90:
            bp_risk = 0.35

        cardiac_risk = max(qtc_risk, bp_risk)
        risk_components['Cardiac Safety (QTc & BP)'] = {
            'value': f"QTc: {qtc} ms, BP: {sbp}/{dbp} mmHg",
            'score': cardiac_risk,
            'weight': 0.20,
            'severity': 'High' if cardiac_risk > 0.6 else ('Medium' if cardiac_risk > 0.2 else 'Low')
        }
        weighted_score += cardiac_risk * 0.20
        total_weight += 0.20

        # 4. Comorbidities Burden
        comorbidities_raw = volunteer.get('comorbidities', '')
        if isinstance(comorbidities_raw, str):
            comorbidities = [c.strip() for c in comorbidities_raw.split(',') if c.strip()]
        else:
            comorbidities = comorbidities_raw or []
            
        comorbidity_count = len(comorbidities)
        if comorbidity_count >= 4:
            comorbidity_risk = 0.85
        elif comorbidity_count == 3:
            comorbidity_risk = 0.65
        elif comorbidity_count == 2:
            comorbidity_risk = 0.40
        elif comorbidity_count == 1:
            comorbidity_risk = 0.20
        else:
            comorbidity_risk = 0.05
            
        risk_components['Comorbidities Burden'] = {
            'value': f"{comorbidity_count} active conditions ({', '.join(comorbidities) if comorbidities else 'None'})",
            'score': comorbidity_risk,
            'weight': 0.15,
            'severity': 'High' if comorbidity_risk > 0.6 else ('Medium' if comorbidity_risk > 0.2 else 'Low')
        }
        weighted_score += comorbidity_risk * 0.15
        total_weight += 0.15

        # 5. Polypharmacy & Drug-Drug Interactions (DDI Matrix)
        meds_raw = volunteer.get('current_medications', '')
        ddi_alerts, ddi_mod = EligibilityRiskModule.evaluate_ddi_matrix(meds_raw)
        
        if isinstance(meds_raw, str):
            meds = [m.strip() for m in meds_raw.split(',') if m.strip()]
        else:
            meds = meds_raw or []
            
        med_count = len(meds)
        base_poly_risk = 0.05
        if med_count >= 5:
            base_poly_risk = 0.70
        elif med_count >= 3:
            base_poly_risk = 0.45
        elif med_count >= 1:
            base_poly_risk = 0.20
            
        poly_risk = min(base_poly_risk + ddi_mod, 0.95)
        risk_components['Polypharmacy & DDI Matrix'] = {
            'value': f"{med_count} concurrent meds ({len(ddi_alerts)} high-risk pairs detected)",
            'score': round(poly_risk, 4),
            'weight': 0.10,
            'severity': 'High' if poly_risk > 0.6 else ('Medium' if poly_risk > 0.2 else 'Low')
        }
        weighted_score += poly_risk * 0.10
        total_weight += 0.10

        # 6. Prior Adverse Reactions (ADRs)
        adrs_raw = volunteer.get('previous_adverse_reactions', '')
        if isinstance(adrs_raw, str):
            adrs = [a.strip() for a in adrs_raw.split(',') if a.strip()]
        else:
            adrs = adrs_raw or []
            
        adr_count = len(adrs)
        if adr_count >= 2:
            adr_risk = 0.80
        elif adr_count == 1:
            adr_risk = 0.45
        else:
            adr_risk = 0.05
            
        risk_components['Prior Adverse Reactions'] = {
            'value': f"{adr_count} recorded ADRs ({', '.join(adrs) if adrs else 'None'})",
            'score': adr_risk,
            'weight': 0.10,
            'severity': 'High' if adr_risk > 0.6 else ('Medium' if adr_risk > 0.2 else 'Low')
        }
        weighted_score += adr_risk * 0.10
        total_weight += 0.10

        final_pillar_a_score = round(weighted_score / total_weight, 4)

        return {
            'score': final_pillar_a_score,
            'risk_percentage': round(final_pillar_a_score * 100, 1),
            'components': risk_components,
            'ddi_alerts': ddi_alerts
        }
