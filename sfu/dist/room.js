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
import { mediaCodecs } from './media-codecs.js';
import { config } from './config.js';
import { startBweOverride, stopBweOverride, adjustBweEstimate } from './bwe-override.js';
// ═══════════════════════════════════════════════════════════
// Room Class
// ═══════════════════════════════════════════════════════════
export class Room {
    id;
    router;
    webRtcServer;
    peers = new Map();
    events;
    // Active speaker state
    audioLevelObserver = null;
    MAX_HD_STREAMS = 3; // Top N speakers get 1080p
    constructor(id, router, webRtcServer, events) {
        this.id = id;
        this.router = router;
        this.webRtcServer = webRtcServer;
        this.events = events;
    }
    /**
     * Create a new Room with a Mediasoup Router.
     */
    static async create(worker, webRtcServer, roomId, events) {
        const router = await worker.createRouter({ mediaCodecs });
        console.log(`[Room ${roomId}] Created with codecs:`, router.rtpCapabilities.codecs?.map((c) => c.mimeType).join(', '));
        const room = new Room(roomId, router, webRtcServer, events);
        room.startActiveSpeakerDetection();
        return room;
    }
    /**
     * Get Router RTP capabilities (sent to clients for device loading).
     */
    get rtpCapabilities() {
        return this.router.rtpCapabilities;
    }
    /**
     * Get list of existing participants (for new joiners).
     */
    getParticipants() {
        const result = [];
        for (const [peerId, peer] of this.peers) {
            const producers = [];
            for (const [producerId, producer] of peer.producers) {
                producers.push({ producerId, kind: producer.kind });
            }
            result.push({ peerId, displayName: peer.displayName, producers });
        }
        return result;
    }
    // ─────────────────────────────────────────────────────
    // Peer Lifecycle
    // ─────────────────────────────────────────────────────
    addPeer(peerId, displayName) {
        if (this.peers.has(peerId)) {
            console.warn(`[Room ${this.id}] Peer ${peerId} already exists`);
            return;
        }
        const peer = {
            id: peerId,
            displayName,
            transports: new Map(),
            producers: new Map(),
            consumers: new Map(),
            audioLevel: 0,
            lastAudioLevelUpdate: Date.now(),
        };
        this.peers.set(peerId, peer);
        this.events.onPeerJoined(peerId, displayName);
        console.log(`[Room ${this.id}] Peer joined: ${displayName} (${peerId})`);
    }
    removePeer(peerId) {
        const peer = this.peers.get(peerId);
        if (!peer)
            return;
        // Close all consumers
        for (const [, consumer] of peer.consumers) {
            try {
                if (!consumer.closed) {
                    consumer.close();
                }
            }
            catch (error) {
                console.warn(`[Room ${this.id}] Failed to close consumer ${consumer.id} for peer ${peerId}:`, error);
            }
        }
        peer.consumers.clear();
        // Close all producers (and stop BWE override)
        for (const [producerId, producer] of peer.producers) {
            try {
                stopBweOverride(producerId);
                if (!producer.closed) {
                    producer.close();
                }
            }
            catch (error) {
                console.warn(`[Room ${this.id}] Failed to close producer ${producerId} for peer ${peerId}:`, error);
            }
        }
        peer.producers.clear();
        // Close all transports
        for (const [, transport] of peer.transports) {
            try {
                if (!transport.closed) {
                    transport.close();
                }
            }
            catch (error) {
                console.warn(`[Room ${this.id}] Failed to close transport ${transport.id} for peer ${peerId}:`, error);
            }
        }
        peer.transports.clear();
        this.peers.delete(peerId);
        this.events.onPeerLeft(peerId);
        console.log(`[Room ${this.id}] Peer left: ${peer.displayName} (${peerId})`);
    }
    // ─────────────────────────────────────────────────────
    // Transport
    // ─────────────────────────────────────────────────────
    async createWebRtcTransport(peerId) {
        const peer = this.getPeer(peerId);
        // Use WebRtcServer (single-port) instead of listenIps (port-range).
        // The webRtcServer already has the correct IP / announcedAddress bound.
        const transport = await this.router.createWebRtcTransport({
            webRtcServer: this.webRtcServer,
            enableUdp: config.mediasoup.webRtcTransport.enableUdp,
            enableTcp: config.mediasoup.webRtcTransport.enableTcp,
            preferUdp: config.mediasoup.webRtcTransport.preferUdp,
            preferTcp: config.mediasoup.webRtcTransport.preferTcp,
            initialAvailableOutgoingBitrate: config.mediasoup.webRtcTransport.initialAvailableOutgoingBitrate,
        });
        // Set max incoming bitrate
        const maxIncomingBitrate = config.mediasoup.webRtcTransport.maxIncomingBitrate;
        if (maxIncomingBitrate > 0) {
            await transport.setMaxIncomingBitrate(maxIncomingBitrate);
        }
        // Monitor transport-level DTLS state
        transport.on('dtlsstatechange', (dtlsState) => {
            if (dtlsState === 'failed' || dtlsState === 'closed') {
                console.warn(`[Room ${this.id}] Transport ${transport.id} DTLS state: ${dtlsState}`);
                transport.close();
            }
        });
        transport.on('@close', () => {
            peer.transports.delete(transport.id);
        });
        peer.transports.set(transport.id, transport);
        return {
            transportId: transport.id,
            iceParameters: transport.iceParameters,
            iceCandidates: transport.iceCandidates,
            dtlsParameters: transport.dtlsParameters,
        };
    }
    async connectTransport(peerId, transportId, dtlsParameters) {
        const peer = this.getPeer(peerId);
        const transport = peer.transports.get(transportId);
        if (!transport)
            throw new Error(`Transport ${transportId} not found`);
        await transport.connect({ dtlsParameters });
    }
    // ─────────────────────────────────────────────────────
    // Producer (sending media)
    // ─────────────────────────────────────────────────────
    async produce(peerId, transportId, kind, rtpParameters) {
        const peer = this.getPeer(peerId);
        const transport = peer.transports.get(transportId);
        if (!transport)
            throw new Error(`Transport ${transportId} not found`);
        const producer = await transport.produce({
            kind,
            rtpParameters: this.enforceTargetBitrates(kind, rtpParameters),
        });
        peer.producers.set(producer.id, producer);
        // For video producers, start BWE override to maintain 12 Mbps
        if (kind === 'video') {
            const ssrc = producer.rtpParameters.encodings?.[0]?.ssrc ??
                rtpParameters.encodings?.[0]?.ssrc;
            if (ssrc) {
                startBweOverride(transport, ssrc, producer.id);
            }
        }
        // Track audio levels for active speaker detection
        if (kind === 'audio') {
            this.audioLevelObserver
                ?.addProducer({ producerId: producer.id })
                .catch(() => {
                // Producer may close before observer attaches.
            });
            producer.on('score', (score) => {
                // Use producer score as proxy for audio activity
                // (Real implementation would use audioLevelObserver)
            });
        }
        // Notify all other peers to create consumers
        for (const [otherPeerId, otherPeer] of this.peers) {
            if (otherPeerId === peerId)
                continue;
            this.events.onNewConsumerNeeded(otherPeerId, peerId, producer);
        }
        producer.on('transportclose', () => {
            console.log(`[Room ${this.id}] Producer ${producer.id} transport closed`);
            if (producer.kind === 'audio') {
                this.audioLevelObserver
                    ?.removeProducer({ producerId: producer.id })
                    .catch(() => {
                    // Ignore race with close.
                });
            }
            stopBweOverride(producer.id);
            peer.producers.delete(producer.id);
        });
        producer.on('@close', () => {
            stopBweOverride(producer.id);
            peer.producers.delete(producer.id);
        });
        console.log(`[Room ${this.id}] ${peer.displayName} producing ${kind} (${producer.id})`);
        return producer.id;
    }
    // ─────────────────────────────────────────────────────
    // Consumer (receiving media)
    // ─────────────────────────────────────────────────────
    async consume(consumingPeerId, transportId, producerId, rtpCapabilities) {
        // Check if Router can consume this producer
        if (!this.router.canConsume({ producerId, rtpCapabilities })) {
            console.warn(`[Room ${this.id}] Cannot consume producer ${producerId} — codec mismatch`);
            return null;
        }
        const consumingPeer = this.getPeer(consumingPeerId);
        const transport = consumingPeer.transports.get(transportId);
        if (!transport)
            throw new Error(`Transport ${transportId} not found`);
        // Find the producer's peer for display name
        let producerPeerId = '';
        let producerDisplayName = '';
        for (const [pid, peer] of this.peers) {
            if (peer.producers.has(producerId)) {
                producerPeerId = pid;
                producerDisplayName = peer.displayName;
                break;
            }
        }
        // If this peer already has a live consumer for the same producer,
        // return existing mapping instead of creating duplicates.
        for (const [, existingConsumer] of consumingPeer.consumers) {
            if (existingConsumer.producerId === producerId && !existingConsumer.closed) {
                return {
                    consumerId: existingConsumer.id,
                    producerId: existingConsumer.producerId,
                    kind: existingConsumer.kind,
                    rtpParameters: existingConsumer.rtpParameters,
                    producerPeerId,
                    producerDisplayName,
                };
            }
        }
        const consumer = await transport.consume({
            producerId,
            rtpCapabilities,
            paused: true, // Start paused; client resumes when ready
        });
        consumingPeer.consumers.set(consumer.id, consumer);
        consumer.on('transportclose', () => {
            consumingPeer.consumers.delete(consumer.id);
        });
        consumer.on('producerclose', () => {
            consumingPeer.consumers.delete(consumer.id);
        });
        consumer.on('@close', () => {
            consumingPeer.consumers.delete(consumer.id);
        });
        return {
            consumerId: consumer.id,
            producerId: consumer.producerId,
            kind: consumer.kind,
            rtpParameters: consumer.rtpParameters,
            producerPeerId,
            producerDisplayName,
        };
    }
    async resumeConsumer(peerId, consumerId) {
        const peer = this.getPeer(peerId);
        const consumer = peer.consumers.get(consumerId);
        if (!consumer)
            throw new Error(`Consumer ${consumerId} not found`);
        await consumer.resume();
    }
    async pauseConsumer(peerId, consumerId) {
        const peer = this.getPeer(peerId);
        const consumer = peer.consumers.get(consumerId);
        if (!consumer)
            throw new Error(`Consumer ${consumerId} not found`);
        await consumer.pause();
    }
    hasConsumerForProducer(peerId, producerId) {
        const peer = this.getPeer(peerId);
        for (const [, consumer] of peer.consumers) {
            if (consumer.producerId === producerId && !consumer.closed) {
                return true;
            }
        }
        return false;
    }
    /**
     * Quality reports from clients are used to modulate the BWE override.
     * We fan out one report to all video producers of that peer.
     */
    handleQualityReport(peerId, report) {
        const peer = this.peers.get(peerId);
        if (!peer)
            return;
        const packetLossRate = Math.max(0, Math.min(report.packetLossRate, 1));
        const rttMs = Math.max(0, report.rttMs);
        for (const [producerId, producer] of peer.producers) {
            if (producer.kind !== 'video')
                continue;
            adjustBweEstimate(producerId, packetLossRate, rttMs);
        }
    }
    // ─────────────────────────────────────────────────────
    // Active Speaker Detection & Stream Multiplexing
    // ─────────────────────────────────────────────────────
    /**
     * Start periodic active speaker detection.
     * Monitors audio levels and dynamically switches which
     * video streams are forwarded at full quality.
     */
    startActiveSpeakerDetection() {
        // Create AudioLevelObserver on the Router
        this.router
            .createAudioLevelObserver({
            maxEntries: this.MAX_HD_STREAMS,
            threshold: -50, // dBov threshold for "speaking"
            interval: 800, // Check every 800ms
        })
            .then((observer) => {
            this.audioLevelObserver = observer;
            observer.on('volumes', (volumes) => {
                const speakers = volumes.map((vol, idx) => {
                    // Find the peer who owns this producer
                    const peerId = this.findPeerByProducerId(vol.producer.id);
                    if (peerId) {
                        const peer = this.peers.get(peerId);
                        if (peer) {
                            peer.audioLevel = vol.volume;
                            peer.lastAudioLevelUpdate = Date.now();
                        }
                    }
                    return {
                        peerId: peerId || 'unknown',
                        audioLevel: vol.volume,
                        isPrimary: idx === 0,
                    };
                });
                if (speakers.length > 0) {
                    this.events.onActiveSpeakersChanged(speakers);
                    this.updateStreamMultiplexing(speakers);
                }
            });
            observer.on('silence', () => {
                // No one is speaking — keep last active speaker
            });
            // Add all existing audio producers to the observer
            for (const [, peer] of this.peers) {
                for (const [, producer] of peer.producers) {
                    if (producer.kind === 'audio') {
                        observer.addProducer({ producerId: producer.id }).catch(() => {
                            // Producer might have closed
                        });
                    }
                }
            }
            console.log(`[Room ${this.id}] AudioLevelObserver started`);
        })
            .catch((err) => {
            console.error(`[Room ${this.id}] Failed to create AudioLevelObserver:`, err);
        });
    }
    /**
     * Dynamic stream multiplexing: only top N speakers get full 1080p.
     * All other video consumers are paused to save bandwidth.
     */
    updateStreamMultiplexing(speakers) {
        // When few participants are in the room, don't pause any streams —
        // everyone gets full-quality video without active-speaker gating.
        if (this.peers.size <= this.MAX_HD_STREAMS) {
            // Ensure all video consumers are resumed (undo any prior pauses).
            for (const [, peer] of this.peers) {
                for (const [, consumer] of peer.consumers) {
                    if (consumer.kind === 'video' && consumer.paused) {
                        consumer.resume().catch(() => { });
                    }
                }
            }
            return;
        }
        const activePeerIds = new Set(speakers.slice(0, this.MAX_HD_STREAMS).map((s) => s.peerId));
        for (const [peerId, peer] of this.peers) {
            // For each peer's consumers (what they receive)
            for (const [, consumer] of peer.consumers) {
                if (consumer.kind !== 'video')
                    continue;
                // Find who produced this stream
                const producerPeerId = this.findPeerByProducerId(consumer.producerId);
                if (!producerPeerId)
                    continue;
                if (activePeerIds.has(producerPeerId)) {
                    // Active speaker → resume full-quality video
                    if (consumer.paused) {
                        consumer.resume().catch(() => { });
                    }
                }
                else {
                    // Non-active → pause video to save bandwidth
                    if (!consumer.paused) {
                        consumer.pause().catch(() => { });
                    }
                }
            }
        }
    }
    // ─────────────────────────────────────────────────────
    // Helpers
    // ─────────────────────────────────────────────────────
    getPeer(peerId) {
        const peer = this.peers.get(peerId);
        if (!peer)
            throw new Error(`Peer ${peerId} not found in room ${this.id}`);
        return peer;
    }
    findPeerByProducerId(producerId) {
        for (const [peerId, peer] of this.peers) {
            if (peer.producers.has(producerId))
                return peerId;
        }
        return null;
    }
    get peerCount() {
        return this.peers.size;
    }
    enforceTargetBitrates(kind, rtpParameters) {
        const encodings = rtpParameters.encodings && rtpParameters.encodings.length > 0
            ? rtpParameters.encodings.map((encoding) => ({ ...encoding }))
            : [{}];
        if (kind === 'video') {
            for (const encoding of encodings) {
                encoding.maxBitrate = config.bitrate.videoBps;
            }
        }
        if (kind === 'audio') {
            for (const encoding of encodings) {
                encoding.maxBitrate = config.bitrate.audioBps;
            }
        }
        return {
            ...rtpParameters,
            encodings,
        };
    }
    /**
     * Close the room and release all resources.
     */
    close() {
        this.audioLevelObserver?.close();
        this.audioLevelObserver = null;
        for (const [peerId] of this.peers) {
            this.removePeer(peerId);
        }
        this.router.close();
        console.log(`[Room ${this.id}] Closed`);
    }
}
//# sourceMappingURL=room.js.map