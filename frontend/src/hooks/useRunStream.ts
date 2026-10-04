import { useReducer, useEffect, useCallback } from 'react';
import type { RunResult, SSEEvent, PlatformKeywords } from '../types';
import { streamEvents } from '../api';

export interface StreamState {
  status: 'idle' | 'running' | 'done' | 'error';
  stage: 'planner' | 'marketplace' | 'social' | 'analyst' | 'system';
  message: string;
  warnings: string[];
  result: RunResult | null;
  error: string | null;
}

type Action =
  | { type: 'START' }
  | { type: 'EVENT'; event: SSEEvent }
  | { type: 'ERROR'; message: string }
  | { type: 'PATCH_KEYWORDS'; patches: PlatformKeywords[] }
  | { type: 'RESET' };

const initialState: StreamState = {
  status: 'idle',
  stage: 'planner',
  message: '',
  warnings: [],
  result: null,
  error: null,
};

function streamReducer(state: StreamState, action: Action): StreamState {
  switch (action.type) {
    case 'START':
      return {
        ...initialState,
        status: 'running',
        message: 'Initializing multi-agent pipeline...',
      };
    case 'EVENT': {
      const { event } = action;
      if (event.type === 'stage') {
        return { ...state, stage: event.stage, message: event.message };
      }
      if (event.type === 'progress') {
        return { ...state, stage: event.stage, message: event.message };
      }
      if (event.type === 'warning') {
        return { ...state, warnings: [...state.warnings, event.message] };
      }
      if (event.type === 'result' && event.data) {
        return { ...state, result: event.data as unknown as RunResult };
      }
      if (event.type === 'done') {
        return { ...state, status: 'done', message: 'Keyword generation complete.' };
      }
      if (event.type === 'error') {
        return { ...state, status: 'error', error: event.message };
      }
      return state;
    }
    case 'ERROR':
      return { ...state, status: 'error', error: action.message };
    case 'PATCH_KEYWORDS': {
      if (!state.result) return state;
      const patchMap = new Map(action.patches.map((p) => [p.platform, p.keywords]));
      const updatedKeywords = state.result.keywords.map((item) => {
        if (patchMap.has(item.platform)) {
          return { ...item, keywords: patchMap.get(item.platform)! };
        }
        return item;
      });
      return {
        ...state,
        result: {
          ...state.result,
          keywords: updatedKeywords,
        },
      };
    }
    case 'RESET':
      return initialState;
    default:
      return state;
  }
}

export function useRunStream(runId: string | null) {
  const [state, dispatch] = useReducer(streamReducer, initialState);

  useEffect(() => {
    if (!runId) return;

    dispatch({ type: 'START' });

    const cleanup = streamEvents(
      runId,
      (event) => dispatch({ type: 'EVENT', event }),
      (errMsg) => dispatch({ type: 'ERROR', message: errMsg })
    );

    return () => {
      cleanup();
    };
  }, [runId]);

  const patchKeywords = useCallback((patches: PlatformKeywords[]) => {
    dispatch({ type: 'PATCH_KEYWORDS', patches });
  }, []);

  const reset = useCallback(() => {
    dispatch({ type: 'RESET' });
  }, []);

  return { state, patchKeywords, reset };
}
