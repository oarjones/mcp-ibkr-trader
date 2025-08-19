import threading
import time
from queue import Queue, Empty
from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from loguru import logger

class TWSClient(EWrapper, EClient):
    def __init__(self):
        EClient.__init__(self, self)
        self.response_queues = {}
        self.next_valid_id = None
        self.is_connected = False

    def nextValidId(self, orderId: int):
        super().nextValidId(orderId)
        self.next_valid_id = orderId
        self.is_connected = True
        logger.info(f"Connection successful. Next valid order ID: {orderId}")

    def error(self, reqId, errorCode, errorString):
        super().error(reqId, errorCode, errorString)
        logger.error(f"IBKR Error. ReqId: {reqId}, Code: {errorCode}, Msg: {errorString}")

    def connectionClosed(self):
        super().connectionClosed()
        self.is_connected = False
        logger.warning("IBKR connection closed.")

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

    def get_response_queue(self, reqId):
        if reqId not in self.response_queues:
            self.response_queues[reqId] = Queue()
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
        self.get_response_queue(reqId).put(None) # Signal end of data

    def get_historical_data(self, reqId, contract, endDateTime, durationStr, barSizeSetting, whatToShow, useRTH):
        self.reqHistoricalData(
            reqId,
            contract,
            endDateTime,
            durationStr,
            barSizeSetting,
            whatToShow,
            useRTH,
            1,
            False,
            []
        )
        
        bars = []
        while True:
            try:
                response = self.wait_for_response(reqId, timeout=10)
                if response is None:
                    break
                bars.append(response)
            except TimeoutError:
                logger.error(f"Timeout waiting for historical data for reqId: {reqId}")
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

    def make_bracket_order(self, parentOrderId, action, quantity, limitPrice, takeProfitPrice, stopLossPrice):
        from ibapi.order import Order
        parent = Order()
        parent.orderId = parentOrderId
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
        takeProfit.parentId = parentOrderId
        takeProfit.transmit = False

        stopLoss = Order()
        stopLoss.orderId = parent.orderId + 2
        stopLoss.action = "SELL" if action == "BUY" else "BUY"
        stopLoss.orderType = "STP"
        stopLoss.auxPrice = stopLossPrice
        stopLoss.totalQuantity = quantity
        stopLoss.parentId = parentOrderId
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

    def get_positions(self):
        self.reqPositions()
        
        positions = []
        while True:
            try:
                response = self.wait_for_response(self.next_valid_id, timeout=5)
                if response is None:
                    break
                positions.append(response)
            except TimeoutError:
                logger.error("Timeout waiting for positions")
                break
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
