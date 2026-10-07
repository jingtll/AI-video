import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

let adapter;
try { adapter = await import('../scripts/captions_zh.mjs'); } catch {}
test('中文字幕适配入口可加载', () => assert.ok(adapter, '尚未提供中文字幕适配器'));

const manifest = { frames: [{ number: 1, durationSeconds: 4, voiceover: '缓存让读取更快。' }], globals: { format: '1080x1920' } };
const word = (text, start, end) => ({ text, start, end });
const meta = (words) => ({ voices: [{ frame: 1, duration_s: 4, words }] });
if (adapter) {
  test('默认字幕区域水平居中且无底色', () => {
    const html = adapter.buildHtml([], 4, 1080, 1920);
    assert.match(html, /left:151px;top:1382px;width:778px/);
    assert.match(html, /background:transparent/);
    assert.match(html, /text-align:center/);
  });
  test('浅色视频使用深色字幕，自定义宽度仍居中', () => {
    const html = adapter.buildHtml([], 4, 1080, 1920, { theme: 'light', width: 800 });
    assert.match(html, /left:140px/);
    assert.match(html, /color:#17212b/);
    assert.match(html, /text-shadow:none/);
  });
  test('支持淡色底和明确的样式覆盖', () => {
    const html = adapter.buildHtml([], 4, 1080, 1920, { theme: 'light', color: '#123456', background: 'rgba(255,255,255,.16)', left: 100 });
    assert.match(html, /left:100px/);
    assert.match(html, /color:#123456/);
    assert.ok(html.includes('background:rgba(255,255,255,.16)'));
    assert.throws(() => adapter.buildHtml([], 4, 1080, 1920, { theme: 'invalid' }));
  });
  test('中文不插入空格，句号结束当前字幕组', () => {
    const groups = adapter.buildGroups(manifest, meta([word('缓存', 0.1, 0.4), word('更快。', 0.4, 0.8), word('第二句', 0.8, 1.3)]));
    assert.deepEqual(groups.map(g => g.text), ['缓存更快。', '第二句']);
  });
  test('拉丁单词保留词间空格和原有数值', () => {
    const groups = adapter.buildGroups(manifest, meta([word('Vue', 0.1, 0.4), word('3', 0.4, 0.8), word('版本1.5。', 0.8, 1.3)]));
    assert.equal(groups[0].text, 'Vue 3版本1.5。');
  });
  test('字幕按照行宽预算切组，而非只按词数', () => {
    const groups = adapter.buildGroups(manifest, meta([word('第一块文字', 0.1, 0.6), word('第二块文字', 0.6, 1.1), word('第三块文字', 1.1, 1.6)]), { max_units_per_line: 6, max_lines: 1 });
    assert.deepEqual(groups.map(g => g.text), ['第一块文字', '第二块文字', '第三块文字']);
  });
  test('末组字幕不会跨入下一镜头', () => {
    const board = { frames: [{ number: 1, durationSeconds: 1, voiceover: '第一句' }, { number: 2, durationSeconds: 1, voiceover: '第二句' }] };
    const groups = adapter.buildGroups(board, { voices: [{ frame: 1, audio_duration_s: 1, words: [word('第一句', 0.1, 0.98)] }, { frame: 2, audio_duration_s: 1, words: [word('第二句', 0.1, 0.9)] }] });
    assert.equal(groups[0].end, 1);
    assert.equal(groups[1].start, 1.1);
  });
  test('空词级时间戳会阻止字幕组装', () => assert.throws(() => adapter.buildGroups(manifest, meta([]))));
  test('重复音频镜头会阻止字幕组装', () => {
    const voice = { frame: 1, words: [word('缓存', 0.1, 0.8)] };
    assert.throws(() => adapter.buildGroups(manifest, { voices: [voice, voice] }));
  });
  test('过长的单个时间戳词条要求重新对齐', () => assert.throws(() => adapter.buildGroups(manifest, meta([word('这是一条超过单行预算的长句', 0.1, 0.8)]), { max_units_per_line: 4, max_lines: 1 })));
  test('实际字体测量会识别两行装不下的字幕', () => {
    const result = adapter.layoutLines(['甲', '乙', '丙'].map(text => ({ text })), text => text.length * 64, 100, 2);
    assert.equal(result.overflow, true);
    assert.equal(result.lines.length, 3);
  });
  test('实际字体测量会优先在词条之间换行', () => {
    const result = adapter.layoutLines([{ text: '缓存' }, { text: '更快' }], text => text.length * 64, 160, 2);
    assert.equal(result.overflow, false);
    assert.deepEqual(result.lines.map(row => row.map(w => w.text)), [['缓存'], ['更快']]);
  });
  test('本地运行依赖不允许逃逸项目或注入 HTML', () => {
    const groups = adapter.buildGroups(manifest, meta([word('缓存', 0.1, 0.8)]));
    assert.throws(() => adapter.buildHtml(groups, 4, 1080, 1920, { gsap_src: '../outside.js' }));
    assert.throws(() => adapter.buildHtml(groups, 4, 1080, 1920, { gsap_src: 'assets/a" onload="x.js' }));
  });
  test('字幕时间戳不能落在实际音频结束之后', () => {
    assert.throws(() => adapter.buildGroups(manifest, { voices: [{ frame: 1, audio_duration_s: 1, duration_s: 1.5, words: [word('缓存', 3, 3.5)] }] }));
  });
  test('缺失音频时长不能静默通过', () => {
    assert.throws(() => adapter.buildGroups(manifest, { voices: [{ frame: 1, words: [word('缓存', 0.1, 0.8)] }] }));
  });
  test('运行样例不会覆盖已有项目', () => {
    const project = mkdtempSync(join(tmpdir(), 'ai-video-preserve-'));
    try {
      writeFileSync(join(project, 'SCRIPT.md'), 'KEEP ME');
      const result = spawnSync(process.execPath, [fileURLToPath(new URL('./create_smoke.mjs', import.meta.url)), project]);
      assert.notEqual(result.status, 0);
      assert.equal(readFileSync(join(project, 'SCRIPT.md'), 'utf8'), 'KEEP ME');
    } finally { rmSync(project, { recursive: true, force: true }); }
  });
}
