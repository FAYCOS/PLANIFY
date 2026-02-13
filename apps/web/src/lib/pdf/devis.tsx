import React from "react";
import {
  Document,
  Image,
  Page,
  StyleSheet,
  Text,
  View,
} from "@react-pdf/renderer";

import type { devis as DevisRow } from "@/db/schema";

type DevisPdfProps = {
  devis: typeof DevisRow.$inferSelect;
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
  signature: {
    marginTop: 24,
    width: 160,
    height: 60,
    objectFit: "contain",
  },
});

export function DevisPdf({ devis, companyName }: DevisPdfProps) {
  return (
    <Document>
      <Page size="A4" style={styles.page}>
        <View style={styles.header}>
          <View>
            <Text style={styles.title}>Devis</Text>
            <Text>Numero: {devis.numero}</Text>
            <Text>
              Date:{" "}
              {devis.dateCreation
                ? new Date(devis.dateCreation).toLocaleDateString("fr-FR")
                : "-"}
            </Text>
          </View>
          <View>
            <Text>{companyName ?? "Planify"}</Text>
          </View>
        </View>

        <View style={styles.section}>
          <Text style={styles.label}>Client</Text>
          <Text>{devis.clientNom}</Text>
          {devis.clientEmail ? <Text>{devis.clientEmail}</Text> : null}
          {devis.clientTelephone ? <Text>{devis.clientTelephone}</Text> : null}
          {devis.clientAdresse ? <Text>{devis.clientAdresse}</Text> : null}
        </View>

        <View style={styles.section}>
          <Text style={styles.label}>Prestation</Text>
          <Text>{devis.prestationTitre}</Text>
          {devis.prestationDescription ? (
            <Text>{devis.prestationDescription}</Text>
          ) : null}
        </View>

        <View style={styles.table}>
          <View style={styles.tableHeader}>
            <Text style={[styles.col, { flex: 3 }]}>Description</Text>
            <Text style={[styles.col, { textAlign: "right" }]}>Montant HT</Text>
          </View>
          <View style={styles.tableRow}>
            <Text style={[styles.col, { flex: 3 }]}>{devis.prestationTitre}</Text>
            <Text style={[styles.col, { textAlign: "right" }]}>
              {devis.montantHt ?? "0"}
            </Text>
          </View>
        </View>

        <View style={styles.totals}>
          <View style={styles.row}>
            <Text>Total HT</Text>
            <Text>{devis.montantHt ?? "0"}</Text>
          </View>
          <View style={styles.row}>
            <Text>TVA</Text>
            <Text>{devis.montantTva ?? "0"}</Text>
          </View>
          <View style={styles.row}>
            <Text>Total TTC</Text>
            <Text>{devis.montantTtc ?? "0"}</Text>
          </View>
        </View>

        {devis.signatureImage ? (
          <Image style={styles.signature} src={devis.signatureImage} />
        ) : null}
      </Page>
    </Document>
  );
}
