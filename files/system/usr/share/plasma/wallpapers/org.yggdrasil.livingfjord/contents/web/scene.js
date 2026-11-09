// Yggdrasil Sky: the living fjord for the Windows desktop and Yggdrasil OS.
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
  house: null,            // the steading feed: {lights, garage, door, hearth, home_since, solar, export, leak, fire, forge, raven, chest}
  kp: null,               // tonight's planetary Kp (NOAA); null = northern lights some clear nights
  feastUntil: 0,          // "Preview the birthday": the name-day feast until this time
};
let shipOut = -1, flareAt = 0, lastHomeSince = 0;
let snowAt = 0;
try { snowAt = +(localStorage.getItem("snowAt") || 0); } catch (e) { }
let land = null, ship = null;
let landTint = null, shipTint = null, tintKey = "";
let fg = null, refl = null;           // cached: tinted land+ship, and the mountains' reflection
let shipRefl = null;                  // cached: the longship mirrored about its own waterline
let sailCloth = null, sailOff = null, sailFill = 0.3, sailAt = 0;   // the sail's cloth and how full the wind has it
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

  // layout: the layers are ART_W x ART_H, cover-cropped to the screen. On screens narrower than
  // the G9 the crop slides just far enough to keep the steading (lantern post included) and the
  // longship in view; when everything already fits it stays centred.
  const s = Math.max(w / ART_W, h / ART_H);
  const vw = w / s, cx = vw >= FOCUS_R - FOCUS_L
    ? clamp(ART_W / 2, FOCUS_R - vw / 2, FOCUS_L + vw / 2) : (FOCUS_L + FOCUS_R) / 2;
  const ox = w / 2 - clamp(cx, Math.min(vw, ART_W) / 2, ART_W - Math.min(vw, ART_W) / 2) * s, oy = (h - ART_H * s) / 2;
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
  // tonight's real phase: a glow that grows with it, the dark face faintly, the lit part bright
  const mAge = moonAge(now), mLit = moonLit(mAge);
  const moonA = Math.max(0, p.dark - 0.5) * 2 * (1 - cloud) * (0.25 + 0.75 * mLit);
  const mx = w * 0.78, my = h * 0.16, mr = 40 * u;
  if (moonA > 0.02) {
    gr = ctx.createRadialGradient(mx, my, 0, mx, my, mr * 5);
    gr.addColorStop(0, rgba(hex(0xE8F0FF), 0.35 * moonA * mLit)); gr.addColorStop(1, "rgba(232,240,255,0)");
    ctx.fillStyle = gr; ctx.beginPath(); ctx.arc(mx, my, mr * 5, 0, 6.283); ctx.fill();
    ctx.fillStyle = rgba(mix(top, hex(0x2A3348), 0.5), 0.85 * moonA); ctx.beginPath(); ctx.arc(mx, my, mr, 0, 6.283); ctx.fill();
    ctx.fillStyle = rgba(hex(0xEDEFF5), 0.92 * moonA); moonPath(mx, my, mr, mAge); ctx.fill();
  }
  // midwinter: on the solstice the sun keeps low in the fjord's mouth all day
  const solstice = isSolstice(new Date(now)) && light > 0.3;
  const sunA = solstice ? light * (1 - cloud) * 0.7 : light * (1 - p.glow) * (1 - cloud) * 0.6;
  if (sunA > 0.02) {
    const sx = solstice ? ox + ART_W * s * 0.62 : w * 0.72, sy = solstice ? hz - h * 0.05 : h * 0.18, sr = h * 0.9;
    gr = ctx.createRadialGradient(sx, sy, 0, sx, sy, sr);
    gr.addColorStop(0, rgba(hex(0xFFF4D6), sunA)); gr.addColorStop(0.25, rgba(hex(0xFFE9A8), sunA * 0.25)); gr.addColorStop(1, "rgba(255,233,168,0)");
    ctx.fillStyle = gr; ctx.fillRect(sx - sr, 0, sr * 2, hz);
  }

  // northern lights: strength varies night to night
  const night = Math.floor((now - 12 * 3600000) / 86400000);
  const fr = (x) => x - Math.floor(x);
  // with NOAA's Kp: none below 4, faint at 4, a fair chance at 6, full from 8; without it, some most clear nights
  const kp = state.kp;
  const auroraNight = demo ? demo.aurora : kp == null ? 0.35 + 0.65 * fr(Math.sin(night * 12.9898) * 43758.5453)
    : kp < 4 ? 0 : Math.min(1, 0.15 + (kp - 4) * 0.25);
  const auroraA = auroraNight * clamp((p.dark - 0.65) / 0.35, 0, 1) * clamp(1 - cloud * 2.2, 0, 1);
  if (auroraA > 0.03) drawAurora(w, h, hz, t, auroraA);

  // Yggdrasil itself: on clear nights the World Tree's bare crown rises behind the mountains,
  // edged green while the northern lights are out
  const treeA = clamp((p.dark - 0.6) / 0.4, 0, 1) * clamp(1 - cloud * 2, 0, 1);
  if (treeA > 0.03 && tree) {
    const th = (hz - oy) * 0.9, tw = th * tree.width / tree.height, cx = ox + ART_W * s * 0.5;
    ctx.globalAlpha = 0.92 * treeA;
    ctx.drawImage(tintedTree(mix(top, [0, 0, 0], 0.55)), cx - tw / 2, hz - th, tw, th + 2);
    if (auroraA > 0.03) {
      ctx.globalCompositeOperation = "lighter"; ctx.globalAlpha = 0.1 * auroraA * treeA;
      ctx.drawImage(glowTree(), cx - tw / 2, hz - th - 2 * u, tw, th + 2);
      ctx.globalCompositeOperation = "source-over";
    }
    ctx.globalAlpha = 1;
  }

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

  // Jason's name-day: Bifröst across the daytime sky, fireworks from midnight to five
  const feast = feastOn(realNow), fireworks = fireworksOn(realNow);
  if (feast && light > 0.3) {
    const bands = [0xB0402A, 0xE0703A, 0xECD08F, 0x6FA86A, 0x8FC4E0, 0x5A6AB0, 0x8A6AB0], bw = h * 0.012;
    const r0 = hz * 0.95, bcx = ox + ART_W * s * 0.55, bcy = hz + hz * 0.1;
    ctx.lineWidth = bw * 1.05;
    bands.forEach((c, i) => { ctx.strokeStyle = rgba(hex(c), 0.2 * light * (1 - cloud * 0.6)); ctx.beginPath(); ctx.arc(bcx, bcy, r0 - i * bw, Math.PI, 2 * Math.PI); ctx.stroke(); });
  }
  if (fireworks) drawFireworks(w, hz, u, t, false);

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
    shipRefl = mirrorShip(shipTint, shipRefl);      // the reflection keeps the sail as painted
    sailCloth = cutSail(shipTint, sailCloth);       // the cloth is drawn on its own, shaped by the wind
    fg = landTint;      // the longship is drawn on its own now: it can sail off
    refl = refl || document.createElement("canvas"); refl.width = ART_W; refl.height = ART_H;
    const r = refl.getContext("2d"); r.clearRect(0, 0, ART_W, ART_H);
    r.save(); r.translate(0, 2 * ART_H * HZ); r.scale(1, -1); r.globalAlpha = 80 / 255; r.drawImage(landTint, 0, 0); r.restore();
    tintKey = key;
  }

  if (refl) ctx.drawImage(refl, ox, oy, ART_W * s, ART_H * s);   // reflection of the mountains
  if (fireworks) drawFireworks(w, hz, u, t, true);

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

  if (fg) ctx.drawImage(fg, ox, oy, ART_W * s, ART_H * s);         // the mountains

  // snow lies on the steading while it falls, and for a day and a half after while it stays at freezing
  if (!demo && kind === "snow" && realNow - snowAt > 600000) { snowAt = realNow; try { localStorage.setItem("snowAt", String(snowAt)); } catch (e) { } }
  const tempF = state.weather && state.weather.tempF;
  const snowCover = kind === "snow" || (!demo && realNow - snowAt < 36 * 3600000 && tempF != null && tempF <= 33);

  // the house as the feed reports it; the name-day lights every window and the hearth
  let hs = state.house;
  if (feast) hs = Object.assign({}, hs || {}, { lights: true, hearth: true });
  if (demo) hs = Object.assign({}, hs || {}, { lights: true, hearth: true, solar: p.dark < 0.4 ? SOLAR_FULL_W : 0 });
  // a homecoming (someone home again within the last two minutes) makes the windows flare
  if (state.house && state.house.home_since && state.house.home_since !== lastHomeSince) {
    if (lastHomeSince && realNow - state.house.home_since < 120000) flareAt = realNow;
    lastHomeSince = state.house.home_since;
  }
  const flareAge = realNow - flareAt;
  const flare = flareAge >= 0 && flareAge < 20000 ? (1 - flareAge / 20000) * (0.6 + 0.4 * Math.sin(t * 0.01)) : 0;
  const steadingMoves = drawSteading({ s, ox, oy, t, light, dark: p.dark, snow: snowCover, house: hs, feast, flare });

  // the longship: it sails out of the fjord when no one's home and back when someone is,
  // rows while the house sends power to the grid, and its sail glows with the panels
  const outTarget = hs && hs.hearth === false && !feast ? 1 : 0;
  if (shipOut < 0) shipOut = state.house ? outTarget : 0;
  if (shipOut !== outTarget) { const step = dt / 16; shipOut = shipOut < outTarget ? Math.min(outTarget, shipOut + step) : Math.max(outTarget, shipOut - step); }
  const sailing = shipOut !== outTarget;
  const rowing = sailing || (hs && hs.export > 150);
  let gale = 0;
  if (shipTint && shipOut < 0.995) {
    const ss = shipOut * shipOut * (3 - 2 * shipOut), k = 1 - 0.9 * ss, fade = 1 - ss * ss * ss;
    const pivX = ox + SHIP_PIVOT[0] * s, pivY = oy + SHIP_PIVOT[1] * s;
    ctx.save();
    ctx.translate(lerp(pivX, valleyX, ss), lerp(pivY, hz, ss)); ctx.scale(k, k); ctx.translate(-pivX, -pivY);
    ctx.save(); ctx.translate(ox, oy); ctx.scale(s, s);
    const sun = hs && hs.solar ? Math.sqrt(clamp(hs.solar / SOLAR_FULL_W, 0, 1)) : 0;
    const [sx0, sy0, sx1, sy1] = SAIL;
    if (sun > 0.02) {
      const cx = (sx0 + sx1) / 2, cy = (sy0 + sy1) / 2, rr = (sy1 - sy0) * 1.1;
      const g = ctx.createRadialGradient(cx, cy, 0, cx, cy, rr);
      g.addColorStop(0, rgba(hex(0xECD08F), 0.32 * sun * fade)); g.addColorStop(1, rgba(hex(0xECD08F), 0));
      ctx.fillStyle = g; ctx.beginPath(); ctx.arc(cx, cy, rr, 0, 6.283); ctx.fill();
    }
    if (shipRefl) drawShipReflection(t, fade, rowing);   // below its own waterline, rippling
    ctx.globalAlpha = fade; ctx.drawImage(shipTint, 0, 0); ctx.globalAlpha = 1;
    // the sail, filled by the real wind (as on the launcher): slack in a calm, bellied out in a
    // breeze, shuddering in a gale. In the demo the wind follows its weather.
    const wx = state.weather;
    const windNow = demo ? ({ 95: 40, 63: 18, 73: 14, 45: 2 })[demo.code] ?? 9 : wx && wx.windMph != null ? wx.windMph : 6;
    const gustNow = demo ? windNow * 1.3 : wx && wx.gustMph != null ? wx.gustMph : 0;
    const nowMs = Date.now(), sdt = sailAt ? Math.min(60, (nowMs - sailAt) / 1000) : 60; sailAt = nowMs;
    sailFill += (clamp((windNow - 3) / 22, 0, 1) - sailFill) * Math.min(1, sdt / 3);
    gale = clamp((Math.max(gustNow, windNow * 1.3) - 28) / 20, 0, 1);
    drawSail(t, fade, sun, gale);
    drawOars(t, fade, p.dark, rowing);   // the near side's oars, in front of the hull
    if (feast) dressShip(t, fade);
    ctx.restore(); ctx.restore();
  }

  // rain / snow
  const precip = PRECIP[kind] || 0;
  if (precip) drawPrecip(w, h, dt, t, precip, kind === "snow", light, u);

  return !!demo || auroraA > 0.03 || precip > 0 || kind === "thunder" || steadingMoves || sailing || rowing || fireworks || flare > 0 || gale > 0.02;
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
    case "weather": state.weather = { code: m.code | 0, sunrise: +m.sunrise, sunset: +m.sunset, tempF: m.tempF == null ? null : +m.tempF,
                                      windMph: m.windMph == null ? null : +m.windMph, gustMph: m.gustMph == null ? null : +m.gustMph }; break;
    case "house": state.house = m.house && typeof m.house === "object" ? m.house : null; break;
    case "kp": state.kp = m.kp == null ? null : +m.kp; break;
    case "feast": state.feastUntil = Date.now() + 75000; break;
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
  const [landImg, shipImg] = await Promise.all([load("sky-land.png"), load("sky-ship.png")]);
  land = levelShelf(landImg); ship = shipImg;
  sailMask = makeSailMask(shipImg); tree = makeTree();

  // Preview / testing in a normal browser: ?at=HH:MM&code=63&aurora=1&demo=1
  const q = new URLSearchParams(location.search);
  if (q.has("at")) {
    const [hh, mm] = q.get("at").split(":").map(Number), d = new Date(); d.setHours(hh, mm || 0, 0, 0);
    state.forced = { time: d.getTime(), code: +(q.get("code") || 0), aurora: +(q.get("aurora") || 0.8) };
  }
  if (q.has("demo")) state.demoStart = Date.now();
  if (q.has("house")) state.house = JSON.parse(q.get("house"));
  if (q.has("kp")) state.kp = +q.get("kp");
  if (q.has("wind")) state.weather = Object.assign(state.weather || {}, { windMph: +q.get("wind"), gustMph: +(q.get("gust") || 0) });
  if (q.has("feast")) state.feastUntil = Date.now() + 3600000;
  if (q.has("snow")) snowAt = Date.now();

  // Yggdrasil OS (kde.html?selfhost): no host app, so the page fetches its own weather and the steading feed
  if (q.has("selfhost")) selfHost(+(q.get("lat") || 41.134), +(q.get("lon") || -81.485), q.get("feed") || "https://homelab.ozorhaar.com/steading");

  if (window.chrome && window.chrome.webview) {
    window.chrome.webview.addEventListener("message", (e) => onMessage(e.data));
    window.chrome.webview.postMessage({ type: "ready" });
  }
  tick();
}
// ------------------------------------------------------------------ the steading and its living touches
// Ported from the launcher's FjordScene.kt: the longhouse on a levelled shelf of the left-hand
// mountains, following the house (windows, door, lantern, hearth smoke, forge, Surtur's fire,
// a leak), a raven on the ridge or a chest at the door, the longship that leaves when no one's
// home and rows while the panels feed the grid, the real moon, snow on the roofs, the World Tree,
// Yule, the solstice and Jason's name-day feast.

// The shelf on the left-hand mountains, in the art's coordinates (5120 x 1440).
const SHELF_Y = 420, SHELF_L0 = 1330, SHELF_L1 = 1388, SHELF_R1 = 1730, SHELF_R0 = 1780;
const HALL_L = 1420, HALL_R = 1720;
// The longship layer, afloat (win_art.py: art.fjord_layers(afloat=True, live=True)). Ship units are
// art.py's longship() coordinates: x 200 is midships, y 0 the gunwale, and the hull meets the water
// at y = SHIP.draft. win_art.py checks these numbers against its own, so keep the line as it is.
const SHIP = { x: 2048, wl: 892.8, s: 1.993333, draft: 12 };
const shipPt = (u, v) => [SHIP.x + (u - 200) * SHIP.s, SHIP.wl + (v - SHIP.draft) * SHIP.s];
const SHIP_PIVOT = shipPt(212, SHIP.draft);                           // centre of the waterline
const SAIL = [...shipPt(100, -172), ...shipPt(300, -26)];             // sail cloth box
const MAST_TOP = shipPt(200, -185);
const SHIP_BOX = [...shipPt(-80, -192), ...shipPt(480, SHIP.draft)];  // everything above the water (Freki to Geri)
const OAR_PORTS = Array.from({ length: 9 }, (_, i) => shipPt(70 + i * 34, 2));
// what a narrow screen's crop keeps in view: from left of the lantern post to past the stern
const FOCUS_L = HALL_L - 180, FOCUS_R = SHIP_BOX[2] + 80;
const OAR_LEN = 40.2 * SHIP.s, OAR_REST = Math.atan2(36, -18);       // the still art's oar angle
const SOLAR_FULL_W = 7000;
const NAME = "Jason";

let groundTops = null;      // top of the ground per art column (after levelling)
let sailMask = null;        // just the sail's cloth, for lighting it
let tree = null;            // the World Tree silhouette

/** Levels the shelf into the land art (peaks cut away, dips filled with each column's own surface). */
function levelShelf(img) {
  const c = document.createElement("canvas"); c.width = img.width; c.height = img.height;
  const g = c.getContext("2d", { willReadFrequently: true }); g.drawImage(img, 0, 0);
  const W0 = img.width, H0 = img.height;
  const data = g.getImageData(0, 0, W0, H0), d = data.data;
  const tops = new Int16Array(W0);
  const topOf = (x) => { let y = 0; while (y < H0 && d[(y * W0 + x) * 4 + 3] < 128) y++; return y; };
  for (let x = 0; x < W0; x++) tops[x] = topOf(x);
  const ease = (f) => f * f * (3 - 2 * f);
  for (let x = SHELF_L0; x <= SHELF_R0; x++) {
    const top = tops[x];
    if (top >= H0) continue;
    let target;
    if (x < SHELF_L1) target = top + (SHELF_Y - top) * ease((x - SHELF_L0) / (SHELF_L1 - SHELF_L0));
    else if (x > SHELF_R1) target = top + (SHELF_Y - top) * ease((SHELF_R0 - x) / (SHELF_R0 - SHELF_R1));
    else target = SHELF_Y;
    const tt = Math.round(target);
    if (top < tt) { for (let y = 0; y < tt; y++) d[(y * W0 + x) * 4 + 3] = 0; }
    else if (top > tt) {
      const si = (Math.min(H0 - 1, top + 8) * W0 + x) * 4;
      for (let y = tt; y < top; y++) { const i = (y * W0 + x) * 4; d[i] = d[si]; d[i + 1] = d[si + 1]; d[i + 2] = d[si + 2]; d[i + 3] = 255; }
    }
    tops[x] = tt;
  }
  g.putImageData(data, 0, 0);
  groundTops = tops;
  return c;
}

/** The sail's cloth from the longship layer (rigging and hull left out). */
function makeSailMask(img) {
  const [x0, y0, x1, y1] = SAIL, w = x1 - x0, h = y1 - y0;
  const c = document.createElement("canvas"); c.width = w; c.height = h;
  const g = c.getContext("2d", { willReadFrequently: true }); g.drawImage(img, -x0, -y0);
  const data = g.getImageData(0, 0, w, h), d = data.data;
  for (let i = 0; i < d.length; i += 4) {
    const bright = Math.max(d[i], d[i + 1], d[i + 2]);
    if (d[i + 3] > 100 && bright > 60) { d[i] = 236; d[i + 1] = 208; d[i + 2] = 143; d[i + 3] = 255; } else d[i + 3] = 0;
  }
  g.putImageData(data, 0, 0);
  return c;
}

/** The World Tree's bare crown, drawn once, white (tinted when drawn). */
function makeTree() {
  const wd = 900, ht = 1000, r = mulberry(7), segs = [];
  function branch(x, y, ang, len, sw, depth) {
    const x2 = x + Math.cos(ang) * len, y2 = y + Math.sin(ang) * len;
    segs.push([x, y, x2, y2, sw]);
    if (depth === 0) return;
    const kids = depth >= 5 && r() < 0.45 ? 3 : 2;
    for (let k = 0; k < kids; k++) {
      const side = kids === 3 ? [-1, 1, 0][k] : (k === 0 ? -1 : 1);
      const spread = side === 0 ? 0.05 : 0.28 + 0.32 * r();
      const lean = (ang + Math.PI / 2) * 0.10;
      const a = ang + side * spread + lean + (r() - 0.5) * 0.22;
      branch(x2, y2, a, len * (0.66 + 0.12 * r()), Math.max(1, sw * 0.66), depth - 1);
    }
  }
  let x = 0, y = 0, sw = 60;
  for (let i = 0; i < 3; i++) {
    const a = -Math.PI / 2 + (r() - 0.5) * 0.12, x2 = x + Math.cos(a) * 90, y2 = y + Math.sin(a) * 90;
    segs.push([x, y, x2, y2, sw]); x = x2; y = y2; sw *= 0.92;
  }
  for (const a of [-Math.PI / 2 - 0.7, -Math.PI / 2 - 0.15, -Math.PI / 2 + 0.5]) branch(x, y, a, 150, sw * 0.7, 9);
  let minX = 0, maxX = 0, minY = 0;
  for (const g of segs) { minX = Math.min(minX, g[0], g[2]); maxX = Math.max(maxX, g[0], g[2]); minY = Math.min(minY, g[1], g[3]); }
  const sc = Math.min((wd - 20) / (maxX - minX), (ht - 10) / -minY), cx = wd / 2 - (minX + maxX) / 2 * sc;
  const c = document.createElement("canvas"); c.width = wd; c.height = ht;
  const g = c.getContext("2d"); g.strokeStyle = "#fff"; g.lineCap = "round";
  for (const s of segs) {
    g.lineWidth = Math.max(1, s[4] * sc);
    g.beginPath(); g.moveTo(cx + s[0] * sc, ht + s[1] * sc); g.lineTo(cx + s[2] * sc, ht + s[3] * sc); g.stroke();
  }
  return c;
}

let treeTint = null, treeKey = "";
function tintedTree(col) {
  const k = col.map((v) => v | 0).join();
  if (k === treeKey) return treeTint;
  const o = document.createElement("canvas"); o.width = tree.width; o.height = tree.height;
  const x = o.getContext("2d"); x.drawImage(tree, 0, 0); x.globalCompositeOperation = "source-in";
  x.fillStyle = rgba(col); x.fillRect(0, 0, o.width, o.height);
  treeTint = o; treeKey = k; return o;
}
let treeGlow = null;
function glowTree() {
  if (treeGlow) return treeGlow;
  const o = document.createElement("canvas"); o.width = tree.width; o.height = tree.height;
  const x = o.getContext("2d"); x.drawImage(tree, 0, 0); x.globalCompositeOperation = "source-in";
  x.fillStyle = "#3FE0A0"; x.fillRect(0, 0, o.width, o.height);
  return (treeGlow = o);
}

// ------------------------------------------------------------------ calendar and sky helpers
const SYNODIC = 29.530588853, NEW_MOON = 947182440000;
function moonAge(now) { const a = ((now - NEW_MOON) / 86400000 / SYNODIC) % 1; return a < 0 ? a + 1 : a; }
function moonLit(age) { return (1 - Math.cos(2 * Math.PI * age)) / 2; }
function moonPath(cx, cy, r, age) {
  const k = Math.cos(2 * Math.PI * age), rx = Math.max(0.01, r * Math.abs(k));
  ctx.beginPath(); ctx.moveTo(cx, cy - r);
  if (age < 0.5) { ctx.arc(cx, cy, r, -Math.PI / 2, Math.PI / 2, false); ctx.ellipse(cx, cy, rx, r, 0, Math.PI / 2, -Math.PI / 2, k > 0); }
  else { ctx.arc(cx, cy, r, -Math.PI / 2, Math.PI / 2, true); ctx.ellipse(cx, cy, rx, r, 0, Math.PI / 2, -Math.PI / 2, k <= 0); }
  ctx.closePath();
}
const isYule = (d) => d.getMonth() === 11 || (d.getMonth() === 0 && d.getDate() <= 6);
const isSolstice = (d) => d.getMonth() === 11 && d.getDate() === 21;
function feastOn(now) { const d = new Date(now); return (d.getMonth() === 0 && d.getDate() === 1) || now < state.feastUntil; }
function fireworksOn(now) { const d = new Date(now); return (d.getMonth() === 0 && d.getDate() === 1 && d.getHours() < 5) || now < state.feastUntil; }

// ------------------------------------------------------------------ drawing the touches
/** Everything on and around the longhouse. Returns true while something there moves. */
function drawSteading(o) {
  const { s, ox, oy, t, light, dark, snow, house: hs, feast, flare } = o;
  const X = (a) => ox + a * s, Y = (a) => oy + a * s;
  const base = Y(SHELF_Y) + 0.5 * s;
  const wall = mix(hex(0x141820), hex(0x5A5658), light), roof = mix(hex(0x0B0E15), hex(0x3A3638), light);
  const l = X(HALL_L), r = X(HALL_R), wallTop = base - 40 * s, ridge = base - 100 * s, mid = (l + r) / 2;
  const glow = 0.35 + 0.65 * dark;
  let moving = false;

  // the hall: low walls under a deep, curved turf roof, crossed gable boards at both ends
  ctx.fillStyle = rgba(wall); ctx.fillRect(l, wallTop, r - l, base - wallTop);
  ctx.beginPath(); ctx.moveTo(l - 16 * s, wallTop + 4 * s);
  ctx.quadraticCurveTo(l + 10 * s, ridge + 18 * s, l + 40 * s, ridge); ctx.lineTo(r - 40 * s, ridge);
  ctx.quadraticCurveTo(r - 10 * s, ridge + 18 * s, r + 16 * s, wallTop + 4 * s); ctx.closePath();
  ctx.fillStyle = rgba(roof); ctx.fill();
  ctx.strokeStyle = rgba(roof); ctx.lineCap = "round"; ctx.lineWidth = 5 * s;
  for (const gx of [l + 40 * s, r - 40 * s]) {
    ctx.beginPath(); ctx.moveTo(gx - 13 * s, ridge + 12 * s); ctx.lineTo(gx + 10 * s, ridge - 15 * s);
    ctx.moveTo(gx + 13 * s, ridge + 12 * s); ctx.lineTo(gx - 10 * s, ridge - 15 * s); ctx.stroke();
  }
  ctx.lineWidth = 2.5 * s; ctx.beginPath(); ctx.moveTo(l - 6 * s, wallTop + 2 * s); ctx.lineTo(r + 6 * s, wallTop + 2 * s); ctx.stroke();

  // windows: lit while indoor lights are on; a homecoming makes them flare
  if (hs && hs.lights || flare > 0) {
    const warm = hex(0xF0C070), wy = base - 21 * s, gr0 = 22 * s * (1 + 1.6 * flare);
    for (const wx of [l + 34 * s, l + 82 * s, mid - 46 * s, mid + 46 * s, r - 82 * s, r - 34 * s]) {
      const g = ctx.createRadialGradient(wx, wy, 0, wx, wy, gr0);
      g.addColorStop(0, rgba(warm, Math.min(1, 0.6 * glow + 0.4 * flare))); g.addColorStop(1, rgba(warm, 0));
      ctx.fillStyle = g; ctx.beginPath(); ctx.arc(wx, wy, gr0, 0, 6.283); ctx.fill();
      ctx.fillStyle = rgba(warm, 0.95 * glow); ctx.fillRect(wx - 5 * s, wy - 6 * s, 10 * s, 12 * s);
    }
  }
  // the side door, in the middle: dark when barred, ember when unlocked
  ctx.fillStyle = hs && hs.door ? rgba(hex(0xE0703A), 0.9 * glow + 0.1) : rgba(mix(roof, [0, 0, 0], 0.4));
  ctx.fillRect(mid - 9 * s, base - 30 * s, 18 * s, 30 * s);
  // the garage lantern, on a post at the hall's left end
  const px = l - 22 * s;
  ctx.fillStyle = rgba(roof); ctx.fillRect(px - 2 * s, base - 46 * s, 4 * s, 46 * s);
  if (hs && hs.garage) {
    const ly = base - 48 * s, g = ctx.createRadialGradient(px, ly, 0, px, ly, 34 * s);
    g.addColorStop(0, rgba(hex(0xE0703A), 0.75 * glow + 0.2)); g.addColorStop(1, rgba(hex(0xE0703A), 0));
    ctx.fillStyle = g; ctx.beginPath(); ctx.arc(px, ly, 34 * s, 0, 6.283); ctx.fill();
    ctx.fillStyle = "#ECD08F"; ctx.beginPath(); ctx.arc(px, ly, 4.5 * s, 0, 6.283); ctx.fill();
  } else { ctx.fillStyle = rgba(roof); ctx.beginPath(); ctx.arc(px, base - 48 * s, 4 * s, 0, 6.283); ctx.fill(); }

  // the name-day: long banners stream from poles at both gable ends
  if (feast) {
    [l + 40 * s, r - 40 * s].forEach((gx, i) => {
      const top = ridge - 34 * s, wave = Math.sin(t * 0.004 + i * 1.7) * 4 * s;
      ctx.strokeStyle = rgba(roof); ctx.lineWidth = 2.4 * s;
      ctx.beginPath(); ctx.moveTo(gx, ridge - 10 * s); ctx.lineTo(gx, top); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(gx, top);
      ctx.quadraticCurveTo(gx - 20 * s, top + 2 * s + wave, gx - 42 * s, top + 6 * s + wave * 1.5);
      ctx.quadraticCurveTo(gx - 20 * s, top + 10 * s + wave, gx, top + 14 * s); ctx.closePath();
      ctx.fillStyle = rgba(hex(0xB0402A), 0.95); ctx.fill();
      ctx.fillStyle = rgba(hex(0xECD08F), 0.95); ctx.fillRect(gx - 3 * s, top + 1 * s, 3 * s, 12 * s);
    });
    moving = true;
  }

  // Yule: evergreen swags under the eaves hung with lanterns, and a wreath on the door
  if (isYule(new Date())) {
    const green = mix(hex(0x16261B), hex(0x2F5A3A), light * 0.8 + 0.2), ey = wallTop + 4 * s, n = 6;
    ctx.strokeStyle = rgba(green); ctx.lineWidth = 5 * s;
    for (let i = 0; i < n; i++) {
      const x0 = l - 6 * s + (r - l + 12 * s) * i / n, x1 = l - 6 * s + (r - l + 12 * s) * (i + 1) / n;
      ctx.beginPath(); ctx.moveTo(x0, ey); ctx.quadraticCurveTo((x0 + x1) / 2, ey + 16 * s, x1, ey); ctx.stroke();
    }
    ctx.lineWidth = 3.5 * s; ctx.beginPath(); ctx.arc(mid, base - 38 * s, 7 * s, 0, 6.283); ctx.stroke();
    ctx.fillStyle = rgba(hex(0xB0402A), 0.9); ctx.beginPath(); ctx.arc(mid, base - 31.5 * s, 2.2 * s, 0, 6.283); ctx.fill();
    for (let i = 0; i <= n; i++) {
      const lx = l - 6 * s + (r - l + 12 * s) * i / n, tw = 0.75 + 0.25 * Math.sin(t * 0.003 + i * 1.7);
      const col = hex(i % 2 ? 0xE0703A : 0xECD08F), a = (0.45 + 0.55 * dark) * tw;
      const g = ctx.createRadialGradient(lx, ey + 6 * s, 0, lx, ey + 6 * s, 14 * s);
      g.addColorStop(0, rgba(col, 0.6 * a)); g.addColorStop(1, rgba(col, 0));
      ctx.fillStyle = g; ctx.beginPath(); ctx.arc(lx, ey + 6 * s, 14 * s, 0, 6.283); ctx.fill();
      ctx.fillStyle = rgba(col, 0.95 * a + 0.05); ctx.fillRect(lx - 3 * s, ey + 2 * s, 6 * s, 8 * s);
    }
    moving = true;
  }

  // snow on the turf roof and along the shelf
  if (snow) {
    ctx.fillStyle = rgba(mix(hex(0x8A93A6), hex(0xEEF2F8), light * 0.8 + 0.2));
    ctx.beginPath(); ctx.moveTo(l - 16 * s, wallTop + 4 * s);
    ctx.quadraticCurveTo(l + 10 * s, ridge + 18 * s, l + 40 * s, ridge); ctx.lineTo(r - 40 * s, ridge);
    ctx.quadraticCurveTo(r - 10 * s, ridge + 18 * s, r + 16 * s, wallTop + 4 * s);
    ctx.lineTo(r + 10 * s, wallTop + 2 * s); ctx.quadraticCurveTo(r - 14 * s, ridge + 26 * s, r - 42 * s, ridge + 9 * s);
    ctx.lineTo(l + 42 * s, ridge + 9 * s); ctx.quadraticCurveTo(l + 14 * s, ridge + 26 * s, l - 10 * s, wallTop + 2 * s);
    ctx.closePath(); ctx.fill();
    ctx.fillRect(X(SHELF_L1), base - 3 * s, X(SHELF_R1) - X(SHELF_L1), 6 * s);
  }

  // the hearth: embers in the smoke hole and smoke drifting off while someone's home
  if (hs && hs.hearth) {
    const hx = mid + 40 * s, hy = ridge + 3 * s;
    const flick = 0.8 + 0.2 * Math.sin(t * 0.009) * Math.sin(t * 0.0047 + 1.3);
    let g = ctx.createRadialGradient(hx, hy, 0, hx, hy, 18 * s);
    g.addColorStop(0, rgba(hex(0xE0703A), (0.35 + 0.5 * dark) * flick)); g.addColorStop(1, rgba(hex(0xE0703A), 0));
    ctx.fillStyle = g; ctx.beginPath(); ctx.arc(hx, hy, 18 * s, 0, 6.283); ctx.fill();
    ctx.fillStyle = rgba(hex(0xECD08F), 0.9 * flick); ctx.fillRect(hx - 6 * s, hy - 1.5 * s, 12 * s, 3 * s);
    const pale = mix(hex(0x7C8496), hex(0xB4B9C2), light), strength = (0.42 + 0.28 * dark) * (feast ? 1.35 : 1);
    const life = 7000, n = feast ? 24 : 16;
    for (let i = 0; i < n; i++) {
      const age = ((t + i * life / n) % life) / life;
      const rise = age * 230 * s, drift = -age * age * 110 * s + Math.sin(age * 7 + i) * 7 * s, rad = (10 + 34 * age) * s;
      const warm = Math.max(0, 1 - age * 3) * (0.3 + 0.5 * dark);
      ctx.globalAlpha = clamp(strength * (1 - age) * Math.min(1, age * 6), 0, 1);
      ctx.drawImage(tintPuff(mix(pale, hex(0xE0703A), warm)), hx + drift - rad, hy - rise - rad * 0.6, rad * 2, rad * 1.2);
    }
    ctx.globalAlpha = 1; moving = true;
  }

  // the forge: while the printer works, a stone chimney near the right end throws sparks
  if (hs && hs.forge) {
    const cx = r - 72 * s, ctop = ridge + 6 * s;
    ctx.fillStyle = rgba(mix(hex(0x2A2C30), hex(0x6A6660), light)); ctx.fillRect(cx - 7 * s, ctop - 18 * s, 14 * s, 32 * s);
    const heat = 0.75 + 0.25 * Math.sin(t * 0.011);
    const g = ctx.createRadialGradient(cx, ctop - 18 * s, 0, cx, ctop - 18 * s, 22 * s);
    g.addColorStop(0, rgba(hex(0xE0703A), (0.4 + 0.4 * dark) * heat)); g.addColorStop(1, rgba(hex(0xE0703A), 0));
    ctx.fillStyle = g; ctx.beginPath(); ctx.arc(cx, ctop - 18 * s, 22 * s, 0, 6.283); ctx.fill();
    for (let i = 0; i < 10; i++) {
      const age = ((t + i * 397) % 1600) / 1600;
      const sx = cx + Math.sin(i * 2.3 + age * 5) * 10 * s + (i % 3 - 1) * age * 14 * s, sy = ctop - 20 * s - age * 70 * s;
      ctx.fillStyle = rgba(hex(i % 2 ? 0xE0703A : 0xECD08F), (1 - age) * 0.95);
      ctx.beginPath(); ctx.arc(sx, sy, Math.max(0.5, (1.8 - age) * s * 1.4), 0, 6.283); ctx.fill();
    }
    moving = true;
  }

  // Surtur's fire: while the smoker's lit, a cooking fire with a spit on the slope below the lantern
  if (hs && hs.fire && groundTops) {
    const ax = HALL_L - 70, fx = X(ax), fy = Y(groundTops[ax]) + 2 * s;
    let g = ctx.createRadialGradient(fx, fy - 8 * s, 0, fx, fy - 8 * s, 40 * s);
    g.addColorStop(0, rgba(hex(0xE0703A), 0.35 + 0.45 * dark)); g.addColorStop(1, rgba(hex(0xE0703A), 0));
    ctx.fillStyle = g; ctx.beginPath(); ctx.arc(fx, fy - 8 * s, 40 * s, 0, 6.283); ctx.fill();
    ctx.fillStyle = rgba(mix(hex(0x1A1C20), hex(0x4A4846), light));
    for (let k = -2; k <= 2; k++) { ctx.beginPath(); ctx.arc(fx + k * 6 * s, fy, 3.2 * s, 0, 6.283); ctx.fill(); }
    for (let k = 0; k < 3; k++) {
      const fl = 0.7 + 0.3 * Math.sin(t * (0.013 + k * 0.004) + k * 2), fh = (16 + 6 * (k % 2)) * s * fl, bx = fx + (k - 1) * 6 * s;
      ctx.beginPath(); ctx.moveTo(bx - 5 * s, fy - s);
      ctx.quadraticCurveTo(bx - 4 * s, fy - fh * 0.6, bx + Math.sin(t * 0.009 + k) * 2 * s, fy - fh);
      ctx.quadraticCurveTo(bx + 4 * s, fy - fh * 0.6, bx + 5 * s, fy - s); ctx.closePath();
      ctx.fillStyle = rgba(hex(k === 1 ? 0xECD08F : 0xE0703A), 0.9); ctx.fill();
    }
    ctx.strokeStyle = rgba(mix(hex(0x120E0B), hex(0x3A2C20), light)); ctx.lineWidth = 2.4 * s;
    for (const side of [-1, 1]) {
      const sx = fx + side * 18 * s;
      ctx.beginPath(); ctx.moveTo(sx, fy); ctx.lineTo(sx, fy - 24 * s);
      ctx.moveTo(sx, fy - 24 * s); ctx.lineTo(sx - 3 * s, fy - 28 * s); ctx.moveTo(sx, fy - 24 * s); ctx.lineTo(sx + 3 * s, fy - 28 * s); ctx.stroke();
    }
    ctx.beginPath(); ctx.moveTo(fx - 22 * s, fy - 25 * s); ctx.lineTo(fx + 22 * s, fy - 25 * s); ctx.stroke();
    ctx.fillStyle = ctx.strokeStyle; ctx.beginPath(); ctx.ellipse(fx, fy - 25 * s, 8 * s, 5 * s, 0, 0, 6.283); ctx.fill();
    moving = true;
  }

  // a leak: water rises about the hall's footing and the hall glows ember
  if (hs && hs.leak) {
    const beat = 0.5 + 0.5 * Math.sin(t * 0.006);
    ctx.strokeStyle = rgba(hex(0xE0703A), 0.45 + 0.45 * beat); ctx.lineWidth = 3 * s;
    ctx.strokeRect(l, wallTop, r - l, base - wallTop);
    const wl = l - 40 * s, wr = r + 40 * s;
    ctx.beginPath(); ctx.moveTo(wl, base + 10 * s);
    for (let xx = wl; xx <= wr; xx += 6 * s) ctx.lineTo(xx, base - 8 * s + Math.sin(xx / (14 * s) + t * 0.004) * 3 * s);
    ctx.lineTo(wr, base + 10 * s); ctx.closePath();
    ctx.fillStyle = rgba(hex(0x4F86A8), 0.55); ctx.fill();
    moving = true;
  }

  // a delivery waiting: an iron-bound chest on the ground by the door
  if (hs && hs.chest) {
    const cx = mid + 30 * s, w = 42 * s, h = 26 * s, top = base - h;
    ctx.fillStyle = "#3A2414"; ctx.fillRect(cx - 1.5 * s, top - 1.5 * s, w + 3 * s, h + 1.5 * s);
    ctx.fillStyle = "#5A3A22"; ctx.fillRect(cx, top, w, h);
    ctx.beginPath(); ctx.ellipse(cx + w / 2, top, w / 2, h * 0.45, 0, Math.PI, 0); ctx.fill();
    ctx.strokeStyle = rgba(hex(0xECD08F), 0.9); ctx.lineWidth = 2.4 * s;
    for (const f of [0.18, 0.82]) { ctx.beginPath(); ctx.moveTo(cx + w * f, top - h * 0.42); ctx.lineTo(cx + w * f, base); ctx.stroke(); }
    ctx.beginPath(); ctx.moveTo(cx, top + h * 0.55); ctx.lineTo(cx + w, top + h * 0.55); ctx.stroke();
    ctx.fillStyle = rgba(hex(0xECD08F), 0.9); ctx.fillRect(cx + w / 2 - 3.5 * s, top - 2 * s, 7 * s, 9 * s);
  }

  // a raven on the ridge: someone's at a door (or, on the name-day, a herald with a rune-stick)
  if (hs && hs.raven || feast) {
    const rl = 64 * s, pxr = l + 40 * s + (r - l - 80 * s) * 0.18;
    perchedRaven(pxr, ridge, rl, 7 * Math.sin(t / 1000 * 1.3) * Math.sin(t / 1000 * 0.37 + 0.6), feast && !(hs && hs.raven));
    moving = true;
  }
  return moving;
}

/** A raven sitting with its feet at (x, y), facing out over the fjord; bob turns the head (degrees). */
function perchedRaven(x, y, L, bob, stick) {
  const P = (px, py) => [x + px * L, y + py * L];
  const rad = bob * Math.PI / 180, hp = [-0.18, -0.46];
  const turn = ([px, py]) => { const dx = px - hp[0], dy = py - hp[1]; return [hp[0] + dx * Math.cos(rad) - dy * Math.sin(rad), hp[1] + dx * Math.sin(rad) + dy * Math.cos(rad)]; };
  const poly = (pts, head) => { ctx.beginPath(); pts.forEach((q, i) => { const [a, b] = P(...(head ? turn(q) : q)); i ? ctx.lineTo(a, b) : ctx.moveTo(a, b); }); ctx.closePath(); };
  const ellipse = (cx, cy, rx, ry, deg, head) => {
    const pts = []; const rr = deg * Math.PI / 180;
    for (let i = 0; i < 28; i++) { const a = i / 28 * 2 * Math.PI, ex = rx * Math.cos(a), ey = ry * Math.sin(a); pts.push([cx + ex * Math.cos(rr) - ey * Math.sin(rr), cy + ex * Math.sin(rr) + ey * Math.cos(rr)]); }
    poly(pts, head);
  };
  const parts = [
    () => poly([[0.18, -0.30], [0.64, -0.13], [0.61, -0.05], [0.10, -0.17]]),
    () => ellipse(0.02, -0.32, 0.32, 0.17, 20),
    () => poly([[-0.24, -0.47], [-0.37, -0.38], [-0.14, -0.38]], true),
    () => ellipse(-0.30, -0.56, 0.13, 0.12, 0, true),
    () => poly([[-0.38, -0.62], [-0.55, -0.60], [-0.63, -0.54], [-0.40, -0.49]], true),
  ];
  ctx.strokeStyle = rgba(hex(0x8FC4E0), 0.45); ctx.lineWidth = 0.06 * L; ctx.lineJoin = "round";
  for (const p of parts) { p(); ctx.stroke(); }
  ctx.fillStyle = "#05070C";
  for (const p of parts) { p(); ctx.fill(); }
  ctx.strokeStyle = "#05070C"; ctx.lineCap = "round";
  for (const lx of [-0.03, 0.07]) {
    ctx.lineWidth = 0.04 * L; ctx.beginPath(); ctx.moveTo(...P(lx, -0.17)); ctx.lineTo(...P(lx - 0.01, 0)); ctx.stroke();
    ctx.lineWidth = 0.03 * L; ctx.beginPath(); ctx.moveTo(...P(lx - 0.08, 0)); ctx.lineTo(...P(lx + 0.05, 0)); ctx.stroke();
  }
  ctx.fillStyle = "#8FC4E0"; const e = P(...turn([-0.34, -0.58])); ctx.beginPath(); ctx.arc(e[0], e[1], 0.026 * L, 0, 6.283); ctx.fill();
  if (stick) {
    const [sx, sy] = P(-0.62, -0.56);
    ctx.strokeStyle = "#C8A25A"; ctx.lineWidth = 0.07 * L;
    ctx.beginPath(); ctx.moveTo(sx - 0.22 * L, sy + 0.04 * L); ctx.lineTo(sx + 0.12 * L, sy - 0.02 * L); ctx.stroke();
  }
}

/** Oars out of the hull, sweeping aft through the water and lifting back (in art coordinates). */
/** The sail's cloth, tinted like the ship, cut out of it (the rest of the ship keeps its rigging). */
function cutSail(img, prev) {
  if (!sailMask) return null;
  const [x0, y0, x1, y1] = SAIL, w = x1 - x0, h = y1 - y0;
  const c = prev || document.createElement("canvas"); c.width = w; c.height = h;
  const g = c.getContext("2d"); g.clearRect(0, 0, w, h);
  g.drawImage(img, x0, y0, w, h, 0, 0, w, h);
  g.globalCompositeOperation = "destination-in"; g.drawImage(sailMask, 0, 0); g.globalCompositeOperation = "source-over";
  const s = img.getContext("2d");                                  // and take it out of the ship
  s.globalCompositeOperation = "destination-out"; s.drawImage(sailMask, x0, y0); s.globalCompositeOperation = "source-over";
  return c;
}

/**
 * The sail drawn over a mesh, the launcher's shape: the yard along the top stays put;
 * sailFill 0 hangs slack and wrinkled, 1 bellies out (fatter mid-height, the foot curving down,
 * the edges in shadow); gale adds a fast shudder along the free edge. Art coordinates.
 */
function drawSail(t, fade, sun, gale) {
  if (!sailCloth) return;
  const [x0, y0, x1, y1] = SAIL, w = x1 - x0, h = y1 - y0, m = Math.ceil(w * 0.15);
  const off = sailOff || (sailOff = document.createElement("canvas"));
  if (off.width !== w + 2 * m || off.height !== h + 2 * m) { off.width = w + 2 * m; off.height = h + 2 * m; }
  const g = off.getContext("2d"); g.clearRect(0, 0, off.width, off.height);
  const C = 32, R = 24, fill = sailFill, slack = 1 - fill, PI = Math.PI;   // fine enough for smooth edges
  const pt = (u, v) => {
    const arc = Math.sin(PI * u);
    let dx = (u - 0.5) * w * 0.10 * fill * Math.sin(PI * v);
    let dy = h * (0.07 * fill * v * v + 0.03 * slack * v) * arc;
    dx += w * 0.008 * slack * v * Math.sin(v * 9 + u * 2 + t * 0.0015);
    dx += w * (0.004 + 0.014 * gale) * fill * v * u * Math.sin(t * (0.012 + 0.02 * gale) - u * 7 + v * 3);
    if (gale > 0) dy += h * 0.01 * gale * v * Math.sin(t * 0.03 + u * 11);
    return [m + u * w + dx, m + v * h + dy];
  };
  const grid = [];
  for (let j = 0; j <= R; j++) for (let i = 0; i <= C; i++) grid.push(pt(i / C, j / R));
  for (let j = 0; j < R; j++) for (let i = 0; i < C; i++) {
    const q = [grid[j * (C + 1) + i], grid[j * (C + 1) + i + 1], grid[(j + 1) * (C + 1) + i], grid[(j + 1) * (C + 1) + i + 1]];
    const xs = q.map((p) => p[0]), ys = q.map((p) => p[1]);
    const bx = Math.min(...xs), by = Math.min(...ys), bw = Math.max(...xs) - bx, bh = Math.max(...ys) - by;
    g.drawImage(sailCloth, i * w / C, j * h / R, w / C, h / R, bx - 0.5, by - 0.5, bw + 1, bh + 1);
  }
  // light and shade on the cloth only, as smooth gradients (the launcher's per-vertex shading):
  // edges in shadow as it fills, the belly a touch lighter, a slack sail darker toward its foot
  g.globalCompositeOperation = "source-atop";
  const across = g.createLinearGradient(m, 0, m + w, 0);
  for (let k = 0; k <= 10; k++) {
    const u = k / 10, edge = Math.abs(u - 0.5) * 2, d = 0.28 * fill * edge * edge - 0.06 * fill * (1 - edge);
    across.addColorStop(u, d > 0 ? `rgba(0,0,0,${d.toFixed(3)})` : `rgba(255,255,255,${(-d).toFixed(3)})`);
  }
  g.fillStyle = across; g.fillRect(0, 0, off.width, off.height);
  const down = g.createLinearGradient(0, m, 0, m + h * 1.1);
  down.addColorStop(0, "rgba(0,0,0,0)"); down.addColorStop(1, `rgba(0,0,0,${(0.05 * slack).toFixed(3)})`);
  g.fillStyle = down; g.fillRect(0, 0, off.width, off.height);
  if (sun > 0.02) { g.fillStyle = rgba(hex(0xECD08F), 0.38 * sun); g.fillRect(0, 0, off.width, off.height); }   // the panels' power, caught in it
  g.globalCompositeOperation = "source-over";
  ctx.globalAlpha = fade; ctx.drawImage(off, x0 - m, y0 - m); ctx.globalAlpha = 1;
}

/** The longship's reflection: the part above the water, flipped about the waterline and softened. */
function mirrorShip(img, prev) {
  const [x0, y0, x1, y1] = SHIP_BOX, w = Math.ceil(x1 - x0), h = Math.ceil(y1 - y0);
  const c = prev || document.createElement("canvas"); c.width = w; c.height = h;
  const g = c.getContext("2d"); g.clearRect(0, 0, w, h);
  g.filter = "blur(3px)";
  g.translate(0, h); g.scale(1, -1);
  g.drawImage(img, x0, y0, w, h, 0, 0, w, h);
  return c;
}

/**
 * The longship's reflection, drawn in thin bands that sway sideways like the water's surface:
 * barely at the waterline, more with depth (and more while it rows), fading as it goes down.
 */
function drawShipReflection(t, fade, rowing) {
  const img = shipRefl, bw = img.width, bh = img.height, band = 5;
  const amp = rowing ? 9 : 5;
  for (let y = 0; y < bh; y += band) {
    const d = y / bh;
    const dx = amp * d * Math.sin(y * 0.09 + t * 0.0016) + amp * 0.4 * d * Math.sin(y * 0.031 - t * 0.0011);
    ctx.globalAlpha = (0.32 - 0.20 * d) * fade;
    ctx.drawImage(img, 0, y, bw, Math.min(band, bh - y), SHIP_BOX[0] + dx, SHIP.wl + y, bw, Math.min(band, bh - y));
  }
  ctx.globalAlpha = 1;
}

/**
 * The oars on the near side, from the ports below the shields down to the water. Seen from here an
 * oar reaching toward you meets the water below the hull's own waterline, so only the blade goes
 * under. While rowing they sweep back with the blade in, then lift and swing forward again;
 * otherwise they rest with the blades in the water.
 */
function drawOars(t, fade, dark, rowing) {
  const wood = mix(hex(0x6B5032), hex(0x1C150F), dark);
  const ph = t * 0.0026;
  const a = rowing ? OAR_REST + 0.34 * Math.sin(ph) : OAR_REST + 0.08;
  // The ship heads right (bow to the right): the blades catch forward and pull aft (leftward) while
  // in the water, then lift clear for the return, as on the launcher. 0 = in the water, 1 = clear.
  const lift = rowing ? Math.max(0, -Math.cos(ph)) : 0;
  const len = OAR_LEN * (1 - 0.16 * lift);
  ctx.lineCap = "round";
  // their reflections first: each shaft mirrored about the spot where it meets the water
  const ra = Math.cos(OAR_REST), rs = Math.sin(OAR_REST);
  ctx.strokeStyle = rgba(wood, 0.22 * fade); ctx.lineWidth = 5;
  for (const [px, py] of OAR_PORTS) {
    const wy = py + rs * OAR_LEN * 0.76;                          // the oar's own waterline
    const ca = Math.cos(a), sa = Math.sin(a), bx = px + ca * len * 0.76, by = py + sa * len * 0.76;
    const ty = Math.min(by, wy), tx = px + (bx - px) * (ty - py) / (by - py || 1);
    ctx.beginPath(); ctx.moveTo(tx, 2 * wy - ty); ctx.lineTo(px, 2 * wy - py); ctx.stroke();
  }
  for (const [px, py] of OAR_PORTS) {
    const ca = Math.cos(a), sa = Math.sin(a), ex = px + ca * len, ey = py + sa * len;
    const bx = px + ca * len * 0.76, by = py + sa * len * 0.76;
    ctx.strokeStyle = rgba(wood, fade);
    ctx.lineWidth = 5; ctx.beginPath(); ctx.moveTo(px, py); ctx.lineTo(bx, by); ctx.stroke();
    ctx.strokeStyle = rgba(wood, fade * (0.5 + 0.5 * lift));      // the blade, dimmer while under
    ctx.lineWidth = 11; ctx.beginPath(); ctx.moveTo(bx, by); ctx.lineTo(ex, ey); ctx.stroke();
    if (lift < 0.5) {                                              // a ring where it cuts the water
      ctx.strokeStyle = rgba(hex(0xDDE6F5), 0.22 * fade * (1 - 2 * lift)); ctx.lineWidth = 1.5;
      ctx.beginPath(); ctx.ellipse(bx, by, 11, 3, 0, 0, 6.283); ctx.stroke();
    }
  }
}

/** The longship dressed for the feast: a pennant from the masthead and flags along the stay (art coordinates). */
function dressShip(t, fade) {
  const [mx, my] = MAST_TOP, wave = Math.sin(t * 0.004) * 8;
  ctx.beginPath(); ctx.moveTo(mx, my + 6);
  ctx.quadraticCurveTo(mx + 70, my + 10 + wave, mx + 140, my + 18 + wave * 1.4);
  ctx.quadraticCurveTo(mx + 70, my + 26 + wave, mx, my + 32); ctx.closePath();
  ctx.fillStyle = rgba(hex(0xB0402A), 0.95 * fade); ctx.fill();
  const cols = [0xECD08F, 0xE0703A, 0x8FC4E0], ex = 2470, ey = 770;
  ctx.strokeStyle = rgba(hex(0x1C150F), 0.6 * fade); ctx.lineWidth = 1.5;
  ctx.beginPath(); ctx.moveTo(mx, my + 40); ctx.lineTo(ex, ey); ctx.stroke();
  for (let i = 0; i < 9; i++) {
    const f = (i + 0.5) / 9, fx = mx + (ex - mx) * f, fy = my + 40 + (ey - my - 40) * f;
    ctx.beginPath(); ctx.moveTo(fx - 8, fy); ctx.lineTo(fx + 8, fy); ctx.lineTo(fx, fy + 17); ctx.closePath();
    ctx.fillStyle = rgba(hex(cols[i % 3]), 0.95 * fade); ctx.fill();
  }
}

/** Fireworks over the fjord (and, with mirror, their reflection in the water). */
function drawFireworks(w, hz, u, t, mirror) {
  const period = 1400, life = 2000, tl = Math.floor(t);
  for (let k = 0; k <= 2; k++) {
    const b = Math.floor(tl / period) - k, age = tl - b * period;
    if (age < 0 || age > life) continue;
    const rnd2 = mulberry(b * 7919);
    const x = w * (0.08 + 0.84 * rnd2()), y = hz * (0.2 + 0.3 * rnd2());
    const col = hex([0xECD08F, 0xE0703A, 0x8FC4E0, 0xF0C070][Math.floor(rnd2() * 4)]);
    const speed = hz * (0.22 + 0.12 * rnd2()), a = age / 1000, fade = Math.pow(1 - age / life, 1.5), g = hz * 0.25;
    if (age < 160 && !mirror) {
      const gr = ctx.createRadialGradient(x, y, 0, x, y, 70 * u);
      gr.addColorStop(0, rgba(col, 0.6 * (1 - age / 160))); gr.addColorStop(1, rgba(col, 0));
      ctx.fillStyle = gr; ctx.beginPath(); ctx.arc(x, y, 70 * u, 0, 6.283); ctx.fill();
    }
    ctx.fillStyle = rgba(col, fade * (mirror ? 0.25 : 1));
    for (let i = 0; i < 56; i++) {
      const ang = i / 56 * 2 * Math.PI + rnd2() * 0.12, v = speed * (0.75 + 0.25 * rnd2());
      const px = x + Math.cos(ang) * v * a, py = y + Math.sin(ang) * v * a + 0.5 * g * a * a;
      ctx.beginPath(); ctx.arc(px, mirror ? 2 * hz - py : py, 2.6 * u, 0, 6.283); ctx.fill();
    }
  }
}

/** For Yggdrasil OS: weather every 30 minutes, the steading feed every 30 seconds. */
function selfHost(lat, lon, feed) {
  async function weather() {
    try {
      const r = await fetch(`https://api.open-meteo.com/v1/forecast?latitude=${lat.toFixed(3)}&longitude=${lon.toFixed(3)}` +
        "&current=weather_code,temperature_2m,wind_speed_10m,wind_gusts_10m&temperature_unit=fahrenheit&wind_speed_unit=mph" +
        "&daily=sunrise,sunset&timezone=auto&forecast_days=1&timeformat=unixtime");
      const j = await r.json();
      onMessage({ type: "weather", code: j.current.weather_code, tempF: j.current.temperature_2m,
        windMph: j.current.wind_speed_10m, gustMph: j.current.wind_gusts_10m,
        sunrise: j.daily.sunrise[0] * 1000, sunset: j.daily.sunset[0] * 1000 });
    } catch (e) { /* offline: keep the last sky */ }
  }
  async function steading() {
    try {
      const j = await (await fetch(feed, { cache: "no-store" })).json();
      if (j.house) onMessage({ type: "house", house: j.house });
      if (j.kp != null) onMessage({ type: "kp", kp: j.kp });
    } catch (e) { /* away from home: keep the last house */ }
  }
  weather(); steading();
  setInterval(weather, 30 * 60000);
  setInterval(steading, 30000);
}

start();
