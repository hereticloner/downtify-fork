# Spotify Sync Otomatik Eksik İndirme + Başarısızlık Merkezi Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Spotify Sync'e sonradan eklenen parçaları opt-in olarak otomatik kuyruğa almak ve indirme hatalarını restart sonrası da görünür, yeniden denenebilir ve hariç tutulabilir hâle getirmek.

**Architecture:** Yeni `DownloadFailureStore` mevcut kütüphane SQLite dosyasında kalıcı hata kayıtları tutar; `_run_download` başarı/hata geçişlerinde bu store'u günceller. Spotify Sync mevcut diff çıktısındaki `added` listesini kullanır ve yalnız `auto_download_added` açıkken mevcut idempotent missing-track kuyruklama akışını tetikler.

**Tech Stack:** Python 3.12+, FastAPI, SQLite, Vue 3, Vitest, Vite.

**Spec:** `docs/superpowers/specs/2026-11-24-personal-server-feature-program-design.md`

## Global Constraints

- Otomatik indirme varsayılan kapalıdır.
- İlk Spotify Sync baseline alır ve hiçbir parçayı otomatik indirmez.
- Yalnız sonraki eklemeler otomatik kuyruğa alınır; mevcut eksikler ayrı eylekle kalır.
- Mükerrer kuyruk kaydı engellenir.
- Hata mesajları token veya tam URL içermez.
- Resume/Stats API'leri ve mevcut queue yanıtları kırılmaz.
- 8 locale key paritesi korunur.
- Testler offline olur.
- Kullanıcı davranışı değiştiği için README + Spotify Sync/Queue dokümanları güncellenir.

## Review Focus

- **Aynı parça tekrar tekrar başarısız:** tek kalıcı hata kaydı, artan deneme sayısı.
- **Yeniden deneme başarılı:** hata kaydı kapanır; listede görünmez.
- **İlk sync veya ayar kapalı:** otomatik kuyruk oluşmaz.
- **Aynı Spotify parçası iki playlistte eklenir:** kuyrukta tek job, iki playlist bağlamı birleşir.
- **Restart:** çözülmemiş hatalar Queue'da yeniden görünür; çözülmüşler geri gelmez.

---

### Task 1: Kalıcı indirme hatası store'u

**Files:**
- Create: `downtify/download_failures.py`
- Test: `tests/test_download_failures.py`

**Interfaces:**
- Produces:
  - `class DownloadFailureStore(db_path: Path)`
  - `record(*, song_id: str, song: dict[str, Any], message: str, code: str = '', provider: str = '', playlist_name: str = '') -> dict[str, Any]`
  - `resolve(song_id: str) -> bool`
  - `list(limit: int = 100, include_resolved: bool = False) -> list[dict[str, Any]]`
  - `clear() -> int`
  - `forget_song(song_id: str) -> bool`

- [ ] **Step 1: Kayıt/birleştirme testini yaz**

Aynı `song_id` iki kez hata üretsin: liste bir kayıt, `attempts=2`, `last_seen` yenilenmiş olsun. Farklı kullanıcı/playlist bağlamı kaybolmasın.

- [ ] **Step 2: Kırmızıyı doğrula**

Run: `docker exec downtify-feature-py uv run pytest tests/test_download_failures.py -q`
Expected: FAIL, modül yok.

- [ ] **Step 3: Şemayı ve `record` mantığını uygula**

`download_failures` tablosu: `song_id PRIMARY KEY`, `song_json`, `message`, `code`, `provider`, `playlist_name`, `attempts`, `first_seen`, `last_seen`, `resolved_at`. `record` upsert ile `attempts += 1` yapsın. Mesajı 1000 karaktere kırp.

- [ ] **Step 4: Resolve/list/clear testlerini yaz**

`resolve` yalnız açık kaydı kapatır; varsayılan liste çözülmüşleri göstermez; `clear` yalnız çözülmüşleri siler; `forget_song` kaydı tamamen siler.

- [ ] **Step 5: Yeşili doğrula ve lint/commit**

```bash
docker exec downtify-feature-py uv run pytest tests/test_download_failures.py -q
docker exec downtify-feature-py uv run ruff check downtify/download_failures.py tests/test_download_failures.py
docker exec downtify-feature-py uv run ruff format --check downtify/download_failures.py tests/test_download_failures.py
git add downtify/download_failures.py tests/test_download_failures.py
git commit -m "feat(queue): persist download failures"
```

### Task 2: İndirme yaşam döngüsüne bağlama

**Files:**
- Modify: `main.py`, `downtify/api.py`
- Test: `tests/test_download_failures_api.py`

**Interfaces:**
- Consumes: `DownloadFailureStore`.
- Produces: `api.state.download_failures: Optional[DownloadFailureStore]`.

- [ ] **Step 1: Başarı/hata geçiş testini yaz**

`_run_download` başarısız olduğunda store'da bir kayıt olsun; aynı parça yeniden denemeyle başarılı olunca kayıt çözülsün. Test downloader'ı fake ile enjekte et.

- [ ] **Step 2: Kırmızıyı doğrula**

Run: `docker exec downtify-feature-py uv run pytest tests/test_download_failures_api.py -q`
Expected: FAIL.

- [ ] **Step 3: Store'u başlat**

`main.py` içinde `PendingDownloads` ile aynı `library_db` dosyasında `DownloadFailureStore` oluştur; `api.state` alanını ekle.

- [ ] **Step 4: Hata kaydını ekle**

`_run_download` exception bloğunda `job['status']` ve broadcast'ten sonra store'a `record` çağrısını `asyncio.to_thread` ile ekle. `NoAudioMatchError` için `code='no_audio_match'`, policy hataları için mevcut kod, diğerleri `code='download_failed'`.

- [ ] **Step 5: Başarıda kaydı kapat**

Mevcut dosya nedeniyle atlanan indirme de başarı sayılmalı; `resolve(song_id)` çağır. Gerçek indirme başarılı olduğunda da çağır.

- [ ] **Step 6: Test/lint/commit**

```bash
docker exec downtify-feature-py uv run pytest tests/test_download_failures_api.py tests/test_queue_pause.py -q
docker exec downtify-feature-py uv run ruff check main.py downtify/api.py
docker exec downtify-feature-py uv run ruff format --check main.py downtify/api.py
git add main.py downtify/api.py tests/test_download_failures_api.py
git commit -m "feat(queue): close failures when retries succeed"
```

### Task 3: Başarısızlık merkezi API ve arayüzü

**Files:**
- Create: `downtify/download_failure_routes.py`
- Create: `frontend/src/model/downloadFailures.js`
- Create: `frontend/src/components/queue/FailureCenter.vue`
- Modify: `main.py`, `downtify/auth.py`, `frontend/src/model/api.js`, `frontend/src/views/QueueView.vue`
- Test: `tests/test_download_failure_routes.py`, `frontend/src/__tests__/failureCenter.test.js`
- Modify: `frontend/src/i18n/locales/*.js`

**Interfaces:**
- Produces:
  - `GET /api/download-failures -> {"items": list, "count": int}`
  - `DELETE /api/download-failures -> {"cleared": int}`
  - `POST /api/download-failures/retry {"song_id": "..."} -> {"queued": true, "song_id": "..."}`
  - `useDownloadFailures() -> {items, loading, error, load, retry, clear, dismiss}`

- [ ] **Step 1: API testlerini yaz**

Yetkisiz `401`; normal kullanıcı okuyabilir; retry mevcut download akışını çağırır ve kaydı çözmez (indirme başarılı olunca Task 2 çözer); clear çözülmüş kayıtları siler.

- [ ] **Step 2: Kırmızıyı doğrula ve router'ı ekle**

`main.py` include listesine router ekle; auth kurallarında read `CLIENT`, retry `ADMIN`, clear `ADMIN` yap.

- [ ] **Step 3: Frontend model testini yaz**

Boş yanıt `items=[]`; dolu yanıt song/message/attempts taşır; `retry` doğru endpoint'i çağırır; hata Home/Queue'u kırmaz.

- [ ] **Step 4: Model ve `FailureCenter` bileşenini ekle**

Queue sağ sütununa kalıcı hata listesi ekle: kapak, başlık, hata, deneme sayısı, **Yeniden dene**, **Hariç tut**, **Temizle**. Hariç tut mevcut `excludeDownload` akışını kullanır. `prefers-reduced-motion` statik kalsın.

- [ ] **Step 5: 8 locale key ekle ve test/build koş**

`queue.failureCenterTitle`, `queue.failureCenterHint`, `queue.failureAttempts`, `queue.failureEmpty`, `queue.failureClear` anahtarlarını ekle.

```bash
docker exec downtify-feature-py uv run pytest tests/test_download_failure_routes.py -q
docker exec downtify-feature-node npm test --prefix frontend -- --run src/__tests__/failureCenter.test.js
docker exec downtify-feature-node npm run build --prefix frontend
```

- [ ] **Step 6: Commit**

```bash
git add downtify/download_failure_routes.py frontend/src/model/downloadFailures.js \
  frontend/src/components/queue/FailureCenter.vue frontend/src/model/api.js \
  frontend/src/views/QueueView.vue frontend/src/__tests__/failureCenter.test.js \
  frontend/src/i18n/locales/*.js main.py downtify/auth.py tests/test_download_failure_routes.py
git commit -m "feat(queue): add persistent failure center"
```

### Task 4: Spotify Sync otomatik eksik indirme

**Files:**
- Modify: `downtify/spotify_sync.py`, `downtify/spotify_sync_api.py`, `downtify/api.py`, `main.py`
- Modify: `frontend/src/model/settings.js`, `frontend/src/views/SettingsView.vue`
- Test: `tests/test_spotify_sync.py`, `frontend/src/__tests__/spotifySync.test.js`
- Modify: `frontend/src/i18n/locales/*.js`

**Interfaces:**
- Consumes: mevcut `_missing_tracks_for_playlist` ve `_submit_playlist_batch`.
- Produces: `spotify_sync.auto_download_added` boolean ayarı; sync özetinde `queued_added` sayısı.

- [ ] **Step 1: Ayar ve davranış testlerini yaz**

- `default_settings()` ve `clean_settings()` `auto_download_added=False` döndürsün.
- İlk sync `apply` çağırmaz; otomatik kuyruk oluşmaz.
- Ayar kapalıyken diff `added` kuyruğa alınmaz.
- Ayar açıkken yalnız `added` id'leri missing-track akışına gider.
- Aynı id zaten kuyrukta/idempotent ise ikinci job oluşmaz.

- [ ] **Step 2: Kırmızıyı doğrula**

Run: `docker exec downtify-feature-py uv run pytest tests/test_spotify_sync.py -k auto_download -q`
Expected: FAIL.

- [ ] **Step 3: Ayarı ekle**

`default_settings`, `clean_settings`, `api.DEFAULT_SETTINGS`, frontend default/merge koduna `auto_download_added` ekle.

- [ ] **Step 4: Diff uygulamasını genişlet**

`apply_sync_diff` `added` listesini silmek yerine ayar açıkken ana event loop'a `_queue_missing_for_spotify_playlist(playlist_name, added_ids)` coroutine'ini planla. Yardımcı; verilen id'leri mevcut missing-track çözümleme/kuyruklama yoluna verir, mevcut dosyaları ve kuyruktaki job'ları çıkarır, playlist bağlamını korur. İlk sync zaten `apply` çağırmadığı için mevcut eksikler otomatik inmez.

- [ ] **Step 5: Özet ve UI**

Sync özetine `queued_added` ekle. Settings → Spotify Sync içine **Yeni eklenenleri otomatik indir** switch'i ve açıklama ekle. 8 locale key paritesini koru.

- [ ] **Step 6: Test/build/lint/commit**

```bash
docker exec downtify-feature-py uv run pytest tests/test_spotify_sync.py tests/test_spotify_sync_api.py -q
docker exec downtify-feature-node npm test --prefix frontend -- --run src/__tests__/spotifySync.test.js
docker exec downtify-feature-node npm run build --prefix frontend
docker exec downtify-feature-py uv run ruff check downtify/spotify_sync.py downtify/spotify_sync_api.py
git add downtify/spotify_sync.py downtify/spotify_sync_api.py downtify/api.py main.py \
  frontend/src/model/settings.js frontend/src/views/SettingsView.vue \
  frontend/src/__tests__/spotifySync.test.js frontend/src/i18n/locales/*.js \
  tests/test_spotify_sync.py tests/test_spotify_sync_api.py
git commit -m "feat(sync): auto-download newly added Spotify tracks"
```

### Task 5: Doküman, tam doğrulama ve deploy

**Files:**
- Modify: `README.md`, `docs/features/spotify-sync.md`, `docs/features/download-queue.md`, `docs/api-reference.md`

- [ ] **Step 1: Dokümanı güncelle**

Otomatik indirme opt-in, ilk sync baseline, yalnız sonraki eklemeler; kalıcı hata merkezi ve restart davranışını anlat.

- [ ] **Step 2: Tam kapıları koş**

```bash
docker exec downtify-feature-py uv run pytest -q
docker exec downtify-feature-py uv run ruff check .
docker exec downtify-feature-py uv run ruff format --check .
docker exec downtify-feature-node npm test --prefix frontend -- --maxWorkers=1
docker exec downtify-feature-node npm run build --prefix frontend
docker exec downtify-feature-node npm test --prefix docs
docker exec downtify-feature-node npm run build --prefix docs
```

- [ ] **Step 3: Commit ve deploy**

Doküman commit'ini al, `feat/personal-server-program` dalını `~/downtify` checkout'una fast-forward et, `~/bin/downtify-deploy.sh` çalıştır ve health/container durumunu doğrula.

- [ ] **Step 4: Yol haritasını ilerlet**

Roadmap'da Spotify Sync + başarısızlık merkezi maddesini tamamlandı işaretle; birleşik arama + hızlı kazanımlar alt planını yaz.
