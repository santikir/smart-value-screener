"""
update_screener.py
──────────────────
Corre el screener completo (~500 empresas) y guarda el Top 5 en Google Sheets.

Uso local:    python3 update_screener.py
En Railway:   se llama automáticamente vía /api/update-screener
"""

import os, json
import time
import yfinance as yf
from datetime import datetime


def get_credentials():
    from google.oauth2 import service_account
    env_creds = os.environ.get("GOOGLE_CREDENTIALS_JSON")
    if env_creds:
        return service_account.Credentials.from_service_account_info(
            json.loads(env_creds),
            scopes=["https://www.googleapis.com/auth/spreadsheets"]
        )
    if os.path.exists("credentials.json"):
        return service_account.Credentials.from_service_account_file(
            "credentials.json",
            scopes=["https://www.googleapis.com/auth/spreadsheets"]
        )
    raise FileNotFoundError("No se encontraron credenciales de Google.")


def write_to_sheets(top5, sheets_id):
    try:
        from googleapiclient.discovery import build
        service = build("sheets", "v4", credentials=get_credentials())
        now     = datetime.now().strftime("%Y-%m-%d %H:%M")
        values  = [[
            d.get("symbol",""), d.get("name",""), d.get("sector",""),
            d.get("current_price",""), d.get("dcf_upside",""),
            d.get("final_score",""), d.get("recommendation",""),
            d.get("rec_color",""), d.get("sentiment",""), now,
        ] for d in top5]
        service.spreadsheets().values().update(
            spreadsheetId=sheets_id,
            range="Top5!A2:J6",
            valueInputOption="RAW",
            body={"values": values}
        ).execute()
        print(f"✅ Top 5 guardado en Google Sheets ({now})")
        return True
    except ImportError:
        print("❌ Faltan librerías: pip3 install google-auth google-api-python-client")
        return False
    except Exception as e:
        print(f"❌ Error escribiendo en Sheets: {e}")
        return False


def run_full_update():
    from app import UNIVERSE, SHEETS_ID, analyze_ticker, sanitize_nan
    import time

    print("=" * 60)
    print(f"  SMART VALUE SCREENER — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Analizando {len(UNIVERSE)} empresas...")
    print("=" * 60)

    results, errors = [], []

    for i, sym in enumerate(UNIVERSE, 1):
        # Delay progresivo para evitar rate limit
        if i % 10 == 0:
            time.sleep(30)  # pausa larga cada 10 empresas
        else:
            time.sleep(3)
        try:
            print(f"  [{i:3d}/{len(UNIVERSE)}] {sym:<14}", end="", flush=True)
            data = analyze_ticker(sym)
            if "error" in data:
                print(f"⚠️  sin datos")
                errors.append(sym)
                continue
            print(f"Score: {data['final_score']:5.1f}  {data['recommendation']}")
            results.append({
                "symbol":         data["symbol"],
                "name":           data["name"],
                "sector":         data["sector"],
                "current_price":  data["current_price"],
                "dcf_upside":     data["dcf_upside"],
                "final_score":    data["final_score"],
                "recommendation": data["recommendation"],
                "rec_color":      data["rec_color"],
                "sentiment":      data["sentiment"],
            })
            import time
            time.sleep(1.5)  # esperar 1.5 segundos entre empresas
        except Exception as e:
            print(f"❌ {e}")
            errors.append(sym)

    results = sanitize_nan(results)
    results.sort(key=lambda x: x["final_score"] or 0, reverse=True)
    top5 = results[:5]

    print("\n" + "=" * 60)
    print("  TOP 5 OPORTUNIDADES")
    print("=" * 60)
    for i, d in enumerate(top5, 1):
        upside = f"+{d['dcf_upside']:.1f}%" if d.get("dcf_upside") else "N/A"
        print(f"  #{i}  {d['symbol']:<10}  Score: {d['final_score']:5.1f}  Upside: {upside}  {d['recommendation']}")
    print(f"\n  Errores: {len(errors)}/{len(UNIVERSE)} tickers")

    ok = write_to_sheets(top5, SHEETS_ID)
    if not ok:
        with open("top5_backup.json", "w") as f:
            json.dump(top5, f, indent=2)
        print("💾 Backup guardado en top5_backup.json")

    return {"analyzed": len(UNIVERSE), "errors": len(errors), "top5": top5, "sheets_updated": ok}


if __name__ == "__main__":
    run_full_update()
    print("\n✅ Listo.")
