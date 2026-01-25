# irt.py
import numpy as np
from scipy.optimize import minimize
from scipy.stats import norm
from typing import List, Dict, Tuple
import logging

logger = logging.getLogger(__name__)

class ThreePLIRT:
    """3-Parameter Logistic Item Response Theory Model"""
    
    def __init__(self):
        self.theta = None  # User ability estimates
        self.b = None      # Item difficulties
        self.a = None      # Item discriminations
        self.c = None      # Guessing parameters
    
    def probability_correct(self, theta: float, b: float, a: float = 1.0, c: float = 0.25) -> float:
        """Calculate probability of correct response using 3PL model"""
        z = a * (theta - b)
        return c + (1 - c) / (1 + np.exp(-z))
    
    def estimate_ability(self, responses: List[Dict], initial_theta: float = 0.0) -> float:
        """
        Estimate user ability using MLE
        
        Args:
            responses: List of dicts with 'correct' (bool), 'difficulty', 
                      'discrimination', 'guessing'
            initial_theta: Initial ability estimate
        """
        if not responses:
            return initial_theta

        def negative_log_likelihood(theta):
            ll = 0
            for r in responses:
                p = self.probability_correct(
                    theta, 
                    r['difficulty'], 
                    r.get('discrimination', 1.0), 
                    r.get('guessing', 0.25)
                )
                # Avoid log(0)
                p = max(min(p, 1 - 1e-10), 1e-10)
                if r['correct']:
                    ll += np.log(p)
                else:
                    ll += np.log(1 - p)
            return -ll
        
        # Constrained optimization
        try:
            result = minimize(
                negative_log_likelihood,
                initial_theta,
                bounds=[(-4, 4)],  # Slightly wider bounds
                method='L-BFGS-B'
            )
            return float(result.x[0])
        except Exception as e:
            logger.error(f"IRT estimation failed: {e}")
            return initial_theta
    
    def update_item_parameters(self, all_responses: List[Dict]) -> Dict:
        """Update item parameters using EM algorithm (simplified)"""
        # This is a simplified version - full EM would be more complex
        items = {}
        for response in all_responses:
            q_id = response['question_id']
            if q_id not in items:
                items[q_id] = {
                    'responses': [],
                    'correct': 0,
                    'total': 0
                }
            items[q_id]['responses'].append(response)
            items[q_id]['total'] += 1
            if response['correct']:
                items[q_id]['correct'] += 1
        
        # Simple estimation (would need full EM for production)
        updated_params = {}
        for q_id, data in items.items():
            p_correct = data['correct'] / data['total']
            # Map proportion correct to difficulty (simplified)
            difficulty = norm.ppf(1 - p_correct)  # Inverse CDF of normal
            updated_params[q_id] = {
                'difficulty': float(difficulty),
                'discrimination': 1.0,  # Placeholder
                'guessing': 0.25  # Placeholder
            }
        
        return updated_params