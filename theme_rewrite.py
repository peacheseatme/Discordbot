import os

BOT_FILE = "bot.py"

# ================================
# 1. STRINGS TO DELETE
#    Anything in this list will be removed completely.
# ================================
DELETE_STRINGS = [
    "await interaction.response.send_message(",
    "await interaction.followup.send(",
    "await interaction.channel.send(",
    "interaction.response.send_message(",
    "interaction.followup.send(",
    "interaction.channel.send(",
]

# ==========================================
# 2. STRAIGHT REPLACEMENTS FOR THEME SYSTEM
#    old → new (exact text replacement)
# ==========================================
REPLACEMENTS = [
    ("✅ Deleted", "moderation.delete.success"),
    ("No valid roles provided!", "moderation.role.invalid"),
    ("❌ You cannot ban yourself.", "moderation.ban.self"),
    ("❌ You cannot ban someone with an equal or higher role.", "moderation.ban.higher_role"),
    ("❌ I don't have permission to ban this member.", "moderation.ban.no_permission"),
    ("❌ Invalid user ID.", "moderation.unban.invalid_id"),
    ("❌ No banned user with ID", "moderation.unban.not_found"),
    ("❌ I don't have permission to unban this user.", "moderation.unban.no_permission"),
    ("An error occurred:", "moderation.error.generic"),
    ("already has the role", "moderation.role.already_has"),
    ("Added role", "moderation.role.added"),
    ("do not have permission to add", "moderation.role.add_no_permission"),
    ("does not have the role", "moderation.role.not_found"),
    ("Removed role", "moderation.role.removed"),
    ("do not have permission to remove", "moderation.role.remove_no_permission"),
    ("Invalid time unit.", "moderation.mute.invalid_unit"),
    ("is already muted.", "moderation.mute.already"),
    ("has been muted", "moderation.mute.success"),
    ("has been unmuted", "moderation.mute.unmuted"),
    ("Created and set mute role", "moderation.mute.role_created"),
    ("Mute role updated", "moderation.mute.role_updated"),
    ("has been hardmuted", "moderation.hardmute.success"),
    ("Missing permission to manage roles.", "moderation.role.missing_permission"),

    # Tickets
    ("Ticket system set up!", "tickets.setup.success"),
    ("This can only be used in a server.", "tickets.error.not_in_guild"),
    ("Ticket system not configured", "tickets.error.not_configured"),
    ("Failed to create ticket channel", "tickets.create.error"),
    ("ticket created", "tickets.create.success"),
    ("Ticket not found.", "tickets.not_found"),
    ("This ticket is already claimed.", "tickets.claim.already_claimed"),
    ("Ticket claimed by", "tickets.claim.success"),
    ("Ticket locked.", "tickets.locked"),
    ("Ticket unlocked.", "tickets.unlocked"),
    ("Ticket closed.", "tickets.closed"),
    ("Deleting channel in 5 seconds", "tickets.delete.countdown"),

    # Logging
    ("Choose a log channel", "logging.menu.choose_channel"),
    ("will now log to", "logging.channel.set"),
    ("Logging for", "logging.state.changed"),
    ("Choose log channels", "logging.menu.main"),

    # Fun commands
    ("has bet", "fun.betting.start"),
    ("coin landed", "fun.coinflip.result"),
    ("You are already married.", "fun.marry.already_you"),
    ("is already married.", "fun.marry.already_target"),
    ("are now married", "fun.marry.success"),
    ("gives", "fun.hug"),
    ("kissed", "fun.kiss"),
    ("Love compatibility", "fun.lovecalc.result"),
    ("Invalid event type", "fun.autorole.invalid_event"),
    ("Invalid action", "fun.autorole.invalid_action"),
    ("Autorole set to", "fun.autorole.success"),
    ("Click the button", "verification.color.start"),

    # Poll
    ("Choose a channel to send the poll", "poll.create.choose_channel"),

    # Warnings
    ("has been warned.", "moderation.warn.success"),
    ("has no warnings.", "moderation.warn.none"),
    ("Invalid warning index.", "moderation.warn.invalid_index"),

    # Verification
    ("You’ve been verified!", "verification.finished"),
    ("Press the button below to verify yourself:", "verification.button.start"),
    ("Verification successful!", "verification.success"),
    ("verified via **Code Method**", "verification.code.logged"),
    ("Incorrect code.", "verification.code.incorrect"),
    ("I can’t DM you the code", "verification.code.dm_failed"),
    ("Check your DMs for the 4-digit code", "verification.code.sent"),
    ("isn't your verification session", "verification.session.invalid"),
    ("Correct! You’ve been verified.", "verification.success"),
    ("Incorrect color.", "verification.color.incorrect"),
    ("I’ve sent you a DM", "verification.color.dm_sent"),
    ("Verification not set up", "verification.not_configured"),
    ("You’re already verified!", "verification.already_verified"),
    ("Invalid verification method.", "verification.invalid_method"),
    ("I couldn’t send the message in", "verification.send_failed"),
    ("I don’t have permission to change my nickname.", "verification.nickname.no_permission"),
    ("Nickname changed to", "verification.nickname.success"),
    ("Failed to change nickname", "verification.nickname.error"),

    # XP / Leveling
    ("Invalid image URL.", "xp.background.invalid_url"),
    ("Background updated successfully", "xp.background.updated"),
    ("Failed to download background", "xp.background.download_failed"),
    ("Error loading background", "xp.background.load_error"),
    ("Could not open background", "xp.background.open_error"),
    ("Set", "xp.set.success"),
    ("Added reward for level", "xp.rewards.added"),
    ("No rewards configured yet", "xp.rewards.none"),

    # Staff Apps
    ("Toggled staff applications!", "applications.toggle"),
    ("Added question:", "applications.questions.added"),
    ("No questions set.", "applications.questions.none"),
    ("Select question to delete:", "applications.questions.select_delete"),
    ("Staff-application system configured.", "applications.configured"),
    ("Staff applications are not enabled", "applications.not_enabled"),
    ("No application questions have been set up yet.", "applications.questions.empty"),
    ("You will be asked", "applications.dm.start"),
    ("I can’t DM you.", "applications.dm.failed"),
    ("Check your DMs", "applications.dm.sent"),

    # Roast
    ("You're as bright as a black hole", "fun.roast.pick"),

    # Calls
    ("Call created:", "calls.create.success"),
    ("This call does not exist", "calls.error.not_found"),
    ("Incorrect password.", "calls.error.bad_password"),
    ("You aren’t the host", "calls.error.not_host"),
    ("Call channel no longer exists.", "calls.error.channel_missing"),
    ("Sent call invite", "calls.invite.sent"),
    ("Removed", "calls.kick.success"),
    ("Call ended.", "calls.end"),
    ("isn’t in the call.", "calls.error.not_in_call"),
    ("is now the call host", "calls.host.transfer"),
]

# -----------------------------
# MAIN REWRITER
# -----------------------------
def rewrite_bot():
    if not os.path.exists(BOT_FILE):
        print(f"ERROR: {BOT_FILE} does not exist.")
        return

    print("Reading bot.py…")
    with open(BOT_FILE, "r", encoding="utf8") as f:
        code = f.read()

    original_code = code

    print("\nDeleting unwanted strings…")
    for text in DELETE_STRINGS:
        if text in code:
            print(f" - Removed: {text}")
        code = code.replace(text, "")

    print("\nApplying replacements…")
    for old, new in REPLACEMENTS:
        if old in code:
            print(f" - Replaced: {old} → {new}")
        code = code.replace(old, new)

    if code == original_code:
        print("\nNo changes were made.")
    else:
        print("\nSaving changes to bot.py…")
        with open(BOT_FILE, "w", encoding="utf8") as f:
            f.write(code)

        print("Done! bot.py updated successfully.")

# -----------------------------
# RUN
# -----------------------------
if __name__ == "__main__":
    rewrite_bot()
