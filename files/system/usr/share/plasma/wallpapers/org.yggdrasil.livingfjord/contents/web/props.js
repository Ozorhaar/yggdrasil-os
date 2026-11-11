// The steading's places, drawn live: each folder that lives in the scene has a thing you can tap.
// Shared drawing for the launcher (ported to FjordScene.kt) and the desktop living fjord.
// Every prop is drawn in its own units (1 = one art pixel at scale 1) from an anchor at its foot,
// up is -y. o = {light 0..1 (daylight), dark 0..1 (night), t ms, forge bool}.
const Props = (() => {
  const hx = (h) => [(h >> 16) & 255, (h >> 8) & 255, h & 255];
  const mix = (a, b, t) => { const A = hx(a), B = hx(b); return A.map((v, i) => Math.round(v + (B[i] - v) * t)); };
  const rgba = (c, a = 1) => `rgba(${c[0]},${c[1]},${c[2]},${a})`;
  const EMBER = 0xE0703A, GOLD = 0xECD08F, FROST = 0x8FC4E0, BONE = 0xE8DCC4;
  const rock = (o) => mix(0x15171d, 0x5c5862, o.light);
  const dark = (o) => mix(0x0b0d12, 0x2c2a2e, o.light);
  const wood = (o) => mix(0x120e0b, 0x4a3828, o.light);
  function glow(g, x, y, r, a, col = EMBER) {
    const gr = g.createRadialGradient(x, y, 0, x, y, r);
    gr.addColorStop(0, rgba(hx(col), a)); gr.addColorStop(1, rgba(hx(col), 0));
    g.fillStyle = gr; g.beginPath(); g.arc(x, y, r, 0, 6.2832); g.fill();
  }
  function flames(g, x, y, w, h, t, n = 3) {
    for (let k = 0; k < n; k++) {
      const fl = 0.7 + 0.3 * Math.sin(t * (0.013 + k * 0.004) + k * 2);
      const fh = h * (1 + 0.3 * (k % 2)) * fl, bx = x + (k - (n - 1) / 2) * w;
      g.beginPath(); g.moveTo(bx - w * 0.85, y);
      g.quadraticCurveTo(bx - w * 0.7, y - fh * 0.6, bx + Math.sin(t * 0.009 + k) * w * 0.35, y - fh);
      g.quadraticCurveTo(bx + w * 0.7, y - fh * 0.6, bx + w * 0.85, y); g.closePath();
      g.fillStyle = rgba(hx(k === Math.floor(n / 2) ? GOLD : EMBER), 0.92); g.fill();
    }
  }
  function star(g, x, y, r, a) {
    g.fillStyle = rgba(hx(0xFFF4D6), a);
    g.beginPath(); g.moveTo(x, y - r); g.lineTo(x + r * 0.25, y - r * 0.25); g.lineTo(x + r, y); g.lineTo(x + r * 0.25, y + r * 0.25);
    g.lineTo(x, y + r); g.lineTo(x - r * 0.25, y + r * 0.25); g.lineTo(x - r, y); g.lineTo(x - r * 0.25, y - r * 0.25); g.closePath(); g.fill();
  }

  /** Personal: a carved runestone on the ridge, its serpent band catching the light. */
  function runestone(g, o) {
    g.fillStyle = rgba(rock(o));
    g.beginPath(); g.moveTo(-22, 2); g.lineTo(-26, -58); g.quadraticCurveTo(-24, -92, 0, -100);
    g.quadraticCurveTo(24, -95, 26, -60); g.lineTo(22, 2); g.closePath(); g.fill();
    // the carving: a serpent band round the face, three runes inside
    const carve = rgba(hx(GOLD), 0.35 + 0.35 * o.dark);
    g.strokeStyle = carve; g.lineWidth = 2.6; g.lineCap = "round";
    g.beginPath(); g.moveTo(-14, -4); g.lineTo(-17, -56); g.quadraticCurveTo(-16, -82, 0, -88);
    g.quadraticCurveTo(16, -84, 17, -58); g.lineTo(14, -10); g.quadraticCurveTo(10, -2, 4, -8); g.stroke();
    g.lineWidth = 2;
    g.beginPath(); g.moveTo(-5, -70); g.lineTo(-5, -50); g.moveTo(-5, -70); g.lineTo(2, -64);        // ᚠ-ish strokes
    g.moveTo(-5, -63); g.lineTo(2, -57); g.moveTo(5, -44); g.lineTo(5, -24); g.moveTo(5, -44); g.lineTo(-2, -36);
    g.moveTo(-3, -32); g.lineTo(6, -26); g.stroke();
  }

  /** Finance: a cave in the mountain's face, a dragon's gold heaped inside, glinting. */
  function cave(g, o) {
    g.fillStyle = rgba(mix(0x030406, 0x14131a, o.light));
    g.beginPath(); g.moveTo(-64, 0); g.quadraticCurveTo(-62, -72, 0, -84); g.quadraticCurveTo(60, -74, 66, 0); g.closePath(); g.fill();
    g.strokeStyle = rgba(rock(o)); g.lineWidth = 7; g.lineJoin = "round";
    g.beginPath(); g.moveTo(-70, 3); g.quadraticCurveTo(-68, -78, 0, -91); g.quadraticCurveTo(66, -80, 72, 3); g.stroke();
    // warm light off the hoard
    glow(g, 0, -12, 70, 0.18 + 0.32 * o.dark, GOLD);
    const gold = mix(0x6b5320, 0xc8a040, 0.55 + 0.45 * Math.max(o.light, o.dark * 0.8));
    g.fillStyle = rgba(gold);
    g.beginPath(); g.moveTo(-50, 0); g.quadraticCurveTo(-36, -24, -12, -30); g.quadraticCurveTo(10, -36, 30, -22);
    g.quadraticCurveTo(44, -12, 52, 0); g.closePath(); g.fill();
    g.fillStyle = rgba(mix(0x8a6a28, 0xECD08F, 0.6));
    for (const [cx, cy] of [[-30, -8], [-14, -18], [4, -24], [20, -14], [34, -6], [-4, -6], [12, -4]]) {
      g.beginPath(); g.ellipse(cx, cy, 4.5, 2.2, 0, 0, 6.2832); g.fill();
    }
    // the dragon's tail curled over its hoard
    g.strokeStyle = rgba(mix(0x07080b, 0x1d1b22, o.light)); g.lineWidth = 7; g.lineCap = "round";
    g.beginPath(); g.moveTo(62, -6); g.quadraticCurveTo(40, -46, 6, -40); g.quadraticCurveTo(-18, -36, -20, -50); g.stroke();
    g.fillStyle = g.strokeStyle;
    for (const [sx, sy] of [[44, -32], [26, -42], [8, -44]]) { g.beginPath(); g.moveTo(sx - 4, sy); g.lineTo(sx, sy - 9); g.lineTo(sx + 4, sy); g.fill(); }
    // glints
    [[-22, -20, 0], [8, -30, 1.7], [28, -16, 3.1], [-38, -6, 4.4]].forEach(([x, y, ph]) => {
      const a = Math.max(0, Math.sin(o.t * 0.002 + ph)); if (a > 0.05) star(g, x, y, 5 * a + 1, 0.9 * a);
    });
  }

  /** Video: a skald by a little fire on the shore, his lyre on his knee. */
  function skald(g, o) {
    // a low hump of the ridge itself under him and his fire, so they sit on any ground
    g.fillStyle = rgba(mix(0x1a151f, 0x3b2f45, o.light));
    g.beginPath(); g.moveTo(-50, 16); g.quadraticCurveTo(-40, 1, -20, 0); g.lineTo(44, 0); g.quadraticCurveTo(60, 1, 68, 16); g.closePath(); g.fill();
    glow(g, 22, -10, 58, 0.25 + 0.45 * o.dark);
    g.fillStyle = rgba(rock(o));
    for (let k = -2; k <= 2; k++) { g.beginPath(); g.arc(22 + k * 6, 0, 3.4, 0, 6.2832); g.fill(); }
    flames(g, 22, -1, 5.5, 16, o.t);
    // the skald, hooded, seated facing the fire
    g.fillStyle = rgba(dark(o));
    g.beginPath(); g.moveTo(-26, 0); g.quadraticCurveTo(-30, -22, -20, -34); g.quadraticCurveTo(-12, -44, -6, -36);
    g.quadraticCurveTo(-2, -24, 2, -14); g.lineTo(6, 0); g.closePath(); g.fill();
    g.beginPath(); g.arc(-12, -40, 7, 0, 6.2832); g.fill();
    g.beginPath(); g.moveTo(-20, -42); g.quadraticCurveTo(-12, -54, -4, -42); g.closePath(); g.fill();   // hood
    // the lyre, firelit
    g.strokeStyle = rgba(hx(GOLD), 0.6 + 0.3 * o.dark); g.lineWidth = 2;
    g.beginPath(); g.moveTo(0, -12); g.quadraticCurveTo(-2, -30, 4, -32); g.moveTo(0, -12); g.quadraticCurveTo(12, -26, 10, -32);
    g.moveTo(3, -30); g.lineTo(10, -30); g.stroke();
    g.lineWidth = 0.8; g.beginPath(); for (const sx of [4, 6, 8]) { g.moveTo(sx, -29); g.lineTo(sx - 2, -14); } g.stroke();
  }

  /** Work: a smithy on a ledge of the slope, its forge glowing through the door, an anvil outside.
   *  While the printer works, sparks fly from its chimney. */
  function smithy(g, o) {
    g.fillStyle = rgba(rock(o));
    g.beginPath(); g.moveTo(-100, 2); g.lineTo(96, 2); g.lineTo(84, 16); g.quadraticCurveTo(0, 26, -88, 14); g.closePath(); g.fill();
    const wall = mix(0x141820, 0x5a5658, o.light), roof = mix(0x0b0e15, 0x3a3638, o.light);
    g.fillStyle = rgba(wall); g.fillRect(-52, -42, 104, 44);
    g.fillStyle = rgba(roof);
    g.beginPath(); g.moveTo(-66, -38); g.quadraticCurveTo(-36, -72, 0, -76); g.quadraticCurveTo(36, -72, 66, -38); g.closePath(); g.fill();
    // chimney of stone at the right end
    g.fillStyle = rgba(rock(o)); g.fillRect(30, -88, 14, 38);
    // the forge seen through the open door, breathing
    const heat = 0.7 + 0.3 * Math.sin(o.t * 0.004) * (o.forge ? 1.6 : 1);
    glow(g, -8, -16, 46, (0.25 + 0.45 * o.dark) * heat);
    g.fillStyle = rgba(hx(EMBER), 0.55 + 0.4 * heat * (0.5 + 0.5 * o.dark)); g.fillRect(-20, -32, 24, 34);
    g.fillStyle = rgba(hx(GOLD), 0.35 * heat); g.fillRect(-16, -12, 16, 10);
    // the anvil on its block, outside
    g.fillStyle = rgba(mix(0x07080b, 0x26262a, o.light));
    g.fillRect(-82, -10, 10, 12);
    g.beginPath(); g.moveTo(-92, -10); g.lineTo(-62, -10); g.quadraticCurveTo(-58, -15, -64, -18); g.lineTo(-90, -18); g.closePath(); g.fill();
    if (o.forge) for (let i = 0; i < 10; i++) {
      const life = 1600, age = ((o.t + i * 397) % life) / life;
      const sx = 37 + Math.sin(i * 2.3 + age * 5) * 10 + (i % 3 - 1) * age * 14, sy = -90 - age * 70;
      g.fillStyle = rgba(hx(i % 2 ? EMBER : GOLD), (1 - age) * 0.95); g.beginPath(); g.arc(sx, sy, (1.8 - age) * 1.4, 0, 6.2832); g.fill();
    }
  }

  /** Food: a cookfire on the shore with a cauldron hung from a tripod, steam rising. */
  function cookfire(g, o) {
    glow(g, 0, -10, 56, 0.25 + 0.45 * o.dark);
    g.fillStyle = rgba(rock(o));
    for (let k = -2; k <= 2; k++) { g.beginPath(); g.arc(k * 7, 0, 3.6, 0, 6.2832); g.fill(); }
    flames(g, 0, -1, 6, 14, o.t);
    g.strokeStyle = rgba(wood(o)); g.lineWidth = 3; g.lineCap = "round";
    g.beginPath(); g.moveTo(-30, 2); g.lineTo(0, -66); g.lineTo(30, 2); g.moveTo(8, 4); g.lineTo(0, -66); g.stroke();
    g.lineWidth = 1.5; g.beginPath(); g.moveTo(0, -66); g.lineTo(0, -44); g.stroke();
    g.fillStyle = rgba(mix(0x07080b, 0x2a2a2e, o.light));
    g.beginPath(); g.moveTo(-19, -44); g.lineTo(19, -44); g.quadraticCurveTo(21, -16, 0, -14); g.quadraticCurveTo(-21, -16, -19, -44); g.closePath(); g.fill();
    g.strokeStyle = rgba(mix(0x2a2a2e, 0x7a7670, o.light)); g.lineWidth = 2.5;
    g.beginPath(); g.moveTo(-21, -44); g.lineTo(21, -44); g.stroke();
    // steam
    for (let i = 0; i < 4; i++) {
      const life = 3200, age = ((o.t + i * 800) % life) / life;
      g.fillStyle = rgba(hx(0xE8ECF2), 0.22 * (1 - age));
      g.beginPath(); g.arc(Math.sin(age * 4 + i) * 6, -48 - age * 46, 4 + age * 9, 0, 6.2832); g.fill();
    }
  }

  /** Shop: a knarr, the broad-bellied trader, riding at anchor with bales on deck. */
  function knarrShape(g, o) {
    g.strokeStyle = rgba(dark(o)); g.lineWidth = 4; g.lineCap = "round";
    g.beginPath(); g.moveTo(0, -12); g.lineTo(0, -150); g.stroke();
    g.lineWidth = 5; g.beginPath(); g.moveTo(-62, -142); g.lineTo(62, -142); g.stroke();
    g.lineWidth = 1.6; g.beginPath(); g.moveTo(0, -150); g.lineTo(-112, -30); g.moveTo(0, -150); g.lineTo(112, -30); g.stroke();
    // the sail: frost and bone, furled half-way at anchor
    const sl = 0.55 + 0.45 * o.light;
    for (let i = 0; i < 6; i++) {
      g.fillStyle = rgba(mix(i % 2 ? BONE : FROST, 0x000000, 1 - sl));
      g.fillRect(-56 + i * 18.6, -139, 18.8, 70);
    }
    g.fillStyle = "rgba(0,0,0,0.25)"; g.fillRect(-56, -139, 112, 70);
    // bales on deck
    g.fillStyle = rgba(mix(0x2a2016, 0x8a6e4a, o.light));
    for (const [bx, bw] of [[-82, 26], [-54, 22], [48, 24], [74, 22]]) { g.beginPath(); g.roundRect(bx, -30, bw, 18, 5); g.fill(); }
    // the broad hull with its low stem and stern
    g.fillStyle = rgba(dark(o));
    g.beginPath(); g.moveTo(-118, -36); g.quadraticCurveTo(-112, -10, -96, -12); g.lineTo(96, -12); g.quadraticCurveTo(112, -10, 118, -36);
    g.quadraticCurveTo(124, -12, 104, 4); g.quadraticCurveTo(0, 18, -104, 4); g.quadraticCurveTo(-124, -12, -118, -36); g.closePath(); g.fill();
    g.strokeStyle = rgba(hx(GOLD), 0.25 + 0.2 * o.light); g.lineWidth = 1.6;
    g.beginPath(); g.moveTo(-98, -8); g.quadraticCurveTo(0, 2, 98, -8); g.stroke();
  }
  function knarr(g, o) {
    const bob = Math.sin(o.t * 0.0015) * 3, roll = Math.sin(o.t * 0.0011) * 0.012;
    g.save(); g.scale(1, -1); g.globalAlpha *= 0.28; g.translate(0, -bob); g.rotate(-roll); knarrShape(g, o); g.restore();
    g.save(); g.translate(0, bob); g.rotate(roll); knarrShape(g, o); g.restore();
    g.strokeStyle = rgba(hx(0xDDE6F5), 0.18); g.lineWidth = 1.5;
    g.beginPath(); g.moveTo(-120, 6); g.lineTo(-90, 6); g.moveTo(92, 6); g.lineTo(124, 6); g.stroke();
  }

  return { runestone, cave, skald, smithy, cookfire, knarr };
})();
if (typeof module !== "undefined") module.exports = Props;
