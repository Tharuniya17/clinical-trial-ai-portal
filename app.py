import os
import json
from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
from werkzeug.security import check_password_hash, generate_password_hash
from config import Config
from database.db import execute_query, init_db_schema

# Import 7 Project Modules
from modules.eligibility_risk import EligibilityRiskModule
from modules.drug_similarity import DrugSimilarityModule
from modules.pk_simulation import PKSimulationModule
from modules.risk_engine import AIRiskEngineModule
from modules.explainable_ai import ExplainableAIModule
from modules.confidence import ConfidenceModule
from modules.reviewer import ReviewerModule

app = Flask(__name__)
app.config.from_object(Config)

# Ensure DB is ready
init_db_schema()

@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return redirect(url_for('dashboard'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = execute_query("SELECT * FROM users WHERE username = %s", (username,), fetchone=True)
        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['full_name'] = user['full_name']
            session['role'] = user['role']
            flash('Logged in successfully.', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password.', 'danger')
            
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully.', 'info')
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    evaluations = execute_query(
        """
        SELECT e.*, v.volunteer_code, v.age, v.gender, d.drug_name, d.drug_code, t.trial_name, t.trial_code
        FROM risk_evaluations e
        JOIN volunteers v ON e.volunteer_id = v.id
        JOIN investigational_drugs d ON e.investigational_drug_id = d.id
        JOIN clinical_trials t ON e.trial_id = t.id
        ORDER BY e.evaluated_at DESC
        """,
        fetchall=True
    ) or []

    trials = execute_query("SELECT * FROM clinical_trials ORDER BY id DESC", fetchall=True) or []
    volunteers = execute_query("SELECT * FROM volunteers ORDER BY id DESC", fetchall=True) or []
    drugs = execute_query("SELECT * FROM investigational_drugs ORDER BY id DESC", fetchall=True) or []

    return render_template('dashboard.html',
                           evaluations=evaluations,
                           trials=trials,
                           volunteers=volunteers,
                           drugs=drugs)

@app.route('/trial/new', methods=['GET', 'POST'])
def new_trial():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    if request.method == 'POST':
        code = request.form.get('trial_code')
        existing = execute_query("SELECT id FROM clinical_trials WHERE trial_code = %s", (code,), fetchone=True)
        if existing:
            flash(f'Trial protocol with code "{code}" already exists. Please choose a different code.', 'warning')
            return render_template('trial_entry.html')

        name = request.form.get('trial_name')
        phase = request.form.get('phase')
        indication = request.form.get('target_indication')
        sponsor = request.form.get('sponsor')
        
        try:
            execute_query(
                "INSERT INTO clinical_trials (trial_code, trial_name, phase, target_indication, sponsor) VALUES (%s, %s, %s, %s, %s)",
                (code, name, phase, indication, sponsor),
                commit=True
            )
            flash('New trial protocol registered successfully!', 'success')
            return redirect(url_for('dashboard'))
        except Exception as e:
            flash(f'Trial registration error: {e}', 'danger')
            return render_template('trial_entry.html')
        
    return render_template('trial_entry.html')

@app.route('/volunteer/new', methods=['GET', 'POST'])
def new_volunteer():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    if request.method == 'POST':
        code = request.form.get('volunteer_code')
        
        # Check if volunteer code already exists
        existing = execute_query("SELECT id FROM volunteers WHERE volunteer_code = %s", (code,), fetchone=True)
        if existing:
            flash(f'Volunteer code "{code}" is already registered. Please specify a unique volunteer code.', 'warning')
            return render_template('volunteer_entry.html')

        age = int(request.form.get('age', 30))
        gender = request.form.get('gender')
        weight = float(request.form.get('weight_kg', 70))
        height = float(request.form.get('height_cm', 175))
        bmi = round(weight / ((height/100)**2), 1)
        
        egfr = float(request.form.get('egfr', 90))
        alt = float(request.form.get('alt_u_l', 25))
        ast = float(request.form.get('ast_u_l', 25))
        bili = float(request.form.get('bilirubin_mg_dl', 0.8))
        qtc = float(request.form.get('qtc_ms', 410))
        sbp = int(request.form.get('systolic_bp', 120))
        dbp = int(request.form.get('diastolic_bp', 80))
        hr = int(request.form.get('heart_rate', 70))
        
        comorbidities = request.form.get('comorbidities', '')
        meds = request.form.get('current_medications', '')
        adrs = request.form.get('previous_adverse_reactions', '')
        cyp2d6 = request.form.get('cyp2d6_genotype', 'Normal')
        cyp2c19 = request.form.get('cyp2c19_genotype', 'Normal')
        
        try:
            execute_query(
                """
                INSERT INTO volunteers (
                    volunteer_code, age, gender, weight_kg, height_cm, bmi,
                    egfr, alt_u_l, ast_u_l, bilirubin_mg_dl, qtc_ms,
                    systolic_bp, diastolic_bp, heart_rate, comorbidities,
                    current_medications, previous_adverse_reactions,
                    cyp2d6_genotype, cyp2c19_genotype
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (code, age, gender, weight, height, bmi, egfr, alt, ast, bili, qtc,
                 sbp, dbp, hr, comorbidities, meds, adrs, cyp2d6, cyp2c19),
                commit=True
            )
            flash(f'Volunteer {code} registered successfully!', 'success')
            return redirect(url_for('dashboard'))
        except Exception as e:
            flash(f'Registration error: {e}', 'danger')
            return render_template('volunteer_entry.html')

    return render_template('volunteer_entry.html')

@app.route('/drug/new', methods=['GET', 'POST'])
def new_drug():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    if request.method == 'POST':
        code = request.form.get('drug_code')
        
        # Check if drug code already exists
        existing = execute_query("SELECT id FROM investigational_drugs WHERE drug_code = %s", (code,), fetchone=True)
        if existing:
            flash(f'Drug Code "{code}" is already registered. Please choose a different drug code.', 'warning')
            return render_template('drug_entry.html')

        name = request.form.get('drug_name')
        chem_class = request.form.get('chemical_class')
        moa = request.form.get('mechanism_of_action')
        pathway = request.form.get('metabolic_pathway')
        mw = float(request.form.get('molecular_weight', 350))
        logP = float(request.form.get('logP', 2.0))
        pb = float(request.form.get('protein_binding', 0.85))
        hl = float(request.form.get('target_half_life', 6.0))
        alerts = request.form.get('toxicity_alerts', '')
        
        try:
            d_id = execute_query(
                """
                INSERT INTO investigational_drugs (
                    drug_code, drug_name, chemical_class, mechanism_of_action,
                    metabolic_pathway, molecular_weight, logP, protein_binding,
                    target_half_life, toxicity_alerts
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (code, name, chem_class, moa, pathway, mw, logP, pb, hl, alerts),
                commit=True
            )
            flash(f'Investigational Drug {name} registered successfully!', 'success')
            return redirect(url_for('dashboard'))
        except Exception as e:
            flash(f'Drug registration error: {e}', 'danger')
            return render_template('drug_entry.html')

    return render_template('drug_entry.html')

@app.route('/evaluate', methods=['GET', 'POST'])
def run_evaluation():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    if request.method == 'POST':
        trial_id = int(request.form.get('trial_id'))
        volunteer_id = int(request.form.get('volunteer_id'))
        drug_id = int(request.form.get('drug_id'))
        
        # 1. Fetch DB records
        volunteer = execute_query("SELECT * FROM volunteers WHERE id = %s", (volunteer_id,), fetchone=True)
        drug = execute_query("SELECT * FROM investigational_drugs WHERE id = %s", (drug_id,), fetchone=True)
        trial = execute_query("SELECT * FROM clinical_trials WHERE id = %s", (trial_id,), fetchone=True)
        
        # 2. Run Module 1 (Pillar A)
        res_a = EligibilityRiskModule.evaluate(volunteer)
        
        # 3. Run Module 2 (Pillar B)
        res_b = DrugSimilarityModule.evaluate(drug, volunteer)
        
        # 4. Run Module 3 (Pillar C PK Simulation)
        res_c = PKSimulationModule.simulate(volunteer, drug)
        
        # 5. Run Module 4 (AI Risk Engine & Fusion)
        fusion = AIRiskEngineModule.calculate_fusion_risk(res_a['score'], res_b['score'], res_c['score'])
        
        # 6. Run Module 5 (SHAP Explainability)
        gb_model = AIRiskEngineModule.get_or_train_model()
        med_count = len([m for m in (volunteer.get('current_medications') or '').split(',') if m.strip()])
        comorbidity_count = len([c for c in (volunteer.get('comorbidities') or '').split(',') if c.strip()])
        
        shap_feature_dict = {
            'age': volunteer['age'],
            'egfr': volunteer['egfr'],
            'alt': volunteer['alt_u_l'],
            'qtc': volunteer['qtc_ms'],
            'comorbidity_count': comorbidity_count,
            'med_count': med_count,
            'analog_risk': res_b['score'],
            'sim_cmax_ratio': res_c['pk_parameters']['toxic_exposure_ratio']
        }
        shap_res = ExplainableAIModule.explain(gb_model, shap_feature_dict)
        
        # 7. Run Module 6 (Confidence & Calibration)
        conf_res = ConfidenceModule.evaluate(res_a['score'], res_b['score'], res_c['score'], volunteer, drug)
        
        # 8. Store Evaluation in DB
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
                trial_id, volunteer_id, drug_id,
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
        
        # Log Audit Trail Entry
        execute_query(
            "INSERT INTO audit_logs (evaluation_id, user_id, action, previous_status, new_status, comments) VALUES (%s, %s, %s, %s, %s, %s)",
            (eval_id, session['user_id'], 'EVALUATION_GENERATED', 'None', 'Pending Review', 'AI Risk Screening Assessment Generated'),
            commit=True
        )

        flash('AI Risk Evaluation generated successfully!', 'success')
        return redirect(url_for('view_analysis', eval_id=eval_id))

    trials = execute_query("SELECT * FROM clinical_trials", fetchall=True) or []
    volunteers = execute_query("SELECT * FROM volunteers", fetchall=True) or []
    drugs = execute_query("SELECT * FROM investigational_drugs", fetchall=True) or []
    return render_template('evaluate.html', trials=trials, volunteers=volunteers, drugs=drugs)

@app.route('/analysis/<int:eval_id>')
def view_analysis(eval_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    eval_rec = execute_query(
        """
        SELECT e.*, v.volunteer_code, v.age, v.gender, v.weight_kg, v.height_cm, v.bmi, v.egfr, v.alt_u_l, v.ast_u_l, v.qtc_ms,
               v.comorbidities, v.current_medications, v.previous_adverse_reactions, v.cyp2d6_genotype, v.cyp2c19_genotype,
               d.drug_name, d.drug_code, d.chemical_class, d.mechanism_of_action, d.metabolic_pathway, d.toxicity_alerts,
               t.trial_name, t.trial_code, t.phase
        FROM risk_evaluations e
        JOIN volunteers v ON e.volunteer_id = v.id
        JOIN investigational_drugs d ON e.investigational_drug_id = d.id
        JOIN clinical_trials t ON e.trial_id = t.id
        WHERE e.id = %s
        """,
        (eval_id,),
        fetchone=True
    )
    
    if not eval_rec:
        flash('Evaluation record not found.', 'danger')
        return redirect(url_for('dashboard'))

    # Parse JSON payloads
    shap_data = json.loads(eval_rec['shap_json']) if eval_rec['shap_json'] else {}
    pk_sim_data = json.loads(eval_rec['pk_sim_json']) if eval_rec['pk_sim_json'] else {}

    # Calculate pillar component breakdowns for view
    res_a = EligibilityRiskModule.evaluate(eval_rec)
    res_b = DrugSimilarityModule.evaluate(eval_rec, eval_rec)
    conf_res = ConfidenceModule.evaluate(eval_rec['pillar_a_score'], eval_rec['pillar_b_score'], eval_rec['pillar_c_score'], eval_rec, eval_rec)
    
    audit_trail = ReviewerModule.get_audit_trail(eval_id)

    return render_template('analysis.html',
                           eval_rec=eval_rec,
                           shap_data=shap_data,
                           pk_sim_data=pk_sim_data,
                           pillar_a=res_a,
                           pillar_b=res_b,
                           confidence=conf_res,
                           audit_trail=audit_trail)

@app.route('/api/reviewer-decision', methods=['POST'])
def submit_decision():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
        
    data = request.json or {}
    eval_id = data.get('evaluation_id')
    decision = data.get('decision')
    notes = data.get('notes', '')
    
    if not eval_id or not decision:
        return jsonify({'error': 'Missing evaluation_id or decision'}), 400
        
    res = ReviewerModule.record_decision(eval_id, session['user_id'], decision, notes)
    return jsonify(res)

@app.route('/model-metrics')
def view_model_metrics():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    from modules.dataset_trainer import DatasetTrainer
    metrics_path = DatasetTrainer.METRICS_PATH
    
    if not os.path.exists(metrics_path):
        metrics = DatasetTrainer.train_and_evaluate()
    else:
        with open(metrics_path, 'r') as f:
            metrics = json.load(f)

    return render_template('model_metrics.html', metrics=metrics)

@app.route('/model-metrics/retrain', methods=['POST'])
def retrain_model_route():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    from modules.dataset_trainer import DatasetTrainer
    metrics = DatasetTrainer.train_and_evaluate()
    flash(f'Model re-trained successfully on {metrics["n_samples"]} benchmark samples! Accuracy: {metrics["accuracy_mean"]*100:.2f}%, AUC: {metrics["roc_auc_mean"]}', 'success')
    return redirect(url_for('view_model_metrics'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
