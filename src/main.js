// Start-up. Load the textures and the course first. Then build everything else, in this order: the scenery
// is placed with one seeded random stream, so the order the modules run in decides where everything goes.
// (Modules that wait on a file let their siblings run meanwhile, which is why the scene is imported only
// once loading has finished.)
import './render/textures.js';
import './course/course.js';

await import('./scene.js');
