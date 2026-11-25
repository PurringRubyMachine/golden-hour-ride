// Seeded random numbers, so the scenery is the same on every visit.
// Each part of the scene draws from its own named stream, so changing one part never moves another part's trees.

// FNV-1a hash of the name, then a final mix, so similar names give unrelated streams.
function seedFor(name) {
  let h = 0x811c9dc5;
  for (let i = 0; i < name.length; i++) h = Math.imul(h ^ name.charCodeAt(i), 0x01000193);
  h = Math.imul(h ^ (h >>> 16), 0x85ebca6b);
  h = Math.imul(h ^ (h >>> 13), 0xc2b2ae35);
  return (h ^ (h >>> 16)) >>> 0;
}

// A stream of numbers from 0 up to (not including) 1: the same sequence every time for the same name.
export function makeRandom(name) {
  let seed = seedFor(name);
  return () => {
    seed = (seed * 1664525 + 1013904223) >>> 0;
    return seed / 4294967296;
  };
}
