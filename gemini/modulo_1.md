Contexto (léelo ANTES de programar)
Construiremos mcp-ibkr-trader, un sistema de trading autónomo que conecta un servidor MCP con Interactive Brokers IB Gateway (sockets ibapi).
Capital inicial: 4.000 €. Meta: maximizar beneficios y reinvertir hasta superar el umbral que elimina Pattern Day Trading (PDT), para intensificar intradía en acciones/opciones.
Operaremos en múltiples mercados para extender horarios y oportunidades: FX, micro-futuros, cripto (si aplica en tu cuenta), acciones/ETFs y opciones.
“Backtesting” = forward testing en IBKR Paper (ejecución real en cuenta paper). Además, actuará como Data Factory para entrenar un agente avanzado (PPO/híbrido) más adelante.
Siempre con guardarraíles: riesgo por ATR, límites de exposición, PDT guard, ventanas horarias, kill switch, whitelists y idempotencia de órdenes.
Todo configurable por YAML/env; DRY_RUN para desarrollo sin Gateway activo.


Eres el desarrollador principal de mcp-ibkr-trader. Debes entregar un sistema modular IA+MCP que opere en IB Gateway (sockets ibapi) con cuenta Paper por defecto.
Objetivos

Servidor MCP (FastAPI) con tools: market data, órdenes bracket, cartera, riesgo, PDT guard.

Adaptador TWS/Gateway (ibapi) confiable: históricos, real-time bars, market data, órdenes, posiciones.

Estrategias deterministas: intradía (FX/FUT/CRYPTO), swing (STK/ETF); sizing por ATR; límites.

Paper Backtesting (IBKR Paper): sesiones reales que generan métricas y datasets.

Data Factory: registrar observaciones, decisiones, fills y contexto para un agente RL (PPO) posterior.

Observabilidad (panel/alertas), kill switch, configuración YAML/env, DRY_RUN.
Reglas
– Trabaja por módulos (0→16). No avances sin cumplir criterios de aceptación del módulo.
– Incluye tests, logs estructurados, scripts de ejecución y documentación en cada módulo.
– Backend único: IB Gateway (no Client Portal). Paper por defecto (puerto 4002).
Ya hemos terminado el módulo 0 en el que hemos creado la estructura del proyecto y el repositorio https://github.com/oarjones/mcp-ibkr-trader. Ahora vamos a impelemntar el módulo 1 (Servidor MCP)



Módulo 1 — Servidor MCP (FastAPI, endpoints)
Objetivo

Exponer tools deterministas accesibles vía HTTP (JSON) para que el orquestador/LLM las invoque. El módulo define contratos estables, validación estricta, mocks deterministas (si dry_run=true) y observabilidad (logging estructurado con correlation-id, métricas básicas, health).

Alcance

API HTTP con FastAPI (OpenAPI/Swagger auto).

Cinco endpoints de tools MCP (POST, JSON):

/tool/market_data.get_bars

/tool/orders.place_bracket

/tool/portfolio.get_positions

/tool/risk.pre_trade_check

/tool/pdt_guard.validate

Endpoints auxiliares:

GET /health → estado vivo/ready.

GET /version → hash corto de commit, fecha build, modo dry_run.

Middleware:

Correlation-ID (X-Correlation-Id entrada ↔ salida).

Medición de latencia y tamaño de payload.

CORS opcional (configurable).

Errores normalizados (JSON con código y detalle).

Pruebas unitarias con fastapi.TestClient.

Convenciones generales

Método: todos los tools → POST con Content-Type: application/json.

Autenticación: (opcional en Mód.1) token simple por header X-API-Key leído de config; si no configurado, deshabilitado.

Idempotencia:

orders.place_bracket acepta plan_id opcional; si llega repetido, retorna el mismo resultado.

Determinismo mocks:

Si ibkr.dry_run=true, devuelve respuestas simuladas con IDs derivados de plan_id (o de un hash del payload) para repetir exactamente el resultado en reintentos.

Time-out:

Validación y mocks < 1s; en producción, delega en adaptador (Mód.2) con sus propios timeouts.

Esquemas y modelos (Pydantic)

Colocar los JSON Schemas en mcp_server/schemas/*.json y reflejarlos en Pydantic models en mcp_server/tools/*.

Tipos y enums base

TimeframeEnum: {"1m","5m","15m","1d"}

AssetTypeEnum: {"STK","FX","FUT","CRYPTO","OPT"}

SideEnum: {"BUY","SELL"}

TifEnum: {"DAY","GTC"}

OrderTypeEntryEnum: {"LMT","MKT"}

OrderTypeStopEnum: {"STP"}

OrderTypeTakeEnum: {"LMT"}

1) /tool/market_data.get_bars (POST)

Request

{
  "symbol": "EUR.USD",
  "asset_type": "FX",
  "tf": "1m",
  "start": "2025-08-01T07:00:00Z",
  "end": "2025-08-01T10:00:00Z",
  "what_to_show": "TRADES"
}


symbol: string obligatorio (formato IBKR esperado por mapping).

asset_type: enum obligatorio.

tf: enum obligatorio (1m/5m/15m/1d).

start, end: ISO-8601 (UTC); start < end, ventana ≤ límites IB (validación soft; si no se cumple, error 422).

what_to_show: "TRADES"|"MIDPOINT"|"BID_ASK" (opcional; por defecto de config).

Response (200)

{
  "symbol": "EUR.USD",
  "tf": "1m",
  "bars": [
    {"t":"2025-08-01T07:00:00Z","o":1.0901,"h":1.0903,"l":1.0898,"c":1.0900,"v":1250},
    {"t":"2025-08-01T07:01:00Z","o":1.0900,"h":1.0902,"l":1.0897,"c":1.0899,"v":1180}
  ],
  "meta": {"what_to_show":"TRADES","source":"IBKR|MOCK","count":2}
}


Errores

400: rango temporal inválido (start≥end).

422: validación de campos.

503: si adaptador no disponible (en Mód.1, devolver MOCK si dry_run).

Mock

Genera N barras deterministas a partir de hash(symbol+start+tf).

2) /tool/orders.place_bracket (POST)

Request

{
  "plan_id": "20250801-SES1-MES-BUY-5550.25",
  "account": "DUXXXXXX",
  "symbol": "MES",
  "asset_type": "FUT",
  "qty": 1,
  "side": "BUY",
  "entry": {"type": "LMT", "price": 5550.25},
  "stop": {"type": "STP", "stop_price": 5538.25},
  "take": {"type": "LMT", "price": 5563.25},
  "tif": "DAY",
  "requires_approval": false
}


Validaciones clave

qty > 0 entero.

Coherencia: entry.type ∈ {LMT,MKT}, stop.type=STP, take.type=LMT.

stop_price/price deben ser números positivos; si side="BUY", stop_price < entry.price y take.price > entry.price. (Si MKT, se omite entry.price).

asset_type permitido en markets_enabled.

Si requires_approval=true y no hay override en config, rechazar (409) en Mód.1 (aprobación se implementa más adelante).

Response (200)

{
  "plan_id": "20250801-SES1-MES-BUY-5550.25",
  "parent_id": "SIM-ORD-5f2e",
  "children_ids": ["SIM-TP-9a1c", "SIM-SL-7b3d"],
  "status": "ACCEPTED",
  "dry_run": true
}


En producción (Mód.7 con adaptador), parent_id/children_ids serán reales.

Idempotencia

Si el mismo plan_id llega de nuevo con payload idéntico → retornar los mismos IDs y status="DUPLICATE".

Errores

400: lógica de precios incoherente con side.

409: requires_approval=true sin aprobación (Mód.1).

422: validación campos.

503: adaptador no disponible (en Mód.1, MOCK si dry_run).

Mock

IDs generados como prefix + hash(plan_id).

3) /tool/portfolio.get_positions (POST)

Request (sin cuerpo o {})

{}


Response (200)

{
  "positions": [
    {"symbol":"MES","asset_type":"FUT","qty":1,"avg_price":5550.25,"unrealized_pnl":125.5,"currency":"USD"},
    {"symbol":"EUR.USD","asset_type":"FX","qty":-10000,"avg_price":1.0910,"unrealized_pnl":-15.2,"currency":"USD"}
  ],
  "equity": 4012.35,
  "timestamp": "2025-08-19T09:10:00Z",
  "source": "MOCK"
}


Mock

Generar 0–2 posiciones deterministas; equity = 4000 + ΣPnL.

4) /tool/risk.pre_trade_check (POST)

Request

{
  "symbol": "MES",
  "asset_type": "FUT",
  "qty": 1,
  "plan": {
    "entry": {"type":"LMT","price":5550.25},
    "stop": {"type":"STP","stop_price":5538.25},
    "take": {"type":"LMT","price":5563.25}
  }
}


Validaciones clave

Comprueba consistencia básica; el cálculo profundo de sizing/ATR se hará en Mód.3, pero aquí ya:

qty>0, stop_price>0.

si BUY: stop_price < entry.price; si SELL: stop_price > entry.price.

En Mód.1 devolver mock de ok=true con allowed_qty=qty.

Response (200)

{
  "ok": true,
  "reasons": [],
  "allowed_qty": 1,
  "policy": {
    "risk_per_trade_pct": 0.01,
    "max_daily_loss_pct": 0.05
  },
  "dry_run": true
}


Errores

422: validación campos.

5) /tool/pdt_guard.validate (POST)

Request

{
  "symbol": "AAPL",
  "asset_type": "STK",
  "side": "BUY",
  "is_intraday": true
}


Response (200)

{
  "ok": true,
  "remaining_intraday_trades": 3,
  "note": "PDT enabled: true | MOCK counter"
}


Mock

Si asset_type!="STK" o is_intraday=false → remaining_intraday_trades=∞.

Si asset_type="STK" y is_intraday=true → devolver 3 (constante) en Mód.1.

Especificaciones transversales
Health & Version

GET /health → {"status":"ok","dry_run":true,"uptime_sec":123.4}

GET /version → {"commit":"abc1234","built_at":"2025-08-19T08:00:00Z","version":"0.1.0"}

Headers y Correlation ID

Si llega X-Correlation-Id, propagarlo a logs y respuesta; si no, generar UUID v4.

Añadir X-Served-By: mcp-ibkr-trader y X-Request-Duration-ms.

Logging (Loguru)

Formato JSON por línea (campos: ts, level, corr_id, path, status, duration_ms, payload_size, msg).

Eventos:

request.received, request.validated, tool.start, tool.success, tool.error.

Seguridad / CORS

CORS opcional con orígenes en config (por defecto desactivado).

API key opcional:

Si utils.load_config().get("api_key") existe → exigir header X-API-Key.

Validación fuerte

Usa Pydantic para todos los bodies.

422 para cualquier campo faltante/tipo incorrecto.

Mensajes de error uniformes:

{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Field 'symbol' is required",
    "details": [{"loc":["body","symbol"],"msg":"field required"}]
  }
}

Estructura de carpetas (Mód.1)

mcp_server/main.py: crea app, monta routers, middleware, health/version.

mcp_server/tools/*.py: implementaciones de endpoints (por tool).

mcp_server/schemas/*.json: referencia de contratos (no obligatorio en runtime, sí en repo).

Mocks deterministas (detalles)

Implementar un helper deterministic_id(seed: str, prefix: str) -> str que haga:

hex = sha1(seed).hexdigest()[:4] → f"{prefix}-{hex}"

orders.place_bracket:

seed = plan_id or json.dumps(body, sort_keys=True)

parent: SIM-ORD-<hex>; children: SIM-TP-<hex2>, SIM-SL-<hex3>

Si el mismo plan_id se repite con body idéntico → devolver los mismos IDs y status="DUPLICATE".

market_data.get_bars:

Longitud N = min( (end-start)/tf , 50 ) para limitar payload.

Precios simulados con PRNG seeded por symbol+tf+start.

portfolio.get_positions:

0–2 posiciones con PnL fijo basado en hash del account.

Pruebas (fastapi.TestClient)

Crea tests/test_market_data.py, tests/test_orders.py con casos:

market_data.get_bars

200 con cuerpo válido; len(bars)>0.

422 si falta symbol.

400 si start>=end.

orders.place_bracket

200 con plan_id dado → IDs deterministas.

422 si qty<=0 o precios incoherentes.

409 si requires_approval=true (Mód.1) y no hay aprobación.

Idempotencia: segunda llamada mismo plan_id + payload → status="DUPLICATE".

portfolio.get_positions

200 y estructura válida; equity numérico.

risk.pre_trade_check

200 ok=true (mock).

422 si faltan campos esenciales.

pdt_guard.validate

200; remaining_intraday_trades correcto según mock.

headers

Si envío X-API-Key correcto (si configurado) → 200; si incorrecto → 401.

X-Correlation-Id eco en respuesta.

Comandos ejemplo (curl)

curl -s -X POST http://localhost:8000/tool/market_data.get_bars \
 -H 'Content-Type: application/json' \
 -d '{"symbol":"EUR.USD","asset_type":"FX","tf":"1m","start":"2025-08-01T07:00:00Z","end":"2025-08-01T07:30:00Z"}'

curl -s -X POST http://localhost:8000/tool/orders.place_bracket \
 -H 'Content-Type: application/json' \
 -d '{"plan_id":"demo-001","account":"DUXXXXXX","symbol":"MES","asset_type":"FUT","qty":1,"side":"BUY","entry":{"type":"LMT","price":5550.25},"stop":{"type":"STP","stop_price":5538.25},"take":{"type":"LMT","price":5563.25},"tif":"DAY"}'

Criterios de aceptación (checklist)

 Endpoints creados con FastAPI y responden 200 OK con mocks deterministas (si dry_run=true).

 Validación estricta con Pydantic (422 en errores de schema).

 Errores normalizados (estructura error.code/message/details).

 Correlation-ID soportado en middleware; latencia registrada en logs Loguru.

 Health/Version activos.

 Tests de los 5 tools + cabeceras; pytest -q pasa.

 OpenAPI visible en /docs y /openapi.json; descripciones claras de cada campo.

Notas de implementación

Usa routers por dominio: router_market_data, router_orders, etc., y monta en app.include_router.

Coloca schemas JSON como referencia contractual; los modelos pydantic son la fuente de verdad en runtime.

Prepara interfaces para conectar con TWSAdapter en Mód.2:

market_data.get_bars llamará a TWSAdapter.get_bars(...).

orders.place_bracket llamará a TWSAdapter.place_bracket_order(...).

portfolio.get_positions llamará a TWSAdapter.get_positions().

Este módulo no abre conexión a IBKR: solo define API, contratos, mocks y pruebas.