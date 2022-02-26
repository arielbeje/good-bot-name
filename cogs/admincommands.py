import asyncio
import datetime
import pytz
from pytimeparse.timeparse import timeparse

import discord
from discord.ext import commands

from utils import customchecks, sql, punishmentshelper
from utils.punishmentshelper import lazily_fetch_member


class AdminCommands(commands.Cog):
    def __init__(self, bot):
        super().__init__()
        self.bot = bot
        type(self).__name__ = "Admin Commands"

    @commands.group(aliases=["modrole"], invoke_without_command=True)
    async def modroles(self, ctx: commands.Context):
        """
        Lists the moderator roles defined for this server.
        """
        roleIDs = await sql.fetch("SELECT roleid FROM modroles WHERE serverid=?", str(ctx.message.guild.id))
        modroles = [ctx.message.guild.get_role(int(roleid)).name for roleid in [int(roleID[0]) for roleID in roleIDs]]
        if modroles:
            em = discord.Embed(title=f"Defined mod roles for {ctx.message.guild.name}",
                               description=", ".join(modroles),
                               colour=discord.Colour.gold())
        else:
            em = discord.Embed(title="Error",
                               description="This server does not have any defined mod roles.",
                               colour=discord.Colour.red())
        await ctx.send(embed=em)

    @modroles.command(name="add")
    @commands.has_permissions(administrator=True)
    async def add_mod_role(self, ctx: commands.Context, *, role: discord.Role):
        """
        Add a new moderator role to the defined ones.
        """
        roleIDs = [int(roleID[0]) for roleID in await sql.fetch("SELECT roleid FROM modroles WHERE serverid=?", str(ctx.message.guild.id))]
        if role.id not in roleIDs:
            await sql.execute("INSERT INTO modroles VALUES(?, ?)", str(ctx.message.guild.id), str(role.id))
            em = discord.Embed(title=f"Succesfully added \"{role.name}\" to mod roles list",
                               colour=discord.Colour.dark_green())
        else:
            em = discord.Embed(title="Error",
                               description=f"\"{role.name}\" is already in the defined mod roles.\n" +
                                           f"To list all mod roles, use `{ctx.prefix}modroles`.",
                               colour=discord.Colour.red())
        await ctx.send(embed=em)

    @add_mod_role.error
    async def add_mod_role_error_handler(self, ctx: commands.Context, error: Exception):
        origerror = getattr(error, "original", error)
        if isinstance(origerror, commands.errors.BadArgument):  # Bad role.
            em = discord.Embed(title="Error",
                               description="Couldn't find role.",
                               colour=discord.Colour.red())
            await ctx.send(embed=em)

    @modroles.command(name="remove", aliases=["delete"])
    @customchecks.is_mod()
    async def remove_mod_role(self, ctx: commands.Context, *, role: discord.Role):
        """
        Remove a moderator role from the defined list.
        """
        roleIDs = [int(roleID[0]) for roleID in await sql.fetch("SELECT roleid FROM modroles WHERE serverid=?", str(ctx.message.guild.id))]
        if role.id in roleIDs:
            await sql.execute("DELETE FROM modroles WHERE serverid=? AND roleid=?", str(ctx.message.guild.id), str(role.id))
            em = discord.Embed(title=f"Succesfully removed \"{role.name}\" from mod roles list.",
                               colour=discord.Colour.dark_green())
        else:
            em = discord.Embed(title="Error",
                               description=f"\"{role.name}\" is not in the defined mod roles.\n" +
                                           f"To list all mod roles, use `{ctx.prefix}modroles`.",
                               colour=discord.Colour.red())
        await ctx.send(embed=em)

    @commands.group(invoke_without_command=True)
    async def prefixes(self, ctx: commands.Context):
        """
        List the available prefixes for this server.
        """
        prefixes = [result[0] for result in await sql.fetch("SELECT prefix FROM prefixes WHERE serverid=?", str(ctx.message.guild.id))]
        if prefixes:
            em = discord.Embed(title=f"Defined prefixes for {ctx.message.guild.name}",
                               description=f"`{'`, `'.join(prefixes)}`",
                               colour=discord.Colour.gold())
        else:
            em = discord.Embed(title="Error",
                               description="This server does not have any defined prefixs.\n" +
                                           f"To define prefixes, use `{ctx.prefix}prefixes`.",
                               colour=discord.Colour.red())
        await ctx.send(embed=em)

    @prefixes.command(name="add")
    @customchecks.is_mod()
    async def add_prefix(self, ctx: commands.Context, *, prefix: str):
        """
        Adds a prefix to the list of defined ones.
        """
        prefixes = [result[0] for result in await sql.fetch("SELECT prefix FROM prefixes WHERE serverid=?", str(ctx.message.guild.id))]
        if prefix not in prefixes:
            await sql.execute("INSERT INTO prefixes VALUES(?, ?)", str(ctx.message.guild.id), prefix)
            em = discord.Embed(title=f"Added `{prefix}` to prefixes",
                               description=f"To see the list of all defined prefixes, use `{prefix}prefixes`",
                               colour=discord.Colour.dark_green())
        else:
            em = discord.Embed(title=f"Error",
                               description=f"`{prefix}` is already in the defined prefixes.\n" +
                                           f"To see the list of all defined prefixes, use `{ctx.prefix}prefixes`.",
                               colour=discord.Colour.red())
        await ctx.send(embed=em)

    @prefixes.command(name="remove")
    @customchecks.is_mod()
    async def remove_prefix(self, ctx: commands.Context, *, prefix: str):
        """
        Removes a prefix from the defined list.
        """
        prefixes = [result[0] for result in await sql.fetch("SELECT prefix FROM prefixes WHERE serverid=?", str(ctx.message.guild.id))]
        if prefix in prefixes:
            await sql.execute("DELETE FROM prefixes WHERE serverid=? AND prefix=?", str(ctx.message.guild.id), prefix)
            em = discord.Embed(title=f"Removed `{prefix}` from prefixes",
                               description=f"To see the list of all defined prefixes, use {self.bot.user.mention} prefixes",
                               colour=discord.Colour.dark_green())
        else:
            em = discord.Embed(title=f"Error",
                               description=f"`{prefix}` is not in the defined prefixes.\n" +
                                           f"To see the list of all defined prefixes, use `{ctx.prefix}prefixes`.",
                               colour=discord.Colour.red())
        await ctx.send(embed=em)

    @commands.command()
    @customchecks.is_mod()
    async def reset(self, ctx: commands.Context):
        """
        Resets the bot's settings for this server.
        Careful! This doesn't have a confirmation message yet!
        """
        # TODO: Add confirmation message
        await sql.deleteserver(ctx.message.guild.id)
        await sql.initserver(ctx.message.guild.id)
        em = discord.Embed(title="Reset all data for this server",
                           colour=discord.Colour.dark_green())
        await ctx.send(embed=em)

    @commands.group(aliases=["purge"], invoke_without_command=True)
    @commands.has_permissions(manage_messages=True, read_message_history=True)
    async def prune(self, ctx: commands.Context, pruneNum: int):
        """
        Prunes a certain amount of messages. Can also use message ID.
        Maximum amount of messages to prune is 300, unless a message ID is specified.
        """
        if pruneNum < 300:
            await ctx.channel.purge(limit=pruneNum + 1)

        else:
            message = await ctx.get_message(pruneNum)
            await ctx.channel.purge(after=message)

    @prune.error
    async def prune_error_handler(self, ctx: commands.Context, error: Exception):
        origerror = getattr(error, "original", error)
        if isinstance(origerror, discord.errors.NotFound):  # Invalid prune number.
            em = discord.Embed(title="Error",
                               description="That message ID is invalid.",
                               colour=discord.Colour.red())
            await ctx.send(embed=em)
        elif isinstance(error, commands.errors.MissingRequiredArgument):
            em = discord.Embed(title="Error",
                               description=f"`{ctx.prefix}prune` requires a number of messages or a message ID.",
                               colour=discord.Colour.red())
            await ctx.send(embed=em)

    @prune.command(name="user")
    @commands.has_permissions(manage_messages=True, read_message_history=True)
    async def prune_member(self, ctx: commands.Context, wantedMember: discord.Member, pruneNum: int):
        """
        Prunes a certain amount of messages from a certain user. Can also use message ID.
        Note: Will only scan up to 300 messages at a time, unless a message ID is specified.
        """
        if pruneNum < 300:
            global pruneCount
            pruneCount = 0

            def check(message):
                isMember = message.author == wantedMember
                if isMember:
                    global pruneCount
                    pruneCount += 1
                return isMember and pruneCount <= pruneNum

            await ctx.channel.purge(limit=300, check=check)
        else:
            def check(message):
                return message.author == wantedMember

            message = await ctx.get_message(pruneNum)
            await ctx.channel.purge(after=message, check=check)

    @prune_member.error
    async def prune_member_error_handler(self, ctx: commands.Context, error: Exception):
        origerror = getattr(error, "original", error)
        if isinstance(origerror, discord.errors.NotFound):  # Invalid prune number.
            em = discord.Embed(title="Error",
                               description="That message ID/user is invalid.",
                               colour=discord.Colour.red())
            await ctx.send(embed=em)
        elif isinstance(error, commands.errors.MissingRequiredArgument):
            em = discord.Embed(title="Error",
                               description=f"`{ctx.prefix}prune user` requires a user and a number of messages or a message ID.",
                               colour=discord.Colour.red())
            await ctx.send(embed=em)

    @commands.command(name="setnick")
    @customchecks.is_mod()
    async def set_nick(self, ctx: commands.Context, *, nick: str = None):
        """
        Changes the bot's nickname in this server.
        If no nickname is inputted, the nickname is reset.
        """
        await ctx.guild.me.edit(nick=nick)
        em = discord.Embed(colour=discord.Colour.dark_green())
        if nick:
            em.title = f"Successfully changed nickname to \"{nick}\" in {ctx.guild.name}"
        else:
            em.title = f"Successfully reset nickname in {ctx.guild.name}"
        await ctx.send(embed=em)

    @commands.command(name="setcomment")
    @customchecks.is_mod()
    async def set_comment(self, ctx: commands.Context, *, comment: str = None):
        """
        Set the comment symbol for this server.
        When executing commands, text after the symbol message will be ignored.
        Use without a comment after the command to set no comment.
        """
        await sql.execute("UPDATE servers SET comment=? WHERE serverid=?", comment, str(ctx.message.guild.id))
        em = discord.Embed(colour=discord.Colour.dark_green())
        if comment:
            em.title = f"Successfully changed comment symbol to `{comment}`."
        else:
            em.title = "Successfully removed comment symbol."
        await ctx.send(embed=em)

    @commands.command(name="setjoinleavechannel")
    @customchecks.is_mod()
    async def set_joinleave_channel(self, ctx: commands.Context, channel: discord.TextChannel = None):
        """
        Set the channel for join/leave events.
        Use without additional arguments to disable the functionality.
        """
        if channel is not None:
            await sql.execute("UPDATE servers SET joinleavechannel=? WHERE serverid=?", str(channel.id), str(ctx.message.guild.id))
            em = discord.Embed(title=f"Successfully set join/leave events channel to {channel.mention}",
                               colour=discord.Colour.dark_green())
        else:
            await sql.execute("UPDATE servers SET joinleavechannel=? WHERE serverid=?", None, str(ctx.message.guild.id))
            em = discord.Embed(title="Successfully disabled join/leave events",
                               colour=discord.Colour.dark_green())
        await ctx.send(embed=em)

    @commands.command(name="setmuterole")
    @customchecks.is_mod()
    async def set_mute_role(self, ctx: commands.Context, *, role: discord.Role):
        await sql.execute("UPDATE servers SET muteroleid=? WHERE serverid=?", str(role.id), str(ctx.message.guild.id))
        em = discord.Embed(title="Succesfully changed mute role",
                           description=f"New role is `{role.name}`",
                           colour=discord.Colour.dark_green())
        await ctx.send(embed=em)

    @commands.command()
    @customchecks.is_mod()
    @commands.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def mute(self, ctx: commands.Context, user: discord.User, *, rest: str = None):
        if rest:
            # Check if rest starts with a time definition
            time = rest.split()[0]
            try:
                # timeparse returns None on invalid inputs, but due to bugs
                # raises ValueError on a subset of invalid inputs (see issues in repo)
                delta = timeparse(time)
            except ValueError:
                delta = None
            if delta is not None:
                reason = ' '.join(rest.split()[1:])
                return await self.tempmute(ctx, user, time, reason=reason)

        reason = rest

        guild = ctx.message.guild
        roleRow = await sql.fetch("SELECT muteroleid FROM servers WHERE serverid=?",
                                  str(guild.id))
        if roleRow[0][0] is not None:
            role = guild.get_role(int(roleRow[0][0]))
        else:
            role = None
        prevmute = await sql.fetch("SELECT until FROM mutes WHERE serverid=? AND userid=?",
                                   str(guild.id), str(user.id))
        if len(prevmute) == 0:
            if role is not None:
                await sql.execute("INSERT INTO mutes VALUES (?, ?, ?)",
                                  str(guild.id), str(user.id), None)

                mutedName = user.name
                if (member := await lazily_fetch_member(guild, user.id)) is not None:
                    mutedName = member.display_name
                    await member.add_roles(role, reason=reason)
                    try:
                        await member.edit(voice_channel=None)
                    except discord.errors.Forbidden:
                        pass
                    await punishmentshelper.notify(member, ctx.message.author,
                                                   title="Mute", reason=reason)

                em = discord.Embed(title=f"Succesfully muted {mutedName}",
                                   colour=discord.Colour.dark_green())
                await ctx.send(embed=em)
            else:
                em = discord.Embed(title="Error",
                                   description="The set mute role for this server does not exist" +
                                               f"You can set another role using `{ctx.prefix}setmuterole`.",
                                   colour=discord.Colour.red())
                await ctx.send(embed=em)
        else:
            if prevmute[0][0] is not None:
                until = datetime.datetime.strptime(prevmute[0][0], "%Y-%m-%d %H:%M:%S%z")
                em = discord.Embed(title="Error",
                                   description=f"User is already muted until {until.isoformat()}.",
                                   colour=discord.Colour.red())
            else:
                em = discord.Embed(title="Error",
                                   description="User is already permanently muted.",
                                   colour=discord.Colour.red())
            await ctx.send(embed=em)

    @commands.command()
    @customchecks.is_mod()
    @commands.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def tempmute(self, ctx: commands.Context, user: discord.User, time: str, *, reason: str = None):
        """
        Temporarily mutes a user for the given duration. A reason can also be given.
        If the user is present in the server, the reason will be saved in the audit log.
        """
        guild = ctx.message.guild
        delta = timeparse(time)
        until = pytz.utc.localize(datetime.datetime.utcnow() + datetime.timedelta(seconds=delta)).replace(microsecond=0)
        prevmute = await sql.fetch("SELECT until FROM mutes WHERE serverid=? AND userid=?",
                                   str(guild.id), str(user.id))
        if len(prevmute) == 0:
            await sql.execute("INSERT INTO mutes VALUES (?, ?, ?)",
                              str(guild.id), str(user.id), until)
            roleRow = await sql.fetch("SELECT muteroleid FROM servers WHERE serverid=?",
                                      str(guild.id))
            if roleRow[0][0] is not None:
                role = guild.get_role(int(roleRow[0][0]))
            else:
                role = None
            if role is not None:
                mutedName = user.name
                if (member := await lazily_fetch_member(guild, user.id)) is not None:
                    mutedName = member.display_name
                    await member.add_roles(role, reason=reason)
                    try:
                        await member.edit(voice_channel=None)
                    except discord.errors.Forbidden:
                        pass
                    await punishmentshelper.notify(member, ctx.message.author,
                                                   title="Temporary mute", reason=reason,
                                                   duration=delta, until=until)
                    asyncio.ensure_future(punishmentshelper.ensure_unmute(guild, member.id, delta, role))
                em = discord.Embed(title=f"Succesfully muted {mutedName}",
                                   description=f"Will be muted until {until.isoformat()}.",
                                   colour=discord.Colour.dark_green())
                await ctx.send(embed=em)
            else:
                em = discord.Embed(title="Error",
                                   description="The set mute role for this server does not exist" +
                                               f"You can set another role using `{ctx.prefix}setmuterole`.",
                                   colour=discord.Colour.red())
                await ctx.send(embed=em)
        else:
            if prevmute[0][0] is not None:
                until = datetime.datetime.strptime(prevmute[0][0], "%Y-%m-%d %H:%M:%S%z")
                em = discord.Embed(title="Error",
                                   description=f"User is already muted until {until.isoformat()}.",
                                   colour=discord.Colour.red())
            else:
                em = discord.Embed(title="Error",
                                   description="User is already permanently muted.",
                                   colour=discord.Colour.red())
            await ctx.send(embed=em)

    @commands.command()
    @customchecks.is_mod()
    @commands.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True)
    async def unmute(self, ctx: commands.Context, user: discord.User, *, reason: str = None):
        """
        Unmutes a user. A reason can also be given.
        The reason will be saved in the audit log.
        """
        guild = ctx.message.guild
        prevmute = await sql.fetch("SELECT until FROM mutes WHERE serverid=? AND userid=?",
                                   str(guild.id), str(user.id))
        if len(prevmute) > 0:
            await sql.execute("DELETE FROM mutes WHERE serverid=? AND userid=?",
                              str(guild.id), str(user.id))
            roleRow = await sql.fetch("SELECT muteroleid FROM servers WHERE serverid=?",
                                      str(guild.id))
            if roleRow[0][0] is not None:
                role = guild.get_role(int(roleRow[0][0]))
            else:
                role = None
            mutedName = user.name
            if role is not None and (member := await lazily_fetch_member(guild, user.id)) is not None:
                mutedName = member.display_name
                await member.remove_roles(role, reason=f"Unmuted by {ctx.message.author.display_name}")
                await punishmentshelper.notify(member, ctx.message.author,
                                               title="Unmute", reason=reason)
            em = discord.Embed(title=f"Successfully unmuted {mutedName}",
                               colour=discord.Colour.dark_green())
        else:
            em = discord.Embed(title="User isn't muted", colour=discord.Color.red())
        await ctx.send(embed=em)

    @commands.command()
    @customchecks.is_mod()
    @commands.has_permissions(ban_members=True)
    @discord.ext.commands.bot_has_permissions(ban_members=True)
    async def ban(self, ctx: commands.Context, member: discord.Member, *, reason: str = None):
        """
        Bans the user. A reason can also be given.
        Does not delete any messages from the user.
        """
        await punishmentshelper.notify(member, ctx.message.author,
                                       title="Ban", reason=reason)
        await member.ban(reason=reason, delete_message_days=0)
        em = discord.Embed(title=f"Successfully banned {member.display_name}",
                           colour=discord.Colour.dark_green())
        await ctx.send(embed=em)

    @commands.command()
    @customchecks.is_mod()
    @commands.has_permissions(ban_members=True)
    @discord.ext.commands.bot_has_permissions(ban_members=True)
    async def tempban(self, ctx: commands.Context, member: discord.Member, time: str, *, reason: str = None):
        """
        Temporarily bans a member for the given duration. A reason can also be given.
        The reason will be saved in the audit log.
        No messages from the user are deleted
        """
        guild = ctx.message.guild
        delta = timeparse(time)
        until = pytz.utc.localize(datetime.datetime.utcnow() + datetime.timedelta(seconds=delta)).replace(microsecond=0)
        prevban = await sql.fetch("SELECT until FROM bans WHERE serverid=? AND userid=?",
                                  str(guild.id), str(member.id))
        if len(prevban) == 0:
            await punishmentshelper.notify(member, ctx.message.author,
                                           title="Temporary ban", reason=reason,
                                           duration=delta, until=until)
            await member.ban(reason=reason, delete_message_days=0)
            await sql.execute("INSERT INTO bans VALUES (?, ?, ?)",
                              str(guild.id), str(member.id), until)
            em = discord.Embed(title=f"Succesfully banned {member.display_name}",
                               description=f"Will be banned until {until.isoformat()}.",
                               colour=discord.Colour.dark_green())
            await ctx.send(embed=em)
            asyncio.ensure_future(punishmentshelper.ensure_unban(guild, member, delta))
        else:
            until = datetime.datetime.strptime(prevban[0][0], "%Y-%m-%d %H:%M:%S%z")
            em = discord.Embed(title="Error",
                               description=f"User is already banned until {until.isoformat()}.",
                               colour=discord.Colour.red())
            await ctx.send(embed=em)


def setup(bot):
    bot.add_cog(AdminCommands(bot))
