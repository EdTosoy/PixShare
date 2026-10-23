"use client";
import { useEffect, useRef } from "react";

type Props = {
  open: boolean;
  isPending: boolean;
  error: Error | null;
  onClose: () => void;
  onConfirm: () => void;
};
export function DeletePostDialog({
  open,
  isPending,
  error,
  onClose,
  onConfirm,
}: Props) {
  const ref = useRef<HTMLDialogElement>(null);
  const cancel = useRef<HTMLButtonElement>(null);
  const confirm = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    const dialog = ref.current;
    if (!dialog || !open) return;
    const trigger = document.activeElement as HTMLElement | null;
    dialog.showModal();
    cancel.current?.focus();
    return () => {
      dialog.close();
      trigger?.focus();
    };
  }, [open]);
  return (
    <dialog
      ref={ref}
      className="delete-dialog"
      aria-labelledby="delete-title"
      aria-describedby="delete-description"
      onKeyDown={(event) => {
        if (event.key !== "Tab" || isPending) return;
        // Native modality makes the page inert, but reverse Tab can still move
        // into browser chrome. Keep keyboard cycling within the two actions.
        if (event.shiftKey && document.activeElement === cancel.current) {
          event.preventDefault();
          confirm.current?.focus();
        } else if (!event.shiftKey && document.activeElement === confirm.current) {
          event.preventDefault();
          cancel.current?.focus();
        }
      }}
      onCancel={(event) => {
        event.preventDefault();
        if (!isPending) onClose();
      }}
    >
      <span className="eyebrow">YOUR GALLERY</span>
      <h2 id="delete-title">Delete this image?</h2>
      <p id="delete-description">
        This permanently removes your post and its image. This action cannot be
        undone.
      </p>
      {error && (
        <p role="alert" className="error-banner">
          {error.message}
        </p>
      )}
      <div className="form-actions">
        <button
          ref={cancel}
          className="button secondary"
          onClick={onClose}
          disabled={isPending}
        >
          Keep image
        </button>
        <button
          ref={confirm}
          className="button danger"
          onClick={onConfirm}
          disabled={isPending}
        >
          {isPending ? "Deleting…" : "Delete post"}
        </button>
      </div>
    </dialog>
  );
}
