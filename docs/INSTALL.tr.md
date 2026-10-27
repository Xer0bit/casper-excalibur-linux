# Ubuntu üzerinde kurulum

[English](INSTALL.md) | **Türkçe**

Desteklenen sistemler: Ubuntu 22.04, 24.04 ve üstü (Debian tabanlı türevler de), standart `linux-generic` çekirdeği.
Casper Excalibur G900 (kart `NLCB 001`) üzerinde, Ubuntu 26.04 ve çekirdek 7.0 ile test edildi.

## 1. Gereksinimler

| Gerekli | Neden | Nereden gelir |
|---|---|---|
| Casper Excalibur G900 (`NLCB 001`) | EC yazma (klavye rengi) yalnızca bu kartta açıktır | donanım |
| `ec_sys` çekirdek modülü | gömülü denetleyici (EC) erişimi | standart Ubuntu çekirdeği |
| Secure Boot **kapalı** | çekirdek kilidi EC yazmasını ve imzasız DKMS modüllerini engeller | BIOS ayarı |
| NVIDIA özel sürücüsü | GPU durumu, saat kilidi | `ubuntu-drivers` |
| `acpica-tools` | bu dizüstünün EC haritasını kendi ACPI tablolarından çözer | apt |
| `python3-gi`, `gir1.2-gtk-3.0`, `pkexec` | arayüz ve parola penceresi | apt |

Bunları elle kurmanız gerekmez. `doctor` eksikleri bulur ve kurar.

## 2. Kurulum (üç komut)

```
git clone https://github.com/Xer0bit/casper-excalibur-linux.git
cd casper-excalibur-linux
sudo ./install.sh
```

Ya da hazır paketle: [Releases](https://github.com/Xer0bit/casper-excalibur-linux/releases) sayfasından `.deb` dosyasını indirip
`sudo apt install ./casper-excalibur-linux_0.1.0_all.deb` çalıştırın.

Kurulum betiği apt paketlerini kurar, `casper-ctl` ve `casper-gui` dosyalarını `/usr/local/bin` altına kopyalar, EC haritasını
çözer ve sonunda aşağıdaki sürücü denetimini çalıştırır.

## 3. Eksik sürücüleri bulma ve kurma

```
sudo casper-ctl doctor          # yalnızca rapor verir
sudo casper-ctl doctor --fix    # eksikleri kurar, sonra tekrar denetler
```

Örnek çıktı:

```
ok       board          Casper Excalibur G900 (NLCB 001): all features
ok       ec_sys         embedded controller interface present
MISSING  gtk3           python3-gi / GTK3 typelib (needed by casper-gui)
MISSING  nvidia         NVIDIA GPU found, no working driver (reboot first if you just installed one)
```

| Durum | Anlamı |
|---|---|
| `ok` | var ve çalışıyor |
| `MISSING` | bir özellik çalışmaz; `--fix` apt ile kurabildiklerini kurar |
| `warn` | sınırlı çalışır (örneğin başka bir kart olduğu için EC yazma kapalıdır) |
| `info` | yapılacak bir şey yok |

`--fix` apt paketlerini kurar, `intel_rapl_msr` modülünü yükler, EC haritasını çıkarır ve NVIDIA sürücüsünü
(`ubuntu-drivers install`) kurmadan **önce sorar**, çünkü yeniden başlatma gerekir. Secure Boot'a veya çekirdeğe dokunmaz.

Secure Boot durumunu `mokutil --sb-state` ile kontrol edin. Açıksa `doctor` `warn lockdown` gösterir. BIOS'tan kapatın,
yoksa klavye rengi değişmez.

## 4. İlk çalıştırma

```
sudo casper-ctl status
sudo casper-ctl kbd-color 8000FF       # klavye mor olur
casper-gui                             # veya uygulama menüsünde "Casper" arayın
```

Klavye rengini yeniden başlatma ve uykudan sonra korumak için:

```
sudo casper-ctl install-service none
```

## 5. Sorun giderme

| Belirti | Neden ve çözüm |
|---|---|
| `EC interface unavailable` | `ec_sys` yok ya da debugfs bağlı değil. `doctor` çalıştırın; standart çekirdeği kullanın |
| Renk komutu başarılı ama klavye değişmiyor | Secure Boot çekirdek kilidi. Kapatıp yeniden başlatın |
| Sürücü kurulumundan hemen sonra `nvidia-smi` hata veriyor | Bir kez yeniden başlatın |
| Arayüz açılmıyor | `doctor` `gtk3` eksik diyorsa: `sudo casper-ctl doctor --fix` |
| `preset` sırasında `WARN: no platform_profile`, `no EC fan map` | Bu dizüstünde beklenir: üretici platform sürücüsü yok, fan kayıtları çözülmedi. Fan hızı yalnızca izlenebilir |
| Farklı Casper modeli | EC yazma kapalı kalır. CPU ve GPU kontrolleri çalışır. Bkz. [EC-MAP.tr.md](EC-MAP.tr.md) |

## 6. Casper'ın çevrimiçi hizmetleri

Casper'ın dizüstü donanım kontrolleri için, bu projenin doğrulayabildiği, belgelenmiş herkese açık bir API'si yoktur.
Casper'ın Windows araçları aynı gömülü denetleyiciyle konuşur, `casper-ctl` de öyle. Bu yüzden `doctor` sürücüleri kendi
makinenizden (DMI, çekirdek, apt) bulur ve hiçbir Casper sunucusunu çağırmaz. Casper bir API veya sürücü kaynağı
yayımlarsa, bağlantısıyla bir issue açın; eklenebilir.

## 7. Kaldırma

```
sudo ./uninstall.sh            # --purge /etc/casper-ctl dizinini de siler
```

`.deb` ile kurduysanız: `sudo apt remove casper-excalibur-linux` (ayarlar dahil silmek için `purge`).
