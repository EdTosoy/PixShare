import { useEffect } from "react";

type DeletePostDialogProps = {
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
}: DeletePostDialogProps) {
  useEffect(() => {
    if (!open) {
      return;
    }

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape" && !isPending) {
        onClose();
      }
    };

    document.addEventListener("keydown", handleKeyDown);

    return () => {
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [open, isPending, onClose]);

  if (!open) {
    return null;
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
      role="presentation"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget && !isPending) {
          onClose();
        }
      }}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="delete-post-title"
        aria-describedby="delete-post-description"
        className="w-full max-w-md rounded-lg border border-gray-200 bg-white p-6 shadow-xl dark:border-[#30363d] dark:bg-[#161b22]"
      >
        <h2
          id="delete-post-title"
          className="text-lg font-semibold text-gray-900 dark:text-white"
        >
          Delete post?
        </h2>

        <p
          id="delete-post-description"
          className="mt-2 text-sm text-gray-600 dark:text-gray-400"
        >
          This action cannot be undone. The post and its uploaded file will be
          permanently deleted.
        </p>

        {error && (
          <div className="mt-4 rounded-md border border-red-300 bg-red-50 p-3 text-sm text-red-800 dark:border-red-900 dark:bg-[#2d1117] dark:text-red-300">
            {error.message}
          </div>
        )}

        <div className="mt-6 flex justify-end gap-3">
          <button
            type="button"
            onClick={onClose}
            disabled={isPending}
            className="rounded-md border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50 dark:border-[#30363d] dark:text-gray-300 dark:hover:bg-[#21262d]"
          >
            Cancel
          </button>

          <button
            type="button"
            onClick={onConfirm}
            disabled={isPending}
            className="rounded-md bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700 disabled:opacity-50"
          >
            {isPending ? "Deleting..." : "Delete post"}
          </button>
        </div>
      </div>
    </div>
  );
}
