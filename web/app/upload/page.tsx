"use client";
import { AuthGate } from "@/components/Feedback";
import { PostForm } from "@/components/posts/PostForm";
export default function UploadPage() {
  return (
    <main id="main" className="page-shell form-shell">
      <AuthGate>
        <div className="page-heading">
          <h1>Add a photograph.</h1>
          <p>Choose a photo and give it a caption.</p>
        </div>
        <PostForm />
      </AuthGate>
    </main>
  );
}
