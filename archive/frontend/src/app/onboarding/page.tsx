import OnboardingClient from "@/components/app/OnboardingClient";

export default function OnboardingPage({
  searchParams
}: {
  searchParams?: { username?: string };
}) {
  return <OnboardingClient initialUsername={searchParams?.username} />;
}
