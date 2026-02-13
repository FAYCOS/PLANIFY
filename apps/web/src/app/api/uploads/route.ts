import { NextResponse } from "next/server";
import { PutObjectCommand } from "@aws-sdk/client-s3";

import { s3, s3Bucket, s3PublicUrl } from "@/lib/s3";
import { requireOrgDb } from "@/lib/tenant";

const MAX_FILE_SIZE = 20 * 1024 * 1024; // 20 MB
const ALLOWED_MIME_TYPES = new Set([
  "image/png",
  "image/jpeg",
  "image/webp",
  "application/pdf",
]);

export async function POST(req: Request) {
  const guard = await requireOrgDb();
  if ("response" in guard) return guard.response;
  if (!s3 || !s3Bucket) {
    return NextResponse.json(
      { error: "Stockage S3 non configure" },
      { status: 500 },
    );
  }

  const formData = await req.formData();
  const file = formData.get("file");

  if (!file || !(file instanceof File)) {
    return NextResponse.json({ error: "Fichier manquant" }, { status: 400 });
  }
  if (file.size > MAX_FILE_SIZE) {
    return NextResponse.json({ error: "Fichier trop volumineux" }, { status: 400 });
  }
  if (file.type && !ALLOWED_MIME_TYPES.has(file.type)) {
    return NextResponse.json({ error: "Type de fichier non autorise" }, { status: 400 });
  }

  const safeName = file.name.replace(/[^a-zA-Z0-9._-]/g, "_");
  const objectKey = `${guard.orgId}/${Date.now()}-${safeName}`;
  const body = Buffer.from(await file.arrayBuffer());

  await s3.send(
    new PutObjectCommand({
      Bucket: s3Bucket,
      Key: objectKey,
      Body: body,
      ContentType: file.type || "application/octet-stream",
    }),
  );

  const publicUrl = s3PublicUrl
    ? `${s3PublicUrl.replace(/\/$/, "")}/${s3Bucket}/${objectKey}`
    : null;

  return NextResponse.json({ key: objectKey, url: publicUrl });
}
