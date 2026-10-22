import logging
from typing import Dict, List, Optional, Tuple
import cv2
import numpy as np

logger = logging.getLogger(__name__)


class RATGGovernor:
    """
    Implements Risk-Adaptive Temporal Gating (RATG) governor from Section III-A of the research paper:
      - Equation (1): Scalar risk index r_t in [0, 1] balancing:
          d_t: thumbnail background pixel displacement
          u_t: mean normalized trace of active Kalman covariance matrices
          z_t: boundary proximity to enforcement lines
          a_t: elapsed frames since last detector pass (ceiling K_max)
          q_t: track-level plate uncertainty (proportion lacking locked plate)
      - Equation (2): Trigger primary detection if r_t >= tau_D or (t - t_D) >= K_max or z_t >= tau_Z.
      - Hysteresis margin delta avoids boundary jitter.
    """
    def __init__(
        self,
        weights: List[float] = None,
        tau_d: float = 0.5,
        tau_z: float = 0.7,
        k_max: int = 4,
        hysteresis_delta: float = 0.05,
        thumb_size: Tuple[int, int] = (160, 120),
        zone_distance: float = 150.0
    ):
        # Weights: [w_d, w_u, w_z, w_a, w_q]
        raw_weights = weights or [0.25, 0.20, 0.25, 0.15, 0.15]
        s = sum(raw_weights) if sum(raw_weights) > 0 else 1.0
        self.weights = [w / s for w in raw_weights]

        self.tau_d = tau_d
        self.tau_z = tau_z
        self.k_max = k_max
        self.delta = hysteresis_delta
        self.thumb_size = thumb_size
        self.zone_distance = zone_distance

        self.last_thumbnail: Optional[np.ndarray] = None
        self.t_d: int = 0
        self.last_mode: str = "PRIMARY"
        self.stats = {
            "primary_frames": 0,
            "propagate_frames": 0,
            "total_frames": 0
        }

    def reset(self):
        self.last_thumbnail = None
        self.t_d = 0
        self.last_mode = "PRIMARY"
        self.stats = {"primary_frames": 0, "propagate_frames": 0, "total_frames": 0}

    def compute_thumbnail_diff(self, frame: np.ndarray) -> float:
        """Computes normalized mean absolute pixel difference on 160x120 grayscale thumbnails."""
        if frame is None or frame.size == 0:
            return 0.0
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if len(frame.shape) == 3 else frame
        thumb = cv2.resize(gray, self.thumb_size, interpolation=cv2.INTER_AREA)

        if self.last_thumbnail is None:
            self.last_thumbnail = thumb
            return 1.0 # First frame triggers primary detection

        diff = float(np.mean(np.abs(thumb.astype(np.float32) - self.last_thumbnail.astype(np.float32))))
        self.last_thumbnail = thumb
        # Normalization: typical surveillance dynamic range is 0-25 px mean diff
        return float(np.clip(diff / 25.0, 0.0, 1.0))

    def compute_boundary_proximity(self, tracks: List[dict], stop_line_y: float) -> float:
        """
        Computes z_t: inverse spatial distance from any vehicle bounding box to nearest enforcement boundary.
        """
        if not tracks or stop_line_y is None:
            return 0.0

        max_prox = 0.0
        for trk in tracks:
            bbox = trk.get("bbox", [0, 0, 0, 0])
            # Vehicle bottom edge represents leading point crossing stop line
            bottom_y = bbox[3]
            dist = abs(bottom_y - stop_line_y)
            prox = max(0.0, 1.0 - (dist / max(1.0, self.zone_distance)))
            if prox > max_prox:
                max_prox = prox

        return float(np.clip(max_prox, 0.0, 1.0))

    def evaluate_risk(
        self,
        frame: np.ndarray,
        frame_idx: int,
        tracks: List[dict],
        mean_cov_trace: float,
        stop_line_y: float,
        consensus_cache
    ) -> Tuple[float, dict, bool]:
        """
        Evaluates scalar risk r_t according to Eq. (1) and gating decision g_t according to Eq. (2).
        Returns:
          (risk_score, factors_dict, should_run_primary)
        """
        # 1. d_t: Background pixel displacement
        d_t = self.compute_thumbnail_diff(frame)

        # 2. u_t: Mean normalized trace of active Kalman covariance matrices
        # Trace typically ranges 30 (tight) to 150+ (coasting/uncertain)
        u_t = float(np.clip(mean_cov_trace / 150.0, 0.0, 1.0)) if mean_cov_trace > 0 else 0.0

        # 3. z_t: Inverse spatial distance to enforcement boundary
        z_t = self.compute_boundary_proximity(tracks, stop_line_y)

        # 4. a_t: Elapsed frames since last detector pass, reaching 1.0 at K_max
        elapsed = frame_idx - self.t_d
        a_t = float(min(1.0, elapsed / max(1, self.k_max)))

        # 5. q_t: Proportion of active tracks lacking a locked plate reading
        if tracks:
            unlocked_count = sum(1 for t in tracks if not consensus_cache.is_locked(str(t.get("track_id"))))
            q_t = float(unlocked_count / len(tracks))
        else:
            q_t = 0.0

        # Composite risk scalar index r_t (Eq. 1)
        wd, wu, wz, wa, wq = self.weights
        r_t = float(np.clip(wd * d_t + wu * u_t + wz * z_t + wa * a_t + wq * q_t, 0.0, 1.0))

        factors = {
            "d_t": round(d_t, 3),
            "u_t": round(u_t, 3),
            "z_t": round(z_t, 3),
            "a_t": round(a_t, 3),
            "q_t": round(q_t, 3),
            "r_t": round(r_t, 3),
            "elapsed_since_detector": elapsed
        }

        # Gating Decision (Eq. 2):
        # Fire primary detection if:
        #   - Risk exceeds threshold tau_D, OR
        #   - Detector age reached hard ceiling K_max, OR
        #   - Vehicle in immediate boundary zone (z_t >= tau_Z)
        force_override = (frame_idx <= 1) or (elapsed >= self.k_max) or (z_t >= self.tau_z)

        if self.last_mode == "PRIMARY":
            # Hysteresis: to leave primary mode, risk must drop below tau_d - delta
            should_detect = force_override or (r_t >= (self.tau_d - self.delta))
        else:
            should_detect = force_override or (r_t >= self.tau_d)

        mode = "PRIMARY" if should_detect else "PROPAGATE"
        if should_detect:
            self.t_d = frame_idx
            self.stats["primary_frames"] += 1
        else:
            self.stats["propagate_frames"] += 1

        self.last_mode = mode
        self.stats["total_frames"] += 1

        return r_t, factors, should_detect
