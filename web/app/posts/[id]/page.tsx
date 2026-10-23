import { PostView } from "@/components/posts/PostView";
export default async function Page({
  params,
  searchParams,
}: {
  params: Promise<{ id: string }>;
  searchParams: Promise<{ success?: string }>;
}) {
  return (
    <PostView id={(await params).id} success={(await searchParams).success} />
  );
}
