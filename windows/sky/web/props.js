// The steading's places, drawn live: each folder that lives in the launcher's scene has a thing here.
// A line-for-line port of the launcher's Props.kt (the source of truth): change both together.
// Every prop is drawn in its own units (1 = one art pixel at scale 1) from an anchor at its foot, up is -y.
// Call Props.set({ light, dark, t, forge, moon, snow, frost, printPct }) once a frame, then draw.
const Props = (() => {
  const EMBER = 0xE0703A, GOLD = 0xECD08F, FROST = 0x8FC4E0, BONE = 0xE8DCC4;
  const S = { light: 1, dark: 0, t: 0, forge: false, moon: 0, snow: false, frost: 0, printPct: -1 };
  const hx = (h) => [(h >> 16) & 255, (h >> 8) & 255, h & 255];
  const mixc = (a, b, f) => { f = Math.min(1, Math.max(0, f)); const A = hx(a), B = hx(b); return (A.map((v, i) => Math.round(v + (B[i] - v) * f))); };
  const toInt = (c) => (c[0] << 16) | (c[1] << 8) | c[2];
  const mix = (a, b, f) => toInt(mixc(a, b, f));
  const rgba = (c, a = 1) => { const [r, g, b] = hx(c); return `rgba(${r},${g},${b},${Math.min(1, Math.max(0, a)).toFixed(3)})`; };
  const rock = () => mix(0x15171d, 0x5c5862, S.light);
  const darkC = () => mix(0x0b0d12, 0x2c2a2e, S.light);
  const wood = () => mix(0x120e0b, 0x4a3828, S.light);
  const snowC = () => mix(0xDDE4EE, 0xF4F7FA, S.light);
  const capped = () => S.snow || S.frost > 0.05;
  const capStyle = () => S.snow ? rgba(snowC()) : rgba(mix(0xB8C8DC, 0xEAF2FA, S.light), 0.22 + 0.45 * S.frost);
  const PI = Math.PI;

  function fill(g, style) { g.fillStyle = style; }
  function stroke(g, style, w) { g.strokeStyle = style; g.lineWidth = w; g.lineCap = "round"; g.lineJoin = "round"; }
  function lines(g, a) { g.beginPath(); for (let i = 0; i < a.length; i += 4) { g.moveTo(a[i], a[i + 1]); g.lineTo(a[i + 2], a[i + 3]); } g.stroke(); }
  function rect(g, l, t, r, b) { g.fillRect(l, t, r - l, b - t); }
  function oval(g, l, t, r, b) { g.beginPath(); g.ellipse((l + r) / 2, (t + b) / 2, (r - l) / 2, (b - t) / 2, 0, 0, 2 * PI); g.fill(); }
  function circle(g, x, y, r) { g.beginPath(); g.arc(x, y, Math.max(0, r), 0, 2 * PI); g.fill(); }
  function glow(g, x, y, r, a, col = EMBER) {
    const gr = g.createRadialGradient(x, y, 0, x, y, r);
    gr.addColorStop(0, rgba(col, a)); gr.addColorStop(1, rgba(col, 0));
    g.fillStyle = gr; circle(g, x, y, r);
  }
  function flames(g, x, y, w, h, n = 3) {
    for (let k = 0; k < n; k++) {
      const fl = 0.7 + 0.3 * Math.sin(S.t * (0.013 + k * 0.004) + k * 2);
      const fh = h * (1 + 0.3 * (k % 2)) * fl, bx = x + (k - (n - 1) / 2) * w;
      g.beginPath(); g.moveTo(bx - w * 0.85, y);
      g.quadraticCurveTo(bx - w * 0.7, y - fh * 0.6, bx + Math.sin(S.t * 0.009 + k) * w * 0.35, y - fh);
      g.quadraticCurveTo(bx + w * 0.7, y - fh * 0.6, bx + w * 0.85, y); g.closePath();
      fill(g, rgba(k === Math.floor(n / 2) ? GOLD : EMBER, 0.92)); g.fill();
    }
  }
  function fourPoint(g, x, y, r) {
    g.beginPath(); g.moveTo(x, y - r); g.lineTo(x + r * 0.25, y - r * 0.25); g.lineTo(x + r, y); g.lineTo(x + r * 0.25, y + r * 0.25);
    g.lineTo(x, y + r); g.lineTo(x - r * 0.25, y + r * 0.25); g.lineTo(x - r, y); g.lineTo(x - r * 0.25, y - r * 0.25); g.closePath(); g.fill();
  }
  function star(g, x, y, r, a) { fill(g, rgba(0xFFF4D6, a)); fourPoint(g, x, y, r); }
  /** A four-pointed glint. */
  function glint(g, x, y, r, a, col = FROST) { fill(g, rgba(col, a)); fourPoint(g, x, y, r); }
  function sparks(g, x, y, n, life, rise) {
    for (let i = 0; i < n; i++) {
      const age = ((S.t + i * life / n) % life) / life;
      const sx = x + Math.sin(i * 2.3 + age * 5) * 8 + (i % 3 - 1) * age * 12;
      fill(g, rgba(i % 2 === 0 ? GOLD : EMBER, (1 - age) * 0.95)); circle(g, sx, y - age * rise, (1.8 - age) * 1.2 + 0.3);
    }
  }
  /** A few rime crystals twinkling along a line (frost only, not snow). */
  function rime(g, x0, x1, y, n = 4) {
    if (S.snow || S.frost < 0.05) return;
    const shine = S.frost * Math.max(0.3 + 0.7 * S.moon, S.light * 0.6);
    for (let i = 0; i < n; i++) {
      const u = (i + 0.5) / n, tw = Math.max(0, Math.sin(S.t * 0.0023 + i * 2.4 + x0 * 0.05));
      if (tw > 0.1) glint(g, x0 + (x1 - x0) * u, y, 2.5 + 3 * tw, 0.8 * shine * tw);
    }
  }
  function stones(g, cx, gap, r) { fill(g, rgba(rock())); for (let k = -2; k <= 2; k++) circle(g, cx + k * gap, 0, r); }

  // ---------- the rune of the day (RuneOfDay.kt; sowilo, tiwaz, algiz, othala and jera are never used)
  const RUNES = [
    [0, 0, 0, 1, 0, .3, .65, 0, 0, .58, .65, .28],                                     // Fehu
    [0, 1, 0, 0, 0, 0, .7, .35, .7, .35, .7, 1],                                       // Uruz
    [0, 0, 0, 1, 0, .25, .6, .5, .6, .5, 0, .75],                                      // Thurisaz
    [0, 0, 0, 1, 0, 0, .6, .3, 0, .3, .6, .6],                                         // Ansuz
    [0, 0, 0, 1, 0, 0, .6, .22, .6, .22, 0, .45, 0, .45, .6, 1],                       // Raidho
    [.6, 0, 0, .5, 0, .5, .6, 1],                                                      // Kenaz
    [0, 0, 1, 1, 1, 0, 0, 1],                                                          // Gebo
    [0, 0, 0, 1, 0, 0, .6, .22, .6, .22, 0, .45],                                      // Wunjo
    [0, 0, 0, 1, 1, 0, 1, 1, 0, .35, 1, .65],                                          // Hagalaz
    [.5, 0, .5, 1, .15, .35, .85, .62],                                                // Naudiz
    [.5, 0, .5, 1],                                                                    // Isa
    [.5, 0, .5, 1, .5, 0, .85, .22, .5, 1, .15, .78],                                  // Eihwaz
    [0, 0, 0, 1, 0, 0, .55, .25, .55, .25, .55, .05, 0, 1, .55, .75, .55, .75, .55, .95], // Perthro
    [.5, 0, 1, .5, 1, .5, .5, 1, .5, 1, 0, .5, 0, .5, .5, 0],                          // Ingwaz
    [0, 0, 0, 1, 1, 0, 1, 1, 0, 0, 1, 1, 1, 0, 0, 1],                                  // Dagaz
    [0, 0, 0, 1, 1, 0, 1, 1, 0, 0, 1, .45, 1, 0, 0, .45],                              // Mannaz
    [0, 0, 0, 1, 0, 0, .6, .3],                                                        // Laguz
    [0, 0, 0, 1, 0, 0, .6, .25, .6, .25, 0, .5, 0, .5, .6, .75, .6, .75, 0, 1],        // Berkano
    [0, 0, 0, 1, 1, 0, 1, 1, 0, 0, .5, .35, .5, .35, 1, 0],                            // Ehwaz
  ];
  function runeToday(now = new Date()) {
    const doy = Math.floor((Date.UTC(now.getFullYear(), now.getMonth(), now.getDate()) - Date.UTC(now.getFullYear(), 0, 0)) / 86400000);
    const n = now.getFullYear() * 400 + doy, m = RUNES.length;
    return RUNES[(((n * 7) % m) + m) % m];
  }

  /** Personal: a carved runestone on the ridge, the rune of the day cut large in its serpent band. */
  function runestone(g, stir = false) {
    const pulse = 0.5 + 0.5 * Math.sin(S.t * 0.004);
    if (stir) glow(g, 0, -50, 64, 0.18 + 0.22 * pulse);
    g.beginPath(); g.moveTo(-22, 2); g.lineTo(-26, -58); g.quadraticCurveTo(-24, -92, 0, -100);
    g.quadraticCurveTo(24, -95, 26, -60); g.lineTo(22, 2); g.closePath();
    fill(g, rgba(rock())); g.fill();
    stroke(g, stir ? rgba(EMBER, 0.6 + 0.4 * pulse) : rgba(GOLD, 0.35 + 0.35 * S.dark), 2.6);
    g.beginPath(); g.moveTo(-14, -4); g.lineTo(-17, -56); g.quadraticCurveTo(-16, -82, 0, -88);
    g.quadraticCurveTo(16, -84, 17, -58); g.lineTo(14, -10); g.quadraticCurveTo(10, -2, 4, -8); g.stroke();
    const r = runeToday();
    let minX = 1, maxX = 0;
    for (let i = 0; i < r.length; i += 2) { minX = Math.min(minX, r[i]); maxX = Math.max(maxX, r[i]); }
    const gw = 22, gh = 44, ox = -(minX + maxX) / 2 * gw, oy = -72;
    g.lineWidth = 2.6;
    lines(g, r.map((v, i) => i % 2 === 0 ? ox + v * gw : oy + v * gh));
    if (capped()) {
      g.beginPath(); g.moveTo(-25, -78); g.quadraticCurveTo(-23, -97, 0, -103); g.quadraticCurveTo(23, -98, 25, -78);
      g.lineTo(19, -84); g.quadraticCurveTo(0, -91, -19, -84); g.closePath();
      fill(g, capStyle()); g.fill();
    }
    rime(g, -20, 20, -96, 3);
  }

  /** Finance: a cave in the mountain's face, a dragon's gold heaped inside, glinting. */
  function cave(g, stir = false) {
    g.beginPath(); g.moveTo(-64, 0); g.quadraticCurveTo(-62, -72, 0, -84); g.quadraticCurveTo(60, -74, 66, 0); g.closePath();
    fill(g, rgba(mix(0x030406, 0x14131a, S.light))); g.fill();
    stroke(g, rgba(rock()), 7);
    g.beginPath(); g.moveTo(-70, 3); g.quadraticCurveTo(-68, -78, 0, -91); g.quadraticCurveTo(66, -80, 72, 3); g.stroke();
    if (capped()) { stroke(g, capStyle(), 4); g.beginPath(); g.moveTo(-58, -48); g.quadraticCurveTo(-52, -86, 0, -95); g.quadraticCurveTo(52, -88, 60, -50); g.stroke(); }
    rime(g, -50, 50, -86, 4);
    glow(g, 0, -12, 70, 0.18 + 0.32 * S.dark, GOLD);
    g.beginPath(); g.moveTo(-50, 0); g.quadraticCurveTo(-36, -24, -12, -30); g.quadraticCurveTo(10, -36, 30, -22);
    g.quadraticCurveTo(44, -12, 52, 0); g.closePath();
    fill(g, rgba(mix(0x6b5320, 0xc8a040, 0.55 + 0.45 * Math.max(S.light, S.dark * 0.8)))); g.fill();
    fill(g, rgba(mix(0x8a6a28, GOLD, 0.6)));
    for (const [x, y] of [[-30, -8], [-14, -18], [4, -24], [20, -14], [34, -6], [-4, -6], [12, -4]]) oval(g, x - 4.5, y - 2.2, x + 4.5, y + 2.2);
    const tail = mix(0x07080b, 0x1d1b22, S.light);
    stroke(g, rgba(tail), 7);
    g.beginPath(); g.moveTo(62, -6); g.quadraticCurveTo(40, -46, 6, -40); g.quadraticCurveTo(-18, -36, -20, -50); g.stroke();
    fill(g, rgba(tail));
    for (const [x, y] of [[44, -32], [26, -42], [8, -44]]) { g.beginPath(); g.moveTo(x - 4, y); g.lineTo(x, y - 9); g.lineTo(x + 4, y); g.closePath(); g.fill(); }
    for (const [x, y, ph] of [[-22, -20, 0], [8, -30, 1.7], [28, -16, 3.1], [-38, -6, 4.4]]) {
      const a = Math.max(0, Math.sin(S.t * 0.002 + ph)); if (a > 0.05) star(g, x, y, 5 * a + 1, 0.9 * a);
    }
    if (stir && (S.t % 5200) > 220) for (const ex of [-13, 13]) {
      glow(g, ex, -60, 11, 0.55, GOLD);
      fill(g, rgba(0xFFE08A, 0.95)); oval(g, ex - 5.5, -62.6, ex + 5.5, -57.4);
      fill(g, "#14100A"); rect(g, ex - 0.9, -62.2, ex + 0.9, -57.8);
    }
  }

  /** Video: a skald by a little fire on the ridge, his lyre on his knee. */
  function skald(g, stir = false) {
    g.beginPath(); g.moveTo(-50, 16); g.quadraticCurveTo(-40, 1, -20, 0); g.lineTo(44, 0); g.quadraticCurveTo(60, 1, 68, 16); g.closePath();
    fill(g, rgba(mix(0x1a151f, 0x3b2f45, S.light))); g.fill();
    glow(g, 22, -10, stir ? 80 : 58, 0.25 + 0.45 * S.dark + (stir ? 0.15 : 0));
    stones(g, 22, 6, 3.4);
    flames(g, 22, -1, 5.5, stir ? 28 : 16);
    if (stir) sparks(g, 22, -18, 8, 2200, 80);
    fill(g, rgba(darkC()));
    g.beginPath(); g.moveTo(-26, 0); g.quadraticCurveTo(-30, -22, -20, -34); g.quadraticCurveTo(-12, -44, -6, -36);
    g.quadraticCurveTo(-2, -24, 2, -14); g.lineTo(6, 0); g.closePath(); g.fill();
    circle(g, -12, -40, 7);
    g.beginPath(); g.moveTo(-20, -42); g.quadraticCurveTo(-12, -54, -4, -42); g.closePath(); g.fill();
    stroke(g, rgba(GOLD, 0.6 + 0.3 * S.dark), 2);
    g.beginPath(); g.moveTo(0, -12); g.quadraticCurveTo(-2, -30, 4, -32); g.moveTo(0, -12); g.quadraticCurveTo(12, -26, 10, -32);
    g.moveTo(3, -30); g.lineTo(10, -30); g.stroke();
    g.lineWidth = 0.8; lines(g, [4, -29, 2, -14, 6, -29, 4, -14, 8, -29, 6, -14]);
  }

  /** Work: a smithy on a ledge, its forge glowing through the door (rising with a print), an anvil outside. */
  function smithy(g, stir = false) {
    g.beginPath(); g.moveTo(-140, 2); g.lineTo(96, 2); g.lineTo(84, 16); g.quadraticCurveTo(-10, 26, -128, 14); g.closePath();
    fill(g, rgba(rock())); g.fill();
    fill(g, rgba(mix(0x141820, 0x5a5658, S.light))); rect(g, -52, -42, 52, 2);
    g.beginPath(); g.moveTo(-66, -38); g.quadraticCurveTo(-36, -72, 0, -76); g.quadraticCurveTo(36, -72, 66, -38); g.closePath();
    fill(g, rgba(mix(0x0b0e15, 0x3a3638, S.light))); g.fill();
    fill(g, rgba(rock())); rect(g, 30, -88, 44, -50);
    const prog = S.forge && S.printPct >= 0 ? Math.min(100, Math.max(0, S.printPct)) / 100 : -1;
    const heat = (0.7 + 0.3 * Math.sin(S.t * 0.004) * (S.forge ? 1.6 : 1)) * (prog >= 0 ? 0.6 + 0.6 * prog : 1);
    glow(g, -8, -16, 46 + (prog >= 0 ? 20 * prog : 0), (0.25 + 0.45 * S.dark) * heat);
    fill(g, rgba(EMBER, 0.55 + 0.4 * heat * (0.5 + 0.5 * S.dark))); rect(g, -20, -32, 4, 2);
    if (prog >= 0) { fill(g, rgba(GOLD, 0.9)); rect(g, -18, 1 - 32 * prog, 2, 1); }
    else { fill(g, rgba(GOLD, 0.35 * heat)); rect(g, -16, -12, 0, -2); }
    if (capped()) {
      g.beginPath(); g.moveTo(-66, -38); g.quadraticCurveTo(-36, -72, 0, -76); g.quadraticCurveTo(36, -72, 66, -38);
      g.lineTo(60, -42); g.quadraticCurveTo(34, -65, 0, -69); g.quadraticCurveTo(-34, -65, -60, -42); g.closePath();
      fill(g, capStyle()); g.fill();
      stroke(g, capStyle(), 3); lines(g, [-96, 1, 92, 1]);
    }
    rime(g, -50, 50, -64, 4); rime(g, -120, 80, 0, 5);
    g.save(); g.translate(3.5, -1); g.scale(1.5, 1.5);
    fill(g, rgba(mix(0x07080b, 0x26262a, S.light))); rect(g, -82, -10, -72, 2);
    g.beginPath(); g.moveTo(-92, -10); g.lineTo(-62, -10); g.quadraticCurveTo(-58, -15, -64, -18); g.lineTo(-90, -18); g.closePath(); g.fill();
    if (stir || prog >= 0) {
      const ph = (S.t % 2400) / 2400;
      if (ph < 0.32) {
        const k = ph / 0.32;
        glow(g, -77, -18, 26, 0.6 * (1 - k), GOLD);
        for (let i = 0; i < 12; i++) {
          const a = -PI / 2 + (i - 5.5) * 0.2, r = 6 + k * (24 + (i % 4) * 6);
          fill(g, rgba(i % 2 === 0 ? GOLD : EMBER, 1 - k));
          circle(g, -77 + Math.cos(a) * r, -18 + Math.sin(a) * r + k * k * 10, 1.6 * (1 - k) + 0.4);
        }
      }
    }
    g.restore();
    if (S.forge) for (let i = 0; i < 10; i++) {
      const life = 1600, age = ((S.t + i * 397) % life) / life;
      const sx = 37 + Math.sin(i * 2.3 + age * 5) * 10 + (i % 3 - 1) * age * 14, sy = -90 - age * 70;
      fill(g, rgba(i % 2 === 1 ? EMBER : GOLD, (1 - age) * 0.95)); circle(g, sx, sy, (1.8 - age) * 1.4);
    }
  }

  /** Food: a cookfire with a cauldron hung from a tripod, steam rising. */
  function cookfire(g, stir = false) {
    glow(g, 0, -10, 56, 0.25 + 0.45 * S.dark);
    stones(g, 0, 7, 3.6);
    flames(g, 0, -1, 6, 14);
    stroke(g, rgba(wood()), 3);
    lines(g, [-30, 2, 0, -66, 0, -66, 30, 2, 8, 4, 0, -66]);
    g.lineWidth = 1.5; lines(g, [0, -66, 0, -44]);
    g.beginPath(); g.moveTo(-19, -44); g.lineTo(19, -44); g.quadraticCurveTo(21, -16, 0, -14); g.quadraticCurveTo(-21, -16, -19, -44); g.closePath();
    fill(g, rgba(mix(0x07080b, 0x2a2a2e, S.light))); g.fill();
    stroke(g, rgba(mix(0x2a2a2e, 0x7a7670, S.light)), 2.5); lines(g, [-21, -44, 21, -44]);
    const puffs = stir ? 9 : 4, life = stir ? 2000 : 3200;
    for (let i = 0; i < puffs; i++) {
      const age = ((S.t + i * life / puffs) % life) / life;
      fill(g, rgba(0xE8ECF2, (stir ? 0.32 : 0.22) * (1 - age)));
      circle(g, Math.sin(age * 4 + i) * (stir ? 10 : 6), -48 - age * (stir ? 70 : 46), (stir ? 5 : 4) + age * (stir ? 13 : 9));
    }
    if (stir) for (let i = 0; i < 4; i++) {
      const ph = (((S.t * 0.003 + i * 1.7) % 1) + 1) % 1;
      fill(g, rgba(0xBFD3E6, 0.7 * (1 - ph))); circle(g, -12 + i * 8, -45 - ph * 7, 1.6);
    }
  }

  function knarrShape(g, lantern, furled = false) {
    stroke(g, rgba(darkC()), 4); lines(g, [0, -12, 0, -150]);
    g.lineWidth = 5; lines(g, [-62, -142, 62, -142]);
    g.lineWidth = 1.6; lines(g, [0, -150, -112, -30, 0, -150, 112, -30]);
    const sl = 0.55 + 0.45 * S.light;
    if (furled) { stroke(g, rgba(mix(BONE, 0x000000, 1 - sl)), 7); lines(g, [-58, -137, 58, -137]); }
    else {
      for (let i = 0; i < 6; i++) { fill(g, rgba(mix(i % 2 === 1 ? BONE : FROST, 0x000000, 1 - sl))); rect(g, -56 + i * 18.6, -139, -56 + i * 18.6 + 18.8, -69); }
      fill(g, "rgba(0,0,0,0.25)"); rect(g, -56, -139, 56, -69);
    }
    fill(g, rgba(mix(0x2a2016, 0x8a6e4a, S.light)));
    for (const [bx, bw] of [[-82, 26], [-54, 22], [48, 24], [74, 22]]) { g.beginPath(); g.roundRect(bx, -30, bw, 18, 5); g.fill(); }
    g.beginPath(); g.moveTo(-118, -36); g.quadraticCurveTo(-112, -10, -96, -12); g.lineTo(96, -12); g.quadraticCurveTo(112, -10, 118, -36);
    g.quadraticCurveTo(124, -12, 104, 4); g.quadraticCurveTo(0, 18, -104, 4); g.quadraticCurveTo(-124, -12, -118, -36); g.closePath();
    fill(g, rgba(darkC())); g.fill();
    stroke(g, rgba(GOLD, 0.25 + 0.2 * S.light), 1.6);
    g.beginPath(); g.moveTo(-98, -8); g.quadraticCurveTo(0, 2, 98, -8); g.stroke();
    if (lantern) {
      const fl = 0.8 + 0.2 * Math.sin(S.t * 0.011) * Math.sin(S.t * 0.0067 + 1);
      stroke(g, rgba(darkC()), 2); lines(g, [110, -36, 110, -58]);
      glow(g, 110, -62, 34, (0.45 + 0.3 * S.dark) * fl, GOLD);
      fill(g, rgba(GOLD, 0.95 * fl)); g.beginPath(); g.roundRect(106, -67, 8, 10, 2); g.fill();
    }
  }
  /** Shop: a knarr, the broad-bellied trader, riding at anchor with bales on deck, and its reflection. */
  function knarr(g, stir = false) {
    const bob = Math.sin(S.t * 0.0015) * 3, roll = Math.sin(S.t * 0.0011) * 0.012;
    g.save(); g.globalAlpha *= 0.28; g.scale(1, -1); g.translate(0, -bob); g.rotate(-roll); knarrShape(g, stir); g.restore();
    g.save(); g.translate(0, bob); g.rotate(roll); knarrShape(g, stir); g.restore();
    stroke(g, rgba(0xDDE6F5, 0.18), 1.5); lines(g, [-120, 6, -90, 6, 92, 6, 124, 6]);
  }
  /** The knarr drawn up on the shore for the cold, its sail furled (no reflection: it's on land). */
  function knarrBeached(g, stir = false) {
    g.save(); g.rotate(-5 * PI / 180); knarrShape(g, stir, true);
    if (capped()) { stroke(g, capStyle(), 3); lines(g, [-100, -13, 100, -13]); }
    rime(g, -90, 90, -14, 5);
    g.restore();
  }

  /** Mail: Ratatoskr, head up (the caller turns him along his branch), tail plumed; gold-edged by the moon. */
  function squirrel(g) {
    const lit = Math.max(S.light, 0.38 + 0.3 * S.moon);
    const fur = rgba(mix(0x3a1a0c, 0xa9532a, lit)), dk = rgba(mix(0x1c0d06, 0x5e2a12, lit));
    const sheen = S.moon * (0.75 + 0.25 * Math.sin(S.t * 0.0021)) * (1 - S.light);
    if (sheen > 0.03) glow(g, 6, -6, 30, 0.22 * sheen, GOLD);
    const tailPath = () => { g.beginPath(); g.moveTo(3, 10); g.bezierCurveTo(22, 16, 26, -8, 14, -20); g.bezierCurveTo(10, -25, 4, -22, 6, -16); };
    fill(g, fur); tailPath(); g.bezierCurveTo(14, -8, 12, 6, 2, 4); g.closePath(); g.fill();
    if (sheen > 0.03) { stroke(g, rgba(GOLD, 0.75 * sheen), 1.3); tailPath(); g.stroke(); fill(g, fur); }
    oval(g, -7, -13, 7, 13);
    circle(g, -1, -16, 5.6);
    g.beginPath(); g.moveTo(-3, -20); g.lineTo(-1, -27); g.lineTo(2, -20); g.closePath(); g.fill();
    stroke(g, dk, 2.2); lines(g, [-5, -6, -10, -9, -5, 8, -10, 11]);
    if (sheen > 0.03) { stroke(g, rgba(GOLD, 0.55 * sheen), 1.1); g.beginPath(); g.ellipse(-1, -16, 5.6, 5.6, 0, -70 * PI / 180, 50 * PI / 180); g.stroke(); }
    fill(g, "#0A0604"); circle(g, -3.2, -17, 1.2);
  }

  /** Games: Jörmungandr's coils breaking the water (anchor on the waterline), tail tip at the left, head at the right:
   *  low and sleepy, or risen with a burning eye and a flicking tongue when a game calls. */
  function serpent(g, stir = false) {
    const lit = Math.max(S.light, 0.38 * S.moon);
    const scale = mix(0x0c2224, 0x2e5f57, lit), spine = mix(0x061314, 0x1d3a35, lit);
    const silver = S.moon * (1 - S.light), band = 24;
    const humps = [[-430, 150, 0], [-210, 170, 1.3], [20, 160, 2.6], [240, 140, 3.9]];
    const hump = (x, w, ph, refl) => {
      const hh = 44 + 6 * Math.sin(S.t * 0.0012 + ph);
      fill(g, refl ? rgba(scale, 0.22 + 0.1 * silver) : rgba(scale));
      g.beginPath(); g.moveTo(x - w / 2, 0); g.bezierCurveTo(x - w / 2, -hh * 1.33, x + w / 2, -hh * 1.33, x + w / 2, 0);
      g.lineTo(x + w / 2 - band, 0);
      g.bezierCurveTo(x + w / 2 - band, -(hh - band) * 1.33, x - w / 2 + band, -(hh - band) * 1.33, x - w / 2 + band, 0);
      g.closePath(); g.fill();
      if (refl) return;
      fill(g, rgba(spine));
      for (let k = 1; k < 6; k++) {
        const a = PI * (1 - k / 6), cx = x + Math.cos(a) * w / 2 * 0.98, cy = -Math.sin(a) * hh;
        g.beginPath(); g.moveTo(cx - 5, cy + 2); g.lineTo(cx + Math.cos(a) * 3, cy - 11); g.lineTo(cx + 5, cy + 2); g.closePath(); g.fill();
      }
      if (silver > 0.03) {
        stroke(g, rgba(0xCFDBF0, 0.35 * silver), 1.8);
        g.beginPath(); g.moveTo(x - w / 2, 0); g.bezierCurveTo(x - w / 2, -hh * 1.33, x + w / 2, -hh * 1.33, x + w / 2, 0); g.stroke();
        for (let j = 0; j < 3; j++) {
          const u = (S.t * 0.00018 + ph * 0.37 + j / 3) % 1, a = PI * (1 - u), tw = Math.sin(u * PI);
          glint(g, x + Math.cos(a) * w / 2, -Math.sin(a) * hh, 4 + 4 * tw, 0.8 * silver * tw);
        }
      }
      stroke(g, rgba(mix(0x2a4a5a, 0xdde6f5, S.light * 0.6), 0.35), 1.6);
      g.beginPath(); g.ellipse(x - w / 2 + band / 2, 2, band, 4, 0, 0, 2 * PI); g.stroke();
      g.beginPath(); g.ellipse(x + w / 2 - band / 2, 2, band, 4, 0, 0, 2 * PI); g.stroke();
    };
    g.save(); g.scale(1, -1); for (const h of humps) hump(h[0], h[1], h[2], true); g.restore();
    for (const h of humps) hump(h[0], h[1], h[2], false);
    fill(g, rgba(scale));
    const tf = 6 * Math.sin(S.t * 0.002);
    g.beginPath(); g.moveTo(-560, 0); g.quadraticCurveTo(-585, -30 + tf, -606, -22 + tf); g.quadraticCurveTo(-588, -14 + tf, -572, 0); g.closePath(); g.fill();
    const hy = -(stir ? 26 + 4 * Math.sin(S.t * 0.003) : 0);
    g.beginPath(); g.moveTo(350, 0); g.quadraticCurveTo(352, hy - 30, 386, hy - 34); g.quadraticCurveTo(430, hy - 38, 452, hy - 22);
    g.quadraticCurveTo(470, hy - 14, 468, hy - 6); g.quadraticCurveTo(440, hy - 4, 420, hy - 8); g.quadraticCurveTo(404, hy + 4, 392, 0); g.closePath();
    fill(g, rgba(scale)); g.fill();
    fill(g, rgba(spine)); g.beginPath(); g.moveTo(372, hy - 32); g.lineTo(380, hy - 48); g.lineTo(390, hy - 34); g.closePath(); g.fill();
    if (stir) {
      glow(g, 420, hy - 24, 26, 0.7, GOLD);
      fill(g, "#FFC860"); oval(g, 415, hy - 27, 425, hy - 21);
      if (S.t % 1400 < 300) { stroke(g, "#B0402A", 1.6); lines(g, [468, hy - 8, 486, hy - 6, 486, hy - 6, 492, hy - 10, 486, hy - 6, 492, hy - 2]); }
    } else { stroke(g, rgba(spine), 2); lines(g, [414, hy - 24, 426, hy - 24]); }
  }

  function set(o) { Object.assign(S, o); }
  return { set, runestone, cave, skald, smithy, cookfire, knarr, knarrBeached, squirrel, serpent, glint, sparks, runeToday };
})();
if (typeof module !== "undefined") module.exports = Props;
