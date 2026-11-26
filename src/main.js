// Start-up. Load the textures and the course first, then build the scene and start the ride.
// (A module that waits on a file lets its siblings run meanwhile, so the scene is imported only once loading
// has finished: every scene module can then rely on the textures and the course being ready.)
import './render/textures.js';
import './course/course.js';

await import('./scene.js');
