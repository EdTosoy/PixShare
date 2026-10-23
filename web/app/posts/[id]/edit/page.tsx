import { EditPost } from "@/components/posts/EditPost";
export const metadata = { title: "Edit image" };
export default async function Page({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  return <EditPost id={(await params).id} />;
}
