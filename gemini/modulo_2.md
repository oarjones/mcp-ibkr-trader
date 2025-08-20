Contexto del proyecto

Estás trabajando en el repositorio mcp-ibkr-trader, cuyo objetivo es construir un servidor MCP que permita a un agente IA (como ChatGPT) interactuar con IBKR a través de IB Gateway, para hacer trading automatizado con control de riesgos.
El Módulo 0 ya creó la estructura base y el repositorio en GitHub, y el Módulo 1 implementó un servidor MCP con endpoints deterministas (mock).
Ahora toca desarrollar el Módulo 2, que conecta de verdad con IB Gateway usando la librería oficial ibapi.

Objetivo del Módulo 2 — Adaptador IB Gateway (ibapi):

Implementar un adaptador robusto para IB Gateway que:

Maneje conexión/desconexión con reconexión automática.

Exponga métodos de alto nivel (TWSAdapter) para datos de mercado, órdenes bracket, y posiciones/cuenta.

Controle pacing rules y use colas con timeouts para respuestas.

Funcione en modo real contra IB Gateway o en modo DRY_RUN (simulación).

Esté totalmente encapsulado en ibkr_adapter/.

Tareas a realizar
1. Estructura de archivos

Crear los siguientes archivos dentro de ibkr_adapter/:

tws_client.py → implementación de bajo nivel (subclase de EWrapper, EClient).

adapter.py → capa de alto nivel síncrona/awaitable que usa TWSClient.

mapping.py → utilidades para construir contratos IBKR (resolve_contract).

2. Clase TWSClient

Ubicación: ibkr_adapter/tws_client.py

Subclase de EWrapper, EClient.

Funcionalidades mínimas:

Conexión/desconexión: connect(host, port, client_id), disconnect().

Hilo de eventos: iniciar loop en thread separado (threading.Thread).

Callbacks básicos:

nextValidId → almacenar el próximo ID de orden.

error → loggear con loguru.

connectionClosed → disparar lógica de reconexión.

Market data:

reqHistoricalData: recuperar OHLCV respetando pacing (2s entre llamadas).

reqRealTimeBars: suscripción a barras de 5s.

reqMktData: obtener bid/ask en tiempo real.

Órdenes:

Implementar make_bracket_order(parentId, action, qty, limitPrice, takeProfitPrice, stopLossPrice) que devuelva lista [parent, takeProfit, stopLoss] con transmit correcto.

Cuenta/posiciones:

reqPositions, reqAccountSummary.

Colas para respuestas:

Usa queue.Queue para responses asociadas a requestId.

Implementa helper wait_for_response(reqId, timeout=5.0) que devuelve o lanza TimeoutError.

3. Clase TWSAdapter

Ubicación: ibkr_adapter/adapter.py

Encapsula un TWSClient.

Exposición de API de alto nivel:

class TWSAdapter:
    def get_bars(self, symbol: str, tf: str, start: str, end: str) -> pd.DataFrame: ...
    def place_bracket_order(self, symbol: str, asset_type: str, qty: int, side: str,
                            entry: float, stop: float, take: float, tif: str) -> dict: ...
    def get_positions(self) -> list[dict]: ...


get_bars: devuelve pandas DataFrame con columnas [ts, open, high, low, close, volume].

place_bracket_order: envía orden bracket y devuelve dict con IDs.

get_positions: devuelve lista de posiciones normalizadas (symbol, qty, avg_price, unrealized_pnl).

Maneja timeouts: si no recibe respuesta → lanza excepción.

Reconexión: usar tenacity o un backoff manual si la conexión cae.

4. Archivo mapping.py

Implementar resolve_contract(symbol: str, asset_type: str) -> Contract.

Cachear resultados (functools.lru_cache).

Ejemplos:

symbol="AAPL", asset_type="STK" → contrato NASDAQ.

symbol="EUR.USD", asset_type="FX" → contrato de forex.

symbol="ES", asset_type="FUT" → contrato de futuros CME.

5. Configuración (usar YAML del Módulo 0)

Usar credenciales de IB Gateway desde config.yaml:

ibkr:
  host: "127.0.0.1"
  port: 4002
  client_id: 123
  account: "DU123456"
dry_run: true


Si dry_run: true, todos los métodos devuelven mocks deterministas en vez de llamar a Gateway.

6. Logging

Usa loguru con correlation_id pasado desde capa superior.

Logea cada request/response (reqId, símbolo, tiempo de espera).

7. Criterios de aceptación

Script de prueba tests/test_tws_adapter.py que:

Si dry_run: true → devuelve mocks deterministas.

Si dry_run: false y Gateway activo → conecta, pide 5 velas de EUR.USD y devuelve DataFrame no vacío.

Cobertura de errores:

Timeout controlado.

Manejo de pacing: si se llaman dos reqHistoricalData en <2s → cola la segunda.

Reintento de conexión si connectionClosed o error 1100.

8. Ejemplo de uso
from ibkr_adapter.adapter import TWSAdapter

adapter = TWSAdapter(config_path="config.yaml")
df = adapter.get_bars("EUR.USD", "1m", "20250101 09:00:00", "20250101 09:10:00")
print(df.head())

order = adapter.place_bracket_order("AAPL", "STK", 10, "BUY", 180.0, 175.0, 190.0, "DAY")
print(order)

positions = adapter.get_positions()
print(positions)