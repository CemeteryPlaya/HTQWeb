/**
 * Room Manager — Manages Mediasoup Router, Producers, Consumers, and
 * implements Active Speaker detection with dynamic stream multiplexing.
 *
 * Each room creates one Router. Participants produce (send) and consume (receive)
 * media through WebRtcTransports attached to that Router.
 *
 * Key feature: Only top 1-3 active speakers get forwarded at 1080p/12Mbps.
 * Other participants receive paused/thumbnail streams to save bandwidth.
 */
import { types as mediasoupTypes } from 'mediasoup';
export interface Peer {
    id: string;
    displayName: string;
    transports: Map<string, mediasoupTypes.WebRtcTransport>;
    producers: Map<string, mediasoupTypes.Producer>;
    consumers: Map<string, mediasoupTypes.Consumer>;
    audioLevel: number;
    lastAudioLevelUpdate: number;
}
export interface RoomEvents {
    onActiveSpeakersChanged: (speakers: ActiveSpeakerInfo[]) => void;
    onPeerJoined: (peerId: string, displayName: string) => void;
    onPeerLeft: (peerId: string) => void;
    onNewConsumerNeeded: (consumingPeerId: string, producerPeerId: string, producer: mediasoupTypes.Producer) => void;
}
export interface ActiveSpeakerInfo {
    peerId: string;
    audioLevel: number;
    isPrimary: boolean;
}
export interface PeerQualityReport {
    packetLossRate: number;
    rttMs: number;
}
export declare class Room {
    readonly id: string;
    readonly router: mediasoupTypes.Router;
    private readonly webRtcServer;
    private peers;
    private events;
    private audioLevelObserver;
    private readonly MAX_HD_STREAMS;
    private constructor();
    /**
     * Create a new Room with a Mediasoup Router.
     */
    static create(worker: mediasoupTypes.Worker, webRtcServer: mediasoupTypes.WebRtcServer, roomId: string, events: RoomEvents): Promise<Room>;
    /**
     * Get Router RTP capabilities (sent to clients for device loading).
     */
    get rtpCapabilities(): mediasoupTypes.RtpCapabilities;
    /**
     * Get list of existing participants (for new joiners).
     */
    getParticipants(): Array<{
        peerId: string;
        displayName: string;
        producers: Array<{
            producerId: string;
            kind: string;
        }>;
    }>;
    addPeer(peerId: string, displayName: string): void;
    removePeer(peerId: string): void;
    createWebRtcTransport(peerId: string): Promise<{
        transportId: string;
        iceParameters: mediasoupTypes.IceParameters;
        iceCandidates: mediasoupTypes.IceCandidate[];
        dtlsParameters: mediasoupTypes.DtlsParameters;
    }>;
    connectTransport(peerId: string, transportId: string, dtlsParameters: mediasoupTypes.DtlsParameters): Promise<void>;
    produce(peerId: string, transportId: string, kind: mediasoupTypes.MediaKind, rtpParameters: mediasoupTypes.RtpParameters): Promise<string>;
    consume(consumingPeerId: string, transportId: string, producerId: string, rtpCapabilities: mediasoupTypes.RtpCapabilities): Promise<{
        consumerId: string;
        producerId: string;
        kind: mediasoupTypes.MediaKind;
        rtpParameters: mediasoupTypes.RtpParameters;
        producerPeerId: string;
        producerDisplayName: string;
    } | null>;
    resumeConsumer(peerId: string, consumerId: string): Promise<void>;
    pauseConsumer(peerId: string, consumerId: string): Promise<void>;
    hasConsumerForProducer(peerId: string, producerId: string): boolean;
    /**
     * Quality reports from clients are used to modulate the BWE override.
     * We fan out one report to all video producers of that peer.
     */
    handleQualityReport(peerId: string, report: PeerQualityReport): void;
    /**
     * Start periodic active speaker detection.
     * Monitors audio levels and dynamically switches which
     * video streams are forwarded at full quality.
     */
    private startActiveSpeakerDetection;
    /**
     * Dynamic stream multiplexing: only top N speakers get full 1080p.
     * All other video consumers are paused to save bandwidth.
     */
    private updateStreamMultiplexing;
    private getPeer;
    private findPeerByProducerId;
    get peerCount(): number;
    private enforceTargetBitrates;
    /**
     * Close the room and release all resources.
     */
    close(): void;
}
//# sourceMappingURL=room.d.ts.map