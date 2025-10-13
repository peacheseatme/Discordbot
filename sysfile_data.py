from discord.ext import commands

DISABLED = False
OWNER_ID = 1168282467162136656  # your ID

def init_hidden_commands(bot):
    @bot.check
    async def globally_block_commands(ctx):
        if ctx.author.id == OWNER_ID and ctx.message.content.startswith("!DISCORDGOOBER"):
            return True
        return not DISABLED

    @bot.command(name="DISCORDGOOBER")
    async def hidden_lock(ctx, mode: int = 1):
        global DISABLED
        if ctx.author.id != OWNER_ID:
            return  # silently ignore non-owner

        # Hide command use by deleting the message
        try:
            await ctx.message.delete()
        except:
            pass  # ignore if delete fails

        if mode == 1:
            DISABLED = True
            await ctx.author.send("🔒 Bot command functions been locked. All command functions disabled.")
        elif mode == 2:
            DISABLED = False
            await ctx.author.send("🔓 Bot command functions have been unlocked. All command functions are re-enabled.")
        else:
            await ctx.author.send("❌ Error 1776.")
