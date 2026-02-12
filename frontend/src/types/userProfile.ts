export interface UserProfile {
    id: string;
    email: string;
    firstName?: string;
    lastName?: string;
    display_name: string;
    bio: string;
    avatarUrl?: string; // Read-only URL
    avatar?: File | null; // For upload
    roles: string[];
    settings: {
        language?: string;
        timezone?: string;
    };
    created_at: string;
    updated_at: string;
}

export interface ProfileFormData {
    display_name: string;
    bio: string;
    settings: {
        language?: string;
        timezone?: string;
    };
    avatar?: FileList;
}
