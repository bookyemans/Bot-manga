# File: main.py
from __future__ import annotations

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from pathlib import Path
from telegram import BotCommand, BotCommandScopeChat, Update
from telegram.ext import Application, ApplicationBuilder
from telegram.constants import ParseMode

from config.bootstrap import configure_logging, load_settings, validate_startup_settings
from shared.database import Database
from shared.event_bus import EventBus
from shared.logger import job_logger
from shared.container import ServiceContainer
from utils.instance_lock import SingleInstanceLock, InstanceAlreadyRunning
from utils.image_optimizer import optimize_image

from systems.access_control.manager import AccessManager
from systems.access_control.api_key_manager import APIKeyManager
from systems.access_control.user_settings import UserSettingsManager

from systems.ai_engine.gemini import GeminiProvider

from systems.translation_pipeline.registry import PersonaRegistry

from systems.job_orchestration.queue import AsyncSingleWorkerQueue
from systems.job_orchestration.worker import JobManager

from systems.delivery.batch import BatchManager
from systems.delivery.renderers.telegram import TelegramRenderer
from systems.delivery.senders.strategies.grouped_session import GroupedSessionStrategy
from systems.delivery.senders.strategies.individual_session import IndividualSessionStrategy
from systems.delivery.notifier import BotErrorNotifier
from systems.delivery.pipeline import DeliveryPipeline

from systems.glossary.manager import GlossaryManager

from systems.delivery.ui.registration import register_handlers

logger = logging.getLogger("manga_bot.main")

async def post_init(app: Application) -> None:
    settings = app.bot_data["settings"]
    bot = app.bot
    
    # Limit ThreadPoolExecutor to prevent CPU thrashing on heavy DOCX generation
    loop = asyncio.get_running_loop()
    loop.set_default_executor(
        ThreadPoolExecutor(
            max_workers=max(1, settings.thread_pool_workers),
            thread_name_prefix="void-bot",
        )
    )
    
    database_path = Path(settings.database_path)
    database_path.parent.mkdir(parents=True, exist_ok=True)
    db = Database(
        db_path=str(database_path),
        busy_timeout_ms=settings.db_busy_timeout_ms,
        cache_size_kib=settings.db_cache_size_kib,
        wal_autocheckpoint_pages=settings.db_wal_autocheckpoint_pages,
    )
    await db.connect()
    event_bus = EventBus()
    
    access_manager = AccessManager(db=db, super_admin_ids=settings.super_admin_ids)
    api_key_manager = APIKeyManager(db=db)
    settings_manager = UserSettingsManager(db=db)
    
    ai_provider = GeminiProvider(
        timeout=settings.ai_timeout_seconds, 
        cb_threshold=settings.cb_failure_threshold, 
        cb_cooldown=settings.cb_cooldown_seconds,
        connector_limit=settings.ai_http_connection_limit,
        models=[model.strip() for model in settings.gemini_models.split(",") if model.strip()],
        max_retries=settings.gemini_max_retries,
        retry_delay_seconds=settings.gemini_retry_delay_seconds,
    )
    
    persona_registry = PersonaRegistry(plugins_dir="systems/translation_pipeline/plugins")
    
    ai_queue = AsyncSingleWorkerQueue(max_size=settings.queue_max_size)
    delivery_queue = AsyncSingleWorkerQueue(max_size=settings.queue_max_size)
    
    job_manager = JobManager(
        ai_queue=ai_queue,
        delivery_queue=delivery_queue,
        post_job_delay=settings.post_job_delay_seconds,
        ai_worker_count=settings.ai_worker_count,
        delivery_worker_count=settings.delivery_worker_count,
    )
    
    batch_manager = BatchManager()
    telegram_renderer = TelegramRenderer(
        batch_size=settings.telegram_send_batch_size,
        batch_delay_seconds=settings.telegram_send_delay_seconds,
    )
    
    grouped_strategy = GroupedSessionStrategy(
        bot=bot, batch=batch_manager, settings=settings_manager,
        personas=persona_registry, queue=ai_queue, renderer=telegram_renderer,
        jobs=job_manager
    )
    
    individual_strategy = IndividualSessionStrategy(
        bot=bot, batch=batch_manager, settings=settings_manager,
        personas=persona_registry, queue=ai_queue, renderer=telegram_renderer,
        jobs=job_manager
    )
    
    error_notifier = BotErrorNotifier(bot=bot)
    glossary_manager = GlossaryManager()
    
    delivery_pipeline = DeliveryPipeline(
        bot=bot,
        ai_provider=ai_provider,
        persona_registry=persona_registry,
        api_key_manager=api_key_manager,
        settings_manager=settings_manager,
        batch_manager=batch_manager,
        grouped_strategy=grouped_strategy,
        individual_strategy=individual_strategy,
        image_optimizer=partial(
            optimize_image,
            max_side=settings.image_max_side,
            max_pixels=settings.image_max_pixels,
        ),
        queue_manager=ai_queue,
        glossary_manager=glossary_manager,
        job_manager=job_manager,
        env_settings=settings,
    )
    
    grouped_strategy.set_pipeline(delivery_pipeline)
    individual_strategy.set_pipeline(delivery_pipeline)
    
    job_manager.attach(
        pipeline=delivery_pipeline,
        error_notifier=error_notifier
    )
    
    container = ServiceContainer(
        db=db, bot=bot, event_bus=event_bus,
        access=access_manager, api_keys=api_key_manager, settings=settings_manager,
        ai=ai_provider, personas=persona_registry,
        queue=ai_queue, jobs=job_manager,
        batch=batch_manager, renderer=telegram_renderer,
        delivery=delivery_pipeline, notifier=error_notifier,
        glossary=glossary_manager
    )
    app.bot_data["container"] = container
    
    public_commands = [
        BotCommand("start", "بدء استخدام البوت"), BotCommand("settings", "فتح الإعدادات"),
        BotCommand("help", "دليل الاستخدام"), BotCommand("start_session", "بدء الجلسة"),
        BotCommand("end_session", "إنهاء الجلسة"), BotCommand("cancel", "إلغاء الجلسة"),
        BotCommand("note", "إضافة ملاحظة للجلسة")
    ]
    await bot.set_my_commands(public_commands)
    
    admin_commands = public_commands + [
        BotCommand("addkey", "➕ إضافة مفتاح API"), BotCommand("listkeys", "📋 عرض مفاتيح API"),
        BotCommand("removekey", "🗑️ حذف مفتاح API"), BotCommand("adduser", "➕ إضافة مستخدم"),
        BotCommand("removeuser", "🗑️ حذف مستخدم"), BotCommand("listusers", "📋 عرض المستخدمين"),
        BotCommand("openrequests", "🟢 فتح باب الانضمام"), BotCommand("closerequests", "🔴 إغلاق باب الانضمام"),
        BotCommand("uploaddict", "📚 رفع قاموس المصطلحات"), BotCommand("downloaddict", "📥 تحميل القاموس"),
    ]
    super_admin_commands = admin_commands + [
        BotCommand("addadmin", "👑 ترقية لمشرف"), BotCommand("removeadmin", "📉 إزالة مشرف")
    ]
    
    admins = await access_manager.get_admins()
    for admin_id in admins:
        try:
            cmds = super_admin_commands if access_manager.is_super_admin(int(admin_id)) else admin_commands
            await bot.set_my_commands(cmds, scope=BotCommandScopeChat(chat_id=int(admin_id)))
        except Exception as e:
            logger.warning(f"Could not set admin commands for {admin_id}: {e}")
            
    await job_manager.start()

async def post_shutdown(app: Application) -> None:
    container = app.bot_data.get("container")
    if container is not None and not isinstance(container, ServiceContainer):
        logger.error("Invalid service container during shutdown; skipping managed cleanup.")
        return
    if not container:
        return
    # Attempt every cleanup step even if one component fails.
    for label, closer in (
        ("job manager", container.jobs.stop),
        ("AI provider", container.ai.close),
        ("database", container.db.close),
    ):
        try:
            await closer()
        except Exception:
            logger.exception("Error while closing %s", label)

def main() -> None:
    settings = load_settings()
    validate_startup_settings(settings)
    configure_logging(settings)

    app = ApplicationBuilder().token(settings.telegram_bot_token).post_init(post_init).post_shutdown(post_shutdown).build()
    app.bot_data["settings"] = settings

    register_handlers(app)

    logger.info("Starting Void Translator...")
    try:
        with SingleInstanceLock(settings.instance_lock_path):
            app.run_polling(allowed_updates=Update.ALL_TYPES)
    except InstanceAlreadyRunning:
        logger.critical("Another bot instance is already running; refusing duplicate polling.")
        raise SystemExit(2)

if __name__ == "__main__":
    main()