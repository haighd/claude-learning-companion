import React, { useState, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Plus, Trash2, GripVertical, Link, Tag, CheckCircle2, Clock, AlertCircle, Circle } from 'lucide-react'

// Types
interface KanbanTask {
  id: number
  title: string
  description?: string
  status: string
  priority: number
  tags: string[]
  linked_learnings: string[]
  linked_heuristics: number[]
  created_at: string
  updated_at: string
  completed_at?: string
}

interface GroupedTasks {
  pending: KanbanTask[]
  in_progress: KanbanTask[]
  review: KanbanTask[]
  done: KanbanTask[]
}

type ColumnId = 'pending' | 'in_progress' | 'review' | 'done'

const COLUMN_CONFIG: Record<ColumnId, { label: string; icon: React.ReactNode; color: string }> = {
  pending: { label: 'Pending', icon: <Circle className="w-4 h-4" />, color: 'bg-gray-500' },
  in_progress: { label: 'In Progress', icon: <Clock className="w-4 h-4" />, color: 'bg-blue-500' },
  review: { label: 'Review', icon: <AlertCircle className="w-4 h-4" />, color: 'bg-yellow-500' },
  done: { label: 'Done', icon: <CheckCircle2 className="w-4 h-4" />, color: 'bg-green-500' },
}

const API_BASE = 'http://localhost:8888'

export function KanbanBoard() {
  const [tasks, setTasks] = useState<GroupedTasks>({
    pending: [],
    in_progress: [],
    review: [],
    done: [],
  })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [newTaskTitle, setNewTaskTitle] = useState('')
  const [addingToColumn, setAddingToColumn] = useState<ColumnId | null>(null)

  // Fetch tasks
  const fetchTasks = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/api/kanban/tasks`)
      const data = await response.json()
      setTasks(data.grouped)
      setError(null)
    } catch (err) {
      setError('Failed to load tasks')
      console.error('Error fetching tasks:', err)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchTasks()
  }, [fetchTasks])

  // Create task
  const createTask = async (column: ColumnId) => {
    if (!newTaskTitle.trim()) return

    try {
      const response = await fetch(`${API_BASE}/api/kanban/tasks`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: newTaskTitle,
          status: column,
          priority: 0,
        }),
      })
      const result = await response.json()
      if (result.success) {
        setNewTaskTitle('')
        setAddingToColumn(null)
        fetchTasks()
      }
    } catch (err) {
      console.error('Error creating task:', err)
    }
  }

  // Update task status (move between columns)
  const moveTask = async (taskId: number, newStatus: ColumnId) => {
    try {
      const response = await fetch(`${API_BASE}/api/kanban/tasks/${taskId}/status`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: newStatus }),
      })
      const result = await response.json()
      if (result.success) {
        fetchTasks()
      }
    } catch (err) {
      console.error('Error moving task:', err)
    }
  }

  // Delete task
  const deleteTask = async (taskId: number) => {
    try {
      const response = await fetch(`${API_BASE}/api/kanban/tasks/${taskId}`, {
        method: 'DELETE',
      })
      const result = await response.json()
      if (result.success) {
        fetchTasks()
      }
    } catch (err) {
      console.error('Error deleting task:', err)
    }
  }

  // Handle drag end
  const handleDragEnd = (taskId: number, targetColumn: ColumnId) => {
    moveTask(taskId, targetColumn)
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-red-900/20 border border-red-500/30 rounded-lg p-4">
        <p className="text-red-400">{error}</p>
        <button
          onClick={fetchTasks}
          className="mt-2 px-3 py-1 bg-red-600 hover:bg-red-700 rounded text-sm"
        >
          Retry
        </button>
      </div>
    )
  }

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-xl font-semibold text-gray-100">Workflow Board</h2>
        <div className="text-sm text-gray-400">
          {Object.values(tasks).flat().length} total tasks
        </div>
      </div>

      {/* Kanban Columns */}
      <div className="flex-1 flex gap-4 overflow-x-auto pb-4">
        {(Object.keys(COLUMN_CONFIG) as ColumnId[]).map((columnId) => (
          <KanbanColumn
            key={columnId}
            columnId={columnId}
            config={COLUMN_CONFIG[columnId]}
            tasks={tasks[columnId]}
            onMoveTask={handleDragEnd}
            onDeleteTask={deleteTask}
            addingTask={addingToColumn === columnId}
            onStartAddTask={() => setAddingToColumn(columnId)}
            onCancelAddTask={() => {
              setAddingToColumn(null)
              setNewTaskTitle('')
            }}
            newTaskTitle={newTaskTitle}
            onNewTaskTitleChange={setNewTaskTitle}
            onCreateTask={() => createTask(columnId)}
          />
        ))}
      </div>
    </div>
  )
}

interface KanbanColumnProps {
  columnId: ColumnId
  config: { label: string; icon: React.ReactNode; color: string }
  tasks: KanbanTask[]
  onMoveTask: (taskId: number, targetColumn: ColumnId) => void
  onDeleteTask: (taskId: number) => void
  addingTask: boolean
  onStartAddTask: () => void
  onCancelAddTask: () => void
  newTaskTitle: string
  onNewTaskTitleChange: (value: string) => void
  onCreateTask: () => void
}

function KanbanColumn({
  columnId,
  config,
  tasks,
  onMoveTask,
  onDeleteTask,
  addingTask,
  onStartAddTask,
  onCancelAddTask,
  newTaskTitle,
  onNewTaskTitleChange,
  onCreateTask,
}: KanbanColumnProps) {
  const [isDragOver, setIsDragOver] = useState(false)

  return (
    <div
      className={`flex-shrink-0 w-72 flex flex-col bg-gray-800/50 rounded-lg border transition-colors ${
        isDragOver ? 'border-blue-500/50 bg-blue-900/20' : 'border-gray-700/50'
      }`}
      onDragOver={(e) => {
        e.preventDefault()
        setIsDragOver(true)
      }}
      onDragLeave={() => setIsDragOver(false)}
      onDrop={(e) => {
        e.preventDefault()
        setIsDragOver(false)
        const taskId = parseInt(e.dataTransfer.getData('taskId'))
        if (taskId) {
          onMoveTask(taskId, columnId)
        }
      }}
    >
      {/* Column Header */}
      <div className="p-3 border-b border-gray-700/50">
        <div className="flex items-center gap-2">
          <div className={`p-1 rounded ${config.color}/20 text-${config.color.replace('bg-', '')}`}>
            {config.icon}
          </div>
          <span className="font-medium text-gray-200">{config.label}</span>
          <span className="ml-auto text-sm text-gray-500 bg-gray-700/50 px-2 py-0.5 rounded">
            {tasks.length}
          </span>
        </div>
      </div>

      {/* Tasks */}
      <div className="flex-1 p-2 space-y-2 overflow-y-auto min-h-[200px]">
        <AnimatePresence>
          {tasks.map((task) => (
            <KanbanCard
              key={task.id}
              task={task}
              onDelete={() => onDeleteTask(task.id)}
            />
          ))}
        </AnimatePresence>

        {/* Add Task Form */}
        {addingTask ? (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            className="bg-gray-700/50 rounded-lg p-3"
          >
            <input
              type="text"
              value={newTaskTitle}
              onChange={(e) => onNewTaskTitleChange(e.target.value)}
              placeholder="Task title..."
              className="w-full bg-gray-800 border border-gray-600 rounded px-2 py-1 text-sm text-gray-100 focus:outline-none focus:border-blue-500"
              autoFocus
              onKeyDown={(e) => {
                if (e.key === 'Enter') onCreateTask()
                if (e.key === 'Escape') onCancelAddTask()
              }}
            />
            <div className="flex gap-2 mt-2">
              <button
                onClick={onCreateTask}
                className="flex-1 px-2 py-1 bg-blue-600 hover:bg-blue-700 rounded text-sm"
              >
                Add
              </button>
              <button
                onClick={onCancelAddTask}
                className="px-2 py-1 bg-gray-600 hover:bg-gray-500 rounded text-sm"
              >
                Cancel
              </button>
            </div>
          </motion.div>
        ) : (
          <button
            onClick={onStartAddTask}
            className="w-full p-2 text-gray-500 hover:text-gray-300 hover:bg-gray-700/30 rounded-lg text-sm flex items-center gap-1 justify-center transition-colors"
          >
            <Plus className="w-4 h-4" />
            Add task
          </button>
        )}
      </div>
    </div>
  )
}

interface KanbanCardProps {
  task: KanbanTask
  onDelete: () => void
}

function KanbanCard({ task, onDelete }: KanbanCardProps) {
  const [showActions, setShowActions] = useState(false)

  return (
    <motion.div
      layout
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.95 }}
      draggable
      onDragStart={(e: any) => {
        e.dataTransfer.setData('taskId', task.id.toString())
      }}
      onMouseEnter={() => setShowActions(true)}
      onMouseLeave={() => setShowActions(false)}
      className="bg-gray-700/70 hover:bg-gray-700 rounded-lg p-3 cursor-grab active:cursor-grabbing border border-gray-600/30 hover:border-gray-500/50 transition-colors group"
    >
      {/* Drag Handle */}
      <div className="flex items-start gap-2">
        <GripVertical className="w-4 h-4 text-gray-500 mt-0.5 flex-shrink-0 opacity-0 group-hover:opacity-100 transition-opacity" />
        <div className="flex-1 min-w-0">
          <h4 className="text-sm font-medium text-gray-100 truncate">{task.title}</h4>
          {task.description && (
            <p className="text-xs text-gray-400 mt-1 line-clamp-2">{task.description}</p>
          )}

          {/* Tags */}
          {task.tags.length > 0 && (
            <div className="flex flex-wrap gap-1 mt-2">
              {task.tags.map((tag, i) => (
                <span
                  key={i}
                  className="px-1.5 py-0.5 bg-gray-600/50 text-gray-400 rounded text-xs flex items-center gap-1"
                >
                  <Tag className="w-3 h-3" />
                  {tag}
                </span>
              ))}
            </div>
          )}

          {/* Linked Items */}
          {(task.linked_learnings.length > 0 || task.linked_heuristics.length > 0) && (
            <div className="flex items-center gap-2 mt-2 text-xs text-gray-500">
              <Link className="w-3 h-3" />
              {task.linked_learnings.length > 0 && (
                <span>{task.linked_learnings.length} learnings</span>
              )}
              {task.linked_heuristics.length > 0 && (
                <span>{task.linked_heuristics.length} heuristics</span>
              )}
            </div>
          )}
        </div>

        {/* Actions */}
        <AnimatePresence>
          {showActions && (
            <motion.button
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.8 }}
              onClick={(e) => {
                e.stopPropagation()
                onDelete()
              }}
              className="p-1 text-gray-500 hover:text-red-400 hover:bg-red-500/10 rounded transition-colors"
            >
              <Trash2 className="w-4 h-4" />
            </motion.button>
          )}
        </AnimatePresence>
      </div>
    </motion.div>
  )
}

export default KanbanBoard
