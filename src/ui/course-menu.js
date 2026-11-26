// The course menu: every course in courses/index.json. Choosing one reloads the page on that course.
import { $ } from '../util/dom.js';
import { course, courses } from '../course/course.js';
import { panel } from './panels.js';

const btn = $('course'),
  box = $('courses');
btn.textContent = 'Course: ' + (course.shortName ?? course.name);

// Built with textContent, not HTML: course names come from contributed files.
const el = (tag, cls, text) => {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (text !== undefined) e.textContent = text;
  return e;
};
box.append(el('h3', '', 'Courses'));
for (const c of courses) {
  const b = el('button', c.id === course.id ? 'pick on' : 'pick');
  b.append(el('b', '', c.name));
  if (c.lengthKm !== undefined) b.append(el('span', 'muted', `${c.lengthKm} km · ${c.climbM} m climbing`));
  b.addEventListener('click', () => {
    if (c.id === course.id) return btn.click(); // already here: just close the menu
    location.search = c.id === 'valley' ? '' : '?course=' + encodeURIComponent(c.id);
  });
  box.append(b);
}
panel(btn, box);
