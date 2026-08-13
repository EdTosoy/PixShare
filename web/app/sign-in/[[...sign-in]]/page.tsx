import { SignIn } from "@clerk/nextjs";

export default function SignInPage() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-[#f6f8fa] px-6">
      <SignIn
        appearance={{
          variables: {
            colorPrimary: "#1f883d",
            borderRadius: "6px",
          },
        }}
      />
    </main>
  );
}
