/**
 * BWE (Bandwidth Estimation) Override Module
 *
 * Problem: Google Congestion Control (GCC) in Chrome aggressively reduces
 * bitrate at the slightest RTT fluctuation or packet loss. To maintain
 * 12 Mbps for H.265 1080p@60fps, we send custom RTCP REMB packets that
 * override Chrome's internal BWE estimator.
 *
 * Mechanism:
 * - RTCP Payload-specific feedback (PT=206, FMT=15)
 * - REMB (Receiver Estimated Maximum Bitrate)
 * - Sent every 50ms from SFU → Producer (browser)
 * - Target: 85% of max bitrate (safety headroom)
 *
 * Safety: When packet loss > 3%, estimate drops to 8 Mbps.
 *         When loss recovers < 1.5%, ramps up +1 Mbps per check.
 *
 * ☠️ WARNING: This is a hack that fights Chrome's congestion control.
 *    Use with caution. Always implement the safety degradation logic.
 */
import type { types as mediasoupTypes } from 'mediasoup';
export interface BweFeedbackSink {
    sendRtcp(packet: Buffer): Promise<void>;
}
export interface BweOverrideOptions {
    feedbackSink?: BweFeedbackSink;
}
/**
 * Build a REMB RTCP packet.
 *
 * Format (draft-alvestrand-rmcat-remb):
 *
 *  0                   1                   2                   3
 *  0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
 * +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
 * |V=2|P| FMT=15  |   PT=206      |          length               |
 * +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
 * |                  SSRC of packet sender                        |
 * +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
 * |                  SSRC of media source (0)                     |
 * +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
 * |  Unique identifier 'R' 'E' 'M' 'B'                           |
 * +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
 * | Num SSRC=1  | BR Exp    |  BR Mantissa (18 bits)              |
 * +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
 * |   SSRC feedback (producer)                                    |
 * +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
 */
export declare function buildRembPacket(senderSsrc: number, mediaSsrc: number, bitrateBps: number): Buffer;
/**
 * Build RTCP APP feedback packet (PT=204, subtype=13) that carries
 * a compact remote bitrate estimate payload.
 *
 * Payload:
 * - uint32 target bitrate bps
 * - uint32 timestamp seconds
 * - uint32 flags/reserved
 */
export declare function buildRemoteEstimateAppPacket(senderSsrc: number, bitrateBps: number, flags?: number): Buffer;
/**
 * Start periodic REMB injection for a producer.
 *
 * NOTE: Mediasoup v3 does not expose a public sendRtcp() on WebRtcTransport.
 * Two viable approaches:
 *
 * A) Use a DirectTransport pipe to inject raw RTCP.
 * B) Use producer.enableTraceEvent(['bwe']) and react to BWE events,
 *    adjusting Consumer priority/preferred layers instead.
 *
 * Approach B is more idiomatic for Mediasoup and is what we implement here.
 * The REMB packet builder is kept for reference and for raw transport use.
 */
export declare function startBweOverride(transport: mediasoupTypes.WebRtcTransport, producerSsrc: number, producerId: string, options?: BweOverrideOptions): void;
/**
 * Adjust BWE estimate based on network metrics.
 * Called when RTCP stats indicate changes in network quality.
 */
export declare function adjustBweEstimate(producerId: string, packetLossRate: number, _roundTripTimeMs: number): void;
/**
 * Stop BWE override for a producer.
 */
export declare function stopBweOverride(producerId: string): void;
/**
 * Stop all active sessions. Call on server shutdown.
 */
export declare function stopAllBweOverrides(): void;
//# sourceMappingURL=bwe-override.d.ts.map