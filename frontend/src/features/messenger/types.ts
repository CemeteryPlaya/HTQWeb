/**
 * Messenger feature — TypeScript types
 */

export interface ChatUser {
    id: number;
    user_id: number;
    username: string;
    full_name: string;
    avatar_url: string;
    department_path: string;
    department_name: string;
    position_title: string;
    is_online: boolean;
    last_seen: string;
}

export interface ChatMembership {
    id: number;
    user: ChatUser;
    role: 'member' | 'admin' | 'owner';
    local_pts: number;
    unread_count: number;
    is_muted: boolean;
    is_pinned: boolean;
    joined_at: string;
    last_read_at: string | null;
}

export interface ChatMessage {
    id: number;
    room: number;
    sender: ChatUser | null;
    msg_type: 'text' | 'file' | 'system' | 'key_exchange';
    encrypted_data: string; // base64
    msg_key_b64: string;    // base64
    pts: number;
    pts_count: number;
    seq_no: number | null;
    reply_to: number | null;
    is_edited: boolean;
    created_at: string;
    // Client-side decoded content (after decryption or direct decode)
    _decoded_text?: string;
}

export interface ChatRoom {
    id: number;
    room_type: 'direct' | 'group' | 'secret';
    title: string;
    avatar_url: string;
    current_pts: number;
    memberships: ChatMembership[];
    last_message: ChatMessage | null;
    is_archived: boolean;
    created_at: string;
    updated_at: string;
}

export interface CreateRoomPayload {
    room_type: 'direct' | 'group' | 'secret';
    title?: string;
    member_user_ids: number[];
}

export interface SendMessagePayload {
    encrypted_data: string; // base64
    msg_key?: string;       // base64
    msg_type?: string;
    reply_to?: number | null;
}

// WebSocket incoming message types
export type WsIncoming =
    | { type: 'new_message';[key: string]: any }
    | { type: 'user_typing'; user_id: number; full_name: string }
    | { type: 'read_receipt'; user_id: number; pts: number };
