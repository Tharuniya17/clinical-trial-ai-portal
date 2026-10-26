from database.db import execute_query
import json

class ReviewerModule:
    """
    Module 7: Human Reviewer Decision & Audit Trail Services
    Handles reviewer override, comments, protocol modification flags, and audit history logging.
    """

    @staticmethod
    def record_decision(evaluation_id, user_id, decision, notes):
        """
        Updates evaluation record with reviewer decision and logs an entry in audit_logs.
        """
        # 1. Fetch current status
        current_eval = execute_query(
            "SELECT reviewer_decision FROM risk_evaluations WHERE id = %s",
            (evaluation_id,),
            fetchone=True
        )
        prev_status = current_eval.get('reviewer_decision', 'Pending Review') if current_eval else 'Pending Review'

        # 2. Update decision in risk_evaluations
        execute_query(
            """
            UPDATE risk_evaluations
            SET reviewer_decision = %s, reviewer_notes = %s, reviewed_by = %s
            WHERE id = %s
            """,
            (decision, notes, user_id, evaluation_id),
            commit=True
        )

        # 3. Log into audit_logs
        execute_query(
            """
            INSERT INTO audit_logs (evaluation_id, user_id, action, previous_status, new_status, comments)
            WHERE_PLACEHOLDER
            VALUES (%s, %s, %s, %s, %s, %s)
            """.replace('WHERE_PLACEHOLDER', ''),
            (evaluation_id, user_id, 'REVIEWER_DECISION_SUBMITTED', prev_status, decision, notes),
            commit=True
        )

        return {
            'status': 'success',
            'evaluation_id': evaluation_id,
            'previous_status': prev_status,
            'new_status': decision
        }

    @staticmethod
    def get_audit_trail(evaluation_id):
        """
        Retrieves complete audit trail for a specific evaluation.
        """
        logs = execute_query(
            """
            SELECT a.*, u.full_name as reviewer_name, u.role as reviewer_role
            FROM audit_logs a
            LEFT JOIN users u ON a.user_id = u.id
            WHERE a.evaluation_id = %s
            ORDER BY a.timestamp DESC
            """,
            (evaluation_id,),
            fetchall=True
        )
        return logs or []
