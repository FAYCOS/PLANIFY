export const dynamic = "force-dynamic";

import Link from "next/link";
import { notFound, redirect } from "next/navigation";
import { and, eq } from "drizzle-orm";

import { db } from "@/db";
import { devis } from "@/db/schema";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { DevisActions } from "@/components/finance/devis-actions";
import { getServerSession } from "@/lib/auth-session";

type Params = { params: Promise<{ id: string }> };

export default async function DevisDetailPage({ params }: Params) {
  const { id } = await params;
  const session = await getServerSession();
  const orgId = session?.user?.orgId;
  if (!orgId) {
    redirect("/signup");
  }
  const [row] = await db
    .select()
    .from(devis)
    .where(and(eq(devis.id, id), eq(devis.orgId, orgId)))
    .limit(1);
  if (!row) notFound();

  const locked = row.estSigne || row.statut === "signe";

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold">Devis {row.numero}</h1>
          <p className="text-sm text-muted-foreground">{row.clientNom}</p>
        </div>
        <div className="flex gap-2">
          <Badge variant={locked ? "success" : "secondary"}>{row.statut}</Badge>
          {!locked ? (
            <Button asChild variant="outline">
              <Link href={`/finance/devis/${row.id}/modifier`}>Modifier</Link>
            </Button>
          ) : null}
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-[2fr_1fr]">
        <Card>
          <CardHeader>
            <CardTitle>Details</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-3 text-sm">
            <div>Prestation: {row.prestationTitre}</div>
            <div>Montant HT: {row.montantHt ?? "0"} €</div>
            <div>Montant TTC: {row.montantTtc ?? "0"} €</div>
            <div>Date creation: {row.dateCreation?.toLocaleString?.() ?? "-"}</div>
            <div>Statut: {row.statut}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Actions</CardTitle>
          </CardHeader>
          <CardContent>
            <DevisActions id={row.id} locked={locked} statut={row.statut} />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
