import { Link } from "react-router-dom";
import { ArrowRight, Compass } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

export default function Discover() {
  return (
    <div className="flex flex-col gap-7">
      <div>
        <p className="eyebrow">Discover</p>
        <h1 className="page-title mt-2">Find the next topic</h1>
        <p className="mt-2 max-w-xl text-sm leading-relaxed text-ink-500">
          Trend discovery pulls from Google News RSS, Hacker News, Reddit, uploaded Trends CSVs, and manual ideas,
          then scores each candidate for safety and carousel viability.
        </p>
      </div>
      <Card>
        <CardContent className="flex flex-col items-start gap-4 py-12">
          <div className="flex h-11 w-11 items-center justify-center rounded-full bg-ember-500/10 text-ember-600">
            <Compass className="h-5 w-5" />
          </div>
          <div>
            <p className="text-sm font-semibold text-ink-900">Discovery is the next build section.</p>
            <p className="mt-1 max-w-md text-sm leading-relaxed text-ink-500">
              Until it lands, start from a topic you already have. The pipeline and review queue are fully wired.
            </p>
          </div>
          <Button asChild>
            <Link to="/new">
              Create a job from a topic <ArrowRight className="h-4 w-4" />
            </Link>
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
