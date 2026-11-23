# Expanded Diagnostic Motion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Downtify UI'sında onaylanan 4 hareket ailesini ve ek CSS-only aileleri v4 kimliği bozmadan eklemek.

**Architecture:** Tüm yeni hareket CSS token/@keyframe/transition sınıflarında; Vue tarafında yalnız TransitionGroup adı ve birkaç sınıf eklemesi. Yeni bağımlılık, JS motion, yeni MCP yok.

**Tech Stack:** Vue 3.5, Tailwind v4, Vite 8, vitest 4.1, CSS token sistemi.

**Spec:** `docs/superpowers/specs/2026-11-23-expanded-motion-design.md`

## Global Constraints

- Palet #F3F3F0 / #171717 / #0047FF, 0 radius, 2px çizgi — dokunulmaz.
- Süre 80–240ms; `linear` veya `steps(n)`; yalnız opacity/transform/background-position.
- Yay, yüzdürme, parlama, gölge, blur, buton scale YOK.
- Global `1ms !important` reduced-motion katili YOK; her ailenin statik son durumu var.
- `npm test` + `npm run build` geçmeli; `format:check` repo-geneli kırık, dokunulmaz.
- Deploy `ssh home '~/bin/downtify-deploy.sh'`; rollback `downtify-fork:pre-v4`.
- `mirror/lockfile` ve `w6/` asla commit edilmez.

## Review Focus

- Kilitli v4 doktrini aşan hareket (spring/glow/shadow/scale) → statik CSS testi yasaklı kalıpları arar.
- Reduced-motion açıkken animasyon çalışmaya devam etmesi → statik test + focus/eq/shimmer statik son durum kontrolü.
- Tailwind utilities katmanının yeni sınıfları ezmesi → testler kaynak CSS'i okur; görsel doğrulama üretim CSS'inde yapılır.
- Mevcut `.list-*` sınıfının bozulması → test opacity-only ve steps(3) şartlarını sabitler.
- Repo-geneli format:check gürültüsünün yeni değişikliğe mal edilmemesi → yalnız 3 kaynak dosya + 2 test dosyası commit edilir.

---

### Task 1: CSS hareket aileleri ve statik testler

**Files:**
- Modify: `frontend/src/styles/tokens.css`
- Modify: `frontend/src/index.css`
- Modify: `frontend/src/__tests__/motionDoctrine.test.js`
- Create: `frontend/src/__tests__/expandedMotion.test.js`

**Interfaces:**
- Consumes: mevcut `--animate-rise`, `--animate-eq`, `--animate-shimmer`, `.page-*`, `.fade-*`, `.list-*`.
- Produces: `.toast-*`, `.stat-*`, `.hover-dim`, `.list-move`, `--animate-stat`, `--animate-toast`, reduced-motion statik kuralları.

- [ ] **Step 1: Yeni testi yaz**

`expandedMotion.test.js`: kaynak CSS'i okur; `.toast-enter-active` `steps(3)` + ≤200ms, `.stat-reveal` `steps(4)` + ≤240ms, `.list-move` `transform` içerir, yasaklı `spring|cubic-bezier|box-shadow|filter: blur|scale(1.1)` yok, reduced bloğunda `.toast-*` ve `.stat-*` statik son durum var.

- [ ] **Step 2: Testin düştüğünü doğrula**

Run Docker vitest. Expected: yeni test FAIL.

- [ ] **Step 3: CSS'i ekle**

tokens.css: `--animate-stat: stat-reveal 200ms steps(4,end) both;`, `@keyframes stat-reveal{from{opacity:0}to{opacity:1}}`, `.toast-enter-active/.toast-leave-active{transition:opacity 160ms steps(3,end),transform 160ms steps(3,end)}`, `.toast-enter-from/.toast-leave-to{opacity:0;transform:translateY(4px)}`, `.stat-reveal` sınıfı, `.hover-dim{transition:opacity 80ms linear}` + `:hover{opacity:.6}`, `:focus-visible` 2px outline korunur (animasyon eklenmez).
index.css: `.list-move{transition:transform 120ms linear,opacity 120ms linear}`; reduced-motion bloğuna `.toast-*`, `.stat-*`, `.list-move`, `.hover-dim` statik son durum kuralları.

- [ ] **Step 4: Testleri geçir**

Run Docker vitest. Expected: tüm testler PASS.

### Task 2: Vue bağlantıları, kapılar, commit, deploy

**Files:**
- Modify: `frontend/src/components/ui/UiToasts.vue:8`
- Modify: `frontend/src/views/HomeView.vue:388-392`
- Modify: `frontend/src/components/library/TrackList.vue:88`

**Interfaces:**
- Consumes: Task 1 `.toast-*`, `.stat-reveal`, `.hover-dim`.
- Produces: — (son task).

- [ ] **Step 1: UiToasts TransitionGroup name="fade" → name="toast"**

- [ ] **Step 2: HomeView `counts` döngüsündeki `<dd>` sınıfına `stat-reveal` ekle** — yalnız sınıf, veri/hesaplama değişmez.

- [ ] **Step 3: TrackList satır sınıfına `hover-dim` ekle** — mevcut `hover:bg-surface-2` korunur.

- [ ] **Step 4: Kapılar** — Docker içinde `npm test` ve `npm run build` geçmeli.

- [ ] **Step 5: Commit** — yalnız 5 dosya; mesaj `feat(ui): expand diagnostic motion families`.

- [ ] **Step 6: Deploy + doğrulama** — `ssh home '~/bin/downtify-deploy.sh'`; health ok; üretim CSS'inde yeni sınıflar; reduced-motion statik.

## Execution Handoff

Yürütme yöntemi kullanıcı tarafından verildi ("hepsini ekle", önceki turda "başla") → native, bu oturumda Echo.
