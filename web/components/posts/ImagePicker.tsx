"use client";
import Image from "next/image";
import { useEffect, useState } from "react";
import { imageDescription } from "@/lib/images";
import type { Post } from "@/lib/types";
import { PostImage } from "./PostImage";

export const UPLOAD_HELP = "JPEG, PNG, or WebP. Up to 10 MB and 16 megapixels.";
export function ImagePicker({
  onChange,
  currentPost,
  disabled = false,
}: {
  onChange: (file: File | null, error: string | null) => void;
  currentPost?: Post;
  disabled?: boolean;
}) {
  const [selection, setSelection] = useState<{
    name: string;
    url: string;
  } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [dragging, setDragging] = useState(false);
  useEffect(
    () => () => {
      if (selection) URL.revokeObjectURL(selection.url);
    },
    [selection],
  );
  function selectFile(file?: File) {
    if (disabled || !file) return;
    let problem: string | null = null;
    if (!["image/jpeg", "image/png", "image/webp"].includes(file.type))
      problem = "Choose a JPEG, PNG, or WebP image.";
    else if (file.size > 10 * 1024 * 1024)
      problem = "Your image is too large. The maximum size is 10 MB.";
    else if (file.size === 0)
      problem = "This file is empty. Please choose an image.";
    setError(problem);
    setSelection(
      problem ? null : { name: file.name, url: URL.createObjectURL(file) },
    );
    onChange(problem ? null : file, problem);
  }
  const source = selection?.url ?? currentPost?.url;
  return (
    <div>
      <div
        className={`image-picker ${dragging ? "dragging" : ""}`}
        onDragOver={(event) => {
          event.preventDefault();
          if (!disabled) setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(event) => {
          event.preventDefault();
          setDragging(false);
          selectFile(event.dataTransfer.files[0]);
        }}
      >
        {source && (
          <div className="upload-preview">
            {selection ? <Image
              src={selection.url}
              alt="Image preview"
              fill
              unoptimized
              sizes="(max-width: 700px) 100vw, 640px"
              className="object-contain"
              onError={() => {
                if (selection) {
                  setError(
                    "This image cannot be previewed. Please choose a valid image.",
                  );
                  onChange(null, "Please choose a valid image.");
                }
              }}
            /> : currentPost && <PostImage
              post={currentPost}
              alt={imageDescription(currentPost)}
              sizes="(max-width: 700px) calc(100vw - 78px), 600px"
              className="object-contain"
              eager
            />}
          </div>
        )}
        <label className="picker-label">
          <strong>
            {selection?.name ??
              (currentPost ? "Replace this image" : "Drop your image here")}
          </strong>
          <span>
            {source
              ? "Choose a different image"
              : "or browse files on your device"}
          </span>
          <span className="muted small" id="upload-help">
            {UPLOAD_HELP}
          </span>
          <input
            type="file"
            aria-label={currentPost ? "Replace image" : "Image"}
            aria-invalid={Boolean(error)}
            aria-describedby="upload-help upload-error"
            accept="image/jpeg,image/png,image/webp"
            disabled={disabled}
            onChange={(event) => {
              selectFile(event.target.files?.[0]);
              event.target.value = "";
            }}
          />
        </label>
      </div>
      <p
        id="upload-error"
        className="form-error"
        role={error ? "alert" : undefined}
      >
        {error}
      </p>
    </div>
  );
}
