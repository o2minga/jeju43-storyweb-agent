// 로컬 정적 서버 — 결과물(지도 인덱스·스토리 페이지)을 localhost로 서빙.
// Windows에서 한글 파일명(관덕정.html)을 UTF-16 API로 정확히 처리한다.
// 사용법:  node scripts/serve.mjs [루트=output] [포트=8000] [--home=/경로]
//   --home: 루트('/')로 접속하면 그 경로로 302 리다이렉트 (앱이 하위 폴더에 있을 때 편의)
import http from "node:http";
import { readFile, stat } from "node:fs/promises";
import { join, extname, normalize, resolve } from "node:path";

const argv = process.argv.slice(2);
const flags = argv.filter((a) => a.startsWith("--"));
const positional = argv.filter((a) => !a.startsWith("--"));
const ROOT = resolve(positional[0] || "output");
const PORT = Number(positional[1] || 8000);
const HOME = (flags.find((f) => f.startsWith("--home=")) || "").split("=")[1] || "";

const TYPES = {
  ".html": "text/html; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".mjs": "text/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
  ".gif": "image/gif", ".webp": "image/webp", ".svg": "image/svg+xml",
  ".ico": "image/x-icon", ".mp3": "audio/mpeg", ".mp4": "video/mp4",
  ".woff": "font/woff", ".woff2": "font/woff2",
};

const server = http.createServer(async (req, res) => {
  try {
    let urlPath = decodeURIComponent(req.url.split("?")[0]);
    // 루트 접속 → --home 지정 시 그쪽으로 리다이렉트 (앱이 하위 폴더에 있을 때)
    if (HOME && (urlPath === "/" || urlPath === "/index.html")) {
      res.writeHead(302, { Location: HOME });
      return res.end();
    }
    if (urlPath.endsWith("/")) urlPath += "index.html";
    // 디렉터리 탈출 방지
    const rel = normalize(urlPath).replace(/^(\.\.(\/|\\|$))+/, "");
    let filePath = join(ROOT, rel);

    let s;
    try {
      s = await stat(filePath);
    } catch {
      res.writeHead(404, { "content-type": "text/html; charset=utf-8" });
      return res.end(`404 Not Found: ${rel}`);
    }
    if (s.isDirectory()) filePath = join(filePath, "index.html");

    const data = await readFile(filePath);
    res.writeHead(200, {
      "content-type": TYPES[extname(filePath).toLowerCase()] || "application/octet-stream",
      "cache-control": "no-cache",
    });
    res.end(data);
  } catch (e) {
    res.writeHead(500, { "content-type": "text/plain; charset=utf-8" });
    res.end(`500 ${e.message}`);
  }
});

server.listen(PORT, "127.0.0.1", () => {
  console.log(`✔ 정적 서버 실행: http://localhost:${PORT}/  (루트: ${ROOT})`);
});
