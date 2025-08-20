Recomendaciones concretas para cerrar Módulo 1 “de libro”
1) Contratos y validación

Pydantic models: asegúrate de tener Request/Response separados para cada tool y response_model en los endpoints.

Esquema de errores unificado: todas las respuestas no-2xx deberían seguir:

{
  "error": {
    "code": "VALIDATION_ERROR|CONFLICT|ADAPTER_DOWN",
    "message": "...",
    "details": [...]
  }
}


Idempotencia en orders.place_bracket: acepta plan_id y devuelve status="DUPLICATE" con los mismos IDs si el payload coincide. Añade test específico.

2) Mocks deterministas (clave para testing y E2E)

Helper deterministic_id(seed, prefix) (sha1 y 4–6 hex chars).

market_data.get_bars: genera barras con PRNG seed = symbol|tf|start.

portfolio.get_positions: genera 0–2 posiciones y equity derivado (seed=account).

pdt_guard.validate: si asset_type!="STK" o is_intraday=false → remaining=Infinity; si STK intradía → remaining=3 (mock).

3) Middleware y observabilidad

Correlation-ID: middleware que lea/escriba X-Correlation-Id y mida latencia; inclúyelo en los logs.

Health & Version: GET /health y GET /version (commit corto, built_at, modo dry_run).

Logging JSON (loguru): al menos ts, level, corr_id, path, status, duration_ms, payload_size.

CORS: desactivado por defecto; configurable en YAML.

4) Seguridad mínima (opcional pero útil)

Header X-API-Key si api_key está definido en config; 401 si falta/incorrecto. Test incluido.

5) Tests que yo añadiría ya

market_data.get_bars: 200 feliz, 422 sin symbol, 400 si start>=end.

orders.place_bracket: 200 feliz; 422 qty≤0; 400 incoherencia de precios según side; 409 si requires_approval=true; idempotencia (plan_id repetido).

pdt_guard: STK intradía → remaining=3; FX → remaining=Infinity.

Headers: eco de X-Correlation-Id y chequeo de X-API-Key cuando aplique.

6) Documentación y DX

README: comandos rápidos:

uvicorn mcp_server.main:app --reload
pytest -q
curl -s -X POST http://localhost:8000/tool/market_data.get_bars \
  -H 'Content-Type: application/json' \
  -d '{"symbol":"EUR.USD","asset_type":"FX","tf":"1m","start":"2025-08-01T07:00:00Z","end":"2025-08-01T07:30:00Z"}'


Makefile (opcional): make dev, make test, make run.

GitHub Actions: workflow simple python -m pip install -r requirements.txt && pytest -q.

7) Config

config.example.yaml: confirma que incluye solo IB Gateway (host, port=4002, client_id, account) y flags: dry_run, markets_enabled, ventanas del scheduler, límites de riesgo, pdt.enabled.

Permite override por variables de entorno (IBKR_HOST, IBKR_PORT, etc.).