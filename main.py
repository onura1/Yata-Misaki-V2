# main.py (Logging Kaldırıldı, config.json Kullanılıyor)

# ----- Gerekli Kütüphaneler -----
import discord
from discord.ext import commands
import os
import asyncio
from dotenv import load_dotenv # .env dosyasını okumak için
from flask import Flask      # Keep-alive için
from threading import Thread # Keep-alive için
import time                  # Botun başlangıç zamanı için
import json                  # config.json okumak için
import traceback             # Detaylı hata yazdırma için

# ----- .env dosyasını yükle (Token için) -----
load_dotenv()
print(".env dosyası yüklendi (eğer varsa).")
BOT_TOKEN = os.getenv("DISCORD_TOKEN") # Token'ı ortam değişkeninden al

# ----- Yapılandırmayı Yükle (config.json) -----
config = {} # Başlangıçta boş yapılandırma sözlüğü
CONFIG_FILE_PATH = "config.json" # Yapılandırma dosyasının adı

try:
    # config.json dosyasını oku
    with open(CONFIG_FILE_PATH, 'r', encoding='utf-8') as f:
        config = json.load(f) # JSON verisini sözlüğe yükle
    print(f"'{CONFIG_FILE_PATH}' dosyasından yapılandırma başarıyla yüklendi.")
except FileNotFoundError:
    print(f"[HATA] Yapılandırma dosyası '{CONFIG_FILE_PATH}' bulunamadı! Bot düzgün çalışmayabilir.")
    config = {"PREFIX": "!"} # Varsayılan prefix ata
    print("[UYARI] Varsayılan prefix '!' olarak ayarlandı.")
except json.JSONDecodeError:
    print(f"[HATA] Yapılandırma dosyası '{CONFIG_FILE_PATH}' geçerli bir JSON formatında değil! Lütfen kontrol edin.")
    config = {"PREFIX": "!"}
    print("[UYARI] Varsayılan prefix '!' olarak ayarlandı.")
except Exception as e:
     print(f"[HATA] Yapılandırma dosyası '{CONFIG_FILE_PATH}' okunurken beklenmedik bir hata oluştu: {e}")
     config = {"PREFIX": "!"}
     print("[UYARI] Varsayılan prefix '!' olarak ayarlandı.")

# BOT_TOKEN'ı .env'den okunan değerle yapılandırma sözlüğüne ekle
config["BOT_TOKEN"] = BOT_TOKEN

# ----- Discord Bot Ayarları (Intents) -----
intents = discord.Intents.default()
intents.members = True      # Üye katılım/ayrılma olayları için
intents.message_content = True # Mesaj içeriğini okuma izni (komutlar için)
print("Discord Intent'leri ayarlandı.")

# ----- Bot Nesnesini Oluşturma -----
# Prefix'i config dosyasından veya varsayılan olarak al
bot_prefix = config.get("PREFIX", "!")
if bot_prefix == "!":
    print(f"[UYARI] Yapılandırmadan prefix okunamadığı için varsayılan prefix '{bot_prefix}' kullanılıyor.")

bot = commands.Bot(
    command_prefix=bot_prefix, # Yapılandırmadan gelen prefix'i kullan
    intents=intents,           # Ayarlanan intent'leri kullan
    help_command=None,         # Kendi yardım komutumuzu kullanacağız
    case_insensitive=True      # Komutları büyük/küçük harf duyarsız yap
)
# Hazırlanan yapılandırma sözlüğünü bot nesnesine ata
bot.config = config
# Botun başlangıç zamanını kaydet (uptime komutu için)
bot.start_time = time.time()
print("Discord Bot nesnesi oluşturuldu ve yapılandırma atandı.")
print(f"Kullanılacak Prefix: {bot_prefix}")

# ----- Botu Ayakta Tutma (Keep Alive - Flask) -----
# (Bu kısım hosting platformuna göre gerekli olabilir, örn: Replit, Glitch)
app = Flask('')
@app.route('/')
def home():
    return "Yata Misaki Bot Aktif!"
def run_flask():
    port = int(os.environ.get('PORT', 8080)) # Ortam değişkeninden port al (varsayılan 8080)
    # Flask'ın kendi loglarını azaltmak isteyebilirsiniz:
    # import logging
    # log = logging.getLogger('werkzeug')
    # log.setLevel(logging.ERROR)
    try:
        app.run(host='0.0.0.0', port=port)
    except Exception as e:
        print(f"[FLASK HATA] Keep-alive sunucusu başlatılamadı: {e}")

def keep_alive():
    print("Keep-alive sunucusu başlatılıyor...")
    server_thread = Thread(target=run_flask)
    server_thread.daemon = True # Ana program kapanınca thread'in de kapanmasını sağlar
    server_thread.start()
    print(f"Keep-alive sunucusu {os.environ.get('PORT', 8080)} portunda başlatıldı.")

# ----- Temel Bot Olayları -----
@bot.event
async def on_ready():
    """Bot başarıyla Discord'a bağlandığında ve hazır olduğunda çalışır."""
    print("-" * 30)
    print(f'Bot olarak giriş yapıldı: {bot.user.name} (ID: {bot.user.id})')
    print(f'Discord.py Sürümü: {discord.__version__}')
    print(f'{len(bot.guilds)} sunucuda aktif.')
    print(f"Yüklü Cog'lar: {', '.join(bot.cogs.keys()) if bot.cogs else 'Yok'}")
    print("-" * 30)
    try:
        # Durum için prefix'i config'den al (artık 'yardim' ana komut)
        status_prefix = bot.config.get("PREFIX", "!")
        await bot.change_presence(activity=discord.Game(name=f"{status_prefix}yardim | Yata Misaki"))
        print("Bot durumu ayarlandı.")
    except Exception as e:
        print(f"[HATA] Bot durumu ayarlanırken hata oluştu: {e}")

@bot.event
async def on_message(message: discord.Message):
    """Gelen her mesajda çalışır."""
    # Botun kendi mesajlarını veya DM'leri (eğer bot DM komutlarını desteklemiyorsa) yoksay
    if message.author.bot:
        return
    # Komutları işlemesi için bot'a gönder
    await bot.process_commands(message)

# Genel komut hatası yakalayıcı
@bot.event
async def on_command_error(ctx: commands.Context, error):
    """Komutlarda oluşan ve özel olarak yakalanmayan hataları yakalar."""
    # Eğer komutun kendi özel hata yakalayıcısı varsa (örn: @komut.error), bu genel yakalayıcı çalışmasın
    if hasattr(ctx.command, 'on_error'):
        return

    # Bilinen hata türlerini daha kullanıcı dostu yönet
    if isinstance(error, commands.CommandNotFound):
        # Bilinmeyen komut yazıldığında sessiz kalabilir veya uyarı verebiliriz
        # print(f"[UYARI] Bilinmeyen komut: {ctx.invoked_with}")
        pass # Şimdilik bir şey yapma
    elif isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"⏳ Bu komutu tekrar kullanmak için lütfen {error.retry_after:.1f} saniye bekleyin.", delete_after=5)
    elif isinstance(error, commands.MissingRequiredArgument):
        print(f"[UYARI] '{ctx.command.name}' komutunda eksik argüman: {error.param.name} ({ctx.author})")
        # Yardımcı bir mesaj gönderelim
        await ctx.send(f"❌ Eksik argüman: `{error.param.name}`. Doğru kullanım için `{bot.config.get('PREFIX', '!')}yardim {ctx.command.name}` yazabilirsin.")
    elif isinstance(error, commands.CheckFailure): # Genel yetki hatası (is_owner, has_permissions vb.)
        print(f"[UYARI] Yetkisiz komut denemesi: {ctx.command.name} ({ctx.author})")
        await ctx.send("❌ Bu komutu kullanma izniniz yok!")
    elif isinstance(error, commands.CommandInvokeError):
         # Komutun çalıştırılması sırasında bir hata oluştuysa
         original_error = error.original # Asıl hatayı al
         print(f"[HATA] '{ctx.command.name}' komutu çalıştırılırken hata oluştu: {original_error.__class__.__name__}: {original_error}")
         # Hatanın tam dökümünü yazdırmak için:
         # traceback.print_exception(type(original_error), original_error, original_error.__traceback__)
         await ctx.send("⚠️ Komut işlenirken bir sorunla karşılaşıldı.") # Kullanıcıya genel mesaj
    else:
        # Diğer tüm beklenmedik hatalar
        print(f"[HATA] İşlenmemiş bir komut hatası oluştu ({ctx.command.name if ctx.command else 'Bilinmiyor'}): {error.__class__.__name__}: {error}")
        traceback.print_exc() # Hatanın tam dökümünü konsola yazdır

# ----- Cog'ları Yükleme Fonksiyonu -----
async def load_extensions():
    """'commands' klasöründeki alt klasörlerde bulunan tüm .py dosyalarını Cog olarak yükler."""
    print("-" * 30)
    print("Cog'lar yükleniyor...")
    loaded_cogs = 0
    total_files_attempted = 0
    commands_dir = './commands' # Cog'ların bulunduğu ana klasör

    if not os.path.exists(commands_dir) or not os.path.isdir(commands_dir):
        print(f"[HATA] Cog klasörü '{commands_dir}' bulunamadı!")
        print("-" * 30)
        return

    # 'commands' klasöründeki öğeleri (alt klasörleri) tara
    for folder_name in os.listdir(commands_dir):
        folder_path = os.path.join(commands_dir, folder_name)
        # Eğer öğe bir klasörse
        if os.path.isdir(folder_path):
            # Bu alt klasörün içindeki dosyaları tara
            for filename in os.listdir(folder_path):
                file_path = os.path.join(folder_path, filename)
                # Eğer dosya .py ile bitiyorsa ve özel __init__.py değilse
                if filename.endswith('.py') and filename != '__init__.py' and os.path.isfile(file_path):
                    total_files_attempted += 1
                    # Uzantı adını oluştur (örn: commands.Owner.status)
                    extension_name = f'commands.{folder_name}.{filename[:-3]}'
                    try:
                        # Uzantıyı (Cog'u) yükle
                        await bot.load_extension(extension_name)
                        # Başarı mesajı Cog'un kendi setup fonksiyonundan gelecek (print olarak)
                        loaded_cogs += 1
                    except commands.errors.NoEntryPointError:
                         print(f"[HATA] '{extension_name}' yüklenemedi: 'setup' fonksiyonu bulunamadı veya hatalı.")
                    except commands.errors.ExtensionAlreadyLoaded:
                        print(f"[UYARI] '{extension_name}' zaten yüklüydü, tekrar yüklenmiyor.")
                    except commands.errors.ExtensionNotFound:
                         print(f"[HATA] '{extension_name}' yüklenemedi: Uzantı bulunamadı. Yolu ve dosya adını kontrol edin.")
                    except Exception as e:
                        # Diğer yükleme hataları (örn: Cog içindeki syntax hatası)
                        print(f"[HATA] '{extension_name}' yüklenirken beklenmedik bir sorun oluştu: {e.__class__.__name__}: {e}")
                        traceback.print_exc() # Hatanın detayını yazdır

    # Yükleme sonucunu bildir
    if total_files_attempted > 0:
        print(f"{loaded_cogs}/{total_files_attempted} Cog dosyası başarıyla yüklendi.")
    else:
        print(f"[UYARI] '{commands_dir}' altında yüklenecek Cog dosyası bulunamadı.")
    print("-" * 30)

# ----- Botu Başlatma -----
async def main():
    """Ana bot başlatma ve çalıştırma fonksiyonu."""
    print("Bot başlatma süreci başlıyor...")
    # Token'ı config sözlüğünden tekrar kontrol et
    bot_token_from_config = bot.config.get("BOT_TOKEN")
    if not bot_token_from_config:
        print("[KRİTİK HATA] DISCORD_TOKEN bulunamadı (.env veya config)! Bot başlatılamıyor.")
        return

    # Keep Alive sunucusunu (varsa) başlat
    if 'FLASK_RUN' in os.environ: # Veya başka bir kontrol mekanizması
       keep_alive()

    # Bot context yöneticisi ile başlatılıyor
    async with bot:
        # Cog'ları yükle
        await load_extensions()
        print("Bot Discord'a bağlanıyor...")
        # Botu başlat (token ile)
        await bot.start(bot_token_from_config)

# Ana program bloğu
if __name__ == "__main__":
    # Keep-alive gerektiren platformdaysa Flask'ı etkinleştirmek için bir ortam değişkeni ayarlanabilir
    # Örn: Glitch için package.json'daki start script'i `FLASK_RUN=1 python main.py` yapabiliriz.
    run_keep_alive = os.getenv('RUN_KEEP_ALIVE', 'false').lower() == 'true'
    if run_keep_alive:
         keep_alive() # Eğer ortam değişkeni ayarlıysa Flask'ı başlat

    try:
        # Ana asenkron fonksiyonu çalıştır
        asyncio.run(main())
    except KeyboardInterrupt:
        # Ctrl+C ile manuel kapatma
        print("\nBot manuel olarak kapatıldı.")
    except discord.LoginFailure:
        # Geçersiz token hatası
        print("[KRİTİK HATA] Geçersiz Discord Token! Lütfen .env dosyasını kontrol edin.")
    except discord.PrivilegedIntentsRequired:
         # Gerekli Intent'ler etkinleştirilmemişse
         print("[KRİTİK HATA] Gerekli Intent'ler (Members/Message Content) Discord Developer Portal'da etkin değil!")
    except Exception as e:
        # Diğer tüm beklenmedik hatalar
        print(f"[KRİTİK HATA] Bot çalışırken yakalanamayan ana hata oluştu!")
        traceback.print_exc() # Hatanın tam dökümünü yazdır