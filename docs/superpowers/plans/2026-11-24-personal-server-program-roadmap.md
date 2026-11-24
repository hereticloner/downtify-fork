# Downtify Kişisel/Sunucu Programı — Yol Haritası

**Goal:** Onaylı kişisel/sunucu özellik setini sırayla, test edilmiş ve dağıtılabilir dilimler halinde tamamlamak.

**Spec:** `docs/superpowers/specs/2026-11-24-personal-server-feature-program-design.md`

**Execution:** Native, sıralı. Her alt plan tamamlanınca test/build/docs kapısı geçilir, commit alınır, `feat/collections` ile senkronlanır ve deploy doğrulanır.

## Sıra

- [x] **Oynatma hafızası + gerçek Stats** → `2026-11-24-playback-memory-stats.md` — canlıda (`befabe1`), health `ok`.
- [x] **Spotify Sync otomatik eksik indirme + başarısızlık merkezi** → `2026-11-24-spotify-sync-failures.md` — canlıda (`fef46c3`), health `ok`.
- [ ] **Birleşik arama + hızlı kazanımlar** → `2026-11-24-search-quickwins.md`
- [ ] **Bildirim/Telegram + yedek/geri yükleme** → alt plan Faz 4'te yazılacak
- [ ] **Kuyruk önceliği + sessiz saatler** → alt plan Faz 5'te yazılacak
- [ ] **Collections güç araçları** → alt plan Faz 6'da yazılacak
- [ ] **Library Health** → alt plan Faz 7'de yazılacak
- [ ] **Söz sağlığı + senkron ofset** → alt plan Faz 8'de yazılacak
- [ ] **Playlist-albüm + Monitor dry-run/Wanted** → alt plan Faz 9'da yazılacak
- [ ] **Offline PWA + depolama analizi + loudness** → alt plan Faz 10'da yazılacak
- [ ] **Güvenlik + final doğrulama** → alt plan Faz 11'de yazılacak

## Her dilimin tanımı

- İlgili backend modeli/API, Vue arayüzü, 8 dil metni, test ve doküman aynı dilimde biter.
- Yeni davranış için önce kırmızı test yazılır.
- `ruff check`, `ruff format --check`, ilgili Vitest testleri ve build geçer.
- Kullanıcı davranışı değiştiyse README + ilgili `docs/features/*.md` güncellenir.
- Commit mesajı `feat(...)` veya `fix(...)` ile dilimi anlatır.
- Deploy öncesi `git branch --show-current`, `git rev-parse HEAD` ve `git status --short` doğrulanır.
- Deploy sonrası `/api/health`, container health ve değişen uçlar ölçülür.

## Test ortamı

Worktree içinde iki geçici konteyner kullanılır:

- `downtify-feature-py`: `python:3.12-slim`, tüm repo `/work` mount, `uv` + dev bağımlılıkları.
- `downtify-feature-node`: `node:26-alpine`, tüm repo `/work` mount, frontend ve docs bağımlılıkları.

Program sonunda iki konteyner kaldırılır. Ana `downtify` ve `downtify-mirror` konteynerlerine dokunulmaz.

## Rollback

- Her dilim ayrı commit.
- Önceki canlı imaj `downtify-fork:pre-v4`.
- Hata durumunda ilgili dalga commit'i geri alınır; veri şeması değişiklikleri geriye uyumlu yazılır.

## Kapsam dışı

Çok kullanıcılı kişisel kütüphaneler, dışa açık paylaşım, OIDC, yeni ses kaynağı, PostgreSQL ve tam upstream motion portu bu programda yoktur. `8000` portu değiştirilmez.
