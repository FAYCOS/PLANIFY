"use client";

import { useEffect, useRef } from "react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const metrics = [
  { label: "Encaissements", value: "12 450 €", delta: "+8%" },
  { label: "Factures en attente", value: "18", delta: "-3%" },
  { label: "Materiel en sortie", value: "4", delta: "+1" },
  { label: "Missions cette semaine", value: "5", delta: "+1" },
];

export function DashboardMetrics() {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!containerRef.current) return;
    const cards = containerRef.current.querySelectorAll("[data-card]");
    let mounted = true;
    void (async () => {
      const { default: gsap } = await import("gsap");
      if (!mounted) return;
      gsap.fromTo(
        cards,
        { opacity: 0, y: 12 },
        {
          opacity: 1,
          y: 0,
          duration: 0.6,
          stagger: 0.08,
          ease: "power2.out",
        },
      );
    })();
    return () => {
      mounted = false;
    };
  }, []);

  return (
    <div ref={containerRef} className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
      {metrics.map((metric) => (
        <Card key={metric.label} data-card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              {metric.label}
            </CardTitle>
          </CardHeader>
          <CardContent className="flex items-baseline justify-between">
            <div className="text-2xl font-semibold">{metric.value}</div>
            <div className="text-xs text-emerald-600">{metric.delta}</div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
