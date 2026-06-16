import json
import os
import pandas as pd
from datetime import datetime

PORTFOLIO_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'portfolio.json')

def load_portfolio():
    """포트폴리오 데이터를 로컬 JSON에서 불러옵니다."""
    if not os.path.exists(PORTFOLIO_FILE):
        return {"holdings": [], "peaks": {}}
    try:
        with open(PORTFOLIO_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading portfolio: {e}")
        return {"holdings": [], "peaks": {}}

def save_portfolio(data):
    """포트폴리오 데이터를 로컬 JSON에 저장합니다."""
    # Ensure data directory exists
    os.makedirs(os.path.dirname(PORTFOLIO_FILE), exist_ok=True)
    try:
        with open(PORTFOLIO_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error saving portfolio: {e}")

def add_holding(ticker, name, shares, avg_price, account="보유"):
    data = load_portfolio()
    holdings = data.get("holdings", [])
    
    # Check if exists in the same account
    existing = next((item for item in holdings if item['ticker'] == ticker and item['account'] == account), None)
    if existing:
        # Update existing
        total_shares = existing['shares'] + shares
        if total_shares > 0:
            existing['avg_price'] = ((existing['avg_price'] * existing['shares']) + (avg_price * shares)) / total_shares
            existing['shares'] = total_shares
        else:
            # If shares become 0 or less, remove it
            holdings.remove(existing)
    else:
        if shares > 0:
            holdings.append({
                "ticker": ticker,
                "name": name,
                "shares": shares,
                "avg_price": avg_price,
                "account": account,
                "buy_date": datetime.now().strftime("%Y-%m-%d")
            })
    
    data["holdings"] = holdings
    save_portfolio(data)

def remove_holding(ticker, account="보유"):
    data = load_portfolio()
    holdings = [h for h in data.get("holdings", []) if not (h['ticker'] == ticker and h['account'] == account)]
    data["holdings"] = holdings
    save_portfolio(data)

def update_peak(ticker, current_price):
    data = load_portfolio()
    peaks = data.get("peaks", {})
    if ticker not in peaks or current_price > peaks.get(ticker, 0):
        peaks[ticker] = current_price
        data["peaks"] = peaks
        save_portfolio(data)

def get_holdings_df():
    data = load_portfolio()
    holdings = data.get("holdings", [])
    if not holdings:
        return pd.DataFrame()
    return pd.DataFrame(holdings)

def get_peaks():
    data = load_portfolio()
    return data.get("peaks", {})
