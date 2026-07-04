from flask import Flask, render_template, jsonify, request
import yfinance as yf
import numpy as np
import requests
import json
import os
from datetime import datetime, timedelta
import traceback

app = Flask(__name__)

# ─────────────────────────────────────────────
# CONFIGURACIÓN — usa variables de entorno en Railway,
# fallback a valores hardcoded para uso local.
# ─────────────────────────────────────────────
FRED_API_KEY    = os.environ.get("FRED_API_KEY",    "TU_FRED_API_KEY")
FINNHUB_API_KEY = os.environ.get("FINNHUB_API_KEY", "TU_FINNHUB_API_KEY")
SHEETS_ID       = os.environ.get("SHEETS_ID",       "TU_GOOGLE_SHEETS_ID")
SHEETS_API_KEY  = os.environ.get("SHEETS_API_KEY",  "TU_GOOGLE_SHEETS_API_KEY")
CRON_SECRET     = os.environ.get("CRON_SECRET",     "smartvalue2026")

# ─────────────────────────────────────────────
# UNIVERSO GLOBAL ~500 EMPRESAS
# ─────────────────────────────────────────────
UNIVERSE = [
    # ── TECNOLOGÍA USA ──
    "AAPL","MSFT","GOOGL","META","AMZN","NVDA","AMD","INTC","ORCL","CRM",
    "ADBE","CSCO","QCOM","TXN","IBM","UBER","LYFT","SNAP","SHOP","TWLO",
    "NOW","INTU","PANW","SNPS","CDNS","FTNT","ANSS","ADSK","WDAY","TEAM",
    "ZS","CRWD","DDOG","NET","MDB","SNOW","PLTR","ROKU","PYPL","SQ",
    "ABNB","DASH","RBLX","U","PATH","HUBS","OKTA","DOCU","ZM","PINS",
    # ── SEMICONDUCTORES ──
    "AVGO","MU","LRCX","KLAC","AMAT","ADI","MRVL","ON","SWKS","QRVO",
    # ── FINANZAS USA ──
    "JPM","BAC","WFC","GS","MS","BLK","V","MA","AXP","COF",
    "C","USB","PNC","TFC","SCHW","CB","MMC","AON","ICE","CME",
    "SPGI","MCO","TRV","ALL","PGR","AIG","MET","PRU","AFL","FIS",
    # ── SALUD USA ──
    "JNJ","UNH","PFE","MRK","ABBV","BMY","LLY","AMGN","GILD","CVS",
    "MDT","SYK","ZBH","ISRG","REGN","VRTX","HUM","CI","ELV","HCA",
    "BSX","BDX","EW","IDXX","IQV","A","RMD","DXCM","ALGN","MRNA",
    # ── CONSUMO / RETAIL USA ──
    "WMT","TGT","COST","HD","LOW","MCD","SBUX","NKE","LULU","TJX",
    "PG","KO","PEP","PM","MO","CL","KMB","GIS","KHC","STZ",
    "EL","HSY","MNST","YUM","CMG","DG","DLTR","ROST","BBY","ORLY",
    # ── ENERGÍA / INDUSTRIAL USA ──
    "XOM","CVX","COP","SLB","PSX","MPC","VLO","OXY","WMB","KMI",
    "BA","CAT","HON","GE","MMM","UPS","FDX","LMT","RTX","NOC",
    "DE","EMR","ETN","ITW","PH","ROK","CMI","PCAR","GD","TDG",
    # ── COMUNICACIÓN / MEDIA USA ──
    "DIS","NFLX","CMCSA","T","VZ","TMUS","CHTR","WBD","EA","TTWO",
    # ── UTILITIES / REAL ESTATE USA ──
    "NEE","DUK","SO","D","AEP","EXC","XEL","ED","PEG","SRE",
    "AMT","PLD","CCI","EQIX","PSA","O","SPG","WELL","DLR","AVB",
    # ── MATERIALES USA ──
    "LIN","APD","SHW","ECL","FCX","NEM","DOW","DD","PPG","NUE",
    # ── EUROPA — UK ──
    "SHEL","AZN","HSBC","BP","GSK","RIO","CRH",
    "VOD","BARC",
    # ── EUROPA — Alemania ──
    "SAP","SIEGY","BAYRY","BMWYY","VWAGY","DTEGY","ALIZY","BASFY","DB","IFNNY",
    # ── EUROPA — Francia ──
    "TTE","LVMUY","ORAN","SAN","SNY","AIQUY","SGSOY","BNPQY","DANOY","EADSY",
    # ── EUROPA — Suiza ──
    "NESNY","RHHBY","UBS",
    # ── EUROPA — Países Bajos ──
    "ASML",
    # ── EUROPA — España / Italia ──
    "BBVA","TEF","ENI","STLA",
    # ── EUROPA — Nórdicos ──
    "NOVO-B.CO","ERIC",
    # ── ASIA — Japón ──
    "TM","SNE","HMC","NTDOY","MUFG","NTTYY","CAJ","MFG","SMFG","TAK",
    # ── ASIA — China / HK ──
    "BABA","JD","PDD","BIDU","NIO","XPEV","LI","TCEHY","NTES","BILI",
    # ── ASIA — Corea del Sur ──
    "005930.KS","000660.KS",
    # ── ASIA — Taiwan ──
    "TSM","UMC",
    # ── ASIA — India ──
    "INFY","WIT","HDB","IBN","TTM",
    # ── ASIA — Australia ──
    "BHP",
    # ── LATAM ──
    "MELI","NU","VALE","PBR","ITUB","BSBR","AMX","VIST","YPF","LOMA",
    "CEPU","GLOB","DESP","BBD","ABEV","GGB","CIB","BAP",
    "TGS","PAM","EDN","SUPV","BMA","IRS",
]

PEER_MAP = {
    "AAPL":["MSFT","GOOGL","META"],  "MSFT":["AAPL","GOOGL","ORCL"],
    "GOOGL":["META","MSFT","AAPL"],  "META":["GOOGL","SNAP","PINS"],
    "AMZN":["WMT","BABA","JD"],      "NVDA":["AMD","INTC","TSM"],
    "AMD":["NVDA","INTC","QCOM"],    "JPM":["BAC","GS","MS"],
    "BAC":["JPM","WFC","C"],         "GS":["MS","JPM","BLK"],
    "JNJ":["PFE","MRK","ABBV"],      "PFE":["MRK","JNJ","BMY"],
    "AZN":["GSK","RHHBY","NESNY"],   "XOM":["CVX","SHEL","TTE"],
    "BP":["SHEL","TTE","XOM"],       "ASML":["INTC","TSM","AMD"],
    "SAP":["ORCL","CRM","MSFT"],     "MELI":["AMZN","SHOP","NU"],
    "VALE":["BHP","RIO","XOM"],      "YPF":["PBR","XOM","CVX"],
    "GLOB":["INFY","WIT","MSFT"],    "BABA":["JD","PDD","AMZN"],
    "TSM":["NVDA","INTC","ASML"],    "TM":["HMC","VWAGY","BMWYY"],
}
DEFAULT_PEERS = ["MSFT","GOOGL","AAPL"]

# ─────────────────────────────────────────────
# HELPERS FINANCIEROS
# ─────────────────────────────────────────────

def get_risk_free_rate():
    try:
        url = f"https://api.stlouisfed.org/fred/series/observations?series_id=DGS10&api_key={FRED_API_KEY}&file_type=json&limit=1&sort_order=desc"
        r = requests.get(url, timeout=5)
        return float(r.json()["observations"][0]["value"]) / 100
    except:
        return 0.045

def get_market_return():
    try:
        sp = yf.Ticker("^GSPC")
        hist = sp.history(period="5y")
        total = (hist["Close"].iloc[-1] / hist["Close"].iloc[0]) - 1
        return (1 + total) ** (1/5) - 1
    except:
        return 0.10

def calculate_wacc(info, rf, rm):
    try:
        beta = info.get("beta", 1.0) or 1.0
        ke   = rf + beta * (rm - rf)
        total_debt = info.get("totalDebt", 0) or 0
        market_cap = info.get("marketCap", 1) or 1
        tax_rate   = info.get("effectiveTaxRate", 0.25) or 0.25
        interest   = abs(info.get("interestExpense", 0) or 0)
        kd = (interest / total_debt * (1 - tax_rate)) if total_debt > 0 else 0.04
        total_cap  = market_cap + total_debt
        wacc = (market_cap/total_cap)*ke + (total_debt/total_cap)*kd
        return max(wacc, 0.07), ke, kd, beta
    except:
        return 0.10, 0.12, 0.04, 1.0

def calculate_fcff(ticker_obj):
    try:
        cf  = ticker_obj.cashflow
        inc = ticker_obj.financials
        bal = ticker_obj.balance_sheet
        ebit = float(inc.loc["EBIT"].iloc[0]) if "EBIT" in inc.index else float(inc.loc["Operating Income"].iloc[0])
        tax_rate = 0.25
        try:
            tax    = float(inc.loc["Tax Provision"].iloc[0])
            pretax = float(inc.loc["Pretax Income"].iloc[0])
            tax_rate = tax / pretax if pretax != 0 else 0.25
        except: pass
        da = 0
        for lbl in ["Depreciation And Amortization","Depreciation","Reconciled Depreciation"]:
            if lbl in cf.index: da = abs(float(cf.loc[lbl].iloc[0])); break
        capex = 0
        for lbl in ["Capital Expenditure","Purchase Of PPE"]:
            if lbl in cf.index: capex = abs(float(cf.loc[lbl].iloc[0])); break
        delta_wc = 0
        try:
            ca_c = float(bal.loc["Current Assets"].iloc[0]); ca_p = float(bal.loc["Current Assets"].iloc[1])
            cl_c = float(bal.loc["Current Liabilities"].iloc[0]); cl_p = float(bal.loc["Current Liabilities"].iloc[1])
            delta_wc = (ca_c - cl_c) - (ca_p - cl_p)
        except: pass
        return ebit*(1-tax_rate) + da - capex - delta_wc, ebit, da, capex, tax_rate
    except:
        return None, None, None, None, None

def dcf_valuation(ticker_obj, info, wacc):
    try:
        fcff, *_ = calculate_fcff(ticker_obj)
        if fcff is None: return None, [], None
        shares     = info.get("sharesOutstanding", 1) or 1
        total_debt = info.get("totalDebt", 0) or 0
        cash       = info.get("totalCash", 0) or 0
        g_short    = min(max(info.get("revenueGrowth", 0.08) or 0.08, 0.02), 0.20)
        g_terminal = 0.025
        projected  = []
        cf = fcff
        for _ in range(5):
            cf = cf*(1+g_short); projected.append(cf)
        tv    = projected[-1]*(1+g_terminal)/(wacc-g_terminal)
        pv    = sum([f/(1+wacc)**i for i,f in enumerate(projected,1)])
        pv_tv = tv/(1+wacc)**5
        return (pv + pv_tv - total_debt + cash)/shares, projected, g_short
    except:
        return None, [], None

def multiples_valuation(symbol, info, peer_list):
    try:
        ebitda   = info.get("ebitda", None)
        earnings = info.get("trailingEps", None)
        shares   = info.get("sharesOutstanding", 1) or 1
        total_debt = info.get("totalDebt", 0) or 0
        cash     = info.get("totalCash", 0) or 0
        peer_evs, peer_pes = [], []
        for peer in peer_list:
            try:
                pi = yf.Ticker(peer).info
                ev = pi.get("enterpriseToEbitda", None)
                pe = pi.get("trailingPE", None)
                if ev and 0 < ev < 100: peer_evs.append(ev)
                if pe and 0 < pe < 100: peer_pes.append(pe)
            except: pass
        val_ev, val_pe = None, None
        if peer_evs and ebitda:
            val_ev = (np.mean(peer_evs)*ebitda - total_debt + cash) / shares
        if peer_pes and earnings:
            val_pe = np.mean(peer_pes)*earnings
        if val_ev and val_pe: final = (val_ev+val_pe)/2
        elif val_ev: final = val_ev
        elif val_pe: final = val_pe
        else: final = None
        return final, round(np.mean(peer_evs),2) if peer_evs else None, round(np.mean(peer_pes),2) if peer_pes else None
    except:
        return None, None, None

def greenblatt_score(info, fx_divisor=1.0):
    try:
        ebit   = (info.get("ebitda", 0) or 0) * fx_divisor * 0.85
        ev     = info.get("enterpriseValue", 1) or 1
        assets = (info.get("totalAssets", 1) or 1) * fx_divisor
        liab   = (info.get("totalLiab", 0) or 0) * fx_divisor
        ey  = max(min(ebit/ev if ev else 0, 1.0), -1.0)
        cap = assets - liab
        roc = max(min(ebit/cap if cap > 0 else 0, 5.0), -1.0)
        score = (min(ey*100, 30)/30*50) + (min(roc*100, 50)/50*50)
        return round(score,1), round(ey*100,2), round(min(roc*100, 99.99),2)
    except:
        return 0, 0, 0

def quality_score(info):
    try:
        score, details = 0, {}
        roe = (info.get("returnOnEquity", 0) or 0)*100
        details["roe"] = round(roe,1)
        if roe > 20: score += 25
        elif roe > 15: score += 18
        elif roe > 10: score += 10
        margin = (info.get("profitMargins", 0) or 0)*100
        details["net_margin"] = round(margin,1)
        if margin > 20: score += 25
        elif margin > 10: score += 15
        elif margin > 5: score += 8
        debt   = info.get("totalDebt", 0) or 0
        ebitda = info.get("ebitda", 1) or 1
        d_eb   = debt/ebitda if ebitda > 0 else 999
        details["debt_ebitda"] = round(d_eb,2)
        if d_eb < 1: score += 25
        elif d_eb < 2: score += 18
        elif d_eb < 3: score += 10
        fcf   = info.get("freeCashflow", 0) or 0
        mkt   = info.get("marketCap", 1) or 1
        fcf_y = (fcf/mkt)*100
        details["fcf_yield"] = round(fcf_y,1)
        if fcf_y > 5: score += 25
        elif fcf_y > 3: score += 18
        elif fcf_y > 1: score += 10
        return round(score,1), details
    except:
        return 0, {}

def momentum_score(ticker_obj):
    try:
        hist  = ticker_obj.history(period="1y")
        if hist.empty: return 0, {}
        price = hist["Close"].iloc[-1]
        ma50  = hist["Close"].tail(50).mean()
        ma200 = hist["Close"].mean()
        ret6m = (price/hist["Close"].iloc[-126]-1)*100 if len(hist)>=126 else 0
        score = 0
        if price > ma200: score += 35
        if price > ma50:  score += 35
        if ret6m > 0:     score += 30
        return round(score,1), {"price":round(price,2),"ma50":round(ma50,2),"ma200":round(ma200,2),"ret_6m":round(ret6m,1)}
    except:
        return 0, {}

def get_news_sentiment(ticker_symbol):
    import xml.etree.ElementTree as ET
    pos_words = ["beat","growth","strong","record","surge","up","gain","profit","bullish","buy","upgrade","outperform","rally","soar","jump"]
    neg_words = ["miss","decline","weak","drop","fall","loss","bearish","sell","downgrade","underperform","concern","risk","slump","plunge","cut"]
    headlines = []
    if FINNHUB_API_KEY and FINNHUB_API_KEY != "TU_FINNHUB_API_KEY":
        try:
            end   = datetime.now().strftime("%Y-%m-%d")
            start = (datetime.now()-timedelta(days=7)).strftime("%Y-%m-%d")
            url   = f"https://finnhub.io/api/v1/company-news?symbol={ticker_symbol}&from={start}&to={end}&token={FINNHUB_API_KEY}"
            r     = requests.get(url, timeout=5)
            news  = r.json()
            if news and isinstance(news, list):
                for a in news[:10]:
                    headlines.append({"title":a.get("headline",""),"url":a.get("url","")})
        except: pass
    if not headlines:
        try:
            rss  = f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={ticker_symbol}&region=US&lang=en-US"
            r    = requests.get(rss, timeout=8, headers={"User-Agent":"Mozilla/5.0"})
            root = ET.fromstring(r.content)
            for item in root.findall(".//item")[:10]:
                t = item.find("title"); l = item.find("link")
                if t is not None and t.text:
                    headlines.append({"title":t.text.strip(),"url":l.text.strip() if l is not None else ""})
        except: pass
    if not headlines: return 50, []
    pos = neg = 0
    for h in headlines:
        title = h["title"].lower()
        pos += sum(1 for w in pos_words if w in title)
        neg += sum(1 for w in neg_words if w in title)
    total = pos+neg
    return int(pos/total*100) if total > 0 else 50, headlines[:5]

def analyst_consensus(ticker_symbol):
    if FINNHUB_API_KEY and FINNHUB_API_KEY != "TU_FINNHUB_API_KEY":
        try:
            url  = f"https://finnhub.io/api/v1/stock/recommendation?symbol={ticker_symbol}&token={FINNHUB_API_KEY}"
            data = requests.get(url, timeout=5).json()
            if data and isinstance(data, list):
                latest = data[0]
                buy  = latest.get("buy",0) + latest.get("strongBuy",0)
                hold = latest.get("hold",0)
                sell = latest.get("sell",0) + latest.get("strongSell",0)
                if buy+hold+sell > 0:
                    return {"buy":buy,"hold":hold,"sell":sell}
        except: pass
    try:
        ud = yf.Ticker(ticker_symbol).upgrades_downgrades
        if ud is not None and not ud.empty:
            recent = ud.head(20)
            buy  = int((recent["Action"].str.lower().isin(["buy","upgrade","overweight","outperform"])).sum())
            sell = int((recent["Action"].str.lower().isin(["sell","downgrade","underweight","underperform"])).sum())
            hold = int((recent["Action"].str.lower().isin(["hold","neutral","maintain"])).sum())
            if buy+hold+sell > 0:
                return {"buy":buy,"hold":hold,"sell":sell}
    except: pass
    return None

def sanitize_nan(obj):
    if isinstance(obj, dict):   return {k: sanitize_nan(v) for k,v in obj.items()}
    elif isinstance(obj, list): return [sanitize_nan(v) for v in obj]
    elif isinstance(obj, float):
        if obj != obj or obj == float('inf') or obj == float('-inf'): return None
        return obj
    return obj

def get_currency_divisor(info):
    currency = info.get("financialCurrency","USD") or "USD"
    if currency == "USD": return 1.0
    try:
        fx   = yf.Ticker(f"{currency}USD=X")
        rate = fx.info.get("regularMarketPrice")
        if not rate:
            hist = fx.history(period="2d")
            rate = float(hist["Close"].iloc[-1]) if not hist.empty else None
        return float(rate) if rate else 1.0
    except:
        fallbacks = {"ARS":0.001,"BRL":0.18,"MXN":0.05,"JPY":0.0065,"KRW":0.00073,
                     "INR":0.012,"CNY":0.138,"GBP":1.27,"EUR":1.08,"CHF":1.12,"AUD":0.65,"CAD":0.73}
        return fallbacks.get(currency, 1.0)

def compute_final_score(dcf_upside, mult_upside, gb_score, qual_score, mom_score, sentiment):
    dcf_pts = 0
    if dcf_upside is not None:
        if dcf_upside > 30: dcf_pts = 25
        elif dcf_upside > 20: dcf_pts = 20
        elif dcf_upside > 10: dcf_pts = 15
        elif dcf_upside > 0:  dcf_pts = 8
    mult_pts = 0
    if mult_upside is not None:
        if mult_upside > 25: mult_pts = 20
        elif mult_upside > 15: mult_pts = 15
        elif mult_upside > 5:  mult_pts = 10
        elif mult_upside > 0:  mult_pts = 5
    return round(min(dcf_pts + mult_pts + gb_score*0.20 + qual_score*0.15 + mom_score*0.10 + sentiment*0.10, 100), 1)

def get_recommendation(score, dcf_upside):
    if score >= 75 and (dcf_upside or 0) > 20: return "STRONG BUY", "#00d26a"
    elif score >= 60: return "BUY", "#4ade80"
    elif score >= 45: return "HOLD", "#facc15"
    elif score >= 30: return "UNDERPERFORM", "#fb923c"
    else: return "SELL", "#f87171"

# ─────────────────────────────────────────────
# GOOGLE SHEETS — LECTURA
# ─────────────────────────────────────────────

def read_top5_from_sheets():
    try:
        url  = (f"https://sheets.googleapis.com/v4/spreadsheets/{SHEETS_ID}"
                f"/values/Top5!A2:J6?key={SHEETS_API_KEY}")
        rows = requests.get(url, timeout=5).json().get("values", [])
        if not rows: return None, "Sheet vacío"

        def pf(s, default=0):
            try: return float(str(s).replace(",","."))
            except: return default

        return [{
            "symbol":         row[0],
            "name":           row[1],
            "sector":         row[2],
            "current_price":  pf(row[3]),
            "dcf_upside":     pf(row[4], None),
            "final_score":    pf(row[5]),
            "recommendation": row[6],
            "rec_color":      row[7],
            "sentiment":      pf(row[8], 50),
            "updated_at":     row[9] if len(row) > 9 else "",
        } for row in rows if len(row) >= 9], None
    except Exception as e:
        return None, str(e)

# ─────────────────────────────────────────────
# ANÁLISIS COMPLETO DE UN TICKER
# ─────────────────────────────────────────────

def analyze_ticker(symbol):
    symbol = symbol.upper().strip()
    t    = yf.Ticker(symbol)
    info = t.info
    if not info or "symbol" not in info:
        return {"error": f"No se encontró información para {symbol}"}

    fx     = get_currency_divisor(info)
    rf     = get_risk_free_rate()
    rm     = get_market_return()
    wacc, ke, kd, beta = calculate_wacc(info, rf, rm)
    peers  = PEER_MAP.get(symbol, DEFAULT_PEERS)

    dcf_value, projected_fcff, g_short = dcf_valuation(t, info, wacc)
    mult_value, avg_ev_ebitda, avg_pe   = multiples_valuation(symbol, info, peers)
    current_price = info.get("currentPrice") or info.get("regularMarketPrice", 0)

    if dcf_value:  dcf_value  *= fx
    if mult_value: mult_value *= fx

    dcf_upside  = ((dcf_value  - current_price)/current_price*100) if dcf_value  and current_price else None
    mult_upside = ((mult_value - current_price)/current_price*100) if mult_value and current_price else None

    gb_score, earnings_yield, roc = greenblatt_score(info, fx)
    qual, qual_details            = quality_score(info)
    mom, mom_details              = momentum_score(t)
    sentiment, headlines          = get_news_sentiment(symbol)
    consensus                     = analyst_consensus(symbol)
    final_score                   = compute_final_score(dcf_upside, mult_upside, gb_score, qual, mom, sentiment)
    recommendation, rec_color     = get_recommendation(final_score, dcf_upside)

    hist = t.history(period="1y")
    price_history = {
        "dates":  [str(d.date()) for d in hist.index[-252:]],
        "prices": [round(p,2) for p in hist["Close"].values[-252:]]
    }

    return sanitize_nan({
        "symbol": symbol, "name": info.get("longName",symbol),
        "sector": info.get("sector","N/A"), "industry": info.get("industry","N/A"),
        "current_price": round(current_price,2),
        "dcf_value":  round(dcf_value,2)  if dcf_value  else None,
        "mult_value": round(mult_value,2) if mult_value else None,
        "dcf_upside":  round(dcf_upside,1)  if dcf_upside  else None,
        "mult_upside": round(mult_upside,1) if mult_upside else None,
        "wacc": round(wacc*100,2), "ke": round(ke*100,2),
        "beta": round(beta,2), "rf": round(rf*100,2),
        "g_short": round((g_short or 0.08)*100,1),
        "projected_fcff": [round(f*fx/1e9,2) for f in (projected_fcff or [])],
        "financial_currency": info.get("financialCurrency","USD") or "USD",
        "gb_score": gb_score, "earnings_yield": earnings_yield, "roc": roc,
        "avg_ev_ebitda": avg_ev_ebitda, "avg_pe": avg_pe,
        "quality_score": qual, "quality_details": qual_details,
        "momentum_score": mom, "momentum_details": mom_details,
        "sentiment": sentiment, "headlines": headlines, "consensus": consensus,
        "final_score": final_score, "recommendation": recommendation, "rec_color": rec_color,
        "price_history": price_history,
        "market_cap": info.get("marketCap",0),
        "pe_ratio": info.get("trailingPE",None),
        "ev_ebitda": info.get("enterpriseToEbitda",None),
        "revenue_growth": round((info.get("revenueGrowth",0) or 0)*100,1),
        "ebitda": info.get("ebitda",None), "peers": peers,
    })

# ─────────────────────────────────────────────
# SCREENER FALLBACK
# ─────────────────────────────────────────────

def run_screener_live():
    results = []
    for sym in UNIVERSE:
        try:
            data = analyze_ticker(sym)
            if "error" not in data and data["final_score"] > 0:
                results.append({
                    "symbol": data["symbol"], "name": data["name"],
                    "sector": data["sector"], "current_price": data["current_price"],
                    "dcf_upside": data["dcf_upside"], "final_score": data["final_score"],
                    "recommendation": data["recommendation"], "rec_color": data["rec_color"],
                    "sentiment": data["sentiment"],
                })
        except: continue
    results.sort(key=lambda x: x["final_score"], reverse=True)
    return sanitize_nan(results[:5])

# ─────────────────────────────────────────────
# RUTAS FLASK
# ─────────────────────────────────────────────

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/api/search/<query>")
def api_search(query):
    try:
        url    = f"https://query2.finance.yahoo.com/v1/finance/search?q={query}&lang=en-US&region=US&quotesCount=8&newsCount=0"
        quotes = requests.get(url, timeout=5, headers={"User-Agent":"Mozilla/5.0"}).json().get("quotes",[])
        return jsonify({"success":True, "data":[
            {"symbol":q.get("symbol",""), "name":q.get("longname") or q.get("shortname",""),
             "exchange":q.get("exchDisp",""), "type":q.get("quoteType","")}
            for q in quotes if q.get("quoteType") in ("EQUITY","ETF")
        ]})
    except:
        return jsonify({"success":False, "data":[]})

@app.route("/api/screener")
def api_screener():
    try:
        if SHEETS_ID != "TU_GOOGLE_SHEETS_ID" and SHEETS_API_KEY != "TU_GOOGLE_SHEETS_API_KEY":
            top5, err = read_top5_from_sheets()
            if top5:
                return jsonify({"success":True, "data":top5, "source":"sheets"})
            print(f"[Sheets] {err} — usando screener en vivo")
        return jsonify({"success":True, "data":run_screener_live(), "source":"live"})
    except Exception as e:
        return jsonify({"success":False, "error":str(e)}), 500

@app.route("/api/analyze/<symbol>")
def api_analyze(symbol):
    try:
        return jsonify({"success":True, "data":analyze_ticker(symbol)})
    except Exception as e:
        return jsonify({"success":False, "error":str(e), "trace":traceback.format_exc()}), 500

@app.route("/api/update-screener", methods=["GET","POST"])
def api_update_screener():
    if request.args.get("secret","") != CRON_SECRET:
        return jsonify({"success":False, "error":"unauthorized"}), 401
    try:
        import threading
        from update_screener import run_full_update
        thread = threading.Thread(target=run_full_update, daemon=True)
        thread.start()
        return jsonify({"success":True, "message":"Screener iniciado en background"})
    except Exception as e:
        return jsonify({"success":False, "error":str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host="0.0.0.0", port=port)
