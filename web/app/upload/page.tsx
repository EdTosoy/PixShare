"use client";
import { AuthGate } from "@/components/Feedback";
import { PostForm } from "@/components/posts/PostForm";
export default function UploadPage() {
  return (
    <main id="main" className="page-shell form-shell">
      <AuthGate>
        <div className="page-heading">
          <span className="eyebrow">SEEN BY YOU. SHARED WITH EVERYONE.</span>
          <h1>
            Share a perspective<span className="accent">.</span>
          </h1>
          <p>A moment doesn’t need to be extraordinary to be worth sharing.</p>
        </div>
        <PostForm />
      </AuthGate>
    </main>
  );
}
