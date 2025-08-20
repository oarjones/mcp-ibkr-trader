import threading
import time
from queue import Queue, Empty
from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from loguru import logger

class IBKRError(Exception):
    """Custom exception for IBKR errors."""
    def __init__(self, code: int, message: str, original_error: str = None):
        self.code = code
        self.message = message
        self.original_error = original_error
        super().__init__(f"IBKR Error {code}: {message} (Original: {original_error})")

IBKR_ERROR_MAP = {
    10167: "Permissions error: Market data not subscribed.",
    200: "Security definition error: Contract not found or invalid.",
    162: "Farm busy: Request throttled by IBKR.",
    321: "Pacing violation: Too many requests in a short period.",
}

_hist_lock = threading.Lock()
_last_hist = 0.0

def _pace_hist(min_gap=2.0):
    global _last_hist
    with _hist_lock:
        now = time.time()
        delay = _last_hist + min_gap - now
        if delay > 0:
            time.sleep(delay)
        _last_hist = time.time()

class TWSClient(EWrapper, EClient):
    # TODO: Consider adding a Semaphore to limit concurrent reqHistoricalData calls
    # to avoid pacing violations (e.g., max 2 concurrent requests).
    def __init__(self):
        EClient.__init__(self, self)
        self.response_queues = {}
        self.next_valid_id = None
        self.is_connected = False
        self._id_lock = threading.Lock()
        self._req_id = 900000  # base for reqId (separado de orderId)
        self._end_events = {}  # reqId -> threading.Event
        self._events_lock = threading.Lock()
        self._lock_subs = threading.Lock()
        self._active_mktdata_req_ids: set[int] = set()
        self._active_rtb_req_ids: set[int] = set()
        self._active_subs: dict[str, dict[int, dict]] = {
            "mktdata": {},
            "rtbars": {}
        }
        self._hist_sem = threading.Semaphore(value=2)

    def _next_req_id(self):
        with self._id_lock:
            self._req_id += 1
            return self._req_id

    def _next_order_id(self):
        with self._id_lock:
            if self.next_valid_id is None:
                raise ConnectionError("Not connected: next_valid_id is not initialized.")
            oid = self.next_valid_id
            self.next_valid_id += 1
            return oid

    def reqMktData(self, reqId, contract, genericTickList, snapshot, regulatorySnapshot, mktDataOptions):
        super().reqMktData(reqId, contract, genericTickList, snapshot, regulatorySnapshot, mktDataOptions)
        with self._lock_subs:
            self._active_mktdata_req_ids.add(reqId)
            self._active_subs["mktdata"][reqId] = {
                "contract": contract,
                "genericTickList": genericTickList,
                "snapshot": snapshot,
                "regulatorySnapshot": regulatorySnapshot
            }

    def cancelMktData(self, reqId: int):
        super().cancelMktData(reqId)
        with self._lock_subs:
            if reqId in self._active_mktdata_req_ids:
                self._active_mktdata_req_ids.remove(reqId)
            if reqId in self._active_subs["mktdata"]:
                del self._active_subs["mktdata"][reqId]

    def reqRealTimeBars(self, reqId, contract, barSize, whatToShow, useRTH, realTimeBarsOptions):
        super().reqRealTimeBars(reqId, contract, barSize, whatToShow, useRTH, realTimeBarsOptions)
        with self._lock_subs:
            self._active_rtb_req_ids.add(reqId)
            self._active_subs["rtbars"][reqId] = {
                "contract": contract,
                "barSize": barSize,
                "whatToShow": whatToShow,
                "useRTH": useRTH,
                "realTimeBarsOptions": realTimeBarsOptions
            }

    def cancelRealTimeBars(self, reqId: int):
        super().cancelRealTimeBars(reqId)
        with self._lock_subs:
            if reqId in self._active_rtb_req_ids:
                self._active_rtb_req_ids.remove(reqId)
            if reqId in self._active_subs["rtbars"]:
                del self._active_subs["rtbars"][reqId]

    def nextValidId(self, orderId: int):
        super().nextValidId(orderId)
        self.next_valid_id = orderId
        self.is_connected = True
        logger.info(f"Connection successful. Next valid order ID: {orderId}")

    def error(self, reqId, errorCode, errorString):
        super().error(reqId, errorCode, errorString)
        friendly_message = IBKR_ERROR_MAP.get(errorCode, "Unknown IBKR error.")
        logger.error(f"IBKR Error. ReqId: {reqId}, Code: {errorCode}, Msg: {errorString}. Friendly: {friendly_message}")
        # Optionally raise a custom exception for critical errors
        # if errorCode in [162, 321]: # Example: raise for pacing/farm busy errors
        #    raise IBKRError(errorCode, friendly_message, errorString)

    def connectionClosed(self):
        super().connectionClosed()
        self.is_connected = False
        logger.warning("IBKR connection closed.")

    def _resubscribe_active(self):
        """Resubscribes to active market data and real-time bars after a reconnection."""
        mktdata_resubscribed = 0
        rtb_resubscribed = 0
        with self._lock_subs:
            # Resubscribe market data
            for reqId, params in list(self._active_subs["mktdata"].items()):
                try:
                    # Use the original reqId if possible, or generate a new one and update maps
                    # For simplicity, let's assume we can reuse reqId for now, or generate new ones if needed.
                    # If generating new reqIds, need to update self._active_mktdata_req_ids and self._active_subs
                    # For now, calling super().reqMktData directly to avoid re-adding to active_subs
                    super().reqMktData(reqId, params["contract"], params["genericTickList"], params["snapshot"], params["regulatorySnapshot"], [])
                    mktdata_resubscribed += 1
                except Exception as e:
                    logger.exception(f"Failed to resubscribe market data for reqId {reqId}: {e}")

            # Resubscribe real-time bars
            for reqId, params in list(self._active_subs["rtbars"].items()):
                try:
                    super().reqRealTimeBars(reqId, params["contract"], params["barSize"], params["whatToShow"], params["useRTH"], params["realTimeBarsOptions"])
                    rtb_resubscribed += 1
                except Exception as e:
                    logger.exception(f"Failed to resubscribe real-time bars for reqId {reqId}: {e}")
        logger.info(f"Resubscribed {mktdata_resubscribed} market data streams and {rtb_resubscribed} real-time bars streams.")

    def disconnect(self):
        # 1) Cancelar suscripciones RT activas
        mktdata_cancelled = 0
        rtb_cancelled = 0
        with self._lock_subs:
            for reqId in list(self._active_mktdata_req_ids):
                try:
                    super().cancelMktData(reqId)
                    mktdata_cancelled += 1
                except Exception as e:
                    logger.exception(f"Error cancelling market data subscription {reqId}: {e}")
            self._active_mktdata_req_ids.clear()
            self._active_subs["mktdata"].clear()

            for reqId in list(self._active_rtb_req_ids):
                try:
                    super().cancelRealTimeBars(reqId)
                    rtb_cancelled += 1
                except Exception as e:
                    logger.exception(f"Error cancelling real-time bars subscription {reqId}: {e}")
            self._active_rtb_req_ids.clear()
            self._active_subs["rtbars"].clear()

        logger.info(f"Cancelled {mktdata_cancelled} market data subscriptions and {rtb_cancelled} real-time bars subscriptions on disconnect.")
        # 2) Cancelar históricos pendientes si llevas registro (opcional)
        # (No se requiere aquí ya que get_historical_data ya maneja su propia cancelación)
        # 3) Llamar a EClient.disconnect()
        super().disconnect()

    def connect_and_run(self, host, port, clientId):
        self.connect(host, port, clientId)
        thread = threading.Thread(target=self.run)
        thread.daemon = True
        thread.start()
        
        # Wait for connection to be established
        for i in range(20):
            if self.is_connected:
                break
            time.sleep(0.5)
        
        if not self.is_connected:
            raise ConnectionError("Could not connect to IBKR.")
        try:
            self._resubscribe_active()
        except Exception as e:
            logger.exception("Failed to resubscribe active streams: %s", e)

    def get_response_queue(self, reqId):
        if reqId not in self.response_queues:
            self.response_queues[reqId] = Queue(maxsize=100)
        return self.response_queues[reqId]

    def wait_for_response(self, reqId, timeout=5):
        q = self.get_response_queue(reqId)
        try:
            return q.get(timeout=timeout)
        except Empty:
            raise TimeoutError(f"Timeout waiting for response for reqId: {reqId}")

    def historicalData(self, reqId, bar):
        self.get_response_queue(reqId).put(bar)

    def historicalDataEnd(self, reqId, start, end):
        super().historicalDataEnd(reqId, start, end)
        self.get_response_queue(reqId)  # ensure queue exists
        with self._events_lock:
            ev = self._end_events.get(reqId)
        if ev: ev.set()

    def get_historical_data(self, contract, endDateTime, durationStr, barSizeSetting,
                        whatToShow="TRADES", useRTH: int = 1, timeout=15.0):
        reqId = self._next_req_id()
        q = self.get_response_queue(reqId)
        bars = []
        done = threading.Event()
        with self._events_lock:
            self._end_events[reqId] = done

        acquired = self._hist_sem.acquire(timeout=timeout)
        if not acquired:
            raise TimeoutError("Historical semaphore acquire timeout")

        try:
            _pace_hist()
            self.reqHistoricalData(reqId, contract, endDateTime, durationStr,
                                   barSizeSetting, whatToShow, useRTH, 1, False, [])

            start_time = time.time()
            while True:
                if done.is_set(): break
                remaining = timeout - (time.time() - start_time)
                if remaining <= 0:
                    self.cancelHistoricalData(reqId)
                    raise TimeoutError(f"historicalData timeout for reqId={reqId}")
                try:
                    item = q.get(timeout=min(remaining, 0.25))
                    bars.append(item)
                except Empty:
                    pass
        finally:
            self._hist_sem.release()
            with self._events_lock:
                if reqId in self._end_events:
                    del self._end_events[reqId]
            # Drain the queue to prevent memory leaks
            while not q.empty():
                try:
                    q.get_nowait()
                except Empty:
                    break
        return bars

    def openOrder(self, orderId, contract, order, orderState):
        super().openOrder(orderId, contract, order, orderState)
        self.get_response_queue(orderId).put(order)

    def orderStatus(self, orderId, status, filled, remaining, avgFillPrice, permId, parentId, lastFillPrice, clientId, whyHeld, mktCapPrice):
        super().orderStatus(orderId, status, filled, remaining, avgFillPrice, permId, parentId, lastFillPrice, clientId, whyHeld, mktCapPrice)
        self.get_response_queue(orderId).put({
            "status": status,
            "filled": filled,
            "remaining": remaining,
            "avgFillPrice": avgFillPrice,
            "permId": permId,
        })

    def make_bracket_order(self, parentId: int, action: str, quantity: int, limitPrice: float, takeProfitPrice: float, stopLossPrice: float):
        from ibapi.order import Order
        parent = Order()
        parent.orderId = parentId
        parent.action = action
        parent.orderType = "LMT"
        parent.totalQuantity = quantity
        parent.lmtPrice = limitPrice
        parent.transmit = False

        takeProfit = Order()
        takeProfit.orderId = parent.orderId + 1
        takeProfit.action = "SELL" if action == "BUY" else "BUY"
        takeProfit.orderType = "LMT"
        takeProfit.totalQuantity = quantity
        takeProfit.lmtPrice = takeProfitPrice
        takeProfit.parentId = parentId
        takeProfit.transmit = False

        stopLoss = Order()
        stopLoss.orderId = parent.orderId + 2
        stopLoss.action = "SELL" if action == "BUY" else "BUY"
        stopLoss.orderType = "STP"
        stopLoss.auxPrice = stopLossPrice
        stopLoss.totalQuantity = quantity
        stopLoss.parentId = parentId
        stopLoss.transmit = True

        return [parent, takeProfit, stopLoss]

    def position(self, account, contract, pos, avgCost):
        super().position(account, contract, pos, avgCost)
        self.get_response_queue(self.next_valid_id).put({
            "account": account,
            "symbol": contract.symbol,
            "secType": contract.secType,
            "currency": contract.currency,
            "position": pos,
            "avgCost": avgCost,
        })

    def positionEnd(self):
        super().positionEnd()
        self.get_response_queue(self.next_valid_id).put(None)

    def get_positions_blocking(self, timeout=5.0):
        q = Queue()
        end_marker = object()

        # Define handlers as closures to capture the queue instance
        def position_handler(account, contract, pos, avgCost):
            q.put((account, contract, pos, avgCost))

        def position_end_handler():
            q.put(end_marker)

        # Temporarily hook the handlers
        original_position_handler = self.position
        original_position_end_handler = self.positionEnd
        self.position = position_handler
        self.positionEnd = position_end_handler
        
        positions = []
        try:
            self.reqPositions()
            start_time = time.time()
            while True:
                remaining = timeout - (time.time() - start_time)
                if remaining <= 0:
                    raise TimeoutError("Timeout waiting for position data.")
                
                try:
                    item = q.get(timeout=remaining)
                except Empty:
                    raise TimeoutError("Timeout waiting for position data.")

                if item is end_marker:
                    break
                
                _account, contract, pos, avg_cost = item
                positions.append({
                    "symbol": contract.symbol,
                    "asset_type": contract.secType,
                    "qty": pos,
                    "avg_price": avg_cost,
                    "unrealized_pnl": None, # Not directly available from position callback
                    "currency": contract.currency
                })
        finally:
            # Restore original handlers
            self.position = original_position_handler
            self.positionEnd = original_position_end_handler
            
        return positions

    def accountSummary(self, reqId, account, tag, value, currency):
        super().accountSummary(reqId, account, tag, value, currency)
        self.get_response_queue(reqId).put({
            "account": account,
            "tag": tag,
            "value": value,
            "currency": currency,
        })

    def accountSummaryEnd(self, reqId: int):
        super().accountSummaryEnd(reqId)
        self.get_response_queue(reqId).put(None)

    def get_account_summary(self, reqId, group, tags):
        self.reqAccountSummary(reqId, group, tags)
        
        summary = []
        while True:
            try:
                response = self.wait_for_response(reqId, timeout=5)
                if response is None:
                    break
                summary.append(response)
            except TimeoutError:
                logger.error("Timeout waiting for account summary")
                break
        return summary