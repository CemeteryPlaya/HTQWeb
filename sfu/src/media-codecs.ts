/**
 * Mediasoup Media Codecs — tolerant cross-device profile set.
 *
 * This is the central codec registry used when creating Mediasoup Routers.
 * Each Room gets its own Router with these capabilities.
 */

import type { types as mediasoupTypes } from 'mediasoup';

export const mediaCodecs: mediasoupTypes.RtpCodecCapability[] = [
  {
    kind: 'audio',
    mimeType: 'audio/opus',
    preferredPayloadType: 111,
    clockRate: 48000,
    channels: 2,
    parameters: {
      maxaveragebitrate: 192000,
      stereo: 1,
      cbr: 1,
      useinbandfec: 1,
      usedtx: 0,
      'sprop-stereo': 1,
      minptime: 10,
      maxptime: 40,
    },
  },

  // Primary fallback codec across desktop/mobile browsers.
  {
    kind: 'video',
    mimeType: 'video/VP8',
    preferredPayloadType: 96,
    clockRate: 90000,
    parameters: {},
  },

  // H264 Constrained Baseline profile (preferred stable intersection).
  {
    kind: 'video',
    mimeType: 'video/H264',
    preferredPayloadType: 102,
    clockRate: 90000,
    parameters: {
      'packetization-mode': '1',
      'profile-level-id': '42e01f',
      'level-asymmetry-allowed': '1',
    },
  },

  // Keep codec list intentionally strict:
  // - only H264 Constrained Baseline (42e01f)
  // - no H264 Main/High profiles
  // - no H265/HEVC
];
