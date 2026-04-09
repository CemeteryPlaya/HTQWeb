/**
 * MessengerPage — full-page messenger UI.
 *
 * Layout: split-panel with chat list on the left and active chat on the right.
 * Accessible from /messenger route and linked from ProfileSidebar + BottomNav.
 */

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';
import {
    MessageCircle, Send, Search, Plus, ArrowLeft,
    Users, Lock, User, Loader2, Check, CheckCheck, Trash2, Paperclip, FileText, Download, Music, X
} from 'lucide-react';
import { toast } from 'sonner';
import { Header } from '@/components/Header';
import { Footer } from '@/components/Footer';
import { messengerApi } from './api/messengerApi';
import type { ChatRoom, ChatMessage, ChatUser } from './types';

// ---------------------------------------------------------------------------
//  Helper: decode message text from base64 (non-E2EE rooms store plaintext JSON)
// ---------------------------------------------------------------------------
function decodeMessageText(msg: ChatMessage): { text: string; file_url?: string; file_name?: string; mime_type?: string; } | string {
    if (!msg.encrypted_data) return '';
    try {
        const binString = atob(msg.encrypted_data);
        const bytes = Uint8Array.from(binString, (m) => m.codePointAt(0)!);
        const jsonStr = new TextDecoder().decode(bytes);
        const json = JSON.parse(jsonStr);
        if (msg.msg_type === 'file') {
            return json;
        }
        return json.text || json.body || '';
    } catch {
        // For E2EE messages or parsing errors, show placeholder
        try {
            const binString = atob(msg.encrypted_data);
            const bytes = Uint8Array.from(binString, (m) => m.codePointAt(0)!);
            return new TextDecoder().decode(bytes);
        } catch {
            return '🔒 Зашифрованное сообщение';
        }
    }
}

// ---------------------------------------------------------------------------
//  Helper: encode plaintext to base64 for sending (non-E2EE rooms)
// ---------------------------------------------------------------------------
function encodeMessageText(payload: any): string {
    const jsonStr = JSON.stringify(payload);
    const bytes = new TextEncoder().encode(jsonStr);
    const binString = Array.from(bytes, (byte) => String.fromCodePoint(byte)).join("");
    return btoa(binString);
}

// ---------------------------------------------------------------------------
//  Helper: get other user in direct chat
// ---------------------------------------------------------------------------
function getOtherMember(room: ChatRoom, myUserId: number) {
    const other = room.memberships.find(m => m.user.user_id !== myUserId);
    return other?.user || null;
}

// ---------------------------------------------------------------------------
//  Helper: format time
// ---------------------------------------------------------------------------
function formatTime(dateStr: string): string {
    const d = new Date(dateStr);
    const now = new Date();
    const isToday = d.toDateString() === now.toDateString();
    if (isToday) {
        return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }
    return d.toLocaleDateString([], { day: 'numeric', month: 'short' });
}

// ---------------------------------------------------------------------------
//  Main Component
// ---------------------------------------------------------------------------

const MessengerPage: React.FC = () => {
    const { t } = useTranslation();
    const queryClient = useQueryClient();

    const [activeRoomId, setActiveRoomId] = useState<number | null>(null);
    const [showNewChat, setShowNewChat] = useState(false);
    const [searchQuery, setSearchQuery] = useState('');
    const [isGroupMode, setIsGroupMode] = useState(false);
    const [selectedUserIds, setSelectedUserIds] = useState<number[]>([]);
    const [groupTitle, setGroupTitle] = useState('');
    const [messageText, setMessageText] = useState('');
    const [mobileShowChat, setMobileShowChat] = useState(false);
    const [uploadingFile, setUploadingFile] = useState<boolean>(false);
    const [selectedFile, setSelectedFile] = useState<File | null>(null);
    const messagesEndRef = useRef<HTMLDivElement>(null);
    const fileInputRef = useRef<HTMLInputElement>(null);

    // --- Data queries ---
    const { data: me } = useQuery({
        queryKey: ['messenger-me'],
        queryFn: messengerApi.getMe,
    });

    const { data: rooms = [], isLoading: roomsLoading } = useQuery({
        queryKey: ['messenger-rooms'],
        queryFn: messengerApi.getRooms,
        refetchInterval: 5000,
    });

    const { data: messages = [], isLoading: msgsLoading } = useQuery({
        queryKey: ['messenger-messages', activeRoomId],
        queryFn: () => activeRoomId ? messengerApi.getMessages(activeRoomId) : [],
        enabled: !!activeRoomId,
        refetchInterval: 3000,
    });

    const { data: searchResults = [], isLoading: searchLoading } = useQuery({
        queryKey: ['messenger-search', searchQuery],
        queryFn: () => messengerApi.searchUsers(searchQuery),
        enabled: showNewChat,
    });

    // --- Mutations ---
    const sendMutation = useMutation({
        mutationFn: (payload: { text?: string; file_url?: string; file_name?: string; mime_type?: string; msg_type?: string }) => {
            if (!activeRoomId) throw new Error('No active room');
            return messengerApi.sendMessage(activeRoomId, {
                encrypted_data: encodeMessageText(payload),
                msg_type: payload.msg_type || 'text',
            });
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['messenger-messages', activeRoomId] });
            queryClient.invalidateQueries({ queryKey: ['messenger-rooms'] });
        },
        onError: () => toast.error('Ошибка отправки'),
    });

    const createRoomMutation = useMutation({
        mutationFn: (data: { room_type: 'direct' | 'group', member_user_ids: number[], title?: string }) =>
            messengerApi.createRoom(data),
        onSuccess: (room: ChatRoom) => {
            queryClient.invalidateQueries({ queryKey: ['messenger-rooms'] });
            setActiveRoomId(room.id);
            setShowNewChat(false);
            setSearchQuery('');
            setIsGroupMode(false);
            setSelectedUserIds([]);
            setGroupTitle('');
            setMobileShowChat(true);
        },
    });

    const deleteRoomMutation = useMutation({
        mutationFn: (roomId: number) => messengerApi.deleteRoom(roomId),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['messenger-rooms'] });
            setActiveRoomId(null);
            toast.success('Чат удален');
        },
        onError: () => toast.error('Ошибка удаления чата'),
    });

    // --- Scroll to bottom ---
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    // --- Send handler ---
    const handleSend = useCallback(async () => {
        const text = messageText.trim();
        if ((!text && !selectedFile) || sendMutation.isPending || uploadingFile) return;

        if (selectedFile) {
            setUploadingFile(true);
            try {
                const res = await messengerApi.uploadAttachment(selectedFile);
                sendMutation.mutate({
                    text,
                    file_url: res.file, // This assumes backend returns relative/absolute URL
                    file_name: selectedFile.name,
                    mime_type: selectedFile.type,
                    msg_type: 'file',
                });
                setSelectedFile(null);
                if (fileInputRef.current) fileInputRef.current.value = '';
                setMessageText('');
            } catch (err) {
                toast.error('Ошибка загрузки файла');
            } finally {
                setUploadingFile(false);
            }
        } else {
            sendMutation.mutate({ text });
            setMessageText('');
        }
    }, [messageText, selectedFile, sendMutation, uploadingFile]);

    const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (file) {
            setSelectedFile(file);
        }
    };

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    };

    // --- Active room ---
    const activeRoom = rooms.find(r => r.id === activeRoomId) || null;

    const getRoomDisplayName = (room: ChatRoom) => {
        if (room.title) return room.title;
        if (me && (room.room_type === 'direct' || room.room_type === 'secret')) {
            const other = getOtherMember(room, me.user_id);
            return other?.full_name || 'Чат';
        }
        return `Чат #${room.id}`;
    };

    const getRoomAvatar = (room: ChatRoom) => {
        if (me && room.room_type === 'direct') {
            const other = getOtherMember(room, me.user_id);
            return other?.avatar_url || '';
        }
        return room.avatar_url;
    };

    const getLastMessagePreview = (room: ChatRoom) => {
        if (!room.last_message) return 'Нет сообщений';
        const decoded = decodeMessageText(room.last_message);
        if (typeof decoded === 'object') {
            return `📎 ${decoded.file_name || 'Вложение'}`;
        }
        return decoded.substring(0, 60);
    };

    // =========================================================================
    //  RENDER
    // =========================================================================

    return (
        <div className="min-h-screen bg-background flex flex-col">
            <Header />
            <main className="flex-1 container mx-auto px-0 sm:px-4 py-4 sm:py-6 max-w-6xl flex flex-col">
                <div className="mb-4 px-4 sm:px-0">
                    <Link
                        to="/myprofile"
                        className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors w-fit"
                    >
                        <ArrowLeft className="h-4 w-4" />
                        {t('hr.backToMain', 'Назад в профиль')}
                    </Link>
                </div>
                <div className="bg-card rounded-xl border shadow-sm overflow-hidden flex" style={{ height: 'calc(100vh - 200px)', minHeight: '500px' }}>

                    {/* ===== LEFT PANEL: Chat List ===== */}
                    <div className={`w-full sm:w-80 lg:w-96 border-r flex flex-col ${mobileShowChat ? 'hidden sm:flex' : 'flex'}`}>
                        {/* Header */}
                        <div className="p-4 border-b flex items-center justify-between bg-card">
                            <h2 className="font-display text-lg font-bold flex items-center gap-2">
                                <MessageCircle className="h-5 w-5 text-primary" />
                                Сообщения
                            </h2>
                            <button
                                onClick={() => {
                                    setShowNewChat(!showNewChat);
                                    setSearchQuery('');
                                    setIsGroupMode(false);
                                    setSelectedUserIds([]);
                                    setGroupTitle('');
                                }}
                                className="p-2 rounded-lg hover:bg-accent transition-colors"
                                title="Новый чат"
                            >
                                <Plus className="h-5 w-5" />
                            </button>
                        </div>

                        {/* New Chat — employee list with optional search filter */}
                        {showNewChat && (
                            <div className="flex flex-col border-b bg-accent/30 overflow-hidden" style={{ maxHeight: '60%' }}>
                                {/* Search filter */}
                                <div className="p-3 pb-2 flex flex-col gap-3">
                                    <div className="flex justify-between items-center">
                                        <button
                                            onClick={() => { setIsGroupMode(!isGroupMode); setSelectedUserIds([]); setGroupTitle(''); }}
                                            className={`text-xs px-3 py-1.5 rounded-full font-medium transition-colors ${isGroupMode ? 'bg-primary text-primary-foreground' : 'bg-primary/10 text-primary hover:bg-primary/20'}`}
                                        >
                                            {isGroupMode ? 'Отмена группы' : 'Создать группу'}
                                        </button>
                                        {isGroupMode && selectedUserIds.length > 0 && (
                                            <button
                                                onClick={() => createRoomMutation.mutate({ room_type: 'group', member_user_ids: selectedUserIds, title: groupTitle })}
                                                disabled={!groupTitle.trim() || createRoomMutation.isPending}
                                                className="text-xs px-3 py-1.5 rounded-full bg-green-500 text-white font-medium hover:bg-green-600 focus:outline-none disabled:opacity-50"
                                            >
                                                Создать ({selectedUserIds.length + 1})
                                            </button>
                                        )}
                                    </div>

                                    {isGroupMode && (
                                        <input
                                            type="text"
                                            placeholder="Название группы..."
                                            value={groupTitle}
                                            onChange={(e) => setGroupTitle(e.target.value)}
                                            className="w-full px-3 py-2 rounded-lg bg-background border text-sm font-medium focus:outline-none focus:ring-2 focus:ring-primary/40"
                                        />
                                    )}

                                    <div className="relative">
                                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                                        <input
                                            type="text"
                                            placeholder={isGroupMode ? "Поиск участников..." : "Фильтр..."}
                                            value={searchQuery}
                                            onChange={(e) => setSearchQuery(e.target.value)}
                                            className="w-full pl-9 pr-8 py-2 rounded-xl bg-background border text-sm focus:outline-none focus:ring-2 focus:ring-primary/40 transition-shadow"
                                        />
                                        {searchQuery && (
                                            <button
                                                onClick={() => setSearchQuery('')}
                                                className="absolute right-2.5 top-1/2 -translate-y-1/2 p-0.5 rounded-full hover:bg-accent text-muted-foreground hover:text-foreground transition-colors"
                                            >
                                                <span className="text-xs font-bold">✕</span>
                                            </button>
                                        )}
                                    </div>
                                </div>

                                {/* Scrollable employee list */}
                                <div className="flex-1 overflow-y-auto">
                                    {searchLoading ? (
                                        <div className="flex items-center justify-center py-8">
                                            <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
                                        </div>
                                    ) : searchResults.filter(u => u.user_id !== me?.user_id).length > 0 ? (
                                        <div className="py-1">
                                            <p className="px-4 py-1.5 text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">
                                                Сотрудники · {searchResults.filter(u => u.user_id !== me?.user_id).length}
                                            </p>
                                            {searchResults.filter(u => u.user_id !== me?.user_id).map(user => {
                                                const isSelected = selectedUserIds.includes(user.user_id);
                                                return (
                                                    <button
                                                        key={user.id}
                                                        onClick={() => {
                                                            if (isGroupMode) {
                                                                setSelectedUserIds(prev =>
                                                                    prev.includes(user.user_id)
                                                                        ? prev.filter(id => id !== user.user_id)
                                                                        : [...prev, user.user_id]
                                                                );
                                                            } else {
                                                                createRoomMutation.mutate({ room_type: 'direct', member_user_ids: [user.user_id] });
                                                            }
                                                        }}
                                                        className={`w-full flex items-center gap-3 px-4 py-2.5 transition-colors text-left group ${isSelected ? 'bg-primary/10 hover:bg-primary/20' : 'hover:bg-background/60'}`}
                                                    >
                                                        <div className="w-9 h-9 rounded-full bg-gradient-to-br from-primary/20 to-primary/5 flex items-center justify-center text-primary font-bold text-sm flex-shrink-0 group-hover:from-primary/30 group-hover:to-primary/10 transition-all">
                                                            {user.full_name.charAt(0).toUpperCase()}
                                                        </div>
                                                        <div className="flex-1 min-w-0">
                                                            <p className="text-sm font-medium truncate">{user.full_name}</p>
                                                            <p className="text-xs text-muted-foreground truncate">
                                                                {[user.position_title, user.department_name].filter(Boolean).join(' · ') || user.username}
                                                            </p>
                                                        </div>
                                                        {isGroupMode && (
                                                            <div className={`w-5 h-5 rounded-md border flex items-center justify-center flex-shrink-0 transition-colors ${isSelected ? 'bg-primary border-primary text-primary-foreground' : 'border-input bg-background group-hover:border-primary/50'}`}>
                                                                {isSelected && <Check className="h-3 w-3" />}
                                                            </div>
                                                        )}
                                                        {!isGroupMode && user.is_online && (
                                                            <div className="w-2 h-2 rounded-full bg-green-500 flex-shrink-0" title="Онлайн" />
                                                        )}
                                                    </button>
                                                )
                                            })}
                                        </div>
                                    ) : (
                                        <div className="px-4 py-6 text-center text-muted-foreground">
                                            <User className="h-8 w-8 mx-auto mb-2 opacity-30" />
                                            <p className="text-sm">Никого не найдено</p>
                                        </div>
                                    )}
                                </div>
                            </div>
                        )}

                        {/* Room List */}
                        <div className="flex-1 overflow-y-auto">
                            {roomsLoading ? (
                                <div className="flex items-center justify-center h-32">
                                    <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                                </div>
                            ) : rooms.length === 0 ? (
                                <div className="flex flex-col items-center justify-center h-full text-muted-foreground p-8 text-center">
                                    <MessageCircle className="h-12 w-12 mb-3 opacity-30" />
                                    <p className="text-sm font-medium">Нет чатов</p>
                                    <p className="text-xs mt-1">Нажмите + чтобы начать</p>
                                </div>
                            ) : (
                                rooms.map(room => {
                                    const isActive = room.id === activeRoomId;
                                    const unread = room.memberships.find(m => m.user.user_id === me?.user_id)?.unread_count || 0;

                                    return (
                                        <button
                                            key={room.id}
                                            onClick={() => { setActiveRoomId(room.id); setMobileShowChat(true); }}
                                            className={`w-full flex items-center gap-3 p-3 sm:p-4 border-b transition-colors text-left ${isActive ? 'bg-primary/5 border-l-2 border-l-primary' : 'hover:bg-accent/50'
                                                }`}
                                        >
                                            {/* Avatar */}
                                            <div className="relative flex-shrink-0">
                                                {getRoomAvatar(room) ? (
                                                    <img src={getRoomAvatar(room)} alt="" className="w-11 h-11 rounded-full object-cover" />
                                                ) : (
                                                    <div className="w-11 h-11 rounded-full bg-gradient-to-br from-primary/20 to-primary/5 flex items-center justify-center">
                                                        {room.room_type === 'group' ? (
                                                            <Users className="h-5 w-5 text-primary/60" />
                                                        ) : room.room_type === 'secret' ? (
                                                            <Lock className="h-5 w-5 text-primary/60" />
                                                        ) : (
                                                            <span className="font-bold text-primary/60">
                                                                {getRoomDisplayName(room).charAt(0)}
                                                            </span>
                                                        )}
                                                    </div>
                                                )}
                                                {/* Online indicator */}
                                                {room.room_type === 'direct' && me && (() => {
                                                    const other = getOtherMember(room, me.user_id);
                                                    return other?.is_online ? (
                                                        <div className="absolute bottom-0 right-0 w-3 h-3 bg-green-500 rounded-full border-2 border-card" />
                                                    ) : null;
                                                })()}
                                            </div>

                                            {/* Info */}
                                            <div className="flex-1 min-w-0">
                                                <div className="flex items-center justify-between">
                                                    <p className="font-medium text-sm truncate">
                                                        {room.room_type === 'secret' && <Lock className="inline h-3 w-3 mr-1 text-secondary" />}
                                                        {getRoomDisplayName(room)}
                                                    </p>
                                                    {room.last_message && (
                                                        <span className="text-xs text-muted-foreground ml-2 flex-shrink-0">
                                                            {formatTime(room.last_message.created_at)}
                                                        </span>
                                                    )}
                                                </div>
                                                <div className="flex items-center justify-between mt-0.5">
                                                    <p className="text-xs text-muted-foreground truncate max-w-[180px]">
                                                        {getLastMessagePreview(room)}
                                                    </p>
                                                    {unread > 0 && (
                                                        <span className="ml-2 px-1.5 py-0.5 rounded-full bg-primary text-primary-foreground text-[10px] font-bold min-w-[18px] text-center">
                                                            {unread}
                                                        </span>
                                                    )}
                                                </div>
                                            </div>
                                        </button>
                                    );
                                })
                            )}
                        </div>
                    </div>

                    {/* ===== RIGHT PANEL: Chat Room ===== */}
                    <div className={`flex-1 flex flex-col ${!mobileShowChat ? 'hidden sm:flex' : 'flex'}`}>
                        {activeRoom ? (
                            <>
                                {/* Chat Header */}
                                <div className="p-4 border-b flex items-center gap-3 bg-card">
                                    <button
                                        onClick={() => setMobileShowChat(false)}
                                        className="sm:hidden p-1 rounded hover:bg-accent"
                                    >
                                        <ArrowLeft className="h-5 w-5" />
                                    </button>
                                    <div className="w-9 h-9 rounded-full bg-gradient-to-br from-primary/20 to-primary/5 flex items-center justify-center flex-shrink-0">
                                        {activeRoom.room_type === 'secret' ? (
                                            <Lock className="h-4 w-4 text-primary/60" />
                                        ) : (
                                            <span className="font-bold text-primary/60 text-sm">
                                                {getRoomDisplayName(activeRoom).charAt(0)}
                                            </span>
                                        )}
                                    </div>
                                    <div>
                                        <p className="font-medium text-sm">
                                            {activeRoom.room_type === 'secret' && (
                                                <Lock className="inline h-3 w-3 mr-1 text-secondary" />
                                            )}
                                            {getRoomDisplayName(activeRoom)}
                                        </p>
                                        <p className="text-xs text-muted-foreground">
                                            {activeRoom.room_type === 'secret'
                                                ? 'Секретный чат · E2EE'
                                                : activeRoom.room_type === 'group'
                                                    ? `${activeRoom.memberships.length} участников`
                                                    : (() => {
                                                        const other = me ? getOtherMember(activeRoom, me.user_id) : null;
                                                        return other?.is_online ? '🟢 Онлайн' : (other?.position_title || '');
                                                    })()
                                            }
                                        </p>
                                    </div>
                                    <div className="ml-auto flex items-center">
                                        <button
                                            onClick={() => {
                                                if (confirm(activeRoom.room_type === 'group' ? 'Вы уверены, что хотите выйти из группы?' : 'Вы уверены, что хотите удалить этот чат?')) {
                                                    deleteRoomMutation.mutate(activeRoom.id);
                                                }
                                            }}
                                            className="p-2 text-muted-foreground hover:text-destructive hover:bg-destructive/10 rounded-lg transition-colors"
                                            title="Удалить чат (или выйти из группы)"
                                        >
                                            <Trash2 className="h-4 w-4" />
                                        </button>
                                    </div>
                                </div>

                                {/* Messages */}
                                <div className="flex-1 overflow-y-auto p-4 space-y-3 bg-accent/10">
                                    {msgsLoading ? (
                                        <div className="flex items-center justify-center h-full">
                                            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                                        </div>
                                    ) : messages.length === 0 ? (
                                        <div className="flex flex-col items-center justify-center h-full text-muted-foreground">
                                            <MessageCircle className="h-10 w-10 mb-2 opacity-20" />
                                            <p className="text-sm">Начните разговор</p>
                                        </div>
                                    ) : (
                                        messages.map(msg => {
                                            const isMe = msg.sender?.user_id === me?.user_id;
                                            return (
                                                <div
                                                    key={msg.id}
                                                    className={`flex ${isMe ? 'justify-end' : 'justify-start'}`}
                                                >
                                                    <div className={`max-w-[75%] ${isMe ? 'order-1' : ''}`}>
                                                        {!isMe && msg.sender && (
                                                            <p className="text-xs text-muted-foreground mb-1 ml-1">
                                                                {msg.sender.full_name}
                                                            </p>
                                                        )}
                                                        <div
                                                            className={`px-3.5 py-2 rounded-2xl text-sm leading-relaxed ${isMe
                                                                ? 'bg-primary text-primary-foreground rounded-br-md'
                                                                : 'bg-card border rounded-bl-md shadow-sm'
                                                                }`}
                                                        >
                                                            <div className="whitespace-pre-wrap break-words">
                                                                {(() => {
                                                                    const decoded = decodeMessageText(msg);
                                                                    if (typeof decoded === 'object') {
                                                                        const isAudio = decoded.mime_type?.startsWith('audio/');
                                                                        return (
                                                                            <div className="flex flex-col gap-2">
                                                                                {decoded.text && <p className="text-sm mb-1">{decoded.text}</p>}
                                                                                <div className="flex items-center gap-2 bg-background/20 p-2 rounded-lg">
                                                                                    {isAudio ? <Music className="h-5 w-5 opacity-70" /> : <FileText className="h-5 w-5 opacity-70" />}
                                                                                    <span className="text-sm font-medium truncate max-w-[150px]" title={decoded.file_name}>{decoded.file_name || 'Файл'}</span>
                                                                                    <a
                                                                                        href={decoded.file_url}
                                                                                        target="_blank"
                                                                                        rel="noreferrer"
                                                                                        download={decoded.file_name}
                                                                                        className="ml-2 p-1.5 bg-background/30 rounded-full hover:bg-background/50 transition-colors"
                                                                                        title="Скачать"
                                                                                    >
                                                                                        <Download className="h-4 w-4" />
                                                                                    </a>
                                                                                </div>
                                                                                {isAudio && (
                                                                                    <audio controls src={decoded.file_url} className="h-8 max-w-[220px]" />
                                                                                )}
                                                                            </div>
                                                                        )
                                                                    }
                                                                    return decoded;
                                                                })()}
                                                            </div>
                                                            <p className={`text-[10px] mt-1 flex items-center justify-end gap-1 ${isMe ? 'text-primary-foreground/60' : 'text-muted-foreground'
                                                                }`}>
                                                                {formatTime(msg.created_at)}
                                                                {isMe && <CheckCheck className="h-3 w-3" />}
                                                            </p>
                                                        </div>
                                                    </div>
                                                </div>
                                            );
                                        })
                                    )}
                                    <div ref={messagesEndRef} />
                                </div>

                                {/* Message Input */}
                                <div className="p-3 border-t bg-card">
                                    {selectedFile && (
                                        <div className="mb-2 flex items-center justify-between gap-2 bg-accent/30 p-2 rounded-lg border border-accent max-w-sm">
                                            <div className="flex items-center gap-2 min-w-0">
                                                {selectedFile.type.startsWith('audio/') ? <Music className="h-4 w-4 text-primary flex-shrink-0" /> : <FileText className="h-4 w-4 text-primary flex-shrink-0" />}
                                                <span className="text-sm font-medium truncate">{selectedFile.name}</span>
                                            </div>
                                            <button
                                                type="button"
                                                onClick={() => { setSelectedFile(null); if (fileInputRef.current) fileInputRef.current.value = ''; }}
                                                className="p-1 hover:bg-background rounded-full transition-colors flex-shrink-0"
                                                title="Удалить файл"
                                            >
                                                <X className="h-4 w-4 text-muted-foreground hover:text-destructive transition-colors" />
                                            </button>
                                        </div>
                                    )}
                                    <div className="flex items-end gap-2">
                                        <input
                                            type="file"
                                            ref={fileInputRef}
                                            onChange={handleFileSelect}
                                            className="hidden"
                                            accept=".zip,.rar,.doc,.docx,.xls,.xlsx,.pdf,audio/*,image/*,.1c"
                                        />
                                        <button
                                            type="button"
                                            onClick={() => fileInputRef.current?.click()}
                                            disabled={uploadingFile}
                                            className="p-2.5 rounded-xl bg-accent text-accent-foreground hover:bg-accent/80 transition-colors disabled:opacity-40"
                                            title="Прикрепить файл"
                                        >
                                            {uploadingFile ? <Loader2 className="h-5 w-5 animate-spin" /> : <Paperclip className="h-5 w-5" />}
                                        </button>
                                        <textarea
                                            value={messageText}
                                            onChange={(e) => setMessageText(e.target.value)}
                                            onKeyDown={handleKeyDown}
                                            placeholder="Написать сообщение..."
                                            className="flex-1 resize-none rounded-xl border bg-background px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30 max-h-32"
                                            rows={1}
                                        />
                                        <button
                                            onClick={handleSend}
                                            disabled={(!messageText.trim() && !selectedFile) || sendMutation.isPending || uploadingFile}
                                            className="p-2.5 rounded-xl bg-primary text-primary-foreground hover:bg-primary/90 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                                        >
                                            {sendMutation.isPending || uploadingFile ? (
                                                <Loader2 className="h-5 w-5 animate-spin" />
                                            ) : (
                                                <Send className="h-5 w-5" />
                                            )}
                                        </button>
                                    </div>
                                </div>
                            </>
                        ) : (
                            /* Empty state */
                            <div className="flex-1 flex flex-col items-center justify-center text-muted-foreground">
                                <div className="w-24 h-24 rounded-full bg-primary/5 flex items-center justify-center mb-4">
                                    <MessageCircle className="h-12 w-12 text-primary/30" />
                                </div>
                                <p className="font-medium text-lg">Мессенджер</p>
                                <p className="text-sm mt-1 max-w-xs text-center">
                                    Выберите чат слева или создайте новый, чтобы начать общение с коллегами
                                </p>
                            </div>
                        )}
                    </div>
                </div>
            </main>
        </div>
    );
};

export default MessengerPage;
