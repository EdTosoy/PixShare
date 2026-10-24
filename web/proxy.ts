import { NextResponse } from "next/server";
import { clerkMiddleware } from "@clerk/nextjs/server";

const authorizedParties = process.env.CLERK_AUTHORIZED_PARTIES?.split(",").map(value => value.trim()).filter(Boolean);
if (process.env.PIXSHARE_ENVIRONMENT === "production") {
  if (!process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY?.startsWith("pk_live_") ||
      !process.env.CLERK_SECRET_KEY?.startsWith("sk_live_") || !authorizedParties?.length ||
      authorizedParties.some(value => {
        try { const url = new URL(value); return url.protocol !== "https:" || url.origin !== value || value.includes("*") || url.hostname === "localhost"; }
        catch { return true; }
      })) throw new Error("Production Clerk requires live keys and explicit HTTPS authorized origins");
}

export default process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY
  ? clerkMiddleware({ authorizedParties })
  : function proxy() {
      return NextResponse.next();
    };

export const config = {
  matcher: [
    "/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)",
    "/(api|trpc)(.*)",
    "/__clerk/(.*)",
  ],
};
