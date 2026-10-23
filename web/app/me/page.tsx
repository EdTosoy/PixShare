import { PersonalGallery } from "@/components/PersonalGallery";
export const metadata = { title: "My gallery" };
export default async function Page({
  searchParams,
}: {
  searchParams: Promise<{ deleted?: string }>;
}) {
  return <PersonalGallery deleted={(await searchParams).deleted === "1"} />;
}
