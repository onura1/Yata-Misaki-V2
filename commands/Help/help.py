# commands/Help/help.py (Sahip Komutları Bölümü Eklendi)
import discord
from discord.ext import commands
# import logging # Loglama kaldırıldı

class HelpCog(commands.Cog, name="Yardım Komutları"):
    """Yardım menüsünü içerir ve sahip komutlarını sadece sahibe gösterir."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # self.logger = logging.getLogger(__name__) # Loglama kaldırıldı
        # Sahip komutlarını içeren Cog'ların tam adları (Cog sınıfındaki name='...' parametresi)
        self.owner_cog_names = {
            "Ping Komutu (Sahip)",
            "Durum Ayarları",
            "Kapatma",
            "Yeniden Başlatma",
            "Aktiflik Süresi (Sahip)"
        }

    # Komut adı 'yardim', alias'lar güncellendi
    @commands.command(name="yardim", aliases=["help", "komutlar", "yardimkomutu"])
    async def help_command(self, ctx: commands.Context):
        """Tüm kullanılabilir komutları listeler. Bot sahibi için özel komutları da gösterir."""
        prefix = self.bot.config.get("PREFIX", "!") # Prefix'i config'den al, yoksa '!' kullan
        embed = discord.Embed(
            title="Yardım Menüsü",
            description=f"Aşağıda kullanabileceğin komutların bir listesi bulunmaktadır.\nPrefix: `{prefix}`",
            color=discord.Color.blue() # Renk sabit veya config'den alınabilir
        )

        public_commands_by_cog = {} # Herkesin görebileceği komutlar
        owner_commands = []         # Sadece sahibin göreceği komutlar

        # Botun tüm komutlarını dolaş
        for command in self.bot.commands:
            if command.hidden: continue # Gizli komutları atla

            cog_name = command.cog_name or "Diğer" # Cog adını al

            # Komut sahip komutu mu? (Cog adına göre kontrol)
            if cog_name in self.owner_cog_names:
                owner_commands.append(f"`{prefix}{command.name}`")
            else:
                # Değilse, kullanıcı çalıştırabilir mi?
                try:
                    if await command.can_run(ctx):
                        if cog_name not in public_commands_by_cog:
                            public_commands_by_cog[cog_name] = []
                        public_commands_by_cog[cog_name].append(f"`{prefix}{command.name}`")
                except commands.CommandError:
                    continue # Çalıştıramıyorsa veya hata verirse atla

        # Embed'i oluşturmaya başla
        if not public_commands_by_cog and not owner_commands:
             embed.description += "\n\nGörünüşe göre listelenecek bir komut bulunmuyor."
        else:
            # Herkese açık komutları ekle
            sorted_public_cogs = sorted(public_commands_by_cog.items())
            for cog_name, command_list in sorted_public_cogs:
                commands_str = "\n".join(sorted(command_list))
                if commands_str:
                    embed.add_field(name=f"**{cog_name}**", value=commands_str, inline=False)

            # Komutu çalıştıran kişi sahip mi?
            is_bot_owner = await self.bot.is_owner(ctx.author)

            # Eğer sahipse ve sahip komutları varsa, özel bölümü ekle
            if is_bot_owner and owner_commands:
                owner_commands_str = "\n".join(sorted(owner_commands))
                if owner_commands_str:
                     embed.add_field(
                         name="👑 Sahip Komutları 👑",
                         value=owner_commands_str,
                         inline=False
                     )
            elif not public_commands_by_cog and not is_bot_owner and owner_commands:
                 embed.description += "\n\nGörünüşe göre senin çalıştırabileceğin bir komut bulunmuyor."

        # Alt bilgi ve zaman damgası
        embed.set_footer(text=f"{ctx.guild.name if ctx.guild else 'DM'} | {self.bot.user.name}")
        embed.timestamp = discord.utils.utcnow()

        try:
            await ctx.send(embed=embed)
        except discord.HTTPException:
            print(f"[HATA] Yardım mesajı gönderilemedi (HTTPException): Kanal {ctx.channel.id}")
            await ctx.send("Yardım mesajı gönderilemedi (çok fazla komut veya karakter olabilir).")
        except discord.Forbidden:
             print(f"[UYARI] Yardım mesajı gönderilemedi (İzin Yok): Kanal {ctx.channel.id}")
        except Exception as e:
            print(f"[HATA] Yardım mesajı gönderilirken beklenmedik hata: {e}")
            # traceback.print_exc() # Detaylı hata için eklenebilir
            await ctx.send("Yardım mesajı gönderilirken bir sorun oluştu.")

    # Hata Yönetimi
    @help_command.error
    async def help_command_error(self, ctx: commands.Context, error):
        # Genel hata yakalayıcıya gitmeden önce burada özel işlem yapılabilir
        print(f"[HATA] Yardım komutunda hata ({ctx.command.name}): {error}")
        await ctx.send(f"❓ Yardım komutu işlenirken bir hata oluştu.")

# Cog'u bota tanıtmak için gerekli setup fonksiyonu
async def setup(bot: commands.Bot):
    await bot.add_cog(HelpCog(bot))
    print("✅ Help Cog yüklendi!")