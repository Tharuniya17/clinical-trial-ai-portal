import numpy as np
from sklearn.ensemble import GradientBoostingClassifier
import joblib
import os
from config import Config

class AIRiskEngineModule:
    """
    Module 4: AI Risk Engine & Multi-Pillar Model Fusion
    Trains / loads Gradient Boosting Classifier and computes weighted multi-pillar fusion score:
    R = wA * rA + wB * rB + wC * rC
    """
    
    MODEL_PATH = os.path.join(os.path.dirname(__file__), 'gb_risk_model.joblib')

    @classmethod
    def get_or_train_model(cls):
        if os.path.exists(cls.MODEL_PATH):
            try:
                return joblib.load(cls.MODEL_PATH)
            except Exception:
                pass
                
        # Train with DatasetTrainer if not exists
        from modules.dataset_trainer import DatasetTrainer
        DatasetTrainer.train_and_evaluate()
        return joblib.load(cls.MODEL_PATH)
        
        # Features: [age, egfr, alt, qtc, comorbidity_count, med_count, analog_risk, sim_cmax_ratio]
        X = []
        y = []
        for _ in range(n_samples):
            age = np.random.randint(18, 75)
            egfr = np.random.uniform(20, 120)
            alt = np.random.uniform(15, 150)
            qtc = np.random.uniform(380, 520)
            comorbidity_count = np.random.randint(0, 5)
            med_count = np.random.randint(0, 6)
            analog_risk = np.random.uniform(0.1, 0.9)
            sim_cmax_ratio = np.random.uniform(0.4, 2.0)

            # Synthetic risk rule
            risk_idx = (
                (1 if egfr < 60 else 0) +
                (1 if alt > 80 else 0) +
                (1 if qtc > 450 else 0) +
                (1 if comorbidity_count >= 3 else 0) +
                (1 if med_count >= 3 else 0) +
                (1 if analog_risk > 0.6 else 0) +
                (1 if sim_cmax_ratio > 1.2 else 0)
            )
            label = 1 if risk_idx >= 3 else 0
            
            X.append([age, egfr, alt, qtc, comorbidity_count, med_count, analog_risk, sim_cmax_ratio])
            y.append(label)

        model = GradientBoostingClassifier(n_estimators=100, learning_rate=0.1, max_depth=3, random_state=42)
        model.fit(X, y)
        
        try:
            joblib.dump(model, cls.MODEL_PATH)
        except Exception as e:
            print(f"[Model Warning] Could not save model file: {e}")

        return model

    @staticmethod
    def calculate_fusion_risk(pillar_a_score, pillar_b_score, pillar_c_score,
                              w_a=Config.WEIGHT_PILLAR_A,
                              w_b=Config.WEIGHT_PILLAR_B,
                              w_c=Config.WEIGHT_PILLAR_C):
        """
        Fused Risk Calculation:
        R = wA * rA + wB * rB + wC * rC
        """
        total_w = w_a + w_b + w_c
        w_a_norm = w_a / total_w
        w_b_norm = w_b / total_w
        w_c_norm = w_c / total_w

        fused_risk = (w_a_norm * pillar_a_score) + (w_b_norm * pillar_b_score) + (w_c_norm * pillar_c_score)
        fused_risk = round(min(max(fused_risk, 0.0), 1.0), 4)

        if fused_risk >= Config.MEDIUM_RISK_THRESHOLD:
            category = 'High Risk'
            monitoring = 'Intensive In-patient Monitoring & Frequent Blood Sampling Required'
        elif fused_risk >= Config.LOW_RISK_THRESHOLD:
            category = 'Moderate Risk'
            monitoring = 'Enhanced Monitoring (Extended ECG & Lab Markers at 12h/24h)'
        else:
            category = 'Low Risk'
            monitoring = 'Standard Phase-1 Protocol Monitoring'

        return {
            'overall_risk_score': fused_risk,
            'risk_percentage': round(fused_risk * 100, 1),
            'risk_category': category,
            'suggested_monitoring': monitoring,
            'weights_used': {
                'pillar_a': round(w_a_norm, 2),
                'pillar_b': round(w_b_norm, 2),
                'pillar_c': round(w_c_norm, 2)
            }
        }
