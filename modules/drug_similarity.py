import json

class DrugSimilarityModule:
    """
    Module 2: Pillar B - Drug Similarity, Analog Risk & CYP Pharmacogenomics Engine
    Evaluates investigational drug against approved/recalled analogs, chemical class toxicity,
    and performs CYP Enzyme Inhibitor/Inducer DDI lookups against concurrent medications.
    """
    
    # Knowledge base of known drug analog risk profiles
    ANALOG_DATABASE = {
        'Kinase Inhibitor': [
            {'name': 'Sunitinib', 'similarity': 0.82, 'black_box': True, 'withdrawn': False, 'adverse_events': ['Cardiotoxicity', 'Hepatotoxicity', 'Hypertension']},
            {'name': 'Sorafenib', 'similarity': 0.78, 'black_box': True, 'withdrawn': False, 'adverse_events': ['Cardiac Ischemia', 'Bleeding', 'Stevens-Johnson']},
            {'name': 'Regorafenib', 'similarity': 0.71, 'black_box': True, 'withdrawn': False, 'adverse_events': ['Severe Hepatotoxicity']}
        ],
        'SGLT2 Inhibitor': [
            {'name': 'Canagliflozin', 'similarity': 0.85, 'black_box': True, 'withdrawn': False, 'adverse_events': ['Ketoacidosis', 'Lower Limb Amputation', 'Mycotic Infections']},
            {'name': 'Empagliflozin', 'similarity': 0.81, 'black_box': False, 'withdrawn': False, 'adverse_events': ['UTI', 'Hypotension']},
            {'name': 'Dapagliflozin', 'similarity': 0.79, 'black_box': False, 'withdrawn': False, 'adverse_events': ['Renal Function Decline', 'Ketoacidosis']}
        ],
        'Monoclonal Antibody': [
            {'name': 'Natalizumab', 'similarity': 0.75, 'black_box': True, 'withdrawn': True, 'adverse_events': ['Progressive Multifocal Leukoencephalopathy (PML)', 'Hepatotoxicity']},
            {'name': 'Teralizumab (TGN1412)', 'similarity': 0.65, 'black_box': True, 'withdrawn': True, 'adverse_events': ['Cytokine Release Syndrome', 'Multi-Organ Failure']}
        ],
        'NSAID / Cox-2 Inhibitor': [
            {'name': 'Rofecoxib (Vioxx)', 'similarity': 0.88, 'black_box': True, 'withdrawn': True, 'adverse_events': ['Myocardial Infarction', 'Stroke', 'Thromboembolism']},
            {'name': 'Valdecoxib (Bextra)', 'similarity': 0.84, 'black_box': True, 'withdrawn': True, 'adverse_events': ['Toxic Epidermal Necrolysis', 'Cardiovascular Events']}
        ],
        'Default': [
            {'name': 'Reference Analog Alpha', 'similarity': 0.60, 'black_box': False, 'withdrawn': False, 'adverse_events': ['Mild Nausea', 'Headache']},
            {'name': 'Reference Analog Beta', 'similarity': 0.55, 'black_box': False, 'withdrawn': False, 'adverse_events': ['Transient Transaminitis']}
        ]
    }

    # CYP Enzyme Inhibitor & Inducer Knowledge Base
    CYP_KNOWLEDGE_BASE = {
        'CYP3A4': {
            'strong_inhibitors': ['ketoconazole', 'itraconazole', 'clarithromycin', 'ritonavir', 'cobicistat', 'grapefruit juice'],
            'moderate_inhibitors': ['fluconazole', 'diltiazem', 'verapamil', 'erythromycin', 'amiocarone', 'cimetidine'],
            'strong_inducers': ['rifampin', 'carbamazepine', 'phenytoin', 'st. john\'s wort', 'phenobarbital']
        },
        'CYP2D6': {
            'strong_inhibitors': ['fluoxetine', 'paroxetine', 'bupropion', 'quinidine'],
            'moderate_inhibitors': ['duloxetine', 'terbinafine', 'amiodarone', 'sertraline'],
            'strong_inducers': ['rifampin', 'dexamethasone']
        },
        'CYP2C19': {
            'strong_inhibitors': ['fluvoxamine', 'fluconazole', 'omeprazole', 'ticlopidine'],
            'moderate_inhibitors': ['voriconazole', 'esomeprazole'],
            'strong_inducers': ['rifampin', 'efavirenz']
        },
        'CYP2C9': {
            'strong_inhibitors': ['fluconazole', 'amiodarone', 'miconazole'],
            'moderate_inhibitors': ['sulfamethoxazole', 'metronidazole'],
            'strong_inducers': ['rifampin', 'carbamazepine', 'secobarbital']
        }
    }

    @classmethod
    def analyze_cyp_interactions(cls, drug_pathway, current_medications_str):
        """
        Analyzes volunteer's current medications against the investigational drug's metabolic pathway.
        Detects CYP Inhibition (spikes drug exposure) or CYP Induction (reduces drug efficacy).
        """
        if isinstance(current_medications_str, str):
            meds = [m.strip().lower() for m in current_medications_str.split(',') if m.strip()]
        else:
            meds = [str(m).strip().lower() for m in (current_medications_str or [])]

        pathway_upper = (drug_pathway or 'CYP3A4').upper()
        detected_interactions = []
        cyp_risk_modifier = 0.0

        for cyp_enzyme, profiles in cls.CYP_KNOWLEDGE_BASE.items():
            if cyp_enzyme in pathway_upper:
                # Check Strong Inhibitors
                for med in meds:
                    for inhibitor in profiles['strong_inhibitors']:
                        if inhibitor in med:
                            detected_interactions.append({
                                'enzyme': cyp_enzyme,
                                'medication': med.title(),
                                'type': 'Strong Inhibitor',
                                'severity': 'Major',
                                'effect': f'Inhibits {cyp_enzyme} metabolism. Risk of 2-5x spike in investigational drug AUC and systemic toxicity.',
                                'recommendation': 'Contraindicated or mandatory dose reduction / extended clearance washout.'
                            })
                            cyp_risk_modifier += 0.40

                    for inhibitor in profiles['moderate_inhibitors']:
                        if inhibitor in med:
                            detected_interactions.append({
                                'enzyme': cyp_enzyme,
                                'medication': med.title(),
                                'type': 'Moderate Inhibitor',
                                'severity': 'Moderate',
                                'effect': f'Moderately decreases {cyp_enzyme} clearance. Expect 1.5-2x increased drug plasma levels.',
                                'recommendation': 'Enhanced pharmacokinetic sampling at 6h, 12h, and 24h.'
                            })
                            cyp_risk_modifier += 0.25

                    for inducer in profiles['strong_inducers']:
                        if inducer in med:
                            detected_interactions.append({
                                'enzyme': cyp_enzyme,
                                'medication': med.title(),
                                'type': 'Strong Inducer',
                                'severity': 'Major (Efficacy Loss)',
                                'effect': f'Induces {cyp_enzyme} clearance. Rapid drug elimination may lead to sub-therapeutic efficacy.',
                                'recommendation': 'Consider medication substitute or protocol exclusion.'
                            })
                            cyp_risk_modifier += 0.30

        return detected_interactions, min(cyp_risk_modifier, 0.60)

    @staticmethod
    def evaluate(drug, volunteer=None):
        chem_class = drug.get('chemical_class', 'Default')
        pathway = drug.get('metabolic_pathway', 'CYP3A4')
        toxicity_alerts_raw = drug.get('toxicity_alerts', '')
        
        # Get matching analogs from knowledge base
        analogs = DrugSimilarityModule.ANALOG_DATABASE.get(chem_class, DrugSimilarityModule.ANALOG_DATABASE['Default'])
        
        # Risk factors derived from analogs
        black_box_count = sum(1 for a in analogs if a.get('black_box'))
        withdrawn_count = sum(1 for a in analogs if a.get('withdrawn'))
        max_similarity = max([a.get('similarity', 0.5) for a in analogs], default=0.5)
        
        # Calculate base structural analog risk
        analog_risk = 0.20
        if withdrawn_count > 0:
            analog_risk += 0.45
        if black_box_count > 0:
            analog_risk += 0.25
            
        analog_risk = min(analog_risk * max_similarity, 0.95)

        # Pharmacogenomic & CYP Enzyme Interactions
        cyp_risk = 0.10
        cyp_interactions = []
        if volunteer:
            cyp2d6 = volunteer.get('cyp2d6_genotype', 'Normal')
            cyp2c19 = volunteer.get('cyp2c19_genotype', 'Normal')
            meds_str = volunteer.get('current_medications', '')
            
            # Analyze CYP Inhibitor/Inducer interactions
            cyp_interactions, cyp_mod = DrugSimilarityModule.analyze_cyp_interactions(pathway, meds_str)
            cyp_risk += cyp_mod

            if 'CYP2D6' in pathway.upper() and cyp2d6 in ['Poor Metabolizer', 'Ultra-rapid Metabolizer']:
                cyp_risk += 0.35
                cyp_interactions.append({
                    'enzyme': 'CYP2D6',
                    'medication': f'Genetic Variant ({cyp2d6})',
                    'type': 'Pharmacogenomic Phenotype',
                    'severity': 'Major',
                    'effect': f'Volunteer is CYP2D6 {cyp2d6}. Impaired metabolism will alter drug exposure profile.',
                    'recommendation': 'Adjust starting dose and conduct dense baseline PK sampling.'
                })
            if 'CYP2C19' in pathway.upper() and cyp2c19 in ['Poor Metabolizer']:
                cyp_risk += 0.30
                cyp_interactions.append({
                    'enzyme': 'CYP2C19',
                    'medication': f'Genetic Variant ({cyp2c19})',
                    'type': 'Pharmacogenomic Phenotype',
                    'severity': 'Moderate',
                    'effect': 'Volunteer is CYP2C19 Poor Metabolizer.',
                    'recommendation': 'Close monitoring of hepatic enzymes.'
                })
                
        # Known Drug Toxicity Alerts
        alert_risk = 0.10
        if toxicity_alerts_raw:
            alert_count = len([t for t in toxicity_alerts_raw.split(',') if t.strip()])
            alert_risk += min(alert_count * 0.20, 0.50)

        # Combined Pillar B Score
        pillar_b_score = round(0.45 * analog_risk + 0.35 * cyp_risk + 0.20 * alert_risk, 4)
        pillar_b_score = min(max(pillar_b_score, 0.05), 0.98)

        return {
            'score': pillar_b_score,
            'risk_percentage': round(pillar_b_score * 100, 1),
            'chemical_class': chem_class,
            'metabolic_pathway': pathway,
            'matched_analogs': analogs,
            'analog_risk': round(analog_risk, 4),
            'cyp_pgx_risk': round(cyp_risk, 4),
            'cyp_interactions': cyp_interactions
        }
