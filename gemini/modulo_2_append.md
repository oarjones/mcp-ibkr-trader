Para corregir/robustecer:

Configuración: clave usada es ib_gateway, pero en el plan usamos ibkr.

get_bars:

Fuerza asset_type="STK" (ignora el real del símbolo).

Pasa tf directamente a barSizeSetting; IB espera "1 min", "5 mins", "15 mins", "1 day".

durationStr está hardcodeado "1 D" y no se calcula a partir de start/end.

Conversión de fechas: historicalData entrega bar.date como string "YYYYMMDD HH:MM:SS" (no epoch); unit='s' es incorrecto.

No hay control de pacing ni espera a historicalDataEnd para agrupar barras. 
GitHub

IDs/estado:

next_valid_id se usa antes de garantizar que está inicializado (riesgo de None).

reqId/orderId deben gestionarse de forma atómica/thread-safe.

Bracket orders:

Firma make_bracket_order y llamada: en adapter usas parentOrderId= mientras tu helper probablemente espera parentId= (conviene alinear).

Asegura transmit=False en parent/TP y True en stop para enviar los tres como bloque.

mapping.py:

FUT fija lastTradeDateOrContractMonth="202509" (hardcoded).

CRYPTO: IB admite secType="CRYPTO" con exchange="PAXOS" en cuentas compatibles, pero a veces se usa CASH (BTC/USD). Conviene soportar ambas variantes por config/flag. 
GitHub

get_positions:

En adapter llamas self.client.get_positions(), pero no veo método de alto nivel implementado en TWSClient que agregue posiciones usando position/positionEnd. (No aparece en el diff mostrado). 
GitHub

DRY_RUN:

Bien que devuelva mocks, pero mejor hacerlos deterministas por semilla (symbol|tf|start / plan_id) para que los tests sean idempotentes.

Parches sugeridos (mínimos pero sólidos)
1) Config coherente

En TWSAdapter.__init__ usa la misma clave del Módulo 0 (ibkr) y respeta dry_run:

cfg = load_config()
self.dry_run = bool(cfg.get("dry_run", True))
ib = cfg.get("ibkr", {})  # <- no "ib_gateway"
host = ib.get("host", "127.0.0.1")
port = int(ib.get("port", 4002))
client_id = int(ib.get("client_id", 101))

2) Mapeo tf → (barSize,duration)

Crea un helper:

TF_MAP = {
    "1m":  ("1 min",  "1800 S"),   # 30 min
    "5m":  ("5 mins", "3600 S"),   # 1 h
    "15m": ("15 mins","7200 S"),   # 2 h
    "1d":  ("1 day",  "1 M"),      # 1 mes (ajusta si quieres)
}

def ib_hist_params(tf, start_iso, end_iso):
    bar_size, default_duration = TF_MAP[tf]
    # Calcula duración aproximada por diferencia de start/end
    # y limita a los máximos de IB si hace falta:
    # ... (puede quedarse default_duration por simplicidad inicial)
    return bar_size, default_duration

3) get_bars correcto (esperar hasta historicalDataEnd)

En TWSClient añade un método “alto nivel”:

def get_historical_data(self, contract, endDateTime, durationStr, barSizeSetting,
                        whatToShow="TRADES", useRTH=1, timeout=15.0):
    reqId = self._next_req_id()  # thread-safe
    q = self.get_response_queue(reqId)
    bars = []

    # emitir petición
    self.reqHistoricalData(reqId, contract, endDateTime, durationStr,
                           barSizeSetting, whatToShow, useRTH, 1, False, [])
    # recopilar hasta 'historicalDataEnd'
    end_marker = object()
    def _on_end(_reqId, _start, _end):
        if _reqId == reqId:
            q.put(end_marker)

    # hook temporal:
    orig_end = getattr(self, "historicalDataEnd")
    def wrap_end(_reqId, _start, _end):
        _on_end(_reqId, _start, _end)
        orig_end(_reqId, _start, _end)
    self.historicalDataEnd = wrap_end  # monkey patch simple (o usa señales propias)

    start_time = time.time()
    while True:
        remaining = timeout - (time.time() - start_time)
        if remaining <= 0:
            raise TimeoutError(f"historicalData timeout for reqId={reqId}")
        item = q.get(timeout=remaining)
        if item is end_marker:
            break
        # item es un 'BarData' con campos .date, .open, .high, .low, .close, .volume
        bars.append(item)

    # restaurar callback original
    self.historicalDataEnd = orig_end
    return bars


En TWSAdapter.get_bars:

asset_type = self._infer_asset_type(symbol)  # opcional o pásalo como arg
contract = resolve_contract(symbol, asset_type)

bar_size, duration = ib_hist_params(tf, start, end)
bars = self.client.get_historical_data(contract,
                                       endDateTime=end.replace("T"," ").replace("Z",""),
                                       durationStr=duration,
                                       barSizeSetting=bar_size,
                                       whatToShow="TRADES",
                                       useRTH=1, timeout=20)

import pandas as pd
rows = []
for b in bars:
    # b.date suele ser "YYYYMMDD  HH:MM:SS" o "YYYYMMDD"
    ts = pd.to_datetime(b.date, format="%Y%m%d  %H:%M:%S", errors="coerce")
    if pd.isna(ts):
        ts = pd.to_datetime(b.date, format="%Y%m%d", errors="coerce")
    rows.append({"ts": ts, "open": b.open, "high": b.high,
                 "low": b.low, "close": b.close, "volume": getattr(b, "volume", 0)})

df = pd.DataFrame(rows).dropna(subset=["ts"]).sort_values("ts").reset_index(drop=True)
return df


Nota: si quieres calcular durationStr a partir de start/end, haz pd.to_datetime(end) - pd.to_datetime(start) y mapea a los sufijos de IB (“S”, “D”, “W”, “M”).

4) next_valid_id y reqId thread-safe

Añade en TWSClient.__init__:

import threading
self._id_lock = threading.Lock()
self._req_id = 900000  # base para reqId (separado de orderId)

def _next_req_id(self):
    with self._id_lock:
        self._req_id += 1
        return self._req_id

def _next_order_id(self):
    with self._id_lock:
        oid = self.next_valid_id
        self.next_valid_id += 1
        return oid


En connect_and_run, espera a que nextValidId llegue antes de permitir usar _next_order_id().

5) Bracket order (firma y transmit)

Alinea las firmas:

def make_bracket_order(self, parentId:int, action:str, quantity:int,
                       limitPrice:float, takeProfitPrice:float, stopLossPrice:float):
    # parent (transmit=False), TP (transmit=False), SL (transmit=True)
    ...


Y en TWSAdapter.place_bracket_order(...) pásale parentId= (no parentOrderId=). Al generar IDs:

parent_order_id = self.client._next_order_id()
orders = self.client.make_bracket_order(parentId=parent_order_id, action=side,
                                        quantity=qty, limitPrice=entry,
                                        takeProfitPrice=take, stopLossPrice=stop)
for o in orders:
    self.client.placeOrder(o.orderId, contract, o)

return {"parent_id": parent_order_id,
        "children_ids": [parent_order_id+1, parent_order_id+2]}

6) Posiciones

Implementa en TWSClient:

def get_positions_blocking(self, timeout=5.0):
    reqId = self._next_req_id()
    q = self.get_response_queue(reqId)
    positions = []
    end_marker = object()

    def position(account, contract, position, avgCost):
        q.put((account, contract, position, avgCost))
    def positionEnd():
        q.put(end_marker)

    # engancha callbacks temporalmente (o crea estructura propia por señales)
    orig_pos, orig_end = getattr(self, "position", None), getattr(self, "positionEnd", None)
    self.position = position
    self.positionEnd = positionEnd

    self.reqPositions()
    start = time.time()
    while True:
        item = q.get(timeout=timeout - (time.time()-start))
        if item is end_marker:
            break
        account, contract, pos, avg_cost = item
        positions.append({"symbol": contract.symbol, "asset_type": contract.secType,
                          "qty": pos, "avg_price": avg_cost})

    # restaurar callbacks
    self.position = orig_pos
    self.positionEnd = orig_end
    return positions


Y en TWSAdapter.get_positions():

if self.dry_run:
    return [{"symbol": "DRY", "asset_type":"STK", "qty":100, "avg_price":100.0, "unrealized_pnl":10.0}]
return self.client.get_positions_blocking()

7) mapping.py más flexible

FUT: permite pasar contract_month opcional, y si no se pasa usa la front month a partir de un mapeo simple/placeholder o config.

CRYPTO: añade opción use_crypto_secType: true|false en config; si false crear como CASH symbol="BTC", currency="USD", exchange="PAXOS".

Tests que faltan (añádelos a tests/test_tws_adapter.py)

test_get_bars_dry_run_deterministic() → misma llamada ⇒ mismo DF (mismo hash/seed).

test_place_bracket_dry_run_idempotent(plan_id) si añades plan_id al adapter.

test_get_bars_parses_dates() → verifica que ts es datetime64.

(Opcional integración) con Gateway levantado: pide 10 min de EUR.USD y espera df.shape[0]>0.