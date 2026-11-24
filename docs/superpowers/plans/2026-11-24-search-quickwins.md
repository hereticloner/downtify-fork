# Birleşik Arama + Hızlı Kazanımlar Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Aynı aramada yerel kütüphane ve uzak sonuçları birleştirmek; çalma kuyruğunu playlist'e çevirmek, sanatçı izlemeyi tek tıkla başlatmak, Similar'da toplu indirme ve Collections üye çıkarmayı eklemek.

**Architecture:** Mevcut Vue modelleri ve API'ler genişletilir; yeni backend tablosu gerekmez. Yerel arama mevcut library filtresini kullanır, uzak sonuçlar aynı listelerde etiketlenir. Playlist ve Monitor aksiyonları mevcut uçları çağırır.

**Tech Stack:** Vue 3, Vitest, Vite, FastAPI.

**Spec:** `docs/superpowers/specs/2026-11-24-personal-server-feature-program-design.md`

## Global Constraints

- v4 kimliği ve reduced-motion davranışı korunur.
- 8 locale key paritesi korunur.
- Mevcut API yanıtları kırılmaz.
- Testler offline olur.
- Kullanıcı davranışı değiştiği için README + ilgili feature sayfaları güncellenir.

## Review Focus

- **Yerel/uzak aynı şarkı:** iki satır görünmez; uzak satır "kütüphanede" işaretlenir.
- **Boş/çok uzun arama:** yerel sonuçlar uzak ağ hatasını gizlemez.
- **Stream içeren kuyruk:** yalnız indirilen parçalar playlist'e kaydedilir.
- **Sanatçı eşleşmesi:** yanlış Spotify/YouTube Music eşleşmesi kullanıcıya onaylatılır.
- **Akıllı koleksiyon üyesi:** kurala uyen üye çıkarılsa yeniden hesaplanabilir; statik üye kalıcı çıkarılır.

---

### Task 1: Birleşik arama

**Files:**
- Modify: `frontend/src/model/search.js`, `frontend/src/views/SearchView.vue`, `frontend/src/lib/searchMerge.js`
- Test: `frontend/src/__tests__/searchMerge.test.js`, `frontend/src/__tests__/searchLocal.test.js`

**Interfaces:**
- Produces: `mergeSearchResults(localTracks, remoteTracks) -> {tracks, localKeys}`; `useSearch().localTracks`.

- [ ] **Step 1: Merge testini yaz**

Yerel `A - One.mp3` ile uzak `One` aynı normalize anahtarda olsun; sonuç tek yerel satır ve uzak satır `inLibrary=true` taşısın.

- [ ] **Step 2: Kırmızıyı doğrula ve saf yardımcıyı yaz**

`searchMerge.js` içinde normalize + merge fonksiyonunu oluştur.

- [ ] **Step 3: Yerel sorguyu modele ekle**

`useLibrary().ensureTracks()` sonrası mevcut `filterLibraryEntries` veya `searchLibraryTracks` yardımcısıyla ilk 50 yerel parçayı al. Uzak isteklerle `Promise.allSettled` çalışsın.

- [ ] **Step 4: SearchView'e yerel bölüm ekle**

Üstte **Kütüphanem**, altında mevcut uzak bölümler olsun. Yerel satır `SongRow` veya mevcut track bileşeniyle oynat/kuyruğa ekleme yapsın. Uzak satırlarda küçük "kütüphanende" rozeti göster.

- [ ] **Step 5: 8 locale key + test/build ekle**

`search.library`, `search.inLibrary`, `search.libraryEmpty` anahtarlarını ekle.

```bash
docker exec downtify-feature-node npm test --prefix frontend -- --run \
  src/__tests__/searchMerge.test.js src/__tests__/searchLocal.test.js
docker exec downtify-feature-node npm run build --prefix frontend
```

- [ ] **Step 6: Commit**

### Task 2: Çalma kuyruğunu playlist olarak kaydet

**Files:**
- Modify: `frontend/src/components/player/UpNextPanel.vue`, `frontend/src/model/playlistActions.js`
- Test: `frontend/src/__tests__/queueToPlaylist.test.js`

**Interfaces:**
- Produces: `playlistActions.saveQueueAsPlaylist(name) -> Promise<string>`.

- [ ] **Step 1: Testi yaz**

Yalnız `track.file` olan parçalar sırayla `createNamed(name, files)` çağrısına geçsin; stream parçaları atlansın; boş kuyruk hata versin.

- [ ] **Step 2: Kırmızıyı doğrula ve aksiyonu ekle**

`UpNextPanel` başlığına **Playlist olarak kaydet** düğmesi ve ad istemi ekle. Mevcut `createNamed` yardımcısını kullan.

- [ ] **Step 3: 8 locale key + test/build**

`player.saveQueue`, `player.saveQueueTitle`, `player.saveQueueEmpty`, `player.saveQueueDone` anahtarlarını ekle.

- [ ] **Step 4: Commit**

### Task 3: Sanatçı sayfasından yeni çıkanları izle

**Files:**
- Modify: `frontend/src/views/ArtistView.vue`, `frontend/src/model/monitor.js`
- Test: `frontend/src/__tests__/artistWatch.test.js`

**Interfaces:**
- Consumes: `addMonitoredPlaylist(url, interval, {new_only:true})`.
- Produces: `ArtistView.watchArtist()`.

- [ ] **Step 1: Testi yaz**

Sanatçı Spotify URL'i varsa `new_only:true` ile Monitor API'si çağrılsın; URL yoksa aksiyon gizlenmeli.

- [ ] **Step 2: Kırmızıyı doğrula ve butonu ekle**

Artist hero aksiyonlarına **Yeni çıkanları izle** ekle. Zaten izleniyorsa **İzleniyor** göster; mevcut Monitor listesini kullan.

- [ ] **Step 3: 8 locale key + test/build**

`artist.watchNew`, `artist.watching`, `artist.watchFailed` anahtarlarını ekle.

- [ ] **Step 4: Commit**

### Task 4: Similar'da toplu seçim ve indirme

**Files:**
- Modify: `frontend/src/views/SimilarView.vue`
- Test: `frontend/src/__tests__/similarBulk.test.js`

**Interfaces:**
- Consumes: mevcut `useSelection` + `useDownloadManager`.
- Produces: `SimilarView.downloadVisibleNew()`.

- [ ] **Step 1: Testi yaz**

Yalnız yüklenen görünür sonuçlar seçilsin; kütüphanede olanlar atlansın; seçim yeni sayfa yüklendiğinde sıfırlansın.

- [ ] **Step 2: Kırmızıyı doğrula ve toplu aksiyonu ekle**

Başlığa **Yeni olanların tamamını indir** düğmesi ekle. Sonsuz listede tüm gelecek sayfaları değil, o an yüklü sonuçlar kapsansın.

- [ ] **Step 3: 8 locale key + test/build**

`similar.downloadNew`, `similar.downloadNewCount` anahtarlarını ekle.

- [ ] **Step 4: Commit**

### Task 5: Collections üye çıkarma

**Files:**
- Modify: `frontend/src/views/CollectionsView.vue`, `frontend/src/model/collections.js`
- Test: `frontend/src/__tests__/collectionRemove.test.js`

**Interfaces:**
- Consumes: `POST /api/collections/{name}/items {remove:[...]}`.
- Produces: `useCollections().removeItem(name, playlist)`.

- [ ] **Step 1: Testi yaz**

Chip yanına çıkarma düğmesi gelsin; statik üye API'den çıkarılsın; akıllı kural üyesi için kullanıcıya "kurallar yeniden ekleyebilir" bilgisi gösterilsin.

- [ ] **Step 2: Kırmızıyı doğrula ve UI/modeli ekle**

Mevcut API zaten `remove` destekliyor. Chip'i link + çıkarma düğmesi olarak yeniden düzenle.

- [ ] **Step 3: 8 locale key + test/build**

`collections.removeItem`, `collections.smartMayReturn` anahtarlarını ekle.

- [ ] **Step 4: Commit**

### Task 6: Doküman, tam doğrulama ve deploy

- [ ] README + `docs/features/search.md`, `player.md`, `playlist-monitor.md`, `similar.md`, `collections.md` güncelle.
- [ ] Tam pytest, ruff, Vitest, frontend build, docs test/build kapılarını koş.
- [ ] Commit al, `feat/personal-server-program` dalını ana checkout'a fast-forward et, deploy et ve health doğrula.
- [ ] Roadmap'da birleşik arama + hızlı kazanımlar maddesini tamamlandı işaretle; bildirim/Telegram + yedek/geri yükleme alt planını yaz.
