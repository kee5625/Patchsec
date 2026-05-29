import { useEffect, useRef, useState } from "react";
import {
  Accordion,
  AccordionDetails,
  AccordionSummary,
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  Divider,
  LinearProgress,
  Paper,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import SecurityIcon from "@mui/icons-material/Security";
import { Finding, Job, Severity, getJob, startScan } from "./api";

const SEV_COLOR: Record<Severity, string> = {
  critical: "#d32f2f",
  high: "#f57c00",
  medium: "#fbc02d",
  low: "#0288d1",
  info: "#757575",
};

const TERMINAL = (s: Job["state"]) => s === "done" || s === "error";

function FindingCard({ f }: { f: Finding }) {
  return (
    <Accordion disableGutters sx={{ bgcolor: "#1a1a1a" }}>
      <AccordionSummary expandIcon={<ExpandMoreIcon />}>
        <Stack direction="row" spacing={1} alignItems="center" className="w-full">
          <Chip
            label={f.severity}
            size="small"
            sx={{ bgcolor: SEV_COLOR[f.severity], color: "#fff", fontWeight: 700 }}
          />
          <Chip label={f.category} size="small" variant="outlined" />
          <Chip label={f.source} size="small" variant="outlined" />
          <Typography className="flex-1 truncate" title={f.title}>
            {f.title}
          </Typography>
        </Stack>
      </AccordionSummary>
      <AccordionDetails>
        <Typography variant="caption" color="text.secondary">
          {f.file}
          {f.line != null ? `:${f.line}` : ""} · confidence: {f.confidence}
        </Typography>
        <Typography variant="body2" sx={{ mt: 1, whiteSpace: "pre-wrap" }}>
          {f.detail}
        </Typography>
      </AccordionDetails>
    </Accordion>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <Box>
      <Typography variant="caption" color="text.secondary">
        {label}
      </Typography>
      <Typography variant="body1" className="truncate" sx={{ maxWidth: 220 }}>
        {value}
      </Typography>
    </Box>
  );
}

function JobPanel({ job }: { job: Job }) {
  const running = !TERMINAL(job.state);
  const r = job.result;
  return (
    <Stack spacing={2} className="h-full overflow-auto p-6">
      <Stack direction="row" spacing={1} alignItems="center">
        <Typography variant="h6">Scan</Typography>
        <Chip
          label={job.state}
          color={
            job.state === "done"
              ? "success"
              : job.state === "error"
              ? "error"
              : "info"
          }
          size="small"
        />
        <Typography variant="caption" color="text.secondary">
          {job.id}
        </Typography>
      </Stack>

      <Typography variant="body2" color="text.secondary">
        {job.git_url}
      </Typography>

      {running && (
        <Box>
          <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1 }}>
            <CircularProgress size={16} />
            <Typography variant="body2">{job.progress}</Typography>
          </Stack>
          <LinearProgress />
        </Box>
      )}

      {job.state === "error" && <Alert severity="error">{job.error}</Alert>}

      {r && (
        <>
          <Divider />
          <Stack direction="row" spacing={3}>
            <Stat label="Repo" value={r.repo} />
            <Stat label="Findings" value={String(r.findings.length)} />
            <Stat label="Scanned" value={String(r.files_scanned)} />
            <Stat label="Skipped" value={String(r.files_skipped)} />
          </Stack>
          {r.truncated && (
            <Alert severity="warning">
              Repo truncated to fit scan limits — not all files analyzed.
            </Alert>
          )}
          {r.notes.map((n, i) => (
            <Alert key={i} severity="info">
              {n}
            </Alert>
          ))}
          <Stack spacing={1}>
            {r.findings.length === 0 ? (
              <Typography color="text.secondary">No findings.</Typography>
            ) : (
              r.findings.map((f, i) => <FindingCard key={i} f={f} />)
            )}
          </Stack>
        </>
      )}
    </Stack>
  );
}

export default function App() {
  const [url, setUrl] = useState("");
  const [token, setToken] = useState("");
  const [job, setJob] = useState<Job | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const timer = useRef<number | null>(null);

  useEffect(() => {
    if (!job || TERMINAL(job.state)) {
      if (timer.current) window.clearInterval(timer.current);
      return;
    }
    timer.current = window.setInterval(async () => {
      try {
        const next = await getJob(job.id);
        setJob(next);
      } catch (e) {
        setError(String(e));
      }
    }, 1500);
    return () => {
      if (timer.current) window.clearInterval(timer.current);
    };
  }, [job?.id, job?.state]);

  async function onScan() {
    setError(null);
    setSubmitting(true);
    try {
      const j = await startScan(url.trim(), token.trim() || undefined);
      setJob(j);
    } catch (e) {
      setError(String(e));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Box className="flex h-full">
      {/* Left: form */}
      <Box className="w-1/2 flex items-center justify-center p-8">
        <Paper elevation={3} className="w-full max-w-md p-8">
          <Stack spacing={3}>
            <Stack direction="row" spacing={1} alignItems="center">
              <SecurityIcon color="primary" />
              <Typography variant="h5" fontWeight={700}>
                Patchsec
              </Typography>
            </Stack>
            <Typography variant="body2" color="text.secondary">
              Scan a public GitHub repo for security vulnerabilities and major
              logic problems.
            </Typography>
            <TextField
              label="GitHub repo URL"
              placeholder="https://github.com/owner/repo"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              fullWidth
            />
            <TextField
              label="GitHub token (optional)"
              placeholder="ghp_… raises rate limit / private repos"
              type="password"
              value={token}
              onChange={(e) => setToken(e.target.value)}
              fullWidth
            />
            <Button
              variant="contained"
              size="large"
              disabled={!url.trim() || submitting}
              onClick={onScan}
            >
              {submitting ? "Starting…" : "Scan repo"}
            </Button>
            {error && <Alert severity="error">{error}</Alert>}
          </Stack>
        </Paper>
      </Box>

      <Divider orientation="vertical" flexItem />

      {/* Right: job status */}
      <Box className="w-1/2 h-full">
        {job ? (
          <JobPanel job={job} />
        ) : (
          <Box className="flex h-full items-center justify-center">
            <Typography color="text.secondary">
              Start a scan to see live status here.
            </Typography>
          </Box>
        )}
      </Box>
    </Box>
  );
}
