# Expanded Diagnostic Motion — Kısa Tasarım

**Tarih:** 2026-11-23 · **Onay:** "hepsi güzel hepsini ekle" (yeet)

## Intent

Downtify UI'sında hareket çeşitliliği yetersiz. İlk tur (100ms opacity fade) yetmedi; kullanıcı 4 varyantın tamamını ve daha fazlasını istiyor. v4 "The Printing Desk" kimliği korunur, motion maddesi genişletilir.

## Yaklaşımlar

1. **Doktrin sabit, kapsam geniş** — reddedildi; aynı sade dil yetersiz kaldı.
2. **Doktrin güncellenmiş, paketsiz (seçilen)** — renk/tipografi/ızgara aynen; motion "diagnostic and legible", 80–240ms, opacity/transform + steps. CSS token/keyframe + mevcut Vue `<Transition>`'lar.
3. **JS motion kütüphanesi / MCP** — ertelendi; bağımlılık + "nothing springs, floats or glows" kuralıyla çelişki. Ayrı turda değerlendirilecek.

## Kararlar

- Palet/ızgara dokunulmaz: #F3F3F0 / #171717 / #0047FF, 0 radius, 2px çizgi, light default + tam dark inversion.
- Onaylanan 4 aile: stepped reveal (220ms steps(4)), list stagger (160ms + 22ms/satır), panel slide (200ms steps(5)), seek glide + eq + shimmer (240ms / steps(4) / steps(6)).
- Ek aileler (aynı dilde): sayısal sayaç (stepped increment), odak halkası izi (2px outline, adımlı), toast girişi (stepped), chip/satır hover geri bildirimi (opacity), sıralama sonrası satır ötelemesi (transform), yön duyarlı sayfa geçişi (opacity + kısa translate).
- Süre aralığı 80–240ms; `linear` veya `steps(n)`; yalnız opacity/transform/background-position. Yay, yüzdürme, parlama, gölge, blur, buton scale YOK.
- `prefers-reduced-motion`: her ailenin statik son durumu var; global `1ms !important` katili kullanılmıyor.
- Yeni bağımlılık YOK, yeni MCP YOK.

## Kısıtlar

- Kapılar: `npm test`, `npm run build` geçmeli. `format:check` repo-geneli mevcut kırık (298 dosya) — dokunulmaz.
- Deploy: `ssh home '~/bin/downtify-deploy.sh'`. Rollback: `downtify-fork:pre-v4`.
- `mirror/lockfile` ve `w6/` untracked — asla commit edilmez.
- Kod işi ücretsiz model zinciriyle.

## Uygulayıcıya bırakılan

Hangi bileşende hangi ailenin kullanılacağı, kesin gecikme değerleri ve statik CSS testlerinin kapsamı uygulayıcının kararı; yukarıdaki doktrini aşmamak koşuluyla.
