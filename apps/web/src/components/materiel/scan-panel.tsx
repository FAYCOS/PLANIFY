"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

type ScanResult = {
  status: "ok" | "error";
  message?: string;
  materiel?: {
    id: string;
    nom: string;
    numeroSerie?: string | null;
    codeBarre?: string | null;
    statut?: string | null;
  };
};

type ScanMode = "sortie" | "entree";

export function ScanPanel() {
  const [mode, setMode] = useState<ScanMode>("sortie");
  const [code, setCode] = useState("");
  const [history, setHistory] = useState<ScanResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [useCamera, setUseCamera] = useState(false);
  const [cameraError, setCameraError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const rafRef = useRef<number | null>(null);
  const detectorRef = useRef<BarcodeDetector | null>(null);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const handleScan = useCallback(async (forcedCode?: string) => {
    const scanCode = (forcedCode ?? code).trim();
    if (!scanCode) return;
    setLoading(true);
    try {
      const res = await fetch("/api/materiel/scan", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ code: scanCode, type: mode }),
      });
      if (!res.ok) {
        const payload = await res.json();
        setHistory((prev) => [
          {
            status: "error",
            message: payload.error || "Materiel introuvable",
          },
          ...prev,
        ]);
      } else {
        const payload = await res.json();
        setHistory((prev) => [
          {
            status: "ok",
            materiel: payload.materiel,
          },
          ...prev,
        ]);
      }
    } catch {
      setHistory((prev) => [
        { status: "error", message: "Erreur reseau" },
        ...prev,
      ]);
    } finally {
      setLoading(false);
      setCode("");
      inputRef.current?.focus();
    }
  }, [code, mode]);

  const stopCamera = () => {
    if (rafRef.current) {
      cancelAnimationFrame(rafRef.current);
      rafRef.current = null;
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
    detectorRef.current = null;
  };

  const scanLoop = useCallback(async () => {
    if (!videoRef.current || !detectorRef.current) return;
    try {
      const barcodes = await detectorRef.current.detect(videoRef.current);
      if (barcodes.length) {
        const rawValue = barcodes[0]?.rawValue;
        if (rawValue) {
          setUseCamera(false);
          stopCamera();
          await handleScan(rawValue);
          return;
        }
      }
    } catch {
      setCameraError("Erreur camera.");
    }
    rafRef.current = requestAnimationFrame(scanLoop);
  }, [handleScan]);

  useEffect(() => {
    if (!useCamera) {
      stopCamera();
      return;
    }

    let mounted = true;
    setCameraError(null);
    void (async () => {
      if (!("BarcodeDetector" in window)) {
        setCameraError("BarcodeDetector non supporte.");
        setUseCamera(false);
        return;
      }
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: "environment" },
        });
        if (!mounted) return;
        streamRef.current = stream;
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
          await videoRef.current.play();
        }
        detectorRef.current = new BarcodeDetector({
          formats: [
            "code_128",
            "code_39",
            "ean_13",
            "ean_8",
            "upc_a",
            "upc_e",
            "qr_code",
          ],
        });
        rafRef.current = requestAnimationFrame(scanLoop);
      } catch {
        setCameraError("Acces camera refuse.");
        setUseCamera(false);
      }
    })();

    return () => {
      mounted = false;
      stopCamera();
    };
  }, [useCamera, scanLoop]);

  return (
    <div className="grid gap-6 lg:grid-cols-[1.2fr_1fr]">
      <Card>
        <CardHeader>
          <CardTitle>Scan {mode === "sortie" ? "sortie" : "retour"}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex gap-2 flex-wrap">
            <Button
              variant={mode === "sortie" ? "default" : "outline"}
              onClick={() => setMode("sortie")}
            >
              Sortie
            </Button>
            <Button
              variant={mode === "entree" ? "default" : "outline"}
              onClick={() => setMode("entree")}
            >
              Retour
            </Button>
            <Button
              variant={useCamera ? "default" : "outline"}
              onClick={() => setUseCamera((prev) => !prev)}
            >
              Camera
            </Button>
          </div>

          <div className="space-y-2">
            <Input
              ref={inputRef}
              value={code}
              onChange={(event) => setCode(event.target.value)}
              placeholder="Scannez ou saisissez un code..."
              onKeyDown={(event) => {
                if (event.key === "Enter") handleScan();
              }}
            />
            <Button onClick={() => handleScan()} disabled={loading}>
              Valider
            </Button>
          </div>

          {useCamera ? (
            <div className="space-y-2">
              <div className="rounded-xl border bg-black/5 p-2">
                <video
                  ref={videoRef}
                  className="h-56 w-full rounded-lg object-cover"
                  muted
                  playsInline
                />
              </div>
              {cameraError ? (
                <div className="text-xs text-red-600">{cameraError}</div>
              ) : (
                <div className="text-xs text-muted-foreground">
                  Visez le code-barres dans le cadre.
                </div>
              )}
            </div>
          ) : null}

          <div className="text-xs text-muted-foreground">
            Le champ reste en focus pour lecture code-barres.
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Historique recent</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {history.length === 0 ? (
            <div className="text-sm text-muted-foreground">
              Aucun scan pour le moment.
            </div>
          ) : (
            history.slice(0, 8).map((item, index) => (
              <div
                key={`${item.materiel?.id ?? item.message}-${index}`}
                className="rounded-lg border bg-white px-3 py-2"
              >
                {item.status === "ok" ? (
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <div className="text-sm font-medium">
                        {item.materiel?.nom}
                      </div>
                      <div className="text-xs text-muted-foreground">
                        {item.materiel?.numeroSerie ||
                          item.materiel?.codeBarre ||
                          "Sans reference"}
                      </div>
                    </div>
                    <Badge variant="success">OK</Badge>
                  </div>
                ) : (
                  <div className="flex items-center justify-between gap-3">
                    <div className="text-sm">{item.message}</div>
                    <Badge variant="warning">Erreur</Badge>
                  </div>
                )}
              </div>
            ))
          )}
        </CardContent>
      </Card>
    </div>
  );
}
