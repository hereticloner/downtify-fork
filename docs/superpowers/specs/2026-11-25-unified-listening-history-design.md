# Birleştirilmiş Dinleme Geçmişi — Tasarım

- Tarih: 2026-11-25
- Durum: öneri — kullanıcı onayı bekliyor
- Kaynak dal: `feat/personal-server-program` @ `1a914db`
- Canlı dal: `feat/collections` @ `1a914db`
- Kapsam: Downtify + Spotify + Last.fm kayıtlarını tek bir kalıcı dinleme günlüğünde birleştirmek

## 1. Niyet

Normal Spotify istemcisinde dinlenen parçalar Downtify Stats'ın son çalmalar, ısı haritası, trendi ve toplam play sayılarına girmiyor. Spotify verisi ayrı bir panelde bulunsa da ana Stats aggregates yalnız Downtify oynatıcısının `activity.playback` kayıtlarını okuyor. Ayrıca Spotify'nin orijinal API gövdesi saklanmıyor; Last.fm bağlantısı yalnızca dışa scrobble yapıyor.

Hedef: üç kaynağın da play'larını kalıcı, tek normalize edilmiş bir günlükte birleştirmek; ham Spotify ve Last.fm kayıtlarını korumak; aynı play'ı birden fazla kaynaktan gelse de bir kez saymak.

Başarı ölçütü: canlı Spotify play'ı Stats'ta görünür; Last.fm geçmişi arka planda sayfa sayfa içe alınır; Downtify + Spotify + Last.fm aynı play için tek satır üretir; ölçülmeyen dinleme süresi uydurulmaz.

## 2. Doğrulanan mevcut durum

- Spotify importu sağlıklı: canlıda `spotify_recently_played` tablosunda 2.728 play ve bugüne ait yeni kayıtlar var; gerekli `user-read-recently-played` scope'u verilmiş.
- Bu play'lar yalnız `stats.spotify` bloğuna gidiyor. `stats.playback.total`, `recent`, `heatmap`, `top_tracks`, `streak_days` ve `best_day` yalnız `activity.kind='playback'` verisinden üretiliyor (`downtify/stats.py:259-336`).
- Spotify parser ham gövdeyi ve ISRC/context alanlarını bırakıyor; tablo kullanıcı kimliği taşımıyor (`downtify/spotify_history.py:59-82,166-201`).
- Last.fm hesabında 98.601 scrobble var; son 200 kayıt 22–25 Kasım'ı kapsıyor. Downtify oynatıcısı 22 Kasım'dan beri play üretmediği için bu yeni kayıtlar normal Spotify dinlemesinden geliyor.
- Last.fm kodu yalnız `track.updateNowPlaying` ve `track.scrobble` yapıyor; `user.getRecentTracks` okuma yolu yok.
- Spotify recently-played uç noktası en fazla 50 kayıt veriyor; tam geçmiş için sürekli çekim veya Last.fm gerekir.
- Last.fm `user.getRecentTracks` kimlik doğrulaması istemez; `api_key` + public `user` yeterli. Sayfa başına en fazla 200 kayıt ve `from`/`to` UTC Unix zaman filtreleri vardır.

Kaynaklar:

- Spotify Get Recently Played: https://developer.spotify.com/documentation/web-api/reference/get-recently-played
- Last.fm user.getRecentTracks: https://www.last.fm/api/show/user.getRecentTracks
- Spotify 50 kayıt sınırı örneği: https://community.spotify.com/forum/en/discussion/5860931/get-all-recently-played-tracks-for-a-given-period

## 3. Hedefler

1. Downtify, Spotify ve Last.fm play'ları tek kalıcı dinleme günlüğünde toplanır.
2. Ham Spotify play gövdesi ve ham Last.fm track objesi kendi tablolarında saklanır.
3. Kaynak önceliği Downtify → Spotify → Last.fm olur; aynı play tek canonical satır başına sayılır.
4. Last.fm geçmişi idempotent, kaldığı yerden devam eden bir backfill ile içe alınır.
5. Stats mevcut API alanlarını korur; `playback.recent` satırlarına geriye uyumlu bir `source` alanı eklenir.
6. Kullanıcı bazlı Stats korunur; global sağlayıcı bağlantıları ilk Downtify admin'ine atanır.
7. Yeni veriler mevcut yedek/geri yükleme kapsamına girer.

## 4. Kapsam dışı / anti-hedefler

- Last.fm kayıtlarını teker teker Spotify Search ile Spotify ID'ye çevirmek.
- Spotify'nin 50 kayıtlık penceresinin ötesine geçmeye çalışmak.
- Dinleme süresi, completion veya skip uydurmak; bu ölçüler yalnız Downtify position raporlarından gelir.
- Yeni müzik sağlayıcısı, çok kullanıcılı kütüphane, OIDC veya PostgreSQL.
- Mevcut Spotify panelini kaldırmak; API uyumu için korunur.
- Fuzzy sanatçı/başlık eşleştirmesi veya sürüm/remaster çözümleme. İlk sürüm normalize edilmiş tam sanatçı + başlık kullanır.

## 5. Seçilen yaklaşım

### Kalıcı birleştirilmiş dinleme günlüğü

Ham gözlemler ve canonical play'lar ayrılır:

```text
Downtify player ──┐
Spotify recent ───┼─> raw observation tables ──> link_or_create ──> listening_events
Last.fm history ──┘                                              │
                                                                └─> GET /api/stats
```

- Ham gözlemler değiştirilmeden saklanır.
- `listening_events` Stats'ın okuduğu tek canonical tablodur.
- Her ham gözlem bir `listening_event_id` ile canonical satıra bağlanır.
- Daha yüksek öncelikli kaynak sonra gelirse canonical satırın kaynağı/metadata'sı yükseltilir; eski ham gözlem bağlantısı korunur.

Reddedilen alternatifler:

- **Anlık birleştirme:** 98 bin kayıtta her Stats isteğinde tarama ve eşleştirme yapar; kalıcı dedupe kimliği oluşmaz.
- **Yalnız Last.fm:** Stats için yeterlidir ancak orijinal Spotify gövdesi ve kesin Spotify ID'si saklanmaz; kullanıcının ilk isteğini karşılamaz.

## 6. Veri modeli

Tüm tablolar mevcut `/data/downtify_activity.db` içinde, geriye uyumlu `CREATE TABLE IF NOT EXISTS` ve açık migration adımlarıyla oluşturulur.

### 6.1 `listening_events` — canonical

| Alan | Anlam |
|---|---|
| `id` | Birincil anahtar |
| `user_id` | Downtify hesabı; global import ilk admin'ine atanır |
| `source` | Güncel en yüksek öncelikli kaynak: `downtify`, `spotify`, `lastfm` |
| `identity_key` | İlk gözlemin değişmez kimliği; `UNIQUE(user_id, identity_key)` |
| `source_key` | Güncel kaynağın kararlı kimliği; bilgi amaçlıdır, unique değildir |
| `played_at` | Güncel en yüksek öncelikli kaynağın zamanı |
| `match_key` | Normalize edilmiş `artist + title` |
| `title`, `artist`, `album` | Görüntülenen metadata |
| `spotify_track_id` | Varsa kesin Spotify ID; yoksa boş |
| `duration_ms` | Bilinen parça süresi; dinlenen süre değildir |
| `context`, `context_type` | Varsa playlist/albüm bağlamı |
| `created_at` | İlk oluşturma zamanı |

Endeksler: `(user_id, match_key, played_at)` ve `(user_id, played_at DESC)`.

`identity_key` hiç değişmez. Ham gözlem tabloları kendi `source_key` değerinde unique olduğundan aynı kaynağın tekrar importu veya backup restore'u canonical tabloya ikinci satır açmaz. Daha üst öncelikli kaynak geldiğinde `source`, `source_key`, `played_at` ve metadata yükseltilir; `identity_key` korunur.

### 6.2 `spotify_recently_played` — ham Spotify gözlemleri

Mevcut tablo güvenli biçimde yeniden kurulur:

- `id`, `user_id`, `source_key`, `listening_event_id` eklenir.
- `played_at` tek başlık anahtar olmaktan çıkar; aynı saniyedeki iki farklı parça kaybolmaz.
- `isrc`, `context_json`, `raw_json` eklenir.
- Eski 2.728 satır ilk admin'ine, `raw_json='{}'` ve kararlı `source_key` ile taşınır; geriye dönük olarak mevcut olmayan ham gövde uydurulmaz.
- `raw_json`, Spotify'nin o play için döndürdüğü orijinal `item` objesidir.

### 6.3 `lastfm_recent_tracks` — ham Last.fm gözlemleri

- `id`, `user_id`, `source_key`, `listening_event_id`
- `played_at` (UTC ISO), `artist_name`, `track_name`, `album_name`, `mbid`
- `raw_json` (orijinal track objesi), `imported_at`
- `nowplaying=true` ve tarihsiz kayıtlar canonical play'a çevrilmez.
- Aynı saniye/sanatçı/başlık için birden fazla gerçek scrobble varsa kararlı occurrence sıra numarası `source_key`e eklenir; import tekrarı aynı sırayı üretir.

### 6.4 `history_import_state`

- `source` birincil anahtar
- `newest_at`, `oldest_at`, `backfill_done`

Last.fm backfill'i hangi zaman aralığının içe alındığını ve yeni kayıtların nereden devam edeceğini tutar.

### 6.5 `listening_event_sources` — kaynak başına tek gözlem kapısı

- `event_id`, `source`, `PRIMARY KEY(event_id, source)`
- Bir canonical play'a aynı kaynaktan ikinci gözlem bağlanamaz.
- Aynı kaynaktan gelen yeni gerçek play yeni canonical satır açar.
- Bu tablo kaynak yükseltmesi sırasında da korunur; eski kayıtların provenance bağı kopmaz.

## 7. Eşleştirme ve dedupe

### 7.1 Kaynak önceliği

1. `downtify` — gerçek position/start raporu
2. `spotify` — kesin Spotify ID'si ve zengin metadata
3. `lastfm` — geniş geçmiş, metadata eşleşmesi

### 7.2 Kimlik

- `match_key`: Unicode NFKC + casefold + boşluk normalize edilmiş tam sanatçı ve başlık.
- Aynı `user_id` ve `match_key` için adaylar `played_at` çevresinde aranır.
- Zaman penceresi: `max(300 saniye, min(parça süresi + 300 saniye, 1800 saniye))`.
- Adaylar arasında en yakın zaman seçilir.
- Aynı kaynağın ikinci gözlemi aynı canonical satıra bağlanamaz; `listening_event_sources` bunu transaction içinde zorunlu kılar. Yeni gerçek play olarak değerlendirilir.
- Daha yüksek öncelikli kaynak geldiğinde canonical satırın `source`, `source_key`, `played_at` ve metadata'sı yükseltilir; `identity_key` ve önceki kaynak bağlantıları korunur.
- Last.fm scrobble zamanı bazen play başlangıcından birkaç dakika sonradır. Downtify veya Spotify gözlemi geldiğinde doğru başlangıç zamanı canonical satıra taşınır; gün sınırı da bu doğru zamana göre hesaplanır.
- Spotify ID varsa eşleşmeyi güçlendirir; Last.fm MBID'si Spotify ID'si değildir ve doğrudan eşleştirme anahtarı yapılmaz.

Bilinen sınır: farklı sanatçı yazımı, sürüm veya remaster aynı play'ı iki satır üretebilir. İlk sürüm yanlış birleştirmeden kaçınmak için fuzzy eşleştirme yapmaz.

## 8. Import akışları

### 8.1 Downtify

- `ActivityLog.record()` geriye uyumlu biçimde yeni satırın `id`'sini döndürür.
- `POST /api/activity/playback` yeni bir play başlattığında canonical kayıt `source_key=activity:{id}` ile yazılır.
- Eski `activity.playback` satırları açılışta bir kez `listening_events` tablosuna taşınır.
- `PlaybackStore` ve ölçülmüş metrikler değişmez.

### 8.2 Spotify

- Mevcut 30 dakikalık import döngüsü korunur.
- Parser ham `item`, ISRC ve context'i de saklar.
- Her yeni ham gözlem `link_or_create` üzerinden canonical satıra bağlanır.
- Daha fazla geçmiş Spotify API'sinden çekilmez.

### 8.3 Last.fm

- `scrobbling.import_history` yeni opt-in ayarı eklenir; varsayılan `false`.
- Ayar için `lastfm_enabled`, API key ve kullanıcı adı yeterlidir; session key okuma için gerekli değildir.
- Yeni arka plan döngüsü 15 dakikada bir çalışır:
  1. `newest_at` sonrası yeni scrobble'ları getirir.
  2. `backfill_done=false` ise `oldest_at` öncesini sayfa sayfa, koşu başına en fazla 20 sayfa çeker.
  3. Her sayfayı işledikten sonra cursor'ı kalıcı yazar; hata durumunda sonraki koşu aynı yerden devam eder.
- Sayfa boyutu 200; `from`/`to` Unix saniye cinsindendir.
- 429/16 hatalarında döngü koşuyu bırakır, sonraki periyodunda tekrar dener; token veya session key loglanmaz.
- İlk kurulumda 98.601 kayıt yaklaşık 494 sayfa olduğundan tam backfill birkaç saat sürebilir; Stats içe alındıkça büyür.

## 9. Stats ve API

`GET /api/stats?days=7|30|90&scope=user|server` mevcut üst seviye sözleşmeyi korur.

- `playback.total`, `top_tracks`, `heatmap`, `streak_days`, `best_day`, `recent`, `top_contexts` artık `listening_events` verisinden üretilir.
- `playback.measured` yalnız `PlaybackStore.summary()` kalır; Spotify/Last.fm saniye, completion veya skip üretmez.
- `playback.recent` satırlarına `source` eklenir. Mevcut alanlar korunur.
- `spotify` bloğu API uyumu için aynı kalır.
- `scope=user` yalnız kullanıcının canonical kayıtlarını; `scope=server` admin için tüm hesapları toplar.
- Toplam ve geçmiş all-time'dır; ısı haritası mevcut 364 günlük pencereyi korur.
- Büyük geçmişte her istekte 98 bin satır Python'a çekilmemesi için toplam/top/günlük/recent/context aggregates SQLite'da üretilir.

## 10. Kullanıcı ataması ve gizlilik

- Spotify ve Last.fm bağlantıları yalnız admin ayarlarında yapılabilir; import edilen kayıtlar `UserStore.first_admin()` hesabına atanır.
- Mevcut Spotify satırları migration sırasında aynı kuralla taşınır.
- Başka bir admin bağlantıyı sonradan değiştirirse eski kayıtlar ilk admin'e ait kalır; bu ilk sürüm sınırıdır.
- Ham gövde token, cookie veya authorization header içermez; yine de yedek token içeren settings gibi hassas kabul edilir.
- Yeni import/settings uçları admin-only kalır.

## 11. Arayüz

- Stats son çalmalar listesindeki her satıra küçük kaynak rozeti eklenir: `Downtify`, `Spotify`, `Last.fm`.
- Sekiz locale anahtarı eş zamanlı eklenir; mevcut palet, tipografi, 0 radius, 2px çizgi ve reduced-motion davranışı korunur.
- Last.fm ayarlarına “geçmişi Stats'a aktar” switch'i ve açıklaması eklenir.
- Spotify import açıklaması ham veri saklama ve birleşik Stats'a katkıyı belirtir.
- Ek kaynak filtresi veya yeni metrik eklenmez.

## 12. Yedek ve geri yükleme

- `listening_events`, `listening_event_sources`, `spotify_recently_played`, `lastfm_recent_tracks`, `history_import_state` mevcut metadata yedeğine eklenir.
- Primary key'ler ve additive restore kuralları genişletilir.
- Ham gövde nedeniyle yedek büyüyebilir; mevcut 64 MiB sınırı fail-closed kalır, sessiz kısmi yedek üretilmez.
- Ses dosyaları yedeklenmez.

## 13. Test planı

### Backend

1. Eski Spotify şemasından yeni şemaya kayıpsız migration; aynı saniyedeki iki farklı parça.
2. Spotify parser'ın ham gövde, ISRC ve context'i birebir saklaması.
3. Last.fm tek/çok track yanıtı, `nowplaying` atlama, `from`/`to`, 200 limit, hata ve 429 davranışı.
4. Aynı kaynaktan idempotent import; aynı saniyedeki gerçek tekrar scrobble'ları.
5. Downtify + Spotify + Last.fm aynı play için tek canonical satır, değişmeyen `identity_key` ve kaynak önceliği yükseltmesi.
6. Zaman penceresi dışındaki gerçek tekrarın ve aynı kaynağın ikinci gerçek gözleminin ayrı sayılması.
7. Kullanıcı/admin server scope ayrımı.
8. Stats aggregates, `source` alanı ve measured metriklerin değişmemesi.
9. Yeni tabloların yedek/geri yükleme testi.
10. 50/200/boş/kırık provider yanıtlarında sayfanın 500 vermemesi.

### Frontend

1. Kaynak rozetlerinin üç kaynak için doğru metin göstermesi.
2. Sekiz locale key paritesi.
3. Mevcut Stats client-render ve reduced-motion testlerinin yeşil kalması.
4. 2560/780/390 px genişliklerinde yatay taşma olmaması.

### Canlı kabul

- Deploy öncesi/sonrası Spotify ve Last.fm satır sayıları.
- Canonical satır sayısının ham gözlem sayısından küçük/eşit olması ve bilinen örnek play'ın tek satır olması.
- Stats yanıtında yeni Spotify/Last.fm play'ları `recent` ve ısı haritasında görünmesi.
- `measured.seconds` değerinin dış importlardan artmaması.
- `/api/health`, container health ve deploy HEAD doğrulaması.

## 14. Yürütme ve geri dönüş

1. Test-first migration/store/import dilimi.
2. Stats/API/UI dilimi.
3. Yedek ve doküman dilimi.
4. Tam test/build/docs kapıları ve bağımsız inceleme.
5. `feat/personal-server-program` → `feat/collections` fast-forward merge.
6. `ssh home '~/bin/downtify-deploy.sh'` ile deploy ve canlı doğrulama.
7. Kullanıcı onayıyla Last.fm import ayarını açma ve backfill ilerlemesini izleme.

Geri dönüş: import switch'lerini kapatmak ve önceki imaja dönmek. Şema additive olduğundan veri silinmez; rollback imajı `downtify-fork:pre-v4`.

## 15. Planlayıcıya bırakılanlar

- SQLite migration ifadelerinin kesin sırası.
- `ListeningStore` metot imzaları ve SQL aggregate sorguları.
- Last.fm occurrence anahtarının kesin encoding'i.
- Test fixture'larının ve container komutlarının ayrıntılı listesi.
- Küçük i18n metinlerinin nihai çevirileri.
