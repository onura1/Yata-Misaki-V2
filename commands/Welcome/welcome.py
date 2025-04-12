# commands/Welcome/welcome.py (Config erişimi ve ID dönüşümü güncellendi)
import discord
from discord.ext import commands

class WelcomeCog(commands.Cog, name="Hoş Geldin"): # Yardım komutunun tanıması için Cog adı
    """Yeni üyelere hoş geldin mesajı gönderen Cog."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Config ayarlarına self.bot.config üzerinden erişeceğiz

    def get_channel_id_from_config(self, key: str) -> int | None:
        """Config'den ID alır ve integer'a çevirir, hata durumunda None döner."""
        channel_id_str = self.bot.config.get(key)
        if not channel_id_str:
            print(f"[UYARI] Yapılandırmada '{key}' bulunamadı.")
            return None
        try:
            return int(channel_id_str)
        except ValueError:
            print(f"[HATA] Yapılandırmadaki '{key}' ('{channel_id_str}') geçerli bir sayı değil.")
            return None

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """Bir üye sunucuya katıldığında tetiklenir."""
        # Ayarlardan hoş geldin kanalının ID'sini al ve integer'a çevir
        welcome_channel_id = self.get_channel_id_from_config("WELCOME_CHANNEL_ID")
        if not welcome_channel_id:
            return # ID alınamadıysa veya geçersizse devam etme

        # Kanal nesnesini ID ile bul
        kanal = self.bot.get_channel(welcome_channel_id)

        if kanal:
            sunucu = member.guild
            uye_sayisi = sunucu.member_count # Güncel üye sayısı

            # Diğer kanal ID'lerini config'den al (.get ile, yoksa varsayılan '#')
            # Not: get_channel_id_from_config burada kullanılmadı, çünkü sadece metin içinde geçiyorlar.
            # Eğer bu kanalların nesnelerine ihtiyaç olsaydı, benzer bir kontrol gerekirdi.
            rules_ch_id = self.bot.config.get("RULES_CHANNEL_ID", "#")
            color_role_ch_id = self.bot.config.get("COLOR_ROLE_CHANNEL_ID", "#")
            general_roles_ch_id = self.bot.config.get("GENERAL_ROLES_CHANNEL_ID", "#")
            events_ch_id = self.bot.config.get("EVENTS_CHANNEL_ID", "#")
            giveaways_ch_id = self.bot.config.get("GIVEAWAYS_CHANNEL_ID", "#")
            partnership_rules_ch_id = self.bot.config.get("PARTNERSHIP_RULES_CHANNEL_ID", "#")

            # Mesaj içeriğini f-string ile oluştur
            desc = (
                f"Hoş geldin! Kuralları okumayı unutma <#{rules_ch_id}>.\n"
                f"Kendine bir renk rolü al <#{color_role_ch_id}>.\n"
                f"Rollerimizden uygun olanları almayı unutma <#{general_roles_ch_id}>.\n"
                f"Etkinliklerimize göz at, belki eğlenirsin <#{events_ch_id}>.\n"
                f"Çekilişlerimize katılmayı unutma <#{giveaways_ch_id}>.\n"
                f"Partnerlik şartlarını oku <#{partnership_rules_ch_id}>."
            )

            embed = discord.Embed(
                description=desc,
                color=discord.Color.red() # Rengi de config'e ekleyebilirsin: discord.Color(int(self.bot.config.get("WELCOME_EMBED_COLOR", "0xFF0000"), 16)) gibi
            )

            embed.set_footer(text=f"👥 Şu anda sunucumuzda toplam {uye_sayisi} üye bulunuyor!")

            # Resim URL'sini config'den al (.get ile, yoksa boş string)
            welcome_image_url = self.bot.config.get("WELCOME_IMAGE_URL", "")
            if welcome_image_url:
                embed.set_image(url=welcome_image_url)

            try:
                # Hoş geldin mesajını gönder
                await kanal.send(content=f" Heyy {member.mention}! Yooo! Sen Hoş geldin!", embed=embed)
            except discord.Forbidden:
                print(f"[HATA] {kanal.name} ({kanal.id}) kanalına mesaj gönderme izni yok.")
            except discord.HTTPException as e:
                print(f"[HATA] Hoş geldin mesajı gönderilirken HTTP hatası oluştu: {e}")
            except Exception as e:
                print(f"[HATA] Hoş geldin mesajı gönderilirken beklenmedik hata: {e}")
        else:
            print(f"[HATA] Hoş geldin kanalı (ID: {welcome_channel_id}) bulunamadı.")

# Cog'u bota tanıtmak için gerekli setup fonksiyonu
async def setup(bot: commands.Bot):
    await bot.add_cog(WelcomeCog(bot))
    print("✅ Welcome Cog yüklendi!")