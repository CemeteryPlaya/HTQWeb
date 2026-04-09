/**
 * SFU Server Configuration
 * Loads environment variables and provides typed config object.
 */
import type { types as mediasoupTypes } from 'mediasoup';
export declare const config: {
    readonly port: number;
    readonly host: string;
    readonly tls: {
        readonly cert: string;
        readonly key: string;
    };
    readonly mediasoup: {
        readonly numWorkers: number;
        readonly workerSettings: {
            readonly logLevel: mediasoupTypes.WorkerLogLevel;
            readonly logTags: mediasoupTypes.WorkerLogTag[];
            readonly workerBin: string | undefined;
        };
        readonly listenIps: mediasoupTypes.TransportListenIp[];
        readonly exposeInternalIp: boolean;
        readonly webRtcServerPort: number;
        readonly webRtcTransport: {
            readonly initialAvailableOutgoingBitrate: number;
            readonly maxIncomingBitrate: number;
            readonly enableUdp: boolean;
            readonly enableTcp: boolean;
            readonly preferUdp: boolean;
            readonly preferTcp: boolean;
        };
    };
    readonly bitrate: {
        readonly videoBps: number;
        readonly audioBps: number;
    };
    readonly bwe: {
        readonly intervalMs: number;
        readonly safetyFactor: number;
        readonly plrThreshold: number;
        readonly degradedBitrateBps: number;
    };
    readonly turn: {
        readonly url: string;
        readonly urls: string[];
        readonly username: string;
        readonly credential: string;
    };
    readonly signaling: {
        readonly requireTls: boolean;
        readonly wsPaths: string[];
        readonly disableOriginCheck: boolean;
        readonly allowRequestsWithoutOrigin: boolean;
        readonly allowedOriginPatterns: string[];
    };
};
//# sourceMappingURL=config.d.ts.map