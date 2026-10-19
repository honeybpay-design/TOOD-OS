import { proxyToApi } from "@/lib/api-proxy";

export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  return proxyToApi("tenders", request, "session");
}

export async function POST(request: Request) {
  return proxyToApi("tenders", request, "session");
}
