// output/ 결과물을 (1) Next 앱이 서빙할 수 있게 public/preview-assets/ 로 복사하고,
// (2) HTML 안의 상대경로를 절대경로로 치환한 뒤 (3) Supabase `locations` 로 올린다.
//
// 팀 미리보기(localhost:3000)의 /api/preview/map · /api/preview/detail 은 이 테이블을
// 읽어 map_html/detail_html 을 그대로 브라우저에 써 넣는다(document.write). 그래서 HTML
// 안의 상대경로(assets/…, chatbot-modal.js 등)는 /api/preview/ 기준으로 풀려 404가 난다.
// 이 스크립트가 그 경로들을 절대경로로 바꾸고 에셋을 앱이 서빙할 위치로 복사한다.
//
//   - 지도 배경/썸네일/오디오/JS  →  /preview-assets/<output상대경로>
//   - 지도의 상세 링크(<id>/05-assemble.html)  →  /api/preview/detail?id=<id>
//
// 사용법:  node scripts/publish-to-supabase.mjs [출력루트=output]
//   .env.local 의 NEXT_PUBLIC_SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY 를 사용한다.
import { readFile, writeFile, mkdir, readdir, copyFile } from "node:fs/promises";
import { resolve, join } from "node:path";
import { createClient } from "@supabase/supabase-js";

const ASSET_EXT = new Set([
  "png", "jpg", "jpeg", "webp", "gif", "svg", "ico",
  "mp3", "mp4", "wav", "ogg", "webm",
  "js", "mjs", "css", "woff", "woff2",
]);
const PUBLIC_DIR = "public/preview-assets"; // Next 는 public/ 을 루트('/')로 서빙 → /preview-assets/…

// --- .env.local 수동 로드 (dotenv 의존성 없이) ---
async function loadEnv(file) {
  let text;
  try {
    text = await readFile(file, "utf8");
  } catch {
    return;
  }
  for (const line of text.split(/\r?\n/)) {
    const m = line.match(/^\s*([A-Z0-9_]+)\s*=\s*(.*)$/);
    if (!m) continue;
    let val = m[2].trim();
    if (
      (val.startsWith('"') && val.endsWith('"')) ||
      (val.startsWith("'") && val.endsWith("'"))
    ) {
      val = val.slice(1, -1);
    }
    if (!(m[1] in process.env)) process.env[m[1]] = val;
  }
}

// --- posix 경로 유틸 (URL은 항상 forward slash) ---
function posixJoin(base, rel) {
  const parts = (base ? base.split("/") : []).concat(rel.split("/"));
  const out = [];
  for (const p of parts) {
    if (p === "" || p === ".") continue;
    if (p === "..") out.pop();
    else out.push(p);
  }
  return out.join("/");
}

const EXTERNAL = /^(https?:)?\/\/|^\/|^data:|^#|^mailto:|^tel:|^javascript:/i;

// HTML 태그 속성만 치환한다.
function rewriteAttrs(seg, baseDir) {
  return seg.replace(
    /\b(src|href|poster|data-thumbnail)\s*=\s*"([^"]*)"/gi,
    (whole, attr, url) => {
      if (!url || EXTERNAL.test(url)) return whole;

      // 지도의 상세 페이지 링크 → 미리보기 API 로
      if (attr.toLowerCase() === "href" && /\/05-assemble\.html$/i.test(url)) {
        const id = url.split("/")[0];
        return `${attr}="/api/preview/detail?id=${encodeURIComponent(id)}"`;
      }

      // 그 외 상대경로 에셋 → /preview-assets/<output상대경로>
      const abs = "/preview-assets/" + posixJoin(baseDir, url);
      return `${attr}="${abs}"`;
    },
  );
}

// 지도 마커 데이터(<script> 안 PLACES 배열)의 상대경로 치환.
// 속성 치환은 <script>를 건너뛰므로, 여기서 "따옴표로 감싼" 안전·명확한 패턴만 전역 치환한다.
//   - "<id>/05-assemble.html"  → 상세 미리보기 API
//   - "<id>/assets/…"          → /preview-assets/…  (썸네일)
// 두 패턴 모두 이미 절대경로(/…)로 바뀐 문자열은 시작 문자가 달라 다시 매치되지 않는다.
function rewriteEmbeddedData(html) {
  return html
    .replace(/"([A-Za-z0-9_-]+)\/05-assemble\.html"/g, '"/api/preview/detail?id=$1"')
    .replace(/"([A-Za-z0-9_-]+\/assets\/[^"]+)"/g, '"/preview-assets/$1"');
}

// baseDir: 이 HTML 파일의 output 기준 디렉터리("" = output 루트, "gwandeokjeong" = 상세)
// 실행 <script> 블록은 속성 치환에서 건드리지 않는다 — 그 안의 JS 문자열 리터럴(예:
// '<img src="'+v+'"')을 속성으로 오인해 깨뜨리지 않도록. 대신 명확한 데이터 패턴만
// rewriteEmbeddedData 로 별도 치환한다.
function rewriteHtml(html, baseDir) {
  const parts = html.split(/(<script\b[^>]*>[\s\S]*?<\/script>)/gi);
  const attrs = parts
    .map((seg, i) => (i % 2 === 1 ? seg : rewriteAttrs(seg, baseDir)))
    .join("");
  return rewriteEmbeddedData(attrs);
}

// output/ 트리에서 에셋 파일만 public/preview-assets/ 로 복사(구조 보존)
async function syncAssets(root) {
  let count = 0;
  async function walk(relDir) {
    const abs = relDir ? join(root, relDir) : root;
    const entries = await readdir(abs, { withFileTypes: true });
    for (const e of entries) {
      const rel = relDir ? `${relDir}/${e.name}` : e.name;
      if (e.isDirectory()) {
        await walk(rel);
      } else {
        const ext = e.name.split(".").pop().toLowerCase();
        if (!ASSET_EXT.has(ext)) continue;
        const dest = join(PUBLIC_DIR, rel);
        await mkdir(join(dest, ".."), { recursive: true });
        await copyFile(join(root, rel), dest);
        count++;
      }
    }
  }
  await walk("");
  return count;
}

async function main() {
  const ROOT = resolve(process.argv[2] || "output");
  await loadEnv(resolve(".env.local"));

  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const key = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!url || !key) {
    console.error(
      "✗ NEXT_PUBLIC_SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY 가 .env.local 에 설정돼 있지 않습니다.",
    );
    process.exit(1);
  }
  const supabase = createClient(url, key, { auth: { persistSession: false } });

  // 1) 에셋을 앱이 서빙할 위치로 복사
  const copied = await syncAssets(ROOT);
  console.log(`✔ 에셋 ${copied}개 → ${PUBLIC_DIR}/ 복사`);

  // 2) 지도 인덱스 (baseDir = "" 루트) — API는 최신 행의 map_html 하나만 서빙한다
  const rawMap = await readFile(join(ROOT, "index.html"), "utf8").catch(() => {
    console.error(`✗ ${join(ROOT, "index.html")} 를 읽을 수 없습니다. 06-map 을 먼저 실행하세요.`);
    process.exit(1);
  });
  const mapHtml = rewriteHtml(rawMap, "");

  // 3) 대상 장소 목록
  const places = JSON.parse(
    await readFile(join(ROOT, "map-places.json"), "utf8").catch(() => {
      console.error(`✗ ${join(ROOT, "map-places.json")} 를 읽을 수 없습니다.`);
      process.exit(1);
    }),
  );

  const now = new Date().toISOString();
  const rows = [];
  for (const p of places) {
    const id = p.location_id;
    let detailHtml = "";
    try {
      const raw = await readFile(join(ROOT, id, "05-assemble.html"), "utf8");
      detailHtml = rewriteHtml(raw, id); // baseDir = 장소 id
    } catch {
      console.warn(`⚠ ${id}: 05-assemble.html 없음 — detail_html 을 빈 값으로 올립니다.`);
    }
    rows.push({ location_id: id, detail_html: detailHtml, map_html: mapHtml, updated_at: now });
  }

  if (rows.length === 0) {
    console.error("✗ 올릴 장소가 없습니다 (map-places.json 이 비어 있음).");
    process.exit(1);
  }

  const { error } = await supabase
    .from("locations")
    .upsert(rows, { onConflict: "location_id" });
  if (error) {
    console.error("✗ 업로드 실패:", error.message);
    process.exit(1);
  }

  console.log(`✔ ${rows.length}개 장소 업로드 완료: ${rows.map((r) => r.location_id).join(", ")}`);
  console.log("  → localhost:3000/preview-login 로 확인하세요.");
}

main().catch((e) => {
  console.error("✗ 예기치 못한 오류:", e.message);
  process.exit(1);
});
