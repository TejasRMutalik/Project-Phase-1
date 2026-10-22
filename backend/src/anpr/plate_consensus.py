import re
import math
import logging
from typing import Dict, List, Optional, Tuple
import cv2
import numpy as np

logger = logging.getLogger(__name__)


def levenshtein_distance(s1: str, s2: str) -> int:
    """Compute Levenshtein edit distance between two strings."""
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)
    if len(s2) == 0:
        return len(s1)

    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]


class OCRCandidate:
    def __init__(self, text: str, confidence: float, sharpness: float, syntax_valid: int, weight: float):
        self.text = text
        self.confidence = confidence
        self.sharpness = sharpness
        self.syntax_valid = syntax_valid
        self.weight = weight


class TrackLevelOCRConsensus:
    """
    Implements Track-Level OCR Consensus Cache from Section III-B of RATG-OC paper:
      - Laplacian sharpness filtering (threshold tau_L)
      - Non-linear vote weighting: omega_ij = c_ij^alpha * log(1 + h_ij) * [lambda + (1 - lambda) * v_ij]
      - Levenshtein-distance-1 clustering
      - Lifetime consensus plate resolution: s_hat = argmax_C sum(omega_ij)
      - Permanent plate locking when cluster weight >= tau_C and leads runner-up by margin m
      - Discontinuous velocity check to mitigate close-proximity identity swaps
    """
    def __init__(
        self,
        tau_l: float = 100.0,
        tau_c: float = 2.0,
        stability_margin: float = 0.5,
        cache_limit: int = 10,
        alpha: float = 1.0,
        lambda_param: float = 0.5
    ):
        self.tau_l = tau_l
        self.tau_c = tau_c
        self.stability_margin = stability_margin
        self.cache_limit = cache_limit
        self.alpha = alpha
        self.lambda_param = lambda_param

        # track_id -> list of OCRCandidate
        self.votes: Dict[str, List[OCRCandidate]] = {}
        # track_id -> {"plate": str, "confidence": float, "locked": bool, "cluster_weight": float}
        self.consensus: Dict[str, dict] = {}
        # track_id -> list of (cx, cy, frame_idx) for velocity vector checking
        self.velocity_history: Dict[str, List[Tuple[float, float, int]]] = {}

    @staticmethod
    def compute_laplacian_sharpness(image: np.ndarray) -> float:
        """Computes variance of Laplacian on grayscale image crop."""
        if image is None or image.size == 0:
            return 0.0
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
        return float(cv2.Laplacian(gray, cv2.CV_64F).var())

    @staticmethod
    def check_syntax(text: str) -> int:
        """
        Adherence check to standard registration syntax (e.g. 2 letters, 2 digits, 2 letters, 4 digits).
        Returns 1 if matches valid plate pattern, 0 otherwise.
        """
        if not text or text == "UNKNOWN":
            return 0
        cleaned = re.sub(r'[^A-Z0-9]', '', text.upper())
        # Indian standard: 2 letters (state), 1-2 digits (RTO), 1-2 letters, 4 digits (e.g. KA01AB1234 or DL3CAA1234)
        if re.match(r'^[A-Z]{2}[0-9]{1,2}[A-Z]{0,3}[0-9]{4}$', cleaned):
            return 1
        # Generic vehicle plate: 6 to 10 alphanumeric characters
        if 6 <= len(cleaned) <= 10 and any(c.isalpha() for c in cleaned) and any(c.isdigit() for c in cleaned):
            return 1
        return 0

    def compute_weight(self, confidence: float, sharpness: float, syntax_valid: int) -> float:
        """
        Eq. (3): omega_ij = c_ij^alpha * log(1 + h_ij) * [lambda + (1 - lambda) * v_ij]
        """
        conf_term = math.pow(max(0.0, float(confidence)), self.alpha)
        sharp_term = math.log(1.0 + max(0.0, float(sharpness)))
        syntax_term = self.lambda_param + (1.0 - self.lambda_param) * float(syntax_valid)
        return float(conf_term * sharp_term * syntax_term)

    def is_locked(self, track_id: str) -> bool:
        """Check if plate for track_id is already permanently locked."""
        tid = str(track_id)
        return self.consensus.get(tid, {}).get("locked", False)

    def get_plate(self, track_id: str) -> Tuple[str, float, bool]:
        """Returns (plate_number, confidence, is_locked) for track_id."""
        tid = str(track_id)
        if tid in self.consensus:
            entry = self.consensus[tid]
            return entry.get("plate", "UNKNOWN"), entry.get("confidence", 0.0), entry.get("locked", False)
        return "UNKNOWN", 0.0, False

    def update_velocity_and_check_swap(self, track_id: str, bbox: list, frame_idx: int) -> bool:
        """
        Track-level velocity vector continuity check to mitigate ID swaps in dense stop-line queues.
        If spatial velocity angle shifts abruptly (> 90 deg) or speed spikes discontinuous,
        we invalidate the consensus buffer for this track.
        Returns True if buffer was invalidated.
        """
        tid = str(track_id)
        cx = (bbox[0] + bbox[2]) / 2.0
        cy = (bbox[1] + bbox[3]) / 2.0

        if tid not in self.velocity_history:
            self.velocity_history[tid] = [(cx, cy, frame_idx)]
            return False

        hist = self.velocity_history[tid]
        last_cx, last_cy, last_f = hist[-1]
        df = frame_idx - last_f
        if df <= 0:
            return False

        vx = (cx - last_cx) / df
        vy = (cy - last_cy) / df
        hist.append((cx, cy, frame_idx))
        if len(hist) > 5:
            hist.pop(0)

        # Need at least two velocity vectors to compare direction change
        if len(hist) >= 3:
            p0, p1, p2 = hist[-3], hist[-2], hist[-1]
            df1 = max(1, p1[2] - p0[2])
            df2 = max(1, p2[2] - p1[2])
            v1 = np.array([(p1[0] - p0[0]) / df1, (p1[1] - p0[1]) / df1])
            v2 = np.array([(p2[0] - p1[0]) / df2, (p2[1] - p1[1]) / df2])

            norm1 = np.linalg.norm(v1)
            norm2 = np.linalg.norm(v2)
            if norm1 > 3.0 and norm2 > 3.0:
                dot = np.dot(v1, v2) / (norm1 * norm2)
                dot = np.clip(dot, -1.0, 1.0)
                angle_rad = np.arccos(dot)
                # If velocity vector shifts abruptly (> 100 degrees), suspected ID swap
                if angle_rad > np.radians(100):
                    logger.debug(f"Velocity vector discontinuity on track {tid} ({np.degrees(angle_rad):.1f} deg). Invalidating OCR cache.")
                    self.invalidate_track(tid)
                    return True
        return False

    def invalidate_track(self, track_id: str):
        """Invalidate voting cache and unlock plate for track_id."""
        tid = str(track_id)
        self.votes.pop(tid, None)
        self.consensus.pop(tid, None)

    def add_candidate(self, track_id: str, text: str, confidence: float, crop: np.ndarray) -> Tuple[str, float, bool]:
        """
        Process new OCR candidate string on track_id:
        Calculates sharpness, syntax validity, weight, groups into Levenshtein equivalence clusters,
        and resolves consensus plate.
        """
        tid = str(track_id)
        if self.is_locked(tid):
            entry = self.consensus[tid]
            return entry["plate"], entry["confidence"], True

        if not text or text == "UNKNOWN" or confidence <= 0:
            return self.get_plate(tid)

        sharpness = self.compute_laplacian_sharpness(crop)
        syntax_valid = self.check_syntax(text)
        weight = self.compute_weight(confidence, sharpness, syntax_valid)

        if tid not in self.votes:
            self.votes[tid] = []

        candidate = OCRCandidate(text, confidence, sharpness, syntax_valid, weight)
        self.votes[tid].append(candidate)

        # Enforce maximum cache limit B
        if len(self.votes[tid]) > self.cache_limit:
            self.votes[tid].pop(0)

        # Group candidates into Levenshtein distance <= 1 clusters
        clusters: List[List[OCRCandidate]] = []
        for cand in self.votes[tid]:
            matched_cluster = None
            for cl in clusters:
                # Compare against representative (first item) of cluster
                if levenshtein_distance(cand.text, cl[0].text) <= 1:
                    matched_cluster = cl
                    break
            if matched_cluster is not None:
                matched_cluster.append(cand)
            else:
                clusters.append([cand])

        # Score clusters: sum(weight) for each cluster
        cluster_scores = []
        for cl in clusters:
            tot_weight = sum(c.weight for c in cl)
            # Pick representative string with highest single confidence in cluster
            best_cand = max(cl, key=lambda c: c.confidence)
            avg_conf = sum(c.confidence for c in cl) / len(cl)
            cluster_scores.append((tot_weight, best_cand.text, avg_conf, cl))

        # Sort clusters by total weight descending
        cluster_scores.sort(key=lambda x: x[0], reverse=True)

        winning_score, winning_text, winning_conf, winning_cluster = cluster_scores[0]
        runner_up_score = cluster_scores[1][0] if len(cluster_scores) > 1 else 0.0

        # Permanent lock condition: winning_score >= tau_c AND (winning_score - runner_up_score) >= stability_margin
        is_locked = False
        if winning_score >= self.tau_c and (winning_score - runner_up_score) >= self.stability_margin:
            is_locked = True
            logger.info(f"RATG-OC: Permanently locked plate for track {tid} -> {winning_text} (Score: {winning_score:.2f})")

        self.consensus[tid] = {
            "plate": winning_text,
            "confidence": round(float(winning_conf), 2),
            "locked": is_locked,
            "cluster_weight": round(float(winning_score), 2)
        }

        return winning_text, float(winning_conf), is_locked
