// Yggdrasil Sky: the living fjord for the Windows desktop.
// A port of the launcher's FjordScene.kt. The sky (time of day, stars, moon,
// northern lights, clouds, rain, snow, lightning, fog) is painted live; the
// mountains and the longship are fixed layers rendered by win_art.py.
"use strict";

const DEMO_SECONDS = 80;
const ART_W = 5120, ART_H = 1440, HZ = 0.62;   // layer size and waterline

// ------------------------------------------------------------------ state
const canvas = document.getElementById("sky");
const ctx = canvas.getContext("2d");
const state = {
  weather: null,          // {code, sunrise, sunset} (epoch ms) from the host
  demoStart: 0,
  paused: false,
  fps: 15,
  calmFps: 5,             // still weather: clouds drift, water shimmers, stars twinkle (0 = one frame a minute)
  scale: 1,               // render resolution (0.5-1); lower = cheaper on big screens
  forced: null,           // preview only: {time, code, aurora}
};
let land = null, ship = null;
let landTint = null, shipTint = null, tintKey = "";
let fg = null, refl = null;           // cached: tinted land+ship, and the mountains' reflection
let ray = null, puff = null;
let timer = 0, lastT = 0, flashAt = 0, nextFlash = 0;
let W = 0, H = 0;

// fixed random features (seeded so the sky is the same every start)
function mulberry(a) { return () => { a |= 0; a = a + 0x6D2B79F5 | 0; let t = Math.imul(a ^ a >>> 15, 1 | a); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }
const rnd = mulberry(11);
function gauss() { let s, v1, v2; do { v1 = 2 * rnd() - 1; v2 = 2 * rnd() - 1; s = v1 * v1 + v2 * v2; } while (s >= 1 || s === 0); return v1 * Math.sqrt(-2 * Math.log(s) / s); }
const stars = Array.from({ length: 700 }, () => [rnd(), rnd() * rnd() * 0.5, 0.8 + rnd() * 1.8, 0.3 + rnd() * 0.7, rnd() * 6.3]);
const glints = Array.from({ length: 140 }, () => [gauss(), Math.abs(gauss()), 0.4 + rnd(), rnd() * 6.3]);
const clouds = Array.from({ length: 28 }, () => [rnd(), 0.04 + rnd() * 0.42, 0.55 + rnd() * 0.5, 0.6 + rnd() * 0.8]);
const drops = Array.from({ length: 640 }, () => [rnd(), rnd(), 0.7 + rnd() * 0.6]);

// ------------------------------------------------------------------ colour helpers
const hex = (c) => [(c >> 16) & 255, (c >> 8) & 255, c & 255];
function mix(a, b, t) { t = Math.min(1, Math.max(0, t)); return [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t]; }
const rgba = (c, a = 1) => `rgba(${c[0] | 0},${c[1] | 0},${c[2] | 0},${Math.min(1, Math.max(0, a)).toFixed(3)})`;
const lerp = (a, b, t) => a + (b - a) * t;
const clamp = (x, a, b) => Math.min(b, Math.max(a, x));

// ------------------------------------------------------------------ sky timeline
const pal = (top, mid, hor, dark, glow) => ({ top: hex(top), mid: hex(mid), hor: hex(hor), dark, glow });
const P_NIGHT = pal(0x04060D, 0x0B1430, 0x1A2342, 1, 0);
const P_DAWN = pal(0x1A2342, 0x5B3A6A, 0xE8946A, 0.55, 1);
const P_DAY = pal(0x2F6FB3, 0x6AA6D8, 0xBFE0F0, 0, 0);
const P_GOLDEN = pal(0x2D5A9A, 0x8AA8C8, 0xF0C070, 0.05, 0.6);
const P_DUSK = pal(0x141A3A, 0x5B3A4A, 0xE0703A, 0.45, 1);

function onDay(ms, ref) { const d = new Date(ms), r = new Date(ref); d.setFullYear(r.getFullYear(), r.getMonth(), r.getDate()); return d.getTime(); }
function sunTimes(now, useWeather = true) {
  const w = state.weather;
  if (useWeather && w && w.sunrise && w.sunset) return [onDay(w.sunrise, now), onDay(w.sunset, now)];
  const d = new Date(now); d.setSeconds(0, 0);
  d.setHours(7, 15); const rise = d.getTime();
  d.setHours(17, 45); return [rise, d.getTime()];
}
function skyAt(now, useWeather) {
  const [rise, set] = sunTimes(now, useWeather), m = 60000;
  const f = [[rise - 70 * m, P_NIGHT], [rise - 15 * m, P_DAWN], [rise + 50 * m, P_DAY],
    [set - 90 * m, P_DAY], [set - 25 * m, P_GOLDEN], [set + 5 * m, P_DUSK], [set + 55 * m, P_NIGHT]];
  if (now <= f[0][0] || now >= f[f.length - 1][0]) return P_NIGHT;
  for (let i = 0; i < f.length - 1; i++) {
    const [t0, a] = f[i], [t1, b] = f[i + 1];
    if (now >= t0 && now <= t1) {
      const x = clamp((now - t0) / (t1 - t0), 0, 1), s = x * x * (3 - 2 * x);
      return { top: mix(a.top, b.top, s), mid: mix(a.mid, b.mid, s), hor: mix(a.hor, b.hor, s), dark: lerp(a.dark, b.dark, s), glow: lerp(a.glow, b.glow, s) };
    }
  }
  return P_NIGHT;
}

function skyKind(code) {
  if (code == null) return "clear";
  if (code === 0) return "clear";
  if (code === 1 || code === 2) return "partly";
  if (code === 3) return "cloudy";
  if (code === 45 || code === 48) return "fog";
  if ([51, 53, 55, 56, 57].includes(code)) return "drizzle";
  if ([61, 63, 65, 66, 67, 80, 81, 82].includes(code)) return "rain";
  if ([71, 73, 75, 77, 85, 86].includes(code)) return "snow";
  if ([95, 96, 99].includes(code)) return "thunder";
  return "cloudy";
}
const CLOUD = { clear: 0, partly: 0.3, cloudy: 0.75, fog: 0.6, drizzle: 0.7, rain: 0.8, snow: 0.75, thunder: 0.9 };
const PRECIP = { drizzle: 220, rain: 480, thunder: 600, snow: 420 };

// Demo: a whole clear day, a night of northern lights, rain, a storm at dusk, snow, a foggy dawn.
function demoState(realNow) {
  if (!state.demoStart) return null;
  const sec = (realNow - state.demoStart) / 1000;
  if (sec < 0 || sec > DEMO_SECONDS) { state.demoStart = 0; return null; }
  const [rise, set] = sunTimes(realNow, false), m = 60000;
  if (sec < 30) return { time: rise - 80 * m + (set + 70 * m - (rise - 80 * m)) * (sec / 30), code: 0, aurora: 0 };
  if (sec < 44) return { time: set + 180 * m, code: 0, aurora: 1 };
  if (sec < 54) return { time: rise + 240 * m, code: 63, aurora: 0 };
  if (sec < 64) return { time: set + 20 * m, code: 95, aurora: 0 };
  if (sec < 74) return { time: rise + 200 * m, code: 73, aurora: 0 };
  return { time: rise + 10 * m, code: 45, aurora: 0 };
}

// ------------------------------------------------------------------ sprites
function makeRay() {
  const c = document.createElement("canvas"); c.width = 4; c.height = 256;
  const g = c.getContext("2d"), img = g.createImageData(4, 256);
  const vio = hex(0x9A7FE0), fro = hex(0x8FC4E0), grn = hex(0x3FE0A0);
  for (let y = 0; y < 256; y++) {
    const u = y / 255;
    const col = u < 0.6 ? mix(vio, fro, u / 0.6) : mix(fro, grn, (u - 0.6) / 0.4);
    const a = u < 0.85 ? u / 0.85 : 1 - (u - 0.85) / 0.15 * 0.7;
    for (let x = 0; x < 4; x++) { const i = (y * 4 + x) * 4; img.data[i] = col[0]; img.data[i + 1] = col[1]; img.data[i + 2] = col[2]; img.data[i + 3] = a * a * 255; }
  }
  g.putImageData(img, 0, 0); return c;
}
function makePuff() {
  const c = document.createElement("canvas"); c.width = 256; c.height = 128;
  const g = c.getContext("2d"), r = mulberry(5);
  for (let i = 0; i < 9; i++) {
    const x = 40 + r() * 176, y = 54 + r() * 30, rad = 30 + r() * 34;
    const gr = g.createRadialGradient(x, y, 0, x, y, rad);
    gr.addColorStop(0, "rgba(255,255,255,0.4)"); gr.addColorStop(1, "rgba(255,255,255,0)");
    g.fillStyle = gr; g.beginPath(); g.arc(x, y, rad, 0, Math.PI * 2); g.fill();
  }
  return c;
}
const srcPixels = new Map();
function tinted(src, prev, r, g, b) {
  // Scales the layer's colour channels (like the launcher's ColorMatrix), cached
  // and redone only when the light changes, which is over minutes, not frames.
  let base = srcPixels.get(src);
  if (!base) {
    const c0 = document.createElement("canvas"); c0.width = src.width; c0.height = src.height;
    const x0 = c0.getContext("2d", { willReadFrequently: true }); x0.drawImage(src, 0, 0);
    const all = x0.getImageData(0, 0, src.width, src.height).data;
    let y0 = src.height, y1 = 0;                       // only the rows that hold any pixels
    for (let y = 0; y < src.height; y++) {
      for (let i = (y * src.width) * 4 + 3, e = i + src.width * 4; i < e; i += 4) if (all[i]) { y0 = Math.min(y0, y); y1 = y; break; }
    }
    if (y1 < y0) { y0 = 0; y1 = 0; }
    base = { y0, img: x0.getImageData(0, y0, src.width, y1 - y0 + 1) };
    srcPixels.set(src, base);
  }
  const c = prev || document.createElement("canvas");
  if (c.width !== src.width || c.height !== src.height) { c.width = src.width; c.height = src.height; }
  const a = base.img.data, out = new ImageData(base.img.width, base.img.height), o = out.data;
  for (let i = 0; i < a.length; i += 4) {
    if (a[i + 3] === 0) continue;
    o[i] = a[i] * r; o[i + 1] = a[i + 1] * g; o[i + 2] = a[i + 2] * b; o[i + 3] = a[i + 3];
  }
  c.getContext("2d").putImageData(out, 0, base.y0);
  return c;
}

// ------------------------------------------------------------------ drawing
function draw(uptime) {
  const realNow = Date.now();
  const demo = state.forced || demoState(realNow);
  const now = demo ? demo.time : realNow;
  const dt = lastT ? clamp(uptime - lastT, 0, 100) / 1000 : 0;
  lastT = uptime;
  const t = uptime;
  const w = W, h = H;

  const kind = skyKind(demo ? demo.code : state.weather && state.weather.code);
  const cloud = CLOUD[kind];
  const p = skyAt(now, !demo);
  const light = 1 - p.dark;
  const grey = mix(hex(0x2A2E36), hex(0x8A919C), light);
  const top = mix(p.top, grey, cloud * 0.8), mid = mix(p.mid, grey, cloud * 0.85), hor = mix(p.hor, grey, cloud * 0.75);

  // layout: the layers are ART_W x ART_H, cover-cropped to the screen
  const s = Math.max(w / ART_W, h / ART_H);
  const ox = (w - ART_W * s) / 2, oy = (h - ART_H * s) / 2;
  const hz = oy + ART_H * s * HZ;
  const u = h / 1440;                       // size unit (1 on the G9)

  ctx.globalAlpha = 1; ctx.globalCompositeOperation = "source-over";

  // sky
  let gr = ctx.createLinearGradient(0, 0, 0, hz);
  gr.addColorStop(0, rgba(top)); gr.addColorStop(0.5, rgba(mid)); gr.addColorStop(1, rgba(hor));
  ctx.fillStyle = gr; ctx.fillRect(0, 0, w, hz + 2);

  // stars
  const starA = p.dark * Math.max(0, 1 - cloud * 1.2);
  if (starA > 0.02) {
    ctx.fillStyle = "#fff";
    for (const st of stars) {
      const tw = 0.7 + 0.3 * Math.sin(t * 0.0021 * (0.5 + st[3]) + st[4]);
      ctx.globalAlpha = clamp(starA * st[3] * tw, 0, 1);
      ctx.beginPath(); ctx.arc(st[0] * w, st[1] * hz * 1.4, st[2] * u * 1.1, 0, 6.283); ctx.fill();
    }
    ctx.globalAlpha = 1;
  }

  // moon / sun
  const moonA = Math.max(0, p.dark - 0.5) * 2 * (1 - cloud);
  const mx = w * 0.78, my = h * 0.16, mr = 40 * u;
  if (moonA > 0.02) {
    gr = ctx.createRadialGradient(mx, my, 0, mx, my, mr * 5);
    gr.addColorStop(0, rgba(hex(0xE8F0FF), 0.35 * moonA)); gr.addColorStop(1, "rgba(232,240,255,0)");
    ctx.fillStyle = gr; ctx.beginPath(); ctx.arc(mx, my, mr * 5, 0, 6.283); ctx.fill();
    ctx.fillStyle = rgba(hex(0xEDEFF5), 0.9 * moonA); ctx.beginPath(); ctx.arc(mx, my, mr, 0, 6.283); ctx.fill();
    ctx.fillStyle = rgba(top, 0.85 * moonA); ctx.beginPath(); ctx.arc(mx + mr * 0.45, my - mr * 0.15, mr * 0.92, 0, 6.283); ctx.fill();
  }
  const sunA = light * (1 - p.glow) * (1 - cloud) * 0.6;
  if (sunA > 0.02) {
    const sx = w * 0.72, sy = h * 0.18, sr = h * 0.9;
    gr = ctx.createRadialGradient(sx, sy, 0, sx, sy, sr);
    gr.addColorStop(0, rgba(hex(0xFFF4D6), sunA)); gr.addColorStop(0.25, rgba(hex(0xFFE9A8), sunA * 0.25)); gr.addColorStop(1, "rgba(255,233,168,0)");
    ctx.fillStyle = gr; ctx.fillRect(sx - sr, 0, sr * 2, hz);
  }

  // northern lights: strength varies night to night
  const night = Math.floor((now - 12 * 3600000) / 86400000);
  const fr = (x) => x - Math.floor(x);
  const auroraNight = demo ? demo.aurora : 0.35 + 0.65 * fr(Math.sin(night * 12.9898) * 43758.5453);
  const auroraA = auroraNight * clamp((p.dark - 0.65) / 0.35, 0, 1) * clamp(1 - cloud * 2.2, 0, 1);
  if (auroraA > 0.03) drawAurora(w, h, hz, t, auroraA);

  // clouds
  if (cloud > 0.15) {
    const tint = mix(hex(0x30343C), hex(0xDDE2EA), light * 0.85 + p.glow * 0.1);
    const n = Math.min(clouds.length, Math.round((4 + cloud * 10) * Math.max(1, w / h / 1.6)));
    ctx.globalAlpha = 0.18 + 0.35 * cloud;
    for (let i = 0; i < n; i++) {
      const cl = clouds[i], span = w * 1.4;
      const x = ((cl[0] * span + t * 0.012 * cl[3] * u) % span) - w * 0.2;
      const cw = hz * 2.4 * cl[2], ch = cw * 0.38;
      ctx.drawImage(tintPuff(tint), x - cw / 2, cl[1] * hz - ch / 2, cw, ch);
    }
    ctx.globalAlpha = 1;
    ctx.fillStyle = rgba(tint, cloud * 0.3); ctx.fillRect(0, 0, w, hz);
  }

  // the glow in the fjord's mouth at dawn and dusk
  const valleyX = ox + ART_W * s * 0.62;
  const glowA = p.glow * (1 - cloud * 0.7);
  if (glowA > 0.02) {
    const r = h * 1.1;
    gr = ctx.createRadialGradient(valleyX, hz, 0, valleyX, hz, r);
    gr.addColorStop(0, rgba(hex(0xECD08F), 0.85 * glowA)); gr.addColorStop(0.3, rgba(hex(0xE0703A), 0.4 * glowA)); gr.addColorStop(1, "rgba(224,112,58,0)");
    ctx.fillStyle = gr; ctx.fillRect(valleyX - r, hz - r, r * 2, r);
  }

  // lightning
  if (kind === "thunder") {
    if (!nextFlash || uptime > nextFlash) { flashAt = uptime; nextFlash = uptime + 9000 + Math.random() * 25000; }
    const age = uptime - flashAt;
    if (age < 600) {
      const f = (1 - age / 600) * (age >= 120 && age <= 200 ? 0.3 : 1);
      ctx.fillStyle = rgba(hex(0xE8F0FF), 0.55 * f); ctx.fillRect(0, 0, w, hz);
    }
  }

  // fog band over the water line
  if (kind === "fog") {
    gr = ctx.createLinearGradient(0, hz - h * 0.3, 0, hz + h * 0.1);
    gr.addColorStop(0, rgba(grey, 0)); gr.addColorStop(0.7, rgba(grey, 0.55)); gr.addColorStop(1, rgba(grey, 0));
    ctx.fillStyle = gr; ctx.fillRect(0, hz - h * 0.3, w, h * 0.4);
  }

  // water
  const deep = hex(0x060912);
  gr = ctx.createLinearGradient(0, hz, 0, h);
  gr.addColorStop(0, rgba(mix(hor, deep, 0.45))); gr.addColorStop(0.3, rgba(mix(mid, deep, 0.7))); gr.addColorStop(1, rgba(deep));
  ctx.fillStyle = gr; ctx.fillRect(0, hz, w, h - hz);

  // the land and ship follow the light (warm at dawn and dusk, dim at night)
  const l = lerp(1.3, 0.5, p.dark), sl = lerp(1.15, 0.65, p.dark);
  const key = [l, p.glow, sl].map((v) => Math.round(v * 25)).join();   // 0.04 steps
  if (key !== tintKey && land && ship) {
    landTint = tinted(land, landTint, l * (1 + 0.15 * p.glow), l, l * (1 - 0.1 * p.glow));
    shipTint = tinted(ship, shipTint, sl, sl, sl);
    fg = fg || document.createElement("canvas"); fg.width = ART_W; fg.height = ART_H;
    const f = fg.getContext("2d"); f.drawImage(landTint, 0, 0); f.drawImage(shipTint, 0, 0);
    refl = refl || document.createElement("canvas"); refl.width = ART_W; refl.height = ART_H;
    const r = refl.getContext("2d"); r.clearRect(0, 0, ART_W, ART_H);
    r.save(); r.translate(0, 2 * ART_H * HZ); r.scale(1, -1); r.globalAlpha = 80 / 255; r.drawImage(landTint, 0, 0); r.restore();
    tintKey = key;
  }

  if (refl) ctx.drawImage(refl, ox, oy, ART_W * s, ART_H * s);   // reflection of the mountains

  // glints on the water under the sun, glow or moon
  const glintA = Math.max(p.glow, light * 0.35, moonA * 0.6) * (1 - cloud * 0.85);
  if (glintA > 0.03) {
    const byMoon = moonA > p.glow && moonA > light;
    const gx = byMoon ? mx : valleyX, gc = hex(byMoon ? 0xDDE6F5 : 0xECD08F);
    for (const g of glints) {
      const tw = 0.5 + 0.5 * Math.sin(t * 0.004 * g[2] + g[3]);
      ctx.fillStyle = rgba(gc, glintA * tw * 0.6);
      ctx.fillRect(gx + g[0] * h * 0.3, hz + g[1] * h * 0.07 + 4 * u, (24 + 80 * g[2]) * u, 3 * u);
    }
  }

  if (fg) ctx.drawImage(fg, ox, oy, ART_W * s, ART_H * s);         // mountains + longship

  // rain / snow
  const precip = PRECIP[kind] || 0;
  if (precip) drawPrecip(w, h, dt, t, precip, kind === "snow", light, u);

  return !!demo || auroraA > 0.03 || precip > 0 || kind === "thunder";
}

let puffTint = null, puffKey = "";
function tintPuff(c) {
  const k = c.map((v) => v | 0).join();
  if (k === puffKey) return puffTint;
  const o = document.createElement("canvas"); o.width = puff.width; o.height = puff.height;
  const x = o.getContext("2d");
  x.drawImage(puff, 0, 0); x.globalCompositeOperation = "source-in";
  x.fillStyle = rgba(c); x.fillRect(0, 0, o.width, o.height);
  puffTint = o; puffKey = k; return o;
}

function drawAurora(w, h, hz, t, a) {
  const n = Math.round(90 * Math.max(1, w / h / 1.6));
  const colW = w / n * 1.7;
  for (let b = 0; b < 3; b++) {
    const base = hz * (0.30 + b * 0.08), amp = hz * 0.05, tall = hz * (0.20 + 0.06 * b);
    for (let i = 0; i < n; i++) {
      const v = i / (n - 1);
      const x = v * w * 1.1 - w * 0.05;
      const y = base + amp * Math.sin(v * 2 * Math.PI * 2.6 + t * 0.00022 * (1 + b * 0.3) + b) +
        amp * 0.5 * Math.sin(v * 2 * Math.PI * 6.2 - t * 0.00037);
      const shimmer = 0.5 + 0.5 * Math.sin(i * 0.7 + t * 0.0011 * (b + 1)) * Math.sin(i * 0.23 - t * 0.0007);
      ctx.globalAlpha = clamp(a * (0.12 + 0.32 * shimmer) * (1 - b * 0.22), 0, 1);
      ctx.drawImage(ray, x - colW / 2, y - tall, colW, tall + hz * 0.02);
    }
  }
  ctx.globalAlpha = 1;
}

function drawPrecip(w, h, dt, t, count, snow, light, u) {
  const n = Math.min(count, drops.length);
  if (snow) {
    ctx.fillStyle = rgba([255, 255, 255], 0.75 + 0.2 * light);
    for (let i = 0; i < n; i++) {
      const d = drops[i];
      d[1] += dt * 0.12 * d[2];
      d[0] += dt * 0.004 * Math.sin(t * 0.001 + i);
      if (d[1] > 1) { d[1] -= 1; d[0] = Math.random(); }
      ctx.beginPath(); ctx.arc((((d[0] % 1) + 1) % 1) * w, d[1] * h, (1.5 + 2.5 * d[2]) * u, 0, 6.283); ctx.fill();
    }
  } else {
    ctx.strokeStyle = rgba(hex(0x8FC4E0), 0.28 + 0.15 * light);
    ctx.lineWidth = 2.2 * u; ctx.beginPath();
    const len = h * 0.045;
    for (let i = 0; i < n; i++) {
      const d = drops[i];
      d[1] += dt * 1.6 * d[2];
      d[0] -= dt * 0.05 * d[2];
      if (d[1] > 1) { d[1] -= 1; d[0] = Math.random() * 1.2; }
      const x = (((d[0] % 1) + 1) % 1) * w, y = d[1] * h;
      ctx.moveTo(x, y); ctx.lineTo(x + len * 0.18 * d[2], y - len * d[2]);
    }
    ctx.stroke();
  }
}

// ------------------------------------------------------------------ loop
function resize() {
  const dpr = (window.devicePixelRatio || 1) * state.scale;
  W = Math.round(window.innerWidth * dpr); H = Math.round(window.innerHeight * dpr);
  canvas.width = W; canvas.height = H;
  canvas.style.width = window.innerWidth + "px"; canvas.style.height = window.innerHeight + "px";
}
function tick() {
  clearTimeout(timer); timer = 0;
  if (state.paused) return;
  requestAnimationFrame((ts) => {
    if (state.paused) return;
    const moving = draw(ts);
    const calm = state.calmFps > 0 ? 1000 / state.calmFps : 60000;
    timer = setTimeout(tick, moving ? 1000 / state.fps : calm);
  });
}
function load(src) { return new Promise((ok, bad) => { const i = new Image(); i.onload = () => ok(i); i.onerror = bad; i.src = src; }); }

function onMessage(m) {
  if (!m || typeof m !== "object") return;
  switch (m.type) {
    case "weather": state.weather = { code: m.code | 0, sunrise: +m.sunrise, sunset: +m.sunset }; break;
    case "pause": state.paused = true; clearTimeout(timer); return;
    case "resume": state.paused = false; lastT = 0; break;
    case "demo": state.demoStart = Date.now(); break;
    case "fps": state.fps = clamp(m.fps | 0, 5, 30); break;
    case "calm": state.calmFps = clamp(m.fps | 0, 0, 15); break;
    case "scale": state.scale = clamp(+m.scale || 1, 0.5, 1); resize(); break;
    default: return;
  }
  tick();
}

async function start() {
  resize();
  window.addEventListener("resize", () => { resize(); tick(); });
  ray = makeRay(); puff = makePuff();
  [land, ship] = await Promise.all([load("sky-land.png"), load("sky-ship.png")]);

  // Preview / testing in a normal browser: ?at=HH:MM&code=63&aurora=1&demo=1
  const q = new URLSearchParams(location.search);
  if (q.has("at")) {
    const [hh, mm] = q.get("at").split(":").map(Number), d = new Date(); d.setHours(hh, mm || 0, 0, 0);
    state.forced = { time: d.getTime(), code: +(q.get("code") || 0), aurora: +(q.get("aurora") || 0.8) };
  }
  if (q.has("demo")) state.demoStart = Date.now();

  if (window.chrome && window.chrome.webview) {
    window.chrome.webview.addEventListener("message", (e) => onMessage(e.data));
    window.chrome.webview.postMessage({ type: "ready" });
  }
  tick();
}
start();
