import React, { useState } from 'react';
import { Shirt, AlertOctagon } from 'lucide-react';
import type { ProductBrief, PlatformKeywords } from './types';
import { createRun } from './api';
import { useRunStream } from './hooks/useRunStream';
import { useQuota } from './hooks/useQuota';
import { QuotaBadge } from './components/QuotaBadge';
import { BriefForm } from './components/BriefForm';
import { ProgressStrip } from './components/ProgressStrip';
import { PlatformKeywordCard } from './components/PlatformKeywordCard';
import { OtherFactors } from './components/OtherFactors';
import { ChatBlock } from './components/ChatBlock';

export const App: React.FC = () => {
  const [currentRunId, setCurrentRunId] = useState<string | null>(null);
  const [patchedPlatform, setPatchedPlatform] = useState<string | null>(null);
  const [startError, setStartError] = useState<string | null>(null);

  const { quota, loading: quotaLoading, error: quotaError, refreshQuota } = useQuota();
  const { state: streamState, patchKeywords } = useRunStream(currentRunId);

  const handleBriefSubmit = async (brief: ProductBrief) => {
    setStartError(null);
    try {
      const { run_id } = await createRun(brief);
      setCurrentRunId(run_id);
    } catch (err: unknown) {
      setStartError((err as Error)?.message || 'Failed to submit brief.');
    }
  };

  const handleKeywordsPatched = (patches: PlatformKeywords[]) => {
    patchKeywords(patches);
    if (patches.length > 0) {
      setPatchedPlatform(patches[0].platform);
      setTimeout(() => setPatchedPlatform(null), 3000);
    }
    refreshQuota();
  };

  const isRunning = streamState.status === 'running';
  const result = streamState.result;

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 py-8 px-4 sm:px-6 lg:px-8">
      <div className="max-w-5xl mx-auto">
        {/* Header */}
        <header className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-8 pb-4 border-b border-slate-800/80">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-gradient-to-br from-sky-500 to-blue-600 text-white shadow-md">
              <Shirt className="w-6 h-6" />
            </div>
            <div>
              <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-white">
                Marketplace Keyword Agent
              </h1>
              <p className="text-xs text-slate-400">
                AI-driven organic search intelligence for Amazon.in, Myntra &amp; Flipkart
              </p>
            </div>
          </div>

          <QuotaBadge quota={quota} loading={quotaLoading} error={quotaError} />
        </header>

        {/* Start / Submission Error Alert */}
        {startError && (
          <div className="mb-6 p-4 rounded-xl bg-rose-950/50 border border-rose-800 text-rose-300 text-sm flex items-center gap-2">
            <AlertOctagon className="w-5 h-5 shrink-0 text-rose-400" />
            <span>{startError}</span>
          </div>
        )}

        {/* 1. Brief Input Form */}
        <section aria-label="Product Brief Input">
          <BriefForm onSubmit={handleBriefSubmit} isRunning={isRunning} />
        </section>

        {/* 2. Thin Live Progress Strip */}
        <section aria-label="Pipeline Progress">
          <ProgressStrip
            status={streamState.status}
            stage={streamState.stage}
            message={streamState.message}
            warnings={streamState.warnings}
          />
        </section>

        {/* Pipeline Error Banner */}
        {streamState.error && (
          <div className="my-6 p-4 rounded-xl bg-rose-950/60 border border-rose-800 text-rose-300 text-sm flex items-center gap-2">
            <AlertOctagon className="w-5 h-5 shrink-0 text-rose-400" />
            <div>
              <strong className="block font-semibold">Execution Issue</strong>
              <span>{streamState.error}</span>
            </div>
          </div>
        )}

        {/* 3. Platform Results Section */}
        {result && (
          <main className="mt-8 space-y-8 animate-fadeIn">
            {/* Keyword Cards Grid (1 card per requested platform) */}
            <section aria-label="Platform Keyword Results">
              <h2 className="text-lg font-bold text-slate-100 mb-4">Marketplace Keywords</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
                {result.keywords.map((kwData) => (
                  <PlatformKeywordCard
                    key={kwData.platform}
                    data={kwData}
                    isPatched={patchedPlatform === kwData.platform}
                  />
                ))}
              </div>
            </section>

            {/* 4. Other Factors Section (Visually Separated) */}
            <section aria-label="Strategic Factors">
              <OtherFactors factors={result.other_factors} />
            </section>

            {/* 5. Interactive Chat Block */}
            {currentRunId && (
              <section aria-label="Analyst Chat Assistant">
                <ChatBlock
                  runId={currentRunId}
                  onPatchKeywords={handleKeywordsPatched}
                />
              </section>
            )}
          </main>
        )}
      </div>
    </div>
  );
};

export default App;
