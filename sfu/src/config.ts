/**
 * SFU Server Configuration
 * Loads environment variables and provides typed config object.
 */

import { config as dotenvConfig } from 'dotenv';
import { cpus } from 'os';
import type { types as mediasoupTypes } from 'mediasoup';

dotenvConfig();

function envInt(key: string, fallback: number): number {
  const v = process.env[key];
  return v ? parseInt(v, 10) : fallback;
}

function envFloat(key: string, fallback: number): number {
  const v = process.env[key];
  return v ? parseFloat(v) : fallback;
}

function envStr(key: string, fallback: string): string {
  return process.env[key] ?? fallback;
}

function envBool(key: string, fallback: boolean): boolean {
  const raw = process.env[key];
  if (raw === undefined) return fallback;

  switch (raw.trim().toLowerCase()) {
    case '1':
    case 'true':
    case 'yes':
    case 'on':
      return true;
    case '0':
    case 'false':
    case 'no':
    case 'off':
      return false;
    default:
      return fallback;
  }
}

function resolveSfuHost(): string {
  const configuredHost = envStr('SFU_HOST', '0.0.0.0').trim();
  if (!configuredHost) {
    return '0.0.0.0';
  }

  const normalized = configuredHost.toLowerCase();
  if (normalized === 'localhost' || normalized === '127.0.0.1' || normalized === '::1') {
    console.warn(
      `[config] SFU_HOST=${configuredHost} is loopback-only. ` +
        'Overriding to 0.0.0.0 for LAN reachability.'
    );
    return '0.0.0.0';
  }

  return configuredHost;
}

function normalizePath(value: string): string {
  const trimmed = value.trim();
  if (!trimmed) return '/';
  return trimmed.startsWith('/') ? trimmed : `/${trimmed}`;
}

function parseList(raw: string): string[] {
  return raw
    .split(',')
    .map((entry) => entry.trim())
    .filter(Boolean);
}

function parseAllowedOriginPatterns(): string[] {
  const raw = envStr(
    'SIGNALING_ALLOWED_ORIGINS',
    'https://*.instatunnel.my,http://*.instatunnel.my'
  );
  return parseList(raw);
}

function parseWsPaths(): string[] {
  const raw = envStr('SIGNALING_WS_PATHS', '/ws/sfu,/ws/sfu/');
  const normalized = new Set(parseList(raw).map(normalizePath));
  normalized.add('/ws/sfu');
  normalized.add('/ws/sfu/');
  return Array.from(normalized);
}

/**
 * Parse TURN URLs.
 * Supports:
 * - TURN_URLS=turn:global.turn.twilio.com:3478?transport=udp,turns:global.turn.twilio.com:443?transport=tcp
 * - TURN_URL=turn:your-project.metered.live:443?transport=tcp (legacy single URL)
 */
function parseTurnUrls(): string[] {
  const urls = parseList(envStr('TURN_URLS', ''));
  const single = envStr('TURN_URL', '').trim();
  if (single) {
    urls.push(single);
  }
  return Array.from(new Set(urls));
}

function parseListenIpEntry(entry: string): mediasoupTypes.TransportListenIp {
  const trimmed = entry.trim();
  if (!trimmed) {
    return { ip: '0.0.0.0' };
  }

  // Bracket format for IPv6: "[::1]:203.0.113.10"
  const bracketMatch = trimmed.match(/^\[([^\]]+)\](?::(.+))?$/);
  if (bracketMatch) {
    return {
      ip: bracketMatch[1] || '::',
      announcedIp: bracketMatch[2] || undefined,
    };
  }

  // Preferred format for IPv6-safe parsing: "listenIp|announcedIp"
  const pipeIndex = trimmed.indexOf('|');
  if (pipeIndex >= 0) {
    const ip = trimmed.slice(0, pipeIndex).trim();
    const announcedIp = trimmed.slice(pipeIndex + 1).trim();
    return {
      ip: ip || '0.0.0.0',
      announcedIp: announcedIp || undefined,
    };
  }

  // Legacy IPv4 format: "listenIp:announcedIp"
  const parts = trimmed.split(':');
  if (parts.length === 2) {
    const [ip, announcedIp] = parts;
    return {
      ip: ip || '0.0.0.0',
      announcedIp: announcedIp || undefined,
    };
  }

  // IPv6 or plain host/IP without announcedIp.
  return {
    ip: trimmed,
  };
}

/**
 * Parse WEBRTC_LISTEN_IPS from env.
 * Supported formats:
 * - WEBRTC_LISTEN_IP + WEBRTC_ANNOUNCED_IP
 * - WEBRTC_LISTEN_IPS="ip1:announcedIp1,ip2:announcedIp2" (legacy IPv4)
 * - WEBRTC_LISTEN_IPS="ip1|announcedIp1,ip2|announcedIp2" (IPv6-safe)
 */
function parseListenIps(): mediasoupTypes.TransportListenIp[] {
  const explicitIp = envStr('WEBRTC_LISTEN_IP', '').trim();
  const explicitAnnouncedIp = envStr('WEBRTC_ANNOUNCED_IP', '').trim();
  if (explicitIp) {
    return [
      {
        ip: explicitIp,
        announcedIp: explicitAnnouncedIp || undefined,
      },
    ];
  }

  const raw = envStr('WEBRTC_LISTEN_IPS', '0.0.0.0');
  return parseList(raw).map((entry) => {
    const parsed = parseListenIpEntry(entry);
    if (!parsed.announcedIp && explicitAnnouncedIp) {
      return {
        ...parsed,
        announcedIp: explicitAnnouncedIp,
      };
    }
    return parsed;
  });
}

/**
 * Strict validation: if listenIp is a wildcard (0.0.0.0 / ::) and
 * announcedIp is absent, the server CANNOT expose correct SDP candidates
 * to external clients — which causes black video / no RTP.
 *
 * We throw a fatal error so startup fails loudly instead of silently
 * producing broken connections.
 */
function validateListenIps(
  listenIps: mediasoupTypes.TransportListenIp[]
): void {
  for (const entry of listenIps) {
    const ip = String(entry.ip || '').trim();
    const announcedIp = String(entry.announcedIp || '').trim();
    const isWildcard = ip === '0.0.0.0' || ip === '::';

    if (isWildcard && !announcedIp) {
      throw new Error(
        `[config] FATAL: listenIp "${ip}" is a wildcard but announcedIp is not set. ` +
        'External clients will receive SDP with "0.0.0.0" as the media endpoint, ' +
        'causing black video / no RTP. ' +
        'Fix: set WEBRTC_ANNOUNCED_IP=<your LAN or public IP> in sfu/.env and restart.'
      );
    }
  }
}

function parseWebRtcTransportProtocols(): {
  enableUdp: boolean;
  enableTcp: boolean;
  preferUdp: boolean;
  preferTcp: boolean;
} {
  let enableUdp = envBool('WEBRTC_ENABLE_UDP', true);
  let enableTcp = envBool('WEBRTC_ENABLE_TCP', true);
  const preferUdp = envBool('WEBRTC_PREFER_UDP', false);
  const preferTcp = envBool('WEBRTC_PREFER_TCP', true);

  // Keep server reachable even when misconfigured.
  if (!enableUdp && !enableTcp) {
    enableTcp = true;
    enableUdp = false;
  }

  return {
    enableUdp,
    enableTcp,
    preferUdp,
    preferTcp,
  };
}

function warnIfSuspiciousBitrate(
  key: string,
  value: number,
  minExpectedBps: number
): void {
  if (!Number.isFinite(value) || value <= 0) {
    throw new Error(
      `[config] FATAL: ${key} must be a positive integer bitrate in bps, got "${value}".`
    );
  }

  if (value < minExpectedBps) {
    const suggestedBps = value * 1000;
    console.warn(
      `[config] ${key}=${value} looks very low for bps. ` +
        `mediasoup expects bits per second; if you meant kbps, use ${suggestedBps}.`
    );
  }
}

export const config = {
  // ── Server ──
  port: envInt('SFU_PORT', 4443),
  // LAN-safe default (listen on all IPv4 interfaces, not loopback only).
  host: resolveSfuHost(),

  // ── TLS ──
  tls: {
    cert: envStr('TLS_CERT', ''),
    key: envStr('TLS_KEY', ''),
  },

  // ── Mediasoup ──
  mediasoup: {
    numWorkers: envInt('MEDIASOUP_WORKERS', 0) || cpus().length,
    workerSettings: {
      logLevel: 'warn' as mediasoupTypes.WorkerLogLevel,
      logTags: [
        'info',
        'ice',
        'dtls',
        'rtp',
        'srtp',
        'rtcp',
        'rtx',
        'bwe',
        'score',
        'simulcast',
        'svc',
      ] as mediasoupTypes.WorkerLogTag[],
      workerBin: envStr('MEDIASOUP_WORKER_BIN', '').trim() || undefined,
      // NOTE: rtcMinPort/rtcMaxPort removed — ports are now managed by
      // a single WebRtcServer (WEBRTC_SERVER_PORT). No port range needed.
    },
    listenIps: parseListenIps(),
    exposeInternalIp: envBool('WEBRTC_EXPOSE_INTERNAL_IP', false),
    webRtcServerPort: envInt('WEBRTC_SERVER_PORT', 44444),
    webRtcTransport: {
      ...parseWebRtcTransportProtocols(),
      initialAvailableOutgoingBitrate: envInt(
        'WEBRTC_INITIAL_AVAILABLE_OUTGOING_BITRATE',
        envInt('VIDEO_BITRATE_BPS', 12_000_000)
      ),
      maxIncomingBitrate: envInt(
        'WEBRTC_MAX_INCOMING_BITRATE',
        Math.floor(envInt('VIDEO_BITRATE_BPS', 12_000_000) * 1.25)
      ),
    },
  },

  // ── Bitrate Targets ──
  bitrate: {
    videoBps: envInt('VIDEO_BITRATE_BPS', 12_000_000),
    audioBps: envInt('AUDIO_BITRATE_BPS', 192_000),
  },

  // ── BWE Override ──
  bwe: {
    intervalMs: envInt('BWE_INTERVAL_MS', 50),
    safetyFactor: envFloat('BWE_SAFETY_FACTOR', 0.85),
    plrThreshold: envFloat('BWE_PLR_THRESHOLD', 0.03),
    degradedBitrateBps: envInt('BWE_DEGRADED_BITRATE_BPS', 8_000_000),
  },

  // ── TURN ──
  turn: {
    url: envStr('TURN_URL', ''),
    urls: parseTurnUrls(),
    username: envStr('TURN_USERNAME', ''),
    credential: envStr('TURN_CREDENTIAL', ''),
  },

  // ── Signaling ──
  signaling: {
    requireTls: envBool('SIGNALING_REQUIRE_TLS', true),
    wsPaths: parseWsPaths(),
    disableOriginCheck: envBool('SIGNALING_DISABLE_ORIGIN_CHECK', true),
    allowRequestsWithoutOrigin: envBool('SIGNALING_ALLOW_NO_ORIGIN', true),
    allowedOriginPatterns: parseAllowedOriginPatterns(),
  },
} as const;

// Validate at module load time — kills the process before any worker is created.
validateListenIps(config.mediasoup.listenIps);
warnIfSuspiciousBitrate(
  'WEBRTC_INITIAL_AVAILABLE_OUTGOING_BITRATE',
  config.mediasoup.webRtcTransport.initialAvailableOutgoingBitrate,
  100_000
);
warnIfSuspiciousBitrate(
  'WEBRTC_MAX_INCOMING_BITRATE',
  config.mediasoup.webRtcTransport.maxIncomingBitrate,
  100_000
);
warnIfSuspiciousBitrate('VIDEO_BITRATE_BPS', config.bitrate.videoBps, 100_000);
warnIfSuspiciousBitrate('AUDIO_BITRATE_BPS', config.bitrate.audioBps, 16_000);
warnIfSuspiciousBitrate(
  'BWE_DEGRADED_BITRATE_BPS',
  config.bwe.degradedBitrateBps,
  100_000
);
