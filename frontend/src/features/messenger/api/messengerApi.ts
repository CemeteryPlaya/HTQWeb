/**
 * Messenger API client — isolated from the rest of the app.
 * Uses the shared axios instance for auth token handling.
 */

import api from '@/api/client';
import type {
    ChatUser,
    ChatRoom,
    ChatMessage,
    CreateRoomPayload,
    SendMessagePayload,
} from '../types';

const BASE = 'messenger/';

export const messengerApi = {
    // --- Users ---
    searchUsers: (query: string) =>
        api.get<ChatUser[]>(`${BASE}users/search/`, { params: { q: query } })
            .then(r => r.data),

    searchByDepartment: (dept: string) =>
        api.get<ChatUser[]>(`${BASE}users/search/`, { params: { department: dept } })
            .then(r => r.data),

    getMe: () =>
        api.get<ChatUser>(`${BASE}users/me/`).then(r => r.data),

    // --- Rooms ---
    getRooms: () =>
        api.get<ChatRoom[]>(`${BASE}rooms/`).then(r => r.data),

    createRoom: (payload: CreateRoomPayload) =>
        api.post<ChatRoom>(`${BASE}rooms/create/`, payload).then(r => r.data),

    getRoom: (roomId: number) =>
        api.get<ChatRoom>(`${BASE}rooms/${roomId}/`).then(r => r.data),

    deleteRoom: (roomId: number) =>
        api.delete(`${BASE}rooms/${roomId}/delete/`).then(r => r.data),

    // --- Messages ---
    getMessages: (roomId: number, afterPts = 0, limit = 50) =>
        api.get<ChatMessage[]>(`${BASE}rooms/${roomId}/messages/`, {
            params: { after_pts: afterPts, limit },
        }).then(r => r.data),

    sendMessage: (roomId: number, payload: SendMessagePayload) =>
        api.post<ChatMessage>(`${BASE}rooms/${roomId}/messages/send/`, payload)
            .then(r => r.data),

    getDifference: (roomId: number, localPts: number) =>
        api.get<ChatMessage[]>(`${BASE}rooms/${roomId}/messages/difference/`, {
            params: { local_pts: localPts },
        }).then(r => r.data),

    markRead: (roomId: number, pts: number) =>
        api.post(`${BASE}rooms/${roomId}/read/`, { pts }),

    // --- Attachments ---
    uploadAttachment: (file: File) => {
        const formData = new FormData();
        formData.append('file', file);
        return api.post<{ id: string; file: string; created_at: string; }>(
            `${BASE}attachments/upload/`,
            formData,
            { headers: { 'Content-Type': 'multipart/form-data' } }
        ).then(r => r.data);
    },

    // --- Key Bundles ---
    getKeyBundle: (userId: number) =>
        api.get(`${BASE}keys/${userId}/`).then(r => r.data),

    uploadKeyBundle: (data: {
        identity_pub_key: string;
        signed_prekey: string;
        prekey_signature: string;
    }) => api.post(`${BASE}keys/`, data).then(r => r.data),

    // --- Admin ---
    admin: {
        getAllRooms: () =>
            api.get<ChatRoom[]>(`${BASE}admin/rooms/`).then(r => r.data),

        getRoomMessages: (roomId: number, afterPts = 0, limit = 200) =>
            api.get<{ room: ChatRoom; messages: ChatMessage[] }>(
                `${BASE}admin/rooms/${roomId}/messages/`,
                { params: { after_pts: afterPts, limit } }
            ).then(r => r.data),
    }
};
