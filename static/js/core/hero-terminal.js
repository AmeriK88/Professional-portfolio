(function () {
  const TIMING = {
    card: 2500,
    transition: 600,
    stepStart: 400,
    typeDelay: 50,
    afterCommand: 500,
    lineDelay: 320,
    afterStep: 1000,
    doneLineDelay: 300,
    done: 1500,
    restartPause: 800
  };

  class Cancelled extends Error {}

  function initializeHeroTerminal() {
    const panel = document.querySelector('.home-visual-panel');
    if (!panel || panel.dataset.terminalInitialized === 'true') return;

    const steps = Array.from(panel.querySelectorAll('[data-term-step]'));
    const done = panel.querySelector('[data-term-done]');
    if (!steps.length || !done) return;

    panel.dataset.terminalInitialized = 'true';

    const motionQuery = window.matchMedia
      ? window.matchMedia('(prefers-reduced-motion: reduce)')
      : null;
    const hasObserver = 'IntersectionObserver' in window;
    let inViewport = !hasObserver;
    let running = false;
    let timerId = null;
    let cancelWait = null;

    function wait(ms) {
      return new Promise((resolve, reject) => {
        cancelWait = () => reject(new Cancelled());
        timerId = window.setTimeout(() => {
          timerId = null;
          cancelWait = null;
          resolve();
        }, ms);
      });
    }

    function cancel() {
      if (timerId !== null) window.clearTimeout(timerId);
      timerId = null;
      if (cancelWait) {
        const reject = cancelWait;
        cancelWait = null;
        reject();
      }
    }

    function lines(block) {
      return Array.from(block.querySelectorAll('.home-term-line'));
    }

    function resetTerminal() {
      panel.removeAttribute('data-scene');
      [...steps, done].forEach((block) => {
        block.classList.remove('is-active');
        lines(block).forEach((line) => line.classList.remove('is-visible'));
      });
      steps.forEach((step) => {
        const typed = step.querySelector('[data-term-typed]');
        if (typed) typed.textContent = '';
      });
    }

    function activate(block) {
      [...steps, done].forEach((item) => item.classList.toggle('is-active', item === block));
    }

    async function typeCommand(step) {
      const typed = step.querySelector('[data-term-typed]');
      const command = step.dataset.command || '';
      typed.textContent = '';
      for (const char of command) {
        await wait(TIMING.typeDelay);
        typed.textContent += char;
      }
    }

    async function revealLines(block, delay) {
      for (const line of lines(block)) {
        await wait(delay);
        line.classList.add('is-visible');
      }
    }

    async function runCycle() {
      for (;;) {
        resetTerminal();
        await wait(TIMING.card);

        panel.dataset.scene = 'terminal';
        await wait(TIMING.transition);

        for (const step of steps) {
          activate(step);
          step.querySelector('[data-term-typed]').textContent = '';
          await wait(TIMING.stepStart);
          await typeCommand(step);
          await wait(TIMING.afterCommand);
          await revealLines(step, TIMING.lineDelay);
          await wait(TIMING.afterStep);
        }

        activate(done);
        await revealLines(done, TIMING.doneLineDelay);
        await wait(TIMING.done);

        panel.removeAttribute('data-scene');
        await wait(TIMING.transition + TIMING.restartPause);
      }
    }

    function start() {
      if (running) return;
      running = true;
      runCycle().catch((error) => {
        if (!(error instanceof Cancelled)) throw error;
      });
    }

    function stop() {
      running = false;
      cancel();
      resetTerminal();
    }

    function sync() {
      const reduced = motionQuery && motionQuery.matches;
      if (!reduced && !document.hidden && inViewport) {
        start();
      } else {
        stop();
      }
    }

    if (hasObserver) {
      const observer = new IntersectionObserver((entries) => {
        const entry = entries[entries.length - 1];
        inViewport = entry.isIntersecting;
        sync();
      });
      observer.observe(panel);
    }

    document.addEventListener('visibilitychange', sync);
    window.addEventListener('pagehide', stop);
    window.addEventListener('pageshow', sync);

    if (motionQuery) {
      if (motionQuery.addEventListener) {
        motionQuery.addEventListener('change', sync);
      } else if (motionQuery.addListener) {
        motionQuery.addListener(sync);
      }
    }

    sync();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeHeroTerminal, { once: true });
  } else {
    initializeHeroTerminal();
  }
})();
