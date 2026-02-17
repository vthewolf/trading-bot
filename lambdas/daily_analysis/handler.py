import os
import json
import logging
from datetime import datetime

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
            "aws_region": os.getenv("AWS_REGION", "eu-west-1")
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
    
    # Siempre incluir crypto
    crypto_tickers = ["BTC-USD", "ETH-USD"]
    all_tickers = list(set(tickers + crypto_tickers))
    
    market_data = {}
    
    for ticker in all_tickers:
        try:
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
Eres un analista financiero experto. Fecha y hora actual: {today}

════════════════════════════════════════
PORTFOLIO ACTUAL
════════════════════════════════════════

Capital total: {portfolio.get('total_value_eur', portfolio.get('cash_eur', 0))}€
Efectivo disponible: {portfolio.get('cash_eur', 0)}€
Posiciones abiertas: {len(positions_detail)}

{json.dumps(positions_detail, indent=2, ensure_ascii=False) if positions_detail else "Sin posiciones abiertas actualmente."}

════════════════════════════════════════
DATOS MERCADO ACTUALES
════════════════════════════════════════

{json.dumps(market_data, indent=2, ensure_ascii=False)}

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

Realiza el siguiente análisis COMPLETO y ORDENADO:

1. CONTEXTO MACRO
   - Busca eventos importantes hoy/esta semana (Fed, datos macro, geopolítica)
   - Evalúa impacto en mercados
   - Nivel riesgo macro: BAJO/MEDIO/ALTO
   - Si riesgo ALTO → recomendar cautela general

2. ANÁLISIS POSICIONES ACTUALES
   Para cada posición:
   - Estado actual (precio, P&L, distancia stop/target)
   - Noticias últimas 24h relevantes
   - Análisis técnico (momentum, soportes/resistencias)
   - Correlaciones entre posiciones (avisar si >70% correlacionado)
   - Eventos corporativos próximos (earnings, dividendos, splits)
   - Recomendación clara: MANTENER / VENDER / VENDER PARCIAL / AJUSTAR STOP

3. NUEVAS OPORTUNIDADES (solo si hay efectivo disponible O swap vale la pena)
   Para cada oportunidad validar 4 CHECKS:
   ✅ Técnico: Precio cerca soporte, RSI <70
   ✅ Fundamental: P/E razonable, balance sano
   ✅ Sentimiento: Catalizador confirmado múltiples fuentes
   ✅ Timing: Volumen >1M diario, no pre-market errático
   
   Solo recomendar si 4/4 ✅
   Si 3/4 → "Esperar confirmación"
   Si <3/4 → No mencionar
   
   NO recomendar tickers de la lista de no disponibles TR.
   ES PERFECTAMENTE VÁLIDO no recomendar ninguna entrada hoy.

4. CALCULADORA COSTES (para cada operación propuesta)
   Calcular:
   - Comisión entrada: 1€
   - Spread entrada ({rules['trade_republic_costs']['spread_percent_estimate']}%): X€
   - FX entrada si USD ({rules['trade_republic_costs']['fx_spread_percent_usd_eur']}%): X€
   - Total costes entrada: X€
   - Comisión salida: 1€
   - Spread salida: X€
   - FX salida si USD: X€
   - Total costes salida: X€
   - TOTAL COSTES OPERACIÓN: X€
   - Breakeven necesario: X%
   - Ganancia bruta con target {rules['trading_rules']['target_profit_percent']}%: X€
   - Menos costes: X€
   - Menos impuestos (19%): X€
   - GANANCIA NETA REAL: X€ (Y%)

5. GESTIÓN RIESGO PORTFOLIO
   - Exposición por sector
   - Exposición geográfica (USA/Europa/Crypto)
   - Correlación general
   - Alertas si concentración >40% en sector/país

6. ANÁLISIS INPUTS EXTERNOS
   Para cada input (Zumitow/amigos):
   - Contexto completo (NO aislar ticker del contexto)
   - Validar con datos reales
   - Clasificar: Oportunidad válida / Descartar / Vigilar

7. CRYPTO
   - BTC y ETH: precio, cambio 24h, niveles clave
   - Solo señal si oportunidad excepcional

8. PERFORMANCE Y APRENDIZAJE
   - Win rate actual
   - Patterns que están funcionando
   - Ajustes estrategia si procede

9. RESUMEN EJECUTIVO
   - 3-4 líneas máximo
   - Acción principal recomendada hoy
   - Nivel riesgo general: BAJO/MEDIO/ALTO

FORMATO SALIDA:
- Usa emojis para facilitar lectura rápida
- Sé conciso pero completo
- Solo información accionable
- Evita repeticiones
"""
    
    return prompt

def analyze_with_claude(prompt, config):
    """
    Llama a Claude Opus 4.6 con el prompt construido.
    """
    client = anthropic.Anthropic(api_key=config["claude_api_key"])
    
    logger.info("Llamando a Claude API...")
    
    message = client.messages.create(
        model="claude-opus-4-6-20260205",
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
                "text": msg,
                "parse_mode": "Markdown"
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
        header = f"📊 *ANÁLISIS DIARIO - {datetime.now().strftime('%d/%m/%Y %H:%M')} CET*\n\n"
        send_telegram(header + analysis, config)
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