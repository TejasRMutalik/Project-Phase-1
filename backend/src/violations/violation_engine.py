import logging

logger = logging.getLogger(__name__)

class ViolationEngine:
    def __init__(self, config_path: str):
        self.config_path = config_path
        logger.info("Violation Rules Engine initialized.")
        self.rules = {
            "no_helmet": True,
            "signal_jump": True,
            "no_entry": True
        }

    def check_helmet(self, track_info: dict) -> bool:
        """Check if a rider is wearing a helmet (Phase 2 stub)."""
        # Currently a stub, would use a secondary CNN classifier
        if track_info.get("class_id") == 3: # Motorcycle
            return False # Simulating violation
        return True

    def check_signal_jump(self, track_info: dict, light_status: str) -> bool:
        """Check if a vehicle crosses the stop line during a red light."""
        if light_status == "RED" and track_info.get("speed", 0) > 10:
            return True
        return False

    def evaluate_all(self, track_info: dict, context: dict) -> list:
        """Evaluate all rules for a given tracked entity."""
        violations = []
        if not self.check_helmet(track_info):
            violations.append("NO_HELMET")
        
        if self.check_signal_jump(track_info, context.get("light_status", "GREEN")):
            violations.append("SIGNAL_JUMP")
            
        return violations
