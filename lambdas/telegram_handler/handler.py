import os
import json
import logging
from datetime import datetime

import boto3
import requests
from dotenv import load_dotenv

# Configurar logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Cargar .env si estamos en local
load_dotenv()


# ════════════════════════════════════════
# CONFIGURACIÓN
# ════════════════════════════════════════

def get_config():
    """Lee configuración según entorno."""
    environment = os.getenv("ENVIRONMENT", "aws")

    if environment == "local":
        return {
            "telegram_token": os.getenv("TELEGRAM_TOKEN"),
            "telegram_chat_id": os.getenv("TELEGRAM_CHAT_ID"),
            "s3_bucket": os.getenv("S3_BUCKET"),
            "aws_region": os.getenv("AWS_REGION", "eu-west-1")
        }
    else:
        ssm = boto3.client("ssm", region_name="eu-west-1")
        params = ssm.get_parameters(
            Names=[
                "/trading-bot/telegram-token",
                "/trading-bot/telegram-chat-id"
            ],
            WithDecryption=True
        )
        config = {}
        for param in params["Parameters"]:
            name = param["Name"].split("/")[-1]
            config[name.replace("-", "_")] = param["Value"]

        config["s3_bucket"] = os.getenv("S3_BUCKET", "trading-system-data")
        config["aws_region"] = "eu-west-1"
        return config


# ════════════════════════════════════════
# S3 HELPERS
# ════════════════════════════════════════

def load_s3_json(s3_client, bucket, key, default=None):
    """Carga JSON desde S3. Retorna default si no existe."""
    try:
        response = s3_client.get_object(Bucket=bucket, Key=key)
        return json.loads(response["Body"].read().decode("utf-8"))
    except:
        return default if default is not None else {}


def save_s3_json(s3_client, bucket, key, data):
    """Guarda JSON en S3."""
    try:
        s3_client.put_object(
            Bucket=bucket,
            Key=key,
            Body=json.dumps(data, indent=2, ensure_ascii=False),
            ContentType="application/json"
        )
        logger.info(f"✅ Guardado S3: {key}")
        return True
    except Exception as e:
        logger.error(f"❌ Error guardando S3 {key}: {e}")
        return False


def load_s3_text(s3_client, bucket, key):
    """Carga texto desde S3."""
    try:
        response = s3_client.get_object(Bucket=bucket, Key=key)
        return response["Body"].read().decode("utf-8")
    except:
        return ""


def save_s3_text(s3_client, bucket, key, text):
    """Guarda texto en S3."""
    try:
        s3_client.put_object(
            Bucket=bucket,
            Key=key,
            Body=text.encode("utf-8"),
            ContentType="text/plain"
        )
        return True
    except Exception as e:
        logger.error(f"❌ Error guardando texto S3: {e}")
        return False


# ════════════════════════════════════════
# TELEGRAM HELPERS
# ════════════════════════════════════════

def send_telegram(message_text, config):
    """Envía mensaje via Telegram."""
    token = config["telegram_token"]
    chat_id = config["telegram_chat_id"]
    url = f"https://api.telegram.org/bot{token}/sendMessage"

    try:
        response = requests.post(url, json={
            "chat_id": chat_id,
            "text": message_text
        })
        if response.status_code == 200:
            logger.info("✅ Telegram mensaje enviado")
        else:
            logger.error(f"❌ Error Telegram: {response.text}")
    except Exception as e:
        logger.error(f"❌ Error enviando Telegram: {e}")

# ════════════════════════════════════════
# COMANDOS
# ════════════════════════════════════════

def cmd_help():
    """Retorna mensaje de ayuda con todos los comandos."""
    return """
🤖 TRADING ASSISTANT - COMANDOS DISPONIBLES

💰 OPERACIONES

/compro TICKER CANTIDAD PRECIO(€)
  Registra una compra
  Ej: /compro AAPL 2 180.50

/vendo TICKER CANTIDAD PRECIO(€)
  Registra una venta
  Ej: /vendo AAPL 2 195.00

📊 CONSULTAS

/portfolio
  Muestra posiciones actuales y P&L

/balance
  Resumen financiero total

/stats
  Estadísticas: win rate, mejor/peor trade

🔧 CONFIGURACIÓN

/blacklist TICKER
  Marca ticker como no disponible en TR
  Ej: /blacklist PLTR

/remove_blacklist TICKER
  Elimina ticker de la blacklist
  Ej: /remove_blacklist PLTR

/blacklists
  Muestra tickers bloqueados en TR

/tip TICKER RAZÓN
  Añade recomendación externa para análisis
  Ej: /tip NVDA Amigo dice que presentan GPU

/remove_tip TICKER
  Elimina tip externo
  Ej: /remove_tip NVDA

/tips
  Muestra tips externos activos

⚡ ACCIONES

/run
  Lanza análisis manual ahora mismo

/help
  Muestra este mensaje
"""


def cmd_compro(parts, s3, config):
    """Registra una compra en el portfolio."""
    if len(parts) != 4:
        return "❌ Formato incorrecto\nUso: /compro TICKER CANTIDAD PRECIO\nEj: /compro AAPL 2 180.50"

    ticker = parts[1].upper()
    try:
        quantity = float(parts[2])
        price = float(parts[3])
    except ValueError:
        return "❌ Cantidad y precio deben ser números\nEj: /compro AAPL 2 180.50"

    bucket = config["s3_bucket"]
    portfolio = load_s3_json(s3, bucket, "portfolio/current_positions.json",
                             default={"positions": [], "cash_eur": 2300})

    # Verificar si ya existe posición en ese ticker
    existing = next((p for p in portfolio["positions"] if p["ticker"] == ticker), None)

    if existing:
        # Calcular precio medio ponderado
        total_qty = existing["quantity"] + quantity
        avg_price = ((existing["quantity"] * existing["entry_price"]) + (quantity * price)) / total_qty
        existing["quantity"] = total_qty
        existing["entry_price"] = round(avg_price, 2)
        existing["last_updated"] = datetime.now().isoformat()
        msg = f"✅ Posición ampliada\n{ticker}: {total_qty} acc @ {round(avg_price, 2)}€ (precio medio)"
    else:
        # Nueva posición
        portfolio["positions"].append({
            "ticker": ticker,
            "quantity": quantity,
            "entry_price": price,
            "date_open": datetime.now().strftime("%Y-%m-%d"),
            "last_updated": datetime.now().isoformat()
        })
        msg = f"✅ Compra registrada\n{ticker}: {quantity} acc @ {price}€"

    # Actualizar efectivo
    cost = quantity * price + 1  # +1€ comisión TR
    portfolio["cash_eur"] = round(portfolio.get("cash_eur", 0) - cost, 2)
    portfolio["last_updated"] = datetime.now().isoformat()

    save_s3_json(s3, bucket, "portfolio/current_positions.json", portfolio)

    msg += f"\nEfectivo restante: {portfolio['cash_eur']}€"
    return msg


def cmd_vendo(parts, s3, config):
    """Registra una venta y calcula P&L."""
    if len(parts) != 4:
        return "❌ Formato incorrecto\nUso: /vendo TICKER CANTIDAD PRECIO\nEj: /vendo AAPL 2 195.00"

    ticker = parts[1].upper()
    try:
        quantity = float(parts[2])
        price = float(parts[3])
    except ValueError:
        return "❌ Cantidad y precio deben ser números"

    bucket = config["s3_bucket"]
    portfolio = load_s3_json(s3, bucket, "portfolio/current_positions.json",
                             default={"positions": [], "cash_eur": 2300})

    # Buscar posición
    position = next((p for p in portfolio["positions"] if p["ticker"] == ticker), None)

    if not position:
        return f"❌ No tienes {ticker} en portfolio"

    if quantity > position["quantity"]:
        return f"❌ Solo tienes {position['quantity']} acciones de {ticker}"

    # Calcular P&L
    entry_price = position["entry_price"]
    gross_pnl = (price - entry_price) * quantity
    costs = 2  # 2€ comisiones (entrada ya pagada + salida)
    net_before_tax = gross_pnl - costs
    tax = max(0, net_before_tax * 0.19)  # Solo si hay ganancia
    net_pnl = round(net_before_tax - tax, 2)
    pnl_pct = round(((price - entry_price) / entry_price) * 100, 2)

    # Actualizar portfolio
    if quantity == position["quantity"]:
        portfolio["positions"].remove(position)
        status = "cerrada"
    else:
        position["quantity"] = round(position["quantity"] - quantity, 4)
        position["last_updated"] = datetime.now().isoformat()
        status = "parcial"

    # Actualizar efectivo
    proceeds = quantity * price - 1  # -1€ comisión TR
    portfolio["cash_eur"] = round(portfolio.get("cash_eur", 0) + proceeds, 2)
    portfolio["last_updated"] = datetime.now().isoformat()

    save_s3_json(s3, bucket, "portfolio/current_positions.json", portfolio)

    # Guardar en historial
    trade = {
        "ticker": ticker,
        "quantity": quantity,
        "entry_price": entry_price,
        "exit_price": price,
        "date_close": datetime.now().strftime("%Y-%m-%d"),
        "gross_pnl": round(gross_pnl, 2),
        "net_pnl": net_pnl,
        "pnl_pct": pnl_pct,
        "result": "win" if net_pnl > 0 else "loss"
    }

    # Añadir a operations_full.csv
    save_trade_to_history(s3, bucket, trade)

    emoji = "📈" if net_pnl > 0 else "📉"

    return f"""{emoji} Venta registrada ({status})
{ticker}: {quantity} acc @ {price}€

Entrada: {entry_price}€
Salida: {price}€
P&L bruto: {round(gross_pnl, 2)}€ ({pnl_pct:+}%)
Costes: -{costs}€
Impuestos (19%): -{round(tax, 2)}€
P&L NETO: {net_pnl}€

Efectivo: {portfolio['cash_eur']}€"""


def save_trade_to_history(s3, bucket, trade):
    """Añade trade al historial CSV."""
    try:
        existing = load_s3_text(s3, bucket, "history/operations_full.csv")

        if not existing:
            header = "ticker,quantity,entry_price,exit_price,date_close,gross_pnl,net_pnl,pnl_pct,result\n"
            existing = header

        row = f"{trade['ticker']},{trade['quantity']},{trade['entry_price']},{trade['exit_price']},{trade['date_close']},{trade['gross_pnl']},{trade['net_pnl']},{trade['pnl_pct']},{trade['result']}\n"
        save_s3_text(s3, bucket, "history/operations_full.csv", existing + row)

    except Exception as e:
        logger.error(f"❌ Error guardando historial: {e}")


def cmd_portfolio(s3, config):
    """Muestra posiciones actuales."""
    bucket = config["s3_bucket"]
    portfolio = load_s3_json(s3, bucket, "portfolio/current_positions.json",
                             default={"positions": [], "cash_eur": 2300})

    positions = portfolio.get("positions", [])

    if not positions:
        return f"💼 PORTFOLIO\n\nSin posiciones abiertas\nEfectivo: {portfolio.get('cash_eur', 0)}€"

    msg = "💼 PORTFOLIO\n\n"
    total_invested = 0

    for p in positions:
        invested = p["quantity"] * p["entry_price"]
        total_invested += invested
        msg += f"{p['ticker']}: {p['quantity']} acc @ {p['entry_price']}€\n"
        msg += f"Invertido: {round(invested, 2)}€\n"
        msg += f"Desde: {p.get('date_open', 'N/A')}\n\n"

    msg += f"Total invertido: {round(total_invested, 2)}€\n"
    msg += f"Efectivo: {portfolio.get('cash_eur', 0)}€\n"
    msg += f"Total portfolio: {round(total_invested + portfolio.get('cash_eur', 0), 2)}€"

    return msg


def cmd_balance(s3, config):
    """Muestra resumen financiero total."""
    bucket = config["s3_bucket"]
    portfolio = load_s3_json(s3, bucket, "portfolio/current_positions.json",
                             default={"positions": [], "cash_eur": 2300})

    # Leer historial para calcular P&L total
    csv_text = load_s3_text(s3, bucket, "history/operations_full.csv")

    total_net_pnl = 0
    total_trades = 0
    wins = 0

    if csv_text:
        lines = csv_text.strip().split("\n")[1:]  # Skip header
        for line in lines:
            if line:
                parts = line.split(",")
                try:
                    net_pnl = float(parts[6])
                    result = parts[8]
                    total_net_pnl += net_pnl
                    total_trades += 1
                    if result == "win":
                        wins += 1
                except:
                    pass

    cash = portfolio.get("cash_eur", 0)
    invested = sum(p["quantity"] * p["entry_price"] for p in portfolio.get("positions", []))
    total_value = cash + invested

    win_rate = round((wins / total_trades * 100), 1) if total_trades > 0 else 0

    return f"""💰 BALANCE

Capital actual: {round(total_value, 2)}€
  Efectivo: {cash}€
  Invertido: {round(invested, 2)}€

P&L realizado: {round(total_net_pnl, 2)}€
Operaciones cerradas: {total_trades}
Win rate: {win_rate}%"""


def cmd_stats(s3, config):
    """Muestra estadísticas detalladas."""
    bucket = config["s3_bucket"]
    csv_text = load_s3_text(s3, bucket, "history/operations_full.csv")

    if not csv_text or len(csv_text.strip().split("\n")) <= 1:
        return "📊 STATS\n\nSin operaciones cerradas aún.\nLas estadísticas aparecerán tras tu primera venta."

    lines = csv_text.strip().split("\n")[1:]
    trades = []

    for line in lines:
        if line:
            parts = line.split(",")
            try:
                trades.append({
                    "ticker": parts[0],
                    "net_pnl": float(parts[6]),
                    "pnl_pct": float(parts[7]),
                    "result": parts[8]
                })
            except:
                pass

    if not trades:
        return "📊 STATS\n\nSin datos suficientes."

    wins = [t for t in trades if t["result"] == "win"]
    losses = [t for t in trades if t["result"] == "loss"]
    win_rate = round(len(wins) / len(trades) * 100, 1)

    best = max(trades, key=lambda x: x["net_pnl"])
    worst = min(trades, key=lambda x: x["net_pnl"])

    total_pnl = sum(t["net_pnl"] for t in trades)

    return f"""📊 STATS

Total operaciones: {len(trades)}
Win rate: {win_rate}% ({len(wins)}W / {len(losses)}L)
P&L total neto: {round(total_pnl, 2)}€

Mejor trade: {best['ticker']} +{best['net_pnl']}€ ({best['pnl_pct']:+}%)
Peor trade: {worst['ticker']} {worst['net_pnl']}€ ({worst['pnl_pct']:+}%)"""


def cmd_blacklist(parts, s3, config, remove=False):
    """Añade o elimina ticker de blacklist."""
    if len(parts) != 2:
        action = "remove_blacklist" if remove else "blacklist"
        return f"❌ Formato incorrecto\nUso: /{action} TICKER\nEj: /{action} PLTR"

    ticker = parts[1].upper()
    bucket = config["s3_bucket"]

    current = load_s3_text(s3, bucket, "external/tickers_blacklist.txt")
    tickers = [t.strip() for t in current.split("\n") if t.strip()]

    if remove:
        if ticker not in tickers:
            return f"❌ {ticker} no está en la blacklist"
        tickers.remove(ticker)
        save_s3_text(s3, bucket, "external/tickers_blacklist.txt", "\n".join(tickers))
        return f"✅ {ticker} eliminado de blacklist\nClaud puede volver a recomendarlo"
    else:
        if ticker in tickers:
            return f"⚠️ {ticker} ya está en blacklist"
        tickers.append(ticker)
        save_s3_text(s3, bucket, "external/tickers_blacklist.txt", "\n".join(tickers))
        return f"✅ {ticker} añadido a blacklist\nNo se recomendará en futuros análisis"
    
def cmd_blacklists(s3, config):
    """Muestra tickers en blacklist."""
    bucket = config["s3_bucket"]
    current = load_s3_text(s3, bucket, "external/tickers_blacklist.txt")
    tickers = [t.strip() for t in current.split("\n") if t.strip()]

    if not tickers:
        return "🚫 BLACKLIST\n\nSin tickers bloqueados."

    return "🚫 BLACKLIST\n\n" + "\n".join(tickers)

def cmd_tip(parts, s3, config, remove=False):
    """Añade o elimina tip externo."""
    bucket = config["s3_bucket"]
    tips = load_s3_json(s3, bucket, "external/user_tips.json", default=[])

    if remove:
        if len(parts) != 2:
            return "❌ Formato incorrecto\nUso: /remove_tip TICKER"
        ticker = parts[1].upper()
        original_count = len(tips)
        tips = [t for t in tips if t.get("ticker") != ticker]
        if len(tips) == original_count:
            return f"❌ No hay tip para {ticker}"
        save_s3_json(s3, bucket, "external/user_tips.json", tips)
        return f"✅ Tip de {ticker} eliminado"

    else:
        if len(parts) < 3:
            return "❌ Formato incorrecto\nUso: /tip TICKER RAZÓN\nEj: /tip NVDA Amigo dice que presentan GPU"

        ticker = parts[1].upper()
        reason = " ".join(parts[2:])

        # Actualizar si ya existe
        existing = next((t for t in tips if t.get("ticker") == ticker), None)
        if existing:
            existing["context"] = reason.strip()
            existing["date"] = datetime.now().strftime("%Y-%m-%d")
            msg = f"✅ Tip actualizado\n{ticker}: {reason.strip()}"
        else:
            tips.append({
                "ticker": ticker,
                "context": reason.strip(),
                "date": datetime.now().strftime("%Y-%m-%d"),
                "source": "user"
            })
            msg = f"✅ Tip añadido\n{ticker}: {reason.strip()}\nSe analizará en el próximo análisis"

        save_s3_json(s3, bucket, "external/user_tips.json", tips)
        return msg
    
def cmd_tips(s3, config):
    """Muestra tips externos activos."""
    bucket = config["s3_bucket"]
    tips = load_s3_json(s3, bucket, "external/user_tips.json", default=[])

    if not tips:
        return "💡 TIPS ACTIVOS\n\nSin tips pendientes."

    msg = "💡 TIPS ACTIVOS\n\n"
    for t in tips:
        msg += f"{t['ticker']}: {t['context']}\n"
        msg += f"Añadido: {t.get('date', 'N/A')}\n\n"

    return msg

def cmd_run(config):
    """Lanza análisis manual invocando daily_analysis Lambda."""
    environment = os.getenv("ENVIRONMENT", "aws")

    if environment == "local":
        return "⚠️ /run solo funciona en AWS\nEn local ejecuta: python3 lambdas/daily_analysis/handler.py"

    try:
        lambda_client = boto3.client("lambda", region_name=config["aws_region"])
        lambda_client.invoke(
            FunctionName="daily_analysis",
            InvocationType="Event"  # Asíncrono
        )
        return "⚡ Análisis lanzado\nRecibirás el resultado en unos segundos"
    except Exception as e:
        logger.error(f"❌ Error invocando Lambda: {e}")
        return f"❌ Error lanzando análisis: {e}"


# ════════════════════════════════════════
# PROCESADOR DE COMANDOS
# ════════════════════════════════════════

def process_command(text, s3, config):
    """Parsea y ejecuta el comando recibido."""
    if not text or not text.startswith("/"):
        return None

    parts = text.strip().split()
    command = parts[0].lower()

    logger.info(f"Comando recibido: {command}")

    if command == "/help":
        return cmd_help()

    elif command == "/compro":
        return cmd_compro(parts, s3, config)

    elif command == "/vendo":
        return cmd_vendo(parts, s3, config)

    elif command == "/portfolio":
        return cmd_portfolio(s3, config)

    elif command == "/balance":
        return cmd_balance(s3, config)

    elif command == "/stats":
        return cmd_stats(s3, config)

    elif command == "/blacklist":
        return cmd_blacklist(parts, s3, config, remove=False)

    elif command == "/remove_blacklist":
        return cmd_blacklist(parts, s3, config, remove=True)
    
    elif command == "/blacklists":
        return cmd_blacklists(s3, config)

    elif command == "/tip":
        return cmd_tip(parts, s3, config, remove=False)

    elif command == "/remove_tip":
        return cmd_tip(parts, s3, config, remove=True)
    
    elif command == "/tips":
        return cmd_tips(s3, config)

    elif command == "/run":
        return cmd_run(config)

    else:
        return f"❌ Comando desconocido: {command}\nEscribe /help para ver comandos disponibles"


# ════════════════════════════════════════
# ENTRY POINT
# ════════════════════════════════════════

def lambda_handler(event, context):
    """
    Entry point webhook.
    Telegram llama directamente cuando el usuario escribe.
    """
    logger.info("🤖 Telegram webhook recibido")
    
    try:
        config = get_config()
        s3 = boto3.client("s3", region_name=config["aws_region"])
        
        # Parsear evento de Telegram
        body = json.loads(event.get("body", "{}"))
        message = body.get("message", {})
        text = message.get("text", "")
        
        if not text:
            logger.info("Mensaje sin texto, ignorando")
            return {"statusCode": 200, "body": "OK"}
        
        logger.info(f"Mensaje recibido: {text}")
        
        # Procesar comando
        response = process_command(text, s3, config)
        
        if response:
            send_telegram(response, config)
        
        return {"statusCode": 200, "body": "OK"}
        
    except Exception as e:
        logger.error(f"❌ Error procesando webhook: {e}")
        return {"statusCode": 500, "body": "Error"}


# Para testing local - simula webhook
if __name__ == "__main__":
    # Simula evento de Telegram webhook
    mock_event = {
        "body": json.dumps({
            "message": {
                "text": "/help",
                "chat": {"id": int(os.getenv("TELEGRAM_CHAT_ID", "0"))}
            }
        })
    }
    lambda_handler(mock_event, {})