import api from '@/api/client';

export interface UserBasic {
    id: number;
    username: string;
    email: string;
    first_name: string;
    last_name: string;
}

export interface EmailAttachment {
    id: number;
    file: string; // URL
    name?: string;
    uploaded_at: string;
}

export interface EmailMessage {
    id: number;
    subject: string;
    body: string;
    sender: UserBasic;
    is_draft: boolean;
    created_at: string;
    sent_at: string | null;
    attachments: EmailAttachment[];
    external_recipients: string[];
}

export interface EmailRecipientStatus {
    id: number;
    message: EmailMessage;
    user: UserBasic;
    recipient_type: 'to' | 'cc' | 'bcc';
    folder: 'inbox' | 'archive' | 'trash';
    is_read: boolean;
    read_at: string | null;
}

export interface OAuthStatus {
    connected: boolean;
    provider: 'google' | 'microsoft' | null;
    email: string | null;
    primary_email: string | null;
    connected_at?: string;
    token_expires_at?: string;
}

export interface OAuthInitResponse {
    auth_url: string;
    provider: string;
}

export interface OAuthCallbackResponse {
    status: string;
    provider: string;
    email: string;
}

export interface PaginatedResponse<T> {
    count: number;
    next: string | null;
    previous: string | null;
    results: T[];
}

export const emailService = {
    getInbox: async () => {
        const response = await api.get<PaginatedResponse<EmailRecipientStatus>>('/email/inbox/');
        return response.data.results || [];
    },
    getSent: async () => {
        const response = await api.get<PaginatedResponse<EmailMessage>>('/email/sent/');
        return response.data.results || [];
    },
    getDrafts: async () => {
        const response = await api.get<PaginatedResponse<EmailMessage>>('/email/drafts/');
        return response.data.results || [];
    },
    getTrash: async () => {
        const response = await api.get<PaginatedResponse<EmailRecipientStatus>>('/email/trash/');
        return response.data.results || [];
    },
    sendEmail: async (data: FormData) => {
        const response = await api.post<EmailMessage>('/email/send/', data, {
            headers: {
                'Content-Type': 'multipart/form-data',
            },
        });
        return response.data;
    },
    saveDraft: async (data: { subject: string; body: string }) => {
        const response = await api.post<EmailMessage>('/email/draft/', data);
        return response.data;
    },
    markAsRead: async (statusId: number, is_read: boolean = true) => {
        const response = await api.patch<EmailRecipientStatus>(`/email/${statusId}/read/`, { is_read });
        return response.data;
    },

    // ── OAuth 2.0 ──
    getOAuthStatus: async (): Promise<OAuthStatus> => {
        const response = await api.get<OAuthStatus>('/email/oauth/status/');
        return response.data;
    },
    initiateOAuth: async (provider: 'google' | 'microsoft'): Promise<OAuthInitResponse> => {
        const response = await api.get<OAuthInitResponse>(`/email/oauth/init/?provider=${provider}`);
        return response.data;
    },
    handleOAuthCallback: async (code: string, state: string): Promise<OAuthCallbackResponse> => {
        const response = await api.get<OAuthCallbackResponse>(
            `/email/oauth/callback/?code=${encodeURIComponent(code)}&state=${encodeURIComponent(state)}`
        );
        return response.data;
    },
    disconnectOAuth: async (): Promise<{ status: string }> => {
        const response = await api.delete<{ status: string }>('/email/oauth/disconnect/');
        return response.data;
    },
};
