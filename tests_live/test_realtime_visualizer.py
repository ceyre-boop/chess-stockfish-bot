"""tests_live/test_realtime_visualizer.py

Lightweight real-time candlestick visualizer using matplotlib.
Updates every second for 60 seconds. Uses Alpaca 1-minute bars as source,
shows candles, volume, provider label, regime overlay and confidence.
"""
import time
from datetime import datetime, timedelta
import math

import matplotlib.pyplot as plt
import matplotlib.dates as mdates

from adapters.alpaca_adapter import get_historical_bars


def extract_features(bar):
    momentum = (bar['close'] - bar['open'])
    volatility = (bar['high'] - bar['low'])
    return {'momentum': momentum, 'volatility': volatility}


def classify_regime(features):
    m = features.get('momentum', 0)
    if m > 0:
        return 'bull', min(1.0, abs(m) / (features.get('volatility', 1.0) + 1e-6))
    if m < 0:
        return 'bear', min(1.0, abs(m) / (features.get('volatility', 1.0) + 1e-6))
    return 'neutral', 0.0


def to_mpl_dates(bars):
    return [mdates.date2num(datetime.utcfromtimestamp(int(b['timestamp']) if isinstance(b['timestamp'], (int, float)) else datetime.fromisoformat(b['timestamp']).timestamp())) for b in bars]


def main():
    symbol = 'AAPL'
    print('Starting realtime visualizer (60s) — provider: Alpaca')
    end = datetime.utcnow()
    start = end - timedelta(minutes=60)
    try:
        bars = get_historical_bars(symbol, start, end, '1Min')
    except Exception as e:
        print('Alpaca fetch error:', e)
        return

    if not bars:
        print('No bars available')
        return

    # Use most recent 60
    bars = bars[-60:]

    # Prepare plot
    fig, ax = plt.subplots()
    plt.ion()
    fig.show()

    for i in range(60):
        try:
            # Update data by refetching recent bars
            end = datetime.utcnow()
            start = end - timedelta(minutes=60)
            bars = get_historical_bars(symbol, start, end, '1Min') or bars
            bars = bars[-60:]

            times = []
            opens = []
            highs = []
            lows = []
            closes = []
            volumes = []
            regimes = []
            confidences = []

            for b in bars:
                ts = b.get('timestamp') or b.get('timestamp_utc')
                try:
                    if isinstance(ts, (int, float)):
                        t = datetime.utcfromtimestamp(int(ts))
                    else:
                        t = datetime.fromisoformat(ts)
                except Exception:
                    t = datetime.utcnow()
                times.append(mdates.date2num(t))
                opens.append(float(b.get('open') or 0))
                highs.append(float(b.get('high') or 0))
                lows.append(float(b.get('low') or 0))
                closes.append(float(b.get('close') or 0))
                volumes.append(int(b.get('volume') or 0))
                f = extract_features({'open': opens[-1], 'high': highs[-1], 'low': lows[-1], 'close': closes[-1]})
                regime, conf = classify_regime(f)
                regimes.append(regime)
                confidences.append(conf)

            ax.clear()
            ax2 = ax.twinx()
            ax.set_title(f"Realtime candles — {symbol} (provider: Alpaca)")

            # Draw candles as vertical lines with colored body
            for t, o, h, l, c in zip(times, opens, highs, lows, closes):
                color = 'g' if c >= o else 'r'
                ax.vlines(t, l, h, color='k', linewidth=1)
                ax.add_patch(plt.Rectangle((t-0.0005, min(o, c)), 0.001, abs(c-o), color=color))

            ax2.fill_between(times, volumes, color='0.9')
            ax.set_xlim(min(times), max(times))
            ax.xaxis_date()
            fig.canvas.draw()
            fig.canvas.flush_events()

            # Print top-of-iteration summary
            latest_idx = -1
            print(f"Iteration {i+1}: latest close={closes[latest_idx]} regime={regimes[latest_idx]} conf={confidences[latest_idx]:.3f}")

        except Exception as e:
            print('Visualizer iteration error:', e)

        time.sleep(1)

    plt.ioff()
    print('Visualizer finished (60s)')


if __name__ == '__main__':
    main()
