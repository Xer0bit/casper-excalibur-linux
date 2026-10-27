# casper-excalibur-linux

[English](README.md) | **Türkçe**

**Casper Excalibur G900** (kart `NLCB 001`, Insyde BIOS, i7-10750H, RTX 2060 Mobile) için Linux desteği.
Casper klavye aydınlatması ile fan ve performans ayarları için yalnızca Windows yazılımı sunar. Bu proje aynı gömülü
denetleyiciyle (EC) ve çekirdek arayüzleriyle Linux üzerinden konuşur:

- `casper-ctl`: tek dosyalık bash komut satırı aracı
- `casper-gui`: GTK3 arayüzü (tek seferlik parola isteği)

EC kayıt haritası, bu dizüstünün kendi ACPI DSDT tablosundan çıkarıldı. Proje Casper tarafından onaylanmış değildir.

**Anahtar kelimeler:** Casper Excalibur G900 Linux, Casper Linux sürücü, Casper klavye RGB ışık rengi Linux,
Casper fan hızı Linux, Casper oyuncu dizüstü Ubuntu, NLCB 001, Insyde BIOS, EC (gömülü denetleyici), ACPI DSDT,
klavye aydınlatma, fan devri (RPM), sıcaklık izleme, CPU güç sınırı (PL1/PL2), turbo, RTX 2060 saat kilidi,
Ubuntu, Debian, GTK3, bash.

## Durum

| Özellik | Durum |
|---|---|
| Klavye rengi (`kbd-color`) | Donanımda çalışıyor |
| Klavye seviye / mod / efekt | Komutlar çalışıyor; değerlerin anlamı henüz çıkarılmadı |
| Açılış ve uykudan dönüşte klavye durumunu koruma | Uygulandı (`install-service`) |
| Fan devri (RPM) ve sıcaklık | Donanımda çalışıyor |
| Fan hızı ayarı | **Yok.** Bu kartın EC fan arayüzü çözülmedi, yalnızca izleme var |
| CPU güç sınırları, turbo, EPP, governor, hazır profiller | Standart sysfs üzerinden |
| GPU saat kilidi / güç sınırı | `nvidia-smi` ile; bu vBIOS güç sınırını `N/A` bildirir |
| GTK arayüzü | Çalışıyor |
| Çevrimdışı test paketi | `tests/run.sh` (sahte EC imajı, donanım gerekmez) |

## Kurulum (Ubuntu)

```
git clone https://github.com/Xer0bit/casper-excalibur-linux.git
cd casper-excalibur-linux
sudo ./install.sh
```

Eksik sürücü ve paketleri bulmak ve kurmak için:

```
sudo casper-ctl doctor          # yalnızca rapor verir
sudo casper-ctl doctor --fix    # eksikleri kurar, sonra tekrar kontrol eder
```

`doctor` şunlara bakar: kart modeli, `ec_sys`, Secure Boot kilidi, `acpica-tools`, GTK3, `pkexec`, NVIDIA sürücüsü,
`intel_pstate` ve RAPL. NVIDIA sürücüsünü yeniden başlatma gerektirdiği için kurmadan önce sorar.

Ayrıntılı rehber (İngilizce): [docs/INSTALL.md](docs/INSTALL.md).

Klavye rengini yeniden başlatma ve uykudan sonra korumak için:

```
sudo casper-ctl kbd-color 00FF00
sudo casper-ctl install-service none
```

Kaldırma: `sudo ./uninstall.sh` (`--purge` ayarları da siler).

## Kullanım

```
sudo casper-ctl status                    # okunabilen tüm durum
sudo casper-ctl kbd-color FF8040          # klavye rengi (RRGGBB)
sudo casper-ctl fan-status [watch]        # iki fan devri ve sıcaklık
sudo casper-ctl preset balanced           # quiet | balanced | performance | max
sudo casper-ctl rapl 45 65                # CPU PL1 / PL2 (watt)
sudo casper-ctl gpu-lock 300 1500         # GPU saat kilidi (MHz)
casper-gui                                # grafik arayüz
```

## Güvenlik

- EC yazma işlemleri yalnızca kart adı `NLCB 001` ise açıktır. Diğer modellerde EC haritası farklıdır.
- Yazılan her EC baytı kaydedilir; `sudo casper-ctl ec-undo` geri alır.
- Sınırlar: PL1 120 W, PL2 135 W üstü ve %30 altı fan hızı, `FORCE=1` olmadan reddedilir.
- Secure Boot açıksa çekirdek kilidi EC yazmasını engelleyebilir; BIOS'tan kapatın.

## Katkı

Başka bir Casper veya Tongfang tabanlı modelin doğrulanmış EC haritasını içeren pull request'ler memnuniyetle
karşılanır. Yöntem için [docs/EC-MAP.md](docs/EC-MAP.md) dosyasına bakın.

## Lisans

MIT. Bkz. [LICENSE](LICENSE).
