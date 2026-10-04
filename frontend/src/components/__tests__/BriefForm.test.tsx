import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { BriefForm } from '../BriefForm';

describe('BriefForm Component', () => {
  it('renders all platform options and handles submission with defaults', () => {
    const handleSubmit = vi.fn();
    render(<BriefForm onSubmit={handleSubmit} isRunning={false} />);

    expect(screen.getByText(/Amazon\.in/i)).toBeInTheDocument();
    expect(screen.getByText(/Myntra/i)).toBeInTheDocument();
    expect(screen.getByText(/Flipkart/i)).toBeInTheDocument();

    const submitBtn = screen.getByRole('button', { name: /Find keywords/i });
    fireEvent.click(submitBtn);

    expect(handleSubmit).toHaveBeenCalledTimes(1);
    const brief = handleSubmit.mock.calls[0][0];
    expect(brief.platforms).toEqual(['amazon', 'myntra', 'flipkart']);
    expect(brief.tshirt_type).toBe('oversized graphic tee');
    expect(brief.color).toBe('black');
  });

  it('validates empty required fields', () => {
    const handleSubmit = vi.fn();
    render(<BriefForm onSubmit={handleSubmit} isRunning={false} />);

    const typeInput = screen.getByPlaceholderText(/e\.g\. oversized graphic tee/i);
    fireEvent.change(typeInput, { target: { value: '' } });

    const submitBtn = screen.getByRole('button', { name: /Find keywords/i });
    fireEvent.click(submitBtn);

    expect(handleSubmit).not.toHaveBeenCalled();
    expect(screen.getByText(/T-shirt type is required/i)).toBeInTheDocument();
  });
});
