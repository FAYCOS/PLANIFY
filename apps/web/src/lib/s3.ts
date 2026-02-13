import { S3Client } from "@aws-sdk/client-s3";

const endpoint = process.env.S3_ENDPOINT || undefined;
const accessKeyId = process.env.S3_ACCESS_KEY;
const secretAccessKey = process.env.S3_SECRET;
const bucket = process.env.S3_BUCKET;
const region = process.env.S3_REGION || "us-east-1";

export const s3PublicUrl = process.env.S3_PUBLIC_URL || null;
export const s3Bucket = bucket || null;

export const s3 =
  accessKeyId && secretAccessKey && bucket
    ? new S3Client({
        region,
        endpoint,
        forcePathStyle: Boolean(endpoint),
        credentials: {
          accessKeyId,
          secretAccessKey,
        },
      })
    : null;
