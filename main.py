
"""
Discord E‑Okul Not Sistemi Botu (2025)
--------------------------------------
Bu bot, slash komutları aracılığıyla öğrenci, ders ve not işlemlerini Discord
sunucunuzdan yönetmenizi sağlar. Temel CLI sürümünün (e_okul_not_sistemi_2025.py)
veri modelini ve JSON depolamasını paylaşır, böylece aynı `veri.json` dosyasını
kullanabilirsiniz.

Gereksinimler
~~~~~~~~~~~~~
• Python 3.10+
• discord.py 2.3+  →  ``pip install -U discord.py``

Kurulum
~~~~~~~~
1. Bot uygulaması oluşturup token alın: https://discord.com/developers/applications
2. ``DISCORD_TOKEN`` ortam değişkenine token’ı ekleyin **veya** kod sonundaki
   ``TOKEN = "..."`` satırına yazın.
3. Gerekli kütüphaneleri kurun ve ``python e_okul_not_bot_2025.py`` komutunu
   çalıştırın.

Slash Komutları
~~~~~~~~~~~~~~~
• ``/ders_ekle kod ad kredi`` — Yeni ders ekler.
• ``/ogrenci_ekle no ad sinif`` — Yeni öğrenci ekler.
• ``/not_gir no ders_kodu sinav1 sinav2 proje`` — Not girer/günceller (boş bırakmak
  için -1 kullanın).
• ``/karne no`` — Öğrencinin karnesini görüntüler.

Not → Discord slash komut adlarında Türkçe karakter kullanılamadığından komut
isimleri ASCII tutulmuştur.
"""
import discord
from __future__ import annotations

import json
import os
from dataclasses import dataclass, asdict, field
from pathlib import Path
from statistics import mean
from typing import Dict, List, Optional

import discord
from discord import app_commands
from discord.ext import commands

# ---------------------------------------------------------------------------
# Veri Modelleri (CLI sürümünden aynen alındı)
# ---------------------------------------------------------------------------

@dataclass
class Ders:
    kod: str
    ad: str
    kredi: int = 1

@dataclass
class NotKaydi:
    ders_kodu: str
    sinav1: Optional[float] = None
    sinav2: Optional[float] = None
    proje: Optional[float] = None

    def ortalama(self) -> Optional[float]:
        puanlar = [p for p in (self.sinav1, self.sinav2, self.proje) if p is not None]
        return mean(puanlar) if puanlar else None

    def harf_notu(self) -> Optional[str]:
        ort = self.ortalama()
        if ort is None:
            return None
        if ort >= 90:
            return "AA"
        elif ort >= 85:
            return "BA"
        elif ort >= 80:
            return "BB"
        elif ort >= 70:
            return "CB"
        elif ort >= 60:
            return "CC"
        elif ort >= 50:
            return "DC"
        elif ort >= 40:
            return "DD"
        else:
            return "FF"

@dataclass
class Ogrenci:
    no: str
    ad: str
    sinif: str
    notlar: Dict[str, NotKaydi] = field(default_factory=dict)

    def genel_ortalama(self) -> Optional[float]:
        ortalamalar = [nk.ortalama() for nk in self.notlar.values() if nk.ortalama() is not None]
        return mean(ortalamalar) if ortalamalar else None

# ---------------------------------------------------------------------------
# Veri Yönetimi
# ---------------------------------------------------------------------------

DATA_FILE = Path("veri.json")

class DataManager:
    def __init__(self):
        self.data = self._load()

    # ---------------------- IO ---------------------- #
    def _default(self) -> dict:
        return {"ogrenciler": {}, "dersler": {}}

    def _load(self) -> dict:
        if DATA_FILE.exists():
            with DATA_FILE.open("r", encoding="utf-8") as f:
                return json.load(f)
        return self._default()

    def _save(self):
        with DATA_FILE.open("w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)

    # ---------------------- Ders --------------------- #
    def ders_ekle(self, kod: str, ad: str, kredi: int = 1) -> bool:
        kod = kod.upper()
        if kod in self.data["dersler"]:
            return False
        self.data["dersler"][kod] = asdict(Ders(kod, ad, kredi))
        self._save()
        return True

    # -------------------- Öğrenci -------------------- #
    def ogrenci_ekle(self, no: str, ad: str, sinif: str) -> bool:
        if no in self.data["ogrenciler"]:
            return False
        self.data["ogrenciler"][no] = asdict(Ogrenci(no, ad, sinif))
        self._save()
        return True

    # ---------------------- Not ---------------------- #
    def not_gir(self, no: str, ders_kodu: str, s1: float | None, s2: float | None, prj: float | None) -> str:
        if no not in self.data["ogrenciler"]:
            return "Öğrenci bulunamadı."
        if ders_kodu.upper() not in self.data["dersler"]:
            return "Ders bulunamadı."
        ogr = self.data["ogrenciler"][no]
        nk = ogr["notlar"].get(ders_kodu.upper(), {})
        if s1 is not None:
            nk["sinav1"] = s1
        if s2 is not None:
            nk["sinav2"] = s2
        if prj is not None:
            nk["proje"] = prj
        ogr["notlar"][ders_kodu.upper()] = nk
        self._save()
        return "Notlar güncellendi."

    # ------------------- Karne ----------------------- #
    def karne(self, no: str) -> Optional[str]:
        if no not in self.data["ogrenciler"]:
            return None
        ogr = Ogrenci(**self.data["ogrenciler"][no])
        satirlar = [
            f"Öğrenci: {ogr.ad} ({ogr.no})  Sınıf: {ogr.sinif}",
            "-----------------------------------------",
            f"{'Ders':<10} {'S1':>5} {'S2':>5} {'PR':>5} {'Ort':>6} {'Harf':>5}",
        ]
        for ders_kodu, nk_dict in ogr.notlar.items():
            nk = NotKaydi(**nk_dict)
            satirlar.append(
                f"{ders_kodu:<10} {nk.sinav1 or '-':>5} {nk.sinav2 or '-':>5} "
                f"{nk.proje or '-':>5} {nk.ortalama() or '-':>6} {nk.harf_notu() or '-':>5}"
            )
        satirlar.append("-----------------------------------------")
        genel = ogr.genel_ortalama()
        satirlar.append(f"Genel Ortalama: {genel:.2f}" if genel else "Genel Ortalama: -")
        return "\n".join(satirlar)

# ---------------------------------------------------------------------------
# Discord Bot Tanımı
# ---------------------------------------------------------------------------

data_mgr = DataManager()

class EOkulBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(command_prefix="/", intents=intents)

    async def on_ready(self):
        print(f"✅ Bot giriş yaptı: {self.user} (ID: {self.user.id})")
        try:
            synced = await self.tree.sync()
            print(f"🌐 {len(synced)} komut senkronize edildi.")
        except Exception as e:
            print("🔴 Komut senkronizasyon hatası:", e)

bot = EOkulBot()

# ----------------------- Slash Komutları ----------------------- #

@bot.tree.command(name="ders_ekle", description="Yeni ders ekle")
@app_commands.describe(kod="Ders kodu (örn: MAT101)", ad="Ders adı", kredi="Kredi (varsayılan 1)")
async def ders_ekle(inter: discord.Interaction, kod: str, ad: str, kredi: int = 1):
    if data_mgr.ders_ekle(kod, ad, kredi):
        await inter.response.send_message("✅ Ders eklendi.", ephemeral=True)
    else:
        await inter.response.send_message("❗ Bu ders kodu zaten mevcut!", ephemeral=True)

@bot.tree.command(name="ogrenci_ekle", description="Yeni öğrenci ekle")
@app_commands.describe(no="Öğrenci numarası", ad="Ad Soyad", sinif="Sınıf (örn: 10-A)")
async def ogrenci_ekle(inter: discord.Interaction, no: str, ad: str, sinif: str):
    if data_mgr.ogrenci_ekle(no, ad, sinif):
        await inter.response.send_message("✅ Öğrenci eklendi.", ephemeral=True)
    else:
        await inter.response.send_message("❗ Bu numara zaten kayıtlı!", ephemeral=True)

@bot.tree.command(name="not_gir", description="Not gir / güncelle")
@app_commands.describe(
    no="Öğrenci numarası",
    ders_kodu="Ders kodu (örn: MAT101)",
    sinav1="Sınav 1 (boş için -1)",
    sinav2="Sınav 2 (boş için -1)",
    proje="Proje (boş için -1)",
)
async def not_gir(
    inter: discord.Interaction,
    no: str,
    ders_kodu: str,
    sinav1: float,
    sinav2: float,
    proje: float,
):
    s1 = None if sinav1 == -1 else sinav1
    s2 = None if sinav2 == -1 else sinav2
    pr = None if proje == -1 else proje
    sonuc = data_mgr.not_gir(no, ders_kodu, s1, s2, pr)
    await inter.response.send_message(sonuc, ephemeral=True)

@bot.tree.command(name="karne", description="Öğrencinin karnesini göster")
@app_commands.describe(no="Öğrenci numarası")
async def karne(inter: discord.Interaction, no: str):
    rapor = data_mgr.karne(no)
    if rapor is None:
        await inter.response.send_message("❗ Öğrenci bulunamadı.", ephemeral=True)
    else:
        # Discord mesaj uzunluğu sınırlı, bu nedenle raporu ````` bloğu içinde gönderiyoruz.
        await inter.response.send_message(f"```\n{rapor}\n```", ephemeral=False)

# ---------------------------------------------------------------------------
# Çalıştır
# ---------------------------------------------------------------------------

def main():
    token = os.getenv("")
    if token == "" or not token:
        raise RuntimeError("Bot token'ınızı kodun sonundaki TOKEN değişkenine veya DISCORD_TOKEN ortam değişkenine ekleyin!")
    bot.run()

if __name__ == "__main__":
    main("bot.token")