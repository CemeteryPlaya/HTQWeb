import React, { useState, useEffect } from 'react';
import { DragDropContext, Droppable, Draggable, DropResult } from '@hello-pangea/dnd';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Bug, BookOpen, Layers, CheckSquare, ListTodo } from 'lucide-react';

import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import type { Task, TaskStatus } from '@/types/tasks';

const STATUS_CONFIG: Record<TaskStatus, { color: string; labelKey: string }> = {
    open: { color: 'bg-slate-500 text-white', labelKey: 'tasks.pages.list.status.open' },
    in_progress: { color: 'bg-blue-600 text-white', labelKey: 'tasks.pages.list.status.in_progress' },
    in_review: { color: 'bg-purple-500 text-white', labelKey: 'tasks.pages.list.status.in_review' },
    done: { color: 'bg-green-500 text-white', labelKey: 'tasks.pages.list.status.done' },
    closed: { color: 'bg-gray-600 text-white', labelKey: 'tasks.pages.list.status.closed' },
};

const TYPE_ICONS: Record<string, React.ReactNode> = {
    task: <CheckSquare className="h-4 w-4 text-blue-500 shrink-0" />,
    bug: <Bug className="h-4 w-4 text-red-500 shrink-0" />,
    story: <BookOpen className="h-4 w-4 text-green-500 shrink-0" />,
    epic: <Layers className="h-4 w-4 text-purple-500 shrink-0" />,
    subtask: <ListTodo className="h-4 w-4 text-gray-500 shrink-0" />,
};

interface KanbanBoardProps {
    tasks: Task[];
    onStatusChange: (taskId: number, newStatus: TaskStatus) => void;
}

export const KanbanBoard: React.FC<KanbanBoardProps> = ({ tasks, onStatusChange }) => {
    const { t } = useTranslation();
    const [columns, setColumns] = useState<Record<TaskStatus, Task[]>>({
        open: [], in_progress: [], in_review: [], done: [], closed: []
    });

    // Sync tasks prop to local state to allow optimistic immediate sorting
    useEffect(() => {
        const cols: Record<TaskStatus, Task[]> = {
            open: [], in_progress: [], in_review: [], done: [], closed: []
        };
        tasks.forEach(t => {
            if (cols[t.status]) {
                cols[t.status].push(t);
            }
        });
        setColumns(cols);
    }, [tasks]);

    const onDragEnd = (result: DropResult) => {
        if (!result.destination) return;
        const { source, destination, draggableId } = result;

        if (source.droppableId !== destination.droppableId) {
            const sourceCol = source.droppableId as TaskStatus;
            const destCol = destination.droppableId as TaskStatus;

            const newCols = { ...columns };
            const sourceTasks = [...newCols[sourceCol]];
            const destTasks = [...newCols[destCol]];

            const [movedTask] = sourceTasks.splice(source.index, 1);
            movedTask.status = destCol; // optimistic update
            destTasks.splice(destination.index, 0, movedTask);

            newCols[sourceCol] = sourceTasks;
            newCols[destCol] = destTasks;

            setColumns(newCols);
            onStatusChange(Number(draggableId), destCol);
        } else {
            // Reordering within the same column
            const col = source.droppableId as TaskStatus;
            const newCols = { ...columns };
            const colTasks = [...newCols[col]];
            const [movedTask] = colTasks.splice(source.index, 1);
            colTasks.splice(destination.index, 0, movedTask);
            newCols[col] = colTasks;

            setColumns(newCols);
        }
    };

    return (
        <DragDropContext onDragEnd={onDragEnd}>
            <div className="flex gap-4 overflow-x-auto pb-4 h-[calc(100vh-250px)] min-h-[500px] w-full items-start">
                {(Object.keys(STATUS_CONFIG) as TaskStatus[]).map(status => (
                    <div key={status} className="bg-muted/30 rounded-xl p-3 flex flex-col w-[320px] shrink-0 border border-muted/50">
                        <div className="flex items-center justify-between mb-3 px-1">
                            <span className="font-semibold text-sm uppercase tracking-wider text-muted-foreground">
                                {t(STATUS_CONFIG[status].labelKey, status)}
                            </span>
                            <Badge variant="secondary" className="rounded-full shadow-sm">
                                {columns[status].length}
                            </Badge>
                        </div>

                        <Droppable droppableId={status}>
                            {(provided, snapshot) => (
                                <div
                                    ref={provided.innerRef}
                                    {...provided.droppableProps}
                                    className={`flex-1 flex flex-col gap-3 min-h-[100px] transition-colors rounded-lg ${snapshot.isDraggingOver ? 'bg-primary/5' : ''}`}
                                >
                                    {columns[status].map((task, index) => (
                                        <Draggable key={task.id} draggableId={String(task.id)} index={index}>
                                            {(provided, snapshot) => (
                                                <div
                                                    ref={provided.innerRef}
                                                    {...provided.draggableProps}
                                                    {...provided.dragHandleProps}
                                                    className="focus:outline-none"
                                                    style={provided.draggableProps.style}
                                                >
                                                    <Card className={`cursor-grab hover:border-primary/50 transition-all shadow-sm ${snapshot.isDragging ? 'rotate-2 scale-105 shadow-md border-primary' : ''}`}>
                                                        <CardContent className="p-3">
                                                            <div className="flex justify-between items-start mb-2">
                                                                <Link to={`/tasks/${task.id}`} className="font-mono text-xs font-bold text-primary hover:underline">
                                                                    {task.key}
                                                                </Link>
                                                                <span className={`text-[10px] uppercase font-bold px-1.5 py-0.5 rounded text-white ${task.priority === 'critical' ? 'bg-red-500' : task.priority === 'high' ? 'bg-orange-500' : task.priority === 'medium' ? 'bg-yellow-500' : 'bg-blue-500'}`}>
                                                                    {task.priority}
                                                                </span>
                                                            </div>
                                                            <p className="text-sm font-medium mb-3 line-clamp-2 leading-tight">
                                                                {task.summary}
                                                            </p>
                                                            <div className="flex items-center justify-between text-xs text-muted-foreground">
                                                                <div className="flex items-center gap-1.5">
                                                                    {TYPE_ICONS[task.task_type]}
                                                                </div>
                                                                <div className="flex -space-x-1">
                                                                    {task.assignee_name ? (
                                                                        <div
                                                                            className="h-6 w-6 rounded-full bg-primary/10 border border-background flex items-center justify-center text-[10px] font-bold text-primary"
                                                                            title={task.assignee_name}
                                                                        >
                                                                            {task.assignee_name.charAt(0).toUpperCase()}
                                                                        </div>
                                                                    ) : (
                                                                        <div className="h-6 w-6 rounded-full bg-muted border border-background flex items-center justify-center" title="Unassigned">
                                                                            <span className="text-muted-foreground">?</span>
                                                                        </div>
                                                                    )}
                                                                </div>
                                                            </div>
                                                        </CardContent>
                                                    </Card>
                                                </div>
                                            )}
                                        </Draggable>
                                    ))}
                                    {provided.placeholder}
                                </div>
                            )}
                        </Droppable>
                    </div>
                ))}
            </div>
        </DragDropContext>
    );
};
