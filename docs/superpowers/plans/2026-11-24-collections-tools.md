# Collections Power Tools Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete Collections with grouped smart rules, safe previews, custom covers, play/queue actions and basic collection analytics.

**Architecture:** Keep the existing one-JSON-file-per-collection store. Extend the pure rule engine with backward-compatible AND/OR/NOT groups, add read-only preview/tracks/analysis endpoints over the existing library snapshot, and reuse the player/download manager for actions. Covers live beside collection JSON and reuse the existing image normalizer. Static member removal and mosaic fallback already exist; this plan regressions them rather than rebuilding them.

**Tech Stack:** FastAPI, SQLite/JSON, Vue 3, Vitest, existing `playlist_mosaic.normalize_uploaded_cover`.

**Spec:** `docs/superpowers/specs/2026-11-24-personal-server-feature-program-design.md` §6.8 and §6.14.

## Global Constraints

- API geriye uyumluluğu korunacak; eski düz kural listeleri AND olarak yorumlanacak.
- Her yeni kullanıcı davranışı 8 dilde eklenecek; locale key paritesi ve offline testler korunacak.
- Büyük dosya yazımları atomik olacak; token içeren dosyalar `0600` olacak.
- Koleksiyon silme/üye çıkarma kaynak playlistleri veya ses dosyalarını silmeyecek.
- Mevcut v4 paleti, tipografiyi, 0 radius, 2px çizgileri ve reduced-motion davranışını koru.
- `8000` portu değişmez; yeni bağımlılık eklenmez.
- Her görev test-first ilerler; faz sonunda tam pytest/Vitest/build/docs kapıları, ayrı commit ve doğrulanmış deploy yapılır.

## Review Focus

- **Bozuk iç içe kural:** `{op:"or", rules:[...bozuk...]}` HTTP 400 döndürmeli, mevcut kuralları değiştirmemeli — Task 1.
- **Önizleme kayıt uyumu:** aynı kural kümesi preview ve save sonrasında aynı üyeleri vermeli; preview diske yazmamalı — Task 1.
- **Kapak sınırı ve yol:** 10 MB üstü/bozuk kapak reddedilmeli, koleksiyon adı klasör dışına çıkamamalı — Task 2.
- **Mükerrer parça:** iki playlistte aynı kararlı parça bir kez oynanmalı/kuyruğa girmeli — Task 3.
- **Akıllı üye çıkarma:** statik listeden çıkarılan ama kurala uyan playlist bir sonraki okumada geri gelebilmeli; kaynak playlist silinmemeli — Task 4.

---

### Task 1: Grouped smart rules and preview

**Files:**
- Modify: `downtify/collection_rules.py`
- Modify: `downtify/collections_api.py`
- Test: `tests/test_collection_rules.py`, `tests/test_api_collections.py`
- Modify: `frontend/src/lib/collectionRules.js`, `frontend/src/__tests__/collectionRules.test.js`

**Interfaces:**
- Consumes: mevcut `normalize_rules`, `playlist_matches`, `resolve_collection`, `_library_view`.
- Produces: `normalize_rules(raw: Any) -> list[dict[str, Any]]`; grup biçimi `{op: "and"|"or"|"not", rules: [node, ...]}`; eski düz liste AND kabul eder.
- Produces: `POST /api/collections/{name}/preview` body `{rules: [...]}` → `{name, playlists: [...], computed: [...]}`; diske yazmaz.

- [ ] **Step 1: Eski AND davranışını koruyan kural testlerini yaz.**
- [ ] **Step 2: OR, NOT ve iç içe grup testlerini yaz; geçersiz op/boş NOT için 400 beklentisini ekle.**
- [ ] **Step 3: Testleri kırmızı çalıştır.**
- [ ] **Step 4: `normalize_rules` ve `playlist_matches` içinde özyinelemeli grup değerlendirmesini uygula.**
- [ ] **Step 5: Preview uç testini yaz: mevcut kurallar değişmez, sonuç kaydedilmiş kurallarla aynı üyeleri verir.**
- [ ] **Step 6: Preview uçlarını ekle ve frontend temizleme yardımcısını grup yapısına taşı.**
- [ ] **Step 7: İlgili testleri yeşil çalıştır ve commit al.**

### Task 2: Custom collection covers

**Files:**
- Modify: `downtify/collections.py`
- Modify: `downtify/collections_api.py`
- Test: `tests/test_collections.py`, `tests/test_api_collections.py`

**Interfaces:**
- Consumes: `playlist_mosaic.MAX_PLAYLIST_COVER_BYTES` (10 MB), `normalize_uploaded_cover(data, content_type)`.
- Produces: `set_collection_cover(download_dir, name, data, content_type) -> dict`; `remove_collection_cover(download_dir, name) -> dict`.
- Produces: `GET/PUT/DELETE /api/collections/{name}/cover`; kapak `Playlists/.collections/covers/<safe-name>.jpg` altında tutulur ve JSON `cover` alanı taşır.

- [ ] **Step 1: Kapak yazma/okuma/silme ve eski koleksiyonlarda mosaic fallback testlerini yaz.**
- [ ] **Step 2: 10 MB üstü, bozuk görsel ve güvensiz ad reddi testlerini yaz.**
- [ ] **Step 3: Testleri kırmızı çalıştır.**
- [ ] **Step 4: Atomik kapak yazımını, JSON alanını ve görsel doğrulamasını uygula.**
- [ ] **Step 5: Cover HTTP uçlarını ve auth kurallarını ekle.**
- [ ] **Step 6: Testleri yeşil çalıştır ve commit al.**

### Task 3: Resolved tracks and analytics

**Files:**
- Create: `downtify/collection_actions.py`
- Modify: `downtify/collections_api.py`
- Test: `tests/test_collection_actions.py`, `tests/test_api_collections.py`
- Modify: `frontend/src/model/collections.js`, `frontend/src/__tests__/collectionActions.test.js`

**Interfaces:**
- Consumes: `coll.resolve_collection`, `collections_api._library_view`, `library_catalog` playlist/file alanları.
- Produces: `collection_tracks(data, playlists, tracks) -> list[dict]`; parça playlist sırasında, `song_id`/`url`/`file` kararlı anahtarına göre tekrarsız.
- Produces: `collection_analysis(data, playlists, tracks) -> {tracks, duration_seconds, bytes, missing_tracks, missing_ratio}`.
- Produces: `GET /api/collections/{name}/tracks` ve `GET /api/collections/{name}/analysis`.

- [ ] **Step 1: Çok playlistli tekrar, kararsız parça ve eksik dosya sayımı testlerini yaz.**
- [ ] **Step 2: Testleri kırmızı çalıştır.**
- [ ] **Step 3: Saf `collection_tracks` ve `collection_analysis` fonksiyonlarını uygula.**
- [ ] **Step 4: İki HTTP uçlarını ekle; normal kullanıcı okuyabilir, yazma uçları admin-only kalır.**
- [ ] **Step 5: Frontend model sarmalayıcılarını ve istek testlerini ekle.**
- [ ] **Step 6: Testleri yeşil çalıştır ve commit al.**

### Task 4: Collections UI, docs and release

**Files:**
- Modify: `frontend/src/views/CollectionsView.vue`
- Create: `frontend/src/components/collections/CollectionCoverPicker.vue`
- Modify: `frontend/src/i18n/locales/*.js`
- Modify: `frontend/src/__tests__/collectionCoverGrid.test.js`, `frontend/src/__tests__/collectionRules.test.js`
- Modify: `README.md`, `docs/features/collections.md`, `docs/features/smart-collections.md`, `docs/api-reference.md`
- Modify: `docs/superpowers/plans/2026-11-24-personal-server-program-roadmap.md`

**Interfaces:**
- Consumes: Task 1 preview, Task 2 cover uçları, Task 3 tracks/analysis, mevcut `usePlayer`, `useDownloadManager.fromSongs`.
- Produces: kartlarda Play/Queue, kapak yükle/kaldır, analiz özeti; kural editöründe grup ekle ve Preview.

- [ ] **Step 1: Grup ekleme/kaldırma ve preview isteği için saf frontend testlerini yaz.**
- [ ] **Step 2: Testleri kırmızı çalıştır.**
- [ ] **Step 3: Kural editörünü AND/OR/NOT gruplarına genişlet; eski düz kuralları düzenlerken AND grubuna çevir.**
- [ ] **Step 4: Cover picker ve kart fallback davranışını ekle.**
- [ ] **Step 5: Tracks/analysis verisini kullanarak Play, Queue ve özet satırlarını bağla.**
- [ ] **Step 6: Sekiz locale metnini, dokümanı ve API referansını güncelle.**
- [ ] **Step 7: Tam pytest, ruff, Vitest, frontend/docs build ve locale paritesi kapılarını koş.**
- [ ] **Step 8: Commit, fresh review, Critical/Important düzeltmeleri, fast-forward merge, deploy ve health doğrulaması yap.**
