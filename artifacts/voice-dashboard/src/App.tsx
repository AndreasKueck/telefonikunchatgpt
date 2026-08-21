import { type ReactNode } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Activity, Check, Clock3, Database, RefreshCw, Radio, Server, WifiOff } from 'lucide-react';
import { ErrorBoundary } from '@/components/error-boundary';
import { Toaster } from '@/components/ui/toaster';
import { TooltipProvider } from '@/components/ui/tooltip';
import { useVoiceHealth } from '@/hooks/use-voice-health';
import NotFound from '@/pages/not-found';
import {
  Route,
  Switch,
  useLocation,
  Router as WouterRouter,
} from 'wouter';

const queryClient = new QueryClient();

function Home() {
  const health = useVoiceHealth();
  const isLoading = health.isLoading;
  const isError = health.isError;
  const isHealthy = health.data?.status.toLowerCase() === 'healthy';

  const formatDate = (value: string | null | undefined) => {
    if (!value) return 'Not reported';
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return value;
    return new Intl.DateTimeFormat(undefined, {
      dateStyle: 'medium',
      timeStyle: 'short',
    }).format(date);
  };

  const formatRelative = (value: string | null | undefined) => {
    if (!value) return 'No update received';
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return 'Timestamp unavailable';
    const minutes = Math.max(0, Math.round((Date.now() - date.getTime()) / 60_000));
    if (minutes < 1) return 'Updated just now';
    if (minutes === 1) return 'Updated 1 min ago';
    return `Updated ${minutes} min ago`;
  };

  return (
    <div className="grain min-h-[100dvh] overflow-hidden bg-background">
      <div className="hairline-grid relative min-h-[100dvh]">
        <header className="mx-auto flex w-full max-w-[1320px] items-center justify-between px-5 py-5 sm:px-8 lg:px-12">
          <div className="flex items-center gap-3" data-testid="brand-voice-operations">
            <div className="relative flex h-10 w-10 items-center justify-center rounded-[13px] bg-[#192839] text-[#f7f1e5] shadow-sm">
              <Radio className="h-[18px] w-[18px]" strokeWidth={1.8} />
              <span className="absolute -right-1 -top-1 h-2.5 w-2.5 rounded-full border-2 border-background bg-[#d27a57]" />
            </div>
            <div>
              <p className="text-[13px] font-extrabold tracking-[-0.02em] text-foreground">voice / operations</p>
              <p className="font-mono text-[9px] uppercase tracking-[0.19em] text-muted-foreground">service console</p>
            </div>
          </div>
          <div className="hidden items-center gap-2.5 sm:flex" data-testid="polling-indicator">
            <span className="relative flex h-2 w-2">
              <span className="signal-breathe absolute inline-flex h-full w-full rounded-full bg-primary" />
              <span className="relative inline-flex h-2 w-2 rounded-full bg-primary" />
            </span>
            <span className="font-mono text-[10px] uppercase tracking-[0.16em] text-muted-foreground">Polling every 30s</span>
          </div>
        </header>

        <main className="mx-auto w-full max-w-[1320px] px-5 pb-12 pt-12 sm:px-8 sm:pt-20 lg:px-12 lg:pb-20">
          <section className="page-enter max-w-3xl">
            <p className="mb-5 flex items-center gap-2 font-mono text-[10px] font-medium uppercase tracking-[0.22em] text-primary">
              <span className="h-px w-7 bg-accent" />
              live service status
            </p>
            <h1 className="max-w-2xl text-[clamp(2.75rem,7vw,6.2rem)] font-extrabold leading-[0.98] tracking-[-0.075em] text-foreground">
              Is your assistant ready to answer?
            </h1>
            <p className="mt-6 max-w-xl text-[15px] leading-7 text-muted-foreground sm:text-base">
              One quiet read on the phone line, the assistant runtime, and its live knowledge connection.
            </p>
          </section>

          <section className="page-enter-delay mt-12 grid gap-5 lg:mt-16 lg:grid-cols-[minmax(0,1.35fr)_minmax(290px,.65fr)]">
            <div className={`relative overflow-hidden rounded-[24px] border p-6 shadow-md sm:p-9 ${isError ? 'border-[#e3c0b3] bg-[#fbf1ed]' : 'border-card-border bg-card'}`} data-testid="card-voice-status">
              <div className="absolute right-0 top-0 h-52 w-52 translate-x-1/3 -translate-y-1/3 rounded-full border border-primary/10" />
              <div className="absolute right-8 top-8 hidden h-40 w-40 rounded-full border border-primary/10 sm:block" />
              <div className="relative flex flex-col justify-between gap-12">
                <div className="flex items-start justify-between gap-5">
                  <div className="flex items-center gap-3">
                    <span className={`flex h-9 w-9 items-center justify-center rounded-full ${isError ? 'bg-[#f0d8ce] text-destructive' : 'bg-[#dceee7] text-primary'}`}>
                      {isError ? <WifiOff className="h-4 w-4" /> : <Activity className="h-4 w-4" />}
                    </span>
                    <div>
                      <p className="text-sm font-bold text-foreground">Phone assistant</p>
                      <p className="font-mono text-[10px] uppercase tracking-[0.15em] text-muted-foreground">primary voice line</p>
                    </div>
                  </div>
                  <span className="rounded-full border border-border bg-background/70 px-3 py-1.5 font-mono text-[10px] uppercase tracking-[0.14em] text-muted-foreground">
                    {isError ? 'connection issue' : 'current state'}
                  </span>
                </div>

                {isLoading ? (
                  <div className="animate-pulse" data-testid="status-loading">
                    <div className="h-16 w-56 rounded-lg bg-muted" />
                    <div className="mt-4 h-4 w-72 max-w-full rounded bg-muted" />
                  </div>
                ) : isError ? (
                  <div data-testid="status-error">
                    <h2 className="max-w-lg text-4xl font-extrabold tracking-[-0.055em] text-destructive sm:text-6xl">Status unavailable.</h2>
                    <p className="mt-4 max-w-md text-sm leading-6 text-[#875548]">
                      We could not reach the voice health endpoint. The assistant state may be out of date.
                    </p>
                    <button
                      type="button"
                      onClick={() => health.refetch()}
                      disabled={health.isFetching}
                      className="mt-7 inline-flex items-center gap-2 rounded-lg bg-[#192839] px-4 py-2.5 text-xs font-bold text-[#f7f1e5] transition-transform hover:-translate-y-0.5 disabled:cursor-wait disabled:opacity-70"
                      data-testid="button-retry-status"
                    >
                      <RefreshCw className={`h-3.5 w-3.5 ${health.isFetching ? 'animate-spin' : ''}`} />
                      Try again
                    </button>
                  </div>
                ) : (
                  <div data-testid="status-success">
                    <div className="flex flex-wrap items-end gap-x-5 gap-y-2">
                      <h2 className={`text-5xl font-extrabold tracking-[-0.07em] sm:text-7xl ${isHealthy ? 'text-primary' : 'text-accent'}`}>
                        {isHealthy ? 'Operational' : health.data?.status || 'Unknown'}
                      </h2>
                      <span className={`mb-2 flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-[0.14em] ${isHealthy ? 'text-primary' : 'text-accent'}`}>
                        <span className={`h-2 w-2 rounded-full ${isHealthy ? 'bg-primary' : 'bg-accent'}`} />
                        {health.data?.status}
                      </span>
                    </div>
                    <p className="mt-4 flex items-center gap-2 text-sm text-muted-foreground">
                      <Check className="h-4 w-4 text-primary" strokeWidth={2.5} />
                      Ready to receive incoming calls
                    </p>
                  </div>
                )}

                <div className="flex items-end justify-between gap-5 border-t border-border pt-5">
                  <div>
                    <p className="font-mono text-[9px] uppercase tracking-[0.16em] text-muted-foreground">Last signal</p>
                    <p className="mt-1 text-xs font-semibold text-foreground" data-testid="text-last-signal">{isError ? 'Unable to verify' : formatRelative(health.data?.last_updated)}</p>
                  </div>
                  <div className="flex h-8 items-end gap-1 opacity-70" aria-hidden="true">
                    {[10, 17, 12, 24, 15, 29, 13, 20, 10, 27, 16, 22, 12, 18, 10].map((height, index) => (
                      <span key={index} className="signal-bar w-1 rounded-full bg-primary" style={{ height }} />
                    ))}
                  </div>
                </div>
              </div>
            </div>

            <div className="page-enter-delay-2 flex flex-col rounded-[24px] border border-card-border bg-card p-6 shadow-sm sm:p-7" data-testid="card-system-details">
              <div className="flex items-center justify-between">
                <p className="font-mono text-[10px] font-medium uppercase tracking-[0.18em] text-muted-foreground">System details</p>
                <Server className="h-4 w-4 text-muted-foreground" strokeWidth={1.7} />
              </div>
              <div className="mt-7 divide-y divide-border">
                <div className="flex items-start justify-between gap-4 py-4 first:pt-0">
                  <div className="flex items-center gap-3">
                    <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-secondary text-muted-foreground"><Database className="h-3.5 w-3.5" /></span>
                    <span className="text-sm font-semibold text-foreground">Knowledge layer</span>
                  </div>
                  <span className={`mt-1 text-right font-mono text-[10px] uppercase tracking-[0.1em] ${health.data?.scio_data_available ? 'text-primary' : 'text-accent'}`} data-testid="status-scio-data">
                    {isLoading ? 'Checking' : isError ? 'Unverified' : health.data?.scio_data_available ? 'Available' : 'Unavailable'}
                  </span>
                </div>
                <div className="flex items-start justify-between gap-4 py-4">
                  <div className="flex items-center gap-3">
                    <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-secondary text-muted-foreground"><Clock3 className="h-3.5 w-3.5" /></span>
                    <span className="text-sm font-semibold text-foreground">Data refreshed</span>
                  </div>
                  <span className="mt-1 max-w-[125px] text-right text-xs leading-5 text-muted-foreground" data-testid="text-data-updated">
                    {isLoading ? 'Checking' : isError ? 'Unverified' : formatDate(health.data?.last_updated)}
                  </span>
                </div>
                <div className="flex items-start justify-between gap-4 py-4 last:pb-0">
                  <div className="flex items-center gap-3">
                    <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-secondary text-muted-foreground"><Radio className="h-3.5 w-3.5" /></span>
                    <span className="text-sm font-semibold text-foreground">Health endpoint</span>
                  </div>
                  <span className="mt-1 font-mono text-[10px] tracking-[0.05em] text-muted-foreground">/voice/health</span>
                </div>
              </div>
              <button
                type="button"
                onClick={() => health.refetch()}
                disabled={health.isFetching}
                className="mt-auto flex w-full items-center justify-center gap-2 rounded-xl border border-border bg-background px-4 py-3 text-xs font-bold text-foreground transition-all hover:border-primary/50 hover:bg-[#eef6f2] disabled:cursor-wait disabled:opacity-70"
                data-testid="button-refresh-status"
              >
                <RefreshCw className={`h-3.5 w-3.5 text-primary ${health.isFetching ? 'animate-spin' : ''}`} />
                {health.isFetching ? 'Checking now' : 'Refresh status'}
              </button>
            </div>
          </section>

          <footer className="page-enter-delay-2 mt-10 flex flex-col gap-3 border-t border-border pt-5 text-[11px] text-muted-foreground sm:flex-row sm:items-center sm:justify-between">
            <p>Only the current service signal is shown here.</p>
            <p className="font-mono tracking-[0.06em]" data-testid="text-last-updated">Checked {formatDate(health.data?.last_updated)}</p>
          </footer>
        </main>
      </div>
    </div>
  );
}

function Router() {
  return (
    // Keep a shared shell (sidebar, navbar) outside the boundary so it
    // survives a page crash.
    <RoutedErrorBoundary>
      <Switch>
        <Route path="/" component={Home} />
        <Route component={NotFound} />
      </Switch>
    </RoutedErrorBoundary>
  );
}

function RoutedErrorBoundary({ children }: { children: ReactNode }) {
  const [location] = useLocation();
  return <ErrorBoundary resetKey={location}>{children}</ErrorBoundary>;
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <TooltipProvider>
        <WouterRouter base={import.meta.env.BASE_URL.replace(/\/$/, '')}>
          <Router />
        </WouterRouter>
        <Toaster />
      </TooltipProvider>
    </QueryClientProvider>
  );
}

export default App;
