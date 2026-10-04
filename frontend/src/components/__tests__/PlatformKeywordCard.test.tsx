import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { PlatformKeywordCard } from '../PlatformKeywordCard';
import type { PlatformKeywords } from '../../types';

describe('PlatformKeywordCard Component', () => {
  const sampleData: PlatformKeywords = {
    platform: 'amazon',
    keywords: [
      'oversized black tee',
      'cotton drop shoulder t-shirt',
      'baggy streetwear tee',
    ],
  };

  it('renders only plain keyword chips and copy button', () => {
    const { container } = render(<PlatformKeywordCard data={sampleData} />);

    // Platform header
    expect(screen.getByText(/Amazon\.in/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Copy all/i })).toBeInTheDocument();

    // Verify all keywords are in chips
    expect(screen.getByText('oversized black tee')).toBeInTheDocument();
    expect(screen.getByText('cotton drop shoulder t-shirt')).toBeInTheDocument();
    expect(screen.getByText('baggy streetwear tee')).toBeInTheDocument();

    // Verify chips are items in an unordered list
    const listItems = container.querySelectorAll('ul li');
    expect(listItems.length).toBe(3);

    // Verify strict guardrail: NO scores, volume numbers, percentages, or charts
    const cardText = container.textContent || '';
    expect(cardText).not.toMatch(/score/i);
    expect(cardText).not.toMatch(/volume/i);
    expect(cardText).not.toMatch(/\d+%/);
    expect(cardText).not.toMatch(/0\.\d+/); // No decimals like 0.85
  });
});
