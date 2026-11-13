"use client";
import { use } from "react";
import DossierEditor from "@/components/DossierEditor";
import { useApi } from "@/lib/client";
import { Spinner, ErrorBox } from "@/components/ui";

export default function DossierPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const { data, error, loading, reload } = useApi<any>(`/api/dossiers/${id}`);
  if (loading && !data) return <Spinner />;
  if (error) return <ErrorBox message={error} onRetry={reload} />;
  return <DossierEditor existing={data} />;
}
