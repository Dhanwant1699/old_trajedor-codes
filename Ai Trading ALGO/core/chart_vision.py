"""
Trajedor Chart Vision & Visual Drawing Engine.
Generates institutional-grade candlestick charts with visual annotations:
- Draws Order Block boxes (Demand / Supply zones)
- Draws Fair Value Gaps (shaded imbalances)
- Draws Entry, Stop-Loss, and Take-Profit target lines
- Runs with ZERO external dependencies (Generates vector SVG + Interactive HTML)
"""

import os
from typing import Dict, Any, List, Optional


class ChartVision:
    def __init__(self, output_dir: Optional[str] = None):
        self.output_dir = output_dir or os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "data", "chart_snapshots"
        )
        os.makedirs(self.output_dir, exist_ok=True)

    def generate_chart_svg(
        self,
        candles: List[Dict[str, Any]],
        symbol: str = "XAUUSD",
        order_blocks: Optional[List[Dict[str, Any]]] = None,
        fvgs: Optional[List[Dict[str, Any]]] = None,
        trade_overlay: Optional[Dict[str, float]] = None,
        width: int = 1000,
        height: int = 550,
        filename: str = "latest_setup.svg"
    ) -> str:
        """
        Renders pure-vector SVG chart with candlestick physics, order blocks,
        fair value gaps, and trade entry/SL/TP lines.
        """
        if not candles:
            return ""

        # Margins
        pad_left = 60
        pad_right = 90
        pad_top = 50
        pad_bottom = 50
        plot_w = width - pad_left - pad_right
        plot_h = height - pad_top - pad_bottom

        # Price Extents
        all_highs = [c["high"] for c in candles]
        all_lows = [c["low"] for c in candles]
        if trade_overlay:
            if "entry" in trade_overlay: all_highs.append(trade_overlay["entry"]); all_lows.append(trade_overlay["entry"])
            if "sl" in trade_overlay: all_highs.append(trade_overlay["sl"]); all_lows.append(trade_overlay["sl"])
            if "tp" in trade_overlay: all_highs.append(trade_overlay["tp"]); all_lows.append(trade_overlay["tp"])

        min_p = min(all_lows) - 0.50
        max_p = max(all_highs) + 0.50
        price_range = max_p - min_p or 1.0

        def y_coord(price):
            return pad_top + plot_h - ((price - min_p) / price_range * plot_h)

        num_candles = len(candles)
        candle_w = max(4.0, (plot_w / num_candles) * 0.70)
        gap = plot_w / num_candles

        svg_parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" style="background-color: #0b0f19; font-family: -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, Helvetica, Arial, sans-serif;">',
            f'<!-- Header -->',
            f'<text x="{pad_left}" y="32" fill="#e2e8f0" font-size="18" font-weight="bold">{symbol} · Institutional Analysis &amp; Trade Blueprint</text>',
            f'<text x="{width - pad_right}" y="32" fill="#94a3b8" font-size="13" text-anchor="end">Trajedor Visual Sentry</text>',
            f'<!-- Chart Area Grid -->',
            f'<rect x="{pad_left}" y="{pad_top}" width="{plot_w}" height="{plot_h}" fill="#111827" stroke="#1e293b" stroke-width="1"/>'
        ]

        # Draw Gridlines (5 horizontal price levels)
        for i in range(5):
            p_val = min_p + (i / 4.0 * price_range)
            y = y_coord(p_val)
            svg_parts.append(f'<line x1="{pad_left}" y1="{y}" x2="{pad_left + plot_w}" y2="{y}" stroke="#1e293b" stroke-dasharray="4,4"/>')
            svg_parts.append(f'<text x="{pad_left + plot_w + 10}" y="{y + 4}" fill="#64748b" font-size="11">${p_val:.2f}</text>')

        # Draw Order Blocks (OBs)
        if order_blocks:
            for ob in order_blocks:
                ob_type = ob.get("type", "BULLISH")
                color = "rgba(16, 185, 129, 0.20)" if ob_type == "BULLISH" else "rgba(239, 68, 68, 0.20)"
                stroke = "#10b981" if ob_type == "BULLISH" else "#ef4444"
                top_y = y_coord(ob.get("high", max_p))
                bot_y = y_coord(ob.get("low", min_p))
                ob_h = max(3.0, bot_y - top_y)
                svg_parts.append(f'<rect x="{pad_left}" y="{top_y}" width="{plot_w}" height="{ob_h}" fill="{color}" stroke="{stroke}" stroke-width="1" stroke-dasharray="3,3"/>')
                svg_parts.append(f'<text x="{pad_left + 10}" y="{top_y + 14}" fill="{stroke}" font-size="10" font-weight="bold">{ob_type} ORDER BLOCK</text>')

        # Draw Fair Value Gaps (FVGs)
        if fvgs:
            for fvg in fvgs:
                top_y = y_coord(fvg.get("top", max_p))
                bot_y = y_coord(fvg.get("bottom", min_p))
                fvg_h = max(2.0, bot_y - top_y)
                svg_parts.append(f'<rect x="{pad_left}" y="{top_y}" width="{plot_w}" height="{fvg_h}" fill="rgba(245, 158, 11, 0.15)" stroke="#f59e0b" stroke-width="0.8"/>')
                svg_parts.append(f'<text x="{pad_left + plot_w - 70}" y="{top_y + 12}" fill="#f59e0b" font-size="9">FVG GAP</text>')

        # Draw Candlesticks
        for i, c in enumerate(candles):
            cx = pad_left + (i * gap) + (gap / 2.0)
            is_green = c["close"] >= c["open"]
            color = "#10b981" if is_green else "#ef4444"

            # Wicks
            y_high = y_coord(c["high"])
            y_low = y_coord(c["low"])
            svg_parts.append(f'<line x1="{cx}" y1="{y_high}" x2="{cx}" y2="{y_low}" stroke="{color}" stroke-width="1.2"/>')

            # Body
            y_open = y_coord(c["open"])
            y_close = y_coord(c["close"])
            body_top = min(y_open, y_close)
            body_h = max(1.5, abs(y_close - y_open))
            bx = cx - (candle_w / 2.0)
            svg_parts.append(f'<rect x="{bx}" y="{body_top}" width="{candle_w}" height="{body_h}" fill="{color}"/>')

        # Draw Trade Overlays (Entry, SL, TP)
        if trade_overlay:
            entry = trade_overlay.get("entry")
            sl = trade_overlay.get("sl")
            tp = trade_overlay.get("tp")

            if entry:
                ey = y_coord(entry)
                svg_parts.append(f'<line x1="{pad_left}" y1="{ey}" x2="{pad_left + plot_w}" y2="{ey}" stroke="#38bdf8" stroke-width="2"/>')
                svg_parts.append(f'<rect x="{pad_left + plot_w + 5}" y="{ey - 10}" width="75" height="20" fill="#0284c7" rx="3"/>')
                svg_parts.append(f'<text x="{pad_left + plot_w + 42}" y="{ey + 4}" fill="#ffffff" font-size="10" font-weight="bold" text-anchor="middle">ENTRY ${entry:.2f}</text>')

            if sl:
                sy = y_coord(sl)
                svg_parts.append(f'<line x1="{pad_left}" y1="{sy}" x2="{pad_left + plot_w}" y2="{sy}" stroke="#ef4444" stroke-width="2" stroke-dasharray="5,3"/>')
                svg_parts.append(f'<rect x="{pad_left + plot_w + 5}" y="{sy - 10}" width="75" height="20" fill="#dc2626" rx="3"/>')
                svg_parts.append(f'<text x="{pad_left + plot_w + 42}" y="{sy + 4}" fill="#ffffff" font-size="10" font-weight="bold" text-anchor="middle">SL ${sl:.2f}</text>')

            if tp:
                ty = y_coord(tp)
                svg_parts.append(f'<line x1="{pad_left}" y1="{ty}" x2="{pad_left + plot_w}" y2="{ty}" stroke="#10b981" stroke-width="2" stroke-dasharray="5,3"/>')
                svg_parts.append(f'<rect x="{pad_left + plot_w + 5}" y="{ty - 10}" width="75" height="20" fill="#059669" rx="3"/>')
                svg_parts.append(f'<text x="{pad_left + plot_w + 42}" y="{ty + 4}" fill="#ffffff" font-size="10" font-weight="bold" text-anchor="middle">TP ${tp:.2f}</text>')

        svg_parts.append('</svg>')
        svg_content = "\n".join(svg_parts)

        out_path = os.path.join(self.output_dir, filename)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(svg_content)

        return out_path


if __name__ == "__main__":
    print("Testing Trajedor Chart Vision Engine...")
    vision = ChartVision()

    # Generate 25 sample candles
    sample_candles = []
    base_price = 2650.0
    for i in range(25):
        op = base_price + (i * 0.3)
        cl = op + (0.8 if i % 2 == 0 else -0.4)
        hi = max(op, cl) + 0.6
        lo = min(op, cl) - 0.5
        sample_candles.append({"open": op, "high": hi, "low": lo, "close": cl})

    out_file = vision.generate_chart_svg(
        candles=sample_candles,
        symbol="XAUUSD (Gold)",
        order_blocks=[{"type": "BULLISH", "high": 2649.50, "low": 2648.00}],
        fvgs=[{"top": 2654.00, "bottom": 2652.50}],
        trade_overlay={"entry": 2651.00, "sl": 2647.50, "tp": 2658.00},
        filename="test_trade_plan.svg"
    )

    print(f"Chart snapshot successfully drawn and saved: {out_file}")
