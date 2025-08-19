from ibapi.contract import Contract
from functools import lru_cache

@lru_cache(maxsize=None)
def resolve_contract(symbol: str, asset_type: str) -> Contract:
    """
    Resolves a symbol and asset type to an IBKR contract.
    """
    contract = Contract()
    contract.currency = "USD"

    if asset_type == "STK":
        contract.secType = "STK"
        contract.exchange = "SMART"
        contract.symbol = symbol
    elif asset_type == "FX":
        contract.secType = "CASH"
        contract.exchange = "IDEALPRO"
        contract.symbol = symbol.split('.')[0]
        contract.currency = symbol.split('.')[1]
    elif asset_type == "FUT":
        contract.secType = "FUT"
        contract.exchange = "CME"
        contract.symbol = symbol
        contract.lastTradeDateOrContractMonth = "202509" # This should be dynamic
    elif asset_type == "CRYPTO":
        contract.secType = "CRYPTO"
        contract.exchange = "PAXOS"
        contract.symbol = symbol
    else:
        raise ValueError(f"Unsupported asset type: {asset_type}")

    return contract
