# commands/Genel/kullanici.py (Düzeltilmiş Hali)
import discord
from discord.ext import commands
import datetime

class BilgiCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # Yardımcı Fonksiyon: Embed oluşturmayı sadeleştirme
    def create_embed(self, title: str, description: str, color: discord.Color, footer_user: discord.User = None, thumbnail: str = None):
        embed = discord.Embed(title=title, description=description, color=color)
        if footer_user:
            embed.set_footer(text=f"İsteyen: {footer_user.display_name}", icon_url=footer_user.display_avatar.url)
        if thumbnail:
            embed.set_thumbnail(url=thumbnail)
        return embed

    # !sunucu komutu
    @commands.command(name="sunucu", aliases=['serverinfo', 'sunucubilgi'], help="Komutun kullanıldığı sunucu hakkında detaylı bilgi verir.")
    async def sunucu_bilgi(self, ctx: commands.Context):
        """Sunucu hakkında bilgi gösterir."""
        if not ctx.guild:
            embed = self.create_embed(
                title="❌ Hata!",
                description="Bu komut sadece sunucularda kullanılabilir.",
                color=discord.Color.red(),
                footer_user=ctx.author
            )
            await ctx.send(embed=embed)
            return

        guild = ctx.guild
        created_at = guild.created_at.strftime("%d %B %Y, %H:%M")
        total_members = guild.member_count
        online_members = sum(1 for member in guild.members if member.status != discord.Status.offline)
        humans = sum(1 for member in guild.members if not member.bot)
        bots = sum(1 for member in guild.members if member.bot)
        text_channels = len(guild.text_channels)
        voice_channels = len(guild.voice_channels)
        categories = len(guild.categories)
        roles_count = len(guild.roles)
        highest_role = guild.roles[-1] if len(guild.roles) > 1 else guild.roles[0]

        embed = self.create_embed(
            title=f"{guild.name} Sunucu Bilgileri",
            description=f"**ID:** {guild.id}",
            color=discord.Color.blue(),
            footer_user=ctx.author
        )
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)

        embed.add_field(name="👑 Sahip", value=guild.owner.mention, inline=True)
        embed.add_field(name="📅 Oluşturulma Tarihi", value=created_at, inline=True)
        embed.add_field(name=f"👥 Üyeler ({total_members})", value=f"🟢 Çevrimiçi: {online_members}\n👤 İnsan: {humans}\n🤖 Bot: {bots}", inline=True)
        embed.add_field(name=f"💬 Kanallar ({text_channels + voice_channels})", value=f"Yazı: {text_channels}\nSes: {voice_channels}\nKategori: {categories}", inline=True)
        embed.add_field(name=f"🎭 Roller ({roles_count})", value=f"En Yüksek: {highest_role.mention}", inline=True)
        embed.add_field(name="✅ Doğrulama Seviyesi", value=str(guild.verification_level).capitalize(), inline=True)
        embed.add_field(name="🚀 Boost Seviyesi", value=f"Seviye {guild.premium_tier} ({guild.premium_subscription_count} boost)", inline=True)

        await ctx.send(embed=embed)

    # !kullanıcı komutu
    @commands.command(name="kullanıcı", aliases=['userinfo', 'profil', 'ui'], help="Belirtilen kullanıcı veya komutu kullanan hakkında bilgi verir.")
    async def kullanici_bilgi(self, ctx: commands.Context, member: discord.Member = None):
        """Kullanıcı hakkında bilgi gösterir."""
        target_user = member or ctx.author

        created_at = target_user.created_at.strftime("%d %B %Y, %H:%M")
        embed = self.create_embed(
            title=f"{target_user.display_name} Kullanıcı Bilgileri",
            description=f"**ID:** {target_user.id}",
            color=target_user.top_role.color if hasattr(target_user, 'roles') and len(target_user.roles) > 1 else discord.Color.default(),
            footer_user=ctx.author
        )
        embed.set_thumbnail(url=target_user.display_avatar.url)

        embed.add_field(name="👤 Kullanıcı Adı", value=f"{target_user.name}#{target_user.discriminator}", inline=True)
        embed.add_field(name="📅 Hesap Oluşturma Tarihi", value=created_at, inline=True)
        embed.add_field(name="📊 Durum", value=str(target_user.status).capitalize(), inline=True)

        if ctx.guild:  # Sunucu içindeyse ek bilgiler
            joined_at = target_user.joined_at.strftime("%d %B %Y, %H:%M") if target_user.joined_at else "Bilinmiyor"
            roles = [role.mention for role in reversed(target_user.roles) if not role.is_default()]
            roles_text = ", ".join(roles) if roles else "Rolü Yok"
            if len(roles_text) > 1024:
                roles_text = roles_text[:1020] + "..."

            embed.add_field(name="📥 Sunucuya Katılma Tarihi", value=joined_at, inline=True)
            embed.add_field(name=f"🎭 Roller ({len(roles)})", value=roles_text, inline=False)

        if target_user.activity:
            activity_type = str(target_user.activity.type).split('.')[-1].capitalize()
            activity_name = target_user.activity.name
            embed.add_field(name=f"🎮 Aktivite ({activity_type})", value=activity_name, inline=False)

        await ctx.send(embed=embed)

    # !avatar komutu
    @commands.command(name="avatar", aliases=['av', 'pp'], help="Belirtilen kullanıcının veya komutu kullananın avatarını gösterir.")
    async def avatar_goster(self, ctx: commands.Context, member: discord.Member = None):
        """Kullanıcının avatarını gösterir."""
        target_user = member or ctx.author

        embed = self.create_embed(
            title=f"{target_user.display_name} adlı kullanıcının avatarı",
            description="",
            color=target_user.top_role.color if hasattr(target_user, 'roles') and len(target_user.roles) > 1 else discord.Color.default(),
            footer_user=ctx.author
        )
        avatar_url = target_user.display_avatar.url
        embed.set_image(url=avatar_url)
        embed.add_field(
            name="Linkler",
            value=f"[PNG]({target_user.display_avatar.replace(format='png').url}) | "
                  f"[JPG]({target_user.display_avatar.replace(format='jpg').url}) | "
                  f"[WEBP]({target_user.display_avatar.replace(format='webp').url})",
            inline=False
        )

        await ctx.send(embed=embed)

    # !rolbilgi komutu
    @commands.command(name="rolbilgi", aliases=['roleinfo', 'rolinfo'], help="Belirtilen rol hakkında bilgi verir.")
    async def rol_bilgi(self, ctx: commands.Context, *, role: discord.Role):
        """Belirtilen rol hakkında bilgi gösterir."""
        if not ctx.guild:
            embed = self.create_embed(
                title="❌ Hata!",
                description="Bu komut sadece sunucularda kullanılabilir.",
                color=discord.Color.red(),
                footer_user=ctx.author
            )
            await ctx.send(embed=embed)
            return

        created_at = role.created_at.strftime("%d %B %Y, %H:%M")
        role_color = role.color if role.color != discord.Color.default() else discord.Color.light_grey()

        embed = self.create_embed(
            title=f"'{role.name}' Rol Bilgileri",
            description=f"**ID:** {role.id}",
            color=role_color,
            footer_user=ctx.author
        )

        embed.add_field(name="🏷️ Ad", value=role.name, inline=True)
        embed.add_field(name="#️⃣ ID", value=role.id, inline=True)
        embed.add_field(name="🎨 Renk (Hex)", value=str(role.color), inline=True)
        embed.add_field(name="📅 Oluşturulma Tarihi", value=created_at, inline=True)
        embed.add_field(name="👥 Üye Sayısı", value=len(role.members), inline=True)
        embed.add_field(name="📌 Pozisyon", value=role.position, inline=True)
        embed.add_field(name="🗣️ Bahsedilebilir mi?", value="Evet" if role.mentionable else "Hayır", inline=True)
        embed.add_field(name="↕️ Ayrı Gösteriliyor mu?", value="Evet" if role.hoist else "Hayır", inline=True)
        embed.add_field(name="🤖 Bot Rolü mü?", value="Evet" if role.is_bot_managed() else "Hayır", inline=True)
        embed.add_field(name="👑 Yönetici mi?", value="Evet" if role.permissions.administrator else "Hayır", inline=True)

        if role.icon:
            embed.set_thumbnail(url=role.icon.url)
        elif role.unicode_emoji:
            embed.add_field(name="😀 Emoji", value=role.unicode_emoji, inline=True)

        await ctx.send(embed=embed)

    # !zaman komutu
    @commands.command(name="zaman", aliases=['saat'], help="Geçerli zamanı gösterir.")
    async def zaman(self, ctx: commands.Context):
        """Geçerli zamanı gösterir."""
        current_time = datetime.datetime.now().strftime("%d %B %Y, %H:%M:%S")
        embed = self.create_embed(
            title="⏰ Şu Anki Zaman",
            description=f"📅 **{current_time}**",
            color=discord.Color.purple(),
            footer_user=ctx.author
        )
        await ctx.send(embed=embed)

    # !hesapla komutu
    @commands.command(name="hesapla", help="Basit matematiksel hesaplamalar yapar. Örnek: y!hesapla 5 + 3")
    async def hesapla(self, ctx: commands.Context, *, expression: str):
        """Basit matematiksel hesaplamalar yapar."""
        try:
            # Güvenlik notu: eval() kullanımı riskli olabilir.
            # Sadece basit matematiksel ifadelere izin vermek için kısıtlamalar ekledik.
            # Daha güvenli bir alternatif için 'asteval' gibi kütüphaneler düşünülebilir.
            allowed_chars = "0123456789+-*/(). "
            if not all(c in allowed_chars for c in expression):
                raise ValueError("İfadede izin verilmeyen karakterler var.")

            # Çok uzun ifadeleri engelle
            if len(expression) > 100:
                 raise ValueError("İfade çok uzun.")

            result = eval(expression, {"__builtins__": None}, {"abs": abs, "round": round}) # eval'ı kısıtlıyoruz
            embed = self.create_embed(
                title="🧮 Hesaplama Sonucu",
                description=f"**İfade:** `{expression}`\n**Sonuç:** `{result}`", # Kod bloğu içinde göster
                color=discord.Color.orange(),
                footer_user=ctx.author
            )
            await ctx.send(embed=embed)
        except (SyntaxError, ValueError, TypeError, ZeroDivisionError) as e:
            embed = self.create_embed(
                title="❌ Hata!",
                description=f"Geçersiz veya desteklenmeyen bir ifade girdin: `{expression}`\n*Hata: {str(e)}*",
                color=discord.Color.red(),
                footer_user=ctx.author
            )
            await ctx.send(embed=embed)
        except Exception as e: # Diğer beklenmedik hatalar
            embed = self.create_embed(
                title="❌ Hata!",
                description=f"Hesaplama sırasında beklenmedik bir hata oluştu: `{expression}`",
                color=discord.Color.red(),
                footer_user=ctx.author
            )
            print(f"Hesapla hatası ({expression}): {e}") # Loglama için
            await ctx.send(embed=embed)


    # --- ARTIK GEREKLİ DEĞİL ---
    # !yardım komutu (Bu komut Help Cog'da olduğu için buradan kaldırıldı)
    # @commands.command(name="yardım", aliases=['help'], help="Bilgi komutlarının listesini gösterir.")
    # async def yardim(self, ctx: commands.Context):
    #     ... (KOD BURADAN SİLİNDİ) ...

    # --- ARTIK GEREKLİ DEĞİL ---
    # !ping komutu (Owner Cog'da olduğu için buradan kaldırıldı)
    # @commands.command(name="ping", help="Botun gecikme süresini gösterir.")
    # async def ping(self, ctx: commands.Context):
    #     ... (KOD BURADAN SİLİNDİ) ...


    # --- Hata Yönetimi (Bu Cog'a özel) ---
    # Not: Genel hata yönetimi main.py'deki on_command_error'da yapılıyor.
    # Buradakiler sadece bu Cog'daki komutlara özel daha detaylı hata mesajları için.
    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error):
        # Sadece bu Cog'a ait komutlarda hata olursa ve genel hata yakalayıcı çalışmazsa devreye girer
        if ctx.cog is not self:
            return # Başka bir Cog'un hatasıysa ilgilenme

        # Genel hatalar main.py'de yakalandığı için burayı sadeleştirebiliriz
        # veya sadece bu Cog'a özel hataları (örn: MemberNotFound) burada yakalayabiliriz.
        # Şimdilik MemberNotFound ve RoleNotFound dışındakileri main.py'ye bırakalım.
        pass # Diğer hatalar için bir şey yapma, main.py halleder

    @kullanici_bilgi.error
    @avatar_goster.error
    async def userinfo_avatar_error(self, ctx: commands.Context, error):
        # Sadece bu komutlara özel hata yakalayıcı
        if isinstance(error, commands.MemberNotFound):
            embed = self.create_embed(
                title="❌ Kullanıcı Bulunamadı!",
                description=f"Kullanıcı bulunamadı: `{error.argument}`",
                color=discord.Color.red(),
                footer_user=ctx.author
            )
            await ctx.send(embed=embed)
        # Diğer hatalar (MissingRequiredArgument, CommandOnCooldown vb.) main.py'deki genel yakalayıcıya gider.

    @rol_bilgi.error
    async def rolbilgi_error(self, ctx: commands.Context, error):
        # Sadece bu komuta özel hata yakalayıcı
        if isinstance(error, commands.RoleNotFound):
            embed = self.create_embed(
                title="❌ Rol Bulunamadı!",
                description=f"Rol bulunamadı: `{error.argument}`",
                color=discord.Color.red(),
                footer_user=ctx.author
            )
            await ctx.send(embed=embed)
        elif isinstance(error, commands.MissingRequiredArgument):
             embed = self.create_embed(
                 title="❌ Eksik Argüman!",
                 description="Lütfen bilgi almak istediğiniz rolü belirtin (Ad, ID veya @Rol).",
                 color=discord.Color.red(),
                 footer_user=ctx.author
             )
             await ctx.send(embed=embed)
        # Diğer hatalar main.py'deki genel yakalayıcıya gider.

    @hesapla.error
    async def hesapla_error(self, ctx: commands.Context, error):
        # Sadece bu komuta özel hata yakalayıcı
        if isinstance(error, commands.MissingRequiredArgument):
            embed = self.create_embed(
                title="❌ Eksik Argüman!",
                description=f"Lütfen bir matematiksel ifade girin. Örnek: `{self.bot.config.get('PREFIX', 'y!')}hesapla 5 + 3`", # Prefix'i config'den al
                color=discord.Color.red(),
                footer_user=ctx.author
            )
            await ctx.send(embed=embed)
        # Diğer hatalar main.py'deki genel yakalayıcıya gider.


async def setup(bot: commands.Bot):
    await bot.add_cog(BilgiCog(bot))
    print("✅ BilgiCog yüklendi!") # Setup mesajını güncelleyelim
