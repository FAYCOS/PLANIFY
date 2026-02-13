export const dynamic = "force-dynamic";

import Link from "next/link";

import { and, desc, eq, gte } from "drizzle-orm";

import { db } from "@/db";
import { materiel, materielPrestation, prestation } from "@/db/schema";
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

function formatEuro(value: string | null) {
  const number = Number(value ?? "0");
  return new Intl.NumberFormat("fr-FR", {
    style: "currency",
    currency: "EUR",
    maximumFractionDigits: 2,
  }).format(number);
}

export default async function MaterielPage() {
  const session = await getServerSession();
  const orgId = session?.user?.orgId;
  if (!orgId) {
    redirect("/signup");
  }
  const items = await db
    .select()
    .from(materiel)
    .where(eq(materiel.orgId, orgId))
    .orderBy(desc(materiel.createdAt));

  const today = new Date().toISOString().slice(0, 10);
  const reserved = await db
    .select({ materielId: materielPrestation.materielId })
    .from(materielPrestation)
    .leftJoin(prestation, eq(prestation.id, materielPrestation.prestationId))
    .where(and(eq(prestation.orgId, orgId), gte(prestation.dateDebut, today)));

  const reservedSet = new Set(reserved.map((row) => row.materielId));

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle>Materiel</CardTitle>
        <div className="flex gap-2">
          <Button asChild variant="outline">
            <Link href="/materiel/scan">Scan</Link>
          </Button>
          <Button asChild>
            <Link href="/materiel/nouveau">Nouveau materiel</Link>
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Nom</TableHead>
              <TableHead>Reference</TableHead>
              <TableHead>Statut</TableHead>
              <TableHead className="text-right">Prix HT</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {items.map((item) => {
              const status = reservedSet.has(item.id)
                ? "reserve"
                : item.statut ?? "disponible";
              return (
                <TableRow key={item.id}>
                  <TableCell>{item.nom}</TableCell>
                  <TableCell className="text-muted-foreground">
                    {item.codeBarre || item.numeroSerie || item.id.slice(0, 8)}
                  </TableCell>
                  <TableCell>
                    <Badge
                      variant={status === "disponible" ? "success" : "warning"}
                    >
                      {status}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-right">
                    {formatEuro(item.prixLocation?.toString() ?? "0")}
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}
