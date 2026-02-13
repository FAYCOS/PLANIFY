"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { clearFlowId, loadFlowId, resolveFlowId, saveFlowId } from "@/lib/signup-client";

export default function SignupProvisioningPage() {
  const router = useRouter();
  const [message, setMessage] = useState("Provisionnement en cours...");
  const [canRetry, setCanRetry] = useState(false);

  useEffect(() => {
    const flowId = loadFlowId();
    if (!flowId) {
      resolveFlowId()
        .then((resolved) => {
          if (!resolved) {
            router.replace("/signup");
            return;
          }
          saveFlowId(resolved);
        })
        .catch(() => router.replace("/signup"));
      return;
    }

    let cancelled = false;

    const runProvisioning = async () => {
      try {
        await fetch("/api/signup/provision-db", {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({ flowId }),
        });
      } catch {
        // ignore, status polling will show error
      }
    };

    const pollStatus = async () => {
      try {
        const res = await fetch(`/api/signup/status?flowId=${flowId}`);
        const data = (await res.json().catch(() => null)) as {
          status?: string;
          nextStep?: string;
          error?: string;
          provisioningStatus?: string;
        } | null;

        if (data?.status === "completed") {
          clearFlowId();
          router.push("/signup/success");
          return;
        }
        if (data?.status === "provisioning" && data.provisioningStatus === "failed") {
          setMessage("Provisionnement en echec. Veuillez reessayer.");
          setCanRetry(true);
          return;
        }
        if (data?.status === "provisioning") {
          setMessage("Provisionnement en cours...");
          setCanRetry(false);
        }
        if (data?.status === "expired") {
          clearFlowId();
          router.replace("/signup");
        }
      } catch {
        setMessage("Provisionnement en attente...");
      }
    };

    runProvisioning();
    const timer = setInterval(() => {
      if (!cancelled) {
        pollStatus();
      }
    }, 2000);

    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, [router]);

  return (
    <Card className="w-full max-w-md">
      <CardHeader>
        <CardTitle>Creation de votre espace</CardTitle>
      </CardHeader>
      <CardContent className="text-sm text-muted-foreground">
        <div className="space-y-4">
          <div>{message}</div>
          {canRetry ? (
            <Button
              variant="outline"
              onClick={() => {
                setCanRetry(false);
                setMessage("Provisionnement en cours...");
                fetch("/api/signup/provision-db", {
                  method: "POST",
                  headers: { "content-type": "application/json" },
                  body: JSON.stringify({ flowId: loadFlowId() }),
                }).catch(() => null);
              }}
            >
              Reessayer
            </Button>
          ) : null}
        </div>
      </CardContent>
    </Card>
  );
}
