// The speed model.

/* ---------- speed model: power to speed, against gravity, rolling resistance and air drag ---------- */
export const MASS = 80, CRR = 0.004, DRAG = 0.5 * 1.2 * 0.32;     // rider and bike kg; rolling resistance; half air density x CdA
// Descents count half, and above 54 km/h (15 m/s) the rider feathers the brakes, so speed does not run away downhill.
// climb: rise per metre along the road (sine of the slope). Returns the new speed in m/s, never below 0.5.
export function nextSpeed(v, power, climb, dt) {
  const slope = climb > 0 ? climb : climb * 0.5, brake = v > 15 ? MASS * 0.5 * (v - 15) : 0;
  const force = power / Math.max(v, 2) - MASS * 9.81 * (slope + CRR) - DRAG * v * v - brake;
  return Math.max(0.5, v + force / MASS * dt);
}

