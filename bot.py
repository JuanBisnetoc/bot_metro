from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    filters, ContextTypes, ConversationHandler, CallbackContext
)

import logging
from config import TELEGRAM_TOKEN, CHAT_ID
from database import (
    criar_tabelas,
    obter_linhas_com_problema,
    obter_status_resumido,
    obter_todas_linhas,
    adicionar_usuario,
    remover_usuario,
    usuario_inscrito,
    obter_todos_usuarios,
)
from scraper_oficial import atualizar_status_real

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MENU_PRINCIPAL = 1

BTN_STATUS    = "📊 Status Geral"
BTN_PROBLEMAS = "🚨 Problemas Detectados"
BTN_LINHAS    = "🚇 Todas as Linhas"
BTN_ATUALIZAR = "🔄 Atualizar Dados"
BTN_ASSINAR   = "🔔 Ativar Notificações"
BTN_CANCELAR  = "🔕 Desativar Notificações"
BTN_SAIR      = "❌ Sair"


def _teclado(chat_id: int) -> ReplyKeyboardMarkup:
    inscrito = usuario_inscrito(chat_id)
    btn_notif = BTN_CANCELAR if inscrito else BTN_ASSINAR
    keyboard = [
        [KeyboardButton(BTN_STATUS)],
        [KeyboardButton(BTN_PROBLEMAS)],
        [KeyboardButton(BTN_LINHAS)],
        [KeyboardButton(BTN_ATUALIZAR)],
        [KeyboardButton(btn_notif)],
        [KeyboardButton(BTN_SAIR)],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    await update.message.reply_text(
        "🚇 *Bem-vindo/a ao Monitor Metro/Trem SP!*\n\n"
        "Acompanhe o status das linhas de Metrô, CPTM e ViaMobilidade em tempo real.\n\n"
        "Escolha uma opção:",
        reply_markup=_teclado(chat_id),
        parse_mode="Markdown",
    )
    return MENU_PRINCIPAL


async def handle_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text
    chat_id = update.effective_chat.id

    if BTN_STATUS in texto:
        status = obter_status_resumido()
        if status:
            msg = (
                f"📊 *Status Geral do Sistema*\n\n"
                f"✅ Normais: {status['normais']}\n"
                f"🟡 Em atenção: {status['atencao']}\n"
                f"🔴 Paradas: {status['paradas']}\n"
                f"📈 Total de linhas: {status['total']}"
            )
        else:
            msg = "❌ Não foi possível obter o status geral no momento."
        await update.message.reply_text(msg, parse_mode="Markdown")

    elif BTN_PROBLEMAS in texto:
        linhas = obter_linhas_com_problema()
        if linhas:
            msg = "🚨 *Linhas com Problemas:*\n\n"
            for linha in linhas:
                emoji = "🟡" if linha["status"] == "atencao" else "🔴"
                msg += f"{emoji} {linha['nome']} ({linha['operadora']})\n"
                if linha["descricao_problema"]:
                    msg += f"   {linha['descricao_problema']}\n"
                msg += "\n"
        else:
            msg = "✅ Nenhum problema detectado! Todas as linhas operando normalmente."
        await update.message.reply_text(msg, parse_mode="Markdown")

    elif BTN_LINHAS in texto:
        linhas = obter_todas_linhas()
        if linhas:
            msg = "🚇 *Status de Todas as Linhas:*\n\n"
            for linha in linhas:
                emoji = {"normal": "✅", "atencao": "🟡", "parada": "🔴"}.get(linha["status"], "❓")
                msg += f"{emoji} {linha['nome']} ({linha['operadora']})\n"
        else:
            msg = "❌ Não foi possível obter o status das linhas no momento."
        await update.message.reply_text(msg, parse_mode="Markdown")

    elif BTN_ATUALIZAR in texto:
        await update.message.reply_text("⏳ Atualizando dados... Isso pode levar alguns segundos.")
        atualizar_status_real()
        await update.message.reply_text("✅ Dados atualizados com sucesso!", reply_markup=_teclado(chat_id))

    elif BTN_ASSINAR in texto:
        adicionar_usuario(chat_id)
        await update.message.reply_text(
            "🔔 Notificações ativadas! Você receberá atualizações a cada 2 horas.",
            reply_markup=_teclado(chat_id),
        )

    elif BTN_CANCELAR in texto:
        remover_usuario(chat_id)
        await update.message.reply_text(
            "🔕 Notificações desativadas.",
            reply_markup=_teclado(chat_id),
        )

    elif BTN_SAIR in texto:
        await update.message.reply_text("👋 Até a próxima!")
        return ConversationHandler.END

    return MENU_PRINCIPAL


def _montar_mensagem_status() -> str:
    """Monta mensagem de status para notificação periódica."""
    linhas_problema = obter_linhas_com_problema()
    if not linhas_problema:
        return "✅ *Atualização Metro/Trem SP*\n\nTodas as linhas estão operando normalmente."

    msg = "🚨 *Atualização Metro/Trem SP — Problemas Detectados:*\n\n"
    for linha in linhas_problema:
        emoji = "🟡" if linha["status"] == "atencao" else "🔴"
        msg += f"{emoji} {linha['nome']} ({linha['operadora']})\n"
        if linha["descricao_problema"]:
            msg += f"   └─ {linha['descricao_problema']}\n"
    return msg


async def notificacao_periodica(context: CallbackContext):
    """Atualiza dados e envia status a todos os usuários inscritos a cada 2 horas."""
    atualizar_status_real()
    mensagem = _montar_mensagem_status()
    usuarios = obter_todos_usuarios()

    for chat_id in usuarios:
        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text=mensagem,
                parse_mode="Markdown",
            )
        except Exception as e:
            logger.warning(f"Falha ao notificar {chat_id}: {e}")


async def error_handler(_update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Erro: {context.error}")


async def on_startup(app: Application):
    usuarios = obter_todos_usuarios()
    for chat_id in usuarios:
        try:
            await app.bot.send_message(
                chat_id=chat_id,
                text="🟢 *Bot iniciado!*\nO Monitor Metro/Trem SP está online e monitorando as linhas.\nPara Consultar o status das linhas, use o comando /start",
                parse_mode="Markdown",
            )
        except Exception as e:
            logger.warning(f"Falha ao notificar {chat_id} na inicialização: {e}")


async def manutencao(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_chat.id) != str(CHAT_ID):
        return


              ##MENSAGEM DE MANUTENÇÃO##
              ##MANDAR MENSAGEM DE MANUTENÇÃO PARA TODOS OS USUARIOS##
              ##/manutencao (comando para aviasr usuarios que está em manutenção)
    texto = " ".join(context.args) if context.args else "O bot estará temporariamente offline para manutenção. Voltaremos em breve."
    mensagem = f"🔴 *Aviso de Manutenção*\n\n{texto}"

    usuarios = obter_todos_usuarios()
    enviados = 0
    for cid in usuarios:
        try:
            await context.bot.send_message(chat_id=cid, text=mensagem, parse_mode="Markdown")
            enviados += 1
        except Exception as e:
            logger.warning(f"Falha ao notificar {cid}: {e}")

    await update.message.reply_text(f"✅ Mensagem enviada para {enviados} usuário(s).")


def main():
    criar_tabelas()
    atualizar_status_real()

    app = Application.builder().token(TELEGRAM_TOKEN).post_init(on_startup).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            MENU_PRINCIPAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_menu)]
        },
        fallbacks=[CommandHandler("start", start)],
    )

    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("manutencao", manutencao))
    app.add_error_handler(error_handler)

    # Notificação a cada 2 horas; primeira disparo após 10 minutos
    app.job_queue.run_repeating(notificacao_periodica, interval=7200, first=600)

    print("🤖 Bot iniciado!")
    app.run_polling()


if __name__ == "__main__":
    main()
