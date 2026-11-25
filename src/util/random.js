// Seeded random numbers, so the scenery is the same on every visit.

let seed = 7;
export const rnd = () => {
  seed = (seed * 1664525 + 1013904223) >>> 0;
  return seed / 4294967296;
};
