/**
 * useMessengerSocket — subscribes to messenger socket.io events and refreshes
 * React Query caches in response. Drops REST polling to a slow heartbeat
 * because socket events provide real-time deltas.
 *
 * Usage:
 *   const socket = useMessengerSocket(activeRoomId);
 *   socket.emitTyping(true);
 */

import { useEffect, useMemo } from 'react';
import { useQueryClient } from '@tanstack/react-query';

import {
    getMessengerSocket,
    type MessageNewPayload,
    type MessageReadPayload,
    type UserTypingPayload,
} from '../api/socket';


interface MessengerSocketApi {
    emitTyping: (isTyping: boolean) => void;
}


export function useMessengerSocket(activeRoomId: number | null): MessengerSocketApi {
    const queryClient = useQueryClient();

    useEffect(() => {
        const socket = getMessengerSocket();

        const handleNewMessage = (payload: MessageNewPayload) => {
            queryClient.invalidateQueries({ queryKey: ['messenger-messages', payload.room_id] });
            queryClient.invalidateQueries({ queryKey: ['messenger-rooms'] });
        };
        const handleMessageRead = (payload: MessageReadPayload) => {
            queryClient.invalidateQueries({ queryKey: ['messenger-messages', payload.room_id] });
        };
        const handleUserTyping = (_payload: UserTypingPayload) => {
            // Presence hint — components can opt-in later. No cache invalidation.
        };

        socket.on('message_new', handleNewMessage);
        socket.on('message_read', handleMessageRead);
        socket.on('user_typing', handleUserTyping);

        return () => {
            socket.off('message_new', handleNewMessage);
            socket.off('message_read', handleMessageRead);
            socket.off('user_typing', handleUserTyping);
        };
    }, [queryClient]);

    useEffect(() => {
        if (activeRoomId == null) return;
        const socket = getMessengerSocket();
        socket.emit('join_room', { room_id: activeRoomId });
        return () => {
            socket.emit('leave_room', { room_id: activeRoomId });
        };
    }, [activeRoomId]);

    return useMemo<MessengerSocketApi>(
        () => ({
            emitTyping: (isTyping: boolean) => {
                if (activeRoomId == null) return;
                getMessengerSocket().emit('typing', { room_id: activeRoomId, is_typing: isTyping });
            },
        }),
        [activeRoomId],
    );
}
