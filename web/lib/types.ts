export type Post = {
  id: string;
  user_id: string;
  caption: string | null;
  url: string;
  file_name: string;
  file_type: string;
  created_at: string;
  updated_at: string;
  image?: {
    width: number;
    height: number;
    variants: { url: string; width: number; height: number }[];
  } | null;
};

export type CreatePostInput = {
  file: File;
  caption?: string;
};

export type UpdatePostInput = {
  caption?: string;
  file?: File;
};
