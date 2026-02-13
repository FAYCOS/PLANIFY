export const dynamic = "force-dynamic";

import Link from "next/link";

import { desc, eq } from "drizzle-orm";

import { db } from "@/db";
import { prestation } from "@/db/schema";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { getServerSession } from "@/lib/auth-session";
import { redirect } from "next/navigation";

export default async function MissionsPage({
  searchParams,
}: {
  searchParams?: { q?: string };
}) {
  const q = searchParams?.q?.toLowerCase() ?? "";
  const session = await getServerSession();
  const orgId = session?.user?.orgId;
  if (!orgId) {
    redirect("/signup");
  }
  const missions = await db
    .select()
    .from(prestation)
    .where(eq(prestation.orgId, orgId))
    .orderBy(desc(prestation.createdAt))
    .limit(200);
  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Missions</h1>
          <p className="text-sm text-muted-foreground">
            Planifiez et suivez les prestations en cours.
          </p>
        </div>
        <div className="flex w-full flex-col gap-2 md:w-auto md:flex-row md:items-center">
          <form className="w-full md:w-64">
            <input
              name="q"
              defaultValue={q}
              placeholder="Rechercher..."
              className="w-full rounded-md border border-border bg-white px-3 py-2 text-sm"
            />
          </form>
          <Button asChild>
            <Link href="/missions/nouveau">Nouvelle mission</Link>
          </Button>
        </div>
      </div>

      <Card>
        <CardContent className="pt-6">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Reference</TableHead>
                <TableHead>Client</TableHead>
                <TableHead>Date</TableHead>
                <TableHead>Lieu</TableHead>
                <TableHead>Statut</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {missions
                .filter((mission) => {
                  if (!q) return true;
                  return (
                    mission.clientNom.toLowerCase().includes(q) ||
                    (mission.lieu ?? "").toLowerCase().includes(q) ||
                    mission.id.toLowerCase().includes(q)
                  );
                })
                .map((mission) => (
                <TableRow key={mission.id}>
                  <TableCell>
                    <Link
                      href={`/missions/${mission.id}`}
                      className="text-primary hover:underline"
                    >
                      {mission.id.slice(0, 8)}
                    </Link>
                  </TableCell>
                  <TableCell>{mission.clientNom}</TableCell>
                  <TableCell>
                    {mission.dateDebut
                      ? new Date(mission.dateDebut).toLocaleDateString("fr-FR")
                      : "-"}
                  </TableCell>
                  <TableCell>{mission.lieu ?? "-"}</TableCell>
                  <TableCell>
                    <Badge
                      variant={
                        mission.statut === "confirmee" ? "success" : "secondary"
                      }
                    >
                      {mission.statut}
                    </Badge>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium text-muted-foreground">
            Materiel assigne
          </CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground">
          Ajoutez ici l&apos;affectation materiel par mission (prochaine etape).
        </CardContent>
      </Card>
    </div>
  );
}
