"use client";

import { useEffect, useRef } from "react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export function FinanceChartPlaceholder() {
  const chartRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!chartRef.current) return;
    let mounted = true;
    void (async () => {
      const { default: gsap } = await import("gsap");
      if (!mounted) return;
      gsap.fromTo(
        chartRef.current,
        { opacity: 0, scale: 0.98 },
        { opacity: 1, scale: 1, duration: 0.6, ease: "power2.out" },
      );
    })();
    return () => {
      mounted = false;
    };
  }, []);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-medium text-muted-foreground">
          Tresorerie (placeholder)
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div
          ref={chartRef}
          className="h-56 w-full rounded-xl border border-dashed border-muted-foreground/20 bg-gradient-to-br from-emerald-50 via-transparent to-transparent"
        />
      </CardContent>
    </Card>
  );
}
