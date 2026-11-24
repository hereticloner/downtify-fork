# Bildirim/Telegram + Yedek/Geri Yükleme Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** İndirme/upgrade/yedek olaylarını Telegram, ntfy ve genel webhook'a ulaştırmak; Telegram'dan salt-okunur durum/kuyruk sorgulamak; ayarlar ve kütüphane metadata'sını atomik, sürümlü yedeklerden geri yüklemek.

**Architecture:** Mevcut `notifications.py` genel bir dispatcher'a dönüştürülür; sırlar `notifications.json` içinde `0600` tutulur. Yeni `backup.py` SQLite/JSON store'ları okur, gzip yedeği atomik yazar ve dry-run sonrası additive geri yükleme yapar. Ses dosyaları yedeklenmez.

**Tech Stack:** FastAPI, SQLite, httpx, Vue 3, Vitest.

**Spec:** `docs/superpowers/specs/2026-11-24-personal-server-feature-program-design.md`

## Global Constraints

- Otomatik indirme gibi bildirimler varsayılan kapalıdır.
- Telegram komutları yalnız yapılandırılan admin chat ID'sinde çalışır.
- Yazılı Telegram komutları bu planda yoktur; yalnız `/help`, `/status`, `/queue`.
- Yedek token içerir; dosya `0600` ve arayüzde açık uyarı gösterilir.
- İki yerel kopya tutulur; uzak konum/passphrase şifreleme kapsam dışıdır.
- Geri yükleme additive merge'dir; mevcut kayıtların üzerine yazılmaz.
- Ses dosyaları yedeklenmez; yalnız stabil Spotify ID'si olan eksik parçalar yeniden kuyruklanır.
- 8 locale key paritesi ve offline testler korunur.

## Review Focus

- **Bildirim sızıntısı:** webhook/token log veya API yanıtında görünmez.
- **Yanlış chat:** başka Telegram chat'inden komut yok sayılır.
- **Yedek yarım yazım:** atomik olmayan dosya mevcut yedeği bozmaz.
- **Dolu sunucuda geri yükleme:** mevcut ayar/izleme/playlist korunur; yalnız eksikler eklenir.
- **Kimliği olmayan parça:** yanlış şarkı indirilmez; çözülemeyenler listelenir.

---

### Task 1: Genel bildirim dispatcher'ı

**Files:**
- Modify: `downtify/notifications.py`, `downtify/api.py`, `main.py`
- Test: `tests/test_notifications.py`

**Interfaces:**
- Produces: `notify_event(settings, event, payload) -> dict`; `notifications.json` store.

- [ ] **Step 1: Telegram mevcut davranış testlerini koru ve ntfy/webhook testlerini yaz.**

Kanal başına `enabled`, URL/token, event filtresi ve `send test` test edilsin. HTTP MockTransport kullanılsın.

- [ ] **Step 2: Kırmızıyı doğrula ve dispatcher'ı yaz.**

`notifications.py` içinde `Telegram`, `Ntfy`, `Webhook` gönderenleri ve `Dispatcher` oluştur. Sırlar settings yerine `notifications.json` içinde `0600` yazılsın; API yalnız `<name>_set` döndürsün.

- [ ] **Step 3: Olay kancalarını ekle.**

İndirme tamamlandı/hattı, upgrade başladı/bitti/hattı ve yedek sonucu için `notify_event` çağrısı ekle. Her parça için değil, toplu özet gönder.

- [ ] **Step 4: Test/lint/commit.**

### Task 2: Telegram salt-okunur komutlar

**Files:**
- Create: `downtify/telegram_commands.py`
- Modify: `main.py`, `downtify/notifications.py`
- Test: `tests/test_telegram_commands.py`

**Interfaces:**
- Produces: `TelegramCommandBot` long-polling döngüsü; `/help`, `/status`, `/queue`.

- [ ] **Step 1: Yetkisiz chat ve komut testlerini yaz.**

Fake Telegram response ile sadece admin chat ID'sinin kabul edildiğini doğrula.

- [ ] **Step 2: Kırmızıyı doğrula ve botu ekle.**

Bot yapılandırılmışsa lifespan'te long-polling başlatsın; kapanışta task iptal edilsin. Komutlar veri değiştirmesin.

- [ ] **Step 3: Test/lint/commit.**

### Task 3: Atomik yedek store'u

**Files:**
- Create: `downtify/backup.py`
- Test: `tests/test_backup.py`

**Interfaces:**
- Produces: `BackupStore(data_dir)`; `write()`, `list()`, `preview(path)`, `restore(path, flags)`.

- [ ] **Step 1: Yedek içeriği ve iki kopya rotasyonu testlerini yaz.**

Settings, notification sırları, kullanıcılar, beğeniler, playlist'ler, collections, watch'lar, queue, exclusion, trash ve lyrics offset'leri dahil; ses ve aktif oturumlar hariç.

- [ ] **Step 2: Kırmızıyı doğrula ve atomik yazımı uygula.**

`.partial` yaz, fsync, geri oku, `os.replace`, `0600`, en yeni iki kopyayı bırak. Bozuk/eski sürüm reddedilsin.

- [ ] **Step 3: Dry-run ve additive restore testlerini yaz.**

Mevcut kayıtlar korunsun; eksik watch/playlist/song eklenir. Spotify ID'si olmayan parça `unresolved` listesine düşsün.

- [ ] **Step 4: Test/lint/commit.**

### Task 4: Yedek API ve arayüzü

**Files:**
- Create: `downtify/backup_routes.py`
- Create: `frontend/src/components/settings/BackupPanel.vue`
- Modify: `main.py`, `downtify/auth.py`, `frontend/src/views/SettingsView.vue`, `frontend/src/model/api.js`
- Test: `tests/test_backup_routes.py`, `frontend/src/__tests__/backupPanel.test.js`

**Interfaces:**
- Produces: `GET/POST /api/backups`, `POST /api/backups/restore`, `DELETE /api/backups/{name}`.

- [ ] **Step 1: API/auth/restore testlerini yaz.**

Admin-only; dosya adı allowlist; dry-run zorunlu; mevcut veri korunur.

- [ ] **Step 2: Kırmızıyı doğrula ve router'ı ekle.**

- [ ] **Step 3: Settings → Server → Backups panelini ekle.**

Yedek al, indir, yükle, önizle, onayla geri yükle ve zamanlama (kapalı/günlük/3 gün/haftalık) ekle. Token uyarısını göster.

- [ ] **Step 4: 8 locale key + test/build/commit.**

### Task 5: Doküman, tam doğrulama ve deploy

- [ ] README + `docs/features/notifications.md`, `docs/features/backups.md`, API reference güncelle.
- [ ] Tam pytest, ruff, Vitest, frontend/docs build kapılarını koş.
- [ ] Commit, fast-forward, deploy ve health doğrula.
- [ ] Roadmap'da bildirim/yedek maddesini tamamlandı işaretle; kuyruk önceliği + sessiz saatler planını yaz.
