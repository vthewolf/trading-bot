# Tracking Costes API & AWS

## Estimaciones Teóricas

### Claude API (Opus 4.6)

**Precios actuales:**
- Input: $5/millón tokens
- Output: $25/millón tokens

**Desglose por análisis diario:**
```
Input tokens (~2500):
- Prompt instrucciones: 1500 tokens
- Portfolio actual: 200 tokens
- Histórico últimas 10 ops: 500 tokens
- Patterns aprendidos: 300 tokens

Output tokens (~1250):
- Análisis completo formateado

Coste por análisis:
(2500 × $5/1M) + (1250 × $25/1M) = $0.044 (~0.04€)
```

**Estimación mensual:**
- 30 análisis diarios: 30 × 0.04€ = **1.20€**
- 4 parsing Zumitow: 4 × 0.02€ = **0.08€**
- 3 post-mortems: 3 × 0.03€ = **0.09€**
- 1 consolidación mensual: 1 × 0.10€ = **0.10€**
- **TOTAL MES: ~1.5€**

**Estimación anual:**
- 12 × 1.5€ = **18€/año**

### AWS Free Tier

**Servicios ALWAYS FREE:**
- Lambda: 1M requests + 400K GB-seconds/mes
- Parameter Store: 10K parámetros standard tier
- EventBridge: Reglas programadas ilimitadas

**Servicios 12 MESES FREE:**
- S3: 5GB storage, 20K GET, 2K PUT/mes
- CloudWatch: 5GB logs ingestion

**Uso estimado (año 1):**
```
Lambda:
- Requests: 30-50/mes
- Compute: ~2000 GB-s/mes

S3:
- Storage: <100 MB
- GET: ~100/mes
- PUT: ~50/mes

EventBridge:
- Reglas programadas: 2

Parameter Store:
- Parámetros: 3

CloudWatch Logs:
- Ingestion: ~500 MB/mes

TOTAL AWS AÑO 1: 0€
```

**Uso estimado (año 2+):**
```
S3 (ya no Free Tier):
- Storage <100MB: ~$0.0023/mes
- GET/PUT requests: ~$0.001/mes
- TOTAL: ~$0.25/mes

Resto servicios: GRATIS

TOTAL AWS AÑO 2+: 0.25€/mes
```

### Créditos AWS ($200 nuevos clientes)

**Bonus 2026:**
- $100 al registrarse
- $100 explorando servicios
- **TOTAL: $200 disponibles 6 meses**

**Implicación:**
- Primeros 6 meses: cualquier exceso cubierto
- Margen error enorme para experimentos

## Costes Totales Sistema

### Año 1 (meses 1-12)
```
AWS:        0€/mes      (Free Tier + créditos)
Claude API: 1.5€/mes    (30 análisis + extras)
───────────────────────
TOTAL:      1.5€/mes    → 18€/año
```

### Año 2+
```
AWS:        0.25€/mes   (solo S3 storage)
Claude API: 1.5€/mes    (idem)
───────────────────────
TOTAL:      1.75€/mes   → 21€/año
```

## Tracking Real Mensual

TODO: _Actualizar cada fin de mes con costes reales Anthropic Console + AWS Billing_

### Febrero 2026
**Período:** 17-28 Feb (12 días parciales)
- **Claude API:** $TBD → X€
- **AWS:** $0 (Free Tier)
- **TOTAL:** X€

**Notas:**
- Primera ejecución: [fecha]
- Análisis ejecutados: X
- Tokens input: X
- Tokens output: X

### Marzo 2026
**Período:** 1-31 Mar (mes completo)
- **Claude API:** $TBD → X€
- **AWS:** $0 (Free Tier)
- **TOTAL:** X€

**Notas:**
- Análisis ejecutados: X
- Operaciones realizadas: X
- Post-mortems: X
- Consolidación mensual: ✅

### Abril 2026
- TBD

## Optimizaciones Implementadas

### Ventana Deslizante Histórico
**Problema original:** Histórico crece infinito → tokens crecen → coste crece

**Solución implementada:**
- Solo últimas 10 ops con detalle completo (500 tokens)
- Resto agregado en patterns_learned.json (300 tokens)
- **Tokens fijos:** ~1150/análisis (no crece con el tiempo)

**Ahorro estimado:**
- Sin optimización año 2: ~7€/mes
- Con optimización: ~1.5€/mes
- **Ahorro: 5.5€/mes → 66€/año**

### Consolidación Mensual vs Diaria
**Decisión:** Análisis profundo solo 1 vez/mes

**Razón:**
- Analizar 30 trades diariamente: desperdicio tokens
- Consolidar mensualmente: insights útiles, coste mínimo
- **Ahorro:** ~2€/mes

## Alertas Configuradas

### AWS Billing Alerts
- $1 alcanzado → Email warning
- $3 alcanzado → Email urgente
- $5 alcanzado → Email crítico + review consumo

### Anthropic Console
- Budget mensual: $3 (~2.5€)
- Alerta 80% consumo
- Alerta 100% consumo

## Benchmark Competencia

### Alternativas mercado (coste/mes)

**Trading bots comerciales:**
- TradingView Premium: 15-60€/mes
- Cryptohopper: 19-99€/mes
- 3Commas: 22-75€/mes

**Este sistema:**
- **1.5€/mes** → 90% más barato
- Personalizado 100%
- Aprendizaje continuo
- Sin límites artificiales

## ROI Calculado

**Coste sistema año 1:** 18€

**Para recuperar inversión necesitas:**
- 1 trade ganador +2% con 1000€ = +20€ neto
- **ROI mes 1 si 1 trade exitoso**

**Breakeven ultra conservador:**
- Incluso 0 trades ganadores → coste oportunidad 18€/año
- Equivalente: 2 cafés/mes

## Notas Adicionales

### Tokens API - Factores Variables

**Pueden incrementar coste:**
- Análisis más largos (más noticias ese día)
- Post-mortems complejos (trades con muchas variables)
- Parsing Zumitow newsletters extensas

**Pueden reducir coste:**
- Días sin eventos → análisis más corto
- Períodos sin operar → menos post-mortems
- Newsletters Zumitow breves

**Estimación:** Rango real 1.2-2€/mes

### AWS - Sorpresas Posibles

**Costes inesperados a vigilar:**
- Data transfer out S3 (si descargas mucho)
- CloudWatch Logs retention (si acumulas >5GB)
- Lambda concurrency (si ejecutas manual muchas veces)

**Todos muy improbables en nuestro uso, pero monitorizar primeras semanas.**