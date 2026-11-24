# Downtify Kişisel/Sunucu Özellik Programı — Tasarım

- Tarih: 2026-11-24
- Durum: onay bekliyor
- Kaynak dal: `feat/collections` @ `aadb477`
- Çalışma dalı: `feat/personal-server-program`
- Worktree: `/home/yeet/downtify/.worktrees/personal-server-program`
- Ürün hedefi: yeet'in kişisel indirme/çalma aracı ve özel sunucusu; dışa açık SaaS ürünü değil.

## 1. Niyet

Downtify'in mevcut indirme → kütüphane → oynatma döngüsünü bozmadan, günlük kullanımda gerçek fark yaratan özellikleri sırayla tamamlamak. Son turki animasyon çalışmasının ardından odak ürün derinliği, güvenilirlik ve operasyon kontrolüdür.

Başarı: listedeki kişisel/sunucu özelliklerinin tamamı ayrı ayrı test edilerek, mevcut API ve arayüz kimliği korunarak canlıya alınır. Kullanıcı tekrar tekrar "bu neden yok?" dediği akışlarda otomatikleştirme ve görünürlük oluşur.

## 2. Hedefler

1. Oynatma durumunu cihazlar arası taşımak ve gerçek dinleme istatistiği üretmek.
2. Spotify Sync, başarısız indirmeler ve uzun süreli işler için tam otomasyon ve görünürlük sağlamak.
3. Yerel kütüphane ile uzak keşfi tek aramada birleştirmek.
4. Yedek/geri yükleme ile veri kaybı riskini azaltmak.
5. İndirme kuyruğunu öncelik, zamanlama ve toplu yönetimle kontrol edilebilir hâle getirmek.
6. Collections, Library Health ve söz bakımı gibi fork'a özgü özellikleri tamamlamak.
7. Jellyfin/Plex uyumlu albüm indirme, Monitor dry-run/Wanted, offline PWA kabuğu, depolama analizi ve opt-in loudness/ReplayGain eklemek.
8. Public sunucu için açık güvenlik borçlarını kapatmak.

## 3. Kapsam dışı / anti-hedefler

- Kullanıcı başına ayrı kütüphaneler (upstream #666).
- Herkese açık playlist/collection paylaşım bağlantıları.
- OIDC/SSO ve dışa açık SaaS kimlik akışı.
- Yeni ses kaynağı ekleme (SoundCloud, Deemix vb.).
- PostgreSQL geçişi; ölçülmüş bir SQLite darboğazı yok.
- Upstream'in tam skeleton/motion taşınması; mevcut v4 motion sistemi korunur.
- `git merge upstream/main`; yalnız seçici commit/desen portu yapılır.
- Ürün kimliğini değiştirmek: palet, tipografi, 0 radius, 2px çizgi ve reduced-motion davranışı korunur.

## 4. Kısıtlar

- Mevcut FastAPI + Vue 3 + SQLite/JSON mimarisi korunacak.
- Her yeni kullanıcı davranışı 8 dilde eklenecek; locale key paritesi test edilecek.
- API geriye uyumluluğu korunacak; yeni uçlar eklenecek, mevcut yanıtlar kırılmayacak.
- Testler offline olacak; dış servisler fixture/mock ile doğrulanacak.
- Yeni bağımlılık yalnız standart kütüphane/mevcut paketlerle çözülemeyse eklenecek.
- Büyük dosya yazımları atomik olacak; token içeren dosyalar `0600` olacak.
- Worktree içinde çalışılacak; her faz sonunda test/build ve doküman kapısı geçilecek.
- Canlıya deploy yalnız doğrulanmış commit ile `~/bin/downtify-deploy.sh` üzerinden yapılacak; önce geri dönüş etiketi doğrulanacak.

## 5. Değerlendirilen yaklaşımlar

### A. Upstream 3.14'i merge etmek

Avantaj: çok sayıda özellik hazır gelir.
Dezavantaj: fork'un Collections, Stats, Mirror, Sync ve trash tasarımı çakışır; slskd/podcast geri gelir; UI kimliği bozulur.
Karar: reddedildi.

### B. Büyük yeniden yazım / tek seferde bütün özellikler

Avantaj: temiz bir model.
Dezavantaj: yüksek regresyon riski; mevcut 2600+ test ve canlı veriyle uyum zorlaşır.
Karar: reddedildi.

### C. İzole dalda dikey dilimler (seçilen)

Her özellik backend + API + UI + test + doküman olarak tamamlanır; test/build yeşilse commit edilir. Mümkün olduğunda faz sonunda deploy ve health doğrulaması yapılır.
Avantaj: en küçük güvenli adım, kolay geri dönüş, net kabul ölçütü.
Karar: seçildi.

## 6. Mimari kararlar

### 6.1 Oynatma hafızası

- `downtify_activity.db` içine `playback_positions` ve `playback_events` tabloları eklenecek.
- `playback_positions`: kullanıcı + cihaz + kararlı parça kimliği + son konum + süre + durum + bağlam + zaman.
- `playback_events`: başlangıç, duraklatma, devam, durdurma, tamamlama ve atlama olayları; mevcut 30 sn heartbeat verisi kullanılacak.
- Mevcut `POST /api/activity/playback` ucu genişletilecek; istemci zaten `position` ve `duration` gönderiyor.
- `GET /api/playback/resume` son kaldığı yerden devam eden parçayı döndürecek.
- Stats; dinleme süresi, tamamlama/atlama oranı ve 7/30/90 günlük dönem seçici üretecek.
- Stream parçalar için localStorage davranışı korunacak; sunucu kalıcılığı yalnız kararlı kimliği çözümlenebilen parçalar için kullanılacak.

### 6.2 Spotify Sync

- Sync diff çıktısı `added` listesini koruyacak.
- Yeni opt-in ayar: eklene parçaları otomatik kuyruğa al.
- Mevcut `download-missing` akışı kullanılacak; mükerrer kuyruk kaydı engellenecek.
- UI'da son sync'te eklenen/çıkarılan parça sayısı ve otomatik indirme durumu gösterilecek.

### 6.3 Başarısızlık merkezi

- İndirme hataları için yapılandırılmış kayıt: parça, kaynak, hata kodu, mesaj, deneme sayısı, son zaman, playlist bağlamı.
- Queue ve Monitor üzerinde ortak bir filtre/eylem yüzeyi: yeniden dene, hariç tut, detayı aç.
- Hassas token veya tam URL loglanmayacak.

### 6.4 Birleşik arama

- `SearchView` yerel kütüphane ve uzak sonuçları aynı yanıtta birleştirecek.
- Yerel sonuçlar önce gösterilecek; aynı parça uzak sonuçta "kütüphanende" olarak işaretlenecek.
- Mevcut eşleştirme yardımcıları kullanılacak; yeni arama motoru yazılmayacak.

### 6.5 Bildirimler ve Telegram

- `notifications.py` Telegram'ya bağlı tek amaçlı koddan genel dispatcher'a dönüştürülecek.
- İlk sürüm: Telegram, ntfy ve genel JSON webhook. Discord/Gotify ileride gerekirse eklenir; kapsam dışı.
- Olaylar: indirme tamamlandı/hattı, toplu indirme özeti, upgrade başladı/bitti/hattı, yedek sonucu.
- Telegram bot yalnız yapılandırılan admin chat ID'sinde çalışacak. İlk komutlar salt okunur: `/status`, `/queue`, `/help`.
- Yazılı komutlar (`/pause`, `/resume`) yalnız açık onayla ve admin kullanıcı için eklenebilir; varsayılan kapalı.

### 6.6 Yedek/geri yükleme

- Sürümlü JSON.gz yedeği: settings, notifications sırları, watch'lar, collections, kütüphane şarkı listesi.
- Ses dosyaları yedekte olmayacak; geri yükleme eksik parçaları mevcut indirme akışına kuyruklayacak.
- İki kopya rotasyonu, atomik yazım, okuduktan sonra doğrulama ve `0600` izin.
- Zamanlanmış yedek: kapalı, günlük, 3 gün, haftalık.
- Geri yükleme dry-run önizlemesi gösterecek; onay olmadan değişiklik yapmayacak.

### 6.7 Kuyruk kontrolü

- Kalıcı kuyruk sırasına `priority` alanı eklenecek; yalnız `queued` işler taşınacak.
- Toplu seçim: kaldır, askıya al, sürdür.
- Sessiz saat penceresi mevcut `queue_pause` kapısına bağlanacak; saat dilimi ve DST açıkça tanımlanacak.
- Çalışan indirme kesilmeden tamamlanacak; yeni işler pencere dışında bekleyecek.

### 6.8 Collections

- Statik koleksiyon üye çıkarma UI'ı eklenecek.
- Kural motoru geriye uyumlu biçimde AND/OR/NOT gruplarına genişletilecek; eski düz kural listeleri AND olarak yorumlanacak.
- Kaydetmeden önizleme ucu eklenecek.
- Özel koleksiyon kapağı, mozaik fallback ve kapak doğrulaması eklenecek.
- Koleksiyonu oynat/kuyruğa ekle ve temel analiz (parça/süre/boyut/eksik oran) eklenecek.

### 6.9 Library Health

- Salt okunur teşhis: diskteki dosya, TrackIndex, playlist kayıtları, Monitor ve Navidrome eşleşmeleri.
- Bulgular kategorilere ayrılacak: eksik dosya, eşleşmeyen yol, bayat mapping, eksik metadata, yetim kayıt.
- Her bulgu için güvenli eylem önerilecek; otomatik düzeltme varsayılan kapalı.
- Dışa aktarılan teşhis dosyasından yol, token ve kişisel veri redakte edilecek.

### 6.10 Sözler

- LRCLIB search fallback ve isteğe bağlı Kugou sağlayıcısı değerlendirilecek; yeni kaynak kullanıcı ayarıyla kapalı başlayacak.
- "Yalnız senkron" modu ve toplu "tara ve bul" akışı eklenecek.
- Cihaz bazlı ±0,5 sn senkron ofseti; dosya varsayılan olarak değiştirilmeyecek.
- Mevcut MP3/FLAC/M4A/Opus yazma davranışı korunacak.

### 6.11 Hızlı kazanımlar

- Çalma kuyruğunu playlist olarak kaydet.
- Sanatçı sayfasından "Yeni çıkanları izle".
- Benzer şarkılarda yüklenen görünüm içinde toplu seçim/indirme.
- Stream oturumunu kararlı kimlikle yenilemede sürdürme.

### 6.12 Büyük kişisel/sunucu adayları

- **Playlist albüm olarak indir:** upstream #668 deseni; Jellyfin/Plex için tek albüm klasörü.
- **Monitor dry-run:** değişiklikleri önizle, onayla indir; istek kimliğiyle önizleme/uygulama aynı veriyi kullanacak.
- **Wanted:** izlenen sanatçıların eksik albümleri; upstream #604 bağımlılıkları önce port edilecek.
- **Offline PWA kabuğu:** statik UI cache; API network-first; ses dosyası cache edilmeyecek.
- **Depolama büyüme analizi:** günlük snapshot, format/sanatçı/albüm dağılımı, disk dolma tahmini.
- **Loudness/ReplayGain:** opt-in analiz ve önbellek; dosya bozulmadan önce analiz dışa aktarılacak, EQ ile çift gain engellenecek.

### 6.13 Güvenlik sertleştirme

- `settings.json` ve notification sırları için atomik yazım + `0600`.
- CSP başlıklarını tarayıcıda doğrulayarak tamamlamak.
- `:href` şema denetimi için ortak yardımcı.
- Mirror imajına sürüm + SHA-256 pinleme.
- Portu loopback'e çekmeden önce Cloudflare ingress'i `127.0.0.1:8000` olarak doğrulamak; sonra compose'u değiştirmek.

## 6.14 Builder check kararları

- **Kullanıcı modeli:** mevcut çok kullanıcılı hesaplar korunur. Resume, beğeniler, koleksiyonlar, söz ofsetleri ve kişisel istatistikler kullanıcı bazlıdır; admin sunucu genelini görür. Kuyruk ve ayarlar yönetim kapsamında admin kontrolündedir.
- **Yedek kapsamı:** settings, notification sırları, kullanıcılar (parola hash'leri), beğeniler, manuel playlist'ler, collections, activity/Stats, kuyruk, exclusion'lar, trash metadata ve söz ofsetleri dahil; aktif oturumlar ve ses dosyaları hariç.
- **Yedek konumu/şifreleme:** ilk sürümde yerel `backups/` altında iki kopya, atomik yazım ve `0600`. Token içerdiği için arayüzde açık uyarı gösterilir; uzak konum ve passphrase şifreleme sonraki ayrı karardır.
- **Geri yükleme:** varsayılan additive merge; mevcut kayıtların üzerine yazılmaz. Dry-run zorunludur. Yalnız stabil Spotify ID'si olan eksik parçalar otomatik yeniden indirilir; diğerleri "kimlik çözülemedi" listesinde gösterilir.
- **Resume:** kullanıcının en son dinlediği parça önerilir; cihaz başına son konum saklanır. İki cihaz çakışırsa otomatik override yapılmaz, kullanıcı cihaz/konum seçer.
- **Stats sayımı:** heartbeat tekrarları birikimli sayılmaz; benzersiz dinleme saniyesi toplanır. %90 ve üzeri tamamlama, %25 altında veya 15 sn içinde atlama skip sayılır. Seek/replay ikinci kez sayılmaz; eski activity yalnız başlangıç sayısı olarak kalır.
- **Spotify Sync:** global opt-in yalnız sonraki eklemeleri otomatik kuyruğa alır. Mevcut eksikler ayrı "eksikleri indir" eylemiyle kalır; ilk sync baseline alır.
- **Port:** bu programda `8000` publish davranışı değiştirilmez. LAN/tailnet erişimi korunur; loopback kararı ayrı onay ister.
- **Deploy:** her faz worktree'de commit edilir; faz kapısı geçince `feat/personal-server-program` → `feat/collections` fast-forward/merge alınır, `~/bin/downtify-deploy.sh` çalıştırılır ve canlı HEAD/health doğrulanır.
- **Library Health:** ilk sürüm salt okunur rapor; yazılan düzeltme ucu yoktur.
- **Loudness/ReplayGain:** ilk sürüm opt-in analiz/rapor ve oynatıcıda gain önerisi; dosya etiketine yazım yoktur.

## 7. Uygulama sırası ve kabul ölçütleri

Her faz sırayla yapılır; paralel ürün kodu yazılmaz.

| Faz | Çıktı | Kabul ölçütü |
|---|---|---|
| 0 | Worktree, bağımlılıklar, baseline test | pytest + Vitest + build yeşil; mevcut fail yoksa ilerle |
| 1 | Oynatma hafızası + Stats | İki cihazda aynı parça konumu; süre/atlama testleri; 8 dil |
| 2 | Spotify Sync otomatik eksik indirme | Diff önizleme; opt-in; mükerrer kuyruk yok; offline test |
| 3 | Başarısızlık merkezi | Hata detayı; yeniden dene/hariç tut; token sızıntısı yok |
| 4 | Birleşik arama | Yerel + uzak sonuç; duplicate işareti; mevcut arama testleri yeşil |
| 5 | Bildirim + Telegram | Test mesajı; olay gruplama; admin chat doğrulaması; sır maskeleme |
| 6 | Yedek/geri yükleme | Atomik yazım; iki kopya; dry-run; boş sunucuda geri yükleme testi |
| 7 | Kuyruk önceli + sessiz saatler | Restart sonrası sıra; çalışan iş kesilmiyor; DST testi |
| 8 | Collections güç araçları | Üye çıkarma; OR/NOT; önizleme; kapak; oynat/analiz |
| 9 | Library Health | Salt okunur tarama; kategoriler; redakte export; otomatik düzeltme yok |
| 10 | Söz sağlığı + ofset | Senkron arama; toplu tarama; ofset kalıcılığı; format testleri |
| 11 | Hızlı kazanımlar | Queue→playlist; artist watch; Similar bulk; stream resume |
| 12 | Büyük adaylar | Playlist-albüm; Monitor dry-run/Wanted; offline PWA; storage; loudness |
| 13 | Güvenlik + doküman + final | Port/CSP/0600/mirror/href; tüm test/build/docs; deploy health |

## 8. Test ve doğrulama stratejisi

- Her özellik için önce kırmızı test/regresyon testi yazılacak.
- Backend: `uv run pytest`; ilgili test paketleri hızlı, tam paket faz sonunda.
- Frontend: `npm --prefix frontend test` ve `npm --prefix frontend run build`.
- Doküman: `npm --prefix docs test` ve `npm --prefix docs run build`.
- Lint: `ruff check`, `ruff format --check`, Prettier ilgili dosyalarda.
- Kullanıcı davranışı değişen her fazda README + ilgili `docs/features/*.md` güncellenir.
- İndirme davranışı değişen fazlarda gerçek bir parça ve playlist ile metadata/cover/lyrics kontrol edilir; ağ yoksa bu adım açıkça "doğrulanmadı" olarak kaydedilir.
- Her deploy sonrası `/api/health`, container health ve ilgili yeni uç kontrol edilir.

## 9. Riskler ve geri dönüş

- Büyük kapsam nedeniyle sıralı ilerleme ve ayrı commitler şart.
- Spotify/YouTube/Deezer dış servis davranışları değişebilir; testler offline, canlı doğrulama ayrı.
- Worktree deploy komutu ana çalışma dalını kullanabilir; bu yüzden deploy öncesi dal/HEAD doğrulanacak ve gerekirse commit ana dala seçici olarak alınacak.
- Cloudflare ingress dış bağımlılığı varsa port değişikliği kullanıcı onayı olmadan yapılmayacak.
- Yedek dosyası token içerir; `0600`, şifreleme seçeneği ve açık uyarı korunacak.
- Rollback: mevcut `downtify-fork:pre-v4` imajı ve her fazın ayrı commiti.

## 10. Planlayıcıya bırakılanlar

- Dosya bazlı görev kırılımı ve test listesi.
- Mevcut yardımcı fonksiyonların birebir seçimi.
- Küçük API alanı adları ve UI metinleri.
- Worktree içinde test ortamının Docker konteyner düzeni.
