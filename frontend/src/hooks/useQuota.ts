import { useState, useEffect, useCallback } from 'react';
import type { QuotaInfo } from '../types';
import { getQuota } from '../api';

export function useQuota() {
  const [quota, setQuota] = useState<QuotaInfo | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchQuota = useCallback(async () => {
    try {
      setLoading(true);
      const data = await getQuota();
      setQuota(data);
      setError(null);
    } catch (err: unknown) {
      setError((err as Error)?.message || 'Failed to fetch quota');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchQuota();
  }, [fetchQuota]);

  return { quota, loading, error, refreshQuota: fetchQuota };
}
