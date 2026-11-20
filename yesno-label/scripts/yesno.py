#!/usr/bin/env python3
"""One-card-at-a-time yes/no video labelling.

  ./yesno.py "Is this slow motion?" clips/*.mp4 [--out labels.jsonl] [--port 8765]
  ./yesno.py "Which crop is better?" pairs/*.mp4 --choices "Model A,Model B,Neither"

Videos are local paths or http(s) URLs. Answers append to --out (last answer per
video wins), and labelled videos are skipped on restart.
--choices is left,right,middle (default no,yes,unsure); the answer stored is the choice text.
Keys: → or y = right, ← or n = left, ↓ or u = middle, backspace = back, space = 0.25x/1x,
c on the summary = copy the answers as JSONL (one line per video, last answer wins).
"""
import argparse, json, os, time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

PAGE = """<!doctype html>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>yes/no</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link href="https://fonts.googleapis.com/css2?family=Geist:wght@400;500;600;700&family=Geist+Mono&display=swap" rel="stylesheet">
<style>
/* shadcn/ui zinc dark tokens */
:root{--background:240 10% 3.9%;--foreground:0 0% 98%;--card:240 10% 3.9%;--muted:240 3.7% 15.9%;--muted-foreground:240 5% 64.9%;
--border:240 3.7% 15.9%;--primary:0 0% 98%;--primary-foreground:240 5.9% 10%;--destructive:0 72% 51%;--success:142 71% 45%;--ring:240 4.9% 83.9%;--radius:.5rem}
*{box-sizing:border-box}
body{font:14px/1.5 Geist,ui-sans-serif,system-ui,sans-serif;margin:0;background:hsl(var(--background));color:hsl(var(--foreground));height:100vh;display:flex;flex-direction:column;align-items:center;-webkit-font-smoothing:antialiased}
header{width:100%;max-width:1000px;padding:1.25rem 1.5rem .75rem}
h1{font-size:1.5rem;font-weight:600;letter-spacing:-.025em;margin:0}
#meta{color:hsl(var(--muted-foreground));font-size:.875rem;margin:.25rem 0 .75rem;display:flex;gap:.5rem;align-items:center;flex-wrap:wrap;word-break:break-all}
.progress{height:.5rem;border-radius:9999px;background:hsl(var(--muted));overflow:hidden}
.progress>div{height:100%;background:hsl(var(--primary));transition:width .3s}
.card{border:1px solid hsl(var(--border));border-radius:calc(var(--radius) + 4px);background:hsl(var(--card));box-shadow:0 1px 3px rgb(0 0 0/.3)}
#card{flex:1;min-height:0;width:calc(100% - 3rem);max-width:952px;display:flex;justify-content:center;align-items:center;padding:.75rem;transition:transform .15s,opacity .15s}
video{max-width:100%;max-height:100%;border-radius:var(--radius);background:#000}
#bar{display:flex;gap:.75rem;padding:1rem}
.btn{display:inline-flex;align-items:center;justify-content:center;gap:.5rem;height:2.75rem;padding:0 2rem;border-radius:var(--radius);font:500 .95rem Geist,system-ui,sans-serif;cursor:pointer;border:1px solid transparent;transition:background .15s,box-shadow .15s}
.btn:focus-visible{outline:none;box-shadow:0 0 0 2px hsl(var(--background)),0 0 0 4px hsl(var(--ring))}
#no{background:hsl(var(--destructive));color:#fff}#no:hover{background:hsl(var(--destructive)/.9)}
#yes{background:hsl(var(--success));color:#fff}#yes:hover{background:hsl(var(--success)/.9)}
#un{background:transparent;border-color:hsl(var(--border));color:hsl(var(--foreground))}#un:hover{background:hsl(var(--muted))}
kbd{font:500 .7rem "Geist Mono",ui-monospace,monospace;padding:.1rem .35rem;border-radius:.25rem;border:1px solid hsl(var(--border));background:hsl(var(--muted));color:hsl(var(--muted-foreground))}
.btn kbd{background:rgb(255 255 255/.15);border-color:transparent;color:inherit}
#help{color:hsl(var(--muted-foreground));font-size:.75rem;padding-bottom:1rem;display:flex;gap:1rem;flex-wrap:wrap;justify-content:center}
.badge{display:inline-flex;align-items:center;gap:.25rem;border-radius:9999px;padding:.05rem .6rem;font-size:.75rem;font-weight:600;border:1px solid transparent}
.badge.yes{background:hsl(var(--success)/.15);color:hsl(var(--success));border-color:hsl(var(--success)/.3)}
.badge.no{background:hsl(var(--destructive)/.15);color:hsl(0 84% 70%);border-color:hsl(var(--destructive)/.3)}
.badge.unsure,.badge.none{background:hsl(var(--muted));color:hsl(var(--muted-foreground))}
#done{display:none;flex:1;min-height:0;overflow:auto;width:100%;max-width:1000px;padding:0 1.5rem 2rem}
#done h2{font-size:1.875rem;font-weight:700;letter-spacing:-.025em;margin:.5rem 0 .25rem}
#done .sub{color:hsl(var(--muted-foreground));margin-bottom:1.25rem}
#done code{font-family:"Geist Mono",monospace;font-size:.8rem;background:hsl(var(--muted));padding:.1rem .35rem;border-radius:.25rem;color:hsl(var(--foreground))}
.stats{display:grid;grid-template-columns:repeat(3,1fr);gap:1rem;margin-bottom:1.5rem}
.stat{padding:1.25rem}
.stat .l{font-size:.875rem;font-weight:500;color:hsl(var(--muted-foreground));display:flex;justify-content:space-between}
.stat b{display:block;font-size:2rem;font-weight:700;letter-spacing:-.025em}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(170px,1fr));gap:1rem}
.tile{cursor:pointer;overflow:hidden;transition:border-color .15s}
.tile:hover{border-color:hsl(var(--ring))}
.tile video{width:100%;aspect-ratio:16/9;object-fit:cover;display:block;border-radius:0}
.tile div{padding:.5rem .75rem;font-size:.8rem;display:flex;justify-content:space-between;align-items:center;gap:.5rem}
.tile span{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-family:"Geist Mono",monospace;color:hsl(var(--muted-foreground))}
.tile span.badge{flex-shrink:0;overflow:visible}
/* watermelon feel: drag to swipe, spring motion */
.card{border-width:1.6px;border-color:rgb(39 39 42);background:rgb(24 24 27)}
#card{position:relative;padding:1.25rem;cursor:grab;touch-action:pan-y;user-select:none;transition:none;will-change:transform}
#card.spring{transition:transform .5s cubic-bezier(.34,1.56,.64,1),opacity .3s}
#card.fly{transition:transform .35s cubic-bezier(.4,0,1,1),opacity .35s}
#card:active{cursor:grabbing}
#card video{pointer-events:none}
#prog{position:absolute;left:1.25rem;right:1.25rem;bottom:.5rem;height:4px;border-radius:2px;background:hsl(var(--muted));pointer-events:none}
#prog i{display:block;height:100%;width:0;border-radius:inherit;background:hsl(var(--foreground))}
.side{position:absolute;top:.6rem;z-index:1;pointer-events:none;font:600 .8rem Geist,sans-serif;padding:.15rem .6rem;border-radius:calc(var(--radius) - 2px);background:rgb(0 0 0/.65);border:1px solid hsl(var(--border));display:none}
#sideL{left:1.25rem}#sideR{right:1.25rem}
body.ab .side{display:block}
body.ab .tile video{object-fit:contain;background:#000}
#toast{position:fixed;left:50%;bottom:2rem;transform:translate(-50%,1rem) scale(.95);opacity:0;pointer-events:none;padding:.75rem 1.25rem;border-radius:var(--radius);font:600 1rem Geist,sans-serif;background:hsl(var(--success));color:#fff;box-shadow:0 10px 30px rgb(0 0 0/.5);transition:transform .4s cubic-bezier(.34,1.56,.64,1),opacity .2s}
#toast.show{opacity:1;transform:translate(-50%,0) scale(1)}
#toast.err{background:hsl(var(--destructive))}
@keyframes copied{0%{background:hsl(var(--success)/.3);color:hsl(var(--success));box-shadow:0 0 0 3px hsl(var(--success)/.2)}}
#path.copied{animation:copied 1.4s ease-out}
body.ab #no,body.ab #yes{background:hsl(var(--muted));color:hsl(var(--foreground));border-color:hsl(var(--ring)/.35)}
body.ab #no:hover,body.ab #yes:hover{background:hsl(var(--muted)/.7)}
body.ab .badge.yes,body.ab .badge.no{background:hsl(var(--foreground)/.1);color:hsl(var(--foreground));border-color:hsl(var(--foreground)/.25)}
#tint{position:absolute;inset:0;border-radius:inherit;pointer-events:none;opacity:0;display:flex;align-items:center;justify-content:center;font:700 4rem Geist,sans-serif}
.btn{height:3rem;padding:0 2.25rem;transition:transform .2s cubic-bezier(.34,1.56,.64,1),background .15s}
.btn:hover{transform:scale(1.04)}.btn:active{transform:scale(.96)}
.badge{border-radius:calc(var(--radius) - 2px)}
.tile{transition:transform .25s cubic-bezier(.34,1.56,.64,1),border-color .15s}
.tile:hover{transform:translateY(-3px) scale(1.02)}
.progress>div{transition:width .6s cubic-bezier(.34,1.56,.64,1)}
</style>
<header><h1 id="q"></h1><div id="meta"></div><div class="progress"><div id="pb" style="width:0"></div></div></header>
<div id="card" class="card"><span class="side" id="sideL"></span><span class="side" id="sideR"></span><video id="v" autoplay loop muted playsinline></video><div id="tint"></div><div id="prog"><i></i></div></div>
<div id="done"></div><div id="toast"></div>
<div id="bar"><button class="btn" id="no"></button><button class="btn" id="un"></button><button class="btn" id="yes"></button></div>
<div id="help"><span><kbd>⌫</kbd> back</span><span><kbd>space</kbd> 0.25x / 1x</span><span>or drag the card</span></div>
<script>
let items, OUT, labels = {}, i = 0, rate = 1;
let L, R, M, CLS, MARK, yn;  // choices: left, right, middle
const $ = id => document.getElementById(id), v = $("v");
const cap = s => s[0].toUpperCase() + s.slice(1);
async function init() {
  const d = await (await fetch("data")).json();
  items = d.items; OUT = d.out; $("q").textContent = d.question;
  [L, R, M] = d.choices;
  CLS = {[L]: "no", [R]: "yes", [M]: "unsure"};
  yn = L === "no" && R === "yes";
  document.body.classList.toggle("ab", !yn);
  $("sideL").textContent = `← ${L}`; $("sideR").textContent = `${R} →`;
  MARK = {[L]: yn ? "✗" : "←", [R]: yn ? "✓" : "→", [M]: yn ? "?" : "↓"};
  $("no").innerHTML = `${yn ? "✗ " : ""}${esc(cap(L))} <kbd>←</kbd>`;
  $("un").innerHTML = `${esc(cap(M))} <kbd>↓</kbd>`;
  $("yes").innerHTML = `${yn ? "✓ " : ""}${esc(cap(R))} <kbd>→</kbd>`;
  for (const l of d.labels) labels[l.video] = l.answer;
  i = items.findIndex(it => !(it.video in labels));
  if (i < 0) i = items.length;
  render();
}
function render() {
  const done = items.filter(it => it.video in labels).length;
  const fin = i >= items.length;
  for (const id of ["card", "bar", "help"]) $(id).style.display = fin ? "none" : "";
  $("done").style.display = fin ? "block" : "none";
  $("pb").style.width = `${100 * done / items.length}%`;
  if (fin) { v.removeAttribute("src"); v.load(); $("meta").textContent = ""; return showDone(); }
  const it = items[i], prev = labels[it.video];
  $("meta").innerHTML = `<span>${i + 1} of ${items.length} · ${done} answered</span><span class="badge none">${esc(it.video.split("/").pop())}</span>` + (prev ? `<span class="badge ${CLS[prev] || "none"}">saved: ${esc(prev)}</span>` : "");
  v.src = it.src; v.playbackRate = rate;
}
const esc = s => s.replace(/[&<>"]/g, c => `&#${c.charCodeAt(0)};`);
function showDone() {
  const n = {[L]: 0, [R]: 0, [M]: 0};
  for (const it of items) if (labels[it.video] in n) n[labels[it.video]]++;
  const left = items.length - n[L] - n[R] - n[M];
  $("done").innerHTML = `
    <h2>${left ? `${left} left` : "All done 🎉"}</h2>
    <div class="sub">${items.length} clips · saved to <code id="path">${esc(OUT)}</code> · click a clip to change its answer · <span id="copy" style="cursor:pointer"><kbd>c</kbd> copy JSONL</span></div>
    <div class="stats">${(yn ? [R, L, M] : [L, R, M]).map(k => `<div class="card stat"><div class="l">${esc(cap(k))}<span class="badge ${CLS[k]}">${MARK[k]}</span></div><b>${n[k]}</b></div>`).join("")}</div>
    <div class="grid">${items.map((it, k) => {
      const a = labels[it.video];
      return `<div class="card tile" data-k="${k}"><video src="${esc(it.src)}#t=0.5" muted preload="metadata"></video>
        <div><span>${esc(it.video.split("/").pop())}</span><span class="badge ${CLS[a] || "none"}">${a ? (MARK[a] || "") + " " + esc(a) : "unanswered"}</span></div></div>`;
    }).join("")}</div>`;
  $("copy").onclick = copy;
  $("done").querySelectorAll(".tile").forEach(t => t.onclick = () => { i = +t.dataset.k; render(); });
}
async function copy() {
  const last = {};  // the file is append-only; keep the last answer per video
  for (const l of (await (await fetch("data")).json()).labels) last[l.video] = l;
  const rows = Object.values(last), text = rows.map(l => JSON.stringify(l)).join("\\n") + "\\n";
  try { await navigator.clipboard.writeText(text); }
  catch (err) {  // the clipboard API needs https or localhost; fall back to the old copy command
    const t = document.createElement("textarea"); t.value = text; document.body.append(t); t.select();
    const ok = document.execCommand("copy"); t.remove();
    if (!ok) return toast(`Copy failed: ${err.message}`, true);
  }
  const pth = $("path"); pth.classList.remove("copied"); void pth.offsetWidth; pth.classList.add("copied");  // restart the pulse
}
let toastT;
function toast(msg, err) {
  const t = $("toast"); t.textContent = msg; t.className = err ? "show err" : "show";
  clearTimeout(toastT); toastT = setTimeout(() => t.className = err ? "err" : "", 2500);
}
async function answer(a) {
  if (i >= items.length) return;
  const video = items[i].video;
  const r = await fetch("label", {method: "POST", body: JSON.stringify({video, answer: a})});
  if (!r.ok) return alert("Save failed: " + r.status);
  labels[video] = a;
  const c = $("card"), dir = a === R ? 1 : a === L ? -1 : 0;
  c.className = "card fly";
  c.style.transform = dir ? `translateX(${dir * 120}vw) rotate(${dir * 18}deg)` : "translateY(60vh) scale(.9)";
  c.style.opacity = 0; tint(dir * 200);
  setTimeout(() => {
    c.className = "card"; c.style.transform = "scale(.92)"; tint(0); i++; render();
    requestAnimationFrame(() => requestAnimationFrame(() => { c.className = "card spring"; c.style.transform = ""; c.style.opacity = 1; }));
  }, 350);
}
$("yes").onclick = () => answer(R); $("no").onclick = () => answer(L); $("un").onclick = () => answer(M);
document.addEventListener("keydown", e => {
  const a = {ArrowRight: R, y: R, ArrowLeft: L, n: L, ArrowDown: M, u: M}[e.key];
  if (i >= items.length && e.key.toLowerCase() === "c" && !e.metaKey && !e.ctrlKey) { e.preventDefault(); copy(); }
  else if (a) { e.preventDefault(); answer(a); }
  else if (e.key === "Backspace" && i > 0) { e.preventDefault(); i--; render(); }
  else if (e.key === " ") { e.preventDefault(); rate = rate === 1 ? 0.25 : 1; v.playbackRate = rate; }
});
function tint(dx) {
  const t = $("tint"), k = Math.min(Math.abs(dx) / 150, 1);
  t.style.opacity = k;
  if (!yn) {  // neutral: name the side being chosen instead of colouring it good or bad
    t.textContent = dx > 0 ? R : L; t.style.background = `hsl(var(--foreground)/${.12 * k})`; t.style.color = "hsl(var(--foreground))"; return;
  }
  t.textContent = dx > 0 ? MARK[R] : MARK[L];
  t.style.background = dx > 0 ? `hsl(var(--success)/${.25 * k})` : `hsl(var(--destructive)/${.25 * k})`;
  t.style.color = dx > 0 ? "hsl(var(--success))" : "hsl(0 84% 70%)";
}
// playback progress, so it is clear when a looping video has been seen once
(function tick() { const v = $("v"); $("prog").firstChild.style.width = v.duration ? `${100 * v.currentTime / v.duration}%` : "0"; requestAnimationFrame(tick); })();
let x0 = null;  // drag to swipe, mouse or touch
const card = $("card");
card.addEventListener("pointerdown", e => { if (i >= items.length) return; x0 = e.clientX; card.className = "card"; card.setPointerCapture(e.pointerId); });
card.addEventListener("pointermove", e => {
  if (x0 === null) return;
  const dx = e.clientX - x0;
  card.style.transform = `translateX(${dx}px) rotate(${dx / 25}deg)`; tint(dx);
});
const release = e => {
  if (x0 === null) return;
  const dx = e.clientX - x0; x0 = null;
  if (Math.abs(dx) > 100) return answer(dx > 0 ? R : L);
  card.className = "card spring"; card.style.transform = ""; tint(0);
};
card.addEventListener("pointerup", release); card.addEventListener("pointercancel", release);
init();
</script>
"""


def main():
    p = argparse.ArgumentParser()
    p.add_argument("question")
    p.add_argument("videos", nargs="+")
    p.add_argument("--out", default="labels.jsonl")
    p.add_argument("--port", type=int, default=8765)
    p.add_argument("--choices", default="no,yes,unsure", help="left,right,middle")
    a = p.parse_args()
    choices = [c.strip() for c in a.choices.split(",")]
    if len(choices) != 3 or len(set(choices)) != 3 or not all(choices):
        p.error("--choices needs three distinct names: left,right,middle")
    videos = a.videos
    items = [{"video": x, "src": x if x.startswith(("http://", "https://")) else f"/v/{n}"} for n, x in enumerate(videos)]

    class H(SimpleHTTPRequestHandler):
        def do_GET(self):
            if self.path == "/":
                return self.send(200, "text/html", PAGE.encode())
            if self.path == "/data":
                labels = [json.loads(l) for l in open(a.out)] if os.path.exists(a.out) else []
                return self.send(200, "application/json", json.dumps({"question": a.question, "out": os.path.abspath(a.out), "items": items, "labels": labels, "choices": choices}).encode())
            if not self.path.startswith("/v/"):
                return self.send_error(404)
            n = self.path[3:]
            if not n.isdigit() or int(n) >= len(videos) or not os.path.isfile(videos[int(n)]):
                return self.send_error(404)
            path = videos[int(n)]
            size = os.path.getsize(path)
            start, end = 0, size - 1
            rng = self.headers.get("Range")  # Safari won't play video without byte ranges
            if rng:
                s, e = rng.removeprefix("bytes=").split(",")[0].split("-")
                start, end = (size - int(e), size - 1) if not s else (int(s), min(int(e) if e else size - 1, size - 1))
            self.send_response(206 if rng else 200)
            self.send_header("Content-Type", "video/mp4"); self.send_header("Accept-Ranges", "bytes")
            if rng:
                self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
            self.send_header("Content-Length", str(end - start + 1)); self.end_headers()
            with open(path, "rb") as f:
                f.seek(start)
                left = end - start + 1
                while left > 0 and (chunk := f.read(min(left, 1 << 20))):
                    self.wfile.write(chunk); left -= len(chunk)

        def do_POST(self):
            r = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            if r.get("answer") not in choices or r.get("video") not in videos:
                return self.send_error(400)
            with open(a.out, "a") as f:
                print(json.dumps({"video": r["video"], "answer": r["answer"], "question": a.question, "ts": time.time()}), file=f)
            self.send_response(204); self.end_headers()

        def send(self, code, ctype, body):
            self.send_response(code); self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)

    print(f"http://127.0.0.1:{a.port}  ({len(videos)} videos, answers -> {a.out})")
    ThreadingHTTPServer(("127.0.0.1", a.port), H).serve_forever()


if __name__ == "__main__":
    main()
