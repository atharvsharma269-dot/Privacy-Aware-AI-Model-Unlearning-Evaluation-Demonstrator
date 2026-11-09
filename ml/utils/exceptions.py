"""
Custom domain exceptions for machine learning and experiment lifecycle management.
"""

class CancellationError(Exception):
    """Raised when an active training, unlearning, or evaluation job is cancelled by the user."""
    def __init__(self, message: str = "Operation was cancelled by user request"):
        super().__init__(message)
        self.message = message
