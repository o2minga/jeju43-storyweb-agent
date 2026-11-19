"use client";

import { useState, type FormEvent } from "react";

export default function PreviewLoginPage() {
  const [password, setPassword] = useState("");
  const [error, setError] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(false);

    const res = await fetch("/api/preview-login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ password }),
    });

    setSubmitting(false);
    if (res.ok) {
      // next는 제출 시점에만 필요하므로 여기서 그때그때 읽는다 — 마운트 시 useEffect로
      // state에 미리 담아두지 않아도 되고(SSR에서는 window가 없어 그 자체로도 못 함),
      // 렌더 중 setState 호출 관련 린트 경고도 자연스럽게 피한다.
      const params = new URLSearchParams(window.location.search);
      window.location.href = params.get("next") || "/preview/index.html";
    } else {
      setError(true);
    }
  }

  return (
    <div
      style={{
        display: "flex",
        minHeight: "100vh",
        alignItems: "center",
        justifyContent: "center",
        background: "#FAFAF8",
        fontFamily: "sans-serif",
      }}
    >
      <form
        onSubmit={handleSubmit}
        style={{
          display: "flex",
          flexDirection: "column",
          gap: 12,
          padding: 32,
          background: "#fff",
          border: "1px solid #D3D1C7",
          borderRadius: 12,
          width: 320,
        }}
      >
        <h1 style={{ fontSize: "1.1em", margin: 0, color: "#2C2C2A" }}>
          제주 4·3 스토리웹 — 팀 미리보기
        </h1>
        <p style={{ fontSize: "0.85em", color: "#6b6b68", margin: 0 }}>
          팀·함께공 전용입니다. 비밀번호를 입력하세요.
        </p>
        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="비밀번호"
          autoFocus
          style={{ padding: 8, border: "1px solid #D3D1C7", borderRadius: 6 }}
        />
        {error && (
          <p style={{ color: "#b3261e", fontSize: "0.85em", margin: 0 }}>
            비밀번호가 올바르지 않습니다.
          </p>
        )}
        <button
          type="submit"
          disabled={submitting}
          style={{
            padding: 10,
            background: "#1F2A44",
            color: "#fff",
            border: "none",
            borderRadius: 6,
            cursor: submitting ? "default" : "pointer",
          }}
        >
          {submitting ? "확인 중..." : "입장"}
        </button>
      </form>
    </div>
  );
}
