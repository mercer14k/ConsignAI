import { useEffect, useRef } from "react";
import * as echarts from "echarts/core";
import { LineChart } from "echarts/charts";
import { GridComponent, TooltipComponent } from "echarts/components";
import { CanvasRenderer } from "echarts/renderers";
import type { Overview } from "./types";
echarts.use([LineChart, GridComponent, TooltipComponent, CanvasRenderer]);
export function StockChart({ trend }: { trend: Overview["trend"] }) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!ref.current) return;
    const chart = echarts.init(ref.current);
    chart.setOption({
      animationDuration: 500,
      grid: { left: 58, right: 24, top: 20, bottom: 30 },
      tooltip: {
        trigger: "axis",
        backgroundColor: "#17202c",
        borderColor: "#344154",
        textStyle: { color: "#e6edf5" },
        valueFormatter: (v: number) => `$${(v / 100).toLocaleString()}`,
      },
      xAxis: {
        type: "category",
        data: trend.map((d) => d.day),
        boundaryGap: false,
        axisLine: { show: false },
        axisTick: { show: false },
        axisLabel: {
          color: "#91a0b1",
          fontSize: 12,
          formatter: (s: string) =>
            new Date(s + "T12:00:00").toLocaleDateString("en-US", {
              month: "short",
              day: "numeric",
            }),
        },
      },
      yAxis: {
        type: "value",
        scale: true,
        splitNumber: 3,
        axisLabel: {
          color: "#91a0b1",
          fontSize: 12,
          formatter: (v: number) => `$${Math.round(v / 100000000)}M`,
        },
        splitLine: { lineStyle: { color: "#202834", type: "dashed" } },
      },
      series: [
        {
          type: "line",
          data: trend.map((d) => d.value_cents),
          smooth: 0.15,
          symbol: "none",
          lineStyle: { color: "#c4f176", width: 2 },
          areaStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: "rgba(196,241,118,.18)" },
              { offset: 1, color: "rgba(196,241,118,0)" },
            ]),
          },
        },
      ],
    });
    const observer = new ResizeObserver(() => chart.resize());
    observer.observe(ref.current);
    return () => {
      observer.disconnect();
      chart.dispose();
    };
  }, [trend]);
  return (
    <div
      className="chart"
      ref={ref}
      role="img"
      aria-label={`Reported stock value over ${trend.length} days. Latest value ${trend.at(-1)?.value_cents ? "$" + Math.round(trend.at(-1)!.value_cents / 100).toLocaleString() : "unavailable"}.`}
    />
  );
}
