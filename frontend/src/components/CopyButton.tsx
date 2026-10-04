import React, { useState } from 'react';
import { Copy, Check } from 'lucide-react';

interface CopyButtonProps {
  textToCopy: string | string[];
  label?: string;
  className?: string;
  size?: 'sm' | 'md';
}

export const CopyButton: React.FC<CopyButtonProps> = ({
  textToCopy,
  label = 'Copy all',
  className = '',
  size = 'md',
}) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = async (e: React.MouseEvent) => {
    e.stopPropagation();
    const payload = Array.isArray(textToCopy) ? textToCopy.join(', ') : textToCopy;
    try {
      await navigator.clipboard.writeText(payload);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback
    }
  };

  const isSmall = size === 'sm';

  return (
    <button
      type="button"
      onClick={handleCopy}
      aria-label={label}
      className={`inline-flex items-center gap-1.5 font-medium rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-sky-500 ${
        isSmall
          ? 'px-2 py-1 text-xs bg-slate-700/60 hover:bg-slate-700 text-slate-200'
          : 'px-3 py-1.5 text-xs md:text-sm bg-slate-800 hover:bg-slate-700 text-slate-100 border border-slate-700'
      } ${className}`}
    >
      {copied ? (
        <>
          <Check className={`${isSmall ? 'w-3 h-3' : 'w-3.5 h-3.5'} text-emerald-400`} />
          <span className="text-emerald-400">Copied!</span>
        </>
      ) : (
        <>
          <Copy className={`${isSmall ? 'w-3 h-3' : 'w-3.5 h-3.5'} text-slate-400`} />
          <span>{label}</span>
        </>
      )}
    </button>
  );
};
