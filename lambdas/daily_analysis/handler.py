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
    """Lee configuración según entorno."""
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
    """Carga portfolio actual y blacklist desde S3 o archivos locales."""
    environment = os.getenv("ENVIRONMENT", "aws")
    
    if environment == "local":
        logger.info("Cargando portfolio desde archivos locales")
        portfolio = {
            "positions": [],
            "cash_eur": 2300,
            "last_updated": datetime.now().isoformat()
        }
        blacklist = []
        rules = load_rules_local()
        
    else:
        s3 = boto3.client("s3", region_name=config["aws_region"])
        bucket = config["s3_bucket"]
        
        # Portfolio actual
        portfolio = load_s3_json(s3, bucket, "portfolio/current_positions.json")
        
        # Tickers blacklist
        blacklist_raw = load_s3_text(s3, bucket, "external/tickers_blacklist.txt")
        blacklist = [t.strip() for t in blacklist_raw.split("\n") if t.strip()]
        
        # Reglas trading
        rules = load_s3_json(s3, bucket, "config/rules.json")
    
    return portfolio, blacklist, rules


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
    """Descarga solo precio actual para posiciones en portfolio."""
    tickers = []
    
    if portfolio.get("positions"):
        tickers = [p["ticker"] for p in portfolio["positions"]]
    
    market_data = {}
    
    for ticker in tickers:
        try:
            time.sleep(5)
            stock = yf.Ticker(ticker)
            hist = stock.history(period="1d")
            
            if not hist.empty:
                current_price = hist["Close"].iloc[-1]
                market_data[ticker] = {
                    "current_price": round(float(current_price), 2)
                }
                logger.info(f"✅ {ticker}: {current_price:.2f}€")
            
        except Exception as e:
            logger.error(f"❌ Error descargando {ticker}: {e}")
            market_data[ticker] = {"error": str(e)}
    
    return market_data


def build_prompt(portfolio, market_data, blacklist, rules):
    """Construye prompt minimalista para Opus."""
    today = datetime.now().strftime("%d/%m/%Y %H:%M CET")
    
    # Solo incluir posiciones si existen
    positions_text = ""
    if portfolio.get("positions"):
        positions_text = "\n\nPOSICIONES ABIERTAS:\n"
        for pos in portfolio["positions"]:
            ticker = pos["ticker"]
            if ticker in market_data and "current_price" in market_data[ticker]:
                current = market_data[ticker]["current_price"]
                entry = pos["entry_price"]
                pnl_pct = round(((current - entry) / entry) * 100, 2)
                positions_text += f"{ticker}: {pos['quantity']} @ {entry}€ → {current}€ ({pnl_pct:+}%)\n"
    
    prompt = f"""Analista financiero experto. Fecha: {today}{positions_text}

REGLAS: Stop-loss {rules['trading_rules']['stop_loss_percent']}%, Target {rules['trading_rules']['target_profit_percent']}%
NO DISPONIBLE TR: {', '.join(blacklist) if blacklist else 'ninguno'}

ANÁLISIS (máximo 200 palabras):

🌍 MACRO
Riesgo mercado: BAJO/MEDIO/ALTO
Razón: 1 línea (Fed, datos macro, geopolítica, festivos)

💼 POSICIONES (si hay)
Cada una: MANTENER/VENDER/AJUSTAR STOP
Razón: 1 línea por posición

🎯 OPORTUNIDADES (0-3 tickers máximo)
Solo incluir si pasa 4/4 checks:
✅ Técnico (soporte claro, RSI<70)
✅ Fundamental (P/E razonable, balance sano)  
✅ Sentimiento (catalizador confirmado múltiples fuentes)
✅ Timing (volumen >1M, mercado abierto, sin eventos inminentes)

Por cada oportunidad 4/4:
- Ticker + razón compra en 1 línea

Si ninguno pasa 4/4: omitir sección completa

₿ CRYPTO
BTC: ESPERAR/VIGILAR/ACTUAR (razón 3 palabras)
ETH: ESPERAR/VIGILAR/ACTUAR (razón 3 palabras)

✅ RESUMEN EJECUTIVO
2-3 líneas que condensen TODO el análisis.
Debe ser autosuficiente: leyendo solo esto sé exactamente qué hacer hoy.

IMPORTANTE:
- Sin tablas, sin markdown, sin asteriscos
- Directo y accionable
- Si no hay oportunidades claras → no fuerces recomendaciones
- Máximo 200 palabras TOTAL
"""
    
    return prompt


def analyze_with_claude(prompt, config):
    """Llama a Claude Opus 4.6 con el prompt construido."""
    
    # MODO MOCK
    if config.get("mock_claude") == "true":
        logger.info("🔧 MOCK MODE - Sin llamada real a Claude")
        return """⚠️ MODO TEST - Respuesta simulada

🌍 MACRO: MEDIO
Respuesta mockeada.

💼 POSICIONES
Respuesta mockeada.

₿ CRYPTO
BTC: Mock
ETH: Mock

✅ RESUMEN
Mock.

⚠️ TEST - Eliminar MOCK para análisis real."""

    # Llamada real a Claude
    client = anthropic.Anthropic(api_key=config["claude_api_key"])
    logger.info("Llamando a Claude API...")
    
    message = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=1000,
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
    """Limpia markdown residual que Telegram no entiende."""
    import re
    text = re.sub(r'#{1,6}\s', '', text)
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    text = re.sub(r'\*(.*?)\*', r'\1', text)
    text = re.sub(r'`(.*?)`', r'\1', text)
    text = re.sub(r'```[\s\S]*?```', '', text)
    text = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', text)
    return text


def send_telegram(message_text, config):
    """Envía mensaje via Telegram Bot API."""
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


def save_results(analysis, config, portfolio):
    """Guarda log de ejecución en S3. Solo en entorno AWS."""
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
    """Entry point principal."""
    logger.info("🚀 Iniciando análisis diario trading bot")
    
    try:
        # 1. Configuración
        config = get_config()
        logger.info("✅ Config cargada")
        
        # 2. Cargar portfolio y blacklist
        portfolio, blacklist, rules = load_portfolio(config)
        logger.info(f"✅ Portfolio cargado: {len(portfolio.get('positions', []))} posiciones")
        
        # 3. Datos mercado
        market_data = get_market_data(portfolio)
        logger.info(f"✅ Datos mercado: {len(market_data)} tickers")
        
        # 4. Construir prompt
        prompt = build_prompt(portfolio, market_data, blacklist, rules)
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