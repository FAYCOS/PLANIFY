"use client";

import { useEffect, useState } from "react";

export const dynamic = "force-dynamic";

import Link from "next/link";

import { FinanceHeader } from "@/components/finance/finance-header";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

type Transaction = {
  id: string;
  date: string;
  libelle: string;
  montant: string;
  tiers: string;
  statut: string;
};

const defaultTransactions: Transaction[] = [
  {
    id: "local-1",
    date: "08/02/2026",
    libelle: "Paiement devis D-2026-001",
    montant: "+2 450,00 €",
    tiers: "Antoine Anne-Laure",
    statut: "non_justifiee",
  },
];

export default function PaiementsPage() {
  const [transactions, setTransactions] =
    useState<Transaction[]>(defaultTransactions);
  const [selected, setSelected] = useState<Transaction>(defaultTransactions[0]);

  useEffect(() => {
    let mounted = true;
    void (async () => {
      const res = await fetch("/api/paiements");
      if (!res.ok) return;
      const rows = (await res.json()) as Array<{
        id: string;
        createdAt?: string;
        montant?: string;
        statut?: string;
        reference?: string;
        factureId?: string | null;
        devisId?: string | null;
      }>;
      const mapped = rows.map((row) => ({
        id: row.id,
        date: row.createdAt
          ? new Date(row.createdAt).toLocaleDateString("fr-FR")
          : "-",
        libelle: row.reference || "Paiement",
        montant: `${Number(row.montant || 0).toLocaleString("fr-FR", {
          minimumFractionDigits: 2,
        })} €`,
        tiers: row.factureId || row.devisId || "Client",
        statut: row.statut || "en_attente",
      }));
      if (mounted && mapped.length) {
        setTransactions(mapped);
        setSelected(mapped[0]);
      }
    })();
    return () => {
      mounted = false;
    };
  }, []);

  return (
    <div className="space-y-6">
      <FinanceHeader
        title="Transactions"
        subtitle="Suivez les mouvements et justificatifs"
        primaryAction={<Link href="/finance/paiements/nouveau">Nouveau</Link>}
      />
      <div className="grid gap-6 lg:grid-cols-[2fr_1fr]">
        <Card>
          <CardContent className="pt-6">
            <div className="mb-4 flex items-center gap-2">
              <Input placeholder="Rechercher une transaction..." />
              <Button variant="outline">Filtres</Button>
            </div>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Date</TableHead>
                  <TableHead>Libelle</TableHead>
                  <TableHead>Montant</TableHead>
                  <TableHead>Tiers</TableHead>
                  <TableHead>Statut</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {transactions.map((row) => (
                  <TableRow
                    key={row.id}
                    onClick={() => setSelected(row)}
                    className={
                      selected?.id === row.id
                        ? "bg-emerald-50"
                        : undefined
                    }
                  >
                    <TableCell>{row.date}</TableCell>
                    <TableCell>{row.libelle}</TableCell>
                    <TableCell className="font-medium text-emerald-700">
                      {row.montant}
                    </TableCell>
                    <TableCell>{row.tiers}</TableCell>
                    <TableCell>
                      <Badge
                        variant={
                          row.statut === "justifiee" ? "success" : "warning"
                        }
                      >
                        {row.statut.replace("_", " ")}
                      </Badge>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="space-y-4 pt-6">
            <div>
              <div className="text-sm text-muted-foreground">Selection</div>
              <div className="text-xl font-semibold">{selected?.montant}</div>
              <div className="text-xs text-muted-foreground">
                {selected?.libelle}
              </div>
            </div>
            <div className="space-y-1 text-sm">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Date</span>
                <span>{selected?.date}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Client</span>
                <span>{selected?.tiers}</span>
              </div>
            </div>
            <div className="space-y-2">
              <div className="text-sm font-medium">Justificatif</div>
              <div className="rounded-lg border border-dashed p-4 text-xs text-muted-foreground">
                Deposez un fichier PDF/JPG ou cliquez pour ajouter.
              </div>
              <Button variant="outline">Ajouter un justificatif</Button>
            </div>
            <div className="space-y-2">
              <div className="text-sm font-medium">Notes</div>
              <Textarea placeholder="Ajouter une note interne..." />
              <Button>Enregistrer</Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
