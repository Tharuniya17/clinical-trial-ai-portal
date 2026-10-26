import numpy as np

class ConfidenceModule:
    """
    Module 6: Confidence Scoring & Model Calibration
    Measures concordance across Pillar A, B, and C scores to produce an overall confidence metric.
    Issues warnings if predictions have low confidence or high pillar variance.
    """

    @staticmethod
    def evaluate(pillar_a_score, pillar_b_score, pillar_c_score, volunteer_data, drug_data):
        scores = [pillar_a_score, pillar_b_score, pillar_c_score]
        
        # 1. Variance across pillars (Concordance Metric)
        pillar_std = float(np.std(scores))
        concordance_score = max(0.0, 1.0 - (pillar_std * 2.5))
        
        # 2. Data Completeness Metric
        required_fields = ['egfr', 'alt_u_l', 'qtc_ms', 'weight_kg', 'comorbidities', 'current_medications']
        present_count = sum(1 for f in required_fields if volunteer_data.get(f) is not None)
        completeness_score = present_count / len(required_fields)
        
        # 3. Overall Confidence Calculation
        confidence = (0.60 * concordance_score) + (0.40 * completeness_score)
        confidence_score = round(min(max(confidence, 0.35), 0.98), 4)
        
        # 4. Calibration & Flag Warning
        if confidence_score < 0.60:
            flag = 'Low Confidence Warning - High Inter-Pillar Variance'
            warning_msg = 'Pillar scores show significant disagreement (e.g. low clinical risk vs high drug class risk). Manual expert reviewer panel required.'
        elif confidence_score < 0.78:
            flag = 'Moderate Confidence'
            warning_msg = 'Standard confidence level. Standard reviewer verification recommended.'
        else:
            flag = 'High Confidence'
            warning_msg = 'High concordance across clinical history, drug analogs, and PK simulation.'

        return {
            'confidence_score': confidence_score,
            'confidence_percentage': round(confidence_score * 100, 1),
            'confidence_flag': flag,
            'warning_message': warning_msg,
            'inter_pillar_std_dev': round(pillar_std, 4),
            'data_completeness': round(completeness_score, 2)
        }
