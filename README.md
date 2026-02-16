# 📊 Trading Bot - Sistema Análisis Automatizado

Sistema automatizado de análisis de portfolio en Trade Republic usando Claude Opus 4.6, desplegado en AWS Lambda con notificaciones vía Telegram.

## 🎯 Objetivo

Analizar portfolio de trading diariamente, validar oportunidades con múltiples checks anti-FOMO, calcular costes reales (comisiones + spread + impuestos), y aprender de operaciones pasadas para mejorar decisiones.

## 🏗️ Arquitectura

### Servicios AWS
- **Lambda**: 3 funciones (análisis diario, consolidación mensual, Telegram handler)
- **EventBridge**: Triggers programados (8:00 CET diario + mensual)
- **S3**: Storage histórico operaciones y patterns aprendidos
- **Parameter Store**: Secrets (API keys)
- **CloudWatch**: Logs y monitoring

### Integrations
- **Claude API** (Opus 4.6): Motor análisis IA
- **Telegram Bot**: Interface usuario
- **Trade Republic**: Broker (actualización manual portfolio v1)
- **Yahoo Finance**: Datos mercado tiempo real
- **Web Search**: Noticias, contexto macro

## 📊 Funcionalidades

### Análisis Matinal (8:00 CET)
1. **Contexto Macro**: Eventos Fed, geopolítica, datos económicos
2. **Análisis Posiciones**: Correlaciones, eventos corporativos, recomendaciones
3. **Validación Anti-FOMO**: 4 checks (técnico, fundamental, sentimiento, timing)
4. **Calculadora Costes**: Comisiones + spread + divisa + impuestos
5. **Gestión Riesgo**: % correlación, exposición sectorial
6. **Input Externo**: Newsletter Zumitow, tips amigos
7. **Crypto**: BTC/ETH análisis
8. **Tracking Performance**: Win rate, patterns aprendidos

### Comandos Telegram
```
/portfolio - Estado posiciones actuales
/balance - Ganancias/pérdidas totales
/stats - Estadísticas (win rate, mejor trade)
/compra TICKER CANT PRECIO - Registrar compra
/vende TICKER CANT PRECIO - Registrar venta
/blacklist TICKER - Marcar no disponible TR
/tip TICKER - RAZÓN - Input recomendación externa
/deep-analysis - Análisis completo histórico
```

### Consolidación Mensual (automática)
- Análisis operaciones del mes
- Identificación patterns exitosos/fallidos
- Insights consolidados para aprendizaje
- Ventana deslizante (últimos 30 trades)
- Optimización tokens API

### Simulador Paralelo
- Portfolio virtual ejecuta todas recomendaciones
- Comparación mensual: Real vs Simulado
- Identifica desviaciones decisiones

## 📁 Estructura Proyecto
```
trading-bot/
├── README.md
├── CHANGELOG.md
├── .gitignore
├── docs/
│   ├── architecture.md
│   ├── setup-guide.md 
│   ├── api-costs.md  
│   └── telegram-commands.md 
├── lambdas/
│   ├── daily_analysis/
│   │   ├── handler.py
│   │   ├── requirements.txt
│   │   └── prompts/
│   │       └── analysis_prompt.txt
│   ├── monthly_consolidation/
│   │   ├── handler.py
│   │   └── requirements.txt
│   └── telegram_handler/
│       ├── handler.py
│       └── requirements.txt
├── config/
│   ├── rules.json.example  
│   └── aws/
│       └── infrastructure.yaml  
├── scripts/
│   ├── deploy.sh 
│   ├── test_local.py 
│   └── setup_aws.sh 
└── tests/
    ├── test_analysis.py
    └── test_telegram.py
```

## 🔐 Seguridad

- Secrets en AWS Parameter Store
- `.gitignore` configurado para excluir credenciales
- IAM roles con permisos mínimos necesarios
- Alertas billing configuradas

## 📈 Roadmap

### v0.1 (Setup Básico)
- [x] Estructura repo
- [ ] Lambda daily_analysis funcional
- [ ] S3 storage configurado
- [ ] Telegram bot básico

### v0.2 (Análisis Completo)
- [ ] Validación anti-FOMO
- [ ] Calculadora costes completa
- [ ] Contexto macro integrado
- [ ] Parsing Zumitow

### v0.3 (Aprendizaje)
- [ ] Tracking performance
- [ ] Post-mortem automático
- [ ] Consolidación mensual
- [ ] Simulador paralelo

### v1.0 (Producción)
- [ ] Sistema completo funcionando
- [ ] Documentación completa
- [ ] Testing automatizado
- [ ] Monitoring y alertas

### v2.0 (Futuro)
- [ ] Integración API Trade Republic
- [ ] CI/CD con GitHub Actions
- [ ] Alertas intraday
- [ ] Dashboard web visualización

## 📝 Changelog

Ver [CHANGELOG.md](CHANGELOG.md) para historial cambios detallado.

## 🤝 Contribución

Proyecto personal de aprendizaje. No abierto a contribuciones externas.

## 📄 Licencia

Uso personal. Todos los derechos reservados.

## 👤 Autor

**Victor Santiago**
- GitHub: [@vthewolf](https://github.com/vthewolf)
- Email: vsantiagoferrera@gmail.com

---

**Estado**: 🚧 En desarrollo activo
**Última actualización**: Febrero 2026
