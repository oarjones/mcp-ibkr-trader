from ibapi.contract import Contract
from functools import lru_cache
from datetime import datetime

@lru_cache(maxsize=None)
def resolve_contract(symbol: str, asset_type: str, contract_month: str = None, use_crypto_sec_type: bool = True) -> Contract:
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
        if contract_month:
            contract.lastTradeDateOrContractMonth = contract_month
        else:
            # Default to next month if not provided
            now = datetime.now()
            year = now.year
            month = now.month + 1
            if month > 12:
                month = 1
                year += 1
            contract.lastTradeDateOrContractMonth = f"{year}{month:02d}"
    elif asset_type == "CRYPTO":
        if use_crypto_sec_type:
            contract.secType = "CRYPTO"
            contract.exchange = "PAXOS"
            contract.symbol = symbol
        else:
            contract.secType = "CASH"
            contract.exchange = "PAXOS"
            if '.' in symbol:
                parts = symbol.split('.')
                contract.symbol = parts[0]
                contract.currency = parts[1]
            else:
                contract.symbol = symbol
                contract.currency = "USD"
    else:
        raise ValueError(f"Unsupported asset type: {asset_type}")

    return contract
