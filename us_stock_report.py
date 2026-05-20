"""
美股数据采集（Phase 1）
=====================
基于 yfinance 采集美股全维度数据，输出 JSON 供 Phase 2/3 使用。
使用 ThreadPoolExecutor 并发采集，预计 30-60 秒完成。

用法
  python us_stock_report.py AAPL
  python us_stock_report.py TSLA --max-kline-years 5

输出
  output/data_{TICKER}.json
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Any, Callable

import pandas as pd

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

try:
    import yfinance as yf
except ImportError:
    print("[X] 未安装 yfinance，请先 pip install yfinance --upgrade", file=sys.stderr)
    sys.exit(1)


# ============================================================
#  通用工具
# ============================================================

def _safe_call(fn: Callable, *args, retries: int = 1, label: str = "", **kwargs) -> Any:
    backoff = (0.3, 1.0)
    for attempt in range(retries + 1):
        try:
            t0 = time.perf_counter()
            res = fn(*args, **kwargs)
            elapsed = time.perf_counter() - t0
            if isinstance(res, pd.DataFrame):
                rows = len(res)
            elif isinstance(res, dict):
                rows = len(res)
            elif isinstance(res, list):
                rows = len(res)
            else:
                rows = "?"
            print(f"  ✓ {label:45s} {rows} 行 · {elapsed:.1f}s")
            return res
        except Exception as e:
            err_brief = f"{type(e).__name__}: {e}"[:90]
            if attempt < retries:
                time.sleep(backoff[min(attempt, len(backoff) - 1)])
                continue
            print(f"  ✗ {label:45s} {err_brief}")
            return None


def _df_to_records(df: pd.DataFrame | None, max_rows: int | None = None) -> list[dict]:
    if df is None or (isinstance(df, pd.DataFrame) and df.empty):
        return []
    out = df.head(max_rows) if max_rows else df
    out = out.copy()
    out = out.reset_index()
    for c in out.columns:
        if pd.api.types.is_datetime64_any_dtype(out[c]):
            out[c] = out[c].dt.strftime("%Y-%m-%d").where(out[c].notna(), None)
    records = json.loads(out.to_json(orient="records", force_ascii=False, date_format="iso"))
    for row in records:
        for k, v in list(row.items()):
            if isinstance(v, (dict, list)):
                row[k] = str(v)[:120]
    return records


def _dict_to_records(d: dict | None) -> list[dict]:
    if d is None:
        return []
    if isinstance(d, dict):
        return [{"key": str(k), "value": str(v)[:200]} for k, v in d.items() if v is not None]
    return []


def _info_to_records(info: dict | None) -> list[dict]:
    if info is None:
        return []
    key_fields = [
        "shortName", "longName", "symbol", "exchange", "quoteType",
        "sector", "industry", "country", "website", "fullTimeEmployees",
        "marketCap", "enterpriseValue", "trailingPE", "forwardPE",
        "priceToBook", "priceToSalesTrailing12Months",
        "trailingEps", "forwardEps", "pegRatio", "beta",
        "dividendYield", "dividendRate", "payoutRatio",
        "profitMargins", "grossMargins", "operatingMargins", "ebitdaMargins",
        "returnOnEquity", "returnOnAssets", "debtToEquity",
        "totalRevenue", "revenueGrowth", "revenuePerShare",
        "totalCash", "totalDebt", "freeCashflow", "operatingCashflow",
        "earningsGrowth", "earningsQuarterlyGrowth",
        "fiftyTwoWeekHigh", "fiftyTwoWeekLow", "fiftyDayAverage", "twoHundredDayAverage",
        "averageVolume", "averageVolume10days",
        "shortRatio", "shortPercentOfFloat", "sharesShort",
        "heldPercentInsiders", "heldPercentInstitutions",
        "targetHighPrice", "targetLowPrice", "targetMeanPrice", "targetMedianPrice",
        "recommendationMean", "recommendationKey", "numberOfAnalystOpinions",
        "currentPrice", "previousClose", "open", "dayHigh", "dayLow", "volume",
        "longBusinessSummary",
    ]
    return [{"key": k, "value": info.get(k)} for k in key_fields if info.get(k) is not None]


# ============================================================
#  数据收集
# ============================================================

@dataclass
class StockReportData:
    ticker: str
    generated_at: str = field(default_factory=lambda: dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    yf_version: str = ""
    blocks: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)


def _collect_group_b(t: yf.Ticker, label_prefix: str = "") -> dict[str, list]:
    results = {}

    def fetch_financials():
        df = _safe_call(lambda: t.financials, label=f"{label_prefix}年度利润表")
        return ("financials", _df_to_records(df.T if df is not None and not df.empty else df))

    def fetch_quarterly_financials():
        df = _safe_call(lambda: t.quarterly_financials, label=f"{label_prefix}季度利润表")
        return ("quarterly_financials", _df_to_records(df.T if df is not None and not df.empty else df))

    def fetch_balance_sheet():
        df = _safe_call(lambda: t.balance_sheet, label=f"{label_prefix}年度资产负债表")
        return ("balance_sheet", _df_to_records(df.T if df is not None and not df.empty else df))

    def fetch_quarterly_balance():
        df = _safe_call(lambda: t.quarterly_balance_sheet, label=f"{label_prefix}季度资产负债表")
        return ("quarterly_balance_sheet", _df_to_records(df.T if df is not None and not df.empty else df))

    def fetch_income():
        df = _safe_call(lambda: t.income_stmt, label=f"{label_prefix}年度损益表")
        return ("income_stmt", _df_to_records(df.T if df is not None and not df.empty else df))

    def fetch_cashflow():
        df = _safe_call(lambda: t.cashflow, label=f"{label_prefix}年度现金流量表")
        return ("cashflow", _df_to_records(df.T if df is not None and not df.empty else df))

    def fetch_quarterly_cashflow():
        df = _safe_call(lambda: t.quarterly_cashflow, label=f"{label_prefix}季度现金流量表")
        return ("quarterly_cashflow", _df_to_records(df.T if df is not None and not df.empty else df))

    tasks = [fetch_financials, fetch_quarterly_financials, fetch_balance_sheet,
             fetch_quarterly_balance, fetch_income, fetch_cashflow, fetch_quarterly_cashflow]

    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(fn): fn.__name__ for fn in tasks}
        for future in as_completed(futures):
            try:
                key, data = future.result()
                results[key] = data
            except Exception as e:
                print(f"  ✗ {futures[future]:45s} {e}")
                results[futures[future]] = []

    return results


def _collect_group_c(t: yf.Ticker, label_prefix: str = "") -> dict[str, list]:
    results = {}

    def fetch_holders():
        major = _safe_call(lambda: t.major_holders, label=f"{label_prefix}主要股东比例")
        inst = _safe_call(lambda: t.institutional_holders, label=f"{label_prefix}机构持仓")
        mf = _safe_call(lambda: t.mutualfund_holders, label=f"{label_prefix}基金持仓")
        return [
            ("major_holders", _df_to_records(major)),
            ("institutional_holders", _df_to_records(inst)),
            ("mutualfund_holders", _df_to_records(mf)),
        ]

    def fetch_recommendations():
        rec = _safe_call(lambda: t.recommendations, label=f"{label_prefix}分析师评级")
        targets = _safe_call(lambda: t.analyst_price_targets, label=f"{label_prefix}分析师目标价")
        return [
            ("recommendations", _df_to_records(rec)),
            ("analyst_price_targets", _df_to_records(targets) if isinstance(targets, pd.DataFrame) else _dict_to_records(targets) if isinstance(targets, dict) else []),
        ]

    def fetch_news():
        news = _safe_call(lambda: t.news, label=f"{label_prefix}新闻")
        if isinstance(news, list):
            cleaned = []
            for item in news[:20]:
                if isinstance(item, dict):
                    cleaned.append({
                        "title": item.get("title", ""),
                        "publisher": item.get("publisher", ""),
                        "link": item.get("link", ""),
                        "providerPublishTime": item.get("providerPublishTime", ""),
                        "type": item.get("type", ""),
                    })
            return [("news", cleaned)]
        return [("news", [])]

    def fetch_insider():
        insider = _safe_call(lambda: t.insider_transactions, label=f"{label_prefix}内部人交易")
        purchases = _safe_call(lambda: t.insider_purchases, label=f"{label_prefix}内部人买入汇总")
        return [
            ("insider_transactions", _df_to_records(insider)),
            ("insider_purchases", _df_to_records(purchases)),
        ]

    def fetch_dividends():
        divs = _safe_call(lambda: t.dividends, label=f"{label_prefix}分红历史")
        splits = _safe_call(lambda: t.splits, label=f"{label_prefix}拆股历史")
        div_records = []
        if divs is not None and len(divs) > 0:
            div_df = divs.reset_index()
            div_df.columns = ["Date", "Dividend"]
            if pd.api.types.is_datetime64_any_dtype(div_df["Date"]):
                div_df["Date"] = div_df["Date"].dt.strftime("%Y-%m-%d")
            div_records = div_df.to_dict("records")
        split_records = []
        if splits is not None and len(splits) > 0:
            split_df = splits.reset_index()
            split_df.columns = ["Date", "Split"]
            if pd.api.types.is_datetime64_any_dtype(split_df["Date"]):
                split_df["Date"] = split_df["Date"].dt.strftime("%Y-%m-%d")
            split_records = split_df.to_dict("records")
        return [
            ("dividends", div_records),
            ("splits", split_records),
        ]

    def fetch_options_summary():
        try:
            dates = t.options
            if not dates:
                print(f"  ✗ {label_prefix}期权链{'':30s} 无可用到期日")
                return [("options_summary", [])]
            nearest = dates[0]
            chain = t.option_chain(nearest)
            calls_oi = int(chain.calls["openInterest"].sum()) if "openInterest" in chain.calls.columns else 0
            puts_oi = int(chain.puts["openInterest"].sum()) if "openInterest" in chain.puts.columns else 0
            calls_vol = int(chain.calls["volume"].fillna(0).sum()) if "volume" in chain.calls.columns else 0
            puts_vol = int(chain.puts["volume"].fillna(0).sum()) if "volume" in chain.puts.columns else 0
            ratio = round(puts_oi / calls_oi, 3) if calls_oi > 0 else None
            summary = {
                "expiration_dates": list(dates[:6]),
                "nearest_expiry": nearest,
                "calls_open_interest": calls_oi,
                "puts_open_interest": puts_oi,
                "put_call_ratio_oi": ratio,
                "calls_volume": calls_vol,
                "puts_volume": puts_vol,
            }
            print(f"  ✓ {label_prefix}期权链摘要{'':27s} P/C={ratio} · nearest={nearest}")
            return [("options_summary", [summary])]
        except Exception as e:
            print(f"  ✗ {label_prefix}期权链{'':30s} {type(e).__name__}: {str(e)[:60]}")
            return [("options_summary", [])]

    task_fns = [fetch_holders, fetch_recommendations, fetch_news,
                fetch_insider, fetch_dividends, fetch_options_summary]

    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(fn): fn.__name__ for fn in task_fns}
        for future in as_completed(futures):
            try:
                pairs = future.result()
                for key, data in pairs:
                    results[key] = data
            except Exception as e:
                print(f"  ✗ {futures[future]:45s} {e}")

    return results


def collect(ticker: str, max_kline_years: int = 3) -> StockReportData:
    data = StockReportData(ticker=ticker, yf_version=getattr(yf, "__version__", "未知"))

    t = yf.Ticker(ticker)

    # ── Group A: 基础信息（串行，因为 info 会初始化 session） ──
    print("[Group A] 基础信息 + K线")

    info = _safe_call(lambda: t.info, label="公司信息(info)")
    data.blocks["basic_info"] = _info_to_records(info)

    fast_info = _safe_call(lambda: t.fast_info, label="快速行情(fast_info)")
    if fast_info is not None:
        fi_dict = {}
        for attr in ["lastPrice", "open", "dayHigh", "dayLow", "previousClose",
                      "lastVolume", "marketCap", "fiftyDayAverage", "twoHundredDayAverage",
                      "yearHigh", "yearLow", "currency", "exchange", "timezone"]:
            try:
                fi_dict[attr] = getattr(fast_info, attr, None)
            except Exception:
                pass
        data.blocks["spot"] = [fi_dict]
    else:
        data.blocks["spot"] = []

    period = f"{max_kline_years}y"
    df_kline = _safe_call(lambda: t.history(period=period, auto_adjust=True),
                          label=f"日K线({max_kline_years}年)")
    if df_kline is not None and not df_kline.empty:
        kline_records = []
        for idx, row in df_kline.iterrows():
            date_str = idx.strftime("%Y-%m-%d") if hasattr(idx, "strftime") else str(idx)
            kline_records.append({
                "date": date_str,
                "open": round(row.get("Open", 0), 2),
                "high": round(row.get("High", 0), 2),
                "low": round(row.get("Low", 0), 2),
                "close": round(row.get("Close", 0), 2),
                "volume": int(row.get("Volume", 0)),
            })
        data.blocks["kline_daily"] = kline_records
    else:
        data.blocks["kline_daily"] = []

    # ── Group B + C: 并发采集 ──
    print("[Group B] 财务报表（并发）")
    print("[Group C] 市场数据（并发）")

    with ThreadPoolExecutor(max_workers=2) as pool:
        future_b = pool.submit(_collect_group_b, t)
        future_c = pool.submit(_collect_group_c, t)

        try:
            group_b = future_b.result()
            data.blocks.update(group_b)
        except Exception as e:
            print(f"  ✗ Group B 失败: {e}")

        try:
            group_c = future_c.result()
            data.blocks.update(group_c)
        except Exception as e:
            print(f"  ✗ Group C 失败: {e}")

    # ── ESG / Sustainability ──
    sustainability = _safe_call(lambda: t.sustainability, label="ESG/可持续发展评分")
    data.blocks["sustainability"] = _df_to_records(sustainability)

    return data


def main() -> None:
    parser = argparse.ArgumentParser(description="美股全维度数据报告（yfinance 版）")
    parser.add_argument("ticker", nargs="?", help="美股 Ticker（如 AAPL, TSLA, MSFT）")
    parser.add_argument("--max-kline-years", type=int, default=3,
                        help="日K拉取的最长年限（默认 3 年）")
    args = parser.parse_args()

    ticker = args.ticker or input("请输入美股 Ticker：").strip().upper()
    if not ticker:
        print("[X] 未输入 Ticker", file=sys.stderr)
        sys.exit(1)

    ticker = ticker.upper()

    print(f"📊 采集 {ticker} 的全量数据")
    print(f"   yfinance 版本：{getattr(yf, '__version__', '未知')}")
    print(f"   K线年限：{args.max_kline_years} 年")
    print()

    t0 = time.perf_counter()
    data = collect(ticker, max_kline_years=args.max_kline_years)
    elapsed = time.perf_counter() - t0

    n_blocks = sum(1 for v in data.blocks.values() if isinstance(v, list) and v)
    n_total_rows = sum(len(v) for v in data.blocks.values() if isinstance(v, list))
    print(f"\n✅ 数据收集完成：{n_blocks}/{len(data.blocks)} 个数据块，"
          f"共 {n_total_rows} 行，用时 {elapsed:.1f}s")

    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
    os.makedirs(output_dir, exist_ok=True)
    json_path = os.path.join(output_dir, f"data_{ticker}.json")

    json_payload = {
        "ticker": data.ticker,
        "generated_at": data.generated_at,
        "yf_version": data.yf_version,
        "blocks": data.blocks,
    }
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(json_payload, f, ensure_ascii=False, default=str, indent=2)
    print(f"📊 JSON数据已保存：{json_path}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n已中断")
    except Exception:
        traceback.print_exc()
        sys.exit(1)
