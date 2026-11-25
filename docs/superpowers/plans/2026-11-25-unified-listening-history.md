# Birleştirilmiş Dinleme Geçmişi Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Downtify, Spotify ve Last.fm play'larını ham gövdeleri koruyarak tek bir kalıcı canonical dinleme günlüğünde birleştirmek ve Stats'ta bir kez saymak.

**Architecture:** Ham Spotify/Last.fm gözlemleri kendi tablolarında tutulur; `ListeningStore` bunları kaynak önceliği ve zaman penceresiyle `listening_events` tablosuna bağlar. Stats yalnız canonical tabloyu okur; ölçülmüş süre/completion/skip yine `PlaybackStore` kalır.

**Tech Stack:** Python 3.12, FastAPI, SQLite, httpx, loguru; Vue 3, Vitest; mevcut Docker test konteynerleri.

**Spec:** `docs/superpowers/specs/2026-11-25-unified-listening-history-design.md`

## Global Constraints

- Kişisel/sunucu indirici ve oynatıcı; per-user kütüphaneler, dış paylaşım, OIDC, yeni ses kaynağı, PostgreSQL ve tam upstream merge kapsam dışı.
- v4 kimliği, reduced-motion davranışı, API uyumu, 8 dil paritesi ve port `8000` korunur.
- Mevcut FastAPI + Vue 3 + SQLite/JSON mimarisi korunur; yeni bağımlılık eklenmez.
- Testler offline olacak; dış servisler fixture/mock ile doğrulanır.
- Her yeni kullanıcı davranışı önce kırmızı testle yazılır; her görev ayrı commit alır.
- Büyük dosya yazımları atomik olur; token içeren dosyalar `0600` kalır.
- Çalışma dalı `feat/personal-server-program`; tamamlanan dalga ana repodaki `feat/collections` ile fast-forward merge edilir.
- Repo OpenCode konteynerinde mount değil; tüm git/test komutları `ssh home` üzerinden çalışır. Commit blokları host worktree içinde yürütülür.
- Deploy yalnız `ssh home '~/bin/downtify-deploy.sh'` ile yapılır; deploy sonrası HEAD, `/api/health` ve container health doğrulanır.
- Rollback imajı: `downtify-fork:pre-v4`.

## Review Focus

- Aynı play Downtify + Spotify + Last.fm'den gelirse tek canonical satır üretmeli; kaynak yükseltmesi yeniden importta ikinci satır açmamalı.
- Last.fm scrobble zamanı gün sınırına denk gelip sonra Downtify/Spotify zamanı gelirse ısı haritası doğru güne taşınmalı.
- Aynı kaynaktan eşleşme penceresi içindeki ikinci gerçek play yeni canonical satır açmalı; birincine absorbe edilmemeli.
- Eski Spotify şemasından migration mevcut kayıtları kaybetmeden çalışmalı; aynı saniyedeki iki farklı parça korunmalı.
- 98 bin kayıtlık Last.fm backfill'i hata/restart sonrası idempotent devam etmeli; 429 veya yarım sayfa sayaçları bozmamalı.

---

### Task 1: Canonical listening store ve dedupe çekirdeği

**Files:**
- Create: `downtify/listening_history.py`
- Create: `tests/test_listening_history.py`

**Interfaces:**
- Produces:
  - `normalize_match_key(artist: str, title: str) -> str`
  - `source_priority(source: str) -> int`
  - `ListeningStore(db_path: Path)`
  - `ListeningStore.link_or_create(*, user_id: int, source: str, source_key: str, played_at: str, title: str, artist: str, album: str = '', spotify_track_id: str = '', duration_ms: int = 0, context: str = '', context_type: str = '') -> tuple[int, bool]`
  - `ListeningStore.stats(user_id: int = 0, recent_limit: int = 400) -> dict[str, Any]`
  - `ListeningStore.forget_user(user_id: int) -> int`

- [ ] **Step 1: Write failing tests**

`tests/test_listening_history.py` şu davranışları sabitler:

```python
def test_same_source_is_idempotent(tmp_path):
    store = ListeningStore(tmp_path / 'activity.db')
    first, created = store.link_or_create(
        user_id=1, source='spotify', source_key='spotify:1',
        played_at='2026-11-25T20:15:00Z', artist='A', title='T',
    )
    again, created_again = store.link_or_create(
        user_id=1, source='spotify', source_key='spotify:1',
        played_at='2026-11-25T20:15:00Z', artist='A', title='T',
    )
    assert (first, created, again, created_again) == (1, True, 1, False)


def test_higher_priority_promotes_without_changing_identity(tmp_path):
    store = ListeningStore(tmp_path / 'activity.db')
    event_id, _ = store.link_or_create(
        user_id=1, source='lastfm', source_key='lastfm:1',
        played_at='2026-11-25T23:59:30Z', artist='A', title='T',
    )
    promoted, created = store.link_or_create(
        user_id=1, source='downtify', source_key='activity:9',
        played_at='2026-11-25T23:56:00Z', artist='A', title='T',
        spotify_track_id='spotify-1',
    )
    row = store.stats(user_id=1)['recent'][0]
    assert (promoted, created) == (event_id, False)
    assert row['source'] == 'downtify'
    assert row['at'] == '2026-11-25T23:56:00Z'


def test_same_source_second_observation_is_a_new_play(tmp_path):
    store = ListeningStore(tmp_path / 'activity.db')
    store.link_or_create(
        user_id=1, source='spotify', source_key='spotify:1',
        played_at='2026-11-25T20:15:00Z', artist='A', title='T',
    )
    second, created = store.link_or_create(
        user_id=1, source='spotify', source_key='spotify:2',
        played_at='2026-11-25T20:20:00Z', artist='A', title='T',
    )
    assert created is True
    assert second != 1
    assert store.stats(user_id=1)['total'] == 2


def test_stats_are_user_scoped_and_sql_aggregated(tmp_path):
    store = ListeningStore(tmp_path / 'activity.db')
    store.link_or_create(
        user_id=1, source='spotify', source_key='s1',
        played_at='2026-11-25T20:15:00Z', artist='A', title='T',
        context='Mix', context_type='playlist',
    )
    store.link_or_create(
        user_id=2, source='lastfm', source_key='l1',
        played_at='2026-11-25T21:15:00Z', artist='B', title='U',
    )
    assert store.stats(user_id=1)['total'] == 1
    assert store.stats(user_id=0)['total'] == 2
    assert store.stats(user_id=1)['recent'][0]['source'] == 'spotify'
```

Ayrıca `forget_user` için kullanıcının canonical satır ve kaynak bağlantılarının silindiği testi yazılır.

- [ ] **Step 2: Run tests to verify RED**

Run: `ssh home 'docker exec -e PYTHONDONTWRITEBYTECODE=1 downtify-feature-py sh -c "cd /work && .venv/bin/python -m pytest -p no:cacheprovider tests/test_listening_history.py -q"'`

Expected: `ModuleNotFoundError: downtify.listening_history`.

- [ ] **Step 3: Implement `downtify/listening_history.py`**

`listening_events`, `listening_event_sources` ve indeksleri oluştur. `link_or_create` transaction içinde normalize anahtar + zaman penceresi adaylarını arar; `listening_event_sources` aynı kaynağın ikinci bağlanmasını engeller; daha yüksek öncelik gelirse `source/source_key/played_at/metadata` alanlarını yükseltir, `identity_key` değişmez. `stats` SQLite aggregate döndürür: `total`, `top_tracks`, `daily`, `recent`, `top_contexts`.

- [ ] **Step 4: Run tests to verify GREEN**

Run: Step 2 komutu.
Expected: tüm testler PASS.

- [ ] **Step 5: Commit**

```bash
git add downtify/listening_history.py tests/test_listening_history.py
git commit -m "feat(stats): add canonical listening history store"
```

---

### Task 2: Spotify ham payload, migration ve canonical bağlama

**Files:**
- Modify: `downtify/spotify_history.py`
- Modify: `tests/test_spotify_history.py`

**Interfaces:**
- Consumes: Task 1 `ListeningStore.link_or_create`.
- Produces:
  - `parse_plays(body: Any) -> list[dict[str, Any]]` artık `raw_item`, `isrc`, `context` taşır.
  - `save_recently_played(db_path: Any, rows: Any, *, user_id: int = 0) -> int`
  - `link_pending(db_path: Any, listening: Any, *, user_id: int = 0, limit: int = 500) -> int`
  - `run_once(settings: Any, db_path: Any, *, limit: int = 50, request: Optional[Request] = None, user_id: int = 0, listening: Any = None) -> dict[str, Any]`
  - `spotify_history_loop(..., listening_getter: Optional[Callable[[], Any]] = None, user_id_getter: Optional[Callable[[], int]] = None)`

- [ ] **Step 1: Write failing tests**

Mevcut parse testlerini zengin alanlara göre genişlet ve şu migration/dedupe testlerini ekle:

```python
def test_old_spotify_table_migrates_without_losing_rows(tmp_path):
    db = tmp_path / 'activity.db'
    with sqlite3.connect(db) as conn:
        conn.execute(
            'CREATE TABLE spotify_recently_played ('
            'played_at TEXT PRIMARY KEY, track_name TEXT NOT NULL, '
            'artist_name TEXT NOT NULL, album_name TEXT NOT NULL, '
            'spotify_track_id TEXT NOT NULL, duration_ms INTEGER NOT NULL, '
            'synced_at TEXT NOT NULL)'
        )
        conn.execute(
            'INSERT INTO spotify_recently_played VALUES (?,?,?,?,?,?,?)',
            ('2026-11-25T20:15:00Z', 'T', 'A', 'Album', 's1', 1000, 'now'),
        )
    assert spotify_history.save_recently_played(db, [], user_id=1) == 0
    rows = spotify_history.get_recent_from_spotify(db)
    assert len(rows) == 1
    assert rows[0]['user_id'] == 1
    assert rows[0]['raw_json'] == '{}'


def test_same_second_different_tracks_survive(tmp_path):
    rows = [
        {'played_at': '2026-11-25T20:15:00Z', 'spotify_track_id': 's1',
         'track_name': 'T1', 'artist_name': 'A'},
        {'played_at': '2026-11-25T20:15:00Z', 'spotify_track_id': 's2',
         'track_name': 'T2', 'artist_name': 'A'},
    ]
    assert spotify_history.save_recently_played(tmp_path / 'activity.db', rows) == 2
    assert spotify_history.count_plays(tmp_path / 'activity.db') == 2


def test_raw_payload_and_pending_link_are_idempotent(tmp_path):
    db = tmp_path / 'activity.db'
    raw = {'id': 's1', 'external_ids': {'isrc': 'USAAA1200001'}}
    rows = [{'played_at': '2026-11-25T20:15:00Z', 'spotify_track_id': 's1',
             'track_name': 'T', 'artist_name': 'A', 'raw_item': raw,
             'isrc': 'USAAA1200001'}]
    assert spotify_history.save_recently_played(db, rows, user_id=1) == 1
    listening = ListeningStore(db)
    assert spotify_history.link_pending(db, listening, user_id=1) == 1
    assert spotify_history.link_pending(db, listening, user_id=1) == 0
    assert listening.stats(user_id=1)['total'] == 1
    assert json.loads(spotify_history.get_recent_from_spotify(db)[0]['raw_json']) == raw
```

- [ ] **Step 2: Run tests to verify RED**

Run: `ssh home 'docker exec -e PYTHONDONTWRITEBYTECODE=1 downtify-feature-py sh -c "cd /work && .venv/bin/python -m pytest -p no:cacheprovider tests/test_spotify_history.py -q"'`

Expected: yeni alan/migration/link testleri FAIL.

- [ ] **Step 3: Implement Spotify migration ve bağlama**

Eski tabloyu transaction içinde yeni `id/user_id/source_key/listening_event_id/isrc/context_json/raw_json` şemasına taşı. `source_key=spotify:{played_at}:{track_id}` kullan. Eski satırlar `save_recently_played(..., user_id=<first admin id>)` çağrısıyla taşınır. Parser ham `item` objesini JSON olarak saklar. `save_recently_played` boş liste geldiğinde de `_connect` çağırarak migration'ın çalışmasını sağlar; ham gözlemleri yazar. `link_pending` yalnız `listening_event_id IS NULL` satırları canonical store'a bağlar. `run_once` kaydetme sonrası pending satırları bağlar. `main.py` loop'a `user_id_getter` olarak `api.state.auth.users.first_admin()` id'sini verir.

- [ ] **Step 4: Run tests to verify GREEN**

Run: Step 2 komutu.
Expected: tüm Spotify history testleri PASS.

- [ ] **Step 5: Commit**

```bash
git add downtify/spotify_history.py tests/test_spotify_history.py
git commit -m "feat(stats): persist raw Spotify plays and link history"
```

---

### Task 3: Last.fm okuma, backfill ve arka plan döngüsü

**Files:**
- Create: `downtify/lastfm_history.py`
- Create: `tests/test_lastfm_history.py`
- Modify: `downtify/api.py`
- Modify: `main.py`
- Modify: `tests/test_scrobbling.py`

**Interfaces:**
- Consumes: Task 1 `ListeningStore.link_or_create`.
- Produces:
  - `import_enabled(settings: Any) -> bool`
  - `read_config(settings: Any) -> Optional[dict[str, str]]`
  - `fetch_recent_tracks(config: dict[str, str], *, from_uts: Optional[int] = None, to_uts: Optional[int] = None, page: int = 1, limit: int = 200, request: Optional[Callable[..., Any]] = None) -> Optional[dict[str, Any]]`
  - `parse_plays(body: Any) -> list[dict[str, Any]]`
  - `save_recent_tracks(db_path: Any, rows: Any, *, user_id: int = 0) -> int`
  - `count_plays(db_path: Any) -> int`
  - `link_pending(db_path: Any, listening: Any, *, user_id: int = 0, limit: int = 500) -> int`
  - `run_once(settings: Any, db_path: Any, *, listening: Any = None, user_id: int = 0, max_pages: int = 20, request: Optional[Callable[..., Any]] = None) -> dict[str, Any]`
  - `lastfm_history_loop(cfg_getter: Callable[[], Any], db_path: Any, *, listening_getter: Optional[Callable[[], Any]] = None, user_id_getter: Optional[Callable[[], int]] = None, idle_seconds: float = 900, max_pages: int = 20, request: Optional[Callable[..., Any]] = None)`

- [ ] **Step 1: Write failing tests**

```python
def test_fetch_uses_public_read_params_and_skips_nowplaying():
    calls = []
    def sender(method, url, **kwargs):
        calls.append((method, url, kwargs))
        return FakeResponse({'recenttracks': {'track': [
            {'name': 'T', 'artist': {'name': 'A'}, 'date': {'uts': '1'},
             'nowplaying': 'true'},
            {'name': 'U', 'artist': {'name': 'B'}, 'date': {'uts': '2'}},
        ]}})
    body = lastfm_history.fetch_recent_tracks(
        {'api_key': 'k', 'username': 'u'}, from_uts=10, to_uts=20,
        limit=200, request=sender,
    )
    params = calls[0][2]['params']
    assert params == {'method': 'user.getRecentTracks', 'user': 'u',
                      'api_key': 'k', 'format': 'json', 'limit': 200,
                      'from': 10, 'to': 20, 'extended': 1}
    assert [row['track_name'] for row in lastfm_history.parse_plays(body)] == ['U']


def test_backfill_resumes_from_oldest_and_catches_up_newest(tmp_path):
    newest_page = {'recenttracks': {'@attr': {'totalPages': '2'}, 'track': [
        {'name': 'New', 'artist': {'name': 'A'}, 'date': {'uts': '200'}},
        {'name': 'Old', 'artist': {'name': 'A'}, 'date': {'uts': '100'}},
    ]}}
    older_page = {'recenttracks': {'track': [
        {'name': 'Older', 'artist': {'name': 'A'}, 'date': {'uts': '50'}},
    ]}}
    def sender(method, url, **kwargs):
        params = kwargs['params']
        if params.get('from') is not None:
            return FakeResponse({'recenttracks': {'track': []}})
        if params.get('to') is not None:
            return FakeResponse(older_page)
        return FakeResponse(newest_page)
    settings = {'scrobbling': {'enabled': True, 'lastfm_enabled': True,
                'lastfm_api_key': 'k', 'lastfm_username': 'u',
                'import_history': True}}
    db = tmp_path / 'activity.db'
    first = lastfm_history.run_once(settings, db, max_pages=1, request=sender)
    second = lastfm_history.run_once(settings, db, max_pages=1, request=sender)
    assert first['saved'] == 2
    assert second['saved'] == 1
    assert lastfm_history.count_plays(db) == 3
```

Ayrıca ham track objesinin saklandığı, aynı saniyelik iki gerçek scrobble için occurrence anahtarı üretildiği, `link_pending` idempotent olduğu ve 429/16 durumunda cursor ilerlemediği testleri yazılır.

- [ ] **Step 2: Run tests to verify RED**

Run: `ssh home 'docker exec -e PYTHONDONTWRITEBYTECODE=1 downtify-feature-py sh -c "cd /work && .venv/bin/python -m pytest -p no:cacheprovider tests/test_lastfm_history.py tests/test_scrobbling.py -q"'`

Expected: `ModuleNotFoundError` ve `import_history` ayar testleri FAIL.

- [ ] **Step 3: Implement Last.fm importer ve ayar**

`lastfm_recent_tracks` ve `history_import_state` tablolarını oluştur. GET isteğinde `api_key/user/method/format/limit/from/to/extended` kullan; imza veya session key kullanma. `nowplaying` ve tarihsiz kayıtları atla. Her koşuda önce `newest_at` sonrasını, sonra `backfill_done=false` ise `oldest_at` öncesini en fazla `max_pages` sayfa çek; her sayfadan sonra cursor'ı commit et. `api.DEFAULT_SETTINGS['scrobbling']` içine `import_history: False` ekle; `_clean_scrobbling` alanı korur. `main.py` içine 15 dakikalık loop'i ekle; `user_id_getter` ilk admin id'sini verir.

- [ ] **Step 4: Run tests to verify GREEN**

Run: Step 2 komutu.
Expected: tüm Last.fm history ve mevcut scrobbling testleri PASS.

- [ ] **Step 5: Commit**

```bash
git add downtify/lastfm_history.py tests/test_lastfm_history.py downtify/api.py main.py tests/test_scrobbling.py
git commit -m "feat(stats): import resumable Last.fm listening history"
```

---

### Task 4: Downtify köprüsü ve birleşik Stats API

**Files:**
- Modify: `downtify/activity.py`
- Modify: `downtify/account_routes.py`
- Modify: `downtify/api.py`
- Modify: `main.py`
- Modify: `downtify/collections_api.py`
- Modify: `downtify/stats.py`
- Modify: `tests/test_api_stats.py`
- Create: `tests/test_listening_stats_api.py`

**Interfaces:**
- Consumes: Task 1 `ListeningStore.stats/backfill_activity`, Task 2/3 import yolları.
- Produces:
  - `ActivityLog.record(...) -> int`
  - `ListeningStore.backfill_activity(activity: Any) -> int`
  - `build_stats(..., listening_stats: Optional[dict[str, Any]] = None, ...)`
  - `AppState.listening: Optional[Any]`

- [ ] **Step 1: Write failing API tests**

```python
def test_stats_counts_spotify_and_lastfm_without_faking_measured_time(client):
    listening = api.state.listening
    listening.link_or_create(
        user_id=1, source='spotify', source_key='s1',
        played_at='2026-11-25T20:15:00Z', artist='A', title='T',
    )
    listening.link_or_create(
        user_id=1, source='lastfm', source_key='l1',
        played_at='2026-11-25T21:15:00Z', artist='B', title='U',
    )
    data = client.get('/api/stats').json()['playback']
    assert data['total'] == 2
    assert {row['source'] for row in data['recent']} == {'spotify', 'lastfm'}
    assert data['measured']['seconds'] == 0
    assert data['measured']['plays'] == 0


def test_downtify_spotify_lastfm_same_play_is_one_event(client):
    listening = api.state.listening
    listening.link_or_create(
        user_id=1, source='downtify', source_key='activity:1',
        played_at='2026-11-25T20:15:00Z', artist='A', title='T',
        spotify_track_id='s1',
    )
    listening.link_or_create(
        user_id=1, source='spotify', source_key='spotify:1',
        played_at='2026-11-25T20:15:01Z', artist='A', title='T',
        spotify_track_id='s1',
    )
    listening.link_or_create(
        user_id=1, source='lastfm', source_key='lastfm:1',
        played_at='2026-11-25T20:18:00Z', artist='A', title='T',
    )
    data = client.get('/api/stats').json()['playback']
    assert data['total'] == 1
    assert data['recent'][0]['source'] == 'downtify'
```

Mevcut `test_stats_reports_mirrored_spotify_plays` davranışını koru; doğrudan `activity.record('playback')` yazan mevcut Stats testlerini istek öncesi `api.state.listening.backfill_activity(api.state.activity)` çağıracak şekilde güncelle. Eski activity satırlarının açılışta canonical günlüğe taşındığını, kullanıcı/server scope ayrımını ve kullanıcı silindiğinde `ListeningStore.forget_user` çağrıldığını test et.

- [ ] **Step 2: Run tests to verify RED**

Run: `ssh home 'docker exec -e PYTHONDONTWRITEBYTECODE=1 downtify-feature-py sh -c "cd /work && .venv/bin/python -m pytest -p no:cacheprovider tests/test_api_stats.py tests/test_listening_stats_api.py -q"'`

Expected: canonical play'lar Stats yanıtında görünmediği için FAIL.

- [ ] **Step 3: Implement köprü ve Stats okuma**

`ActivityLog.record` yeni `id`'yi döndürür. `account_routes.report_playback` yeni play başladığında bu id ile `ListeningStore.link_or_create(source='downtify')` çağırır. `account_routes.delete_user` `PlaybackStore.forget_user` yanında `ListeningStore.forget_user` çağırır. `main.py` `AppState.listening` alanını açar, startup'ta store'u oluşturur, ilk admin id'siyle Spotify şemasını/pending bağlarını hazırlar ve mevcut activity satırlarını bir kez backfill eder. `collections_api.stats_endpoint` `ListeningStore.stats(user_id)` sonucunu `build_stats`e verir. `build_stats` canonical sonuç varsa onu kullanır; yoksa mevcut activity fallback'ini korur. `measured` değişmez. `recent` satırlarına `source` eklenir.

- [ ] **Step 4: Run tests to verify GREEN**

Run: Step 2 komutu ve `ssh home 'docker exec -e PYTHONDONTWRITEBYTECODE=1 downtify-feature-py sh -c "cd /work && .venv/bin/python -m pytest -p no:cacheprovider tests/test_playback.py tests/test_activity.py -q"'`.
Expected: tüm testler PASS.

- [ ] **Step 5: Commit**

```bash
git add downtify/activity.py downtify/account_routes.py downtify/api.py main.py downtify/collections_api.py downtify/stats.py tests/test_api_stats.py tests/test_listening_stats_api.py
git commit -m "feat(stats): serve unified listening history"
```

---

### Task 5: Kaynak rozetleri, Last.fm ayarı ve 8 dil

**Files:**
- Modify: `frontend/src/views/StatsView.vue`
- Modify: `frontend/src/views/SettingsView.vue`
- Modify: `frontend/src/model/settings.js`
- Modify: `frontend/src/i18n/locales/{bg,el,en,es,fr,hu,pt-BR,tr}.js`
- Create: `frontend/src/__tests__/listeningSources.test.js`
- Modify: `frontend/src/__tests__/statsViewClientRender.test.js`
- Modify: `frontend/src/__tests__/i18nParity.test.js`
- Modify: `frontend/src/__tests__/settingsExtras.test.js`
- Modify: `docs/features/stats.md`
- Modify: `README.md`

**Interfaces:**
- Consumes: `GET /api/stats` `playback.recent[].source`.
- Produces: `stats.sourceDowntify`, `stats.sourceSpotify`, `stats.sourceLastfm`, `settings.lastfmImportHistory`, `settings.lastfmImportHistoryHint` locale anahtarları.

- [ ] **Step 1: Write failing frontend tests**

`listeningSources.test.js` StatsView'i fixture `recent` satırlarıyla derleyip üç rozetin `Downtify`, `Spotify`, `Last.fm` metnini gösterdiğini doğrular. `settingsExtras.test.js` `scrobbling.import_history` varsayılanının `false` olduğunu ve save/load merge'unun alanı koruduğunu doğrular. `i18nParity.test.js` yeni anahtarların 8 dilde bulunduğunu zorunlu kılar.

- [ ] **Step 2: Run tests to verify RED**

Run: `ssh home 'docker exec downtify-feature-node sh -c "cd /work/frontend && npx vitest run --maxWorkers=1 src/__tests__/listeningSources.test.js src/__tests__/settingsExtras.test.js src/__tests__/i18nParity.test.js"'`

Expected: yeni test/anahtarlar bulunamadığı için FAIL.

- [ ] **Step 3: Implement UI ve locale**

Stats son çalmalar satırına mevcut dil stilinde küçük kaynak rozeti ekle. Last.fm ayarlarına bağlıyken gösterilen opt-in switch ekle. `settings.js` blank/default merge kopyalarına `import_history: false` ekle. 8 locale dosyasına kısa çevirileri yaz. `docs/features/stats.md` ve README'de kaynaklar, dedupe, all-time toplam ve measured sınırını açıkla.

- [ ] **Step 4: Run tests to verify GREEN**

Run: Step 2 komutu ve `ssh home 'docker exec downtify-feature-node sh -c "cd /work/frontend && npx vitest run --maxWorkers=1 src/__tests__/statsViewClientRender.test.js src/__tests__/statsPeriod.test.js"'`.
Expected: tüm testler PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/views/StatsView.vue frontend/src/views/SettingsView.vue frontend/src/model/settings.js frontend/src/i18n/locales frontend/src/__tests__/listeningSources.test.js frontend/src/__tests__/statsViewClientRender.test.js frontend/src/__tests__/i18nParity.test.js frontend/src/__tests__/settingsExtras.test.js docs/features/stats.md README.md
git commit -m "feat(ui): show unified listening sources and Last.fm import"
```

---

### Task 6: Yedek, tam kapılar, bağımsız inceleme ve deploy

**Files:**
- Modify: `downtify/backup.py`
- Modify: `tests/test_backup.py`
- Modify: `docs/superpowers/plans/2026-11-24-personal-server-program-roadmap.md`

**Interfaces:**
- Consumes: Task 1–5 tabloları ve API'si.
- Produces: yeni tabloları içeren additive metadata yedeği.

- [ ] **Step 1: Write failing backup test**

`tests/test_backup.py` içinde canonical satır, kaynak bağlantısı, ham Spotify gövdesi, ham Last.fm gövdesi ve import cursor'ı içeren bir yedeği oluşturup boş bir data dizinine geri yükleyen test yaz. `listening_events.total`, `spotify_recently_played.raw_json` ve `history_import_state.newest_at` değerlerinin geri geldiğini doğrula.

- [ ] **Step 2: Run test to verify RED**

Run: `ssh home 'docker exec -e PYTHONDONTWRITEBYTECODE=1 downtify-feature-py sh -c "cd /work && .venv/bin/python -m pytest -p no:cacheprovider tests/test_backup.py -q"'`

Expected: yeni tablolar yedeğe alınmadığı için FAIL.

- [ ] **Step 3: Implement backup kapsamı**

`_SQLITE_TABLES['downtify_activity.db']` listesine `listening_events`, `listening_event_sources`, `spotify_recently_played`, `lastfm_recent_tracks`, `history_import_state` ekle. `_PRIMARY_KEYS` değerlerini ekle. `_ensure_schema` activity dalında `ListeningStore` ve history tablolarını oluştur. 64 MiB fail-closed sınırını koru.

- [ ] **Step 4: Run backup test to verify GREEN**

Run: Step 2 komutu.
Expected: tüm backup testleri PASS.

- [ ] **Step 5: Run full gates**

```bash
ssh home 'docker exec -e PYTHONDONTWRITEBYTECODE=1 downtify-feature-py sh -c "cd /work && .venv/bin/python -m pytest -p no:cacheprovider -q"'
ssh home 'docker exec -e PYTHONDONTWRITEBYTECODE=1 downtify-feature-py sh -c "cd /work && .venv/bin/ruff check . && .venv/bin/ruff format --check ."'
ssh home 'docker exec downtify-feature-node sh -c "cd /work/frontend && npx vitest run --maxWorkers=1 && npm run build"'
ssh home 'docker exec downtify-feature-node sh -c "cd /work/docs && npm test && npm run build"'
```

Expected: pytest, Ruff, Vitest, frontend build ve docs build tamamen yeşil.

- [ ] **Step 6: Commit backup/docs**

```bash
git add downtify/backup.py tests/test_backup.py docs/superpowers/plans/2026-11-24-personal-server-program-roadmap.md
git commit -m "feat(backup): include unified listening history"
```

- [ ] **Step 7: Independent review**

Ücretsiz OpenCode Go `gozden-gecirici` alt-ajanına tüm dalı incele ve Critical/Important bulguları raporla. Bulgu varsa önce kırmızı test, sonra düzeltme ve yeniden inceleme yap. `git diff --check` ve `git status --short` temiz olmalı.

- [ ] **Step 8: Merge and deploy**

```bash
ssh home 'cd /home/yeet/downtify && git branch --show-current && git merge --ff-only feat/personal-server-program'
ssh home '~/bin/downtify-deploy.sh'
```

Deploy sonrası şu komutlarla doğrula:

```bash
ssh home 'cd /home/yeet/downtify && git rev-parse --short HEAD && docker ps --filter name=downtify --format "{{.Status}}"'
curl -fsS https://down.akinyigit.com/api/health
```

Expected: HEAD dalga commit'i; container `healthy`; health `{"status":"ok","version":"4.0.0"}`.

- [ ] **Step 9: Enable live Last.fm import and verify**

Kullanıcı onayıyla `scrobbling.import_history=true` yap. Arka plan importunun satır sayılarını ve cursor ilerlemesini oku; Stats yanıtında yeni Last.fm play'larını, ısı haritasını ve değişmeyen `measured.seconds` değerini doğrula. Ham Spotify/Last.fm satır sayıları ile canonical satır sayısını kaydet; bilinen örnek play'ın tek satır olduğunu göster.

---

## Spec Coverage

| Spec bölümü | Plan görevi |
|---|---|
| 6.1–6.5 veri modeli | Task 1–3 |
| 7 dedupe | Task 1–4 |
| 8.1 Downtify | Task 4 |
| 8.2 Spotify | Task 2 |
| 8.3 Last.fm | Task 3 |
| 9 Stats/API | Task 4 |
| 10 kullanıcı/gizlilik | Task 1, 3, 4 |
| 11 arayüz/8 dil | Task 5 |
| 12 yedek | Task 6 |
| 13 testler | Task 1–6 |
| 14 deploy/geri dönüş | Task 6 |
