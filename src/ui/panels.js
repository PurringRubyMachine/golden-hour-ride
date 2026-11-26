// Panels that drop down under the controls (the ride log, the course menu). One is open at a time.
const panels = [];

// btn opens and closes box; draw (optional) fills it each time it opens.
export function panel(btn, box, draw) {
  panels.push({ btn, box });
  btn.addEventListener('click', () => {
    const show = box.hidden;
    for (const p of panels) {
      p.box.hidden = true;
      p.btn.classList.remove('on');
    }
    if (show) {
      draw?.();
      // just below the controls, which wrap onto a second row in narrower windows
      const bar = btn.closest('#ctl');
      if (bar) box.style.top = Math.round(bar.getBoundingClientRect().bottom + 8) + 'px';
      box.hidden = false;
      btn.classList.add('on');
    }
  });
}
