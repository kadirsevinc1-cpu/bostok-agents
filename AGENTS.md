# Bostok Agent Köyü — Ortak Bilgi Tabanı

Bu dosyayı her agent başlarken okur. Hatalar, başarılı çözümler ve kurallar burada birikir.

## Temel Kurallar

- Gemini Flash günlük 1M token — tasarruflu kullan, gereksiz tekrar etme
- Her görev sonucunu hafızaya kaydet (save_observation)
- Hata yaparsan çözümü bu dosyaya ekle (HATA LOG bölümüne)
- Müşteri bilgilerini memory/clients.json'a kaydet
- Üretilen siteler output/sites/ altına kaydet

## Bostok.dev Hakkında

- Site: https://bostok.dev
- Ajans: Profesyonel web tasarım ve geliştirme
- Hedef pazar: Türkiye + uluslararası KOBİ'ler
- Teknoloji: HTML5, Tailwind CSS, modern JavaScript
- Fiyat aralığı: 2.000 TL (landing) — 50.000 TL+ (e-ticaret)

## Başarılı Çözümler

### Tasarım
- Tailwind CDN: `<script src="https://cdn.tailwindcss.com"></script>`
- Responsive nav: hamburger menu için `md:hidden` / `hidden md:flex` kullan
- Hero section: min-h-screen + flex items-center justify-center
- Renk paleti önerisi: Slate + Indigo (kurumsal), Amber + Stone (restoran), Emerald + Teal (sağlık)

### SEO
- Her sayfada: title, meta description, og:title, og:description, og:image
- H1 sadece bir kez kullan
- Alt text tüm resimlere

### Formlar
- iletişim formu → Formspree.io entegrasyonu (ücretsiz, 50 form/ay)
- `<form action="https://formspree.io/f/FORM_ID" method="POST">`

### İçerik
- Hero başlığı: net, fayda odaklı, max 10 kelime
- CTA butonu: "Hemen Başlayın", "Ücretsiz Teklif Alın", "Bize Ulaşın"

## Hata Logu

<!-- Hatalar buraya eklenir — format: [Tarih] [Agent] Hata → Çözüm -->

## Şablon Referansları

templates/ klasöründe hazır şablonlar:
- restoran.html — Restoran/Kafe siteleri için
- kurumsal.html — Şirket/KOBİ siteleri için
- landing.html — Tek sayfa kampanya siteleri için
- eticaret.html — Ürün vitrin siteleri için

## Agent İletişim Protokolü

1. Manager → Analyst: ham müşteri talebi
2. Analyst → Manager: structured brief (JSON format)
3. Manager → Quote + Content: brief paralel gönderilir
4. Content → Manager: yazılar tamamlandı
5. Manager → Designer: brief + yazılar
6. Designer → Manager: tasarım rehberi + HTML iskelet
7. Manager → Developer: tasarım + içerik paketi
8. Developer → Manager: dosya yolu + satır sayısı
9. Manager → QA: dosya yolu
10. QA → Manager: rapor (puan + hatalar)
11. Manager → Kullanıcı: demo hazır bildirimi
