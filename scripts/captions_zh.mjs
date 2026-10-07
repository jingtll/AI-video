#!/usr/bin/env node
// Chinese caption adapter. Upstream storyboard parsing remains authoritative.
import { existsSync, mkdirSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { dirname, join, relative, resolve } from "node:path";
import { createHash } from "node:crypto";
import { fileURLToPath, pathToFileURL } from "node:url";

const CJK = /[\p{Script=Han}\p{Script=Hiragana}\p{Script=Katakana}\p{Script=Hangul}]/u;
const END = /[。！？!?；;，,：:]$/u;
const PUNCT = /^[\p{P}\p{S}]+$/u;
const round = n => Number(n.toFixed(3));

export function joiner(previous, current) {
  if (!previous || PUNCT.test(current) || /[（(《“‘]$/u.test(previous)) return "";
  return /[A-Za-z0-9]$/u.test(previous) && /^[A-Za-z0-9]/u.test(current) ? " " : "";
}
export function joined(words) {
  return words.map((w, i) => joiner(words[i - 1]?.text, w.text) + w.text).join("");
}
function units(text) {
  return [...text].reduce((sum, char) => sum + (CJK.test(char) || char.codePointAt(0) > 255 ? 1 : /\s/u.test(char) ? 0.35 : 0.75), 0);
}
function positive(value, name) {
  if (!Number.isFinite(value) || value <= 0) throw new Error(name + " 必须是有限正数");
  return value;
}

// Shared with browser-side actual-font layout. Word timestamps are never invented.
export function layoutLines(words, measure, width, maxLines) {
  const lines = [[]];
  let tooWide = false;
  for (const word of words) {
    if (measure(word.text) > width) tooWide = true;
    const line = lines.at(-1);
    if (line.length && measure(joined([...line, word])) > width) lines.push([]);
    lines.at(-1).push(word);
  }
  return { lines, overflow: tooWide || lines.length > maxLines };
}

export function buildGroups(manifest, meta, options = {}) {
  const lineUnits = positive(options.max_units_per_line ?? 12, "max_units_per_line");
  const maxLines = positive(options.max_lines ?? 2, "max_lines");
  const maxDuration = positive(options.max_duration ?? 3, "max_duration");
  const minDuration = positive(options.min_duration ?? 0.18, "min_duration");
  if (!Number.isInteger(maxLines)) throw new Error("max_lines 必须是整数");
  const frames = new Map();
  let total = 0;
  for (const frame of manifest.frames ?? []) {
    if (!Number.isInteger(frame.number) || frame.number < 1 || frames.has(frame.number)) throw new Error("分镜编号无效或重复");
    const duration = positive(frame.durationSeconds, "镜头时长");
    frames.set(frame.number, { ...frame, start: total, end: total + duration });
    total += duration;
  }
  if (!frames.size || !Array.isArray(meta.voices) || !meta.voices.length) throw new Error("有口播的项目缺少分镜或 voices");
  const seen = new Set(), words = [];
  for (const voice of meta.voices) {
    const frame = frames.get(voice.frame);
    if (!frame || seen.has(voice.frame)) throw new Error("音频镜头重复或不在分镜中");
    seen.add(voice.frame);
    const audioDuration = positive(voice.audio_duration_s ?? voice.duration_s - (voice.tail_pad_s ?? 0.5), "音频时长");
    if (audioDuration > frame.durationSeconds + 0.08) throw new Error("Frame " + voice.frame + ": 音频超出镜头，先同步时长");
    if (!Array.isArray(voice.words) || !voice.words.length) throw new Error("Frame " + voice.frame + ": 无词级时间戳");
    let previousEnd = 0;
    for (const word of voice.words) {
      if (typeof word.text !== "string" || !word.text.trim() || !Number.isFinite(word.start) || !Number.isFinite(word.end)
          || word.start < 0 || word.end <= word.start || word.start < previousEnd - 0.03
          || word.end > audioDuration + 0.03
          || frame.start + word.end > frame.end + 0.001) throw new Error("Frame " + voice.frame + ": 词条或时间戳无效");
      previousEnd = word.end;
      words.push({ text: word.text.trim(), start: round(frame.start + word.start), end: round(frame.start + word.end),
                   frame: voice.frame, frameEnd: frame.end });
    }
  }
  for (const frame of frames.values()) {
    const spoken = String(frame.voiceover ?? "").trim();
    if (spoken && !/^(none|null|~|-)$/i.test(spoken) && !seen.has(frame.number)) throw new Error("Frame " + frame.number + ": 缺少旁白");
  }
  words.sort((a, b) => a.start - b.start);
  const groups = [];
  let current = [];
  function flush() {
    if (current.length) groups.push(current);
    current = [];
  }
  for (const word of words) {
    if (units(word.text) > lineUnits || word.end - word.start > maxDuration) {
      throw new Error("Frame " + word.frame + ": 单个词条过长；检查 WordBoundary 或调整字幕预算");
    }
    const previous = current.at(-1);
    const next = [...current, word];
    if (previous && (word.frame !== previous.frame || word.start - previous.end > 0.18
        || word.end - current[0].start > maxDuration
        || layoutLines(next, units, lineUnits, maxLines).overflow)) flush();
    current.push(word);
    if (END.test(word.text) || /(?<!\d)\.$/u.test(word.text)) flush();
  }
  flush();
  return groups.map((group, i) => {
    const start = group[0].start, last = group.at(-1);
    const nextStart = groups[i + 1]?.[0].start ?? total;
    const end = round(Math.min(last.end + 0.12, last.frameEnd, nextStart, total));
    if (end - start < minDuration) throw new Error("Frame " + last.frame + ": 字幕显示时间过短，请合并口播节拍");
    return { id: "caption-group-" + i, frame: last.frame, start, end, text: joined(group),
             words: group.map((word, wi) => ({ id: "caption-word-" + i + "-" + wi,
               text: word.text, start: word.start, end: word.end, joiner: joiner(group[wi - 1]?.text, word.text) })) };
  });
}

export function buildHtml(groups, total, width, height, settings = {}) {
  const fontSize = positive(settings.font_size ?? Math.round(height * 0.0333), "font_size");
  const top = settings.top ?? Math.round(height * 0.72);
  const boxWidth = positive(settings.width ?? Math.round(width * 0.72), "caption width");
  const left = settings.left ?? Math.round((width - boxWidth) / 2);
  const maxLines = positive(settings.max_lines ?? 2, "max_lines");
  const lineHeight = positive(settings.line_height ?? 1.3, "line_height");
  if (!Number.isFinite(left) || !Number.isFinite(top) || left < 0 || top < 0
      || left + boxWidth > width || top + fontSize * lineHeight * maxLines + 32 > height) throw new Error("字幕区域超出画布");
  const family = settings.font_family ?? "Microsoft YaHei";
  if (!/^[\p{L}\p{N} _-]+$/u.test(family)) throw new Error("font_family 必须是单个字体族名称");
  const cssColor = /^(#[0-9a-fA-F]{3,8}|rgba?\(\s*[0-9.,\s]+\)|none|transparent)$/u;
  const theme = settings.theme ?? "dark";
  if (!["dark", "light"].includes(theme)) throw new Error("theme 必须为 dark 或 light");
  const color = settings.color ?? (theme === "light" ? "#17212b" : "#fff");
  const background = settings.background ?? "transparent";
  const textShadow = theme === "light" ? "none" : "0 2px 6px rgba(0,0,0,.4)";
  if (!cssColor.test(color)) throw new Error("color 必须是 CSS 颜色值");
  if (!cssColor.test(background)) throw new Error("background 必须是 CSS 颜色值或 none/transparent");
  const gsapSrc = settings.gsap_src ?? "https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js";
  const defaultIntegrity = "sha384-sG0Hv1tP1lZCk9KQmrIbY/XNwi+OY84GQqhMscbnsoBFqAz8KNCil1kvfL3Hbbk2";
  if (settings.gsap_src && (!/^[A-Za-z0-9_./-]+$/.test(gsapSrc) || gsapSrc.startsWith("/") || gsapSrc.split("/").includes("..")))
    throw new Error("gsap_src 必须是项目内相对路径");
  const integrity = settings.gsap_integrity ?? defaultIntegrity;
  if (!/^sha384-[A-Za-z0-9+/=]+$/.test(integrity)) throw new Error("GSAP 完整性哈希无效");
  const data = JSON.stringify(groups).replace(/</g, "\\u003c");
  return '<template id="captions-template" data-composition-id="captions" data-width="' + width + '" data-height="' + height + '" data-duration="' + total + '">\n'
    + '<div id="captions-root" data-composition-id="captions" data-width="' + width + '" data-height="' + height + '" data-duration="' + total + '"><div id="ai-caption-band"></div></div>\n'
    + '<style>\n@font-face{font-family:"AI Video CJK";src:local("' + family + '"),local("Noto Sans SC"),local("PingFang SC");font-weight:100 900;font-display:block}\n'
    + '#captions-root{position:absolute;inset:0;pointer-events:none}\n'
    + '#ai-caption-band{position:absolute;left:' + left + 'px;top:' + top + 'px;width:' + boxWidth + 'px}\n'
    + '.ai-caption-group{position:absolute;left:0;width:100%;box-sizing:border-box;padding:16px 0;background:' + background + ';border-radius:12px;color:' + color + ';text-shadow:' + textShadow + ';opacity:0;text-align:center;font-family:"AI Video CJK",sans-serif;font-size:' + fontSize + 'px;font-weight:700;line-height:' + lineHeight + '}\n'
    + '.ai-caption-line{white-space:pre}.ai-caption-word{color:' + color + '}\n</style>\n'
    + '<script src="' + gsapSrc + '" integrity="' + integrity + '" crossorigin="anonymous"></script>\n'
    + '<script>\n(async function(){await document.fonts.load(' + JSON.stringify('700 ' + fontSize + 'px "AI Video CJK"') + ',"中文字幕Cache");await document.fonts.ready;\n'
    + 'var GROUPS=' + data + ',band=document.getElementById("ai-caption-band"),tl=gsap.timeline({paused:true});\n'
    + 'var joiner=' + joiner.toString() + ',PUNCT=/^[\\p{P}\\p{S}]+$/u,joined=' + joined.toString() + ',layoutLines=' + layoutLines.toString() + ';\n'
    + 'var canvas=document.createElement("canvas"),ctx=canvas.getContext("2d");ctx.font=' + JSON.stringify('700 ' + fontSize + 'px "AI Video CJK"') + ';\n'
    + 'window.__aiCaptionQA={ready:false,errors:[]};\n'
    + 'GROUPS.forEach(function(g){var el=document.createElement("div");el.className="ai-caption-group";el.dataset.captionId=g.id;el.dataset.frame=g.frame;\n'
    + 'var rows=layoutLines(g.words,function(text){return ctx.measureText(text).width},' + boxWidth + ',' + maxLines + ');\n'
    + 'if(rows.overflow)window.__aiCaptionQA.errors.push({id:g.id,frame:g.frame,reason:"字幕超过实际字体行宽或行数"});\n'
    + 'rows.lines.forEach(function(row){var line=document.createElement("div");line.className="ai-caption-line";row.forEach(function(w,i){var span=document.createElement("span");span.className="ai-caption-word";span.textContent=joiner(row[i-1]?.text,w.text)+w.text;line.appendChild(span)});el.appendChild(line)});band.appendChild(el);\n'
    + 'tl.set(el,{opacity:1},g.start);tl.set(el,{opacity:0},g.end);});\n'
    + 'tl.to({},{duration:' + total + '},0);window.__timelines=window.__timelines||{};window.__timelines.captions=tl;window.__aiCaptionQA.ready=true;\n'
    + '})().catch(function(error){window.__aiCaptionQA={ready:true,errors:[{reason:String(error)}]};console.error(error)});\n</script>\n</template>\n';
}

async function main(argv) {
  const flag = (name, fallback) => {
    const index = argv.indexOf("--" + name);
    return index < 0 ? fallback : argv[index + 1];
  };
  if (argv.includes("--help")) {
    console.log("node captions_zh.mjs build --project <dir> [--faceless-dir <skill-dir>] [--config <json>]");
    return;
  }
  const project = resolve(flag("project", flag("hyperframes", ".")));
  const faceless = resolve(flag("faceless-dir", join(dirname(fileURLToPath(import.meta.url)), "../../faceless-explainer")));
  const { parseStoryboard } = await import(pathToFileURL(join(faceless, "scripts/lib/storyboard.mjs")).href);
  const { parseFormat } = await import(pathToFileURL(join(faceless, "scripts/lib/dimensions.mjs")).href);
  const storyboardPath = resolve(flag("storyboard", join(project, "STORYBOARD.md")));
  const audioMetaPath = resolve(flag("audio-meta", join(project, "audio_meta.json")));
  const manifest = parseStoryboard(readFileSync(storyboardPath, "utf8"));
  const htmlPath = join(project, "compositions/captions.html");
  const out = resolve(flag("out", join(project, "caption_groups.json")));
  const hasScript = existsSync(join(project, "SCRIPT.md"));
  const meta = existsSync(audioMetaPath) ? JSON.parse(readFileSync(audioMetaPath, "utf8")) : { voices: [] };
  if (!hasScript && !meta.voices?.length) {
    rmSync(htmlPath, { force: true });
    rmSync(out, { force: true });
    console.log("中文字幕: 无口播，清除旧字幕后跳过");
    return;
  }
  const configPath = resolve(flag("config", join(project, "ai-video.config.json")));
  const config = existsSync(configPath) ? JSON.parse(readFileSync(configPath, "utf8")).captions ?? {} : {};
  if (config.gsap_src) {
    const source = resolve(project, config.gsap_src);
    const local = relative(project, source);
    if (local.startsWith("..") || !existsSync(source)) throw new Error("本地 GSAP 不存在或不在项目内");
    config.gsap_integrity = "sha384-" + createHash("sha384").update(readFileSync(source)).digest("base64");
  }
  const { width, height } = parseFormat(manifest.globals.format);
  if (!width || !height) throw new Error("STORYBOARD.md 缺少有效 format");
  const groups = buildGroups(manifest, meta, config);
  const total = manifest.frames.reduce((sum, f) => sum + f.durationSeconds, 0);
  const html = buildHtml(groups, total, width, height, config);
  mkdirSync(dirname(out), { recursive: true });
  mkdirSync(dirname(htmlPath), { recursive: true });
  writeFileSync(out, JSON.stringify({ total_duration_s: total, width, height, groups }, null, 2));
  writeFileSync(htmlPath, html);
  const shim = join(project, "caption-overrides.json");
  if (!existsSync(shim)) writeFileSync(shim, "[]\n");
  console.log("中文字幕: " + groups.length + " 组 → compositions/captions.html；预览检查 window.__aiCaptionQA");
}
if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  main(process.argv.slice(2)).catch(error => { console.error("中文字幕生成失败: " + error.message); process.exitCode = 1; });
}
