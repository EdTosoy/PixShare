"use client";
import { SignIn } from "@clerk/nextjs";
import Link from "next/link";
import { useSession } from "@/app/providers";
export default function SignInPage() {
  const { configured } = useSession();
  return (
    <main id="main" className="auth-page">
      {configured ? (
        <SignIn
          withSignUp={false}
          appearance={{
            variables: { colorPrimary: "#35664e", colorMutedForeground: "var(--muted)", fontSize: "14px", borderRadius: "12px" },
          }}
        />
      ) : (
        <div className="state-panel">
          <h1>Sign-in isn’t configured yet.</h1>
          <p>
            Add your Clerk publishable and secret keys to the local environment
            to enable accounts.
          </p>
          <Link href="/explore" className="button primary">
            Explore images
          </Link>
        </div>
      )}
    </main>
  );
}
