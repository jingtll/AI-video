import { existsSync, mkdirSync, readdirSync, readFileSync, writeFileSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { createHash } from 'node:crypto';
import { buildGroups, buildHtml } from '../scripts/captions_zh.mjs';

if (!process.argv[2]) throw new Error('需要空的测试目录参数');
const project = resolve(process.argv[2]);
if (existsSync(project) && readdirSync(project).length) throw new Error('测试目录必须为空，拒绝覆盖已有项目');
const localGsap = process.argv[3] ? readFileSync(resolve(process.argv[3])) : null;
mkdirSync(join(project, 'compositions'), { recursive: true });
const settings = {};
if (localGsap) {
  mkdirSync(join(project, 'assets/vendor'), { recursive: true });
  writeFileSync(join(project, 'assets/vendor/gsap.min.js'), localGsap);
  settings.gsap_src = 'assets/vendor/gsap.min.js';
  settings.gsap_integrity = 'sha384-' + createHash('sha384').update(localGsap).digest('base64');
  writeFileSync(join(project, 'ai-video.config.json'), JSON.stringify({ captions: { gsap_src: settings.gsap_src } }));
}
const manifest = { frames: [{ number: 1, durationSeconds: 2, voiceover: '缓存让读取更快。' }, { number: 2, durationSeconds: 2, voiceover: 'Vue 3也是例子。' }], globals: { format: '1080x1920' } };
const meta = { voices: [
  { frame: 1, duration_s: 2, words: [{ text: '缓存', start: 0.1, end: 0.4 }, { text: '让读取', start: 0.4, end: 0.9 }, { text: '更快。', start: 0.9, end: 1.5 }] },
  { frame: 2, duration_s: 2, words: [{ text: 'Vue', start: 0.1, end: 0.5 }, { text: '3', start: 0.5, end: 0.8 }, { text: '也是例子。', start: 0.8, end: 1.5 }] }
] };
writeFileSync(join(project, 'audio_meta.json'), JSON.stringify(meta));
writeFileSync(join(project, 'SCRIPT.md'), '## Line 1 — A (Frame 1)\n    缓存让读取更快。\n## Line 2 — B (Frame 2)\n    Vue 3也是例子。\n');
writeFileSync(join(project, 'STORYBOARD.md'), '---\nformat: 1080x1920\nmusic: none\n---\n## Frame 1 — A\n- duration: 2s\n- voiceover: 缓存让读取更快。\n## Frame 2 — B\n- duration: 2s\n- voiceover: Vue 3也是例子。\n');
const groups = buildGroups(manifest, meta);
writeFileSync(join(project, 'compositions/captions.html'), buildHtml(groups, 4, 1080, 1920, settings));
writeFileSync(join(project, 'caption_groups.json'), JSON.stringify({ groups }));
writeFileSync(join(project, 'hyperframes.json'), JSON.stringify({ name: 'ai-video-caption-smoke', width: 1080, height: 1920, fps: 30 }));
writeFileSync(join(project, 'index.html'), `<!doctype html><html><head><meta charset="utf-8"><style>html,body{margin:0}#main{position:relative;width:1080px;height:1920px;background:#203040}.clip{position:absolute;inset:0}#circle{position:absolute;left:340px;top:560px;width:400px;height:400px;border-radius:50%;background:#ffca69}</style></head><body><div id="main" data-composition-id="main" data-width="1080" data-height="1920" data-duration="4"><div id="circle"></div><div class="clip" data-composition-id="captions" data-composition-src="compositions/captions.html" data-width="1080" data-height="1920" data-start="0" data-duration="4" data-track-index="8"></div></div><script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js" integrity="sha384-sG0Hv1tP1lZCk9KQmrIbY/XNwi+OY84GQqhMscbnsoBFqAz8KNCil1kvfL3Hbbk2" crossorigin="anonymous"></script><script>var tl=gsap.timeline({paused:true});tl.to({},{duration:4},0);window.__timelines=window.__timelines||{};window.__timelines.main=tl;</script></body></html>`);
const entry = join(project, 'index.html');
let entryHtml = readFileSync(entry, 'utf8').replace('class="clip"', 'id="caption-track" data-track-kind="captions" class="clip"').replace('tl.to({},{duration:4},0)', 'tl.fromTo("#circle",{scale:0.9},{scale:1.1,duration:4,ease:"none"},0)');
if (localGsap) entryHtml = entryHtml.replace('https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js', settings.gsap_src).replace('sha384-sG0Hv1tP1lZCk9KQmrIbY/XNwi+OY84GQqhMscbnsoBFqAz8KNCil1kvfL3Hbbk2', settings.gsap_integrity);
writeFileSync(entry, entryHtml);
console.log('Caption smoke project: ' + project);
