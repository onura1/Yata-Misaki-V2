# commands/partner.py

import discord
from discord.ext import commands
import sqlite3
import logging
import datetime
import re
import os
import pytz
from typing import Optional, List, Tuple

# --- Configuration ---
DB_NAME = os.path.join(os.path.dirname(__file__), "partners.db")
LOG_FILE = "partner_system.log"

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler()
    ]
)

# Türkiye zaman dilimini tanımla (UTC+3)
TURKEY_TZ = pytz.timezone("Europe/Istanbul")

class PartnershipCog(commands.Cog):
    """Partnerlik ile ilgili komutları ve olayları yönetir."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.logger = logging.getLogger("PartnershipCog")
        self._init_db()

    def _init_db(self):
        """SQLite veritabanını başlat."""
        try:
            self.conn = sqlite3.connect(DB_NAME)
            self.cursor = self.conn.cursor()
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS partners (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    guild_id INTEGER NOT NULL,
                    invite_link TEXT NOT NULL,
                    timestamp DATETIME NOT NULL
                )
            """)
            self.conn.commit()
            self.logger.info(f"'{DB_NAME}' veritabanına bağlandı.")
        except sqlite3.Error as e:
            self.logger.error(f"Veritabanı başlatma hatası: {e}")
            self.conn = None
            self.cursor = None

    def _add_partner_record(self, user_id: int, guild_id: int, invite_link: str, timestamp: datetime.datetime):
        """Veritabanına yeni bir partner kaydı ekle."""
        if not self.conn:
            self.logger.error("Veritabanı bağlantısı yok, partner kaydı eklenemiyor.")
            return

        try:
            timestamp_tr = timestamp.astimezone(TURKEY_TZ)
            self.cursor.execute(
                "INSERT INTO partners (user_id, guild_id, invite_link, timestamp) VALUES (?, ?, ?, ?)",
                (user_id, guild_id, invite_link, timestamp_tr.strftime("%Y-%m-%d %H:%M:%S"))
            )
            self.conn.commit()
            self.logger.info(f"Partner kaydı eklendi: Kullanıcı {user_id}, Sunucu {guild_id}, Link {invite_link}, Zaman {timestamp_tr}")
        except sqlite3.Error as e:
            self.logger.error(f"Partner kaydı eklenirken hata: {e}")

    def _get_partner_details(self, period: str) -> List[Tuple[int, str, str]]:
        """Belirli bir dönem için partner ayrıntılarını al."""
        if not self.conn or not self.cursor:
            self.logger.error("Veritabanı bağlantısı yok, partner detayları alınamıyor.")
            return []

        today = datetime.date.today()
        if period == "daily":
            start_date = today.strftime("%Y-%m-%d")
            query = "SELECT user_id, invite_link, timestamp FROM partners WHERE DATE(timestamp) = ? ORDER BY timestamp DESC"
            params = (start_date,)
        elif period == "monthly":
            start_date = today.replace(day=1).strftime("%Y-%m-%d")
            query = "SELECT user_id, invite_link, timestamp FROM partners WHERE timestamp >= ? ORDER BY timestamp DESC"
            params = (start_date,)
        elif period == "yearly":
            start_date = today.replace(month=1, day=1).strftime("%Y-%m-%d")
            query = "SELECT user_id, invite_link, timestamp FROM partners WHERE timestamp >= ? ORDER BY timestamp DESC"
            params = (start_date,)
        else:
            self.logger.warning(f"Geçersiz dönem istendi: {period}")
            return []

        try:
            self.cursor.execute(query, params)
            return self.cursor.fetchall()
        except sqlite3.Error as e:
            self.logger.error(f"Partner detayları alınırken hata: {e}")
            return []

    def _get_leaderboard(self, limit: int = 10) -> List[Tuple[int, int]]:
        """En çok partnerliği olan kullanıcıların lider tablosunu al."""
        if not self.conn or not self.cursor:
            self.logger.error("Veritabanı bağlantısı yok, lider tablosu alınamıyor.")
            return []

        try:
            self.cursor.execute(
                "SELECT user_id, COUNT(*) as count FROM partners GROUP BY user_id ORDER BY count DESC LIMIT ?",
                (limit,)
            )
            return self.cursor.fetchall()
        except sqlite3.Error as e:
            self.logger.error(f"Lider tablosu alınırken hata: {e}")
            return []

    async def _get_server_name_from_invite(self, invite_link: str) -> Optional[str]:
        """Bir Discord davet linkinden sunucu adını al."""
        try:
            invite = await self.bot.fetch_invite(invite_link)
            return invite.guild.name if invite.guild else "Bilinmeyen Sunucu"
        except discord.errors.NotFound:
            self.logger.warning(f"Geçersiz davet linki: {invite_link}")
            return "Geçersiz Link"
        except discord.errors.Forbidden:
            self.logger.error(f"Botun davet linkine erişim izni yok: {invite_link}")
            return "Erişim Yok"
        except discord.errors.HTTPException as e:
            self.logger.error(f"Davet linkinden sunucu adı alınırken HTTP hatası: {e}")
            return "HTTP Hatası"
        except Exception as e:
            self.logger.error(f"Davet linkinden sunucu adı alınırken hata: {e}")
            return "Hata"

    # --- Event Listener ---
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Partner kanalındaki linkleri tespit eder ve partnerliği kaydeder."""
        if message.author.bot or message.guild is None:
            return

        partner_channel_id = self.bot.config.get("PARTNER_CHANNEL_ID")
        if not partner_channel_id:
            self.logger.error("[Hata] Yapılandırmada PARTNER_CHANNEL_ID bulunamadı.")
            return

        try:
            partner_channel_id = int(partner_channel_id)
        except ValueError:
            self.logger.error(f"[Hata] PARTNER_CHANNEL_ID geçersiz: {partner_channel_id}")
            return

        if message.channel.id != partner_channel_id:
            return

        invite_pattern = r"(https?://)?discord\.gg/[\w-]+"
        invites = re.findall(invite_pattern, message.content)
        if not invites:
            return

        for invite_link in invites:
            if not invite_link.startswith("http"):
                invite_link = f"https://{invite_link}"

            try:
                invite = await self.bot.fetch_invite(invite_link)
                if not invite.guild:
                    self.logger.warning(f"Geçersiz davet linki: {invite_link}")
                    continue
                if not invite.expires_at or invite.expires_at > datetime.datetime.now(tz=pytz.UTC):
                    guild_id = invite.guild.id
                else:
                    self.logger.warning(f"Davet linki süresi dolmuş: {invite_link}")
                    continue
            except discord.errors.NotFound:
                self.logger.warning(f"Davet linki geçersiz: {invite_link}")
                continue
            except discord.errors.Forbidden:
                self.logger.warning(f"Botun davet linkine erişim izni yok: {invite_link}")
                continue
            except discord.errors.HTTPException as e:
                self.logger.error(f"Davet linki kontrol edilirken HTTP hatası: {e}")
                continue
            except Exception as e:
                self.logger.error(f"Davet linki kontrol edilirken hata: {e}")
                continue

            timestamp = message.created_at
            self._add_partner_record(message.author.id, guild_id, invite_link, timestamp)

            embed = discord.Embed(
                title="🎯 Yeni bir partnerlik bildirimi!",
                color=discord.Color.red(),
                timestamp=message.created_at
            )
            if message.guild.icon:
                embed.set_thumbnail(url=message.guild.icon.url)

            partner_image_url = self.bot.config.get("PARTNER_IMAGE_URL", "")
            if partner_image_url:
                embed.set_image(url=partner_image_url)

            embed.add_field(
                name=f"👋 Partnerliği yapan: {message.author.display_name}",
                value=(
                    f"🔥 Partnerlik yapılan sunucu: **{invite.guild.name}**\n"
                    f"🆔 Sunucu ID: {invite.guild.id}\n"
                    f"⏰ Partnerlik Zamanı: {timestamp.astimezone(TURKEY_TZ).strftime('%Y-%m-%d %H:%M:%S')}"
                ),
                inline=False
            )
            embed.set_footer(text=f"ID: {message.author.id}")

            try:
                await message.channel.send(embed=embed)
                await message.add_reaction("🤝")
            except discord.Forbidden:
                self.logger.error(f"[Hata] {message.channel.name} kanalına mesaj gönderme veya tepki ekleme izni yok.")
            except discord.HTTPException as e:
                self.logger.error(f"Partnerlik bildirimi gönderilirken bir HTTP hatası oluştu: {e}")

    # --- Commands ---
    @commands.command(name="partnerstats")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def partner_stats_command(self, ctx: commands.Context):
        """Display detailed partner statistics (who partnered with which server and when)."""
        if not ctx.guild:
            await ctx.send("Bu komut sadece sunucularda kullanılabilir.")
            return
        if not self.conn:
            await ctx.send("Veritabanı hatası nedeniyle istatistikler alınamıyor.")
            return

        daily_partners = self._get_partner_details("daily")
        monthly_partners = self._get_partner_details("monthly")
        yearly_partners = self._get_partner_details("yearly")

        embed = discord.Embed(
            title=f"{ctx.guild.name} Partner İstatistikleri",
            color=discord.Color.red()
        )
        if ctx.guild.icon:
            embed.set_thumbnail(url=ctx.guild.icon.url)

        daily_text = []
        for user_id, invite_link, timestamp in daily_partners:
            member = ctx.guild.get_member(user_id)
            user_name = member.display_name if member else f"Ayrılmış Üye (ID: {user_id})"
            server_name = await self._get_server_name_from_invite(invite_link)
            timestamp_str = datetime.datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d %H:%M:%S")
            daily_text.append(f"{server_name} - {user_name} - {timestamp_str}")
        embed.add_field(
            name=f"Günlük Partnerlikler ({len(daily_partners)})",
            value="\n".join(daily_text) if daily_text else "Bugün partnerlik yapılmamış.",
            inline=False
        )

        monthly_text = []
        for user_id, invite_link, timestamp in monthly_partners:
            member = ctx.guild.get_member(user_id)
            user_name = member.display_name if member else f"Ayrılmış Üye (ID: {user_id})"
            server_name = await self._get_server_name_from_invite(invite_link)
            timestamp_str = datetime.datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d %H:%M:%S")
            monthly_text.append(f"{server_name} - {user_name} - {timestamp_str}")
        embed.add_field(
            name=f"Aylık Partnerlikler ({len(monthly_partners)})",
            value="\n".join(monthly_text) if monthly_text else "Bu ay partnerlik yapılmamış.",
            inline=False
        )

        yearly_text = []
        for user_id, invite_link, timestamp in yearly_partners:
            member = ctx.guild.get_member(user_id)
            user_name = member.display_name if member else f"Ayrılmış Üye (ID: {user_id})"
            server_name = await self._get_server_name_from_invite(invite_link)
            timestamp_str = datetime.datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d %H:%M:%S")
            yearly_text.append(f"{server_name} - {user_name} - {timestamp_str}")
        embed.add_field(
            name=f"Yıllık Partnerlikler ({len(yearly_partners)})",
            value="\n".join(yearly_text) if yearly_text else "Bu yıl partnerlik yapılmamış.",
            inline=False
        )

        embed.set_footer(text=f"Tarih: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        await ctx.send(embed=embed)

    @commands.command(name="partnerleaderboard")
    @commands.cooldown(1, 10, commands.BucketType.guild)
    async def partner_leaderboard_command(self, ctx: commands.Context):
        """Display the leaderboard of users with the most partnerships."""
        if not ctx.guild:
            await ctx.send("Bu komut sadece sunucularda kullanılabilir.")
            return
        if not self.conn:
            await ctx.send("Veritabanı hatası nedeniyle lider tablosu alınamıyor.")
            return

        leaderboard = self._get_leaderboard(limit=10)
        embed = discord.Embed(
            title=f"🏆 {ctx.guild.name} Partner Lider Tablosu",
            color=discord.Color.red()
        )
        if ctx.guild.icon:
            embed.set_thumbnail(url=ctx.guild.icon.url)

        if not leaderboard:
            embed.description = "Henüz kimse partnerlik yapmamış."
        else:
            description = ""
            for rank, (user_id, count) in enumerate(leaderboard, start=1):
                member = ctx.guild.get_member(user_id)
                member_name = member.display_name if member else f"Ayrılmış Üye (ID: {user_id})"
                description += f"**{rank}.** {member_name} - {count} partnerlik\n"
            embed.description = description

        embed.set_footer(text=f"Tarih: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        await ctx.send(embed=embed)

    # --- Error Handling ---
    @partner_stats_command.error
    async def partner_stats_error(self, ctx: commands.Context, error):
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"⏳ {error.retry_after:.1f} saniye bekle.")
        else:
            self.logger.error(f"partnerstats komut hatası: {error}")
            await ctx.send("❓ Hata oluştu.")

    @partner_leaderboard_command.error
    async def partner_leaderboard_error(self, ctx: commands.Context, error):
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"⏳ {error.retry_after:.1f} saniye bekle.")
        else:
            self.logger.error(f"partnerleaderboard komut hatası: {error}")
            await ctx.send("❓ Hata oluştu.")

    # --- Cog Lifecycle ---
    def cog_unload(self):
        """Clean up when the cog is unloaded."""
        if self.conn:
            self.conn.close()
            self.logger.info("Cog kaldırıldı, DB bağlantısı kapatıldı.")

async def setup(bot: commands.Bot):
    """Setup function to load the cog."""
    try:
        import sqlite3
    except ImportError:
        logging.error("SQLite3 modülü bulunamadı! Partner sistemi ÇALIŞMAYACAK.")
        return
    if not os.path.exists(DB_NAME):
        logging.warning(f"'{DB_NAME}' veritabanı dosyası bulunamadı, ilk partner kaydında oluşturulacak.")
    await bot.add_cog(PartnershipCog(bot))
    print("✅ Partnership Cog yüklendi!")
