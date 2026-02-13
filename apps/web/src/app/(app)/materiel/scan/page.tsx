import { ScanPanel } from "@/components/materiel/scan-panel";

export default function MaterielScanPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Scan materiel</h1>
        <p className="text-sm text-muted-foreground">
          Enregistrez les sorties et retours en temps reel.
        </p>
      </div>
      <ScanPanel />
    </div>
  );
}
