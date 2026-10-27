# EC / ACPI haritası: Casper Excalibur G900 (kart NLCB 001)

[English](EC-MAP.md) | **Türkçe**

Kaynak: bu dizüstünün DSDT tablosu (Insyde, `CML`); `casper-ctl discover` ve `casper-ctl ec-fields` ile çözüldü.
"Gözlenen", çalışan makinede görülen demektir. "Çıkarım", DSDT kodundan okunan ve henüz bir testle doğrulanmayan demektir.

## EC bölgesi

`OperationRegion (ERAM, EmbeddedControl, Zero, 0xFF)`; Linux `ec_sys` debugfs dosyası
(`/sys/kernel/debug/ec/ec0/io`) üzerinden erişilir. Yazma için `ec_sys write_support=1` gerekir.

## Kullanılan alanlar

Ofsetler `bayt.bit` biçimindedir. Adlar DSDT'den gelir.

| Alan | Ofset | Genişlik | Anlamı |
|---|---|---|---|
| `LKBR` `LKBG` `LKBB` | 0x89 0x8A 0x8B | 8 | Klavye R, G, B. Gözlenen: el sıkışma ile yazınca renk değişti |
| `LKBL` | 0xC1.0 | 4 | Klavye seviyesi. DSDT 0, 1, 2 kullanır (çıkarım: parlaklık seviyeleri) |
| `LKBM` | 0xC1.4 | 4 | Klavye modu (anlamı çözülmedi) |
| `LKBA` | 0xAA.4 | 4 | Klavye efekt/animasyon değeri (anlamı çözülmedi) |
| `LKCC` `LKBE` `LKBC` `LKBS` | 0xAA.0 .1 .2 .3 | 1 | Onay (commit), alındı, değişiklik bayrağı, kaydet |
| `RGBK` | 0xC0.7 | 1 | Bu makinede 0 okundu; anlamı bilinmiyor |
| `BLIS` | 0xC3.2 | 1 | Arka ışık durumu, Fn arka ışık tuşu işleyicisinde kullanılır (çıkarım) |
| `FN1R` `FN2R` | 0xCA 0xCC | 16 | Fan 1 / fan 2 devri (RPM), **önce yüksek bayt** (gözlenen: 2650-4200 RPM aralığı) |
| `RPM1` `RPM2` | 0xB2 0xB3 | 8 | Takometre değerlerinin düşük baytı; tek başına işe yaramaz |
| `RTMP` | 0x58 | 8 | Sıcaklık, °C (gözlenen: coretemp ile uyumlu) |
| `FANM` | 0xC3.0 | 1 | Fn fan tuşu işleyicisine bildirilen fan-maks durumu (çıkarım); gözlenen 0 |
| `FANE` `FAND` | 0xD2.2 .3 | 1 | WMI fonksiyonu 0xFB00/0x0200 seçici 1 ile yazılan tek seferlik fan komut bitleri |
| `SFAN` | 0xF4 | 8 | Tanımlı ama DSDT'de hiç kullanılmıyor |
| `CBSC` | 0xA3 | 8 | Son Fn tuşu olay kodu: 0x10 arka ışık, 0x11 fan, 0x12 diğer (`_Qxx` kodundan) |
| `DWNK` | 0x50.0 | 1 | Windows tuşu kilidi (WMI seçici 0 ile yazılır) |

## Klavye protokolü

`\_SB.GWMI.WSAA`, fonksiyon `0xFB00`, alt fonksiyon `0x0100` (DSDT 60797. satırdan itibaren):

1. `LKBC` = 0
2. `LKBA`, `LKBB`, `LKBG`, `LKBR` = değerler
3. `LKBL` girdi seviyesinden (DSDT girdi 0, 1, 2 değerlerini `LKBL` 2, 0, 1 değerlerine eşler)
4. `LKBM` = mod
5. `LKCC` = 1; `LKBE` = 1 olana kadar bekle
6. `LKBE` = 0; `LKBS` = 1; `LKBE` = 1 olana kadar bekle

`casper-ctl` bunu `kbd_ec_set` olarak uygular (çağrı başına bir el sıkışma). Gözlenen: yeşil (`00FF00`) uygulandı ve EC her iki
beklemeyi de onayladı.

## Fanlar

- İki fan var. RPM okuması çalışır (`fan-status`).
- Gözlenen: `FAND` = 1 bir kez yazmak, ilk örnekte aynı sıcaklıkta RPM'i değiştirmedi. `FAND` temizlenene kadar 1'de kaldı.
  Sonuçsuz; buna güvenmeyin.
- DSDT'de fan hızı yazan bir kod yok. Windows yazılımı fan eğrisi ayarlıyorsa, büyük olasılıkla `WMIA.WMCB` yöntemi ve EC komut
  arayüzü (`ECMD`, `ECXC`) üzerinden yapıyordur. Henüz incelenmedi.

## WMI blokları (`casper-ctl discover` çıktısından)

| GUID | ACPI kapsamı | Nesne | Tür |
|---|---|---|---|
| `86CCFD48-205E-4A77-9C48-2021CBEDE341` | `_SB.WMTF` | `WMTF` | yöntem |
| `2BC49DEF-7B15-4F05-8BB7-EE37B9547C0B` | `_SB.WFDE` | `WMDE` | yöntem |
| `A6FEA33E-DABF-46F5-BFC8-460D961BEC9F` | `_SB.WFDE` | | olay 0xD0 |
| `1F13AB7F-6220-4210-8F8E-8BB5E71EE969` | `_SB.WFTE` | `WMDE` | yöntem |
| `ABBC0F20-8EA1-11D1-00A0-C90629100000` | `_SB.WMIA` | | olay 0x80 |
| `ABBC0F40` ile `ABBC0F48` (aynı sonek) | `_SB.WMIA` | `BV B1 B2 BL BC BW II GS CT` | veri blokları |
| `101F83BB-30B7-DF11-8D81-0800200C9A66` | `_SB.WMIA` | `WMCB` | yöntem, 255 örnek |
| `644C5791-B7B0-4123-A90B-E93876E0DAAD` | `_SB.GWMI` | `AA` | veri bloğu (`WSAA` tarafından yazılır) |
| `74286D6E-429C-427A-B34B-B5D15D032B05` | `_SB.GWMI` | | olay 0x80 |
| `05901221-D566-11D1-B2F0-00A0C9062910` | birkaç | `CC AE AB` | BMOF (yöntem şemaları) |

## Açık sorular

- `LKBL`, `LKBM`, `LKBA` değerlerinin ne yaptığı (parlaklık adımları, efektler).
- Renk kabul eden bir klavyede `RGBK` = 0'ın ne anlama geldiği.
- Fan kontrolü: `WMIA.WMCB`, `ECMD`/`ECXC` ve `FAND`/`FANE` için eşlik eden bir yazma gerekip gerekmediği.
- RAPL ile yazılan güç sınırlarının kalıcı olup olmadığı ya da EC tarafından sıfırlanıp sıfırlanmadığı.
