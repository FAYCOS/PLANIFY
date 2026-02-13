export async function GET() {
  const body = `# HELP planify_up Application up
# TYPE planify_up gauge
planify_up 1
`;
  return new Response(body, {
    headers: {
      "Content-Type": "text/plain; version=0.0.4",
    },
  });
}
