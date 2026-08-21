import { useQuery } from '@tanstack/react-query';

export type VoiceHealth = {
  status: string;
  scio_data_available: boolean;
  last_updated: string | null;
};

async function getVoiceHealth(): Promise<VoiceHealth> {
  const response = await fetch('/voice/health', {
    method: 'GET',
    credentials: 'include',
    headers: { Accept: 'application/json' },
  });

  if (!response.ok) {
    throw new Error(`Health endpoint returned ${response.status}`);
  }

  const payload = (await response.json()) as Partial<VoiceHealth>;
  if (typeof payload.status !== 'string' || typeof payload.scio_data_available !== 'boolean') {
    throw new Error('Health endpoint returned an unexpected response');
  }

  return {
    status: payload.status,
    scio_data_available: payload.scio_data_available,
    last_updated: typeof payload.last_updated === 'string' ? payload.last_updated : null,
  };
}

export function useVoiceHealth() {
  return useQuery({
    queryKey: ['/voice/health'],
    queryFn: getVoiceHealth,
    refetchInterval: 30_000,
    refetchOnWindowFocus: true,
    retry: 1,
  });
}