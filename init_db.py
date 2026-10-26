import json
from database.db import init_db_schema, execute_query
from werkzeug.security import generate_password_hash

def seed_sample_data():
    print("[Seed] Initializing DB schema...")
    init_db_schema()

    # 1. Seed Reviewer User
    user_exists = execute_query("SELECT id FROM users WHERE username = %s", ('dr_smith',), fetchone=True)
    if not user_exists:
        pw_hash = generate_password_hash("password123")
        user_id = execute_query(
            "INSERT INTO users (username, password_hash, full_name, role) VALUES (%s, %s, %s, %s)",
            ('dr_smith', pw_hash, 'Dr. Marcus Vance (Principal Investigator)', 'reviewer'),
            commit=True
        )
        print(f"[Seed] Created default reviewer user 'dr_smith' (ID: {user_id}).")

    # 2. Seed Sample Clinical Trial
    trial_exists = execute_query("SELECT id FROM clinical_trials WHERE trial_code = %s", ('CT-2026-NEXUS-01',), fetchone=True)
    if not trial_exists:
        trial_id = execute_query(
            """
            INSERT INTO clinical_trials (trial_code, trial_name, phase, target_indication, sponsor)
            VALUES (%s, %s, %s, %s, %s)
            """,
            ('CT-2026-NEXUS-01', 'Phase-1 First-in-Human Trial of Novel Kinase Inhibitor VX-409', 'Phase 1', 'Advanced Solid Tumors', 'Aegis BioPharma'),
            commit=True
        )
        print(f"[Seed] Created sample trial 'CT-2026-NEXUS-01' (ID: {trial_id}).")
    else:
        trial_id = trial_exists['id']

    # 3. Seed Sample Investigational Drug
    drug_exists = execute_query("SELECT id FROM investigational_drugs WHERE drug_code = %s", ('VX-409',), fetchone=True)
    if not drug_exists:
        drug_id = execute_query(
            """
            INSERT INTO investigational_drugs 
            (drug_code, drug_name, chemical_class, mechanism_of_action, metabolic_pathway, molecular_weight, logP, protein_binding, target_half_life, toxicity_alerts)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                'VX-409',
                'Vabocarib (VX-409)',
                'Kinase Inhibitor',
                'Dual VEGFR2 / c-MET Receptor Tyrosine Kinase Inhibitor',
                'CYP3A4 / CYP2D6',
                465.5,
                3.2,
                0.92,
                7.5,
                'QTc Prolongation, Hepatotoxicity Alert, Hypertension'
            ),
            commit=True
        )
        print(f"[Seed] Created investigational drug 'VX-409' (ID: {drug_id}).")
        
        # Seed drug analogs
        analogs = [
            ('Sunitinib', 0.82, 'Cardiotoxicity, Hepatotoxicity, Hypertension', 0, 1),
            ('Sorafenib', 0.78, 'Cardiac Ischemia, Bleeding', 0, 1),
            ('Regorafenib', 0.71, 'Severe Hepatotoxicity', 0, 1)
        ]
        for name, sim, aes, w, bb in analogs:
            execute_query(
                """
                INSERT INTO drug_analogs (investigational_drug_id, analog_name, similarity_score, known_adverse_events, withdrawn_status, black_box_warning)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (drug_id, name, sim, aes, w, bb),
                commit=True
            )
    else:
        drug_id = drug_exists['id']

    # 4. Seed Sample Volunteers (Different risk profiles)
    sample_volunteers = [
        {
            'volunteer_code': 'VOL-2026-101',
            'age': 34,
            'gender': 'Male',
            'weight_kg': 76.0,
            'height_cm': 178.0,
            'bmi': 24.0,
            'egfr': 98.0,
            'alt_u_l': 22.0,
            'ast_u_l': 20.0,
            'bilirubin_mg_dl': 0.7,
            'qtc_ms': 405.0,
            'systolic_bp': 118,
            'diastolic_bp': 76,
            'heart_rate': 68,
            'comorbidities': 'None',
            'current_medications': 'None',
            'previous_adverse_reactions': 'None',
            'cyp2d6_genotype': 'Normal',
            'cyp2c19_genotype': 'Normal'
        },
        {
            'volunteer_code': 'VOL-2026-102',
            'age': 58,
            'gender': 'Female',
            'weight_kg': 68.0,
            'height_cm': 162.0,
            'bmi': 25.9,
            'egfr': 52.0,
            'alt_u_l': 65.0,
            'ast_u_l': 58.0,
            'bilirubin_mg_dl': 1.4,
            'qtc_ms': 442.0,
            'systolic_bp': 144,
            'diastolic_bp': 92,
            'heart_rate': 78,
            'comorbidities': 'Hypertension, Mild Renal Insufficiency',
            'current_medications': 'Amlodipine 5mg, Metoprolol 25mg, Atorvastatin 20mg',
            'previous_adverse_reactions': 'ACE Inhibitor Induced Cough',
            'cyp2d6_genotype': 'Poor Metabolizer',
            'cyp2c19_genotype': 'Normal'
        }
    ]

    for vol in sample_volunteers:
        vol_exists = execute_query("SELECT id FROM volunteers WHERE volunteer_code = %s", (vol['volunteer_code'],), fetchone=True)
        if not vol_exists:
            v_id = execute_query(
                """
                INSERT INTO volunteers (
                    volunteer_code, age, gender, weight_kg, height_cm, bmi,
                    egfr, alt_u_l, ast_u_l, bilirubin_mg_dl, qtc_ms,
                    systolic_bp, diastolic_bp, heart_rate, comorbidities,
                    current_medications, previous_adverse_reactions,
                    cyp2d6_genotype, cyp2c19_genotype
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    vol['volunteer_code'], vol['age'], vol['gender'], vol['weight_kg'], vol['height_cm'], vol['bmi'],
                    vol['egfr'], vol['alt_u_l'], vol['ast_u_l'], vol['bilirubin_mg_dl'], vol['qtc_ms'],
                    vol['systolic_bp'], vol['diastolic_bp'], vol['heart_rate'], vol['comorbidities'],
                    vol['current_medications'], vol['previous_adverse_reactions'],
                    vol['cyp2d6_genotype'], vol['cyp2c19_genotype']
                ),
                commit=True
            )
            print(f"[Seed] Created sample volunteer '{vol['volunteer_code']}' (ID: {v_id}).")

    print("[Seed] Database initialization and seeding complete.")

if __name__ == '__main__':
    seed_sample_data()
