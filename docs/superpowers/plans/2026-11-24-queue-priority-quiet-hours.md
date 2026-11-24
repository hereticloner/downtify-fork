# Kuyruk Önceliği + Sessiz Saatler Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bekleyen indirmeleri normal/yüksek öncelikle sıralamak, toplu kaldırma/askıya alma/sürdürme sunmak ve yapılandırılan saat penceresinde yeni indirmeleri durdurmak; çalışan indirmeyi kesmemek.

**Architecture:** `PendingDownloads` SQLite tablosuna `priority` alanı eklenir; yalnız `queued` işler taşınır. `QueuePause` mevcut bekleme kapısına saat penceresi kontrolü eklenir. Ayarlar `queue_control` içinde saklanır; saat dilimi açıkça `Europe/Istanbul` varsayılanıyla yönetilir.

**Tech Stack:** FastAPI, SQLite, asyncio, Vue 3, Vitest.

**Spec:** `docs/superpowers/specs/2026-11-24-personal-server-feature-program-design.md`

## Global Constraints

- Çalışan indirme sessiz saatte kesilmez; bitince yeni işler bekler.
- Öncelik yalnız `queued` işlerde değişir; `downloading`, `done`, `error` etkilenmez.
- Varsayılan öncelik `normal`; varsayılan sessiz saatler kapalı.
- Restart sonrası öncelik ve zamanlama korunur.
- 8 locale key paritesi ve offline testler korunur.
- `8000` portu değişmez.

## Review Focus

- **Sıra:** restart sonrası yüksek öncelikli iş normal işin önüne geçer; aynı öncelikte eski sıra korunur.
- **Kesintisizlik:** sessiz saat başlarken çalışan iş tamamlanır; yeni iş pencere dışında bekler.
- **DST:** saat dilimi geçişleri saat penceresini kaydırmaz; yerel saat esas alınır.
- **Yetki:** kuyruk değişiklikleri admin-only; normal kullanıcı okuyabilir.
- **Mükerrerlik:** toplu işlemler aynı işi iki kez değiştirmez; silinen iş diriltmez.

---

### Task 1: Kalıcı öncelik ve sıralama

**Files:**
- Modify: `downtify/download_queue.py`, `downtify/api.py`
- Test: `tests/test_queue_priority.py`

**Interfaces:**
- Produces: `PendingDownload.priority`; `set_priorities(song_ids, priority)`; `rows()` öncelikli sıra.

- [ ] **Step 1: Şema migrasyonu, varsayılan normal ve sıralama testlerini yaz.**
- [ ] **Step 2: Kırmızıyı doğrula; `priority TEXT NOT NULL DEFAULT 'normal'` ekle ve `ORDER BY priority DESC, seq` uygula.**
- [ ] **Step 3: Yalnız bekleyen işleri güncellemeyi ve mükerrer korumayı test et.**
- [ ] **Step 4: Test/lint/commit.**

### Task 2: Kuyruk kontrol API’si

**Files:**
- Modify: `downtify/api.py`, `downtify/auth.py`
- Test: `tests/test_queue_control_api.py`

**Interfaces:**
- Produces: `POST /api/queue/priority`, `POST /api/queue/bulk`.

- [ ] **Step 1: Admin-only auth, geçersiz öncelik ve toplu remove/pause/resume testlerini yaz.**
- [ ] **Step 2: Kırmızıyı doğrula ve uçları ekle.**
- [ ] **Step 3: Toplu pause yalnız bekleyen işleri durdurur; resume yalnız duraklatılmış işleri sürdürür.**
- [ ] **Step 4: Test/lint/commit.**

### Task 3: Sessiz saat motoru

**Files:**
- Create: `downtify/queue_schedule.py`
- Modify: `downtify/download_queue.py`, `downtify/api.py`, `main.py`
- Test: `tests/test_queue_schedule.py`

**Interfaces:**
- Produces: `QueueSchedule`; `quiet_hours(settings, now)`; `schedule_loop`.

- [ ] **Step 1: Kapalı, gündüz/gece penceresi, sınır saati ve DST testlerini yaz.**
- [ ] **Step 2: Kırmızıyı doğrula; `ZoneInfo` ile yerel saat hesabını ekle.**
- [ ] **Step 3: `QueuePause` kapısına otomatik sessiz durumu bağla; elle pause ile çakışmayı koru.**
- [ ] **Step 4: Test/lint/commit.**

### Task 4: Ayarlar ve kuyruk arayüzü

**Files:**
- Create: `frontend/src/components/settings/QueueControlPanel.vue`
- Modify: `frontend/src/views/QueueView.vue`, `frontend/src/components/queue/QueueItem.vue`, `frontend/src/model/api.js`, `frontend/src/views/SettingsView.vue`
- Test: `frontend/src/__tests__/queueControl.test.js`, `frontend/src/__tests__/queuePriority.test.js`

**Interfaces:**
- Produces: Settings → Server → Queue control; queued satırlarda öncelik ve seçim.

- [ ] **Step 1: Saf sıralama/seçim yardımcılarını test et.**
- [ ] **Step 2: Öncelik düğmeleri ve toplu eylemleri ekle.**
- [ ] **Step 3: Sessiz saat aç/kapa, başlangıç/bitiş ve saat dilimi ayarlarını ekle.**
- [ ] **Step 4: 8 locale key + test/build/commit.**

### Task 5: Doküman, tam doğrulama ve deploy

- [ ] README + `docs/features/download-queue.md` + API reference güncelle.
- [ ] Tam pytest, ruff, Vitest, frontend/docs build kapılarını koş.
- [ ] Commit, fast-forward, deploy ve health doğrula.
- [ ] Roadmap’da kuyruk maddesini tamamlandı işaretle; Collections güç araçları planını yaz.
