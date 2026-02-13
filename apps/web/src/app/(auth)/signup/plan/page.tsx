"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { clearFlowId, loadFlowId, resolveFlowId, saveFlowId } from "@/lib/signup-client";

const PLANS = [
  { code: "starter", title: "Starter", description: "Pour debuter rapidement." },
  { code: "team", title: "Team", description: "Pour equipes en croissance." },
  { code: "business", title: "Business", description: "Pour organisations exigeantes." },
];

export default function SignupPlanPage() {
  const router = useRouter();
  const [message, setMessage] = useState<string | null>(null);
  const [loadingCode, setLoadingCode] = useState<string | null>(null);

  useEffect(() => {
    const flowId = loadFlowId();
    const statusUrl = flowId
      ? `/api/signup/status?flowId=${flowId}`
      : "/api/signup/status";
    fetch(statusUrl)
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (!data) {
          router.replace("/signup");
          return;
        }
        if (data.status === "completed") {
          clearFlowId();
          router.replace("/login");
          return;
        }
        if (data.status === "expired") {
          clearFlowId();
          router.replace("/signup");
          return;
        }
        if (data.flowId && !flowId) {
          saveFlowId(data.flowId);
        }
        if (data?.nextStep && data.nextStep !== "/signup/plan") {
          router.replace(data.nextStep);
        }
      })
      .catch(() => router.replace("/signup"));
  }, [router]);

  const handleChoosePlan = async (planCode: string) => {
    let flowId = loadFlowId();
    if (!flowId) {
      flowId = await resolveFlowId();
    }
    if (!flowId) {
      setMessage("Session d'inscription introuvable.");
      return;
    }
    setLoadingCode(planCode);
    setMessage(null);
    try {
      const res = await fetch("/api/signup/choose-plan", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ flowId, planCode }),
      });
      const data = (await res.json().catch(() => null)) as {
        error?: string;
        nextStep?: string;
      } | null;
      if (!res.ok) {
        setMessage(data?.error || "Impossible de choisir ce plan.");
        return;
      }
      router.push(data?.nextStep || "/signup/provisioning");
    } catch {
      setMessage("Erreur reseau.");
    } finally {
      setLoadingCode(null);
    }
  };

  return (
    <Card className="w-full max-w-3xl">
      <CardHeader>
        <CardTitle>Choisissez votre plan</CardTitle>
      </CardHeader>
      <CardContent className="grid gap-4 md:grid-cols-3">
        {PLANS.map((plan) => (
          <div
            key={plan.code}
            className="flex h-full flex-col rounded-lg border border-slate-200 bg-white p-4"
          >
            <h3 className="text-sm font-semibold text-slate-900">{plan.title}</h3>
            <p className="mt-2 text-sm text-slate-600">{plan.description}</p>
            <div className="mt-auto pt-4">
              <Button
                className="w-full"
                onClick={() => handleChoosePlan(plan.code)}
                disabled={loadingCode === plan.code}
              >
                Choisir
              </Button>
            </div>
          </div>
        ))}
        {message ? (
          <div className="text-sm text-muted-foreground md:col-span-3">
            {message}
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}
