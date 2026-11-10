"""Telegram update and command handler registration.

Keep Telegram-specific routing in this module; application bootstrap remains
focused on constructing and starting the application.
"""
from telegram import Update
from telegram.ext import (
    Application, CallbackQueryHandler, CommandHandler, MessageHandler,
    TypeHandler, filters,
)

from systems.access_control.middleware import firewall_middleware
from systems.delivery.ui.middlewares import state_purge_middleware, session_guard_middleware
from systems.delivery.ui.handlers.start import start_command, help_command
from systems.delivery.ui.handlers.settings import settings_command, settings_callback
from systems.delivery.ui.handlers.session import (
    start_session_command, end_session_command, cancel_command, receive_session_filename,
    set_note_command, handle_skip_filename, handle_cancel_session, handle_cleanup_photos_callback,
    handle_add_note_prompt, handle_cancel_note_prompt, handle_end_session_callback,
    handle_cancel_session_callback,
)
from systems.delivery.ui.handlers.admin import (
    add_public_key_command, list_public_keys_command, remove_public_key_command,
    upload_dict_command, download_dict_command, handle_apikey_callback, handle_admin_cancel,
)
from systems.delivery.ui.handlers.access import (
    add_user_command, remove_user_command, add_admin_command, remove_admin_command,
    list_users_command, open_requests_command, close_requests_command,
    handle_request_callback, handle_access_callback,
)
from systems.delivery.ui.handlers.messages import handle_image, handle_text, handle_document


def register_handlers(app: Application) -> None:
    """Register middleware, commands, callbacks, and message routes."""
    app.add_handler(TypeHandler(Update, firewall_middleware), group=-3)
    app.add_handler(TypeHandler(Update, state_purge_middleware), group=-2)
    app.add_handler(TypeHandler(Update, session_guard_middleware), group=-1)

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("settings", settings_command))
    app.add_handler(CommandHandler("start_session", start_session_command))
    app.add_handler(CommandHandler("end_session", end_session_command))
    app.add_handler(CommandHandler("cancel", cancel_command))
    app.add_handler(CommandHandler("note", set_note_command))

    app.add_handler(CommandHandler("addkey", add_public_key_command))
    app.add_handler(CommandHandler("listkeys", list_public_keys_command))
    app.add_handler(CommandHandler("removekey", remove_public_key_command))
    app.add_handler(CommandHandler("uploaddict", upload_dict_command))
    app.add_handler(CommandHandler("downloaddict", download_dict_command))

    app.add_handler(CommandHandler("adduser", add_user_command))
    app.add_handler(CommandHandler("removeuser", remove_user_command))
    app.add_handler(CommandHandler("listusers", list_users_command))
    app.add_handler(CommandHandler("openrequests", open_requests_command))
    app.add_handler(CommandHandler("closerequests", close_requests_command))
    app.add_handler(CommandHandler("addadmin", add_admin_command))
    app.add_handler(CommandHandler("removeadmin", remove_admin_command))

    app.add_handler(MessageHandler(filters.Regex("⚙️ الإعدادات"), settings_command))
    app.add_handler(MessageHandler(filters.Regex("📖 المساعدة"), help_command))
    app.add_handler(MessageHandler(filters.Regex("🟢 بدء الجلسة"), start_session_command))
    app.add_handler(MessageHandler(filters.Regex("🔴 إنهاء الجلسة"), end_session_command))

    app.add_handler(CallbackQueryHandler(settings_callback, pattern="^(open_|set_|back_|toggle_|add_|del_)"))
    app.add_handler(CallbackQueryHandler(handle_access_callback, pattern="^adm_(sel|conf|nav)_access_"))
    app.add_handler(CallbackQueryHandler(handle_apikey_callback, pattern="^adm_(sel|conf|nav)_apikey_"))
    app.add_handler(CallbackQueryHandler(handle_skip_filename, pattern="^skip_filename$"))
    app.add_handler(CallbackQueryHandler(handle_cancel_session, pattern="^cancel_session$"))
    app.add_handler(CallbackQueryHandler(handle_cleanup_photos_callback, pattern="^cleanup_photos$"))
    app.add_handler(CallbackQueryHandler(handle_admin_cancel, pattern="^adm_cancel$"))
    app.add_handler(CallbackQueryHandler(handle_request_callback, pattern="^(accept_req|reject_req)"))
    app.add_handler(CallbackQueryHandler(handle_add_note_prompt, pattern="^session_add_note$"))
    app.add_handler(CallbackQueryHandler(handle_cancel_note_prompt, pattern="^cancel_note_prompt$"))
    app.add_handler(CallbackQueryHandler(handle_end_session_callback, pattern="^end_session_inline$"))
    app.add_handler(CallbackQueryHandler(handle_cancel_session_callback, pattern="^cancel_session_inline$"))

    app.add_handler(MessageHandler(filters.Document.TEXT, handle_document))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.PHOTO | filters.Document.IMAGE, handle_image))
