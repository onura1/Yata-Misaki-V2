# commands/Leveling/leveling.py (Rol Atama Sorunu Düzeltildi ve Geliştirildi)

import discord
from discord.ext import commands, tasks
import sqlite3
import random
import math
import time
import os
import json
import asyncio
import logging
from typing import Dict, List, Tuple, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("leveling.log"),
        logging.StreamHandler()
    ]
)

# Dosya adları ve yapılandırma
DB_NAME = "levels.db"
# Use an absolute path to ensure the config file is found in the project root
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "leveling_config.json")
DEFAULT_CONFIG = {
    "xp_range": {"min": 15, "max": 25},
    "xp_cooldown_seconds": 60,
    "level_roles": {},
    "remove_roles_if_below_rank": None,
    "remove_previous_roles": True,
    "blacklisted_channels": [],
    "xp_boosts": {}  # Format: {"user_id/role_id": multiplier}
}

class LevelingCog(commands.Cog, name="Seviye Sistemi"):
    """Geliştirilmiş XP, Seviye, Seviye Rolleri ve Admin Komutları Sistemi."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.user_message_cooldowns: Dict[int, Dict[int, float]] = {}
        self.conn: Optional[sqlite3.Connection] = None
        self.cursor: Optional[sqlite3.Cursor] = None
        self.config: Dict = DEFAULT_CONFIG.copy()
        self.rank_removal_threshold: Optional[int] = None
        self.logger = logging.getLogger("LevelingCog")

        # Load configuration and initialize database
        self._load_config()
        self._init_db()

    # --- Configuration Management ---
    def _load_config(self):
        """Load the configuration from the JSON file."""
        self.logger.info(f"Yapılandırma dosyası yükleniyor: {CONFIG_FILE}")
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                    self.logger.info(f"Yüklenen yapılandırma: {loaded_config}")
                    if not isinstance(loaded_config, dict):
                        raise ValueError("Yapılandırma dosyası bir JSON nesnesi olmalı.")
                    self.config.update(loaded_config)
                    self.logger.info(f"Seviye yapılandırması '{CONFIG_FILE}' başarıyla yüklendi.")
                    self.logger.info(f"Yüklenen level_roles: {self.config.get('level_roles', 'Bulunamadı')}")
            else:
                with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                    json.dump(self.config, f, indent=4)
                self.logger.info(f"Seviye yapılandırması oluşturuldu: '{CONFIG_FILE}'")

            # Validate and set rank removal threshold
            threshold = self.config.get("remove_roles_if_below_rank")
            if threshold is not None:
                try:
                    self.rank_removal_threshold = int(threshold)
                    if self.rank_removal_threshold <= 0:
                        self.rank_removal_threshold = None
                    else:
                        self.logger.info(f"Rank > {self.rank_removal_threshold} ise roller kaldırılacak.")
                except (ValueError, TypeError):
                    self.logger.warning(f"'remove_roles_if_below_rank' değeri geçersiz: '{threshold}'")
                    self.rank_removal_threshold = None
        except json.JSONDecodeError as e:
            self.logger.error(f"Yapılandırma dosyası JSON formatı hatalı: {e}. Varsayılan yapılandırma kullanılıyor.")
            self.config = DEFAULT_CONFIG.copy()
            self._save_config()
            self.rank_removal_threshold = None
        except Exception as e:
            self.logger.error(f"Yapılandırma yüklenirken hata: {e}. Varsayılan yapılandırma kullanılıyor.")
            self.config = DEFAULT_CONFIG.copy()
            self._save_config()
            self.rank_removal_threshold = None

    def _save_config(self):
        """Save the current configuration to the JSON file."""
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4)
            self.logger.info(f"Yapılandırma '{CONFIG_FILE}' dosyasına kaydedildi.")
        except Exception as e:
            self.logger.error(f"Yapılandırma kaydedilirken hata: {e}")

    # --- Database Management ---
    def _init_db(self):
        """Initialize the SQLite database with necessary tables and indexes."""
        try:
            self.conn = sqlite3.connect(DB_NAME)
            self.cursor = self.conn.cursor()
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER NOT NULL,
                    guild_id INTEGER NOT NULL,
                    level INTEGER DEFAULT 0,
                    xp INTEGER DEFAULT 0,
                    total_xp INTEGER DEFAULT 0,
                    PRIMARY KEY (user_id, guild_id)
                )
            """)
            try:
                self.cursor.execute("ALTER TABLE users ADD COLUMN total_xp INTEGER DEFAULT 0")
                self.logger.info("DB'ye 'total_xp' sütunu eklendi.")
            except sqlite3.OperationalError:
                pass  # Column already exists

            self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_total_xp ON users (guild_id, total_xp DESC)")
            self.conn.commit()
            self.logger.info(f"'{DB_NAME}' veritabanına bağlandı.")
        except Exception as e:
            self.logger.error(f"Veritabanı başlatma hatası: {e}")
            self.conn = None
            self.cursor = None

    def _get_user_data(self, guild_id: int, user_id: int) -> Tuple[int, int, int]:
        """Retrieve (level, xp, total_xp) for a user. Initialize if not found."""
        if not self.conn or not self.cursor:
            self.logger.error("Veritabanı bağlantısı yok, kullanıcı verisi alınamıyor.")
            return (0, 0, 0)
        try:
            self.cursor.execute(
                "SELECT level, xp, total_xp FROM users WHERE user_id = ? AND guild_id = ?",
                (user_id, guild_id)
            )
            result = self.cursor.fetchone()
            if result and None not in result:
                return (int(result[0]), int(result[1]), int(result[2]))
            else:
                self.logger.info(f"Kullanıcı DB'de bulunamadı/eksik, sıfırlanıyor (K:{user_id}, S:{guild_id})")
                self.cursor.execute(
                    "INSERT OR REPLACE INTO users (user_id, guild_id, level, xp, total_xp) VALUES (?, ?, 0, 0, 0)",
                    (user_id, guild_id)
                )
                self.conn.commit()
                return (0, 0, 0)
        except sqlite3.Error as e:
            self.logger.error(f"Veri alma hatası (K:{user_id}, S:{guild_id}): {e}")
            return (0, 0, 0)

    def _update_user_xp(self, guild_id: int, user_id: int, level: int, xp: int, total_xp: int):
        """Update a user's level, xp, and total_xp in the database."""
        if not self.conn or not self.cursor:
            self.logger.error("Veritabanı bağlantısı yok, XP güncellenemiyor.")
            return
        try:
            self.cursor.execute(
                "INSERT OR REPLACE INTO users (user_id, guild_id, level, xp, total_xp) VALUES (?, ?, ?, ?, ?)",
                (user_id, guild_id, int(level), int(xp), int(total_xp))
            )
            self.conn.commit()
            self.logger.debug(f"Kullanıcı XP güncellendi: K:{user_id}, S:{guild_id}, Seviye:{level}, XP:{xp}, Toplam XP:{total_xp}")
        except sqlite3.Error as e:
            self.logger.error(f"Veri güncelleme hatası (K:{user_id}, S:{guild_id}): {e}")

    # --- Utility Functions ---
    def _calculate_xp_for_level(self, level: int) -> int:
        """Calculate the XP required to reach the next level."""
        if level < 0:
            return 0
        return 5 * (level ** 2) + (50 * level) + 100

    def _get_user_rank(self, guild_id: int, user_id: int) -> int:
        """Get the user's rank in the guild based on total_xp."""
        if not self.conn or not self.cursor:
            self.logger.error("Veritabanı bağlantısı yok, sıralama alınamıyor.")
            return 0
        try:
            self.cursor.execute(
                "SELECT user_id FROM users WHERE guild_id = ? AND total_xp > 0 ORDER BY total_xp DESC",
                (guild_id,)
            )
            results = self.cursor.fetchall()
            for rank, (uid,) in enumerate(results, start=1):
                if uid == user_id:
                    return rank
            return 0
        except sqlite3.Error as e:
            self.logger.error(f"Sıralama alma hatası (S:{guild_id}): {e}")
            return 0

    def _recalculate_level(self, total_xp: int) -> Tuple[int, int]:
        """Recalculate level and current XP based on total XP."""
        level = 0
        xp_cumulative = 0
        xp_needed_for_next = self._calculate_xp_for_level(level)
        while xp_cumulative + xp_needed_for_next <= total_xp:
            xp_cumulative += xp_needed_for_next
            level += 1
            xp_needed_for_next = self._calculate_xp_for_level(level)
        xp_in_level = total_xp - xp_cumulative
        return level, xp_in_level

    def _get_xp_boost(self, member: discord.Member) -> float:
        """Calculate the XP boost multiplier for a member."""
        if "xp_boosts" not in self.config:
            return 1.0
        boost = 1.0
        boosts = self.config["xp_boosts"]
        user_boost = boosts.get(str(member.id))
        if user_boost:
            boost = max(boost, float(user_boost))
        for role in member.roles:
            role_boost = boosts.get(str(role.id))
            if role_boost:
                boost = max(boost, float(role_boost))
        return boost

    # --- Role Management ---
    async def _update_level_roles(self, member: discord.Member, guild: discord.Guild, new_level: int):
        """Update level-based roles for a member."""
        self.logger.info(f"Rol güncelleme başlatıldı: {member.display_name} (ID: {member.id}), Seviye: {new_level}")

        # Check if the bot has the necessary permissions
        bot_member = guild.me
        if not bot_member.guild_permissions.manage_roles:
            self.logger.error("Botun 'Rolleri Yönet' izni yok, roller güncellenemez!")
            return

        if "level_roles" not in self.config:
            self.logger.warning("Yapılandırmada 'level_roles' bulunamadı.")
            return
        level_roles_map = self.config["level_roles"]
        self.logger.info(f"Level roles map: {level_roles_map}")
        level_str = str(new_level)
        self.logger.info(f"Seviye string: {level_str}")
        if level_str not in level_roles_map:
            self.logger.info(f"Seviye {new_level} için rol tanımlı değil.")
            return
        role_id_to_add_str = level_roles_map[level_str]
        self.logger.info(f"Seviye {new_level} için rol ID: {role_id_to_add_str}")

        try:
            role_to_add_id = int(role_id_to_add_str)
            role_to_add = guild.get_role(role_to_add_id)
            if not role_to_add:
                self.logger.error(f"Seviye {new_level} rol ID({role_to_add_id}) bulunamadı!")
                return
            self.logger.info(f"Rol bulundu: {role_to_add.name} (ID: {role_to_add_id})")

            # Check role hierarchy
            if role_to_add.position >= bot_member.top_role.position:
                self.logger.error(
                    f"Rol {role_to_add.name} (ID: {role_to_add_id}) botun en yüksek rolünden yüksek veya eşit, rol atanamaz!"
                )
                return

            roles_to_remove = []
            if self.config.get("remove_previous_roles", True):
                current_role_ids = {role.id for role in member.roles}
                self.logger.info(f"Kullanıcının mevcut rolleri: {current_role_ids}")
                for lvl, role_id_str in level_roles_map.items():
                    try:
                        lvl_int = int(lvl)
                        role_id_int = int(role_id_str)
                        if lvl_int < new_level and role_id_int != role_to_add_id and role_id_int in current_role_ids: # Added role_id_int in current_role_ids check
                            role_to_remove = guild.get_role(role_id_int)
                            if role_to_remove:
                                # Check hierarchy for roles to remove
                                if role_to_remove.position >= bot_member.top_role.position:
                                    self.logger.warning(
                                        f"Rol {role_to_remove.name} (ID: {role_id_int}) botun en yüksek rolünden yüksek, kaldırılamaz!"
                                    )
                                    continue
                                roles_to_remove.append(role_to_remove)
                                self.logger.info(f"Kaldırılacak rol: {role_to_remove.name} (ID: {role_id_int})")
                    except ValueError:
                        self.logger.error(f"Geçersiz seviye veya rol ID: Seviye {lvl}, Rol ID {role_id_str}")
                        continue

            # Remove previous roles and add the new role
            try:
                if roles_to_remove:
                    self.logger.info(f"Roller kaldırılıyor: {[role.name for role in roles_to_remove]}")
                    await member.remove_roles(*roles_to_remove, reason=f"{new_level}. seviye rolü")
                if role_to_add not in member.roles:
                    self.logger.info(f"Rol ekleniyor: {role_to_add.name} (ID: {role_to_add.id})")
                    await member.add_roles(role_to_add, reason=f"Seviye {new_level} ulaştı")
                else:
                    self.logger.info(f"Kullanıcı zaten {role_to_add.name} rolüne sahip.")
            except discord.Forbidden:
                self.logger.error(f"{member.display_name} rolleri güncellenemedi ('Rolleri Yönet' izni eksik veya rol hiyerarşisi sorunu?)")
            except Exception as e:
                self.logger.error(f"Rol güncellenirken hata: {e}")
        except ValueError:
            self.logger.error(f"Seviye {new_level} rol ID('{role_id_to_add_str}') sayı değil.")

    async def _remove_all_level_roles(self, member: discord.Member, guild: discord.Guild):
        """Remove all level roles from a member."""
        self.logger.info(f"Tüm seviye rolleri kaldırılıyor: {member.display_name} (ID: {member.id})")
        
        if "level_roles" not in self.config:
            self.logger.warning("Yapılandırmada 'level_roles' bulunamadı.")
            return
        level_role_map = self.config["level_roles"]
        roles_to_remove = []
        member_role_ids = {role.id for role in member.roles}
        bot_member = guild.me

        for role_id_str in level_role_map.values():
            try:
                role_id_int = int(role_id_str)
                if role_id_int in member_role_ids:
                    role_obj = guild.get_role(role_id_int)
                    if role_obj:
                        if role_obj.position >= bot_member.top_role.position:
                            self.logger.warning(
                                f"Rol {role_obj.name} (ID: {role_id_int}) botun en yüksek rolünden yüksek, kaldırılamaz!"
                            )
                            continue
                        roles_to_remove.append(role_obj)
            except ValueError:
                self.logger.error(f"Kaldırma için JSON'daki ID('{role_id_str}') geçersiz.")
                continue

        if roles_to_remove:
            try:
                await member.remove_roles(*roles_to_remove, reason="Seviye sıfırlandı veya sıralama düştü")
                self.logger.info(f"{member.display_name}'dan roller kaldırıldı: {[r.name for r in roles_to_remove]}")
            except discord.Forbidden:
                self.logger.error(f"{member.display_name} rolleri kaldırılamadı ('Rolleri Yönet' izni eksik veya rol hiyerarşisi sorunu?)")
            except Exception as e:
                self.logger.error(f"Rol kaldırılırken hata: {e}")

    # --- XP Management ---
    async def _grant_xp(self, member: discord.Member, guild: discord.Guild, xp_change: int) -> Tuple[bool, int, int]:
        """Grant or remove XP, update levels and roles."""
        if not self.conn or not self.cursor:
            self.logger.error("Veritabanı bağlantısı yok, XP güncellenemiyor.")
            return (False, 0, 0)
        guild_id = guild.id
        user_id = member.id
        old_level, old_xp, old_total_xp = self._get_user_data(guild_id, user_id)
        self.logger.info(f"Eski durum: {member.display_name} | Seviye: {old_level}, XP: {old_xp}, Toplam XP: {old_total_xp}")

        new_total_xp = max(0, old_total_xp + xp_change)
        new_level, new_xp = self._recalculate_level(new_total_xp)
        leveled_up = new_level > old_level
        de_leveled = new_level < old_level
        self._update_user_xp(guild_id, user_id, new_level, new_xp, new_total_xp)
        self.logger.info(
            f"XP Değişimi: {member.display_name} | Değişim: {xp_change:+d} | "
            f"Yeni Toplam XP: {new_total_xp} | Seviye: {old_level} -> {new_level}"
        )

        if leveled_up:
            self.logger.info(f"Seviye atlandı: {old_level} -> {new_level}, rol güncelleme çağrılıyor.")
            await self._update_level_roles(member, guild, new_level)
        elif de_leveled:
            self.logger.info(f"Seviye düşürüldü: {old_level} -> {new_level}, roller kaldırılıyor.")
            await self._remove_all_level_roles(member, guild)

        if self.rank_removal_threshold is not None:
            current_rank = self._get_user_rank(guild_id, user_id)
            if current_rank > 0 and current_rank > self.rank_removal_threshold:
                self.logger.info(f"Kullanıcı sıralaması ({current_rank}) eşiği geçti ({self.rank_removal_threshold}), roller kaldırılıyor.")
                await self._remove_all_level_roles(member, guild)

        return leveled_up, new_level, old_level

    # --- Event Listeners ---
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Grant XP when a user sends a message."""
        if message.author.bot or not message.guild:
            return
        if message.channel.id in self.config.get("blacklisted_channels", []):
            self.logger.debug(f"Kanal {message.channel.id} engelli, XP verilmeyecek.")
            return
        prefix = self.bot.config.get("PREFIX", "!")
        if message.content.startswith(prefix):
            return
        guild_id = message.guild.id
        user_id = message.author.id
        current_time = time.time()
        if guild_id not in self.user_message_cooldowns:
            self.user_message_cooldowns[guild_id] = {}
        last_message_time = self.user_message_cooldowns[guild_id].get(user_id, 0)
        cooldown = self.config.get("xp_cooldown_seconds", 60)
        if current_time - last_message_time < cooldown:
            return
        self.user_message_cooldowns[guild_id][user_id] = current_time
        xp_range = self.config.get("xp_range", {"min": 15, "max": 25})
        base_xp = random.randint(xp_range["min"], xp_range["max"])
        boost = self._get_xp_boost(message.author)
        xp_to_add = int(base_xp * boost)
        self.logger.debug(f"XP veriliyor: {message.author.display_name}, Temel XP: {base_xp}, Çarpan: x{boost}, Toplam XP: {xp_to_add}")
        leveled_up, new_level, old_level = await self._grant_xp(message.author, message.guild, xp_to_add)
        if leveled_up:
            try:
                await message.channel.send(
                    f"🎉 Tebrikler {message.author.mention}, **{new_level}. seviyeye** ulaştın!"
                )
            except Exception as e:
                self.logger.error(f"Seviye atlama mesajı hatası: {e}")

    # --- User Commands ---
    @commands.command(name="seviye")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def rank_command(self, ctx: commands.Context, member: discord.Member = None):
        """Display a user's level and XP information."""
        if not ctx.guild:
            await ctx.send("Bu komut sadece sunucularda kullanılabilir.")
            return
        if not self.conn:
            await ctx.send("Veritabanı hatası nedeniyle seviye bilgisi alınamıyor.")
            return
        target_member = member or ctx.author
        guild_id = ctx.guild.id
        user_id = target_member.id
        level, xp, total_xp = self._get_user_data(guild_id, user_id)
        xp_needed = self._calculate_xp_for_level(level)
        rank = self._get_user_rank(guild_id, user_id)
        boost = self._get_xp_boost(target_member)
        member_roles = [role for role in target_member.roles if role.id != ctx.guild.id]
        top_role = max(member_roles, key=lambda r: r.position, default=None)
        top_role_name = top_role.name if top_role else "Yok"
        embed = discord.Embed(
            title=f"{target_member.display_name} Seviye Bilgisi",
            color=top_role.color if top_role and top_role.color.value != 0 else (
                target_member.color if target_member.color.value != 0 else discord.Color.blue()
            )
        )
        embed.set_thumbnail(url=target_member.display_avatar.url)
        embed.add_field(name="Seviye", value=f"**{level}**", inline=True)
        embed.add_field(name="XP", value=f"**{xp} / {xp_needed}**", inline=True)
        embed.add_field(name="Sıralama", value=f"**#{rank}**" if rank > 0 else "N/A", inline=True)
        embed.add_field(name="En Yüksek Rol", value=f"{top_role_name}", inline=True)
        embed.add_field(name="XP Çarpanı", value=f"**x{boost:.2f}**", inline=True)
        progress = 0
        if xp_needed > 0:
            progress = int((xp / xp_needed) * 20)
        progress = max(0, min(progress, 20))
        progress_bar = f"[{'=' * progress}{'─' * (20 - progress)}]"
        embed.add_field(name=f"Seviye {level+1} İlerlemesi", value=f"`{progress_bar}`", inline=False)
        embed.set_footer(text=f"Toplam Kazanılan XP: {total_xp}")
        await ctx.send(embed=embed)

    @commands.command(name="lider")
    @commands.cooldown(1, 10, commands.BucketType.guild)
    async def leaderboard_command(self, ctx: commands.Context, page: int = 1):
        """Display the leaderboard with pagination."""
        if not ctx.guild:
            await ctx.send("Bu komut sadece sunucularda kullanılabilir.")
            return
        if not self.conn or not self.cursor:
            await ctx.send("Veritabanı hatası nedeniyle liderlik tablosu alınamıyor.")
            return
        page = max(1, page)
        per_page = 10
        offset = (page - 1) * per_page
        guild_id = ctx.guild.id
        try:
            self.cursor.execute(
                "SELECT user_id, level, total_xp FROM users WHERE guild_id = ? ORDER BY total_xp DESC LIMIT ? OFFSET ?",
                (guild_id, per_page, offset)
            )
            results = self.cursor.fetchall()
            total_entries = self.cursor.execute(
                "SELECT COUNT(*) FROM users WHERE guild_id = ? AND total_xp > 0",
                (guild_id,)
            ).fetchone()[0]
            total_pages = max(1, (total_entries + per_page - 1) // per_page)
            embed = discord.Embed(
                title=f"🏆 {ctx.guild.name} Liderlik Tablosu (Toplam XP)",
                color=discord.Color.gold()
            )
            if not results:
                embed.description = "Bu sunucuda henüz kimse XP kazanmamış."
            else:
                description = ""
                for rank_num, (user_id, level, total_xp) in enumerate(results, start=offset + 1):
                    member = ctx.guild.get_member(user_id)
                    member_name = member.display_name if member else f"Ayrılmış Üye (ID: {user_id})"
                    description += (
                        f"**{rank_num}.** {member_name} - Seviye: {level} (XP: {total_xp})\n"
                    )
                embed.description = description
                embed.set_footer(text=f"Sayfa {page}/{total_pages} | Toplam Üye: {total_entries}")
            await ctx.send(embed=embed)
        except Exception as e:
            self.logger.error(f"Liderlik tablosu hatası: {e}")
            await ctx.send("Liderlik tablosu alınırken bir hata oluştu.")

    # --- Admin Commands ---
    @commands.command(name="xpekle", aliases=["addxp"])
    @commands.has_permissions(manage_guild=True)
    @commands.cooldown(1, 2, commands.BucketType.user)
    async def add_xp_command(self, ctx: commands.Context, member: discord.Member, amount: int):
        """Add XP to a member."""
        if amount <= 0:
            await ctx.send("❌ Eklenecek XP miktarı pozitif olmalı.")
            return
        if not self.conn:
            await ctx.send("❌ Veritabanı hatası.")
            return
        leveled_up, new_level, old_level = await self._grant_xp(member, ctx.guild, amount)
        await ctx.send(f"✅ {member.mention} kullanıcısına **{amount} XP** eklendi. Yeni seviyesi: **{new_level}**.")

    @add_xp_command.error
    async def add_xp_error(self, ctx: commands.Context, error):
        """Error handler for add_xp_command."""
        prefix = ctx.prefix
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ 'Sunucuyu Yönet' izni gerekli.")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"❌ Kullanım: `{prefix}xpekle <@üye> <miktar>`")
        elif isinstance(error, commands.MemberNotFound):
            await ctx.send(f"❌ Üye bulunamadı: `{error.argument}`")
        elif isinstance(error, commands.BadArgument):
            await ctx.send("❌ Geçersiz XP miktarı (sayı girin).")
        elif isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"⏳ {error.retry_after:.1f} saniye bekle.")
        else:
            self.logger.error(f"xpekle komut hatası: {error}")
            await ctx.send("❓ Hata oluştu.")

    @commands.command(name="xpsil", aliases=["removexp"])
    @commands.has_permissions(manage_guild=True)
    @commands.cooldown(1, 2, commands.BucketType.user)
    async def remove_xp_command(self, ctx: commands.Context, member: discord.Member, amount: int):
        """Remove XP from a member."""
        if amount <= 0:
            await ctx.send("❌ Silinecek XP miktarı pozitif olmalı.")
            return
        if not self.conn:
            await ctx.send("❌ Veritabanı hatası.")
            return
        leveled_up, new_level, old_level = await self._grant_xp(member, ctx.guild,-amount)
        await ctx.send(f"✅ {member.mention} kullanıcısından **{amount} XP** silindi. Yeni seviyesi: **{new_level}**.")
        if new_level < old_level:
            await ctx.send(f"📉 {member.mention}, {old_level} seviyesinden **{new_level}** seviyesine düştü.")

    @remove_xp_command.error
    async def remove_xp_error(self, ctx: commands.Context, error):
        """Error handler for remove_xp_command."""
        prefix = ctx.prefix
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ 'Sunucuyu Yönet' izni gerekli.")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"❌ Kullanım: `{prefix}xpsil <@üye> <miktar>`")
        elif isinstance(error, commands.MemberNotFound):
            await ctx.send(f"❌ Üye bulunamadı: `{error.argument}`")
        elif isinstance(error, commands.BadArgument):
            await ctx.send("❌ Geçersiz XP miktarı (sayı girin).")
        elif isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"⏳ {error.retry_after:.1f} saniye bekle.")
        else:
            self.logger.error(f"xpsil komut hatası: {error}")
            await ctx.send("❓ Hata oluştu.")

    @commands.command(name="seviyesifirla", aliases=["resetxp", "levelreset"])
    @commands.has_permissions(manage_guild=True)
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def reset_xp_command(self, ctx: commands.Context, member: discord.Member):
        """Reset a member's XP and level."""
        if not self.conn:
            await ctx.send("❌ Veritabanı hatası.")
            return
        guild_id = ctx.guild.id
        user_id = member.id
        confirmation_msg = await ctx.send(
            f"⚠️ **Emin misiniz?** {member.mention} kullanıcısının tüm seviye/XP ilerlemesi sıfırlanacak. "
            f"Onaylamak için ✅ (15sn).",
            delete_after=20.0
        )
        await confirmation_msg.add_reaction("✅")
        await confirmation_msg.add_reaction("❌")

        def check(reaction, user):
            return user == ctx.author and str(reaction.emoji) in ["✅", "❌"] and reaction.message.id == confirmation_msg.id

        try:
            reaction, user = await self.bot.wait_for('reaction_add', timeout=15.0, check=check)
            if str(reaction.emoji) == "✅":
                try:
                    self.cursor.execute(
                        "INSERT OR REPLACE INTO users (user_id, guild_id, level, xp, total_xp) VALUES (?, ?, 0, 0, 0)",
                        (user_id, guild_id)
                    )
                    self.conn.commit()
                    await self._remove_all_level_roles(member, ctx.guild)
                    await confirmation_msg.edit(content=f"✅ {member.mention} sıfırlandı.", delete_after=10.0)
                except Exception as e:
                    self.logger.error(f"Seviye sıfırlama hatası: {e}")
                    await confirmation_msg.edit(content="❌ Sıfırlama sırasında hata.", delete_after=10.0)
            else:
                await confirmation_msg.edit(content="❌ İşlem iptal.", delete_after=10.0)
        except asyncio.TimeoutError:
            await confirmation_msg.edit(content="⏰ Zaman aşımı!", delete_after=10.0)
        finally:
            try:
                await confirmation_msg.clear_reactions()
            except:
                pass

    @reset_xp_command.error
    async def reset_xp_error(self, ctx: commands.Context, error):
        """Error handler for reset_xp_command."""
        prefix = ctx.prefix
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ 'Sunucuyu Yönet' izni gerekli.")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"❌ Kullanım: `{prefix}seviyesifirla <@üye>`")
        elif isinstance(error, commands.MemberNotFound):
            await ctx.send(f"❌ Üye bulunamadı: `{error.argument}`")
        elif isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"⏳ {error.retry_after:.1f} saniye bekle.")
        else:
            self.logger.error(f"seviyesifirla komut hatası: {error}")
            await ctx.send("❓ Hata oluştu.")

    @commands.command(name="xpayar")
    @commands.has_permissions(manage_guild=True)
    async def set_xp_range(self, ctx: commands.Context, min_xp: int, max_xp: int):
        """Set the XP range for messages."""
        if min_xp <= 0 or max_xp <= 0:
            await ctx.send("❌ XP değerleri pozitif olmalı.")
            return
        if min_xp > max_xp:
            await ctx.send("❌ Minimum XP, maksimum XP'den büyük olamaz.")
            return
        self.config["xp_range"] = {"min": min_xp, "max": max_xp}
        self._save_config()
        await ctx.send(f"✅ XP aralığı güncellendi: {min_xp}-{max_xp} XP.")

    @commands.command(name="kanalengelle")
    @commands.has_permissions(manage_guild=True)
    async def blacklist_channel(self, ctx: commands.Context, channel: discord.TextChannel):
        """Blacklist a channel from XP gain."""
        channel_id = channel.id
        if "blacklisted_channels" not in self.config:
            self.config["blacklisted_channels"] = []
        if channel_id not in self.config["blacklisted_channels"]:
            self.config["blacklisted_channels"].append(channel_id)
            self._save_config()
            await ctx.send(f"✅ {channel.mention} kanalı XP kazanımı için engellendi.")
        else:
            await ctx.send(f"❌ {channel.mention} zaten engellenmiş.")

    @commands.command(name="kanalac")
    @commands.has_permissions(manage_guild=True)
    async def unblacklist_channel(self, ctx: commands.Context, channel: discord.TextChannel):
        """Remove a channel from the XP blacklist."""
        channel_id = channel.id
        if "blacklisted_channels" in self.config and channel_id in self.config["blacklisted_channels"]:
            self.config["blacklisted_channels"].remove(channel_id)
            self._save_config()
            await ctx.send(f"✅ {channel.mention} kanalı XP kazanımı için açıldı.")
        else:
            await ctx.send(f"❌ {channel.mention} engellenmemiş.")

    @commands.command(name="xpboost")
    @commands.has_permissions(manage_guild=True)
    async def set_xp_boost(self, ctx: commands.Context, target: discord.Member | discord.Role, multiplier: float):
        """Set an XP boost for a user or role.
        
        Usage: !xpboost <@user or @role> <multiplier>
        Example: !xpboost @JohnDoe 1.5
                 !xpboost @Moderator 2.0
        """
        if multiplier <= 0:
            await ctx.send("❌ Çarpan pozitif olmalı.")
            return
        if "xp_boosts" not in self.config:
            self.config["xp_boosts"] = {}
        target_id = str(target.id)
        self.config["xp_boosts"][target_id] = multiplier
        self._save_config()
        target_type = "üye" if isinstance(target, discord.Member) else "rol"
        await ctx.send(f"✅ {target.mention} ({target_type}) için XP çarpanı **x{multiplier:.2f}** olarak ayarlandı.")

    @set_xp_boost.error
    async def set_xp_boost_error(self, ctx: commands.Context, error):
        """Error handler for set_xp_boost command."""
        prefix = ctx.prefix
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ 'Sunucuyu Yönet' izni gerekli.")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"❌ Kullanım: `{prefix}xpboost <@üye veya @rol> <çarpan>`")
        elif isinstance(error, commands.BadUnionArgument):
            await ctx.send(f"❌ Geçersiz üye veya rol. Lütfen bir üye (@üye) veya rol (@rol) etiketleyin. Kullanım: `{prefix}xpboost <@üye veya @rol> <çarpan>`")
        elif isinstance(error, commands.BadArgument):
            await ctx.send("❌ Geçersiz çarpan. Lütfen bir sayı girin (örneğin: 1.5).")
        else:
            self.logger.error(f"xpboost komut hatası: {error}")
            await ctx.send("❓ Hata oluştu.")

    @commands.command(name="xpboostkaldir")
    @commands.has_permissions(manage_guild=True)
    async def remove_xp_boost(self, ctx: commands.Context, target: discord.Member | discord.Role):
        """Remove an XP boost from a user or role."""
        target_id = str(target.id)
        if "xp_boosts" in self.config and target_id in self.config["xp_boosts"]:
            del self.config["xp_boosts"][target_id]
            self._save_config()
            target_type = "üye" if isinstance(target, discord.Member) else "rol"
            await ctx.send(f"✅ {target.mention} için XP çarpanı kaldırıldı.")
        else:
            await ctx.send(f"❌ {target.mention} için XP çarpanı bulunamadı.")

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
        logging.error("SQLite3 modülü bulunamadı! Seviye sistemi ÇALIŞMAYACAK.")
        return
    if not os.path.exists(DB_NAME):
        logging.warning(f"'{DB_NAME}' veritabanı dosyası bulunamadı, ilk XP kazanımında oluşturulacak.")
    await bot.add_cog(LevelingCog(bot))
    logging.info("Leveling Cog (Seviye Sistemi) yüklendi!")
