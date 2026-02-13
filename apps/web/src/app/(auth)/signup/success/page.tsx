"use client";

import { useEffect } from "react";
import Link from "next/link";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { clearFlowId, clearInviteToken } from "@/lib/signup-client";

export default function SignupSuccessPage() {
  useEffect(() => {
    clearFlowId();
    clearInviteToken();
    fetch("/api/signup/status").catch(() => null);
  }, []);

  return (
    <Card className="w-full max-w-md">
      <CardHeader>
        <CardTitle>Compte pret</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4 text-sm text-muted-foreground">
        <p>Votre espace Planify est pret. Vous pouvez vous connecter.</p>
        <Button asChild className="w-full">
          <Link href="/login">Se connecter</Link>
        </Button>
      </CardContent>
    </Card>
  );
}
