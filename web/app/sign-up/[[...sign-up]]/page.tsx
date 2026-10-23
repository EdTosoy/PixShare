"use client";

import { SignUp } from "@clerk/nextjs";
import Link from "next/link";
import { useSession } from "@/app/providers";

export default function SignUpPage() {
  const { configured } = useSession();
  return (
    <main id="main" className="auth-page">
      {configured ? (
        <SignUp
          appearance={{
            variables: { colorPrimary: "#35664e", colorMutedForeground: "var(--muted)", fontSize: "14px", borderRadius: "12px" },
          }}
        />
      ) : (
        <div className="state-panel">
          <h1>Sign-up isn’t configured yet.</h1>
          <p>Accounts are currently unavailable. You can still browse images.</p>
          <Link href="/explore" className="button primary">
            Explore images
          </Link>
        </div>
      )}
    </main>
  );
}
