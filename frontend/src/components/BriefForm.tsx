import React, { useState } from 'react';
import { Sparkles, Layers } from 'lucide-react';
import type { ProductBrief, PlatformName } from '../types';

interface BriefFormProps {
  onSubmit: (brief: ProductBrief) => void;
  isRunning: boolean;
}

const PLATFORMS: { id: PlatformName; label: string; badgeClass: string }[] = [
  { id: 'amazon', label: 'Amazon.in', badgeClass: 'border-amber-600/60 text-amber-400 bg-amber-950/30' },
  { id: 'myntra', label: 'Myntra', badgeClass: 'border-rose-600/60 text-rose-400 bg-rose-950/30' },
  { id: 'flipkart', label: 'Flipkart', badgeClass: 'border-blue-600/60 text-blue-400 bg-blue-950/30' },
];

export const BriefForm: React.FC<BriefFormProps> = ({ onSubmit, isRunning }) => {
  const [platforms, setPlatforms] = useState<PlatformName[]>(['amazon', 'myntra', 'flipkart']);
  const [tshirtType, setTshirtType] = useState('oversized graphic tee');
  const [color, setColor] = useState('black');
  const [gender, setGender] = useState<'men' | 'women' | 'unisex' | 'kids'>('men');
  const [fit, setFit] = useState('drop shoulder / loose fit');
  const [fabric, setFabric] = useState('100% combed cotton, 240 GSM');
  const [neck, setNeck] = useState('round neck');
  const [sleeve, setSleeve] = useState('half sleeve');
  const [printOrDesign, setPrintOrDesign] = useState('minimal back anime aesthetic graphic');
  const [occasion, setOccasion] = useState('streetwear / college casual');
  const [priceMin, setPriceMin] = useState<number | ''>(499);
  const [priceMax, setPriceMax] = useState<number | ''>(999);
  const [sizes, setSizes] = useState('S, M, L, XL, XXL');
  const [brandName, setBrandName] = useState('');
  const [extraDetails, setExtraDetails] = useState('');

  const [errors, setErrors] = useState<Record<string, string>>({});

  const togglePlatform = (p: PlatformName) => {
    if (platforms.includes(p)) {
      if (platforms.length === 1) return; // Must have at least one
      setPlatforms(platforms.filter((item) => item !== p));
    } else {
      setPlatforms([...platforms, p]);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const newErrors: Record<string, string> = {};

    if (platforms.length === 0) {
      newErrors.platforms = 'Select at least one marketplace platform.';
    }
    if (!tshirtType.trim()) {
      newErrors.tshirtType = 'T-shirt type is required.';
    }
    if (!color.trim()) {
      newErrors.color = 'Color is required.';
    }

    if (Object.keys(newErrors).length > 0) {
      setErrors(newErrors);
      return;
    }

    setErrors({});
    onSubmit({
      platforms,
      tshirt_type: tshirtType.trim(),
      color: color.trim(),
      gender,
      fit: fit.trim() || null,
      fabric: fabric.trim() || null,
      neck: neck.trim() || null,
      sleeve: sleeve.trim() || null,
      print_or_design: printOrDesign.trim() || null,
      occasion: occasion.trim() || null,
      price_min: typeof priceMin === 'number' ? priceMin : null,
      price_max: typeof priceMax === 'number' ? priceMax : null,
      sizes: sizes.trim() || null,
      brand_name: brandName.trim() || null,
      extra_details: extraDetails.trim() || null,
    });
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="p-6 rounded-2xl bg-slate-900 border border-slate-800 shadow-md transition-all"
    >
      <div className="flex items-center gap-2 mb-5">
        <Layers className="w-5 h-5 text-sky-400" />
        <h2 className="text-lg font-semibold text-slate-100">Product Brief</h2>
      </div>

      {/* Platforms multi-select */}
      <div className="mb-5">
        <label className="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">
          Target Marketplace Platforms *
        </label>
        <div className="flex flex-wrap gap-2.5">
          {PLATFORMS.map((p) => {
            const isSelected = platforms.includes(p.id);
            return (
              <button
                type="button"
                key={p.id}
                onClick={() => togglePlatform(p.id)}
                disabled={isRunning}
                className={`px-3.5 py-1.5 rounded-lg text-sm font-medium border transition-all ${
                  isSelected
                    ? `${p.badgeClass} ring-1 ring-sky-500/50 shadow-sm`
                    : 'bg-slate-800/60 border-slate-700/60 text-slate-400 hover:text-slate-200'
                } ${isRunning ? 'opacity-60 cursor-not-allowed' : 'cursor-pointer'}`}
              >
                {isSelected ? '✓ ' : '+ '}
                {p.label}
              </button>
            );
          })}
        </div>
        {errors.platforms && (
          <p className="mt-1.5 text-xs text-rose-400">{errors.platforms}</p>
        )}
      </div>

      {/* Row 1: T-Shirt Type, Color, Gender */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
        <div>
          <label className="block text-xs font-medium text-slate-300 mb-1.5">
            T-Shirt Type *
          </label>
          <input
            type="text"
            value={tshirtType}
            onChange={(e) => setTshirtType(e.target.value)}
            disabled={isRunning}
            placeholder="e.g. oversized graphic tee"
            className="w-full px-3 py-2 text-sm bg-slate-800/90 border border-slate-700 rounded-lg text-slate-100 focus:outline-none focus:ring-2 focus:ring-sky-500"
          />
          {errors.tshirtType && (
            <p className="mt-1 text-xs text-rose-400">{errors.tshirtType}</p>
          )}
        </div>

        <div>
          <label className="block text-xs font-medium text-slate-300 mb-1.5">
            Color *
          </label>
          <input
            type="text"
            value={color}
            onChange={(e) => setColor(e.target.value)}
            disabled={isRunning}
            placeholder="e.g. black, off-white, pista green"
            className="w-full px-3 py-2 text-sm bg-slate-800/90 border border-slate-700 rounded-lg text-slate-100 focus:outline-none focus:ring-2 focus:ring-sky-500"
          />
          {errors.color && (
            <p className="mt-1 text-xs text-rose-400">{errors.color}</p>
          )}
        </div>

        <div>
          <label className="block text-xs font-medium text-slate-300 mb-1.5">
            Gender
          </label>
          <div className="grid grid-cols-4 gap-1 p-0.5 bg-slate-800 rounded-lg border border-slate-700">
            {(['men', 'women', 'unisex', 'kids'] as const).map((g) => (
              <button
                type="button"
                key={g}
                onClick={() => setGender(g)}
                disabled={isRunning}
                className={`py-1.5 text-xs font-medium rounded-md capitalize transition-colors ${
                  gender === g
                    ? 'bg-sky-600 text-white shadow-sm'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                {g}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Row 2: Fit, Fabric, Neck, Sleeve */}
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4 mb-4">
        <div>
          <label className="block text-xs font-medium text-slate-300 mb-1.5">
            Fit
          </label>
          <input
            type="text"
            value={fit}
            onChange={(e) => setFit(e.target.value)}
            disabled={isRunning}
            placeholder="e.g. boxy, drop shoulder"
            className="w-full px-3 py-2 text-sm bg-slate-800/90 border border-slate-700 rounded-lg text-slate-100 focus:outline-none focus:ring-2 focus:ring-sky-500"
          />
        </div>

        <div>
          <label className="block text-xs font-medium text-slate-300 mb-1.5">
            Fabric / GSM
          </label>
          <input
            type="text"
            value={fabric}
            onChange={(e) => setFabric(e.target.value)}
            disabled={isRunning}
            placeholder="e.g. 240 GSM 100% cotton"
            className="w-full px-3 py-2 text-sm bg-slate-800/90 border border-slate-700 rounded-lg text-slate-100 focus:outline-none focus:ring-2 focus:ring-sky-500"
          />
        </div>

        <div>
          <label className="block text-xs font-medium text-slate-300 mb-1.5">
            Neck Type
          </label>
          <input
            type="text"
            value={neck}
            onChange={(e) => setNeck(e.target.value)}
            disabled={isRunning}
            placeholder="e.g. round neck, polo"
            className="w-full px-3 py-2 text-sm bg-slate-800/90 border border-slate-700 rounded-lg text-slate-100 focus:outline-none focus:ring-2 focus:ring-sky-500"
          />
        </div>

        <div>
          <label className="block text-xs font-medium text-slate-300 mb-1.5">
            Sleeve
          </label>
          <input
            type="text"
            value={sleeve}
            onChange={(e) => setSleeve(e.target.value)}
            disabled={isRunning}
            placeholder="e.g. half sleeve"
            className="w-full px-3 py-2 text-sm bg-slate-800/90 border border-slate-700 rounded-lg text-slate-100 focus:outline-none focus:ring-2 focus:ring-sky-500"
          />
        </div>
      </div>

      {/* Row 3: Design, Occasion, Price Range */}
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4 mb-4">
        <div>
          <label className="block text-xs font-medium text-slate-300 mb-1.5">
            Print or Design
          </label>
          <input
            type="text"
            value={printOrDesign}
            onChange={(e) => setPrintOrDesign(e.target.value)}
            disabled={isRunning}
            placeholder="e.g. typography back print"
            className="w-full px-3 py-2 text-sm bg-slate-800/90 border border-slate-700 rounded-lg text-slate-100 focus:outline-none focus:ring-2 focus:ring-sky-500"
          />
        </div>

        <div>
          <label className="block text-xs font-medium text-slate-300 mb-1.5">
            Occasion / Aesthetic
          </label>
          <input
            type="text"
            value={occasion}
            onChange={(e) => setOccasion(e.target.value)}
            disabled={isRunning}
            placeholder="e.g. college casual, streetwear"
            className="w-full px-3 py-2 text-sm bg-slate-800/90 border border-slate-700 rounded-lg text-slate-100 focus:outline-none focus:ring-2 focus:ring-sky-500"
          />
        </div>

        <div>
          <label className="block text-xs font-medium text-slate-300 mb-1.5">
            Price Range (₹)
          </label>
          <div className="flex items-center gap-2">
            <input
              type="number"
              value={priceMin}
              onChange={(e) => setPriceMin(e.target.value ? Number(e.target.value) : '')}
              disabled={isRunning}
              placeholder="Min"
              className="w-full px-3 py-2 text-sm bg-slate-800/90 border border-slate-700 rounded-lg text-slate-100 focus:outline-none focus:ring-2 focus:ring-sky-500"
            />
            <span className="text-slate-500">-</span>
            <input
              type="number"
              value={priceMax}
              onChange={(e) => setPriceMax(e.target.value ? Number(e.target.value) : '')}
              disabled={isRunning}
              placeholder="Max"
              className="w-full px-3 py-2 text-sm bg-slate-800/90 border border-slate-700 rounded-lg text-slate-100 focus:outline-none focus:ring-2 focus:ring-sky-500"
            />
          </div>
        </div>
      </div>

      {/* Row 4: Brand name & Extra details */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-5">
        <div>
          <label className="block text-xs font-medium text-slate-300 mb-1.5">
            Brand Name (Optional)
          </label>
          <input
            type="text"
            value={brandName}
            onChange={(e) => setBrandName(e.target.value)}
            disabled={isRunning}
            placeholder="Your brand name (excluded from generic keywords)"
            className="w-full px-3 py-2 text-sm bg-slate-800/90 border border-slate-700 rounded-lg text-slate-100 focus:outline-none focus:ring-2 focus:ring-sky-500"
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-slate-300 mb-1.5">
            Available Sizes
          </label>
          <input
            type="text"
            value={sizes}
            onChange={(e) => setSizes(e.target.value)}
            disabled={isRunning}
            placeholder="e.g. S, M, L, XL, XXL"
            className="w-full px-3 py-2 text-sm bg-slate-800/90 border border-slate-700 rounded-lg text-slate-100 focus:outline-none focus:ring-2 focus:ring-sky-500"
          />
        </div>
      </div>

      <div className="mb-6">
        <label className="block text-xs font-medium text-slate-300 mb-1.5">
          Every Detail (Free-text notes, special features, washes, etc.)
        </label>
        <textarea
          rows={3}
          value={extraDetails}
          onChange={(e) => setExtraDetails(e.target.value)}
          disabled={isRunning}
          placeholder="Mention any specific selling points (e.g. bio-washed, pre-shrunk, Japanese kanji back graphic, boxy streetwear drape, college audience)..."
          className="w-full px-3 py-2 text-sm bg-slate-800/90 border border-slate-700 rounded-lg text-slate-100 focus:outline-none focus:ring-2 focus:ring-sky-500 resize-none"
        />
      </div>

      {/* Submit Button */}
      <div className="flex items-center justify-between">
        <p className="text-xs text-slate-500">
          Press <kbd className="px-1.5 py-0.5 bg-slate-800 border border-slate-700 rounded text-slate-400">Ctrl+Enter</kbd> to run
        </p>
        <button
          type="submit"
          disabled={isRunning}
          className={`flex items-center gap-2 px-6 py-2.5 rounded-xl font-medium text-sm text-white shadow-md transition-all ${
            isRunning
              ? 'bg-slate-700 cursor-not-allowed opacity-70'
              : 'bg-gradient-to-r from-sky-500 to-blue-600 hover:from-sky-400 hover:to-blue-500 cursor-pointer'
          }`}
        >
          <Sparkles className="w-4 h-4 text-sky-200" />
          <span>{isRunning ? 'Analyzing...' : 'Find keywords'}</span>
        </button>
      </div>
    </form>
  );
};
