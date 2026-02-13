"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { clearFlowId, loadFlowId, resolveFlowId, saveFlowId } from "@/lib/signup-client";

export default function SignupVerifyPage() {
  const router = useRouter();
  const [code, setCode] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [cooldown, setCooldown] = useState(0);

  useEffect(() => {
    const flowId = loadFlowId();
    const statusUrl = flowId
      ? `/api/signup/status?flowId=${flowId}`
      : "/api/signup/status";
    fetch(statusUrl)
      .then(async (res) => {
        if (!res.ok) {
          clearFlowId();
          return null;
        }
        return (await res.json()) as { flowId?: string; nextStep?: string; status?: string } | null;
      })
      .then((data) => {
        if (!data) {
          router.replace("/signup");
          return;
        }
        if (data.status === "expired") {
          clearFlowId();
          router.replace("/signup");
          return;
        }
        if (data.status === "completed") {
          clearFlowId();
          router.replace("/login");
          return;
        }
        if (data.flowId && !flowId) {
          saveFlowId(data.flowId);
        }
        if (data?.nextStep && data.nextStep !== "/signup/verify") {
          router.replace(data.nextStep);
        }
      })
      .catch(() => router.replace("/signup"));
  }, [router]);

  const handleVerify = async () => {
    let flowId = loadFlowId();
    if (!flowId) {
      flowId = await resolveFlowId();
    }
    if (!flowId) {
      setMessage("Session d'inscription introuvable.");
      return;
    }
    setLoading(true);
    setMessage(null);
    try {
      const res = await fetch("/api/signup/verify-code", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ flowId, code }),
      });
      const data = (await res.json().catch(() => null)) as {
        error?: string;
        nextStep?: string;
      } | null;
      if (!res.ok) {
        setMessage(data?.error || "Code invalide.");
        return;
      }
      router.push(data?.nextStep || "/signup/plan");
    } catch {
      setMessage("Erreur reseau.");
    } finally {
      setLoading(false);
    }
  };

  const handleResend = async () => {
    let flowId = loadFlowId();
    if (!flowId) {
      flowId = await resolveFlowId();
    }
    if (!flowId) {
      setMessage("Session d'inscription introuvable.");
      return;
    }
    setLoading(true);
    setMessage(null);
    try {
      const res = await fetch("/api/signup/resend-code", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ flowId }),
      });
      const data = (await res.json().catch(() => null)) as {
        error?: string;
        cooldownSeconds?: number;
      } | null;
      if (!res.ok) {
        setMessage(data?.error || "Impossible de renvoyer le code.");
        if (data?.cooldownSeconds) {
          setCooldown(data.cooldownSeconds);
        }
        return;
      }
      setMessage("Code envoye.");
      if (data?.cooldownSeconds) {
        setCooldown(data.cooldownSeconds);
      }
    } catch {
      setMessage("Erreur reseau.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (cooldown <= 0) return;
    const timer = setInterval(() => {
      setCooldown((value) => Math.max(0, value - 1));
    }, 1000);
    return () => clearInterval(timer);
  }, [cooldown]);

  return (
    <Card className="w-full max-w-md">
      <CardHeader>
        <CardTitle>Verification email</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-2">
          <Label>Code recu par email</Label>
          <Input
            value={code}
            onChange={(event) => setCode(event.target.value)}
            placeholder="123456"
          />
        </div>
        <Button className="w-full" onClick={handleVerify} disabled={loading}>
          Verifier
        </Button>
        <Button
          className="w-full"
          variant="outline"
          onClick={handleResend}
          disabled={loading || cooldown > 0}
        >
          {cooldown > 0 ? `Renvoyer (${cooldown}s)` : "Renvoyer le code"}
        </Button>
        {message ? (
          <div className="text-sm text-muted-foreground">{message}</div>
        ) : null}
      </CardContent>
    </Card>
  );
}
