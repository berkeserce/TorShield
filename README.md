# TorShield

TorShield, Windows sistemlerde Tor ağı üzerinden güvenli ve hızlı internet bağlantısı sağlayan bir masaüstü uygulamasıdır.

## Özellikler

- Tor ağı üzerinden anonim internet bağlantısı
- Sistem proxy ayarlarını otomatik yönetme
- Optimize edilmiş bağlantı hızı
- Bağlantı durumu ve hız göstergeleri
- Otomatik yeniden bağlanma özelliği
- Sistem tepsisi desteği
- Modern matte siyah arayüz
- Bağlantı geçmişi yönetimi

## Gereksinimler

- Windows 10 veya üzeri
- Python 3.8 veya üzeri
- Tor Expert Bundle (tor klasörü içinde bulunmalıdır)

## Kurulum

1. Gerekli Python paketlerini yükleyin:
```bash
pip install -r requirements.txt
```

2. Tor Expert Bundle'ı indirin ve içeriğini 'tor' klasörüne çıkarın.

## Kullanım

Program otomatik olarak yönetici izniyle başlar:
```bash
python src/main.py
```

### Temel Kullanım
1. "Bağlan" butonuna tıklayarak Tor ağına bağlanın
2. Bağlantı durumunu ve hızını ana ekrandan takip edin
3. Ayarlar menüsünden tercihleri özelleştirin:
   - Başlangıçta otomatik bağlanma
   - Sistem tepsisine küçültme
   - Bağlantı geçmişi kaydetme
   - Bağlantı hızı gösterimi
   - Otomatik yeniden bağlanma süresi

## Güvenlik Özellikleri

- Optimize edilmiş Tor bağlantı protokolü
- Sistem proxy ayarlarının güvenli yönetimi
- Otomatik bağlantı durumu kontrolü
- Güvenli bağlantı kesme ve temizleme

## Lisans

Bu proje MIT lisansı altında lisanslanmıştır. Detaylar için [LICENSE](LICENSE) dosyasına bakın. 