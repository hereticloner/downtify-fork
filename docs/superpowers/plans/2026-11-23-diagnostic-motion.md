# Diagnostic Motion Expansion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Downtify UI perdahini, kilitli v4 tasarım doktrinini bozmadan daha görünür kılmak.

**Architecture:** Yalnızca mevcut CSS katmanlarında değişiklik: Vue geçiş sınıflarını kademeli (steps) opaklık fadesine çevir, tüm butonlara 80ms opaklık basılı-geribildirimi ekle, liste giriş/çıkışındaki doktrin dışı translateYyi kaldır, reduced-motion global 1ms kill-switchi yerine kapsamlı kurallara geçir. Yeni bağımlılık, JS veya bileşen değişikliği yok.

**Tech Stack:** Vue 3, Tailwind v4, Vite 8, vitest.

**Spec:** `DESIGN.md` (v4 "The Printing Desk"), `PRODUCT.md`.

## Global Constraints

- Motion is diagnostic, not decorative: 80–120ms linear fades, stepped equalizer, six-step shimmer.
- Nothing springs, floats or glows. No shadow, no blur, no glow. No lift, no scale, no shadow on buttons.
- Workspace, not a showreel. No new animation library, no MCP, no JS motion engine.
- Reduced motion must leave a usable final state; never globally collapse durations.

## Review Focus

- Press feedback must not alter geometry (no scale/lift) and must skip disabled buttons.
- Stepped fades stay inside the 80–120ms budget and remain opacity-only.
- Reduced motion keeps final states visible; the looping shimmer/equalizer stop cleanly.
- Color/background transitions remain enabled under reduced motion.
- Existing tests and production build stay green.

---

### Task 1: CSS motion expansion

**Files:** Modify `frontend/src/styles/tokens.css`, `frontend/src/index.css`.
**Test:** `frontend/src/__tests__/motionDoctrine.test.js`

- [ ] **Step 1: Add button press feedback in tokens.css `@layer base` next to `button, [role=button]`: `button:not(:disabled) { transition: opacity 80ms linear; }` and `button:not(:disabled):active { opacity: 0.6; }`.**
- [ ] **Step 2: Convert `.page-*` and `.fade-*` in tokens.css to `transition: opacity 100ms steps(3, end);` (both active selectors only).**
- [ ] **Step 3: In index.css, replace `.list-enter-active/.list-leave-active { transition: all 180ms ease-out; }` and the translateY leave state with `opacity 100ms steps(3, end)` and `opacity: 0` only.**
- [ ] **Step 4: Delete the global `1ms !important` reduced-motion block from tokens.css; add a scoped `@media (prefers-reduced-motion: reduce)` block at the END of index.css that stops `.shimmer`/`.animate-eq` with visible final states, zeroes only the named Vue transition classes, and leaves color/background transitions on.**
- [ ] **Step 5: Add a small static-CSS vitest guard in `src/__tests__/motionDoctrine.test.js` (mirrors tokenContrast.test.js) asserting: no `180ms ease-out` in index.css, no global `1ms !important` in tokens.css, press feedback present, reduced-motion block present.**
- [ ] **Step 6: Run `npm --prefix frontend test`, `npm --prefix frontend run build`, `npm --prefix frontend run format:check`.**
- [ ] **Step 7: Verify rendered UI at 2560px desktop and ~780px phone, normal and reduced motion.**
- [ ] **Step 8: Commit on `feat/collections`; deploy with `ssh home "~/bin/downtify-deploy.sh"` after visual check.**
