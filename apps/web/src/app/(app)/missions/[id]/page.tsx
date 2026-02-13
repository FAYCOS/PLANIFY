export const dynamic = "force-dynamic";

import Link from "next/link";
import { notFound, redirect } from "next/navigation";
import { and, eq } from "drizzle-orm";

import { db } from "@/db";
import { prestation } from "@/db/schema";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { getServerSession } from "@/lib/auth-session";

type Params = { params: Promise<{ id: string }> };

export default async function MissionDetailPage({ params }: Params) {
  const { id } = await params;
  const session = await getServerSession();
  const orgId = session?.user?.orgId;
  if (!orgId) {
    redirect("/signup");
  }
  const [mission] = await db
    .select()
    .from(prestation)
    .where(and(eq(prestation.id, id), eq(prestation.orgId, orgId)))
    .limit(1);
  if (!mission) notFound();

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold">
            Mission {mission.id.slice(0, 8)}
          </h1>
          <p className="text-sm text-muted-foreground">{mission.clientNom}</p>
        </div>
        <div className="flex gap-2">
          <Button asChild variant="outline">
            <Link href={`/missions/${mission.id}/modifier`}>Modifier</Link>
          </Button>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Details</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-3 text-sm">
          <div>Lieu: {mission.lieu ?? "-"}</div>
          <div>
            Dates:{" "}
            {mission.dateDebut
              ? new Date(mission.dateDebut).toLocaleDateString("fr-FR")
              : "-"}{" "}
            {mission.dateFin
              ? `→ ${new Date(mission.dateFin).toLocaleDateString("fr-FR")}`
              : ""}
          </div>
          <div>
            Heures: {mission.heureDebut ?? "-"} → {mission.heureFin ?? "-"}
          </div>
          <div>
            Statut:{" "}
            <Badge
              variant={mission.statut === "confirmee" ? "success" : "secondary"}
            >
              {mission.statut}
            </Badge>
          </div>
          <div>Notes: {mission.notes ?? "-"}</div>
        </CardContent>
      </Card>
    </div>
  );
}
