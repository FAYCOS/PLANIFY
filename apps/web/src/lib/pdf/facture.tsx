import React from "react";
import {
  Document,
  Page,
  StyleSheet,
  Text,
  View,
} from "@react-pdf/renderer";

import type { facture as FactureRow } from "@/db/schema";

type FacturePdfProps = {
  facture: typeof FactureRow.$inferSelect;
  companyName?: string;
};

const styles = StyleSheet.create({
  page: {
    padding: 32,
    fontSize: 10,
    color: "#111827",
    fontFamily: "Helvetica",
  },
  header: {
    flexDirection: "row",
    justifyContent: "space-between",
    marginBottom: 16,
  },
  title: {
    fontSize: 18,
    fontWeight: 700,
  },
  section: {
    marginBottom: 12,
  },
  label: {
    fontSize: 9,
    color: "#6B7280",
  },
  row: {
    flexDirection: "row",
    justifyContent: "space-between",
  },
  table: {
    marginTop: 12,
    borderWidth: 1,
    borderColor: "#E5E7EB",
  },
  tableHeader: {
    flexDirection: "row",
    backgroundColor: "#F3F4F6",
    padding: 6,
  },
  tableRow: {
    flexDirection: "row",
    padding: 6,
    borderTopWidth: 1,
    borderColor: "#E5E7EB",
  },
  col: {
    flex: 1,
  },
  totals: {
    marginTop: 12,
    alignSelf: "flex-end",
    width: "50%",
  },
});

export function FacturePdf({ facture, companyName }: FacturePdfProps) {
  return (
    <Document>
      <Page size="A4" style={styles.page}>
        <View style={styles.header}>
          <View>
            <Text style={styles.title}>Facture</Text>
            <Text>Numero: {facture.numero}</Text>
            <Text>
              Date:{" "}
              {facture.dateCreation
                ? new Date(facture.dateCreation).toLocaleDateString("fr-FR")
                : "-"}
            </Text>
          </View>
          <View>
            <Text>{companyName ?? "Planify"}</Text>
          </View>
        </View>

        <View style={styles.section}>
          <Text style={styles.label}>Client</Text>
          <Text>{facture.clientNom}</Text>
          {facture.clientEmail ? <Text>{facture.clientEmail}</Text> : null}
          {facture.clientTelephone ? <Text>{facture.clientTelephone}</Text> : null}
          {facture.clientAdresse ? <Text>{facture.clientAdresse}</Text> : null}
        </View>

        <View style={styles.section}>
          <Text style={styles.label}>Prestation</Text>
          <Text>{facture.prestationTitre}</Text>
          {facture.prestationDescription ? (
            <Text>{facture.prestationDescription}</Text>
          ) : null}
        </View>

        <View style={styles.table}>
          <View style={styles.tableHeader}>
            <Text style={[styles.col, { flex: 3 }]}>Description</Text>
            <Text style={[styles.col, { textAlign: "right" }]}>Montant HT</Text>
          </View>
          <View style={styles.tableRow}>
            <Text style={[styles.col, { flex: 3 }]}>{facture.prestationTitre}</Text>
            <Text style={[styles.col, { textAlign: "right" }]}>
              {facture.montantHt ?? "0"}
            </Text>
          </View>
        </View>

        <View style={styles.totals}>
          <View style={styles.row}>
            <Text>Total HT</Text>
            <Text>{facture.montantHt ?? "0"}</Text>
          </View>
          <View style={styles.row}>
            <Text>TVA</Text>
            <Text>{facture.montantTva ?? "0"}</Text>
          </View>
          <View style={styles.row}>
            <Text>Total TTC</Text>
            <Text>{facture.montantTtc ?? "0"}</Text>
          </View>
          <View style={styles.row}>
            <Text>Montant paye</Text>
            <Text>{facture.montantPaye ?? "0"}</Text>
          </View>
        </View>
      </Page>
    </Document>
  );
}
