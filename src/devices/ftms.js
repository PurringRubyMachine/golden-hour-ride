// Fitness Machine Service (FTMS) messages for smart trainers.
import { CRR, DRAG } from '../physics.js';

export const FTMS = 0x1826, FTMS_POINT = 0x2AD9;          // service, and its Fitness Machine Control Point
export const OP_CONTROL = 0x00, OP_SIM = 0x11, OP_REPLY = 0x80, OP_OK = 0x01;

// write one command to the control point and wait for the trainer's reply to it
export const ftmsAsk = (point, bytes) => new Promise((ok, no) => {
  const end = () => { clearTimeout(t); point.removeEventListener('characteristicvaluechanged', reply); };
  const reply = e => {
    const d = e.target.value;
    if (d.byteLength < 3 || d.getUint8(0) !== OP_REPLY || d.getUint8(1) !== bytes[0]) return;
    end(); d.getUint8(2) === OP_OK ? ok() : no(new Error('trainer refused'));
  };
  const t = setTimeout(() => { end(); no(new Error('no reply from trainer')); }, 3000);
  point.addEventListener('characteristicvaluechanged', reply);
  point.writeValueWithResponse(Uint8Array.from(bytes)).catch(err => { end(); no(err); });
});

// Indoor Bike Simulation Parameters: wind, gradient, rolling resistance and drag, matching the ride's own physics.
// (FTMS has no rider weight here; the trainer uses the weight set in its own app, the game uses MASS.)
export function simParams(gradePct) {
  const d = new DataView(new ArrayBuffer(7));
  d.setUint8(0, OP_SIM);
  d.setInt16(1, 0, true);                                   // wind speed, 0.001 m/s
  d.setInt16(3, Math.round(gradePct * 100), true);          // gradient, 0.01 %
  d.setUint8(5, Math.round(CRR / 0.0001));                  // rolling resistance, 0.0001
  d.setUint8(6, Math.round(DRAG / 0.01));                   // drag (half rho CdA), 0.01 kg/m
  return d;
}

// the gradient the trainer is asked for: the road's, capped at 20 %, scaled by the hills setting (descents by half that)
export const trainerGrade = (grade, hills) => Math.max(-20, Math.min(20, grade)) * (grade > 0 ? hills : hills * 0.5);
