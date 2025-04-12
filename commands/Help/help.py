import discord
from discord.ext import commands
import traceback  # Hata ayıklama için

class HelpCog(commands.Cog, name="Yardım Komutları"):
    """
    Yardım menüsünü oluşturan ve komut listesini embed açıklaması içinde gösteren Cog.
    Sahip komutlarını dinamik olarak alır ve sadece bot sahibine ayrı bir alanda gösterir.
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Sahip komutlarını içeren Cog'ların tam adları
        self.owner_cog_names = {
            "Ping Komutu (Sahip)",
            "Durum Ayarları",
            "Kapatma",
            "Yeniden Başlatma",
            "Aktiflik Süresi (Sahip)"
        }

    @commands.command(
        name="yardim",
        aliases=["help", "komutlar", "yardimkomutu"],
        help="Tüm kullanılabilir komutları listeler."
    )
    async def help_command(self, ctx: commands.Context):
        """
        Belirtilen komut listesini embed'in açıklama kısmında, kategorilere ayrılmış şekilde gösterir.
        Bot sahibi için özel 'Sahip Komutları' bölümünü de dinamik olarak ayrı bir alanda ekler.
        """
        # Prefix'i al
        try:
            if callable(self.bot.command_prefix):
                prefix = (await self.bot.command_prefix(self.bot, ctx.message))[0]
            else:
                prefix = self.bot.command_prefix
            if isinstance(prefix, (list, tuple)):
                prefix = prefix[0]
        except Exception:
            prefix = "y!"  # Varsayılan prefix
            print("[UYARI] Bot prefix'i alınamadı, varsayılan 'y!' kullanılıyor.")

        # --- Komut Listesi Stringlerini Oluştur ---
        # Bilgi Komutları (BilgiCog'dan)
        bilgi_komutlari_str = "\n".join([
            f"`{prefix}sunucu` - Sunucu hakkında detaylı bilgi verir",
            f"`{prefix}kullanıcı` - Kullanıcı bilgisini gösterir",
            f"`{prefix}avatar` - Kullanıcı avatarını gösterir",
            f"`{prefix}rolbilgi` - Rol bilgilerini gösterir",
            f"`{prefix}ping` - Botun gecikme süresini gösterir",
            f"`{prefix}zaman` - Geçerli zamanı gösterir",
            f"`{prefix}hesapla` - Matematiksel hesaplamalar yapar"
        ])

        # Eğlence Komutları
        eglence_komutlari_str = "\n".join([
            f"`{prefix}8ball` - 8 ball özelliği biraz tahmin yürütüyor",
            f"`{prefix}danset` - Komutu kullanan dans ediyor",
            f"`{prefix}espripatlat` - Çok kötü espriler yapıyor",
            f"`{prefix}kedi` - Rastgele kedi gösteriyor sana",
            f"`{prefix}naber` - Bot senle konuşuyor",
            f"`{prefix}rastgele` - Rastgele şeyler söylüyor",
            f"`{prefix}sogukespri` - Soğuk espri yapıyor",
            f"`{prefix}tahmin` - Tahmin yürütüyor sana",
            f"`{prefix}yazitura` - Yazı tura oynuyor",
            f"`{prefix}zar` - Zar atıyor",
            f"`{prefix}şaka` - Şaka yapıyor"
        ])

        # Partnerlik Sistemi
        partnerlik_komutlari_str = "\n".join([
            f"`{prefix}partnerleaderboard` - Partnerlik lider tablosu",
            f"`{prefix}partnerstats` - Partner istatistik kullanıcıların"
        ])

        # Seviye Komutları
        seviye_komutlari_str = "\n".join([
            f"`{prefix}lider` - Seviye sistemin liderlik sistemi",
            f"`{prefix}seviye` - Seviye sistem seviye gösterme"
        ])

        # --- Embed Açıklamasını Oluştur ---
        description_content = (
            f"Aşağıda kullanabileceğin komutların bir listesi bulunmaktadır.\nPrefix: `{prefix}`\n\n"
            f"### Bilgi Komutları\n{bilgi_komutlari_str}\n\n"
            f"### Eğlence Komutları\n{eglence_komutlari_str}\n\n"
            f"### Partnerlik Sistemi\n{partnerlik_komutlari_str}\n\n"
            f"### Seviye Komutları\n{seviye_komutlari_str}"
        )

        # Açıklama uzunluğunu kontrol et (Discord sınırı 4096)
        if len(description_content) > 4096:
            print("[UYARI] Yardım mesajı açıklaması 4096 karakter sınırını aşıyor!")
            description_content = description_content[:4093] + "..."

        embed = discord.Embed(
            title="Yardım Menüsü",
            description=description_content,
            color=discord.Color.blue()
        )

        # --- Dinamik Sahip Komutları ---
        owner_commands_list = []
        try:
            for command in self.bot.commands:
                if command.hidden or command.name != command.qualified_name:
                    continue

                cog_name = command.cog_name or "Diğer"
                is_owner_command_cog = cog_name in self.owner_cog_names
                is_owner_only_check = any(isinstance(check, commands.is_owner().predicate.__class__) for check in command.checks)

                if is_owner_command_cog or is_owner_only_check:
                    owner_commands_list.append(f"`{prefix}{command.name}` - {command.help or 'Açıklama yok'}")

            is_bot_owner = await self.bot.is_owner(ctx.author)
            if is_bot_owner and owner_commands_list:
                owner_commands_str = "\n".join(sorted(owner_commands_list))
                if len(owner_commands_str) > 1024:
                    print("[UYARI] Sahip komutları alanı 1024 karakter sınırını aşıyor!")
                    owner_commands_str = owner_commands_str[:1021] + "..."

                if owner_commands_str:
                    embed.add_field(
                        name="👑 Sahip Komutları 👑",
                        value=owner_commands_str,
                        inline=False
                    )
        except Exception as e:
            print(f"[HATA] Sahip komutları işlenirken hata oluştu: {e}")
            traceback.print_exc()

        # Alt bilgi ve zaman damgası
        embed.set_footer(text=f"Komut '{ctx.invoked_with}' ile çalıştırıldı | {self.bot.user.name}")
        embed.timestamp = discord.utils.utcnow()

        try:
            await ctx.send(embed=embed)
        except discord.HTTPException as e:
            print(f"[HATA] Yardım mesajı gönderilemedi (HTTPException): Kanal {ctx.channel.id}. Hata: {e}")
            await ctx.send("Yardım mesajı gönderilemedi (mesaj çok uzun veya başka bir HTTP sorunu olabilir).")
        except discord.Forbidden:
            print(f"[UYARI] Yardım mesajı gönderilemedi (İzin Yok): Kanal {ctx.channel.id}")
        except Exception as e:
            print(f"[HATA] Yardım mesajı gönderilirken beklenmedik hata: {e}")
            traceback.print_exc()
            await ctx.send("Yardım mesajı gönderilirken bir sorun oluştu.")

    @help_command.error
    async def help_command_error(self, ctx: commands.Context, error):
        """Yardım komutunda oluşan hataları yakalar."""
        if isinstance(error, commands.CommandInvokeError):
            print(f"[HATA] Yardım komutu işlenirken hata oluştu ({ctx.command.name}): {error.original}")
            traceback.print_exc()
            await ctx.send(f"❓ Yardım komutu işlenirken bir iç hata oluştu. Lütfen geliştiriciye bildirin.")
        else:
            print(f"[HATA] Yardım komutunda hata ({ctx.command.name}): {error}")
            await ctx.send(f"❓ Yardım komutu işlenirken bir hata oluştu.")

async def setup(bot: commands.Bot):
    await bot.add_cog(HelpCog(bot))
    print(f"✅ {HelpCog.__name__} yüklendi!")
