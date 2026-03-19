from datetime import datetime

import yfinance as yf

def calculate_technical_indicators(df, window_ma=120, window_rsi=14):
    """
    计算技术指标:
    - MA120: 120日移动平均线 (半年线)
    - RSI: 相对强弱指标
    """
    # 计算 MA
    df['MA_Long'] = df['Close'].rolling(window=window_ma).mean()
    
    # 计算 RSI
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window_rsi).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window_rsi).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    return df


def _build_strategy_signal(rsi, bias):
    multiplier = 1.0
    reason = "市场处于正常波动范围，维持基准定投。"

    if rsi < 30 or bias < -0.10:
        multiplier = 2.0
        reason = "🚨 触发【超卖/低估】信号！市场极度悲观，建议【双倍】定投摊低成本。"
    elif rsi < 40 or bias < -0.05:
        multiplier = 1.5
        reason = "📉 触发【相对低估】信号。价格低于均线或动能较弱，建议【1.5倍】定投。"
    elif rsi > 75 or bias > 0.15:
        multiplier = 0.0
        reason = "🔥 触发【极度超买】信号！价格严重偏离均线，建议【暂停买入】，保留现金。"
    elif rsi > 65 or bias > 0.10:
        multiplier = 0.5
        reason = "⚠️ 触发【高估】信号。价格处于高位，建议【减半】买入 (0.5倍)，防范回调风险。"

    return multiplier, reason


def get_gold_strategy_data(base_budget_cny, period="1y"):
    ticker = yf.Ticker("GC=F")
    hist = ticker.history(period=period)

    if hist.empty:
        raise RuntimeError("无法获取数据，请检查网络连接 (需要访问 Yahoo Finance)。")

    df = calculate_technical_indicators(hist.copy())
    df = df.dropna(subset=["MA_Long", "RSI"])

    if df.empty:
        raise RuntimeError("历史数据不足，无法完成 MA120 与 RSI 计算。")

    latest = df.iloc[-1]
    current_price = float(latest["Close"])
    ma_long = float(latest["MA_Long"])
    rsi = float(latest["RSI"])
    bias = (current_price - ma_long) / ma_long
    multiplier, reason = _build_strategy_signal(rsi, bias)
    suggested_amount = float(base_budget_cny) * multiplier

    chart_df = df.tail(180).copy()
    chart_df["Date"] = chart_df.index.strftime("%Y-%m-%d")
    chart = {
        "dates": chart_df["Date"].tolist(),
        "close": [round(float(v), 2) for v in chart_df["Close"].tolist()],
        "ma_long": [round(float(v), 2) for v in chart_df["MA_Long"].tolist()],
        "rsi": [round(float(v), 2) for v in chart_df["RSI"].tolist()],
    }

    return {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "current_price": round(current_price, 2),
        "ma_long": round(ma_long, 2),
        "bias": round(float(bias), 6),
        "rsi": round(rsi, 2),
        "multiplier": multiplier,
        "reason": reason,
        "base_budget_cny": float(base_budget_cny),
        "suggested_amount_cny": round(suggested_amount, 2),
        "chart": chart,
    }

def get_gold_strategy(base_budget_cny):
    """
    根据当前国际金价 (XAU/USD) 给出人民币定投建议
    虽然国际金价是美元，但趋势与国内金价高度正相关，技术指标通用。
    """
    print("正在获取国际金价数据 (XAU/USD)...")
    try:
        result = get_gold_strategy_data(base_budget_cny=base_budget_cny, period="1y")
        print("\n" + "="*40)
        print(f"日期: {result['date']}")
        print(f"💰 当前国际金价: ${result['current_price']:.2f} / oz")
        print(f"📊 MA120 (半年线): ${result['ma_long']:.2f}")
        print(f"📈 乖离率 (Bias): {result['bias']*100:.2f}% (正值代表高于均线)")
        print(f"📉 RSI (14): {result['rsi']:.2f}")
        print("="*40 + "\n")
        print(f"💡 策略建议: {result['reason']}")
        print(f"💵 基准预算: ¥{result['base_budget_cny']}")
        print(f"🚀 本月建议买入金额: ¥{result['suggested_amount_cny']:.0f}")
        print("="*40)

    except Exception as e:
        print(f"发生错误: {e}")
        print("建议: 如果网络无法访问 Yahoo Finance，请手动参考银行App上的 MA120 和 RSI 指标。")

if __name__ == "__main__":
    print("--- 黄金智能定投计算器 (Smart Beta Gold DCA) ---")
    try:
        budget = float(input("请输入你的每月基准购金预算 (人民币): "))
        get_gold_strategy(budget)
    except ValueError:
        print("请输入有效的数字。")
