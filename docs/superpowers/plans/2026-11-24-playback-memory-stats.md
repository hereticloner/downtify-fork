# Oynatma Hafızası + Gerçek Stats Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Kullanıcının cihazlar arası kaldığı yerden devam etmesini sağlamak ve heartbeat verisinden dinleme süresi, tamamlama ve atlama metrikleri üretmek.

**Architecture:** Yeni odaklı bir `PlaybackStore` SQLite katmanı mevcut `NowPlaying` canlı görünümünü tamamlar. `POST /api/activity/playback` her raporu kalıcı store'a yazar; yeni `/api/playback/resume` ucu son konumu döndürür. Stats mevcut activity tabanlı panoyu korurken kullanıcı bazlı ölçülmüş metrikler ekler.

**Tech Stack:** Python 3.12+, FastAPI, SQLite, Vue 3, Vitest, Vite.

**Spec:** `docs/superpowers/specs/2026-11-24-personal-server-feature-program-design.md`

## Global Constraints

- Mevcut API yanıtları kırılmaz; yeni alanlar eklenir.
- Yeni kullanıcı metrikleri kullanıcı bazlıdır; admin `scope=server` ile sunucu genelini görür.
- Resume otomatik override yapmaz; kullanıcı cihaz/konum seçer.
- Heartbeat tekrarları ikinci kez sayılmaz; seek/replay çift dinleme üretmez.
- %90 ve üzeri tamamlama; %25 altında veya 15 sn içinde atlama skip sayılır.
- 8 locale key paritesi korunur.
- Palet, tipografi, 0 radius, 2px çizgi ve reduced-motion davranışı değişmez.
- Testler offline olur; dış servis mock/fixture ile doğrulanır.
- Yeni bağımlılık eklenmez.
- Kullanıcı davranışı değiştiği için README + player/stats dokümanları aynı planda güncellenir.

## Review Focus

- **Aynı cihazdan gecikmeli/çift heartbeat:** birikimli saniye yalnız ileri doğru, en fazla 45 sn'lik delta olarak sayılır.
- **Seek ve replay:** seek anındaki sıçrama dinleme saniyesine eklenmez; aynı bölüm yeniden çalındığında süre tekrar sayılmaz.
- **İki cihaz aynı parça:** son konum otomatik olarak bir cihaza zorlanmaz; resume yanıtı cihaz bilgisini taşır.
- **Kullanıcı izolasyonu:** bir kullanıcının konumu/istatistiği diğer kullanıcıya sızmaz; admin sunucu kapsamı ayrı yetkiyle alınır.
- **Eski activity verisi:** yeni ölçüm yoksa mevcut başlangıç sayısı ve heatmap çalışmaya devam eder; eski kayıtlar sıfırlanmaz.

---

### Task 0: Worktree test ortamı ve baseline

**Files:**
- Modify: none
- Create: none
- Test: existing full suites

**Interfaces:**
- Consumes: approved spec and worktree.
- Produces: `downtify-feature-py` ve `downtify-feature-node` konteynerleri; baseline test çıktısı.

- [ ] **Step 1: Worktree ve dalı doğrula**

Run:

```bash
cd ~/downtify/.worktrees/personal-server-program
git branch --show-current
git rev-parse HEAD
git status --short
```

Expected: branch `feat/personal-server-program`; yalnız bu planın dokümanları untracked/modified.

- [ ] **Step 2: Python test konteynerini başlat**

Run:

```bash
docker run -d --name downtify-feature-py \
  -v "$PWD:/work" -w /work python:3.12-slim sleep infinity
docker exec downtify-feature-py sh -c \
  'pip install --no-cache-dir uv==0.5.2 && uv sync --all-extras --dev'
```

Expected: exit 0; `.venv` oluşur.

- [ ] **Step 3: Node test konteynerini başlat**

Run:

```bash
docker run -d --name downtify-feature-node \
  -v "$PWD:/work" -w /work node:26-alpine sleep infinity
docker exec downtify-feature-node npm ci --prefix frontend
docker exec downtify-feature-node npm ci --prefix docs
```

Expected: exit 0; `frontend/node_modules` ve `docs/node_modules` oluşur.

- [ ] **Step 4: Baseline testlerini koş**

Run:

```bash
docker exec downtify-feature-py uv run pytest -q
docker exec downtify-feature-node npm test --prefix frontend
docker exec downtify-feature-node npm run build --prefix frontend
docker exec downtify-feature-node npm test --prefix docs
```

Expected: hepsi yeşil. Mevcut bir fail varsa durup kullanıcıya raporla; tahminle geçme.

- [ ] **Step 5: Plan ve tasarım dokümanlarını commit et**

```bash
git add docs/superpowers/specs/2026-11-24-personal-server-feature-program-design.md \
  docs/superpowers/plans/2026-11-24-personal-server-program-roadmap.md \
  docs/superpowers/plans/2026-11-24-playback-memory-stats.md
git commit -m "docs: plan personal/server feature program"
```

### Task 1: Kalıcı oynatma store'u

**Files:**
- Create: `downtify/playback.py`
- Test: `tests/test_playback.py`

**Interfaces:**
- Consumes: `downtify.sqlite_utils.connect_sqlite`, temizlenmiş track dict.
- Produces:
  - `class PlaybackStore(db_path: Path)`
  - `report(*, user_id: int, device_id: str, player: str, state: str, track: dict[str, Any], position: float, seek: bool = False) -> dict[str, Any]`
  - `latest(user_id: int) -> Optional[dict[str, Any]]`
  - `positions(user_id: int, limit: int = 20) -> list[dict[str, Any]]`
  - `summary(user_id: int, days: int = 30) -> dict[str, Any]`
  - `forget_user(user_id: int) -> int`
  - `prune(days: int = 365) -> int`

- [ ] **Step 1: Şema ve kullanıcı izolasyonu testini yaz**

```python
def test_positions_are_user_scoped(tmp_path):
    store = PlaybackStore(tmp_path / 'playback.db')
    track = {'file': 'A - One.mp3', 'title': 'One', 'duration': 100}
    store.report(
        user_id=1,
        device_id='web',
        player='tab',
        state='paused',
        track=track,
        position=42,
    )
    assert store.latest(1)['position'] == 42
    assert store.latest(2) is None
```

- [ ] **Step 2: Testi çalıştır; kırmızı olduğunu doğrula**

Run: `docker exec downtify-feature-py uv run pytest tests/test_playback.py::test_positions_are_user_scoped -q`
Expected: FAIL, `PlaybackStore` yok.

- [ ] **Step 3: Şemayı oluştur**

`playback_positions`, `playback_events` ve `playback_daily` tablolarını `CREATE TABLE IF NOT EXISTS` ile oluştur. Anahtar `(user_id, device_id, track_key)`; track kimliği `track_id || file`; JSON alanları track/context için. Eski şemalara karşı idempotent migrasyon ekle.

- [ ] **Step 4: Heartbeat birikimi testini yaz**

```python
def test_heartbeats_count_unique_seconds_once(tmp_path):
    store = PlaybackStore(tmp_path / 'playback.db')
    track = {'file': 'A - One.mp3', 'duration': 200}
    for position in (0, 30, 60):
        store.report(
            user_id=1,
            device_id='web',
            player='tab',
            state='playing',
            track=track,
            position=position,
        )
    assert store.summary(1)['seconds'] == 60
    assert store.summary(1)['plays'] == 1
```

- [ ] **Step 5: Testi çalıştır; kırmızı olduğunu doğrula**

Run: `docker exec downtify-feature-py uv run pytest tests/test_playback.py::test_heartbeats_count_unique_seconds_once -q`
Expected: FAIL.

- [ ] **Step 6: `report` mantığını uygula**

Aynı track/device için önceki satırı oku. `state=playing`, önceki durum `playing`, `seek=False` ve `0 < delta <= 45` ise delta saniyeyi ekle. Yeni track'te `plays += 1`; `%90` tamamlanmada bir kez `completions += 1`; önceki track `%25` altında veya 15 sn altında bırakıldıysa `skips += 1`. Her raporda konumu upsert et; olayları yalnız anlamlı geçişlerde yaz.

- [ ] **Step 7: Seek, tamamlama ve skip testlerini yaz ve çalıştır**

Testler:
- `0 → seek(120) → 150` toplam saniye `30`.
- `duration=100`, `position=95` tamamlama `1`; tekrar `95` tamamlama yine `1`.
- `duration=100`, `0`'dan 5 sn sonra `stopped position=10` skip `1`.
- `summary(days=7/30/90)` seçilen gün penceresine uyar.

Run: `docker exec downtify-feature-py uv run pytest tests/test_playback.py -q`
Expected: PASS.

- [ ] **Step 8: `latest`, `positions`, `forget_user`, `prune` testlerini ekle**

`latest` en yeni güncellenen kullanıcı kaydını döndürür; `positions` cihaz/parça listesini verir; `forget_user` tüm kullanıcı satırlarını siler; `prune` eski event/daily/position kayıtlarını siler.

- [ ] **Step 9: Store test paketini ve lint'i koş**

```bash
docker exec downtify-feature-py uv run pytest tests/test_playback.py -q
docker exec downtify-feature-py uv run ruff check downtify/playback.py tests/test_playback.py
docker exec downtify-feature-py uv run ruff format --check downtify/playback.py tests/test_playback.py
```

Expected: PASS.

- [ ] **Step 10: Commit**

```bash
git add downtify/playback.py tests/test_playback.py
git commit -m "feat(playback): persist cross-device listening state"
```

### Task 2: Playback API ve auth entegrasyonu

**Files:**
- Create: `downtify/playback_routes.py`
- Modify: `main.py`, `downtify/api.py`, `downtify/account_routes.py`, `downtify/auth.py`
- Test: `tests/test_playback_api.py`

**Interfaces:**
- Consumes: `PlaybackStore`, `clean_track`, `api.principal_of`.
- Produces:
  - `GET /api/playback/resume -> {"track": dict | None, "position": float, "duration": float, "device_id": str, "player": str, "updated_at": str}`
  - `GET /api/playback/positions -> {"items": list[dict]}`
  - `api.state.playback: Optional[PlaybackStore]`

- [ ] **Step 1: Resume uç testini yaz**

İki cihaz raporu gönder; `GET /api/playback/resume` son güncelleneni döndürsün. Başka kullanıcının token'ı ile istek atıldığında o kullanıcının kendi boş sonucu dönsün. Yetkisiz istek `401`.

- [ ] **Step 2: Testi çalıştır; kırmızı olduğunu doğrula**

Run: `docker exec downtify-feature-py uv run pytest tests/test_playback_api.py -q`
Expected: FAIL, route yok.

- [ ] **Step 3: Store'u başlat ve state'e bağla**

`main.py` içinde `ActivityLog` yanında `PlaybackStore(DATABASE_DIR / 'downtify_activity.db')` oluştur; `api.state.playback` alanını ekle; router'ı `main.py` include listesine ekle.

- [ ] **Step 4: Auth kurallarını ekle**

`GET /api/playback/resume` ve `GET /api/playback/positions` için `CLIENT` kuralı ekle. Route testindeki "her route sınıflandırılmış" kontrolünü geçir.

- [ ] **Step 5: Mevcut playback raporunu kalıcılaştır**

`account_routes.report_playback` içinde `now_playing.report` sonrası `playback.report(...)` çağrısını `asyncio.to_thread` ile ekle. `seek_requested`, `device_id`, `player`, `track`, `position` ve `state` değerlerini aktar. Bildirim/scrobble/mirror davranışı değişmez.

- [ ] **Step 6: Resume/positions uçlarını uygula**

`_me(request)` ile kullanıcıyı al; store'dan kullanıcı bazlı sonuç döndür. Track yoksa `track: null` ve sıfır alanlar döndür. Hassas alan (IP, çerez, token) döndürme.

- [ ] **Step 7: Kullanıcı silme/logout temizliğini ekle**

`forget_user` çağrılarını kullanıcı silme akışına ekle; logout'ta son konum korunur, hesap silinince konum silinir.

- [ ] **Step 8: API test paketini koş**

```bash
docker exec downtify-feature-py uv run pytest tests/test_playback_api.py tests/test_users.py tests/test_auth.py -q
docker exec downtify-feature-py uv run ruff check downtify/playback_routes.py downtify/account_routes.py downtify/auth.py main.py
docker exec downtify-feature-py uv run ruff format --check downtify/playback_routes.py downtify/account_routes.py downtify/auth.py main.py
```

Expected: PASS.

- [ ] **Step 9: Commit**

```bash
git add downtify/playback_routes.py main.py downtify/api.py \
  downtify/account_routes.py downtify/auth.py tests/test_playback_api.py
git commit -m "feat(api): expose cross-device playback resume"
```

### Task 3: Kullanıcı bazlı ölçülmüş Stats

**Files:**
- Modify: `downtify/stats.py`, `downtify/collections_api.py`
- Test: `tests/test_api_stats.py`

**Interfaces:**
- Consumes: `PlaybackStore.summary`, `ActivityLog.entries(user_id=...)`.
- Produces:
  - `build_stats(..., user_id: int = 0, days: int = 30, playback: Any = None)`
  - `GET /api/stats?days=7|30|90&scope=user|server`
  - `playback.measured = {"seconds": int, "plays": int, "completions": int, "skips": int, "completion_rate": float, "skip_rate": float}`

- [ ] **Step 1: Kullanıcı izolasyonu testini yaz**

İki kullanıcı için playback kaydı oluştur. Admin olmayan kullanıcının `/api/stats` yanıtı yalnız kendi `measured.plays` değerini içersin. Admin `scope=server` iki kullanıcının toplamını görsün.

- [ ] **Step 2: Testi çalıştır; kırmızı olduğunu doğrula**

Run: `docker exec downtify-feature-py uv run pytest tests/test_api_stats.py -k user_scoped -q`
Expected: FAIL.

- [ ] **Step 3: Activity sorgularını kullanıcı bazlı yap**

`_activity_kinds(log, kind, user_id=0)` içine `user_id` filtresi ekle. `build_stats` yeni `user_id`, `days`, `playback` parametrelerini kabul etsin. `days` değerini `7/30/90` arasına sabitle; geçersiz değer `30` olsun.

- [ ] **Step 4: Ölçülmüş metrikleri ekle**

`playback.summary(user_id, days)` sonucunu `playback.measured` altında döndür. Oranlar `plays=0` iken `0.0` olsun. Mevcut `total`, `heatmap`, `recent`, `top_contexts` alanları geriye uyumluluk için kalsın.

- [ ] **Step 5: Stats uçlarını kullanıcı/scope bilgisine göre bağla**

`collections_api.stats_endpoint` `_me` benzeri principal okusun; varsayılan `scope=user`. `scope=server` yalnız admin. Auth kurallarına `GET /api/stats` için `CLIENT` kuralı ekle. Store yoksa eski boş yanıt korunur.

- [ ] **Step 6: Eski activity ve boş store testlerini koş**

Mevcut tüm `tests/test_api_stats.py` testleri geçmeli; yeni measured alanı eski şekil testlerini kırmamalı.

- [ ] **Step 7: lint ve commit**

```bash
docker exec downtify-feature-py uv run pytest tests/test_api_stats.py -q
docker exec downtify-feature-py uv run ruff check downtify/stats.py downtify/collections_api.py downtify/auth.py
docker exec downtify-feature-py uv run ruff format --check downtify/stats.py downtify/collections_api.py downtify/auth.py
git add downtify/stats.py downtify/collections_api.py downtify/auth.py tests/test_api_stats.py
git commit -m "feat(stats): add user-scoped listening metrics"
```

### Task 4: Ana ekranda cihazlar arası devam et

**Files:**
- Create: `frontend/src/model/resume.js`
- Create: `frontend/src/components/library/ResumeCard.vue`
- Modify: `frontend/src/model/api.js`, `frontend/src/model/player.js`, `frontend/src/views/HomeView.vue`
- Test: `frontend/src/__tests__/resume.test.js`, `frontend/src/__tests__/player.test.js`

**Interfaces:**
- Consumes: `GET /api/playback/resume`, `normalizeTrack`.
- Produces:
  - `API.getResume()`
  - `useResume() -> {item, loading, error, load, dismiss}`
  - `player.resumeTrack(track, position) -> Promise<void>`

- [ ] **Step 1: API ve resume model testlerini yaz**

`getResume` boş yanıtı `item=null` yapar; dolu yanıtta `file/title/artist/position/duration/device_id` alanlarını korur. `dismiss` yalnız bu oturumda kartı kapatır.

- [ ] **Step 2: Testleri çalıştır; kırmızı olduğunu doğrula**

Run: `docker exec downtify-feature-node npm test --prefix frontend -- --run src/__tests__/resume.test.js`
Expected: FAIL.

- [ ] **Step 3: API ve modeli ekle**

`api.js` içine `getResume` ekle. `resume.js` Vue `ref` store'u oluştur; `load` hatalarını sessizce `error` olarak işaretler.

- [ ] **Step 4: Player'a `resumeTrack` ekle**

`setPlaylist([track], {startIndex: 0, context: resume context})` çağır, `restoreTime=position` ayarla ve metadata yüklendiğinde mevcut `loadedmetadata` yoluyla konumu uygula. Kullanıcı tıklaması olmadan otomatik çalma başlatma.

- [ ] **Step 5: ResumeCard bileşenini ekle**

Kapak, başlık, sanatçı, cihaz adı, ilerleme çubuğu ve "Devam et" düğmesi göster. `prefers-reduced-motion` statik kalsın. Mevcut `CoverArt`, `UiButton`, `UiProgress` bileşenlerini kullan.

- [ ] **Step 6: Home'e bağla**

`HomeView` mount'ta `resume.load()` çağırsın. Kart yalnız `item.track` varsa görünsün. Tıklama `player.resumeTrack(item.track, item.position)` çağırsın ve `resume.dismiss()` yapsın.

- [ ] **Step 7: 8 locale key ekle**

`home.resumeTitle`, `home.resumeAction`, `home.resumeOnDevice`, `home.resumeEmpty` (boş durum kartı gösterilmediği için metin yine de parite için eklenir) anahtarlarını 8 locale dosyasına ekle.

- [ ] **Step 8: Player ve resume testlerini koş**

```bash
docker exec downtify-feature-node npm test --prefix frontend -- --run \
  src/__tests__/resume.test.js src/__tests__/player.test.js
docker exec downtify-feature-node npm run build --prefix frontend
```

Expected: PASS.

- [ ] **Step 9: Commit**

```bash
git add frontend/src/model/resume.js frontend/src/components/library/ResumeCard.vue \
  frontend/src/model/api.js frontend/src/model/player.js frontend/src/views/HomeView.vue \
  frontend/src/__tests__/resume.test.js frontend/src/__tests__/player.test.js \
  frontend/src/i18n/locales/*.js
git commit -m "feat(ui): offer cross-device resume from home"
```

### Task 5: Stats dönem seçici ve ölçülmüş metrikler

**Files:**
- Modify: `frontend/src/model/stats.js`, `frontend/src/views/StatsView.vue`, `frontend/src/model/api.js`
- Test: `frontend/src/__tests__/statsViewClientRender.test.js`, yeni `frontend/src/__tests__/statsPeriod.test.js`
- Modify: `frontend/src/i18n/locales/*.js`

**Interfaces:**
- Consumes: `GET /api/stats?days=...`.
- Produces:
  - `useStats() -> {stats, loading, error, days, load}`
  - `API.getStats({days, scope})`

- [ ] **Step 1: Dönem ve metrik testlerini yaz**

`days` varsayılan `30`; 7/90 seçimlerinde `API.getStats` doğru query ile çağrılır. Dinleme süresi `3661` sn için `1:01:01`; tamamlama ve skip oranları yüzdeye çevrilir.

- [ ] **Step 2: Testleri çalıştır; kırmızı olduğunu doğrula**

Run: `docker exec downtify-feature-node npm test --prefix frontend -- --run src/__tests__/statsPeriod.test.js`
Expected: FAIL.

- [ ] **Step 3: Modeli güncelle**

`stats.js` içine `days = ref(30)` ekle; `load` `API.getStats({days: days.value, scope:'user'})` çağırsın. `api.js` query parametrelerini iletin.

- [ ] **Step 4: StatsView'e seçici ekle**

`PageHeader` yanına `UiSegmented` ile `7 / 30 / 90` seçeneği ekle. Seçim değişince `load()` çalışsın. Metric strip'e `Dinleme süresi`, `Tamamlanan`, `Atlanan` alanlarını ekle; grid 8 sütuna genişlet.

- [ ] **Step 5: 8 locale key ekle**

`stats.period7`, `stats.period30`, `stats.period90`, `stats.listeningTime`, `stats.completed`, `stats.skipped`, `stats.completionRate`, `stats.skipRate` anahtarlarını ekle.

- [ ] **Step 6: Test/build/format koş**

```bash
docker exec downtify-feature-node npm test --prefix frontend -- --run \
  src/__tests__/statsPeriod.test.js src/__tests__/statsViewClientRender.test.js
docker exec downtify-feature-node npm run build --prefix frontend
docker exec downtify-feature-node npx prettier --check \
  src/model/stats.js src/views/StatsView.vue src/model/api.js \
  src/__tests__/statsPeriod.test.js src/i18n/locales/*.js
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/model/stats.js frontend/src/views/StatsView.vue \
  frontend/src/model/api.js frontend/src/__tests__/statsPeriod.test.js \
  frontend/src/__tests__/statsViewClientRender.test.js frontend/src/i18n/locales/*.js
git commit -m "feat(stats): add period and measured listening metrics"
```

### Task 6: Doküman, tam doğrulama ve deploy

**Files:**
- Modify: `README.md`, `docs/features/player.md`, `docs/features/stats.md`, `docs/api-reference.md`
- Test: full suites

**Interfaces:**
- Consumes: Tasks 1–5.
- Produces: dokümanlı, test edilmiş ve canlıya alınmış oynatma hafızası.

- [ ] **Step 1: Kullanıcı dokümanını güncelle**

Resume'ın cihaz seçimi, otomatik override olmaması, heartbeat sayım kuralları ve 7/30/90 dönem seçiciyi anlat. API yanıtlarını `docs/api-reference.md` içine ekle.

- [ ] **Step 2: Tam backend/frontend/docs kapılarını koş**

```bash
docker exec downtify-feature-py uv run pytest -q
docker exec downtify-feature-py uv run ruff check .
docker exec downtify-feature-py uv run ruff format --check .
docker exec downtify-feature-node npm test --prefix frontend
docker exec downtify-feature-node npm run build --prefix frontend
docker exec downtify-feature-node npm test --prefix docs
docker exec downtify-feature-node npm run build --prefix docs
docker exec downtify-feature-node npm run format:check --prefix frontend
```

Expected: hepsi yeşil. Repo-geneli bilinen format sorunu varsa yalnız değişen dosyaların temiz olduğunu ayrıca doğrula ve kullanıcıya bildir.

- [ ] **Step 3: Commit**

```bash
git add README.md docs/features/player.md docs/features/stats.md docs/api-reference.md
git commit -m "docs: describe playback memory and listening stats"
```

- [ ] **Step 4: Worktree dalını ana checkout'a fast-forward et**

```bash
git -C ~/downtify merge --ff-only feat/personal-server-program
git -C ~/downtify log --oneline -1
```

Expected: ana checkout HEAD worktree HEAD ile aynı.

- [ ] **Step 5: Deploy et**

Run: `~/bin/downtify-deploy.sh`

Expected: health `{"status":"ok","version":"4.0.0"}`, container healthy.

- [ ] **Step 6: Canlı uçları doğrula**

Girişli tarayıcı yoksa API testini geçici test kullanıcısıyla veya mevcut oturumla çalıştır; `GET /api/playback/resume` ve `GET /api/stats?days=30` yanıtlarını ölç. Giriş yapılamıyorsa bunu açıkça "doğrulanmadı" yaz.

- [ ] **Step 7: Bu planın kutusunu işaretle ve sıradaki alt planı yaz**

Roadmap'daki ilk maddeyi tamamlandı işaretle; Spotify Sync + başarısızlık merkezi alt planını oluştur.
