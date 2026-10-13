import { useState } from "react";
import * as Tabs from "@radix-ui/react-tabs";
import type { PlatformName, PlatformResult } from "../../types";
import { DetailsAccordion } from "./DetailsAccordion";
import { KeywordSection } from "./KeywordSection";
import { TitleSection } from "./TitleSection";
import { TopScrapedTitles } from "./TopScrapedTitles";

export interface PlatformTabsProps {
  platforms: PlatformResult[];
}

const PLATFORM_LABELS: Record<string, string> = {
  amazon: "Amazon",
  myntra: "Myntra",
  flipkart: "Flipkart",
  meesho: "Meesho",
};

export function PlatformTabs({ platforms }: PlatformTabsProps) {
  const [activeTab, setActiveTab] = useState<string>(
    platforms[0]?.platform || "amazon"
  );

  if (!platforms || platforms.length === 0) {
    return null;
  }

  // Ensure activeTab is valid
  const currentTab = platforms.some((p) => p.platform === activeTab)
    ? activeTab
    : platforms[0]?.platform || "amazon";

  return (
    <Tabs.Root
      value={currentTab}
      onValueChange={setActiveTab}
      className="space-y-4"
    >
      {/* Tabs navigation list */}
      <Tabs.List className="flex border-b border-border space-x-1">
        {platforms.map((plat) => {
          const isSelected = plat.platform === currentTab;
          const kwCount = plat.keywords ? plat.keywords.length : 0;
          return (
            <Tabs.Trigger
              key={plat.platform}
              value={plat.platform}
              className={`flex items-center gap-2 px-5 py-3 text-sm font-medium border-b-2 -mb-px transition-colors cursor-pointer ${
                isSelected
                  ? "border-accent text-accent font-bold bg-surface"
                  : "border-transparent text-text-muted hover:text-text hover:border-border"
              }`}
            >
              <span>{PLATFORM_LABELS[plat.platform] || plat.platform}</span>
              <span
                className={`text-xs px-2 py-0.5 rounded-full font-mono font-medium ${
                  isSelected
                    ? "bg-accent/15 text-accent"
                    : "bg-surface-2 text-text-muted"
                }`}
              >
                {kwCount}
              </span>
            </Tabs.Trigger>
          );
        })}
      </Tabs.List>

      {/* Tabs content */}
      {platforms.map((plat) => (
        <Tabs.Content
          key={plat.platform}
          value={plat.platform}
          className="space-y-6 focus:outline-none"
        >
          {/* 1. Exact Ready-to-Use Titles */}
          <TitleSection
            platform={plat.platform as PlatformName}
            titles={plat.titles || []}
          />

          {/* 2. Top 10 Scraped Ranking Titles on Platform */}
          <TopScrapedTitles
            platform={plat.platform as PlatformName}
            competitors={plat.top_scraped_titles || []}
          />

          {/* 3. Keywords chips */}
          <KeywordSection
            platform={plat.platform}
            keywords={plat.keywords || []}
          />

          {/* 4. Details Accordion */}
          <DetailsAccordion
            platform={plat.platform}
            details={plat.details}
          />
        </Tabs.Content>
      ))}
    </Tabs.Root>
  );
}
