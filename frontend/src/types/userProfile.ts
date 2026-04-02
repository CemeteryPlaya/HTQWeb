export interface UserProfile {
    id: string;
    email: string;
    firstName?: string;
    lastName?: string;
    patronymic?: string;
    phone?: string;
    fio?: string;
    display_name: string;
    bio: string;
    avatarUrl?: string; // Read-only URL
    avatar?: File | null; // For upload
    roles: string[];
    settings: {
        language?: string;
        timezone?: string;
    };
    department?: string;
    department_id?: number;
    position?: string;
    must_change_password?: boolean;
    created_at: string;
    updated_at: string;
}

export interface ProfileFormData {
    firstName?: string;
    lastName?: string;
    patronymic?: string;
    phone?: string;
    display_name: string;
    bio: string;
    settings: {
        language?: string;
        timezone?: string;
    };
    avatar?: FileList;
}
