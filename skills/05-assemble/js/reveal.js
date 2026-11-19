/* ============================================================
   reveal.js — 스크롤 등장 애니메이션 (공용)
   Intersection Observer 기반 페이드인 + 방향 슬라이드 + 스태거.

   사용법 (HTML/동적 요소):
     <div class="reveal">...</div>                 기본(아래→위 페이드)
     <div data-reveal="left">...</div>             왼쪽에서 슬라이드
     <div data-reveal="right">...</div>            오른쪽에서
     <div data-reveal="zoom">...</div>             살짝 확대
     <div data-reveal-group> <p/><p/> </div>       자식들이 순차 등장(스태거)

   Reveal.init()      : 문서 전체 관찰 시작
   Reveal.observe(el) : 동적으로 추가된 요소/컨테이너 관찰
   prefers-reduced-motion 이면 즉시 표시(애니메이션 없음).
   ============================================================ */
'use strict';

window.Reveal = (() => {
  const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  let io = null;

  function ensureObserver() {
    if (io || reduce) return;
    io = new IntersectionObserver((entries) => {
      entries.forEach((e) => {
        if (e.isIntersecting) { e.target.classList.add('in'); io.unobserve(e.target); }
      });
    }, { threshold: 0.14, rootMargin: '0px 0px -8% 0px' });
  }

  // 관찰 대상 수집: 자신이 reveal 이거나, 내부의 reveal 요소들
  function collect(root) {
    const list = [];
    const isTarget = (el) => el.classList && (el.classList.contains('reveal') || el.hasAttribute('data-reveal'));
    if (root.nodeType === 1 && isTarget(root)) list.push(root);
    root.querySelectorAll && root.querySelectorAll('.reveal, [data-reveal]').forEach((el) => list.push(el));
    return list;
  }

  function observe(root) {
    // 스태거: data-reveal-group 자식에 순차 지연 부여
    (root.querySelectorAll ? root.querySelectorAll('[data-reveal-group]') : []).forEach(setStagger);
    if (root.hasAttribute && root.hasAttribute('data-reveal-group')) setStagger(root);

    if (reduce) { collect(root).forEach((el) => el.classList.add('in')); return; }
    ensureObserver();
    collect(root).forEach((el) => io.observe(el));
  }

  function setStagger(group) {
    const step = parseInt(group.dataset.revealStep || '80', 10); // ms
    Array.from(group.children).forEach((child, i) => {
      if (child.classList.contains('reveal') || child.hasAttribute('data-reveal')) {
        child.style.transitionDelay = (i * step) + 'ms';
      }
    });
  }

  function init() { observe(document); }

  return { init, observe };
})();
