import numpy as np

class BKT:
    """Bayesian Knowledge Tracing model for tracking student mastery."""
    
    def __init__(self):
        self.p_learned = 0.2  # Initial probability of knowing the skill
        self.p_learn = 0.1    # Probability of learning after a question
        self.p_guess = 0.2    # Probability of guessing correctly
        self.p_slip = 0.1     # Probability of slipping (wrong despite knowing)

    def update(self, correct):
        """Update knowledge state based on correct/incorrect answer."""
        if correct:
            p_correct = (self.p_learned * (1 - self.p_slip)) + ((1 - self.p_learned) * self.p_guess)
            self.p_learned = (self.p_learned * (1 - self.p_slip)) / p_correct
        else:
            p_incorrect = (self.p_learned * self.p_slip) + ((1 - self.p_learned) * (1 - self.p_guess))
            self.p_learned = (self.p_learned * self.p_slip) / p_incorrect
        self.p_learned = min(self.p_learned + self.p_learn * (1 - self.p_learned), 1.0)
        return self.p_learned

def select_next_module(bkt_dict):
    """Select the next module (topic) based on weakest p_learned score."""
    if not bkt_dict:
        return None
    return min(bkt_dict, key=lambda topic: bkt_dict[topic].p_learned)