/* CuffnCode Docs — JavaScript */

// ── Navbar scroll effect ────────────────────────────────────────────────────
window.addEventListener('scroll', () => {
  const nav = document.getElementById('navbar');
  if (window.scrollY > 50) {
    nav.style.borderBottomColor = 'rgba(48, 54, 61, 0.6)';
  } else {
    nav.style.borderBottomColor = 'var(--border)';
  }
});

// ── Mobile nav toggle ───────────────────────────────────────────────────────
function toggleMenu() {
  const links = document.querySelector('.nav-links');
  links.classList.toggle('open');
}

// ── Code tabs ───────────────────────────────────────────────────────────────
function showTab(id) {
  document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
  document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active'));
  document.getElementById('tab-' + id).classList.add('active');
  document.querySelectorAll('.tab-btn').forEach(btn => {
    if (btn.getAttribute('onclick') === `showTab('${id}')`) {
      btn.classList.add('active');
    }
  });
}

// ── Animated BP numbers in hero ─────────────────────────────────────────────
function animateCounter(el, target, duration = 2000) {
  const start = 0;
  const step = target / (duration / 16);
  let current = start;
  const interval = setInterval(() => {
    current = Math.min(current + step, target);
    el.textContent = Math.round(current);
    if (current >= target) clearInterval(interval);
  }, 16);
}

window.addEventListener('load', () => {
  setTimeout(() => {
    animateCounter(document.getElementById('hero-sbp'), 120, 1800);
    animateCounter(document.getElementById('hero-dbp'), 80, 1800);
    animateCounter(document.getElementById('hero-map'), 93, 1800);
    animateCounter(document.getElementById('hero-hr'), 72, 1800);
  }, 400);

  // Draw algorithm chart on canvas
  drawAlgoChart();
});

// ── Intersection Observer for fade-in ────────────────────────────────────────
const observer = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      entry.target.style.opacity = '1';
      entry.target.style.transform = 'translateY(0)';
      observer.unobserve(entry.target);
    }
  });
}, { threshold: 0.1, rootMargin: '0px 0px -40px 0px' });

document.querySelectorAll(
  '.feature-card, .module-card, .team-card, .result-card, .pipeline-step'
).forEach(el => {
  el.style.opacity = '0';
  el.style.transform = 'translateY(24px)';
  el.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
  observer.observe(el);
});

// ── Algorithm chart (canvas) ─────────────────────────────────────────────────
function drawAlgoChart() {
  const canvas = document.getElementById('algoChart');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  const W = canvas.width, H = canvas.height;

  // Gaussian amplitude curve
  const MAP_X = W * 0.55;  // MAP position (~55% through deflation)
  const sigma = W * 0.15;
  const peakAmp = H * 0.7;

  ctx.clearRect(0, 0, W, H);

  // Background
  ctx.fillStyle = '#0D1117';
  ctx.fillRect(0, 0, W, H);

  // Grid lines
  ctx.strokeStyle = '#21262D';
  ctx.lineWidth = 1;
  for (let x = 0; x < W; x += 60) {
    ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, H); ctx.stroke();
  }
  for (let y = 0; y < H; y += 40) {
    ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(W, y); ctx.stroke();
  }

  // Gaussian envelope
  const getY = (x) => {
    const amp = peakAmp * Math.exp(-0.5 * ((x - MAP_X) / sigma) ** 2);
    return H - 30 - amp;
  };

  ctx.beginPath();
  ctx.strokeStyle = '#2ECC71';
  ctx.lineWidth = 3;
  for (let x = 0; x <= W; x++) {
    const y = getY(x);
    x === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
  }
  ctx.stroke();

  // Fill under curve
  ctx.beginPath();
  ctx.moveTo(0, H - 30);
  for (let x = 0; x <= W; x++) ctx.lineTo(x, getY(x));
  ctx.lineTo(W, H - 30);
  ctx.closePath();
  ctx.fillStyle = 'rgba(46, 204, 113, 0.08)';
  ctx.fill();

  // Peak (MAP)
  const mapY = getY(MAP_X);
  ctx.beginPath();
  ctx.strokeStyle = '#F39C12';
  ctx.lineWidth = 2;
  ctx.setLineDash([6, 4]);
  ctx.moveTo(MAP_X, mapY); ctx.lineTo(MAP_X, H - 30);
  ctx.stroke();
  ctx.setLineDash([]);

  // SBP threshold (45% of peak)
  const sbpThresh = 0.45 * peakAmp;
  const sbpAmpY = H - 30 - sbpThresh;
  // Find SBP x (left side of Gaussian where amp = sbpThresh)
  const sbpX = MAP_X - sigma * Math.sqrt(-2 * Math.log(0.45));

  ctx.beginPath();
  ctx.strokeStyle = '#E74C3C';
  ctx.lineWidth = 1.5;
  ctx.setLineDash([4, 4]);
  ctx.moveTo(0, sbpAmpY); ctx.lineTo(W, sbpAmpY);
  ctx.stroke();
  ctx.setLineDash([]);
  ctx.beginPath();
  ctx.strokeStyle = '#E74C3C';
  ctx.lineWidth = 2;
  ctx.moveTo(sbpX, sbpAmpY); ctx.lineTo(sbpX, H - 30);
  ctx.stroke();

  // DBP threshold (70% of peak)
  const dbpThresh = 0.70 * peakAmp;
  const dbpAmpY = H - 30 - dbpThresh;
  const dbpX = MAP_X + sigma * Math.sqrt(-2 * Math.log(0.70));

  ctx.beginPath();
  ctx.strokeStyle = '#2188FF';
  ctx.lineWidth = 1.5;
  ctx.setLineDash([4, 4]);
  ctx.moveTo(0, dbpAmpY); ctx.lineTo(W, dbpAmpY);
  ctx.stroke();
  ctx.setLineDash([]);
  ctx.beginPath();
  ctx.strokeStyle = '#2188FF';
  ctx.lineWidth = 2;
  ctx.moveTo(dbpX, dbpAmpY); ctx.lineTo(dbpX, H - 30);
  ctx.stroke();

  // Labels
  ctx.font = 'bold 12px JetBrains Mono, monospace';
  ctx.fillStyle = '#F39C12';
  ctx.fillText('MAP', MAP_X + 4, mapY - 8);

  ctx.fillStyle = '#E74C3C';
  ctx.fillText('SBP', sbpX + 4, H - 34);
  ctx.fillText('45%', 8, sbpAmpY - 6);

  ctx.fillStyle = '#2188FF';
  ctx.fillText('DBP', dbpX + 4, H - 34);
  ctx.fillText('70%', 8, dbpAmpY - 6);

  ctx.fillStyle = '#2ECC71';
  ctx.fillText('Oscillation Amplitude', 16, 20);

  // X-axis label
  ctx.fillStyle = '#8B949E';
  ctx.font = '11px Inter, sans-serif';
  ctx.fillText('Cuff Pressure (decreasing during deflation →)', W / 2 - 140, H - 6);
}
