import os
import json
import logging
from datetime import datetime
import time

import anthropic
import yfinance as yf
import boto3
import requests
from dotenv import load_dotenv

# Configurar logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Cargar .env si estamos en local
load_dotenv()

def get_config():
    """
    Lee configuración según entorno.
    Local: desde .env
    AWS Lambda: desde Parameter Store
    """
    environment = os.getenv("ENVIRONMENT", "aws")
    
    if environment == "local":
        logger.info("Entorno LOCAL - leyendo .env")
        return {
            "claude_api_key": os.getenv("CLAUDE_API_KEY"),
            "telegram_token": os.getenv("TELEGRAM_TOKEN"),
            "telegram_chat_id": os.getenv("TELEGRAM_CHAT_ID"),
            "s3_bucket": os.getenv("S3_BUCKET"),
            "aws_region": os.getenv("AWS_REGION", "eu-west-1"),
            "mock_claude": os.getenv("MOCK_CLAUDE", "false")
        }
    
    else:
        logger.info("Entorno AWS - leyendo Parameter Store")
        ssm = boto3.client("ssm", region_name="eu-west-1")
        
        params = ssm.get_parameters(
            Names=[
                "/trading-bot/claude-api-key",
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
    
def load_portfolio(config):
    """
    Carga portfolio actual y historial desde S3 o archivos locales.
    """
    environment = os.getenv("ENVIRONMENT", "aws")
    
    if environment == "local":
        logger.info("Cargando portfolio desde archivos locales")
        
        # Portfolio mock para testing
        portfolio = {
            "positions": [],
            "cash_eur": 2300,
            "last_updated": datetime.now().isoformat()
        }
        
        last_trades = []
        patterns = {}
        blacklist = []
        rules = load_rules_local()
        external_tips = []
        
    else:
        s3 = boto3.client("s3", region_name=config["aws_region"])
        bucket = config["s3_bucket"]
        
        # Portfolio actual
        portfolio = load_s3_json(s3, bucket, "portfolio/current_positions.json")
        
        # Historial últimas 10 operaciones
        last_trades = load_s3_json(s3, bucket, "history/last_30_trades.json")
        
        # Patterns aprendidos
        patterns = load_s3_json(s3, bucket, "learning/patterns_learned.json")
        
        # Tickers blacklist
        blacklist_raw = load_s3_text(s3, bucket, "external/tickers_blacklist.txt")
        blacklist = [t.strip() for t in blacklist_raw.split("\n") if t.strip()]
        
        # Reglas trading
        rules = load_s3_json(s3, bucket, "config/rules.json")
        
        # Tips externos (Zumitow + amigos)
        external_tips = load_s3_json(s3, bucket, "external/user_tips.json")
    
    return portfolio, last_trades, patterns, blacklist, rules, external_tips


def load_rules_local():
    """Carga reglas desde archivo ejemplo para testing local."""
    rules_path = "config/rules.json.example"
    with open(rules_path, "r") as f:
        return json.load(f)


def load_s3_json(s3_client, bucket, key):
    """Carga y parsea JSON desde S3. Retorna dict vacío si no existe."""
    try:
        response = s3_client.get_object(Bucket=bucket, Key=key)
        return json.loads(response["Body"].read().decode("utf-8"))
    except s3_client.exceptions.NoSuchKey:
        logger.warning(f"S3 key no encontrada: {key}")
        return {}


def load_s3_text(s3_client, bucket, key):
    """Carga texto plano desde S3."""
    try:
        response = s3_client.get_object(Bucket=bucket, Key=key)
        return response["Body"].read().decode("utf-8")
    except:
        return ""
    
def get_market_data(portfolio):
    """
    Descarga datos actuales de mercado para posiciones en portfolio.
    Siempre incluye BTC y ETH.
    """
    tickers = []
    
    # Tickers del portfolio actual
    if portfolio.get("positions"):
        tickers = [p["ticker"] for p in portfolio["positions"]]
    
    market_data = {}
    
    for ticker in tickers:
        try:
            time.sleep(5)
            stock = yf.Ticker(ticker)
            hist = stock.history(period="5d")
            info = stock.info
            
            if not hist.empty:
                current_price = hist["Close"].iloc[-1]
                prev_price = hist["Close"].iloc[-2] if len(hist) > 1 else current_price
                change_pct = ((current_price - prev_price) / prev_price) * 100
                
                market_data[ticker] = {
                    "current_price": round(float(current_price), 2),
                    "change_24h_pct": round(float(change_pct), 2),
                    "volume": int(hist["Volume"].iloc[-1]),
                    "week_high": round(float(hist["High"].max()), 2),
                    "week_low": round(float(hist["Low"].min()), 2),
                    "pe_ratio": info.get("trailingPE", "N/A"),
                    "market_cap": info.get("marketCap", "N/A")
                }
                logger.info(f"✅ {ticker}: ${current_price:.2f} ({change_pct:+.2f}%)")
            
        except Exception as e:
            logger.error(f"❌ Error descargando {ticker}: {e}")
            market_data[ticker] = {"error": str(e)}
    
    return market_data

def build_prompt(portfolio, market_data, last_trades, patterns, blacklist, rules, external_tips):
    """
    Construye el prompt completo para Claude.
    """
    today = datetime.now().strftime("%d/%m/%Y %H:%M CET")
    
    # Calcular P&L posiciones actuales
    positions_detail = []
    for pos in portfolio.get("positions", []):
        ticker = pos["ticker"]
        entry_price = pos["entry_price"]
        quantity = pos["quantity"]
        
        if ticker in market_data and "current_price" in market_data[ticker]:
            current = market_data[ticker]["current_price"]
            pnl_pct = ((current - entry_price) / entry_price) * 100
            pnl_eur = (current - entry_price) * quantity
            
            stop_loss_price = entry_price * (1 + rules["trading_rules"]["stop_loss_percent"] / 100)
            target_price = entry_price * (1 + rules["trading_rules"]["target_profit_percent"] / 100)
            
            positions_detail.append({
                "ticker": ticker,
                "quantity": quantity,
                "entry_price": entry_price,
                "current_price": current,
                "pnl_pct": round(pnl_pct, 2),
                "pnl_eur": round(pnl_eur, 2),
                "stop_loss_price": round(stop_loss_price, 2),
                "target_price": round(target_price, 2),
                "change_24h": market_data[ticker].get("change_24h_pct", "N/A")
            })
    
    prompt = f"""
NO incluyas título ni encabezado en tu respuesta. Ya se añade externamente.
Eres un analista financiero experto y conciso. Fecha y hora actual: {today}

════════════════════════════════════════
PORTFOLIO ACTUAL
════════════════════════════════════════

Capital total: {portfolio.get('total_value_eur', portfolio.get('cash_eur', 0))}€
Efectivo disponible: {portfolio.get('cash_eur', 0)}€
Posiciones abiertas: {len(positions_detail)}

{json.dumps(positions_detail, indent=2, ensure_ascii=False) if positions_detail else "Sin posiciones abiertas actualmente."}

════════════════════════════════════════
DATOS MERCADO ACTUALES (tus acciones)
════════════════════════════════════════

{json.dumps(market_data, indent=2, ensure_ascii=False) if market_data else "Sin posiciones que monitorizar."}

════════════════════════════════════════
HISTORIAL ÚLTIMAS OPERACIONES
════════════════════════════════════════

{json.dumps(last_trades[-10:] if last_trades else [], indent=2, ensure_ascii=False) if last_trades else "Sin operaciones previas registradas."}

════════════════════════════════════════
PATTERNS APRENDIDOS
════════════════════════════════════════

{json.dumps(patterns, indent=2, ensure_ascii=False) if patterns else "Sin patterns aprendidos aún."}

════════════════════════════════════════
REGLAS DE TRADING
════════════════════════════════════════

Stop-loss: {rules['trading_rules']['stop_loss_percent']}%
Target profit: {rules['trading_rules']['target_profit_percent']}%
Máximo posiciones simultáneas: {rules['trading_rules']['max_positions']}
Reserva mínima efectivo: {rules['trading_rules']['min_cash_reserve_eur']}€
Comisión Trade Republic: {rules['trade_republic_costs']['commission_eur']}€/operación
Spread estimado: {rules['trade_republic_costs']['spread_percent_estimate']}%
FX spread (USD/EUR): {rules['trade_republic_costs']['fx_spread_percent_usd_eur']}%
Impuesto ganancias España: 19% (<6k€/año), 21% (6k-50k€), 26% (>50k€)

════════════════════════════════════════
TICKERS NO DISPONIBLES EN TRADE REPUBLIC
════════════════════════════════════════

{', '.join(blacklist) if blacklist else "Ninguno registrado aún."}

════════════════════════════════════════
INPUTS EXTERNOS
════════════════════════════════════════

{json.dumps(external_tips, indent=2, ensure_ascii=False) if external_tips else "Sin inputs externos hoy."}

════════════════════════════════════════
INSTRUCCIONES ANÁLISIS
════════════════════════════════════════

Realiza el siguiente análisis ORDENADO y CONCISO:

1. 🌍 MACRO
   - Eventos importantes hoy/semana (Fed, datos macro, geopolítica)
   - Nivel riesgo: BAJO/MEDIO/ALTO + razón en 1 línea
   - Si riesgo ALTO → recomendar cautela

2. 💼 POSICIONES
   Solo si hay posiciones abiertas:
   - Estado (P&L, distancia stop/target)
   - Recomendación: MANTENER/VENDER/AJUSTAR STOP
   - Razón en 1 línea

3. 🎯 OPORTUNIDADES
   Solo si hay efectivo disponible:
   Validar 4 checks antes de recomendar:
   ✅ Técnico: soporte cercano, RSI <70
   ✅ Fundamental: P/E razonable, balance sano
   ✅ Sentimiento: catalizador confirmado
   ✅ Timing: volumen >1M, mercado abierto
   
   4/4 ✅ → recomendar entrada con precio y cantidad
   3/4 ✅ → "Esperar confirmación"
   Menos de 3 → omitir
   
   ES VÁLIDO no recomendar nada hoy.
   NO recomendar tickers no disponibles en TR.

4. 🧮 COSTES (solo si hay operación propuesta)
   - Coste entrada + salida + FX si aplica
   - Ganancia neta real tras costes e impuestos (19%)

5. 📨 INPUTS EXTERNOS
   Solo si hay inputs:
   - Validar cada tip con 4 checks
   - Clasificar: Válido/Descartar/Vigilar + razón

6. ₿ CRYPTO
   Busca via web search noticias BTC y ETH últimas 24h.
   NO precio exacto, sino:
   - ¿Algo relevante ha pasado?
   - Señal: COMPRAR/VENDER/MANTENER/VIGILAR
   - Razón en 1 línea máximo

7. 🎯 RESUMEN
   - Acción principal hoy en 1 línea
   - Riesgo general: BAJO/MEDIO/ALTO

════════════════════════════════════════
FORMATO OBLIGATORIO
════════════════════════════════════════

- MÁXIMO 250 palabras en total
- Sin tablas
- Sin secciones vacías (si no hay posiciones, omite esa sección)
- Sin calculadora si no hay operación propuesta
- Sin performance si no hay operaciones previas
- Emojis en cada encabezado
- Texto plano, sin markdown, sin asteriscos, sin #
- Recomendaciones claras y directas
"""
    
    return prompt

def analyze_with_claude(prompt, config):
    
    if config.get("mock_claude") == "true":
        logger.info("🔧 MOCK MODE - Sin llamada real a Claude")
        return """
⚠️ MODO TEST - Respuesta simulada, no real

🌍 MACRO: MEDIO
Semana con datos importantes. Cautela moderada recomendada.

💼 POSICIONES
Sin posiciones abiertas.

₿ CRYPTO
BTC: MANTENER - Consolidando en rango.
ETH: VIGILAR - Debil frente a BTC.

🎯 RESUMEN
Sin operaciones recomendadas hoy. Esperar señal clara.
Riesgo general: MEDIO

⚠️ ESTO ES UN TEST - Para análisis real cambiar quitar MOCK.
"""

    """
    Llama a Claude Opus 4.6 con el prompt construido.
    """
    client = anthropic.Anthropic(api_key=config["claude_api_key"])
    
    logger.info("Llamando a Claude API...")
    
    message = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=4000,
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ]
    )
    
    analysis = message.content[0].text
    
    # Log tokens usados
    logger.info(f"Tokens input: {message.usage.input_tokens}")
    logger.info(f"Tokens output: {message.usage.output_tokens}")
    logger.info(f"Coste estimado: ${(message.usage.input_tokens * 5 + message.usage.output_tokens * 25) / 1_000_000:.4f}")
    
    return analysis

def clean_for_telegram(text):
    import re
    text = re.sub(r'#{1,6}\s', '', text)
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    text = re.sub(r'\*(.*?)\*', r'\1', text)
    text = re.sub(r'`(.*?)`', r'\1', text)
    text = re.sub(r'```[\s\S]*?```', '', text)
    text = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', text)
    return text

def send_telegram(message_text, config):
    """
    Envía mensaje via Telegram Bot API.
    Divide mensajes largos si superan límite Telegram (4096 chars).
    """
    token = config["telegram_token"]
    chat_id = config["telegram_chat_id"]
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    
    # Telegram tiene límite de 4096 caracteres por mensaje
    max_length = 4000
    
    if len(message_text) <= max_length:
        messages = [message_text]
    else:
        # Dividir en partes
        messages = []
        while len(message_text) > 0:
            if len(message_text) <= max_length:
                messages.append(message_text)
                break
            
            # Cortar en salto de línea más cercano
            split_at = message_text[:max_length].rfind("\n")
            if split_at == -1:
                split_at = max_length
            
            messages.append(message_text[:split_at])
            message_text = message_text[split_at:]
    
    for i, msg in enumerate(messages):
        try:
            response = requests.post(url, json={
                "chat_id": chat_id,
                "text": msg
            })
            
            if response.status_code == 200:
                logger.info(f"✅ Telegram mensaje {i+1}/{len(messages)} enviado")
            else:
                logger.error(f"❌ Error Telegram: {response.text}")
                
        except Exception as e:
            logger.error(f"❌ Error enviando Telegram: {e}")

def save_results(analysis, config, portfolio):
    """
    Guarda log de ejecución en S3.
    Solo en entorno AWS.
    """
    environment = os.getenv("ENVIRONMENT", "aws")
    
    if environment == "local":
        logger.info("Local: no guardamos en S3")
        return
    
    s3 = boto3.client("s3", region_name=config["aws_region"])
    bucket = config["s3_bucket"]
    
    today = datetime.now().strftime("%Y-%m-%d")
    
    log_entry = {
        "date": today,
        "timestamp": datetime.now().isoformat(),
        "portfolio_value": portfolio.get("total_value_eur", 0),
        "analysis_length": len(analysis),
        "execution": "success"
    }
    
    log_key = f"logs/daily_analysis_{today}.json"
    
    try:
        s3.put_object(
            Bucket=bucket,
            Key=log_key,
            Body=json.dumps(log_entry, ensure_ascii=False),
            ContentType="application/json"
        )
        logger.info(f"✅ Log guardado: {log_key}")
    except Exception as e:
        logger.error(f"❌ Error guardando log: {e}")

def lambda_handler(event, context):
    """
    Entry point principal.
    AWS Lambda llama esta función automáticamente.
    Para testing local: ejecutar main() directamente.
    """
    logger.info("🚀 Iniciando análisis diario trading bot")
    
    try:
        # 1. Configuración
        config = get_config()
        logger.info("✅ Config cargada")
        
        # 2. Cargar portfolio e historial
        portfolio, last_trades, patterns, blacklist, rules, external_tips = load_portfolio(config)
        logger.info(f"✅ Portfolio cargado: {len(portfolio.get('positions', []))} posiciones")
        
        # 3. Datos mercado
        market_data = get_market_data(portfolio)
        logger.info(f"✅ Datos mercado: {len(market_data)} tickers")
        
        # 4. Construir prompt
        prompt = build_prompt(
            portfolio, market_data, last_trades,
            patterns, blacklist, rules, external_tips
        )
        logger.info("✅ Prompt construido")
        
        # 5. Análisis Claude
        analysis = analyze_with_claude(prompt, config)
        logger.info("✅ Análisis Claude completado")
        
        # 6. Enviar Telegram
        header = f"📊 ANÁLISIS - {datetime.now().strftime('%d/%m/%Y %H:%M')} CET\n\n"
        send_telegram(header + clean_for_telegram(analysis), config)
        logger.info("✅ Telegram enviado")
        
        # 7. Guardar resultados
        save_results(analysis, config, portfolio)
        
        logger.info("✅ Ejecución completada con éxito")
        return {"statusCode": 200, "body": "Análisis completado"}
        
    except Exception as e:
        logger.error(f"❌ Error crítico: {e}")
        raise e


# Para testing local
if __name__ == "__main__":
    lambda_handler({}, {})